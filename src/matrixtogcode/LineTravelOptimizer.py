import math

import torch


class LineTravelOptimizer:
    def __init__(self, conf):
        self.conf = conf

    def optimizetensor(self, tensor):
        tensor = tensor.clone().detach().to(torch.bool)
        print(tensor.shape)
        linetensor = torch.tensor([], dtype=torch.int16)
        # maximumindexs = torch.zeros((1,tensor.shape[1]))
        maximumindexs = torch.tensor([], dtype=torch.int16)
        outputtensor = torch.zeros((1, 2, 2))
        # torch.set_printoptions(profile="full")
        print("input tensor", tensor)
        torch.set_printoptions(profile="default")
        print("input tensor shape", tensor.shape)
        iteration = 0
        lastmaximums = torch.zeros((tensor.shape[1]))
        while (not torch.sum(tensor) == 0):
            print("iteration", iteration)
            values, maximumsfromstart = torch.max(tensor, dim=0, keepdim=True)
            maximumindexs = torch.cat((maximumindexs, (maximumsfromstart + 1) * values), 0)
            # print("waspresent ?",torch.where(maximumsfromstart - 1 == lastmaximums,lastmaximums,0))
            # linemap[]
            print("maximumsfromstart", maximumsfromstart)
            print("values", values)  # torch.logical_not(values)
            print("maximumsfromstart.shape", maximumsfromstart.shape)
            tensor[maximumsfromstart, torch.arange(0, tensor.shape[1], dtype=torch.long)] = 0
            lastmaximums = maximumsfromstart
            iteration += 1
        maximumindexs -= 1
        torch.set_printoptions(profile="full")
        print("maximumindexs", maximumindexs)
        # lastcolumn = torch.

        for i in range(tensor.shape[1]):
            yindex = i

            currentcolumn = maximumindexs[:, i]
            # print("currentcolumn",currentcolumn)

            localtensor = torch.tensor([], dtype=torch.int16)
            xdebut = -1
            for j in range(currentcolumn.shape[0]):
                if currentcolumn[j] == -1:
                    linetensor = torch.cat((linetensor, localtensor), dim=0)

                    break
                # print(j+1,currentcolumn.shape[0])
                if not (j + 1) == currentcolumn.shape[0] and currentcolumn[j] + 1 == currentcolumn[j + 1]:
                    if xdebut == -1:
                        xdebut = currentcolumn[j]
                else:
                    if xdebut == -1:
                        localtensor = torch.cat((localtensor, torch.unsqueeze(
                            torch.tensor([currentcolumn[j], currentcolumn[j] + 1, yindex]), dim=0)), 0)
                    else:
                        localtensor = torch.cat(
                            (localtensor, torch.unsqueeze(torch.tensor([xdebut, currentcolumn[j] + 1, yindex]), dim=0)),
                            0)
                        xdebut = -1
                    if (j + 1) == currentcolumn.shape[0]:
                        linetensor = torch.cat((linetensor, localtensor), dim=0)
        print("linetensor", linetensor.shape)
        # Algo du plus proche voisin
        orderedlinetensor = torch.tensor([], dtype=torch.int16)
        # On divise le tenseur pour plus de rapidite
        numdiv = 3
        linetensorlist = []
        elementsum = 0
        print("startline")
        for i in range(numdiv):
            if i % 2 == 0:
                jrange = range(numdiv)
            else:
                jrange = range(numdiv-1,-1,-1)
            for j in jrange:
                xrange = int(i * self.conf.canvasresolution[0] / numdiv), int(
                    (i + 1) * self.conf.canvasresolution[0] / numdiv)-1
                yrange = int(j * self.conf.canvasresolution[1] / numdiv), int(
                    (j + 1) * self.conf.canvasresolution[1] / numdiv)-1

                print("range",xrange, yrange)
                #currentensor = torch.where(linetensor[:, 0] > xrange[0] and linetensor[:, 0] < xrange[1] and linetensor[:,2] > yrange[0] and linetensor[:,2] < yrange[1])
                filtered_tensor = linetensor[(linetensor[:, 0] >= xrange[0]) & (linetensor[:, 0] <= xrange[1]) & (linetensor[:, 2] >= yrange[0]) & (linetensor[:, 2] <= yrange[1])]
                linetensorlist.append(filtered_tensor)


        for linetensor in linetensorlist:
            if linetensor.shape[0] == 0:
                continue
            linetensor = self.splitlines(linetensor)
            # On selectionne la ligne du milieu
            currentlineindex = int(linetensor.shape[0] / 2)

            currentline = torch.unsqueeze(linetensor[currentlineindex, :], dim=0)
            currentx, currenty = currentline[:, 1], currentline[:,
                                                    2]  # pour la premiere ligne, on prend endx comme coordonnee
            print(currentline, currentx, currenty)
            initialenght = linetensor.shape[0]
            n=-1
            direction = False
            while not linetensor.shape[0] == 1:
                direction = not direction
                n += 1
                print(str(n), "/", initialenght)
                # On enleve la ligne de linetensor
                linetensor = linetensor[torch.arange(linetensor.shape[0]) != currentlineindex, :]
                # On ajoute la ligne a la pile ordonnee
                orderedlinetensor = torch.cat((orderedlinetensor, currentline), dim=0)
                # print(orderedlinetensor)
                # print(currentx,currenty)
                # Calcul des distances a partir du debut de la ligne puis de la fin de la ligne
                # Si la distance parcourue dans un sens depasse la limite, nul besoin de calculer cette partie
                if direction :
                    tensorprox = torch.pow((linetensor[:, 0] - currentx), 2) + torch.pow((linetensor[:, 2] - currenty), 2)
                else :
                    tensorprox= torch.pow((linetensor[:, 1] - currentx), 2) + torch.pow((linetensor[:, 2] - currenty), 2)

                # On prend le minimum des deux et on choisi le plus petit

                valuetensorprox, indicetensorprox = torch.min(tensorprox, 0)
                print("valuetensorprox, indicetensorprox",valuetensorprox, indicetensorprox)

                # valuetensorproxend, indicetensorproxend = torch.min(tensorproxend, 0)
                # print("valuetensorproxend, indicetensorproxend", valuetensorproxend, indicetensorproxend)
                currentlineindex = indicetensorprox
                if direction:
                    currentlinevalue = linetensor[currentlineindex]
                else:
                    currentlinevalue = torch.tensor( [linetensor[currentlineindex, 1], linetensor[currentlineindex, 0], linetensor[currentlineindex, 2]])
                # if valuetensorproxstart >= valuetensorproxend:
                #     currentlineindex = indicetensorproxend
                #     currentlinevalue = torch.tensor(
                #         [linetensor[currentlineindex, 1], linetensor[currentlineindex, 0], linetensor[currentlineindex, 2]])
                # else:
                #     currentlineindex = indicetensorproxstart
                #     currentlinevalue = linetensor[currentlineindex]

                #print("remaining", linetensor.shape[0])
                print("currentlinevalue", currentlinevalue)


                currentline = torch.unsqueeze(currentlinevalue, dim=0)
                currentx, currenty = currentlinevalue[1], currentlinevalue[2]
                # print(currentlineindex)

            # On ajoute la derniere ligne dans le bon sens
            if abs(currentx - linetensor[:, 0]) < abs(currentx - linetensor[:, 1]):
                lastline = torch.tensor(
                    [[linetensor[:, 1], linetensor[:, 0], linetensor[:, 2]]])
            else:
                lastline = linetensor
            orderedlinetensor = torch.cat((orderedlinetensor, lastline), 0)

        #print("orderedlinetensor", orderedlinetensor)
        print("orderedlinetensor.shape", orderedlinetensor.shape)

        return orderedlinetensor

    def splitlines(self,linetensor):
        maxtravel = int((self.conf.maximumtravelinonedirection/self.conf.canvasmax[0]) * self.conf.canvasresolution[0])
        outputtensor = torch.tensor([],dtype=torch.int16)
        #print(linetensor)
        for i in range(linetensor.shape[0]):
            #print("linetensor[i,:]",linetensor[i,:])
            lignedebut,lignefin = linetensor[i,0],linetensor[i,1]
            longueurligne = lignefin - lignedebut
            if longueurligne >= maxtravel:
                nbrdivisions = math.ceil(longueurligne/maxtravel)
                increment = longueurligne / nbrdivisions
                #print("increment",increment,"nbrdivisions",nbrdivisions)
                for j in range(0,nbrdivisions):
                    ligne = (torch.round(increment * j + lignedebut).to(torch.int16),torch.round(increment * (j+1) + lignedebut).to(torch.int16))
                    ligne = torch.tensor([[ligne[0],ligne[1],linetensor[i,2]]],dtype=torch.int16)
                    #print("ligne",ligne)
                    outputtensor = torch.cat((outputtensor, ligne), dim=0)
            else:
                outputtensor = torch.cat((outputtensor,torch.unsqueeze(linetensor[i,:],dim=0)),dim=0)
        return outputtensor