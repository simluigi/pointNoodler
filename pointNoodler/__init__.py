
"""
-- pointNoodler plugin --
Author          : Sim Luigi
Last Modified   : 2020.10.16

End goal is to make a plugin that generates a 'noodle' (cylinder) that traverses any number of given points.
   (noodles sounds more fun than polyCylinder, right?) 

Benchmarks:
-Derive numSections of noodle given the pointList.          (complete as of 2020.10.13)
-Generate a noodle with the appropriate # of sections.      (complete as of 2020.10.13)
-Align the noodle with the given pointList.                 (complete as of 2020.10.14)
-Average out vertex data for smoother segments.             (complete as of 2020.10.15)
-Extract selected edges (kMeshEdgeComponent)                (complete as of 2020.10.15)
-Store selected edge/s' data (MFnSingleIndexedComponent)    (complete as of 2020.10.15) 

-Extract points from edge data                              (needs revisions as of 2020.10.16)  -> getPointListFromEdges()
-Delete duplicate points                                    (needs revisions as of 2020.10.16)  -> removeDuplicatePoints()

-Add radius of 'noodle' as argument to be passed            (complete as of 2020.10.16)

-Implement base pointNoodler()                              (needs revisions as of 2020.10.16)
 * revert argument type to list instead of MPointArray
 * instead of MItMeshEdge, use om.MFnMesh(dagPath)
 * currently only works if points are in sequence on the X-axis
"""

import maya.cmds as cmds
import maya.OpenMaya as om
import pprint

# removing all other arguments until I can get it right and then understand the meaning & implementation of the original arguments (upVecList, parent)
def pointNoodler(pointList, radius, upVecList=None):    

    # error handling: check if there are enough points to make at least 1 section
    if pointList.length() -1 < 2:
        raise Exception ("Need at least 2 points to perform pointNoodler!")
    
    numSections = pointList.length() -1        # -1 : minus the cap
    mod = float( numSections / 2.0 ) 

    # creating noodle with appropriate number of sections
    noodleTr = createNoodle(numSections, radius)                    # noodle Transform
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
    
    matrix = om.MMatrix()
    oldI = om.MVector()
    oldJ = om.MVector()
    oldK = om.MVector()

    for section in xrange(numSections): 
        o = pointList[section]              # maya.OpenMaya.MPoint
        i = pointList[section+1] - o        # maya.OpenMaya.MVector
        i.normalize()                   
        u = (upVecList[section] if upVecList is not None else om.MVector(0, 1, 0))      # default to up-Y if no upVector is provided
        k = i ^ u
        j = k ^ i         

        if section > 0:
            avgI = (i + oldI).normal()
            avgJ = (j + oldJ).normal()
            avgK = (k + oldK).normal()

        else:
            avgI = i
            avgJ = j
            avgK = k

        # plugs in all the values from vectors/points and generates a 4x4 matrix
        # matrix = om.MMatrix()
        om.MScriptUtil.createMatrixFromList( (avgI.x, avgI.y, avgI.z, 0, avgJ.x, avgJ.y, avgJ.z, 0, avgK.x, avgK.y, avgK.z, 0, o.x, o.y, o.z, 0), matrix)

        # translate points HERE
        for index in sectionIndices[section]:       # error when using a pointList with an even number of elements (-1 : odd number of sections)
            p = noodlePoints[index]                
            p.x = 0
            noodlePoints.set(p * matrix, index)

        # save old matrix data for multiplying next step
        oldI = i
        oldJ = j
        oldK = k

    # translate final points (cap) HERE   
    o = pointList[numSections]              
    i = oldI
    u = om.MVector(0, 1, 0)                  
    k = i ^ u
    j = k ^ i     
    om.MScriptUtil.createMatrixFromList( (i.x, i.y, i.z, 0, j.x, j.y, j.z, 0, k.x, k.y, k.z, 0, o.x, o.y, o.z, 0), matrix) 

    for index in sectionIndices[numSections]:     
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
    comp = om.MObject()
    try:
        lst.getDagPath(0, dagPath, comp)
        return dagPath, comp
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

# basic function for getting pointList from selected edges
def getPointListFromEdges():
    sel = om.MSelectionList()
    obj = om.MObject()
    om.MGlobal.getActiveSelectionList(sel)
    sel.getDependNode(0, obj)    

    comp = om.MObject()
    dag = om.MDagPath()
    sel.getDagPath(0, dag, comp)
    
    # error handling: if selected components are edges or not
    if comp.apiTypeStr() != "kMeshEdgeComponent":
        raise Exception ("Selected component/s are not of type kMeshEdgeComponent. Are you in edge selection mode and have selected at least 1 edge?")   
    else:
        edges = om.MFnSingleIndexedComponent(comp)
        edgeCount = edges.elementCount()        
        print ("Number of edges selected: ") + str(edgeCount)

    # MItMeshEdge implementation
    pointList = om.MPointArray()
    edgeIndices = om.MIntArray()
    edges.getElements(edgeIndices)
    print "edge Indices: " + str(edgeIndices)
        
    edgeIt = om.MItMeshEdge(obj)
    while not edgeIt.isDone():
        for count in xrange(edgeCount):
            if edgeIt.index() == edges.element(count):
                pointList.append(edgeIt.point(0))
                pointList.append(edgeIt.point(1))
        edgeIt.next()

    # return resulting pointList after eliminating duplicate points
    removeDuplicatePoints(pointList)
    return pointList
        
# remove duplicate points (for now, assuming points are selected in sequence)
def removeDuplicatePoints(pointList):
    len = pointList.length()
    removeList = om.MIntArray()  

    # compare if current point and next point are the same (except on first and last point)
    for index in xrange(len):
        if index > 1 and index < pointList.length(): 

            next = index + 1
            nextX = pointList[next][0]
            nextY = pointList[next][1]
            nextZ = pointList[next][2]
            
            X = pointList[index][0]
            Y = pointList[index][1]
            Z = pointList[index][2]
            
            # if they are the same point, add the previous point to the list of points to be removed
            if X == nextX and Y == nextY and Z == nextZ:
                print "point # " + str(index) + " flagged for removal." 
                removeList.append(index)

    # finally, remove points to be removed
    rlen = removeList.length()
    for index in xrange(rlen):
        pointList.remove(removeList[index])
        print "point removed at coordinates " + str(pointList[index][0]) + ", " + str(pointList[index][1]) + ", " + str(pointList[index][2]) 

# print matrix contents for debugging
def printMatrix(matrix):
    result = '% .06f, % .06f, % .06f, % .06f,\n% .06f, % .06f, % .06f, % .06f,\n% .06f, % .06f, % .06f, % .06f,\n% .06f, % .06f, % .06f, % .06f,\n'
    print result % (matrix(0, 0), matrix(0, 1), matrix(0, 2), matrix(0, 3), matrix(1, 0), matrix(1, 1), matrix(1, 2), matrix(1, 3), matrix(2, 0), matrix(2, 1), matrix(2, 2), matrix(2, 3), matrix(3, 0), matrix(3, 1), matrix(3, 2), matrix(3, 3))

# delete existing noodles(cylinders)
def deleteNoodles():
    """Deletes existing "cylinder"/s (if any)"""
    noodleList = cmds.ls('pNoodle*')     
    if len(noodleList) > 0:               
        cmds.delete (noodleList)      

# create base noodle (cylinder) with arguments numSections (each section with a unit length of 1) and rad (cylinder radius)
def createNoodle(numSections, rad):
    """Creates the base cylinder. Accepts numSections.  Set height of each section as 1, thus making height = y-subdivisions = numSections."""
    result = cmds.polyCylinder( radius = rad, axis = [1, 0, 0], height = numSections , sy = numSections, name = 'pNoodle#' )
    print 'result: ' + str( result )
    return result