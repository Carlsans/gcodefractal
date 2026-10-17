import os
from xml.dom import minidom
import math

def splitsvg(subfilesnumber = 8,getlengthbypos = False,dellist=None, mode = "bymaximumsize", maxsizeinkb=-1):
    sodipodi ="<sodipodi:namedview id=\"base\" pagecolor=\"#ffffff\" bordercolor=\"#666666\" borderopacity=\"1.0\" inkscape:pageopacity=\"0.0\" inkscape:pageshadow=\"2\" "
    sodipodi += "\ninkscape:zoom=\"0.35\" inkscape:cx=\"400\" inkscape:cy=\"560\" inkscape:document-units=\"mm\" inkscape:current-layer=\"layer1\" showgrid=\"false\" inkscape:window-width=\"1570\" inkscape:window-height=\"1035\" inkscape:window-x=\"-8\" inkscape:window-y=\"-8\" inkscape:window-maximized=\"1\" />"

    svg_file = os.getcwd() +"\\test.svg"
    print(svg_file)

    doc = minidom.parse(svg_file)  # parseString also exists


    widthmm = 900
    heightmm = 865
    def getdlength(elem):
        return len(elem[0])
    def getidvalue(elem):
        return int(elem[2][4:])
    def getcolor(elem):
        return elem[1][6:12]

    def getcoloraverage(elem):
        colorhexstring = elem[1][6:12]
        redcolor = int(colorhexstring[0:1],16)
        greencolor = int(colorhexstring[2:3],16)
        bluecolor = int(colorhexstring[4:5],16)
        print(redcolor," ",greencolor," ",bluecolor)
        return (redcolor+greencolor+bluecolor)/3

    pathlist = []
    isother = True
    for path in doc.getElementsByTagName('path'):
        pathlist.append([path.getAttribute('d'),path.getAttribute('style'),path.getAttribute('id'),path.getAttribute('inkscape:connector-curvature')])


    #pathlist = sorted(pathlist, key=getdlength,reverse=True)
    pathlist = sorted(pathlist, key=getcoloraverage,reverse=False)
    for i in pathlist:
        print(getcoloraverage(i))

    if getlengthbypos:
        n = 0
        for apath in pathlist :
            print(str(getdlength(apath)) + " " + str(n))
            n += 1
        exit()
    if dellist is not None:
        pathlist = [j for i, j in enumerate(pathlist) if i not in dellist]

    #pathlist.sort(key=getdlength,reverse=True)
    #for i in pathlist:
    #    print(i[2],i[1])
    if mode == "mixedfiles":
        maxrange = math.ceil(len(pathlist) / subfilesnumber)
        pathindex = 0
        for filenumber in range(subfilesnumber):
            print("Starting batch " + str(filenumber))
            pathbatch = []
            n = filenumber
            while n < len(pathlist):
                pathbatch.append(pathlist[n])
                n += subfilesnumber
            pathbatch = sorted(pathbatch, key=getidvalue, reverse=True)

            for t in pathbatch:
                print(t[2],t[1])
            with open(os.getcwd() +"\\result" + str(filenumber)+".svg", 'w') as file:
                file.write("<svg width=\""+str(widthmm)+"mm\" height=\""+str(heightmm)+"mm\" viewBox=\"0 0 "+str(widthmm)+" "+str(heightmm)+ "\">")
                file.write(sodipodi)

                for i in pathbatch:
                        #file.write(";id="+str(i[2])+" pathindex="+str(pathindex)+" filenumber "+str(filenumber))
                        file.write("<path \n")
                        file.write("style=\""+i[1]+"\"\n")
                        file.write("d=\""+i[0]+"\"\n")
                        file.write("id=\""+i[2] + "\"\n")
                        file.write("inkscape:connector-curvature=\""+i[3] + "\"\n")
                        file.write(" />")

                file.write("</svg>")
        print("Finished !")
        path_elements = doc.getElementsByTagName('path')
        doc.unlink()


    if mode=="bymaximumsize":
        print("Total elements = ",len(pathlist))
        totalpathbytes = 0
        totalfiles = 0
        bytescount = 0
        pathbatch = []
        pathbatchs = []
        for apath in pathlist:
            pathbatch.append(apath)
            print("id = ", apath[2], "lenght ", len(apath[0]))
            bytescount += len(apath[0])
            if bytescount > maxsizeinkb*1024:
                bytescount = 0
                pathbatchs.append(pathbatch)
                pathbatch = []
                totalfiles += 1

            totalpathbytes += len(apath[0])
        if pathbatch:
            pathbatchs.append(pathbatch)
            totalfiles += 1
        print("Total size = ",totalpathbytes, " on ",totalfiles, " files.")
        filenumber=0

        for pathbatch in pathbatchs:
            with open(os.getcwd() +"\\result" + str(filenumber)+".svg", 'w') as file:
                file.write("<svg width=\""+str(widthmm)+"mm\" height=\""+str(heightmm)+"mm\" viewBox=\"0 0 "+str(widthmm)+" "+str(heightmm)+ "\">")
                file.write(sodipodi)

                for i in pathbatch:
                        #file.write(";id="+str(i[2])+" pathindex="+str(pathindex)+" filenumber "+str(filenumber))
                        file.write("\n<path \n")
                        file.write("style=\""+i[1]+"\"\n")
                        file.write("d=\""+i[0]+"\"\n")
                        file.write("id=\""+i[2] + "\"\n")
                        print("id = ", i[2], "filenumber = ", filenumber)
                        file.write("inkscape:connector-curvature=\""+i[3] + "\"\n")
                        file.write(" />")

                file.write("</svg>")
                filenumber +=1
        print("Finished !")
        path_elements = doc.getElementsByTagName('path')
        doc.unlink()

    if mode=="similartogether":
        print("Total elements = ",len(pathlist))
        floorrange = math.floor(len(pathlist) / subfilesnumber)
        exceedent = len(pathlist) - (floorrange * subfilesnumber)
        print("Excédent ",exceedent)
        for filenumber in range(subfilesnumber):
            start = filenumber*floorrange
            end = filenumber*floorrange + floorrange
            if filenumber == subfilesnumber - 1:
                end = len(pathlist)
            pathbatch = pathlist[start:end]
            print("start",start,"end",end)
            with open(os.getcwd() +"\\result" + str(filenumber)+".svg", 'w') as file:
                file.write("<svg width=\""+str(widthmm)+"mm\" height=\""+str(heightmm)+"mm\" viewBox=\"0 0 "+str(widthmm)+" "+str(heightmm)+ "\">")
                file.write(sodipodi)

                for i in pathbatch:
                        #file.write(";id="+str(i[2])+" pathindex="+str(pathindex)+" filenumber "+str(filenumber))
                        file.write("\n<path \n")
                        file.write("style=\""+i[1]+"\"\n")
                        file.write("d=\""+i[0]+"\"\n")
                        file.write("id=\""+i[2] + "\"\n")
                        file.write("inkscape:connector-curvature=\""+i[3] + "\"\n")
                        file.write(" />")

                file.write("</svg>")
        print("Finished !")
        path_elements = doc.getElementsByTagName('path')
        doc.unlink()
sizeinkb = int(input("Max Size in kb\n"))
splitsvg(subfilesnumber=10,maxsizeinkb=sizeinkb)
