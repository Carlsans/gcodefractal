import os
import glob
import math
def addprogresstolcd(filedata):
    linescount = len(filedata.splitlines())
    lineindex = 0
    output = ""
    currentpercentage = 1
    for line in filedata.splitlines():
        output += line + "\n"
        currentprogressratio = math.floor(lineindex / linescount * 100)
        if currentprogressratio > currentpercentage:
            currentpercentage = currentprogressratio
            output += "\nM117 Progress: " + str(currentpercentage) + "% \n"
        lineindex += 1
        #print(line)
    return output

def fusegcode(split=False,verbose=False):
    gcodedirectory = os.getcwd()+"\\"
    print(gcodedirectory)
    print("Les fichiers suivants seront additionnés dans cet ordre :")
    if os.path.exists(gcodedirectory+"output.gcode"):
        os.remove(gcodedirectory+"output.gcode")

    os.chdir(gcodedirectory)
    data = ""
    filenumber = 0
    splitin = 2
    upmovement = 'G1 Z15 F30000; S0'
    totalfilenumber = 0
    for file in sorted(glob.glob("*.gcode")):
        print(file)
        totalfilenumber += 1
    continuing = input("Continuer ? (O ou o)")
    if not (continuing == "O" or continuing == "o"):
        exit()

    for file in sorted(glob.glob("*.gcode")):
        currentfiledata = ""
        currentfiledata += "\n;File number = " + str(filenumber) + "\n"
        file_stats = os.stat(gcodedirectory+file)

        currentfiledata += "\nM300 S880 P5000\nM117 Sz:" + str(round(file_stats.st_size/1024)) + "Kb" + " F:" + str(filenumber + 1) + "/" + str(totalfilenumber) + "\n"
        currentfiledata += "\nG1 Z25\nG1 X450 Y430\nG1 Z60\nM226 P121\nG1 Z20\nM226 P121\n "
        gcode_file = open(gcodedirectory+file, "r")
        if split:
            linesplitedfile = gcode_file.read().splitlines()
            splittedlinestart = int(len(linesplitedfile) / splitin)
            alinecount = 0
            findnextupmovement = False
            for aline in linesplitedfile:
                alinecount +=1
                currentfiledata += aline + "\n"
                if alinecount == splittedlinestart:
                    findnextupmovement = True

                if findnextupmovement:
                    if aline == upmovement:
                        findnextupmovement = False
                        currentfiledata += "\nG1 Z25\nG1 X480 Y430\nG1 Z20\nM226 P121\n "


        else:
            currentfiledata += gcode_file.read() + "\n"
        currentfiledata = addprogresstolcd(currentfiledata)
        data += currentfiledata
        gcode_file.close()
        filenumber+=1
    output_file = open(gcodedirectory+"output.gcode", "w")

    output_file.write(data)
    output_file.close()
    if verbose:
        print(data)


fusegcode(split=False)
