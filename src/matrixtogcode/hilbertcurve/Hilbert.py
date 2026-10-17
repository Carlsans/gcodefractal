import math
import os
import random
import time

import matplotlib.pyplot as plt
from turtle import *
import torchvision.transforms as transforms
import numpy as np
import torch
from PIL import Image

from src.matrixtogcode.Configuration import Configuration
from src.matrixtogcode.GcodeInterpreter import GcodeInterpreter
from src.matrixtogcode.Machine import Machine


class HilbertMatrix:
    def __init__(self, n, conf, gcode, loadfromcache=True):
        self.conf = conf
        self.gcode = gcode
        self.dir_path = os.path.dirname(os.path.realpath(__file__))
        self.hilbertmatrixfilename = self.dir_path + '/hilbert_of_n_' + str(n) + '.pt'
        self.hilbertdirectionvectorfilename = self.dir_path + '/hilbertdirection_of_n_' + str(n) + '.pt'
        print("self.hilbertmatrixfilename",self.hilbertmatrixfilename)
        self.hilbertmatrixfiles = []
        self.hilbertdirectionfiles = []
        self.gcodefilepath = 'hilbertcurve/gcodetest.gcode'
        d = int(math.pow(2, n + 1))
        max = int(d * d - 1)
        print("d=", d, "max=", max)
        self.n = n
        self.d = d
        self.max = max
        if loadfromcache and os.path.isfile(self.hilbertmatrixfilename):
            self.hilbertmatrixindex = torch.load(self.hilbertmatrixfilename, weights_only=True)
            print("Loaded from cache Hilbert Matrix of shape", self.hilbertmatrixindex.shape)
        else:

            self.hilbertmatrixindex = torch.zeros((d, d), dtype=torch.int32, requires_grad=False)
            self.generate_rule()
            self.generate_indexmatrix()
        # if loadfromcache and os.path.isfile(self.hilbertdirectionvectorfilename):
        #     self.hilbertdirectionvector = torch.load(self.hilbertdirectionvectorfilename, weights_only=True)
        # else:
        #     self.generate_direction_vector()
        #self.hilbertmatrixindex = self.scrambleHilbertMatrix()
        #self.generate_direction_vector()


    def generate_Hilbert_path(self, imagetensor):

        # Padding (le tenseur d'origine doit être superposé à la matrice d'hilbert de 4096*4096)
        imagetensorcopy = torch.clone(imagetensor)
        imagetensor = torch.zeros_like(self.hilbertmatrixindex, dtype=torch.int32)
        imagetensor[0:imagetensorcopy.shape[0], 0:imagetensorcopy.shape[1]] += imagetensorcopy
        # Matrice qui contient l'ordre et les coordonnées X et Y de la matrice d'hilbert
        hilbertmatrixindexandcoord = torch.zeros(3, self.hilbertmatrixindex.shape[0], self.hilbertmatrixindex.shape[1],
                                                 dtype=torch.int32)
        xcoord = torch.arange(0, self.hilbertmatrixindex.shape[0], dtype=torch.int32) * torch.ones(
            (self.hilbertmatrixindex.shape[0], self.hilbertmatrixindex.shape[0]), dtype=torch.int32)
        ycoord = xcoord.mT
        hilbertmatrixindexandcoord[0, :, :] = self.hilbertmatrixindex
        hilbertmatrixindexandcoord[1, :, :] = xcoord
        hilbertmatrixindexandcoord[2, :, :] = ycoord

        # On sélectionne seulement les points qui seront dessinés
        selectedHilbertpathmatrix = hilbertmatrixindexandcoord * imagetensor
        # On met le tout en ordre d'index (poutine compliquée parce que pas assez de mémoire)
        values_to_sort = selectedHilbertpathmatrix[0, :, :]
        values_to_sort = torch.flatten(values_to_sort)

        sorted_indices = torch.argsort(values_to_sort, dim=0)
        cuts = 256  # Multiple de 2 svp ! (nombre de coupes à effectuer)
        cutssize = int((self.d * self.d) / cuts)
        # On applati le tout pour ensuite couper
        order, x, y = torch.flatten(selectedHilbertpathmatrix[0, :]), torch.flatten(
            selectedHilbertpathmatrix[1, :]), torch.flatten(selectedHilbertpathmatrix[2, :])
        # Tenseur vides à concaténer
        currentorder, currentx, currenty = torch.tensor([],dtype=torch.int32), torch.tensor([]), torch.tensor([])
        flattenedimagetensor = torch.flatten(imagetensor).to(torch.bool)
        # On effectue les coupes
        for i in range(cuts):
            start, stop = i * cutssize, i * cutssize + cutssize - 1
            currentsorted_indices = sorted_indices[start:stop]
            currentimagetensor = flattenedimagetensor[currentsorted_indices]
            #print("currentimagetensor",currentimagetensor)
            # seuls les indices de l'image doivent être récupérés, les autres = -1
            currentsorted_indices = torch.where(currentimagetensor,currentsorted_indices,-1)
            # Comme beaucoup de coupes incluent des valeurs index qui contiennent seulement des zeros
            if torch.sum(currentimagetensor) == 0:
                print("Skipping, no indices")
                continue
            #torch.set_printoptions(profile="full")
            #print(currentsorted_indices)
            # on enlève les indices qui ne correspondent pas à des points de l'image
            currentsorted_indices = currentsorted_indices[currentsorted_indices != -1]
            #print(currentsorted_indices)
            #print(currentsorted_indices.shape)
            # On concatène les valeurs des indices ordonnés sans faire crasher le programme par manque de mémoire
            currentorder, currentx, currenty = torch.cat((currentorder, order[currentsorted_indices])), torch.cat(
                (currentx, x[currentsorted_indices])), torch.cat((currenty, y[currentsorted_indices]))

            # sortedorder, sortedcurrentx, sortedcurrenty = currentorder[currentsorted_indices], currentx[currentsorted_indices], currenty[currentsorted_indices]
            # print(sortedorder, sortedcurrentx, sortedcurrenty)
            # result = torch.cat(result,)
        print("currentorder,len(currentorder), currentx, currenty", currentorder, currentx, currenty)
        print("currentorder.shape, currentx.shape, currenty.shape", currentorder.shape, currentx.shape, currenty.shape)
        print("original shape ??? ",flattenedimagetensor.shape)

        gcodex = currentx.detach().numpy()
        gcodey = currenty.detach().numpy()
        gcodeorder = currentorder.detach().numpy()
        numpyhilbertdirectionvector = self.hilbertdirectionvector.detach().numpy()
        self.lastindex = -1
        #self.e = 0
        self.lastx, self.lasty, self.lastorder = -1,-1,-1
        self.isup = True
        self.lastmove = ""
        #self.completegcode = ""
        # Note, inversion de x et y fonctionne pour une raison qui m'échappe.....
        def gcode(y,x,nexty,nextx,order,nextorder):
            gcode = ""
            #self.e+=1
            #print(self.e,order)
            #print("order",order,"nextorder",nextorder)
            currentdirection = numpyhilbertdirectionvector[:,order]
            #print("direction",currentdirection)
            if currentdirection[1]==1:
                compensationx = self.conf.machinecompensationx[1]
            elif currentdirection[1]==-1:
                compensationx = self.conf.machinecompensationx[0]
            else:
                compensationx = 0
            if currentdirection[0]==1:
                compensationy = self.conf.machinecompensationy[1]
            elif currentdirection[0]==-1:
                compensationy = self.conf.machinecompensationy[0]
            else:
                compensationy = 0
            #print("Compensation",compensationx,compensationy)
            squareddistance = pow((float(self.gcode.getyfromindex(y))-float(self.gcode.getyfromindex(nexty))),2)+pow((float(self.gcode.getxfromindex(x))-float(self.gcode.getxfromindex(nextx))),2)
            squaredmaxdistance = self.conf.shorttravelmaxdistance
            longtravel = squareddistance > squaredmaxdistance
            consecutivemove =  (nextorder - order) == 1 and np.abs(currentdirection[1])<=1 and np.abs(currentdirection[0])<=1
            zspeed = " F" + str(self.conf.zspeed)
            xyspeed = " F" + str(self.conf.xyspeed)
            travelspeed = " F" + str(self.conf.travelspeed)
            if np.abs(currentdirection[1])>1 or np.abs(currentdirection[0])>1:
                if not self.isup:
                    gcode += "G1 Z" + str(self.conf.safez) + zspeed + "\n" + "G1" + travelspeed + "\n"
                    self.isup = True
                #gcode += ";" + str(currentdirection[1])+', '+ str(currentdirection[0]) + "\n"
                return gcode



            if consecutivemove:
                currentmove = "G1 X" + self.gcode.getxfromindex(x) +" Y" + self.gcode.getyfromindex(y) + "\n"
                if not currentmove == self.lastmove:
                    gcode += currentmove
                    self.lastmove = currentmove
                if self.isup:
                    currentmove = "G1 Z0" + zspeed + "\n" + "G1" + xyspeed + "\n"
                    gcode += currentmove
                    self.lastmove = currentmove
                    self.isup = False
                currentmove = "G1 X" + self.gcode.getxfromindex(x+currentdirection[1],compensation=compensationx) +" Y" + self.gcode.getyfromindex(y+currentdirection[0],compensation=compensationy) +  "\n"
                if not currentmove == self.lastmove:
                    gcode += currentmove
                    self.lastmove = currentmove
            else:
                currentmove = "G1 X" + self.gcode.getxfromindex(x) +" Y" + self.gcode.getyfromindex(y) + "\n"
                if not currentmove == self.lastmove:
                    gcode += currentmove
                    self.lastmove = currentmove
                if self.isup:
                    currentmove = "G1 Z0" + zspeed + "\n" + "G1" + xyspeed + "\n"
                    gcode += currentmove
                    self.lastmove = currentmove
                    self.isup = False
                currentmove = "G1 X" + self.gcode.getxfromindex(x+currentdirection[1],compensation=compensationx) +" Y" + self.gcode.getyfromindex(y+currentdirection[0],compensation=compensationy)+ "\n"
                if not currentmove == self.lastmove:
                    gcode += currentmove
                    self.lastmove = currentmove
                if longtravel:
                    currentmove = "G1 Z" + str(self.conf.safez) + zspeed + "\n" + "G1" + travelspeed + "\n"
                else:
                    currentmove = "G1 Z" + str(self.conf.shorttravelz) + zspeed + "\n" + "G1" + travelspeed + "\n"
                self.lastmove = currentmove
                gcode += currentmove
                self.isup = True
            # print("--------------")
            # print("consecutivemove",consecutivemove)
            #print("x,y,order || nextx,nexty,nextorder || direction",x,y,order,"||",nextx,nexty,nextorder,"||",currentdirection,"squareddistance",squareddistance)
            #print("gcode",gcode)
            #self.completegcode += gcode
            return gcode

        vfunc = np.vectorize(gcode, otypes=[str])

        result = vfunc(gcodex,gcodey,np.roll(gcodex,-1),np.roll(gcodey,-1),gcodeorder,np.roll(gcodeorder,-1))
        #print(result)
        #print(result.shape)
        return ''.join(result)
        # #print(result_string)
        # with open(self.gcodefilepath, "w") as file:
        #     # Write the string to the file
        #     file.write(result_string)
        #
        # lines = result_string.split('\n')
        # first_500_lines = lines[:500]
        # final_string = '\n'.join(first_500_lines)
        # with open("hilbertcurve/test.gcode", "w") as file:
        #     # Write the string to the file
        #     file.write(final_string)
        #print(self.completegcode)

        # coordinatesvector =

    def generate_direction_vector(self):
        # # Example with a large tensor (e.g., 4000 x 4000)
        # H, W = 400, 400
        # matrix = torch.arange(H * W).reshape(H, W)

        # Flatten and get positions of each value
        print("Generating Direction Vector")
        flat_matrix = self.hilbertmatrixindex.flatten()
        positions = torch.stack(torch.meshgrid(torch.arange(self.hilbertmatrixindex.shape[0]), torch.arange(self.hilbertmatrixindex.shape[1]), indexing='ij'), dim=-1).reshape(-1, 2)

        # Use argsort to get the original value positions (i.e., where 0, 1, ..., n-1 are)
        sorted_positions = positions[flat_matrix.argsort()]

        # Compute deltas between consecutive elements
        self.hilbertdirectionvector = (sorted_positions[1:] - sorted_positions[:-1]).T  # shape (2, n-1)
        print("Direction Vector Generated")
        #print("deltas",deltas)
    # def generate_direction_vector(self):
    #     print(self.hilbertmatrixindex.shape)
    #     device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    #     print("Generating Direction vector")
    #     self.hilbertdirectionvector = torch.zeros((2,self.max)).to(device)
    #     self.hilbertmatrixindex = self.hilbertmatrixindex.to(device)
    #     for i in range(self.max):
    #         if i % 100 == 0:
    #             print(i,"/",self.max)
    #         x1,y1 = (self.hilbertmatrixindex == i).nonzero(as_tuple=True)
    #         x2, y2 = (self.hilbertmatrixindex == i+1).nonzero(as_tuple=True)
    #         #print(x1,y1,x2, y2)
    #         direction = ((x2-x1),(y2-y1))
    #         #print(direction)
    #         self.hilbertdirectionvector[0,i] = direction[0]
    #         self.hilbertdirectionvector[1, i] = direction[1]
    #     self.hilbertdirectionvector = self.hilbertdirectionvector.cpu()
    #     torch.save(self.hilbertdirectionvector, self.hilbertdirectionvectorfilename)

    def generate_indexmatrix(self):
        # print("self.rule",self.rule)
        xdir, ydir = 1, 0
        x, y = 0, 0
        count = 0
        for instruction in self.rule:
            # print(count)
            if instruction == "F":
                self.hilbertmatrixindex[x, y] = count
                x += xdir
                y += ydir
                # print("x,y", x, y)
                count += 1
                continue
            if instruction == "+":
                if xdir == 1 and ydir == 0:
                    xdir, ydir = 0, 1
                elif xdir == 0 and ydir == 1:
                    xdir, ydir = -1, 0
                elif xdir == -1 and ydir == 0:
                    xdir, ydir = 0, -1
                elif xdir == 0 and ydir == -1:
                    xdir, ydir = 1, 0
                continue
            if instruction == "-":
                if xdir == 1 and ydir == 0:
                    xdir, ydir = 0, -1
                elif xdir == 0 and ydir == -1:
                    xdir, ydir = -1, 0
                elif xdir == -1 and ydir == 0:
                    xdir, ydir = 0, 1
                elif xdir == 0 and ydir == 1:
                    xdir, ydir = 1, 0
        self.hilbertmatrixindex[self.d - 1, 0] = self.max
        torch.save(self.hilbertmatrixindex, self.hilbertmatrixfilename)

    def turtledraw(self):
        speed(0)
        count = 0
        for i in self.rule:
            if i == "F":
                forward(3)
                count += 1
                continue
            if i == "+":
                left(90)
                continue
            if i == "-":
                right(90)
                continue
            print("mauvais caracteres !!!")
            exit()

        # print("count", count)

    def generate_rule(self):
        A = "+BF-AFA-FB+"
        B = "-AF+BFB+FA-"
        Result = A
        for i in range(self.n):
            # print(Result)
            nextline = ""
            for j in range(len(Result)):
                if Result[j] == "A":
                    nextline += A
                    continue
                if Result[j] == "B":
                    nextline += B
                    continue
                nextline += Result[j]
            Result = nextline

        # print(Result)
        Result = Result.replace("A", "")
        Result = Result.replace("B", "")
        Result = Result.replace("+-", "")
        Result = Result.replace("-+", "")
        self.rule = Result

    def scrambleHilbertMatrix(self):
        randomscramblerange = (15,30)
        print(self.hilbertmatrixindex.shape)
        #print(self.hilbertdirectionvector.shape)
        originalhibertmatrixshape = self.hilbertmatrixindex.shape
        flattenedhilbertmatrixindex = torch.flatten(self.hilbertmatrixindex)
        print(flattenedhilbertmatrixindex)
        scramblingindex = self.generateScramblingindex(randomscramblerange,flattenedhilbertmatrixindex.shape[0])
        flattenedhilbertmatrixindex = flattenedhilbertmatrixindex[scramblingindex]
        print("flattenedhilbertmatrixindex.shape",flattenedhilbertmatrixindex.shape)
        flattenedhilbertmatrixindex = flattenedhilbertmatrixindex.reshape(originalhibertmatrixshape)
        print(flattenedhilbertmatrixindex)
        return flattenedhilbertmatrixindex

    def generateScramblingindex(self,randomrange,elementscount):
        print("elementscount",elementscount)
        minimumblocksize = 10000000
        block = torch.rand((minimumblocksize)) * (randomrange[1] - randomrange[0]) + randomrange[0]
        block = block.to(torch.int)
        cumulative_sum = torch.cumsum(block, dim=0)
        scrambledindex = cumulative_sum[cumulative_sum <= elementscount]
        if scrambledindex[-1] < elementscount -1:
            scrambledindex = torch.cat((scrambledindex,torch.tensor([elementscount - 1])))
        print("scrambledindex",scrambledindex,scrambledindex.shape)
        ranges = []
        lastrange = 0
        iseven = True
        scrambledindexranges = torch.tensor([],dtype=torch.int32)
        for i in scrambledindex:
            if iseven:
                scrambledindexranges = torch.cat((scrambledindexranges,torch.arange(lastrange,i+1)))
            else:
                scrambledindexranges = torch.cat((scrambledindexranges,torch.arange(i+1,lastrange-2,-1)))


            lastrange = i+2
            iseven = not iseven
        print(ranges)

        scrambledindexranges = scrambledindexranges[scrambledindexranges!=elementscount]
        scrambledindexranges = scrambledindexranges[scrambledindexranges != elementscount+1]
        print('sum',torch.sum(scrambledindexranges))
        if not torch.sum(scrambledindexranges) == ((elementscount-1)*elementscount)/2:
            raise Exception("scrambledindexranges should return all values for 0 to", elementscount-1)
        #torch.set_printoptions(profile='full')
        print("scrambledindexranges",scrambledindexranges)
        return scrambledindexranges

    def generateRandomHilbert(self):
        for i in range(100):
            filename = self.dir_path + "/rndhilbert_of_" + str(self.n) + "_random_" + str(i) + ".pt"
            print("Processing :", filename)
            self.hilbertmatrixindex = self.scrambleHilbertMatrix()
            torch.save(self.hilbertmatrixindex, filename)
            print("Saved :",filename)
            self.generate_direction_vector()
            filename = self.dir_path + "/rndhilbertdirection_of_" + str(self.n) + "_random_" + str(i) + ".pt"
            torch.save(self.hilbertdirectionvector, filename)
            print("Saved :", filename)
    def loadRandomHilbert(self):
        if self.hilbertmatrixfiles == []:
            hilbert_matrix_files = [f for f in os.listdir(self.dir_path) if
                              f.startswith("rndhilbert_of_" ) ]
            hilbert_matrix_files.sort()
            self.hilbertmatrixfiles = hilbert_matrix_files
            print(hilbert_matrix_files)
            hilbert_direction_files = [f for f in os.listdir(self.dir_path) if
                              f.startswith("rndhilbertdirection_of_" ) ]
            hilbert_direction_files.sort()
            self.hilbertdirectionfiles = hilbert_direction_files
            print(hilbert_direction_files)
        print(len(self.hilbertmatrixfiles) ,len(self.hilbertdirectionfiles))
        if not len(self.hilbertmatrixfiles) == len(self.hilbertdirectionfiles ):
            raise Exception("Hilbert matrix files and Hilbert direction files must be the same count.")
        random_index = random.randint(0,len(self.hilbertmatrixfiles))
        self.hilbertmatrixindex = torch.load(self.dir_path + "/" + self.hilbertmatrixfiles[random_index] , weights_only=True)
        self.hilbertdirectionvector = torch.load(self.dir_path + "/" + self.hilbertdirectionfiles[random_index] , weights_only=True)
        print(self.hilbertmatrixfiles[random_index]," and",self.hilbertdirectionfiles[random_index],"loaded.")
        self.hilbertmatrixfiles.remove(self.hilbertmatrixfiles[random_index])
        self.hilbertdirectionfiles.remove(self.hilbertdirectionfiles[random_index])
        #print(len(self.hilbertmatrixfiles), len(self.hilbertdirectionfiles))


conf = Configuration()
machine = Machine()
gcode = GcodeInterpreter(conf, machine)
#hilbertmatrix = HilbertMatrix(11,conf,gcode)
#hilbertmatrix.loadRandomHilbert()
# hilbertmatrix.generateRandomHilbert()
#
# hilbertmatrix.hilbertmatrixindex = hilbertmatrix.scrambleHilbertMatrix()
# #hilbertmatrix.generate_direction_vector_fast()
# hilbertmatrix.generate_direction_vector()
# print("slow",hilbertmatrix.hilbertdirectionvector)



# print(hilbertmatrix.hilbertmatrixindex)
# for i in range(100):
#     print("x,y",hilbertmatrix.hilbertdirectionvector[0,i].item(),hilbertmatrix.hilbertdirectionvector[1,i].item())
# print(hilbertmatrix.hilbertdirectionvector.shape)
# gcode = hilbertmatrix.generate_Hilbert_path(colortensor==1)

#started = time.time()
# Note 11 pour correspondre a la resolution actuelle 4096*4096
# hilbertmatrix = HilbertMatrix(11)
# hilbertmatrix.generate_Hilbert_path(fakeimage)
# torch.set_printoptions(linewidth=1000)
# print(hilbertmatrix.hilbertmatrixindex)
#fakeimage = torch.rand((3000, 2000)) >= 0.5
#fakeimage = torch.ones((3000, 2000),dtype=torch.bool)
# image = Image.open("C:/Users/carls/PycharmProjects/gcodefractal/src/matrixtogcode/images/fract727pen_4_purple.png")
# image = image.convert('RGB')
# # transform image into a pytorch tensor
# transform = transforms.Compose([transforms.PILToTensor()])
# fakeimage = transform(image)
# fakeimage = fakeimage[0,:,:] == 255
# print(fakeimage)
#
# hilbertmatrix.generate_Hilbert_path(fakeimage)
#print("Time for n = " + str(n) + " :", time.time() - started)
# hilbertmatrix.turtledraw()

# hilbertlsystem(13)

# input()
