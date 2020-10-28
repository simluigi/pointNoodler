# temp working file
import maya.cmds as cmds
import maya.OpenMaya as om
import pointNoodler as pm

cmds.polyCube(w = 4, d = 4, sx = 4, sy = 2, sz = 4)

reload(pm)
pm.deleteNoodles()

# old working code: does not take into consideration multiple meshes
masterList = pm.getPointListFromEdges(0)
sel = om.MSelectionList()
om.MGlobal.getActiveSelectionList(sel)
parentName = pm.getParentNameFromSelection(0, sel)

for index in xrange(len(masterList)):
    for i in xrange (len(masterList[index])):
        pm.pointNoodler(masterList[index][i], 0.1, parentName)


# revised code, but still not working
sel = om.MSelectionList()
om.MGlobal.getActiveSelectionList(sel)
selLength = sel.length()
dagPath = om.MDagPath()
comp = om.MObject()
for index in xrange(selLength):
    dagPath, comp = pm.getMDagPath(index, sel)
    parentName = pm.getParentNameFromSelection(index, sel)
    masterList = pm.getPointListFromEdges(index)
    print parentName
    print len(masterList[index][0])
    pm.pointNoodler(masterList[index][0], 0.1, parentName)
        
        