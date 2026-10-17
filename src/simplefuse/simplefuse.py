import os
import glob
import math


def simplefuse(verbose=False):
    gcodedirectory = os.getcwd()+"\\"
    print(gcodedirectory)
    print("Les fichiers suivants seront additionnés dans cet ordre :")
    if os.path.exists(gcodedirectory+"output.gcode"):
        os.remove(gcodedirectory+"output.gcode")

    os.chdir(gcodedirectory)
    data = ""
    filenumber = 0
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
        currentfiledata += "\n;File sub number = " + str(filenumber) + "\n" + upmovement + "\n"
        file_stats = os.stat(gcodedirectory+file)
        gcode_file = open(gcodedirectory+file, "r")
        currentfiledata += gcode_file.read() + "\n"
        data += currentfiledata
        gcode_file.close()
        filenumber+=1
    output_file = open(gcodedirectory+"output.gcode", "w")
    output_file.write(data)
    output_file.close()
    if verbose:
        print(data)
simplefuse()
