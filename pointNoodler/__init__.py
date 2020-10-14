
"""
-- pointNoodler plugin --
Author          : Sim Luigi
Last Modified   : 2020.10.14

End goal is to make a plugin that generates a 'noodle' (thin cylinder) that traverses any number of given points.
   (noodles sounds more fun than polyCylinder, right?) 

Benchmarks:
-Derive numSections of noodle given the pointList.      (complete as of 2020.10.13)
-Generate a noodle with the appropriate # of sections.  (complete as of 2020.10.13)
-Align the noodle with the given pointList.             (in progress as of 2020.10.14)

"""
import maya.cmds as cmds
import maya.OpenMaya as om
import pprint

# removing all other arguments until I can get it right and then understand the meaning & implementation of the original arguments (upVecList, parent)
def pointNoodler(pointList):    

    numSections = len(pointList) -1        # -1 : minus the cap
    mod = float( numSections / 2.0 ) 

    noodleTr = createNoodle(numSections)                    # noodle Transform
    noodle = cmds.listRelatives(noodleTr, shapes=1)[0]      # returns the shape under noodleTr
    objNoodle = om.MObject()
    getMObject(noodle, objNoodle)
    meshNoodle = om.MFnMesh(objNoodle)

    # store all vertices and group by corresponding X value (consider making into a function)
    sectionIndices = {} 

    vit = om.MItMeshVertex(objNoodle)       # iterator of all vertices in mesh
    while not vit.isDone():
        p = vit.position()                  # position of vertex
        k = p.x + mod                       # rounds p to the nearest decimal digit and converts to int format
        lst = sectionIndices.get(k, [])     # add list to key(all points that share the same x-axis)
        lst.append(vit.index())             # appends index of vit to the list
        sectionIndices[k] = lst             # sets this list as the value of sectionIndices[with index k]
        vit.next()                          # moves to the next element in the list

    noodlePoints = om.MPointArray()
    meshNoodle.getPoints(noodlePoints)      # gets all the points in the noodle -mesh- (not node or object) and assigns to noodlePoints(type MPointArray)

    for section in xrange(numSections): 
        o = pointList[section]              # maya.OpenMaya.MPoint
        i = pointList[section+1] - o        # maya.OpenMaya.MVector
        i.normalize()                   
        u = om.MVector(0, 1, 0)             # default to up-Y 
        k = i ^ u
        j = k ^ i         

        # plugs in all the values from vectors/points and generates a 4x4 matrix
        matrix = om.MMatrix()
        om.MScriptUtil.createMatrixFromList( (i.x, i.y, i.z, 0, j.x, j.y, j.z, 0, k.x, k.y, k.z, 0, o.x, o.y, o.z, 0), matrix)

        # translate points HERE
        for index in sectionIndices[section]:       # error when using a pointList with an even number of elements (-1 : odd number of sections)
            p = noodlePoints[index]                
            p.x = 0
            noodlePoints.set(p * matrix, index)

    # translate final points (cap) HERE    
    for index in sectionIndices[numSections]:     
        o = pointList[numSections]              
        i = om.MVector (pointList[numSections])          # no more +1 since final section  
        i.normalize()                 
        u = om.MVector(0, 1, 0)                  
        k = i ^ u
        j = k ^ i         

        # plugs in all the values from vectors/points and generates a 4x4 matrix
        matrix = om.MMatrix()
        om.MScriptUtil.createMatrixFromList( (i.x, i.y, i.z, 0, j.x, j.y, j.z, 0, k.x, k.y, k.z, 0, o.x, o.y, o.z, 0), matrix)   

        p = noodlePoints[index]
        p.x = 0 
        noodlePoints.set(p * matrix, index)   

    # finally, set the points of the generated noodle to align to the matrix
    meshNoodle.setPoints(noodlePoints) 


"""
helper functions
"""

# basic DAG path and Depend Node getter functions
def getMDagPath(node):
    lst = om.MSelectionList()
    lst.add(node)
    dagPath = om.MDagPath()
    try:
        lst.getDagPath(0, dagPath)
        return dagPath
    except:
        print ("Unable to get MDagPath. Have you specified an appropriate node?")
        raise

def getMObject(node, obj):
    lst = om.MSelectionList()
    lst.add(node)
    try:
        return lst.getDependNode(0, obj)
    except:
        print ("Unable to get MObject. Have you specified an appropriate node?")
        raise

def printMatrix(matrix):
    result = '% .06f, % .06f, % .06f, % .06f,\n% .06f, % .06f, % .06f, % .06f,\n% .06f, % .06f, % .06f, % .06f,\n% .06f, % .06f, % .06f, % .06f,\n'
    print result % (matrix(0, 0), matrix(0, 1), matrix(0, 2), matrix(0, 3), matrix(1, 0), matrix(1, 1), matrix(1, 2), matrix(1, 3), matrix(2, 0), matrix(2, 1), matrix(2, 2), matrix(2, 3), matrix(3, 0), matrix(3, 1), matrix(3, 2), matrix(3, 3))

def deleteNoodles():
    """Deletes existing "cylinder"/s (if any)"""
    noodleList = cmds.ls('pNoodle*')     
    if len(noodleList) > 0:               
        cmds.delete (noodleList)      

# 2020.10.09: removed origin offset, relegated to transform matrix in edgeMesher
def createNoodle(numSections):
    """Creates the base cylinder. Accepts numSections.  Set height of each section as 1, thus making height = y-subdivisions = numSections."""
    result = cmds.polyCylinder( radius = 0.1, axis = [1, 0, 0], height = numSections , sy = numSections, name = 'pNoodle#' )
    print 'result: ' + str( result )
    return result