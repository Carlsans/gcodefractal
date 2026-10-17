import json
import os
import random

import torch.random

from src.matrixtogcode.PenColor import PenColor
from src.matrixtogcode.PenColorMix import PenColorMix


class Configuration:
    def __init__(self):
        self.setcolorlist()
        self.setcolormixlist()

        ### Files
        self.outputbasedirectory = os.path.dirname(__file__) + "/images"
        # /home/carl/PycharmProjects/RewriteFractal/images/rescaled/
        self.inputimagepath = os.path.dirname(__file__) + "/images/anaplexity.png"
        self.gcodefile = self.inputimagepath[:-4] + ".gcode"
        self.ztestfile = os.path.dirname(__file__) + "/images/ztest.gcode"
        self.common_dir = os.path.dirname(os.path.dirname(__file__)) + "/common/"

        # Performance
        self.generatepreviews = True
        self.generatemultiplerandompreviews = 500 #200 # Use -1 to disable or 0 to enter seed directly
        #self.generatemultiplerandompreviews = 0
        self.generatemultiplerandompreviewsandmixcolors = True
        self.testmode = False
        # hilbert or splittedlines
        self.resolutionmethod = "random_lines"
        # Travel optimization
        self.maximumtravelinonedirection = 60  # in mm
        # self.traveloptimizationmax_epoch = 500
        # self.traveloptimizationcutscount = 20
        # Options/features/calibration
        self.pencolorcharttest = False
        ### Machine
        # In mm
        self.machinelimits = (909, 865)
        self.canvasmax = (894, 865)
        #self.canvasresolution = (894*3,int(865*3))
        self.canvasresolution = (894 * 4, int(865 * 4))
        #self.canvasresolution = (894 , int(865 ))
        #self.canvasmax = (100, 100)
        #self.canvasresolution = (500, 500)
        self.machinecompensationx = (-.1,.1)#(-.2,.6) Apres :(-.6,.7)(trop)
        self.machinecompensationy = (-.1,.1)#(-.4,.4) Apres :(-.5,.5)
        #self.machinecompensationx = (0, 0)
        #self.machinecompensationy = (0, 0)
        self.channelnumber = len(self.pencolorlist)
        self.xyresolution = (
            self.canvasmax[0] / (self.canvasresolution[0] + 1), self.canvasmax[1] / (self.canvasresolution[1] + 1))
        #self.randomfuzz = (self.xyresolution[0] * 1,self.xyresolution[1] * 1)
        self.randomfuzz = (0,0) # Disabled
        # self.skipcolorlist = ["greenpale"]
        self.xchanneladjustment = self.xyresolution[0] / self.channelnumber
        self.ychanneladjustment = self.xyresolution[1] / self.channelnumber
        print("Resolution X =", self.xyresolution[0], "Y =", self.xyresolution[1], "Y Channel adjustment",
              self.ychanneladjustment)
        self.donotdrawbelow = 0.3
        self.maxdistancebeforewipe = self.canvasmax[0] * 10
        # self.maxdistancebeforewipe = - 1
        # Machine built in
        self.zoffset = -1.2
        self.zmaxforce = 1.7
        self.shorttravelz = 2.5
        self.shorttravelmaxdistance = 5
        self.safez = 7
        self.xyspeed = 3000  # mm par minute
        self.travelspeed = 6000
        print("Estimate speed == ", (self.canvasresolution[0] * self.canvasresolution[1]) / self.xyspeed,
              " minutes or ", (self.canvasresolution[0] * self.canvasresolution[1]) / (self.xyspeed * 60), "hours")
        self.zspeed = 30000
        self.max_line_length_range = (3,4)# etait (8,15)
        self.change_pen_ratio = .3
        self.change_pen_height = 25
        self.generateRustConfigFile()
        
    def generateRustConfigFile(self):
        config = {
            "resolutionX": self.canvasresolution[0],
            "resolutionY": self.canvasresolution[1],
            "sizeX": self.canvasmax[0],
            "sizeY": self.canvasmax[1],
            "xyspeed": self.xyspeed,
            "travelspeed": self.travelspeed,
            "safez": self.safez,
            "shorttravelz" : self.shorttravelz,
            "shorttravelmaxdistance" : self.shorttravelmaxdistance,
            "xyspeed": self.xyspeed,
            "travelspeed": self.travelspeed,
            "zspeed": self.zspeed,
            "max_line_length_min": self.max_line_length_range[0],
            "max_line_length_max": self.max_line_length_range[1],
            "change_pen_ratio": self.change_pen_ratio,
            "change_pen_height": self.change_pen_height,

            #"":,
        }
        filedirectory = os.path.dirname(__file__)+"/../common/"
        print(filedirectory)

        # Save config
        with open(filedirectory+"config.json", "w") as f:
            json.dump(config, f)

    def setcolorlist(self,randomdistributionfactorseed = -1):
        numberofpen = 6
        self.whitecolordistributionfactor = 0  # Si 0, seul la premiere couleur est blanche
        if randomdistributionfactorseed < 0:
            distributionfactorlist = [0.2267058593810488, 0.9622950358343828, 0.12633089865085956, 0.7048169228716079, 0.08518526805075266, 0.24744098492908506]
        else:
            #random.seed = randomdistributionfactorseed
            #distributionfactorlist = []
            torch.manual_seed(randomdistributionfactorseed)
            distributionfactorlist = torch.rand(numberofpen)
            # for i in range(numberofpen):
            #     distributionfactorlist.append(random.random())
        print("distributionfactorlist",distributionfactorlist,"seed",randomdistributionfactorseed)
        lightblue = PenColor("lightblue", (36, 95, 143), 3, distributionfactor=distributionfactorlist[0])
        pink = PenColor("pink", (168, 57, 114), 3, distributionfactor=distributionfactorlist[1])  # 1.3
        green = PenColor("green", (99, 123, 65), 2, distributionfactor=distributionfactorlist[2])
        purple = PenColor("purple", (57, 32, 97), 2, distributionfactor=distributionfactorlist[3])
        red = PenColor("red", (159, 59, 61), 2, distributionfactor=distributionfactorlist[4])
        darkblue = PenColor("darkblue", (50, 48, 117), 1, distributionfactor=distributionfactorlist[5])  # 4

        # Non compatible color list
        #self.noncompatiblepencolor = [["green", "pink"], ["green", "red"], ["lightblue", "red"],["green", "purple"]]
        self.noncompatiblepencolor = [["green", "pink"], ["green", "red"], ["lightblue", "red"], ["green", "purple"],["darkblue", "purple"],["red", "purple"],["lightblue", "purple"]]
        # black = PenColor("black", (0, 0, 0), 1)
        # Printed in that order
        self.pencolorlist = [pink, green, lightblue, red, purple, darkblue]

    def setcolormixlist(self):
        self.colorlistmix = [PenColorMix(['darkblue'], (50, 48, 117), "000001"),
                             PenColorMix(['purple'], (57, 32, 97), "000010"),
                             PenColorMix(['red'], (159, 59, 61), "000100"),
                             PenColorMix(['lightblue'], (36, 95, 143), "001000"),
                             PenColorMix(['green'], (99, 123, 65), "010000"),
                             PenColorMix(['pink'], (168, 57, 114), "100000"),
                             PenColorMix(['purple', 'darkblue'], "57497c", "000011"),
                             PenColorMix(['red', 'darkblue'], "41334a", "000101"),
                             PenColorMix(['red', 'purple'], "7f5678", "000110"),
                             PenColorMix(['lightblue', 'darkblue'], "4c598d", "001001"),
                             PenColorMix(['lightblue', 'purple'], "403e70", "001010"),
                             PenColorMix(['lightblue', 'red'], "565563", "001100"),
                             PenColorMix(['green', 'darkblue'], "404646", "010001"),
                             PenColorMix(['green', 'purple'], "554953", "010010"),
                             PenColorMix(['green', 'red'], "6d5b4d", "010100"),
                             PenColorMix(['green', 'lightblue'], "548278", "011000"),
                             PenColorMix(['pink', 'darkblue'], "624983", "100001"),
                             PenColorMix(['pink', 'purple'], "60327a", "100010"),
                             PenColorMix(['pink', 'red'], "a3527d", "100100"),
                             PenColorMix(['pink', 'lightblue'], "653f78", "101000"),
                             PenColorMix(['pink', 'green'], "744152", "110000"),
                             PenColorMix(['red', 'purple', 'darkblue'], "5b4671", "000111"),
                             PenColorMix(['lightblue', 'purple', 'darkblue'], "615c92", "001011"),
                             PenColorMix(['lightblue', 'red', 'darkblue'], "46466a", "001101"),
                             PenColorMix(['lightblue', 'red', 'purple'], "63527c", "001110"),
                             PenColorMix(['green', 'purple', 'darkblue'], "4b425f", "010011"),
                             PenColorMix(['green', 'red', 'darkblue'], "5b5255", "010101"),
                             PenColorMix(['green', 'red', 'purple'], "5f424e", "010110"),
                             PenColorMix(['green', 'lightblue', 'darkblue'], "3e5055", "011001"),
                             PenColorMix(['green', 'lightblue', 'purple'], "4e5661", "011010"),
                             PenColorMix(['green', 'lightblue', 'red'], "717c77", "011100"),
                             PenColorMix(['pink', 'purple', 'darkblue'], "6a4b8c", "100011"),
                             PenColorMix(['pink', 'red', 'darkblue'], "7a5087", "100101"),
                             PenColorMix(['pink', 'red', 'purple'], "7d417a", "100110"),
                             PenColorMix(['pink', 'lightblue', 'darkblue'], "423d80", "101001"),
                             PenColorMix(['pink', 'lightblue', 'purple'], "4e3576", "101010"),
                             PenColorMix(['pink', 'lightblue', 'red'], "593e67", "101100"),
                             PenColorMix(['pink', 'green', 'darkblue'], "876a88", "110001"),
                             PenColorMix(['pink', 'green', 'purple'], "8a7081", "110010"),
                             PenColorMix(['pink', 'green', 'red'], "a87284", "110100"),
                             PenColorMix(['pink', 'green', 'lightblue'], "7f6c82", "111000"),
                             PenColorMix(['lightblue', 'red', 'purple', 'darkblue'], "736a8e", "001111"),
                             PenColorMix(['green', 'red', 'purple', 'darkblue'], "705c6f", "010111"),
                             PenColorMix(['green', 'lightblue', 'purple', 'darkblue'], "8f8495", "011011"),
                             PenColorMix(['green', 'lightblue', 'red', 'darkblue'], "868588", "011101"),
                             PenColorMix(['green', 'lightblue', 'red', 'purple'], "7c7079", "011110"),
                             PenColorMix(['pink', 'red', 'purple', 'darkblue'], "654876", "100111"),
                             PenColorMix(['pink', 'lightblue', 'purple', 'darkblue'], "4e4976", "101011"),
                             PenColorMix(['pink', 'lightblue', 'red', 'darkblue'], "574d6c", "101101"),
                             PenColorMix(['pink', 'lightblue', 'red', 'purple'], "5e526a", "101110"),
                             PenColorMix(['pink', 'green', 'purple', 'darkblue'], "866c8d", "110011"),
                             PenColorMix(['pink', 'green', 'red', 'darkblue'], "826675", "110101"),
                             PenColorMix(['pink', 'green', 'red', 'purple'], "91657e", "110110"),
                             PenColorMix(['pink', 'green', 'lightblue', 'darkblue'], "625679", "111001"),
                             PenColorMix(['pink', 'green', 'lightblue', 'purple'], "504463", "111010"),
                             PenColorMix(['pink', 'green', 'lightblue', 'red'], "66465d", "111100"),
                             PenColorMix(['green', 'lightblue', 'red', 'purple', 'darkblue'], "534c5c", "011111"),
                             PenColorMix(['pink', 'lightblue', 'red', 'purple', 'darkblue'], "60507c", "101111"),
                             PenColorMix(['pink', 'green', 'red', 'purple', 'darkblue'], "704c66", "110111"),
                             PenColorMix(['pink', 'green', 'lightblue', 'purple', 'darkblue'], "65556f", "111011"),
                             PenColorMix(['pink', 'green', 'lightblue', 'red', 'darkblue'], "776773", "111101"),
                             PenColorMix(['pink', 'green', 'lightblue', 'red', 'purple'], "675265", "111110"),
                             PenColorMix(['pink', 'green', 'lightblue', 'red', 'purple', 'darkblue'], "413d54", "111111")]
        for acolor in self.colorlistmix:
            print(acolor)

    # def getcolorname(self,usesixchannels):
    #     if usesixchannels:
    #         return ["redpale","greendark","bluepale","reddark","greenpale","bluedark"]
    #     return ["red","green","blue"]
