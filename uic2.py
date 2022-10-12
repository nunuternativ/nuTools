import sys, os
import pyside2uic 


inFile = sys.argv[1]

outFile = inFile.replace(".ui", ".py")
pyFile = open(outFile, "w")
try:
    pyside2uic.compileUi(inFile, pyFile, False, 4, False)
except Exception, e:
    print e
    # print("Failed. Invalid file name:\n{0}".format(inFile))
    raise
else:
    print("Success! Result: {0}".format(outFile))
finally:
    pyFile.close()