import time

import numpy as np
import torch
from torch import optim


class ImageTravelOptimizer:
    def __init__(self,conf,stats):
        self.conf = conf
        self.stats = stats
        self.index = 0
        self.totaltensorarea = (self.conf.canvasresolution[0]*self.conf.canvasresolution[1])

        self.cutscount = conf.traveloptimizationcutscount
        self.max_epochs = conf.traveloptimizationmax_epoch
        self.initiatelearningratescheduler()
        self.cutstensor = torch.zeros((self.cutscount,2))
        self.cutstensorgrad = torch.zeros((self.cutscount, 2))
        self.costmatrix = torch.zeros((self.cutscount+1,self.cutscount+1))
        self.initiatecuts()

    def __iter__(self):
        print("blou")
        self.indexX,self.indexY = 0,0
        cutsindex = self.cutstensortoindex(self.cutstensor)
        paddedcutsindex = torch.zeros((cutsindex.shape[0] + 2, 2), dtype=torch.int)
        # print(paddedcutsindex)
        paddedcutsindex[1:-1, :] = cutsindex
        paddedcutsindex[-1, 0] = self.conf.canvasresolution[0]
        paddedcutsindex[-1, 1] = self.conf.canvasresolution[1]
        self.itercutsindex = paddedcutsindex
        print(self.itercutsindex)
        return self

    def __next__(self):
        if self.indexX > self.cutstensor.shape[0]:
            self.indexX = 0
            self.indexY +=1
        #print("xindex", self.indexX, "yindex", self.indexY)
        if self.indexY > self.cutstensor.shape[0]:
            raise StopIteration



        xrange = self.itercutsindex[self.indexX, 0].item(),self.itercutsindex[self.indexX+1, 0].item()
        yrange = self.itercutsindex[self.indexY, 1].item(), self.itercutsindex[self.indexY+1, 1].item()
        #print("xrange",xrange,"yrange",yrange)


        #currentcut = self.itercutsindex[x1,0].item(),self.itercutsindex[y1,1].item(),self.itercutsindex[x2,0].item(),self.itercutsindex[y2,1].item()
        #currentcut = ""
        currentcut = self.masktensor(self.currentchanneltensor,(xrange[0],yrange[0]),(xrange[1],yrange[1]))
        self.indexX += 1
        return currentcut


    def initiatecuts(self):
        #xysteps = (self.conf.canvasresolution[0]/(self.cutscount+1),self.conf.canvasresolution[1]/(self.cutscount+1))
        # xcuts = torch.linspace(xysteps[0],self.conf.canvasresolution[0]-xysteps[0],self.cutscount)
        # ycuts = torch.linspace(xysteps[1], self.conf.canvasresolution[1] - xysteps[1], self.cutscount)
        self.cutstensor[:,0] = torch.linspace(0, 1, self.cutscount+2)[1:-1]
        self.cutstensor[:, 1] = torch.linspace(0, 1, self.cutscount + 2)[1:-1]
        print(self.cutstensor)
        #print(ycuts)
        #self.xindex = torch.round(xcuts).to(torch.int)
        #self.yindex = torch.round(ycuts).to(torch.int)

    def cutstensortoindex(self,cutstensor):
        indextensor = torch.zeros_like(cutstensor,dtype=torch.int)
        indextensor[:,0] = torch.round(cutstensor[:,0] * self.conf.canvasresolution[0]).to(torch.int)
        indextensor[:, 1] = torch.round(cutstensor[:, 1] * self.conf.canvasresolution[1]).to(torch.int)
        return indextensor

    def masktensor(self,tensortomask,startxy,endxy):
        binarymask = torch.zeros_like(tensortomask)
        binarymask[startxy[0]:endxy[0],startxy[1]:endxy[1]] = 1
        print("binarymask",startxy[0],endxy[0],startxy[1],endxy[1])
        return tensortomask * binarymask
    def processcostmatrix(self,cutstensor):
        self.cutstensor = torch.where(self.cutstensor < 0, 0., self.cutstensor)
        self.cutstensor = torch.where(self.cutstensor > 1, 1., self.cutstensor)
        cutsindex = self.cutstensortoindex(cutstensor)
        #print(cutsindex)
        paddedcutsindex = torch.zeros((cutsindex.shape[0]+2,2),dtype=torch.int)
        #print(paddedcutsindex)
        paddedcutsindex[1:-1,:] = cutsindex
        paddedcutsindex[-1,0] = self.conf.canvasresolution[0]
        paddedcutsindex[-1, 1] = self.conf.canvasresolution[1]
        #print(paddedcutsindex)
        totaltravel = 0
        costmatrix = torch.zeros_like(self.costmatrix)
        for i in range(self.costmatrix.shape[0]):
            for j in range(self.costmatrix.shape[0]):
                startx, starty, endx, endy = paddedcutsindex[i,0].item(),  paddedcutsindex[j,1].item(),  paddedcutsindex[i+1,0].item(),  paddedcutsindex[j+1,1].item()
                currentslice = self.currentchanneltensor[startx:endx,starty:endy]
                cost = self.estimatetraveldistance(currentslice)
                costmatrix[i, j] = cost
                totaltravel += cost
                #print(currentslice.shape)
        #print("costmatrix",costmatrix)
        #print("proximitypenalitycost",self.proximitypenalitycost(cutstensor))

        #print(costmatrix)
        return costmatrix,totaltravel

    def proximitypenalitycost(self,cutstensor):
        paddedcuts = torch.zeros((cutstensor.shape[0]+2,2))
        paddedcuts[1:-1, :] = cutstensor
        paddedcuts[-1,:] = 1
        cutaverage = 1 / (self.cutscount+1)
        proximitymatrix = torch.zeros_like(self.costmatrix)
        for i in range(self.cutscount):
            proximitymatrix[i,:] = pow(abs(cutaverage-(paddedcuts[i+1,0] - paddedcuts[i,0]))*cutaverage,2)
            proximitymatrix[:,i] = pow(abs(cutaverage-(paddedcuts[i+1,1] - paddedcuts[i,1]))*cutaverage,2)
        return proximitymatrix

    def optimizecuts(self, channeltensor):
        starttime = int(round(time.time() * 1000))
        #optimizer = optim.Adam(self.cutscount, lr=0.0001)
        unsplittedimagedistance = self.estimatetraveldistance(channeltensor)
        print("Total distance of unsplitted image",unsplittedimagedistance)
        self.currentchanneltensor = channeltensor
        self.shift = -0.01
        bestcost = 10000000000000
        for self.epoch in range(self.max_epochs):
            print("epoch",self.epoch)
            print("initial cut tensors",self.cutstensor)

            currentcostmatrix,totaltravel = self.processcostmatrix(self.cutstensor)
            currentpenalitymatrix = self.proximitypenalitycost(self.cutstensor)
            travelcost,proximitycost = torch.sum(currentcostmatrix),torch.sum(currentpenalitymatrix)
            cost = travelcost + proximitycost
            print("travelcost" ,"proximitycost","cost",travelcost ,proximitycost,cost)
            if cost < bestcost and self.epoch > 10:
                bestcostepoch = self.epoch
                bestcost = cost
                besttravel = totaltravel
                bestcuts = self.cutstensor.clone()
                bestcostmatrix = currentcostmatrix
                bestpenalitymatrix = currentpenalitymatrix
            print("Total travel for actual cost matrix =", totaltravel)
            print("Total cost",cost)
            if self.epoch == 0 :
                self.distancebeforeoptimization = totaltravel
                startcostmatrix = currentcostmatrix
                if totaltravel==0:
                    print("Blank image, skipping")
                    return
            #print("currentcostmatrix",currentcostmatrix)
            self.shift = torch.rand((1)).item() * .1 - .05
            #self.shift = - self.shift

            shiftedcutstensor = self.cutstensor + self.shift
            shiftedcostmatrix,_ = self.processcostmatrix(shiftedcutstensor)
            shiftedpenalitymatrix = self.proximitypenalitycost(shiftedcutstensor)
            #print("shiftedcostmatrix",shiftedcostmatrix)
            #costdifferencematrix = (currentcostmatrix - shiftedcostmatrix)/()
            #print("costdifferencematrix",costdifferencematrix)
            #min,max = torch.min(costdifferencematrix),torch.max(costdifferencematrix)
            #divider = torch.max(torch.tensor([torch.abs(min),torch.abs(max)]))
            #print("min",min,"max",max,"divider",divider)
            #normalizedcostdifferencematrix = costdifferencematrix / divider
            #print("normalizedcostdifferencematrix",normalizedcostdifferencematrix)
            self.processgradients(currentcostmatrix+currentpenalitymatrix,shiftedcostmatrix+shiftedpenalitymatrix)
            self.applygradients()
            #self.dropout()
            self.orderandtrimcutstensor()
        print("Unsplitted image distance",unsplittedimagedistance)
        print("Travel before optimization",self.distancebeforeoptimization)
        self.stats.printandsave("Color = ",self.currentcolor)
        self.stats.printandsave("startcostmatrix",startcostmatrix)
        self.stats.printandsave("bestcostmatrix",bestcostmatrix)
        self.stats.printandsave("bestpenalitymatrix",bestpenalitymatrix)
        self.stats.printandsave("bestcostepoch",bestcostepoch,"/",self.max_epochs)
        self.stats.printandsave("besttravel",besttravel,"multiplied by area =",besttravel*self.totaltensorarea)
        self.stats.printandsave("bestcuts",bestcuts)
        self.stats.printandsave("bestcost",bestcost)
        self.cutstensor = bestcuts
        print("timeelapsed",int(round(time.time() * 1000))-starttime, "ms")

        #self.determinategradientsinglecut(2, "x")
    def dropout(self):
        if torch.rand((1))>0.8:
            index = torch.randint(0,self.cutscount,(1,)).item()
            axis = torch.randint(0,1,(1,)).item()
            self.cutstensor[index,axis] = torch.rand((1)).item()
            print("Dropped index",index,"axis",axis,"to",self.cutstensor[index,axis])

    def orderandtrimcutstensor(self):
        self.cutstensor = torch.where(self.cutstensor < 0 ,0., self.cutstensor)
        self.cutstensor = torch.where(self.cutstensor > 1, 1., self.cutstensor)
        self.cutstensor = torch.sort(self.cutstensor,dim = 0)[0]
        #print("orderedcutstensor",orderedcutstensor)
    def processgradients(self,currentcostmatrix,shiftedcostmatrix):
        for i in range(self.cutstensor.shape[0]):
            #print(costmatrix[:,i])
            xgrad = (torch.sum(currentcostmatrix[:,i]) + torch.sum(currentcostmatrix[:,i+1]) - torch.sum(shiftedcostmatrix[:,i]) - torch.sum(shiftedcostmatrix[:,i+1])) / (-self.shift)
            ygrad = (torch.sum(currentcostmatrix[i]) + torch.sum(currentcostmatrix[i+1]) - torch.sum(shiftedcostmatrix[i]) - torch.sum(shiftedcostmatrix[i+1])) / (-self.shift)

            #ygrad = (torch.sum(costmatrix[i])-torch.sum(costmatrix[i+1]))/self.cutstensor.shape[0]
            #xgrad = (torch.sum(costmatrix[i])-torch.sum(costmatrix[i+1]))/self.cutstensor.shape[0]
            #ygrad = (torch.sum(costmatrix[:,i]) - torch.sum(costmatrix[:,i + 1]))/self.cutstensor.shape[0]
            #print(xgrad,ygrad)
            self.cutstensorgrad[i,0],self.cutstensorgrad[i,1] = xgrad,ygrad
        #self.cutstensorgrad *= -self.shift
        print("cutstensorgrad",self.cutstensorgrad)
        #print(torch.sum(torch.abs(self.cutstensorgrad)))
            #print(torch.sum(costmatrix[i], dim=1) / torch.sum(costmatrix[i + 1], dim=1))
    def applygradients(self):
        #print("self.cutstensorgrad",self.cutstensorgrad)
        # min,max = torch.min(self.cutstensorgrad),torch.max(self.cutstensorgrad)
        # divider = torch.max(torch.tensor([torch.abs(min),torch.abs(max)]))
        # if torch.abs(min) > torch.abs(max):
        #     sign = -1
        # else:
        #     sign = 1
        #divider *= sign
        #print("min",min,"max",max,"divider",divider)

        #self.cutstensorgrad = self.cutstensorgrad / divider
        #print("self.cutstensorgrad normalized", self.cutstensorgrad)
        lr = 0.02
        #lr = .004 / self.distancebeforeoptimization
        #lr = self.lr[self.epoch] / self.distancebeforeoptimization
        print("lr",lr)
        print("cutstensorgradwithLRabsolutemean",torch.mean(torch.abs(self.cutstensorgrad*lr)))
        #print("cutstensorgradwithLR",self.cutstensorgrad*lr)
        self.cutstensor -= self.cutstensorgrad * lr
    def initiatelearningratescheduler(self):
        # Parameters
        initial_lr = 0.03
        decay_rate = initial_lr / 20


        # Generate learning rate schedule
        self.lr = [
            initial_lr * np.exp(-decay_rate * epoch)
            for epoch in range(self.max_epochs)
        ]
        print("Learning Rate",self.lr)
    def getgridcellcutindex(self,gridcellsindex):
        # if gridcellsindex[0] < 0 or gridcellsindex[1] < 0 or gridcellsindex[0] >= self.cutscount[0] or gridcellsindex[1] >= self.cutscount[1]:
        #     print("Grid cells index start at zero and end at " + str(self.cutscount[0]-1) + " for x and " + str(self.cutscount[1]-1) + " for y")
        #     raise NameError('outoffboundexception')
        xvalue,yvalue = -1,-1
        if gridcellsindex[0] < 0:
            xvalue = 0
        if gridcellsindex[1] < 0:
            yvalue = 0

        if gridcellsindex[0] >= self.cutscount[0] :
            xvalue = self.conf.canvasresolution[0]-1
        if gridcellsindex[1] >= self.cutscount[1] :
            yvalue = self.conf.canvasresolution[1]-1

        if xvalue == -1:
            xvalue = self.xindex[gridcellsindex[0]].item()
        if yvalue == -1:
            yvalue = self.yindex[gridcellsindex[1]].item()
        return (xvalue , yvalue)

    def estimatecutstraveldistance(self):
        lastx,lasty = 0, 0
        cutindexx = list(self.xindex)
        cutindexx.append(torch.tensor(self.conf.canvasresolution[0]))
        slicelist = []
        for x in cutindexx:
            print("x", lastx, "to", x.item() - 1)
            for y in self.yindex:
                slicelist.append([(lastx,x.item() - 1),(lasty,y.item() - 1)])
                print("y", lasty, "to", y.item() - 1)
                lasty = y.item()
            slicelist.append([(lastx, x.item() - 1), (lasty, self.conf.canvasresolution[1] - 1)])
            print("y", lasty, "to", self.conf.canvasresolution[1] - 1)

            lastx = x.item()
            lasty = 0
        print(slicelist)
        #print("x", lastx, "to", self.conf.canvasresolution[0]-1)
    def estimatetraveldistance(self,tensor):
        travelalong = 0
        tensor = tensor.clone()
        #print(tensor.shape)
        torch.where(tensor>0,1,0)

        if tensor.numel() == 0 :
            return 0

        _,maximumsfromstart = torch.max(tensor,dim=travelalong)
        _, maximumsfromend = torch.max(torch.flip(tensor,[travelalong]), dim=travelalong)
        distances = torch.abs(maximumsfromend-maximumsfromstart)
        totaldistance = torch.sum(distances)
        totaldistance = totaldistance / (self.conf.canvasresolution[0]*self.conf.canvasresolution[1])
        # print(tensor)
        # print(maximumsfromstart)
        # print(maximumsfromend)
        # print(distances)
        # print(totaldistance)
        return totaldistance.item()
