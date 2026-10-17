import os
import random
import time
from collections import Counter
from datetime import timedelta

import PIL.ImageQt
import numpy as np
import torch
import subprocess
from PIL.Image import Resampling

from src.matrixtogcode.ColorInterpreter import ColorInterpreter
from src.matrixtogcode.Configuration import Configuration
from src.matrixtogcode.GcodeInterpreter import GcodeInterpreter
from PIL import Image
import torchvision.transforms as transforms
import torchvision.transforms.functional as F

from src.matrixtogcode.ImageTravelOptimizer import ImageTravelOptimizer
from src.matrixtogcode.LineTravelOptimizer import LineTravelOptimizer
from src.matrixtogcode.Machine import Machine
from src.matrixtogcode.PenColorChartTest import PenColorChartTest
from src.matrixtogcode.RecordStatistics import RecordStatistics
#from src.matrixtogcode.hilbertcurve.Hilbert import HilbertMatrix


class MatrixtoGcode:
    def __init__(self):
        self.starttime = time.time()
        self.conf = Configuration()
        self.colors = ColorInterpreter(self.conf)
        self.machine = Machine()
        self.gcode = GcodeInterpreter(self.conf, self.machine)
        self.stats = RecordStatistics(self.colors)
        self.linetraveloptimizer = LineTravelOptimizer(self.conf)
        #self.hilbertmatrix = HilbertMatrix(11, self.conf, self.gcode)
        if self.conf.pencolorcharttest :
            self.pencolorcharttest = PenColorChartTest()
        #self.traveloptimizer = ImageTravelOptimizer(self.conf,self.stats)

        #self.traveloptimizer.estimatecutstraveldistance()

        # colornuance1,colornuance2 = self.get_color_nuances()
        # print(colornuance1)
        # print(colornuance2)

        #
        # for i in range(25):
        #     print(format(colornuance1[i], f'0{8}b'))
        #     for j in range(3):
        #         print(bin(colornuance2[i][j]),sep="")
        #     print("")
        # print(256/3)
        # exit()
        # for i in range(0,1000):
        #     print(self.gcode.cubicregression(i/1000))
        # exit()

    def run(self):
        if self.conf.pencolorcharttest:
            # Generate a color calibration test
            self.imagetensor = self.pencolorcharttest.generateAllmixtensor()
        else:
            # Normal program course
            self.importimage()

        if self.conf.generatepreviews :
            # Save every pen channel to an image
            self.saveindividualchannels(self.imagetensor)
            # Generate a preview from color calibration test data
            self.generatepreview()

        if self.conf.generatemultiplerandompreviews >= 0:
            #randomstate = random.getstate()
            #print("randomstate",randomstate)

            for previewseed in range(self.conf.generatemultiplerandompreviews):

                self.conf.setcolorlist(randomdistributionfactorseed=previewseed)
                # Recalculate colors

                if self.conf.generatemultiplerandompreviewsandmixcolors:
                    self.colors = ColorInterpreter(self.conf, previewseed)
                else:
                    self.colors = ColorInterpreter(self.conf)
                self.importimage()
                self.generatepreview(suffix="seed_"+str(previewseed))




        if not self.conf.testmode:
            continuerun = input("Continue ? (Y,n)")
            if continuerun.lower() == "n":
                exit()
        if self.conf.generatemultiplerandompreviews >= 0:
            chooseseed = input("Select a seed")
            chooseseed = int(chooseseed)

            #random.setstate(randomstate)
            self.conf.setcolorlist(randomdistributionfactorseed=chooseseed)
            # Recalculate colors
            if self.conf.generatemultiplerandompreviewsandmixcolors:
                self.colors = ColorInterpreter(self.conf, chooseseed)
            else:
                self.colors = ColorInterpreter(self.conf)
            self.importimage()
            self.generatepreview(suffix="Selectedseed_" + str(chooseseed))

        self.stats.getImageTensorStats(self.imagetensor)
        self.drawimage()
        self.gcode.endroutine()
        endtime = abs(self.starttime - time.time())
        print("Time elapsed ('hh:mm:ss') ", time.strftime("%Hh%Mm%Ss", time.gmtime(endtime))   )

    def importimage(self):
        # import image and resize it
        image = Image.open(self.conf.inputimagepath)
        image = image.resize(self.conf.canvasresolution,resample=Resampling.NEAREST)
        image = image.convert('RGB')

        image.save(self.conf.inputimagepath[:-4] + "resized.png")
        self.colors.getColorslistfromimage(image)

        # transform image into a pytorch tensor
        transform = transforms.Compose([transforms.PILToTensor()])
        tensor = transform(image)
        tensor = torch.transpose(tensor,1,2)
        tensor = self.colors.splitbypencolors(tensor)




        # if self.conf.channelnumber == 6:
        #     tensor = self.splitchannels(tensor)


        if torch.max(tensor) > 1:
            print("Normalizing")
            tensor = tensor.type(torch.float) / 255

        tensor = torch.where(tensor < self.conf.donotdrawbelow, torch.tensor(0.0), tensor)
        self.imagetensor = tensor
        print(tensor.shape)



    def generatepreview(self,suffix=""):

        self.imagetensor = self.imagetensor.to(torch.bool)
        previewimagetensor = torch.zeros((3,self.imagetensor.shape[1],self.imagetensor.shape[2]))
        for acolormix in self.conf.colorlistmix:
            colormixbinary = torch.reshape(acolormix.binary,(acolormix.binary.shape[0],1,1))
            colormixbinary = colormixbinary.expand(-1,self.imagetensor.shape[1],self.imagetensor.shape[2])

            currentselectedcolor = torch.sum(torch.bitwise_xor(self.imagetensor,colormixbinary),dim=0)==0
            currentselectedcolor =  torch.unsqueeze(currentselectedcolor,dim=0).expand(3,-1,-1)

            currentmixcolor = torch.tensor(acolormix.rgb).resize(3,1,1).expand(-1,self.imagetensor.shape[1],self.imagetensor.shape[2])
            #print("currentmixcolor",currentmixcolor)
            #print(currentselectedcolor*currentmixcolor)
            previewimagetensor += currentselectedcolor*currentmixcolor
            #test += torch.sum(torch.bitwise_xor(self.imagetensor,colormixbinary),dim=0)==0

        pilimage = F.to_pil_image(previewimagetensor/255,mode="RGB")
        pilimage = pilimage.transpose(method=Image.Transpose.ROTATE_180)
        #pilimage = pilimage.transpose(method=Image.Transpose.FLIP_TOP_BOTTOM)
        # colornames = self.conf.getcolorname(tensor.shape[0] == 6)
        directory = self.conf.outputbasedirectory + "/"+ self.conf.inputimagepath.split("/")[-1][:-4]
        if not os.path.exists(directory):
            os.makedirs(directory)
        pilimage.save(directory + "/" + "preview"+suffix+".png")




    def saveindividualchannels(self, tensor):
        #print(tensor.shape)

        directory = self.conf.outputbasedirectory + "/" + self.conf.inputimagepath.split("/")[-1][:-4]
        if not os.path.exists(directory):
            os.makedirs(directory)

        transformimage = False
        tensor = tensor.detach().clone()
        for i in range(tensor.shape[0]):
            colorslice = tensor[i,:,:]

            # if tensor.shape[0] == 6:
            #     colorused = i // 2
            # else :
            #     colorused = i

            #print("colorslice",colorslice)
            image = torch.zeros((3,tensor.shape[1],tensor.shape[2]))
            image[:,:,:] = colorslice
            #print("colorsliceimage", image)

            pilimage = F.to_pil_image(image)
            if transformimage:
                pilimage = pilimage.transpose(method=Image.Transpose.ROTATE_270)
                pilimage = pilimage.transpose(method=Image.Transpose.FLIP_TOP_BOTTOM)
            #colornames = self.conf.getcolorname(tensor.shape[0] == 6)

            pilimage.save(directory + "/" + "pen_" + str(i) + "_" + self.colors.getPencolornamebyindex(i) + ".png")

        # White spaces
        tensor = torch.sum(tensor,dim=0)
        image = torch.where(tensor >= 1,0.0,1.0)


        pilimage = F.to_pil_image(image)
        if transformimage :
            pilimage = pilimage.transpose(method=Image.Transpose.ROTATE_270)
            pilimage = pilimage.transpose(method=Image.Transpose.FLIP_TOP_BOTTOM)
        # colornames = self.conf.getcolorname(tensor.shape[0] == 6)

        pilimage.save(directory + "/" + "pen_white.png")


    def drawimage(self):
        numdim = self.imagetensor.shape[0]
        #colornames = self.conf.getcolorname(self.imagetensor.shape[0] == numdim)

        currentcolorchannel = 0
        for i in range(numdim):


            self.currentcolor = self.colors.getPencolornamebyindex(i)
            self.machine.currentcolorchannel = currentcolorchannel
            # if self.colors.getPencolornamebyindex(i) in self.conf.skipcolorlist:
            #     print(colornames[i],"skipped")
            #     continue
            currentcolorchannel += 1
            print("Processing", self.currentcolor)
            self.gcode.comment("Processing " + self.currentcolor)

            self.gcode.displayonscreen(self.currentcolor + " " + self.stats.getMeanbyColorName(self.currentcolor))
            self.gcode.changetool()
            colortensor = self.imagetensor[i, :, :]
            self.drawsinglecolor(colortensor)
            #exit()

    def drawsinglecolor(self, colortensor):
        #print("colortensor.shape",colortensor.shape)
        if torch.sum(colortensor) == 0:
            print("Empty image tensor")
            return


        if self.conf.resolutionmethod == "random_lines":
            filedirectory = self.conf.common_dir
            rustprogramdirectory = os.path.dirname(__file__) + "/../rust/matrix_to_gcode/target/release/"
            print(filedirectory)
            print(colortensor)
            np.save(filedirectory + "array.npy", colortensor.numpy())
            result = subprocess.run([rustprogramdirectory + "matrix_to_gcode",self.conf.common_dir], capture_output=True, text=True) #/home/carl/PycharmProjects/gcodefractal/src/common
            #time.sleep(10)
            if result.returncode != 0:
                print("Rust program failed with error:")
                print("Exit code:", result.returncode)
                print("Stderr:", result.stderr)
            else:
                print("Rust program succeeded:")
                #print("Stdout:", result.stdout)
            with open(filedirectory+"topython.gcode", 'r') as file:
                file_content = file.read()
            self.gcode.safe_single_color_file(file_content,self.currentcolor)
            self.gcode.addpreprocessedgcode(file_content)

        elif self.conf.resolutionmethod == "hilbert":
            # Load a random hilbert matrix with his direction vector.
            # The matrix are precomputed and loaded from drive.
            self.hilbertmatrix.loadRandomHilbert()
            print(colortensor)
            gcode = self.hilbertmatrix.generate_Hilbert_path(colortensor==1)
            gcode = self.gcode.addpencilrefillifneeded(gcode)
            self.gcode.addpreprocessedgcode(gcode)



        elif self.conf.resolutionmethod == "splittedlines":
            linetensor = self.linetraveloptimizer.optimizetensor(colortensor)
            self.drawlines(linetensor)
        else:
            print(self.conf.resolutionmethod,"is not an accepted method. Please use hilbert or splittedlines.")
            exit()
        # if self.currentcolor == 'lightblue':
        #     exit()

            # print(torch.sum(singlecutmask))

    def drawlines(self, linetensor):

        position = (100000000,100000000)
        for linetensorindex in range(linetensor.shape[0]):
            smallline = linetensor[linetensorindex,0],linetensor[linetensorindex,1]
            lineindex = linetensor[linetensorindex,2]
            direction = (smallline[0]-smallline[1])*self.conf.xyresolution[0]
            #print(direction)
            shorttravel = pow(position[0]-smallline[0]*self.conf.xyresolution[0],2)+pow(position[1]-lineindex*self.conf.xyresolution[1],2) < pow(self.conf.shorttravelmaxdistance,2)
            adjacenttravel = abs(position[0]-smallline[0]*self.conf.xyresolution[0]) <= self.conf.xyresolution[0] and abs(position[1]-lineindex*self.conf.xyresolution[1]) <= self.conf.xyresolution[1]
            #print(smallline[0]*self.conf.xyresolution[0],smallline[1]*self.conf.xyresolution[0])
            #print(shorttravel)
            self.gcode.drawline(lineindex, smallline,shorttravel,adjacenttravel)
            position = (smallline[1]*self.conf.xyresolution[0],lineindex*self.conf.xyresolution[1])
            #self.gcode.drawpixel((lineindex, i), aline[i].item())
            if self.conf.maxdistancebeforewipe < self.machine.travelsincelastwipe and not self.conf.maxdistancebeforewipe == -1:
                self.gcode.wipe()
            self.gcode.displayprogress(linetensorindex,linetensor.shape[0])

    def linetorange(self,line,flipped=False):
        rangelist = []
        lasti= -1
        firstoneindex = 0
        index = -1
        for i in line:
            index += 1
            if not i == lasti:
                if i == 0 and not lasti == -1:
                    rangelist.append([firstoneindex,index])
                else:
                    firstoneindex = index

            lasti = i
        if lasti == 1:
            rangelist.append([firstoneindex, index + 1])

        if flipped:
            arange = range(len(rangelist)-1,-1,-1)
            #print(rangelist)
            rangelist = [[rangelist[i][1],rangelist[i][0]] for i in arange]
            #print(rangelist)

        return rangelist

    def get_color_nuances(self):
        # Open the image
        image = Image.open(self.conf.inputimagepath)

        # Get the image data
        image_data = list(image.getdata())

        # Use Counter to count occurrences of each color
        color_counts = Counter(image_data)

        # Extract unique color values from the Counter keys
        color_nuances_list = list(color_counts.keys())

        image = image.convert('RGB')
        # Get the image data
        image_data = list(image.getdata())

        # Use Counter to count occurrences of each color
        color_counts2 = Counter(image_data)

        # Extract unique color values from the Counter keys
        color_nuances_list2 = list(color_counts2.keys())

        return color_nuances_list, color_nuances_list2

    def splitchannels(self, tensor):
        #deprecated
        # 1 + 2 + 4 + 8 = 15, 16 + 32 + 64 + 128 = 240
        # 128 + 32 + 8 + 2 = 170, 64 + 16 + 4 + 1 = 85
        lowervalues = torch.bitwise_and(tensor, 85) / 85
        highervalues = torch.bitwise_and(tensor, 170) / 170
        # print(tensor)
        # print(lowervalues)
        # print(highervalues)
        tensor = torch.zeros((6, tensor.shape[1], tensor.shape[2]))
        # Inverser les valeurs pour avoir ce schéma :
        #  Rp Gd Bp Rd Gp Bd
        # Schéma classique : Rp,Rd,Gp,Gd,Bp,Bd
        tensor[0, :, :] = lowervalues[0, :, :] # 0Rp
        tensor[4, :, :] = lowervalues[1, :, :] # Gp
        tensor[2, :, :] = lowervalues[2, :, :] # Bp
        tensor[3, :, :] = highervalues[0, :, :] # Rd
        tensor[1, :, :] = highervalues[1, :, :] # Gd
        tensor[5, :, :] = highervalues[2, :, :] # Bd
        return tensor

matrixtogcode = MatrixtoGcode()
matrixtogcode.run()
