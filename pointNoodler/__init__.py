"""
-- pointNoodler plugin --
Author          : Sim Luigi
Last xOffsetified   : 2020.11.23

End goal is to make a plugin that generates a 'noodle' (cylinder) that traverses any number of given points across any number of meshes.
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
-Parenting the noodles properly (to align with parent)      (needs revision as of 2020.10.28 - check for dagPath etc.)  
-Segregation of edge pointrconnections into lists           (in progress as of 2020.10.28) 
    Remaining Tasks:
    * combining connected edge lists that were not connected during generation (complete as of 2020.10.28)
    * work across multiple meshes (in progress)
-Get the upVecList                                          (in progress as of 2020.10.28 - functionality currently included in segregatePointIndices())

*******Current Task:   (in progress as of 2020.11.23)
-Implement parameters as class to eliminate unnecessary list nesting 
and handle data management better  

"""
import maya.cmds as cmds
import maya.OpenMaya as om
import pprint

# 2020.11.23: instanced per generated cylinder, not sure yet how to proceed
class Noodle:                                       
    def __init__(self, pointList, radius, parent):
        
        self.m_ID = 0

        self.m_PointList = pointList
        self.m_Radius = radius
        self.m_Parent = parent

        self.m_Object   # ? not sure what to do here yet
        self.m_DagPath
        self.m_Component

        self.mEdgeIDs = []
        self.mPointList = []

# removing all other arguments until I can get it right and then understand the meaning & implementation of the original arguments (upVecList, parent)
# def pointNoodler(index, pointList, radius, parent, upVectorList=None):
def pointNoodler(pointList, radius, parent, upVectorList=None):

    # error handling 1: check if there are enough points to make at least 1 section
    if len(pointList)  < 2:
        raise Exception ("Need at least 2 points to perform pointNoodler!")

    # error handling 2: check if radius is valid (float or int)
    if (type(radius) is not float) and (type(radius) is not int):
        raise Exception ("Specified radius is invalid!  Please enter a float or int value.")

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
        for index in sectionIndices[section]: 
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
def getMDagPath(index, sel):
    dagPath = om.MDagPath()
    comp = om.MObject()
    try:
        sel.getDagPath(index, dagPath, comp)
        return dagPath, comp
    except:
        print ("Unable to get MDagPath. Have you selected an appropriate node?")
        raise

def getMObject(node, obj):
    lst = om.MSelectionList()    
    lst.add(node)
    try:
        return lst.getDependNode(0, obj)
    except:
        print ("Unable to get MObject. Have you selected an appropriate node?")
        raise

def getParentNameFromSelection(index, sel):
    dagPath = om.MDagPath()
    comp = om.MObject()
    try:
        sel.getDagPath(index, dagPath, comp)
        parentName = dagPath.fullPathName()
        return parentName
    except:
        print ("Unable to get parent name from selection. Have you selected an appropriate node?")
        raise

# function for getting point indices from selected edges, segregated into their corresponding segments if edges are not connected
# and combined per mesh (paired by parent name)
def getPointDictFromEdges():
    masterPointDict = {}
    edgeSelection = om.MSelectionList()
    om.MGlobal.getActiveSelectionList(edgeSelection)
    selLength = edgeSelection.length()
 
    # error handling: no selection
    if edgeSelection.isEmpty():
        raise Exception ("Nothing is selected!")

    for index in xrange(selLength):
        edgeDagPath, edgeComponent = getMDagPath(index, edgeSelection)
        edgeObject = om.MObject()
        edgeSelection.getDependNode(index, edgeObject)   

        # error handling: invalid selections
        if not edgeDagPath.isValid():
            raise Exception ("Invalid DAG Path. Have you selected an appropriate node?")   # expound on this later
        if edgeComponent.apiTypeStr() != "kMeshEdgeComponent":
            raise Exception ("Selected component/s are not of type kMeshEdgeComponent. Are you in edge selection xOffsete and have selected at least 1 edge?") 
        if edgeObject.isNull():
            raise Exception ("Resulting MObject returned a null value.  Have you selected an appropriate node?")

        parentName = edgeDagPath.fullPathName()        
        edgeMesh = om.MFnMesh(edgeDagPath)  
        edgeSIComponent = om.MFnSingleIndexedComponent(edgeComponent)
        edgeCount = edgeSIComponent.elementCount() 
        edgeIndices = om.MIntArray() 
        edgeSIComponent.getElements(edgeIndices)        # returns all indices of selected edges

        segregatedList = getSegregatedPointIndices(edgeMesh, edgeIndices, edgeCount)    # get a list of lists with edgeIndices grouped by connected edges
        lst = masterPointDict.get(parentName, [])                       
        nodePointList = getPointMasterList(edgeMesh, segregatedList)
        lst.append(nodePointList)                                                # list of lists of MPoints grouped by segregatedList

        masterPointDict[parentName] = lst

    pprint.pprint(masterPointDict)    
    return masterPointDict

# segregate point indices into respective lists based on edge connection
def getSegregatedPointIndices(edgeMesh, edgeIndices, edgeCount):    
    edgeUtil = om.MScriptUtil()
    edgeVertices = edgeUtil.asInt2Ptr()
    segregatedList = []                     # entry format: [[connected Edge/s], [connected Points]]
    listCount = 0                           # final number of point lists
    pointNrms = {}                          # dictionary of upVectors (normals)

    # consolidated into one for loop (split as you go). 
    # Take into account every possible case i.e. point lists connected to each other, multiple meshes    
    for index in xrange(edgeCount):
        edgeID = edgeIndices[index]
        edgeMesh.getEdgeVertices(edgeID, edgeVertices)
        inP0 = edgeUtil.getInt2ArrayItem(edgeVertices, 0, 0)    # p0 index
        inP1 = edgeUtil.getInt2ArrayItem(edgeVertices, 0, 1)    # p1 index

        # creating dictionary of normals
        if not inP0 in pointNrms:
            N = om.MVector()
            edgeMesh.getVertexNormal(inP0, True, N)
            pointNrms[inP0] = N
        if not inP1 in pointNrms:
            N = om.MVector()
            edgeMesh.getVertexNormal(inP1, True, N)
            pointNrms[inP1] = N

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
                    break
                elif inP1 == headPoint:                             # case 2: incoming p1 matches head of existing list
                    currentEdgeIndices.insert(0, edgeID)            # add edgeID to list of connected edges
                    currentPoints.insert(0, inP0)                   # insert partner to head (inP0, head, ...) - p0 is now head of list
                    break
                elif inP0 == tailPoint:                             # case 3: incoming p0 matches tail of existing list
                    currentEdgeIndices.append(edgeID)               # add edgeID to list of connected edges
                    currentPoints.append(inP1)                      # insert partner to tail (..., tail, p1) - p1 is now tail of list
                    break                               
                elif inP1 == tailPoint:                             # case 4: incoming p1 matches tail of existing list
                    currentEdgeIndices.append(edgeID)               # add edgeID to list of connected edges
                    currentPoints.append(inP0)                      # insert partner to tail (..., tail, p0) - p0 is now tail of list 
                    break   
                else:
                    if inP0 in currentPoints or inP1 in currentPoints:      # case 5: either p1 or p0 is somewhere in the middle of existing list
                        segregatedList.append([[edgeID], [inP0, inP1]])     # create a new point list entry (as a T-section of the shared point)
                        listCount += 1
                        break
            else:
                segregatedList.append([[edgeID], [inP0, inP1]])     # case 6: edge's points are not connected anywhere
                listCount += 1                                   # create a new independent point list entry 

    # connecting point lists with shared endpoints
    # Note: duplicate edges have already been removed in previous step so no need to check for them again below
    outList = segregatedList[:]      
    outIndex = 0                         
    compIndex = 0                        
    listLength = len(outList)

    while outIndex + 1 < listLength:            # skip first entry (no need to compare with itself)
        # helper variables
        isMerged = False
        compIndex = outIndex + 1                # compare current entry to next

        outPoints = outList[outIndex][1]
        outEdgeIndices = outList[outIndex][0]    
        compPoints = outList[compIndex][1]
        compEdgeIndices = outList[compIndex][0]
   
        outHead = outList[outIndex][1][0]
        outTail = outList[outIndex][1][-1]
        compHead = outList[compIndex][1][0]
        compTail = outList[compIndex][1][-1]

        while compIndex < listLength:
            if outHead == compHead and outTail == compTail:                     # test for duplicate/looping points
                l0 = set(outPoints)                                                     
                l1 = set(compPoints)
                if l0 == l1:
                    # case 0: duplicate set of points, skip entry 
                    break
                else:                                                
                                                                                # case 1: (edge case) points connected in a loop (essentially closing the loop)                                                                                
                    compPoints.reverse()                                        # reverse the order of the points to be added 
                    compEdgeIndices.reverse()                                   # reverse the order of the edge indices to be added               
                    outPoints[:0] = compPoints[:-1]                             # insert the contents of the incoming points in reverse order in front (must add at least either head or tail to close the loop)                                
                    outEdgeIndices[:0] = compEdgeIndices                        # insert the associated edge indices in front in reverse order
                    isMerged = True
                break 

            if outHead == compHead:                         # case 2: current head connected to opposing head                                 
                compPoints.reverse()                        # reverse the order of the points to be added 
                compEdgeIndices.reverse()                   # reverse the order of the edge indices to be added    
                outPoints[:0] = compPoints[:-1]             # insert the contents of the incoming points in reverse order in front, excluding the connected point at the last index
                outEdgeIndices[:0] = compEdgeIndices[:]     # insert the associated edge indices in front in reverse order     
                isMerged = True
                break

            # working
            elif outHead == compTail:                       # case 3: current head connected to opposing tail         
                outPoints[:0] = compPoints[:-1]             # insert the contents of the incoming points in reverse order in front, excluding the connected point at the last index
                outEdgeIndices[:0] = compEdgeIndices[:]     # insert the associated edge indices in front  
                isMerged = True
                break

            # working
            elif outTail == compHead:                       # case 4: current tail connected to opposing head
                print compPoints[1:] 
                outPoints.extend(compPoints[1:])            # extend the output list by the incoming list, excluding the connected point at the first index
                outEdgeIndices.extend(compEdgeIndices[:] )  # extend the output edge indices by the associated incoming edge indices
                isMerged = True
                break

            # working    
            elif outTail == compTail:                       # case 5: current tail connected to opposing tail                
                compPoints.reverse()                        # reverse the order of the points to be added 
                compEdgeIndices.reverse()                   # reverse the order of the edge indices to be added  
                outPoints.extend(compPoints[1:])            # extend the output list by the reversed incoming list, excluding the connected point at the first index
                outEdgeIndices.extend(compEdgeIndices[:] )  # extend the output edge indices by the associated incoming edge indices   
                isMerged = True
                break
            else:
                compIndex += 1              # if no matching cases are found, proceed with next iteration

        if isMerged == True:                        
            outList.pop(compIndex)          # remove old list entry that has already been merged (both edge indices and points list)
            listLength = len(outList)       # update the list length
            outIndex = 0                    # start again from the beginning
        else:
            outIndex += 1                   # proceed to next entry

    print "final output list: " + str(outList)

    # return outList, pointNrms
    return outList  # list of lists of each noodle's point indices

# create master list of all points grouped by passed segregatedList
def getPointMasterList(edgeMesh, segregatedList):
    masterList = []
    for index in xrange(len(segregatedList)):        
        for i in xrange(len(segregatedList[index][1])):
            point = om.MPoint()
            edgeMesh.getPoint(segregatedList[index][1][i], point)                     
            masterList.append(point)
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