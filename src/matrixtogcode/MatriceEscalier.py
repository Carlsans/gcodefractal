import torch


class MatriceEscalier:
    def __init__(self,value,debug=False):
        self.debug = debug
        self.ME = torch.tensor(([[ 0],[ 1],[ 4],[ 9],[16],],
                                [[ 2],[ 3],[ 6],[11],[18],],
                                [[ 5],[ 7],[ 8],[13],[20],],
                                [[10],[12],[14],[15],[22],],
                                [[17],[19],[21],[23],[24],],),dtype=torch.int8).squeeze_()
        self.setvalue(value)
        self.computeijmax()
        self.generatecolorpositionadjustementtensor()
        print("Tenseur d'ajustement des couleurs(0 à n couleurs) : ",self.colorpositionadjustementtensor)
    def getij(self,value):
        indexs = (self.ME == value).nonzero(as_tuple=True)
        return int(indexs[0]),int(indexs[1])

    def getijproportions(self,value):
        evaluatedvalueij = self.getij(value)
        print("evaluatedvalueij",evaluatedvalueij)
        return (evaluatedvalueij[0]/self.maxij[0],evaluatedvalueij[1]/self.maxij[1])
    def generatecolorpositionadjustementtensor(self):
        self.colorpositionadjustementtensor = torch.zeros(2,self.currentvalue)
        for colornumber in range(self.currentvalue):
            self.colorpositionadjustementtensor[0,colornumber],self.colorpositionadjustementtensor[1,colornumber]= self.getijproportions(colornumber)
        self.colorpositionadjustementtensornp = self.colorpositionadjustementtensor.detach().numpy()
    def setvalue(self,value):
        self.currentvalue = value

    def computeijmax(self):
        maxi,maxj = 0,0
        for cell in range(self.currentvalue):
            currentcellij = self.getij(cell)
            if maxi < currentcellij[0]:
                maxi = currentcellij[0]
            if maxj < currentcellij[1]:
                maxj = currentcellij[1]

        self.maxij = (maxi+1,maxj+1)
        if(self.debug):
            print("Max i,j=",self.maxij )
            print(self.currentvalue)


# colorsnumber = 12
# me = MatriceEscalier(colorsnumber)
# for colornumber in range(colorsnumber):
#
#     print("Numéro de couleur",colornumber,"proportions",me.getijproportions(colornumber))
# print(me.colorpositionadjustementtensor)