"""
-- pointNoodler plugin --
Author          : Sim Luigi
Last xOffsetified   : 2020.10.21

End goal is to make a plugin that generates a 'noodle' (cylinder) that traverses any number of given points.
   (noodles sounds more fun than polyCylinder, right?) 

Benchmarks:
-Derive numSections of noodle given the pointList.          (complete as of 2020.10.13)
-Generate a noodle with the appropriate # of sections.      (complete as of 2020.10.13)
-Align the noodle with the given pointList.                 (complete as of 2020.10.14)
-Average out vertex data for smoother segments.             (complete as of 2020.10.15)
-Extract selected edges (kMeshEdgeComponent)                (complete as of 2020.10.15)
-Store selected edge/s' data (MFnSingleIndexedComponent)    (complete as of 2020.10.15) 
-Add radius of 'noodle' as argument to be passed            (complete as of 2020.10.16)
-Extract points from edge data                              (complete as of 2020.10.19)     
-Implement base pointNoodler()                              (complete as of 2020.10.21)
    * separation of pointList into separate noodles if the edges are not conected - getPointListFromEdges()
    (now returns a list of lists of MPoints, one list per noodle)
    
-Get the upVecList                                          (incomplete as of 2020.10.19)
    * separate function (
        >> lookAt ^ world up vector (0, 1, 0) = right vector
        >> lookAt ^ right vector = up vector
        >> normalize after

"""

import maya.cmds as cmds
import maya.OpenMaya as om
import pprint

# removing all other arguments until I can get it right and then understand the meaning & implementation of the original arguments (upVecList, parent)
def pointNoodler(pointList, radius, upVecList=None):    

    # error handling: check if there are enough points to make at least 1 section
    if len(pointList)  < 2:
        raise Exception ("Need at least 2 points to perform pointNoodler!")
    
    numSections = len(pointList) -1        # -1 : minus the cap
    xOffset = float(numSections / 2.0) 

    # creating noodle with appropriate number of sections
    noodleTransform = createNoodle(numSections, radius)                    # noodle Transform
    noodle = cmds.listRelatives(noodleTransform, shapes = 1)[0]            # returns the shape under noodleTransform

    objNoodle = om.MObject()
    getMObject(noodle, objNoodle)
    meshNoodle = om.MFnMesh(objNoodle)

    # store all vertices and group by corresponding X value (consider making into a function)
    sectionIndices = {} 

    noodleVertexIterator = om.MItMeshVertex(objNoodle)       # iterator of all vertices in mesh
    while not noodleVertexIterator.isDone():
        p = noodleVertexIterator.position()                  # position of vertex
        xKey = p.x + xOffset                                 # rounds p to the nearest decimal digit and converts to int format
        lst = sectionIndices.get(xKey, [])                   # add list to key(all points that share the same x-axis)
        lst.append(noodleVertexIterator.index())             # appends index of noodleVertexIterator to the list
        sectionIndices[xKey] = lst                           # sets this list as the value of sectionIndices[with index xKey]
        noodleVertexIterator.next()                          # moves to the next element in the list

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
        u = (upVecList[section] if upVecList is not None else om.MVector(0, 1, 0))      # default to world upVector if no upVector is provided
        k = i ^ u   # forward ^ up
        j = k ^ i   # 

        if section > 0:
            avgI = (i + oldI).normal()
            avgJ = (j + oldJ).normal()
            avgK = (k + oldK).normal()

        else:
            avgI = i
            avgJ = j
            avgK = k

        # plugs in all the values from vectors/points and generates a 4x4 matrix
        om.MScriptUtil.createMatrixFromList((avgI.x, avgI.y, avgI.z, 0, avgJ.x, avgJ.y, avgJ.z, 0, avgK.x, avgK.y, avgK.z, 0, o.x, o.y, o.z, 0), matrix)

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
    om.MScriptUtil.createMatrixFromList((i.x, i.y, i.z, 0, j.x, j.y, j.z, 0, k.x, k.y, k.z, 0, o.x, o.y, o.z, 0), matrix) 

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

# function for getting pointList/s from selected edges, segregated into their corresponding segments if edges are not connected
def getPointListFromEdges():
    edgeSelection = om.MSelectionList()
    edgeObject = om.MObject()
    om.MGlobal.getActiveSelectionList(edgeSelection)

    # error handling: no selection
    if edgeSelection.isEmpty():
        raise Exception ("Nothing is selected!")

    edgeSelection.getDependNode(0, edgeObject)    
    edgeComponent = om.MObject()
    edgeDagPath = om.MDagPath()
    edgeSelection.getDagPath(0, edgeDagPath, edgeComponent)
    
    # error handling: if selected components are not edges
    if edgeComponent.apiTypeStr() != "kMeshEdgeComponent":
        raise Exception ("Selected component/s are not of type kMeshEdgeComponent. Are you in edge selection xOffsete and have selected at least 1 edge?")   
    else:
        edgeSIComponent = om.MFnSingleIndexedComponent(edgeComponent)
        edgeCount = edgeSIComponent.elementCount()        
        print ("Number of edges selected: ") + str(edgeCount)

    entryList = []                  # list of lists with format [edgeIndex, edgeP0Index, edgeP1Index]
    segregatedList = []        # entries divided into respective connected pointLists

    edgeIndices = om.MIntArray() 
    edgeSIComponent.getElements(edgeIndices)       # returns all indices of selected edges
    
    # MFnMesh implementation
    edgeMesh = om.MFnMesh(edgeDagPath) 
    edgeUtil = om.MScriptUtil()
    edgeVertices = edgeUtil.asInt2Ptr()

    # first, get all edgeIndices paired with their corresponding points and place in a entryList
    # then add each list as an entry into inputList
    for index in xrange(edgeCount):
        edgeMesh.getEdgeVertices(edgeIndices[index], edgeVertices)
        p0 = edgeUtil.getInt2ArrayItem(edgeVertices, 0, 0)      # p0 index
        p1 = edgeUtil.getInt2ArrayItem(edgeVertices, 0, 1)      # p1 index
        # inputList = [edgeIndices[index], p0, p1]              # [edgeIndex, p0Index, p1Index]
        inputList = [p0, p1]                                    # [p0Index, p1Index]
        entryList.append(inputList)                             # adds current list to entryList
    
    for entry in xrange(edgeCount):           
        if entry == 0:
            segregatedList.append(entryList[entry])         # automatically add first entry to segregated list            
        else:
            isFound = False            
            for i in xrange(len(segregatedList)):                           # test for edge connections (exactly one common vertex)                                               
                if entryList[entry][0] in segregatedList[i]:                # check if p0 is in in one of the lists (meaning edges are connected on incoming p0)
                    segregatedList[i].append(entryList[entry][1])           # if so, add its partner (p1) to that list
                    isFound = True                    
                    break
                if entryList[entry][1] in segregatedList[i]:                # check if p1 is in one of the lists (meaning edges are connected on incoming p1)
                    segregatedList[i].append(entryList[entry][0])           # if so, add its partner (p0) to that list
                    isFound = True
                    break                                                                                 
            if isFound == False:                                            # if not connected to any existing points, create a new entry in masterList designating a new cylinder to be created
                segregatedList.append(entryList[entry])     

    # final conversion of points from their indices 
    masterList = []
    for index in xrange(len(segregatedList)):        
        pointList = []
        for i in xrange(len(segregatedList[index])):
            point = om.MPoint()
            edgeMesh.getPoint(segregatedList[index][i], point)
            pointList.append(point)
            print "point # " + str(segregatedList[index][i]) + " appended to pointList " + str(index) + " with coordinates X: " + str(point[0]) + " Y: " + str(point[1]) + " Z: " + str(point[2])  
        masterList.append(pointList)
        print len(masterList)
    
    return masterList   # list of lists of MPoints segregated into their own divisions

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

# create base noodle (cylinder) with arguments numSections (each section with a unit length of 1), rad (cylinder radius)
def createNoodle(numSections, rad):
    result = cmds.polyCylinder( radius = rad, axis = [1, 0, 0], height = numSections , sy = numSections, name = 'pNoodle#' )
    print 'result: ' + str(result)
    return result