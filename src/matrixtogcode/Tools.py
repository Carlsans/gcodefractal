from src.matrixtogcode.Configuration import Configuration


class Tools:
    def __init__(self):
        self.conf = Configuration()

    def teststyloheight(self):
        self.file = open(self.conf.ztestfile, "w")
        self.file.write("G1 Z15 F2000\nG1 X0\n")
        zvariation = 2
        ymax = self.conf.canvasmax[0]
        steps = 86
        for i in range(steps + 1):
            x = ymax * (i / steps)
            z = zvariation * (i / steps)
            gcodecommand = "G1 Y" + "{:.3f}".format(x) + " Z" + "{:.3f}".format(z) + "\n"
            self.file.write(gcodecommand)
        self.file.write("G1 Z15\n")
tool = Tools()
tool.teststyloheight()