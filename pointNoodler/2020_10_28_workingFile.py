import maya.cmds as cmds
import maya.OpenMaya as om
import pointNoodler as pm

cmds.polyCube(w = 4, d = 4, sx = 4, sy = 2, sz = 4)

reload(pm)
pm.deleteNoodles()
masterList = pm.getPointDictFromEdges()
keyLength = len(masterList.keys())
print keyLength
print masterList.items()[0][0]
print masterList.items()[0][1]
print "pointList length = " + str(len(masterList.items()[0][1]))

masterList = pm.getPointListFromEdges()
keyLength = len(masterList.keys())
for index in xrange(keyLength):
    pointList = masterList.items()[index][1]
    parentName = masterList.items()[index][0]
    pm.pointNoodler(pointList, 0.1, parentName)

 