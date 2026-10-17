class PenColor:
    def __init__(self,colorname,rgb,saturationconstraint,distributionfactor = 1):
        self.colorname = colorname
        self.rgb = rgb
        self.saturationconstraint = saturationconstraint
        self.distributionfactor = distributionfactor
    def __str__(self):
        return self.colorname