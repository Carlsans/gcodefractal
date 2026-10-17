class Machine:
    def __init__(self):
        self.x,self.y,self.z = 0, 0, 15
        self.lastx,self.lasty,self.lastz= 0,0,15
        self.speed = -1
        self.currentcolorchannel = 0
        self.travelsincelastwipe = 0

    def setX(self,x):
        self.lastx = self.x
        self.x = x

    def setY(self,y):
        self.lasty = self.y
        self.y = y

    def setZ(self,z):
        self.lastz = self.z
        self.z = z
    def __str__(self):
        return "X = " + str(self.x)+" Y = "+str(self.y)+" Z = "+str(self.z)+" speed = "+str(self.speed)+" current color = "+str(self.currentcolorchannel)