import random
from collections import Counter

import torch

from src.matrixtogcode.PenColor import PenColor


class ColorInterpreter:
    def __init__(self,conf,randomcolormixseed=None):
        self.conf = conf
        self.randomcolormixseed = randomcolormixseed
        self.setPencolorlist()
        self.getPencolorMixlist()
    def setPencolorlist(self):

        self.pencolorlist = self.conf.pencolorlist
        self.pencolorscount = len(self.pencolorlist)
    def getPencolornamebyindex(self,index):
        return self.pencolorlist[index].colorname
    def getPencolorbyname(self,name):
        for i in self.pencolorlist:
            if name == i.colorname:
                return i
    def getPencolorMixlist(self):
        colorcount = len(self.pencolorlist)
        colorsmixlist = []
        colornames = []
        colorconstraints = torch.zeros(colorcount)
        i=0
        for acolor in self.pencolorlist:
            colornames.append(acolor.colorname)
            colorconstraints[i] = acolor.saturationconstraint
            i+=1
        for i in range(pow(2,colorcount)):
            mask = torch.zeros(colorcount)
            minconstraint = 100000
            colorsum = 0
            colorsselected = []
            for j in range(colorcount,0,-1):
                bit = i >> j-1 & 1
                if bit:
                    colorsselected.append(colornames[colorcount - j])
                    minconstraint = min(minconstraint, colorconstraints[colorcount - j].item() * bit)
                colorsum += bit


                #print(colorconstraints[colorcount - j])
                #print(bit,end="")

            #print("minconstraint=",minconstraint)
            #print("colorsum",colorsum)
            if colorsum <= minconstraint:
                #print(sorted(colorsselected))
                colorsmixlist.append(sorted(colorsselected))

        # Remove incompatible colors
        for color in colorsmixlist[:]:
            for incompatiblecolors in self.conf.noncompatiblepencolor:
                if incompatiblecolors[0] in color and incompatiblecolors[1] in color:
                    colorsmixlist.remove(color)
                    break
        print(colorsmixlist)
        print("Nbr de couleurs :",len(colorsmixlist))

        self.pencolormixlist = colorsmixlist
        ### To do : creer une methode qui trie les couleurs par rgb.

    def getColorslistfromimage(self,pilimage):

        image_data = list(pilimage.getdata())
        color_counts = Counter(image_data)
        self.imagecolorlist = list(color_counts.keys())
        print(len(self.imagecolorlist))
        self.imagecolorlist.sort(key=lambda x: x[2])
        self.imagecolorlist.sort(key=lambda x: x[1])
        self.imagecolorlist.sort(key=lambda x: x[0])
        self.imagecolorlist.sort(key=self.getluminance)
        print(self.imagecolorlist)
        self.imagecolorlist = self.randomshakecolors(self.imagecolorlist)
        self.associatepenandimagecolors()

    def randomshakecolors(self,imagecolorlist):

        if self.randomcolormixseed is None:
            return imagecolorlist
        torch.manual_seed(self.randomcolormixseed)
        #distributionfactorlist = torch.rand(numberofpen)
        slices = torch.randint(1,6,(1,))
        #slices = random.randint(1,6)
        for i in range(slices):
            #slicepoint = random.randint(0,len(imagecolorlist))
            slicepoint = torch.randint(0,len(imagecolorlist),(1,))
            imagecolorlist = imagecolorlist[slicepoint:len(imagecolorlist)] + imagecolorlist[0:slicepoint]
        print("imagecolorlist sliced randomly",imagecolorlist)
        return imagecolorlist

    def splitbypencolors(self,imagetensor):
        #print(imagetensor)
        #print(imagetensor.shape)
        returnimagecolorstensor = torch.zeros((len(self.pencolorlist),imagetensor.shape[1],imagetensor.shape[2]))
        colorindex=0
        for pencolor in self.pencolorlist:
            imagecolors = self.getpencolorcorrespondingimagecolors(pencolor.colorname)
            #print("imagecolors",imagecolors)
            #imagecolorstensor = torch.zeros([3,len(imagetensor)-1])
            imagecolorstensor = torch.zeros([1,imagetensor.shape[1],imagetensor.shape[2]])
            for i in range(len(imagecolors)):
                # Expand all image colors corresponding to a pen color
                imagetotensor = torch.unsqueeze(torch.tensor(imagecolors[i]),dim=1)

                imagetotensor = torch.unsqueeze(imagetotensor.expand(3,imagetensor.shape[1]),dim=2)
                imagetotensor = imagetotensor.expand(3, imagetensor.shape[1], imagetensor.shape[2])
                # Compare the input image with the current color
                comparisiontensor = torch.eq(imagetotensor,imagetensor)
                #print(i,comparisiontensor)
                # Only tensor with 3 True values along dim 0 are from the same color
                comparisiontensor = torch.sum(comparisiontensor, dim=0)
                #print("comparisiontensor",comparisiontensor)
                comparisiontensor = torch.where(comparisiontensor == 3, 1, 0)
                #print(comparisiontensor)
                imagecolorstensor += comparisiontensor
            #print("Color :",pencolor.colorname,imagecolorstensor)


            returnimagecolorstensor[colorindex,:,:] = imagecolorstensor

            colorindex += 1


        #imagecolorstensor = torch.where(imagecolorstensor >= 1, 1, 0 )

        #print(returnimagecolorstensor[i,:,:])

        return returnimagecolorstensor

    def associatepenandimagecolors(self):
        print("len imagecolorlist",len(self.imagecolorlist),"len pencolormixlist",len(self.pencolormixlist))
        #imageperdivision = len(self.imagecolorlist)/len(self.pencolormixlist)
        # if int(imageperdivision) - imageperdivision < 0:
        #     imageperdivision = int(imageperdivision) - 1
        #print("image colors per division",imageperdivision)
        # Establish each color range with appropriate distribution factor
        self.pencolormixdistributionrange = []

        for i in self.pencolormixlist:
            if i == []:
                self.pencolormixdistributionrange.append(self.conf.whitecolordistributionfactor)
                continue
            count=0
            value=0
            for j in i:
                value += self.getPencolorbyname(j).distributionfactor
                count+=1
            value = value / count
            self.pencolormixdistributionrange.append(value)
        self.pencolormixdistributionrange = torch.tensor(self.pencolormixdistributionrange)
        #print(self.pencolormixdistributionrange)
        #self.pencolormixdistributionrange = torch.softmax(self.pencolormixdistributionrange,dim=0)
        self.pencolormixdistributionrange = self.pencolormixdistributionrange / torch.sum(self.pencolormixdistributionrange)
        #print(self.pencolormixdistributionrange)
        lastvalue = 0
        for i in range(self.pencolormixdistributionrange.shape[0]):
            lastvalue += self.pencolormixdistributionrange[i]
            self.pencolormixdistributionrange[i] = lastvalue
        self.pencolormixdistributionrange = list(self.pencolormixdistributionrange)
        self.pencolormixdistributionrange = [i.item() for i in self.pencolormixdistributionrange]
        #print(self.pencolormixdistributionrange)
        self.colorscorrespondance = []

        pencolor = 0
        for i in range(len(self.imagecolorlist)):
            #pencolor = int(i / (len(self.imagecolorlist)) * len(self.pencolormixlist))
            currentprogress = i/len(self.imagecolorlist)
            #print(currentprogress)
            if currentprogress > min(self.pencolormixdistributionrange):
                pencolor += 1
                self.pencolormixdistributionrange.remove(min(self.pencolormixdistributionrange))

            #print("pencolor",pencolor)
            self.colorscorrespondance.append([self.imagecolorlist[i],self.pencolormixlist[pencolor]])
            #print([i,self.pencolormixlist[pencolor]])


        #print(self.colorscorrespondance)

        pencolorsmixcount = {}
        currentcolormix = []
        counter = 0
        for i in self.colorscorrespondance:

            if i[1] in self.pencolormixlist:
                if not str(i[1]) in pencolorsmixcount:
                    pencolorsmixcount[str(i[1])] = 0
                pencolorsmixcount[str(i[1])] += 1

        #print(pencolorsmixcount)


    def getpencolorcorrespondingimagecolors(self,pencolor):
        imagelist = []
        for i in self.colorscorrespondance:
            if pencolor in i[1]:
                imagelist.append(i[0])
        return imagelist

    def docolorcorrespond(self,imagecolor,pencolor):
        return [imagecolor,pencolor] in self.colorscorrespondance

    def getcolorsbychannel(self,channelindex):
        colors = []
        for i in range(len(self.channels)):
            if self.channels[i][channelindex] > 0 :
                colors.append(self.imagecolorlist[i])
        return colors

    def splitchannels(self):
        possiblecolors = pow(2,self.pencolorscount)

        self.channels = []
        colorstochannelsdict = {}
        currentcolor=0
        coloroffset = 0
        for i in range(len(self.imagecolorlist)):

            currentcolorindex = i-coloroffset
            #print(bin(currentcolorindex))
            channel = []
            for j in range(self.pencolorscount):
                digit = (currentcolorindex & (1 << j)) >> j
                channel.append(digit)
            self.channels.append(channel)
            currentcolor +=1
            if currentcolor >= possiblecolors:
                #print("looping colors")
                currentcolor = 0
                coloroffset += possiblecolors
        #print(self.channels)
        #print(len(self.channels))
        print("looped",coloroffset/possiblecolors,"times")

    def getluminance(self,color):
        luminance = (color[0] + color[1] + color[2])
        return luminance