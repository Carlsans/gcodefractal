import random

import torch


class PenColorMix:
    def __init__(self,colornamelist,rgb,binary):
        self.colornamelist = colornamelist
        if isinstance(rgb, str):
            if not len(rgb) == 0:
                if len(rgb) == 7:
                    rgb = rgb[1:7]
                rgb = (int(rgb[0:2], 16),int(rgb[2:4], 16),int(rgb[4:6], 16))
            else:
                rgb = (0,0,0)
        # if isinstance(rgb, tuple):
        #     ...

            #else:
                ### FOR TEST ONLY REMOVE

                #rgb = (random.randint(0,255),random.randint(0,255),random.randint(0,255))


        self.rgb = rgb
        self.binary = torch.tensor([i == "1" for i in binary])

    def __str__(self):
        colors = ""
        for i in self.colornamelist:
            colors += i + ","
        return colors[0:-1]+" = "+str(self.rgb) + " "+ str(self.binary)


