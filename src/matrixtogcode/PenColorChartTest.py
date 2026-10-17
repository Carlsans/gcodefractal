import os

import torch

from src.matrixtogcode.Configuration import Configuration


class PenColorChartTest:
    def __init__(self):
        self.conf = Configuration()
        self.pencolorlist = [i.colorname for i in self.conf.pencolorlist]

    def generateAllmixtensor(self,generateonlycolormixlist = False):
        xyoffset = int(50 /self.conf.xyresolution[0]), int(50 /self.conf.xyresolution[1])
        print(self.pencolorlist)
        self.nbrcolor = len(self.pencolorlist)
        nbrmix = pow(2,self.nbrcolor)
        print("self.nbrcolor",self.nbrcolor,"nbrmix",nbrmix)
        colormixbynbrcolor = {}
        for i in range(1,self.nbrcolor+1):
            colormixbynbrcolor[i] = []
        print(colormixbynbrcolor)

        for i in range(1,nbrmix):
            binstringformat = "{:0"+str(self.nbrcolor)+"b}"
            formatedbinary = binstringformat.format(i)
            colorcountinmix = 0
            for j in formatedbinary:
                if j == "1":
                    colorcountinmix+=1
            colormixbynbrcolor[colorcountinmix].append(formatedbinary)
            #print("formatedbinary",formatedbinary,"colorcountinmix",colorcountinmix)
        print(colormixbynbrcolor)

        if generateonlycolormixlist:
            colormixliststring = ""
            for i in range(1,self.nbrcolor+1):
                for j in colormixbynbrcolor[i]:
                    #print(j)
                    kn=0
                    colorlistforthixmix = ""
                    for k in j:
                        if k == "1":
                            colorlistforthixmix += "'" + self.pencolorlist[kn] + "',"
                            #print(self.pencolorlist[kn])
                        kn+=1
                    print("PenColorMix(["+colorlistforthixmix[0:-1]+"], \"\", \""+j+ "\"),")
            exit()
        totalwidth = 0
        maxheight = 0
        finaltensor = torch.zeros((self.nbrcolor,self.conf.canvasresolution[0],self.conf.canvasresolution[1]),dtype=torch.bool)

        for i in range(1,self.nbrcolor+1):
            print("Nbrcolor",i,len(colormixbynbrcolor[i]))
            totalheight = 0
            for j in colormixbynbrcolor[i]:
                print("j",j)
                singlemixtensor, thiscellwidth,thiscellheight =self.generateSinglemixtensor(j)
                startx,endx = totalwidth + xyoffset[0],totalwidth + thiscellwidth-1 + xyoffset[0]
                print("startx,endx",startx,endx)
                starty,endy = totalheight + xyoffset[1], totalheight + thiscellheight - 1+xyoffset[1]
                print("starty,endy",starty,endy)
                finaltensor[:,startx:endx,starty:endy] = singlemixtensor
                totalheight += thiscellheight
            if maxheight < totalheight:
                maxheight = totalheight
            print("thiscellwidth ,totalheight",thiscellwidth ,totalheight)
            totalwidth += thiscellwidth

        print("totalwidth",totalwidth,"maxheight",maxheight)
        return finaltensor
    def generateSinglemixtensor(self,colormix):
        colorlinewidth = int(2 /self.conf.xyresolution[0])
        colorlinetomixwhitespace = int(3 /self.conf.xyresolution[0])
        colorlineheight = int(10 /self.conf.xyresolution[1])
        colormixsquare = (int(10 /self.conf.xyresolution[0]),int(10 /self.conf.xyresolution[1]))
        print("colorlinewidth",colorlinewidth,"colorlineheight",colorlineheight,"colorlinetomixwhitespace",colorlinetomixwhitespace,"colormixsquare",colormixsquare)
        colorcountinmix = 0
        for i in colormix:
            if i == "1":
                colorcountinmix += 1
        totalwidth = colorcountinmix * colorlinewidth + colormixsquare[0] + colorlinetomixwhitespace
        totalheight = colormixsquare[1]
        colormixtensor = torch.zeros((self.nbrcolor,totalwidth-1,totalheight-1),dtype=torch.bool)
        print(colormixtensor.shape)

        n=0
        colorcount=0
        for i in colormix:
            if i == "1":
                # Draw color guides
                xstart,xend = colorcount * colorlinewidth, colorcount * colorlinewidth + colorlinewidth - 1
                #print("Draw color guides n,xstart,xend",n,xstart,xend)
                colormixtensor[n,xstart:xend,:] = 1
                # Draw mix
                xstart, xend = colorcountinmix * colorlinewidth + colorlinetomixwhitespace, totalwidth - 1
                #print("Draw mix n,xstart,xend", n, xstart, xend)
                colormixtensor[n, xstart:xend, :] = 1
                colorcount+=1
            n+=1

        # torch.set_printoptions(profile="full")
        # print("colormixtensor",colormixtensor*1)
        # torch.set_printoptions(profile="default")
        print("totalwidth",totalwidth,"totalheight",totalheight)
        return colormixtensor, totalwidth, totalheight

# penttest = PenColorChartTest()
# print(penttest.generateAllmixtensor())