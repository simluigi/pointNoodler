import maya.cmds as cmds
import maya.OpenMaya as om
import pointNoodler as pm

cmds.polyCube(w = 4, d = 4, sx = 4, sy = 2, sz = 4)

reload(pm)
pm.deleteNoodles()
masterList = pm.getPointDictFromEdges()
keyLength = len(masterList.keys())
print keyLength

for index in xrange(keyLength):
    pointList = masterList.items()[index][1][0]
    print "pointList length = " + str(len(pointList))
    parentName = masterList.items()[index][0]
    pm.pointNoodler(pointList, 0.1, parentName)

 