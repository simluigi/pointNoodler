"""
-- pointNoodler plugin --
Author          : Sim Luigi
Last xOffsetified   : 2020.10.27

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
-Implement base pointNoodler() with multiple cylinders      (complete as of 2020.10.21)
-Extract points from edge data                              (complete as of 2020.10.21)
-Parenting the noodles properly (to align with parent)      (complete as of 2020.10.23)  * inquire about "cannot parent components or objects in the underworld"
-Segregation of edge connections into respective lists      (in progress as of 2020.10.26) 
    Remaining Tasks:
    * combining connected edge lists that were not connected during generation
    * work across multiple DAG nodes
-Get the upVecList                                          (incomplete as of 2020.10.23)

"""
import maya.cmds as cmds
import maya.OpenMaya as om

# removing all other arguments until I can get it right and then understand the meaning & implementation of the original arguments (upVecList, parent)
def pointNoodler(pointList, radius, parent, upVectorList=None):

    # error handling: check if there are enough points to make at least 1 section
    if len(pointList)  < 2:
        raise Exception ("Need at least 2 points to perform pointNoodler!")
    
    numSections = len(pointList) - 1        # -1 : minus the cap
    xOffset = float(numSections / 2.0)

    # creating noodle with appropriate number of sections
    noodleTransform = createNoodle(numSections, radius)
    cmds.parent(noodleTransform, parent, relative=True)
    noodle = cmds.listRelatives(noodleTransform, shapes = 1)[0] # returns the shape under noodle (pNoodle#Shape)

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
        u = (upVectorList[section] if upVectorList is not None else om.MVector(0, 1, 0))      # default to world upVector if no upVector is provided
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

    indexCount = edgeSelection.length()   
    masterList = []

    """
    JUST MAKING IT WORK IS NOT ENOUGH
    function must think about all ins and outs, all use cases (what the user will do with your tool, you will never anticipate)
    assumptions are visible in naming conventions (you're assuming the selection is a node, etc)
    gives useful feedback, etc

    change node with index; misleading (node - dependNode, index - more suitable)
    Do error handling - check if valid dagPath, then check if mesh is valid (NURBS, etc), check if in object mode, etc
    Stop making assumptions regarding input types

    dont stop a program for a single exception if it doesn't warrant an error (try-catch)
    robust: tell people why plugin is failing all the time
    """

    # use your getMDagPath and getMObject here!!!

    for index in xrange(indexCount):              # perform point selection per index 
        edgeComponent = om.MObject()
        edgeDagPath = om.MDagPath()
        edgeSelection.getDependNode(index, edgeObject)                 
        edgeSelection.getDagPath(index, edgeDagPath, edgeComponent)

        # error handling
        if not edgeDagPath.isValid():
            raise Exception ("Invalid DAG Path!")   # expound on this later
        if edgeComponent.apiTypeStr() != "kMeshEdgeComponent":
            raise Exception ("Selected component/s are not of type kMeshEdgeComponent. Are you in edge selection xOffsete and have selected at least 1 edge?")   

        edgeMesh = om.MFnMesh(edgeDagPath)   
        edgeSIComponent = om.MFnSingleIndexedComponent(edgeComponent)
        edgeCount = edgeSIComponent.elementCount() 
        edgeIndices = om.MIntArray() 
        edgeSIComponent.getElements(edgeIndices)        # returns all indices of selected edges
    
        segregatedList = getSegregatedPointIndices(edgeMesh, edgeIndices, edgeCount)    # get a list of lists with edgeIndices grouped by connected edges
        nodePointList = getPointMasterList(edgeMesh, segregatedList)
        masterList.append(nodePointList)                                                # list of lists of MPoints grouped by segregatedList

    return masterList   


"""
2020.10.26: 
List segregation more or less complete.
Remaining task is to combine lists that were not connected during generation.
Current approach is to traverse the segregated list and compare their head/tail index values
and then add respective points if a match is found.  However, algorithm is not complete.
"""

# segregate point indices into respective lists based on edge connection
def getSegregatedPointIndices(edgeMesh, edgeIndices, edgeCount):    
    edgeUtil = om.MScriptUtil()
    edgeVertices = edgeUtil.asInt2Ptr()
    segregatedList = []                     # entry format: [[connected Edge/s], [connected Points]]
    listCount = 0                           # final number of point lists
    pointNrms = {}

    # consolidated into one for loop (split as you go). 
    # Take into account every possible case i.e. point lists connected to each other, multiple meshes    
    for index in xrange(edgeCount):
        edgeID = edgeIndices[index]
        edgeMesh.getEdgeVertices(edgeID, edgeVertices)
        inP0 = edgeUtil.getInt2ArrayItem(edgeVertices, 0, 0)    # p0 index
        inP1 = edgeUtil.getInt2ArrayItem(edgeVertices, 0, 1)    # p1 index

        if not inP0 in pointNrms:
            N = om.MVector()
            edgeMesh.getVertexNormal(inP0, True, N)
            pointNrms[inP0] = N
        if not inP1 in pointNrms:
            N = om.MVector()
            edgeMesh.getVertexNormal(inP1, True, N)
            pointNrms[inP1] = N

        print "Current Edge ID " + str(edgeID) + " at Index: " + str(index)

        # if edge exists anywhere inside any of the lists so far, skip to next edge
        for cidx in xrange(len(segregatedList)):
            if edgeID in segregatedList[cidx][0]:
                break
        else:
            for current in xrange(len(segregatedList)):
                # helper local variables
                pointTailIndex = len(segregatedList[current][1]) - 1        # index of the tail (last value) of the current point list to be compared to
                headPoint = segregatedList[current][1][0]                   # current head point (type: int)
                tailPoint = segregatedList[current][1][pointTailIndex]      # current tail point (type: int)
                currentPoints = segregatedList[current][1]                  # list of all point indices in current list to be compared  (type: list of ints)
                currentEdgeIndices = segregatedList[current][0]             # list of current edge indices in list to be compared to  (type: list of ints)
 
                if inP0 == headPoint:                               # case 1: incoming p0 matches head of existing list
                    currentEdgeIndices.insert(0, edgeID)            # add edgeID to list of connected edges
                    currentPoints.insert(0, inP1)                   # insert partner to head (inP1, head, ...) - p1 is now head of list
                    print "Connection found at point p0 to head."
                    break
                elif inP1 == headPoint:                             # case 2: incoming p1 matches head of existing list
                    currentEdgeIndices.insert(0, edgeID)            # add edgeID to list of connected edges
                    currentPoints.insert(0, inP0)                   # insert partner to head (inP0, head, ...) - p0 is now head of list
                    print "Connection found at point p1 to head."
                    break
                elif inP0 == tailPoint:                             # case 3: incoming p0 matches tail of existing list
                    currentEdgeIndices.append(edgeID)               # add edgeID to list of connected edges
                    currentPoints.append(inP1)                      # insert partner to tail (..., tail, p1) - p1 is now tail of list
                    print "Connection found at point p0 to tail."
                    break                               
                elif inP1 == tailPoint:                             # case 4: incoming p1 matches tail of existing list
                    currentEdgeIndices.append(edgeID)               # add edgeID to list of connected edges
                    currentPoints.append(inP0)                      # insert partner to tail (..., tail, p0) - p0 is now tail of list
                    print "Connection found at point p1 to tail."   
                    break   
                else:
                    if inP0 in currentPoints or inP1 in currentPoints:      # case 5: either p1 or p0 is somewhere in the middle of existing list
                        segregatedList.append([[edgeID], [inP0, inP1]])     # create a new point list entry (as a T-section of the shared point)
                        listCount += 1
                        break
            else:
                segregatedList.append([[edgeID], [inP0, inP1]])     # case 6: edge's points are not connected anywhere
                listCount += 1                                   # create a new independent point list entry 
                print "No connections. Creating new cylinder."

    """
     INCOMPLETE: debugging in progress
    # """
    # connecting point lists with shared endpoints
    outList = segregatedList[:]         
    outIndex = 0                         
    compIndex = 0                        
    listLength = len(outList)
    print "List Length: " + str(listLength)

    while outIndex + 1 < listLength:            # skip first entry (no need to compare with itself)
        # helper variables
        isMerged = False
        compIndex = outIndex + 1                # compare current entry to next 
        outPoints = outList[outIndex][1] 
        compPoints = outList[compIndex][1]      

        outHead = outList[outIndex][1][0]
        outTail = outList[outIndex][1][-1]
        compHead = outList[compIndex][1][0]
        compTail = outList[compIndex][1][-1]

        # debug
        print "outHead: " + str(outHead) + ", outTail: " + str(outTail)
        print "compHead: " + str(compHead) + ", compTail: " + str(compTail)

        while compIndex < listLength:
            print "outIndex: " + str(outIndex)
            print "compIndex: " + str(compIndex)

            if outHead == compHead:         # case 1: current head connected to opposing head
                print "Case 1"
                compPoints.reverse()
                outPoints[:0] = compPoints[:-1]
                print "new points: " + str (outPoints) 
                isMerged = True
                break
            elif outHead == compTail:      # case 2: current head connected to opposing tail      
                print "Case 2"     
                outPoints.extend(compPoints[1:])  
                print "new points: " + str (outPoints) 
                isMerged = True
                break
            elif outTail == compHead:      # case 3: current tail connected to opposing head
                print "Case 3"
                outPoints[:0] = compPoints[:-1]
                print "new points: " + str (outPoints) 
                isMerged = True
                break

            elif outTail == compTail:     # case 4: current tail connected to opposing tail
                print "Case 4"
                compPoints.reverse()
                outPoints.extend(compPoints[1:])
                print "new points: " + str (outPoints) 
                isMerged = True
                break
            else:
                compIndex += 1

        if isMerged == True:
            # listLength = len(outList)
            listLength -= 1
            outIndex = 0
        else:
            outIndex += 1

    print "outList: " + str(outList)
    print "segList: " + str(segregatedList)

    # return outList, pointNrms
    return segregatedList  # list of lists of each noodle's point indices

# create master list of all points grouped by passed segregatedList
def getPointMasterList(edgeMesh, segregatedList):
    masterList = []
    for index in xrange(len(segregatedList)):        
        pointList = []
        for i in xrange(len(segregatedList[index][1])):
            point = om.MPoint()
            edgeMesh.getPoint(segregatedList[index][1][i], point)
            pointList.append(point)           
        masterList.append(pointList)

    return masterList   # list of lists of MPoints segregated into their own divisions

# print matrix contents for debugging
def printMatrix(matrix):
    result = '% .06f, % .06f, % .06f, % .06f,\n% .06f, % .06f, % .06f, % .06f,\n% .06f, % .06f, % .06f, % .06f,\n% .06f, % .06f, % .06f, % .06f,\n'
    print result % (matrix(0, 0), matrix(0, 1), matrix(0, 2), matrix(0, 3), matrix(1, 0), matrix(1, 1), matrix(1, 2), matrix(1, 3), matrix(2, 0), matrix(2, 1), matrix(2, 2), matrix(2, 3), matrix(3, 0), matrix(3, 1), matrix(3, 2), matrix(3, 3))

# delete existing noodles(cylinders)
def deleteNoodles():
    """Deletes existing "cylinder"/s (if any)"""
    noodleList = cmds.ls("pNoodle*")     
    if len(noodleList) > 0:               
        cmds.delete (noodleList)      

# create base noodle (cylinder) with arguments numSections (each section with a unit length of 1), rad (cylinder radius)
def createNoodle(numSections, rad):    
    result = cmds.polyCylinder(radius = rad, axis = [1, 0, 0], height = numSections , sy = numSections, name = "pNoodle#")
    print "result: " + str(result)
    return result