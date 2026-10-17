import os
import glob
import math
import string
import sys
def findnextcoordinates(startindex,linesplitedfile):
    xcoordinate, ycoordinate = "", ""
    for i in range(startindex,len(linesplitedfile)):
        line = linesplitedfile[i]
        xindex = line.rfind("X")
        if not xindex == -1:
            for j in range(xindex + 1, len(line)):
                if line[j] == " " or line[j] == "\n":
                    break
                xcoordinate += line[j]
            # print(xcoordinate)
        yindex = line.rfind("Y")
        if not yindex == -1:
            for j in range(yindex + 1, len(line)):
                if line[j] == " " or line[j] == "\n":
                    break
                ycoordinate += line[j]
        if not xcoordinate == "" and not ycoordinate == "":
            return float(xcoordinate), float(ycoordinate)
    return 1000000000,1000000000




def optimizegcode(filepath):
    skipfirstlines = 100
    liftupevent = "G1 Z15"
    liftupdistancethreshold = 10
    liftupreplacement = "G1 Z3 F30000"
    appendendfile = "G1 Z15 F30000; S0 \nG1 F3000\n;File optimized low Z travel\n"
    print("Opening",filepath)
    gcode_file = open(filepath, "r")
    output_file = open("finaloutput.gcode", "w")
    linesplitedfile = gcode_file.read().splitlines()
    xcoordinate = 0
    ycoordinate = 0
    lastx = 1000000
    lasty = 1000000
    for iindex, i in enumerate(linesplitedfile):
        if skipfirstlines > 0:
            skipfirstlines -= 1
            output_file.write(i + "\n")
            continue

        position = i.rfind(liftupevent)
        if not position == -1:
            print("liftup")
            xcoordinate, ycoordinate = float(xcoordinate), float(ycoordinate)
            nextx, nexty = findnextcoordinates(iindex,linesplitedfile)
            distance = math.sqrt((xcoordinate-nextx)**2 + (ycoordinate-nexty)**2)
            print("lastcoordinates: X =",xcoordinate," Y =",ycoordinate,"distance",distance)
            if distance < liftupdistancethreshold:
                output_file.write(liftupreplacement+ " ; travel=" + "{:.3f}".format(distance) + "\n")
            else:
                output_file.write(i+" ; travel="+ "{:.3f}".format(distance) + "\n")
            #lastx, lasty = xcoordinate, ycoordinate
            continue
        output_file.write(i+"\n")
        xindex = i.rfind("X")
        if not xindex == -1:
            xcoordinate = ""
            for j in range(xindex+1,len(i)):
                if i[j] == " " or i[j] == "\n" :
                    break
                xcoordinate += i[j]
            #print(xcoordinate)
        yindex = i.rfind("Y")
        if not yindex == -1:
            ycoordinate = ""
            for j in range(yindex + 1, len(i)):
                if i[j] == " " or i[j] == "\n":
                    break
                ycoordinate += i[j]

            #print(ycoordinate)
    output_file.write(appendendfile)

optimizegcode(sys.argv[1])
input("Press enter")