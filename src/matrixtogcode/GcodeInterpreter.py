import torch

from src.matrixtogcode.FastStringModifier import FastStringModifier, modify_string_fast
from src.matrixtogcode.Machine import Machine
from src.matrixtogcode.MatriceEscalier import MatriceEscalier


class GcodeInterpreter:
    def __init__(self,conf,machine):
        self.conf = conf
        self.machine = machine
        self.file = open(self.conf.gcodefile, "w")
        self.startroutine()
        self.lastcommand = ""
        self.matriceescalier = MatriceEscalier(len(self.conf.pencolorlist))


    def startroutine(self):
        self.file.write("G1 Z15\n")
        self.file.write("M851 Z"+self.formatcoordinate(self.conf.zoffset) +"\n")

        self.machine.setZ(15)

    def endroutine(self):
        self.file.write("G1 Z15\n")
        self.machine.setZ(15)
    def addpencilrefillifneeded(self,gcode):
        #modifier = FastStringModifier(gcode)
        changetoolcode = "M117 New stylo\nG1 Z35\nG1 X432.5 Y447.0\nM226 P121\nG1 Z15\n"
        #result = modifier.find_and_insert(50, "G1 Z"+str(self.conf.shorttravelz) , changetoolcode)
        #result = modify_string_fast(gcode, 50, "G1 Z7", changetoolcode)
        #print("G1 Z"+str(self.conf.shorttravelz))
        result = modify_string_fast(gcode, 7500000, "G1 Z"+str(self.conf.shorttravelz), changetoolcode)
        return result
    def safe_single_color_file(self,filecontent,colorname):
        filepath = self.conf.outputbasedirectory +"/"+colorname +".gcode"
        with open(filepath, "w") as f:
            f.write(filecontent)

    def addpreprocessedgcode(self,gcode):
        self.file.write("G1 Z15\n")
        self.file.write(gcode)
        self.file.write("G1 Z15\n")
    def changetool(self):
        self.machine.travelsincelastwipe = 0
        self.lastcommand = ""
        self.file.write("G1 Z35\n")
        self.machine.setZ(32)
        self.machine.setY(self.conf.canvasmax[0] / 2)
        self.machine.setX(self.conf.canvasmax[1] / 2)
        self.file.write("G1 X"+ self.formatcoordinate(self.machine.x) + " Y" + self.formatcoordinate(self.machine.y) + "\n")
        self.file.write("M226 P121\n")
    def displayonscreen(self,text):
        self.file.write("M117 "+ text + "\n")
    def displayprogress(self,lineindex,linescount):
        if lineindex % 20 == 0:
            self.file.write("M117 " + str(lineindex)+"/"+str(linescount)+ "\n")

    def drawpixel(self,coordinateindex,colorforce):
        y,x = self.getcoordinatesfromindex(coordinateindex)
        z = self.extrapolatez(colorforce)
        if z < self.conf.zmaxforce:
            self.machine.travelsincelastwipe += self.conf.xyresolution[0]
            #print(self.machine.travelsincelastwipe)
        #print(y,x,self.extrapolatez(colorforce))

        xcommand, ycommand, zcommand = "", "", ""
        xyspeed = " F" + self.formatcoordinate(self.conf.xyspeed)
        currentspeed = xyspeed
        if not x == self.machine.x:
            self.machine.setX(x)
            xcommand = " X" + self.formatcoordinate(self.machine.x)
        if not y == self.machine.y:
            self.machine.setY(y)
            ycommand = " Y" + self.formatcoordinate(self.machine.y)
        if not z == self.machine.z:
            self.machine.setZ(z)
            currentspeed = self.conf.zspeed
            zcommand = "\nG1 Z" + self.formatcoordinate(self.machine.z) + " F"+ str(self.conf.zspeed)

        if self.machine.speed == currentspeed and not z == self.machine.z:
            xyspeed = ""
        self.machine.speed = currentspeed
        command = "G1" + xcommand + ycommand + xyspeed + zcommand + "\n"
        if not xcommand == ""  and ycommand == "" and zcommand == "" :
            self.lastcommand = command
        else:
            if (not self.lastcommand == "" and not (ycommand == "" or zcommand == "")) or self.isatxendofline(coordinateindex):
                print("x",self.machine.x,"y",self.machine.y,"z",self.machine.z,"color",self.machine.currentcolorchannel)
                print("lastx", self.machine.lastx, "lasty", self.machine.lasty, "lastz", self.machine.lastz)
                print("command:",command)
                if self.machine.lastz == 0:
                    self.file.write(";starting from fringe\n")
                    self.file.write(self.lastcommand)

                    #print(self.lastcommand,"z",self.machine.z,"y",self.machine.y)
                else:
                    self.file.write(";not starting from fringe\n")
                    self.machine.setZ(5)
                    self.file.write("G1 Z5"+ " F" + str(self.conf.zspeed) + "\n")





            self.file.write(command)
            self.lastcommand = ""
        # self.comment(str(self.machine))
        # self.comment(str(coordinateindex))
        #print(movementcommand)
    def drawline(self,lineindex,lineindexrange,shorttravel,adjacenttravel):
        y,x = self.getcoordinatesfromindex((lineindex,lineindexrange[0]))
        _, x2 = self.getcoordinatesfromindex((lineindex, lineindexrange[1]))
        xyspeed = " F" + self.formatcoordinate(self.conf.xyspeed)
        if adjacenttravel:
            self.file.write(";adjacent travel\n")
            command = ""
        elif shorttravel:
            command = "G1 Z"+self.formatcoordinate(self.conf.shorttravelz) +" F"+ str(self.conf.zspeed) +"\n"
        else:
            command = "G1 Z"+self.formatcoordinate(self.conf.safez) +" F"+ str(self.conf.zspeed) +"\n"


        if not y == self.machine.y:
            command += "G1 X" + self.formatcoordinate(x) + " Y" + self.formatcoordinate(y) + xyspeed + "\n"
            self.machine.setY(y)
        else:
            command += "G1 X"+self.formatcoordinate(x) + xyspeed + "\n"

        command += "G1 Z0" +" F"+ str(self.conf.zspeed) +"\n"
        self.machine.setZ(0)

        command += "G1 X"+self.formatcoordinate(x2) + xyspeed + "\n"
        self.machine.setX(x2)
        #print(x,x2)
        self.machine.travelsincelastwipe += abs(x - x2)
        self.file.write(command)


    def wipe(self):
        self.machine.travelsincelastwipe = 0
        xmax = self.conf.machinelimits[0]
        minimumwipez = str(6)
        maximumwipez = str(10)
        wipelenght = 2
        x,y = self.machine.x,self.machine.y
        self.file.write(";Wiping\n")
        self.file.write("G1 X" + self.formatcoordinate(x) + "\n")
        self.file.write("G1 Z30\n")
        self.file.write("G1 X"+str(xmax) + " Y" + self.formatcoordinate(y) +"\n")
        self.file.write("G1 Z"+minimumwipez+"\n")
        self.file.write("G1 Y" + self.formatcoordinate(y+wipelenght) + " Z"+maximumwipez + "\n")
        self.file.write("G1 Y" + self.formatcoordinate(y) + " Z" + minimumwipez + "\n")
        self.file.write("G1 Y" + self.formatcoordinate(y - wipelenght) + " Z" + maximumwipez + "\n")
        self.file.write("G1 Y" + self.formatcoordinate(y) + " Z" + minimumwipez + "\n")
        self.file.write("G1 X" + self.formatcoordinate(xmax - wipelenght) + " Z" + maximumwipez + "\n")
        self.file.write("G1 X" + self.formatcoordinate(xmax) + " Z" + minimumwipez + "\n")
        self.file.write("G1 Z30\n")
        self.file.write("G1 X" + self.formatcoordinate(x) + " Y" + self.formatcoordinate(y) + "\n")
        self.file.write("G1 Z" + self.formatcoordinate(self.machine.z) + "\n")
        self.file.write(";End wiping \n")

    def xchanneladjustment(self):
        if self.conf.resolutionmethod == "hilbert":
            return self.matriceescalier.colorpositionadjustementtensornp[0,self.machine.currentcolorchannel] * self.conf.xyresolution[0]
        elif self.conf.resolutionmethod == "splittedlines":
            return 0
    def ychanneladjustment(self):
        if self.conf.resolutionmethod == "hilbert":
            return self.matriceescalier.colorpositionadjustementtensornp[1,self.machine.currentcolorchannel] * self.conf.xyresolution[1]
        elif self.conf.resolutionmethod == "splittedlines":
            return self.conf.ychanneladjustment * self.machine.currentcolorchannel
    def isatxendofline(self,coordinateindex):
        return coordinateindex[1] == self.conf.canvasresolution[0]-1 or coordinateindex[1] == 0

    def comment(self,comment):
        self.file.write("; "+comment + "\n")
    def formatcoordinate(self,value):
        formatedvalue = "{:.3f}".format(value)
        formatedvalue = str(float(formatedvalue))
        return formatedvalue

    def extrapolatez(self,colorforce):
        #if colorforce < 1/255:

        if colorforce == 1 :
            return 0
        return self.conf.safez
        #z = self.conf.zmaxforce - (self.conf.zmaxforce * colorforce)
        #z = self.cubicregression(colorforce) * self.conf.zmaxforce

    def cubicregression(self,regularizednumber):
        if regularizednumber < 0 or regularizednumber > 1:
            exit("Ce nombre doit être entre 0 et 1")
        return 1.01 - (97.1997 * pow(regularizednumber,3) - 214.4444 * pow(regularizednumber,2) + 49.1770 * regularizednumber + 69.2227)/72
    def getcoordinatesfromindex(self,coordinateindex):
        y = coordinateindex[0] * self.conf.xyresolution[1] + self.ychanneladjustment()
        x = coordinateindex[1] * self.conf.xyresolution[0] + self.xchanneladjustment()
        return (y,x)

    def getxfromindex(self,xindex,compensation = 0):
        xfuzz = torch.rand((1)) * self.conf.randomfuzz[0] - self.conf.randomfuzz[0]/2
        return self.formatcoordinate(xindex * self.conf.xyresolution[0] + self.xchanneladjustment() + xfuzz.item()+compensation)
    def getyfromindex(self,yindex,compensation = 0):
        yfuzz = torch.rand((1)) * self.conf.randomfuzz[1] - self.conf.randomfuzz[1] / 2
        return self.formatcoordinate(yindex* self.conf.xyresolution[1] + self.ychanneladjustment() + yfuzz.item()+compensation)