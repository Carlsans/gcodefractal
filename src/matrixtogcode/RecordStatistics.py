import torch

from src.matrixtogcode.Configuration import Configuration


class RecordStatistics:
    def __init__(self,colors):
        self.conf = Configuration()
        self.colors = colors
        self.statfile = open( self.conf.inputimagepath[0:-4]+"stats.txt", "w")
        #self.printandsave("Color omitted",self.conf.skipcolorlist)

    def getImageTensorStats(self,imagetensor):
        self.printandsave("Image tensor shape =",imagetensor.shape)
        #colornames = self.conf.getcolorname(imagetensor.shape[0]==6)
        stats = []
        for i in range(imagetensor.shape[0]):
            color, mean = self.colors.getPencolornamebyindex(i), torch.mean(imagetensor[i,:,:]*1.0).item()
            std, var = torch.std(imagetensor[i,:,:]*1.0).item(),torch.var(imagetensor[i,:,:]*1.0).item()
            self.printandsave("Color =",color)
            self.printandsave("Mean =",mean )
            self.printandsave("Standard deviation =", std, "Variance =",var)
            stats.append([color, mean, std, var])
            self.printandsave("___________")
        self.stats = stats
        sortbymean = sorted(stats, key=lambda astat: -astat[1])
        colorbymean = [i[0] for i in sortbymean]
        meanbycolor = [i[1] for i in sortbymean]
        self.printandsave("Color mean descendent order",colorbymean)
        self.printandsave("Mean values",meanbycolor)
        self.printandsave()

    def getMeanbyColorName(self,colorname):
        return "M=" + str(int([i[1] for i in self.stats if i[0] == colorname][0]*100))+"%"



    def printandsave(self,*args):
        text = ""
        for i in args:
            text += str(i) + " "
        print(text)
        self.statfile.write(text+"\n")

