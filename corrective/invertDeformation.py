import math

import maya.cmds as mc
import pymel.core as pm
import maya.OpenMaya as om

from nuTools import misc

TOL = 0.000001

def getShapePoints(shapePath, space=om.MSpace.kObject):
    path = getDagPath(shapePath)
    itGeo = om.MItGeometry(path)
    points = om.MPointArray()
    itGeo.allPositions(points, space)
    return points



def setShapePoints(shapePath, points, space=om.MSpace.kObject):
    path = getDagPath(shapePath)
    itGeo = om.MItGeometry(path)
    itGeo.setAllPositions(points, space)



def getOrigShape(obj):
    shps = obj.getShapes()
    if not shps:
        return
    origShps = []
    for shp in shps:
        intStatus = shp.isIntermediate()
        if 'Orig' in shp.nodeName() or intStatus == True:
            if shp.worldMesh.outputs():
                return shp


def getDagPath(obj):
    try:
        msl = om.MSelectionList()
        msl.add(obj)
        nodeDagPath = om.MDagPath()
        msl.getDagPath(0, nodeDagPath)
    except:
        return None

    return nodeDagPath



def setMatrixRow(matrix, newVector, row):
    setMatrixCell(matrix, newVector.x, row, 0)
    setMatrixCell(matrix, newVector.y, row, 1)
    setMatrixCell(matrix, newVector.z, row, 2)



def setMatrixCell(matrix, value, row, column):
    om.MScriptUtil.setDoubleArray(matrix[row], column, value)
    
def invert(base='', corrective='', name=''):
    '''
    reload(id)
    id.invert()
    mc.blendShape('blendShape1', e=True, tc=0, t=('Shirt_Geo', 1,'Shirt_Geo_inverted', 1) 
    '''
    # get selection
    if not base or not corrective:
        sels = mc.ls(sl=True, l=True, type='transform')
        try:
            base = sels[0]
            corrective = sels[1]
        except:
            om.MGlobal.displayError('Select base mesh follow with corrective mesh.')
            return False

    # find orig shape and the baseShape
    shapes = mc.listRelatives(base, s=True, f=True)
    corrShp = mc.listRelatives(corrective, s=True, f=True, ni=True)[0]

    origShp, baseShp = '', ''
    for shp in shapes:
        intStatus = mc.getAttr('%s.intermediateObject' %shp)
        if intStatus == True or 'Orig' in shp:
            origShp = shp
        else:
            baseShp = shp
    if not origShp:
        om.MGlobal.displayError('Cannot find origShape node.')
        return

    # find skinCluster and other deformers
    hiss = mc.listHistory(base, pruneDagObjects =True, il=1)
    deformerTypes = mc.listNodeTypes('deformer')
    skc, deformers = None, []
    for his in hiss:
        nodeType = mc.nodeType(his)
        if nodeType == 'skinCluster':
            skc = his
        elif nodeType in deformerTypes and nodeType != 'tweak':
            deformers.append(his)
    if not skc:
        om.MGlobal.displayError('Cannot find skinCluster node.')
        return

    # create invert mesh
    invert = mc.duplicate(base)[0]
    if not name:
        name = '%s_inverted' % base.split('|')[-1]
    invert = mc.rename(invert, name)
    # misc.unlockChannelBox(invert)
    if mc.listRelatives(invert, p=True):
        mc.parent(invert, w=True)
        invert = '|%s' %invert.split('|')[-1]

    # delete the unnessary shapes on duplicated invert mesh
    shapes = mc.listRelatives(invert, s=True, f=True)
    for shp in shapes:
        if mc.getAttr('%s.intermediateObject' %shp) == True:
            mc.delete(shp)
        else:
            mc.setAttr('%s.visibility'%shp, True)
    invertShp = mc.listRelatives(invert, s=True, f=True, ni=True)[0]
    invertShpDag = misc.getMDagPath(invertShp)

    # get MDag paths
    baseShpDag = misc.getMDagPath(baseShp)
    origShpDag = misc.getMDagPath(origShp)
    corrShpDag = misc.getMDagPath(corrShp)

    # create geo iterators
    baseItGeo = om.MItGeometry(baseShpDag)
    origItGeo = om.MItGeometry(origShpDag)
    corrItGeo = om.MItGeometry(corrShpDag)
    invItGeo = om.MItGeometry(invertShpDag)

    # the vertex count
    numVtx = baseItGeo.count()
    
    # get orig mesh points
    origPoints = om.MPointArray(numVtx)
    origItGeo.allPositions(origPoints, om.MSpace.kObject)

    # get inputGeometry data in the skinCluster node
    sckMObj = misc.getMObject(skc)
    sckFn = om.MFnDependencyNode(sckMObj)
    mPlug = sckFn.findPlug('input')
    mPlug = mPlug.elementByLogicalIndex(0)
    inputGeomPlug = mPlug.child(0)
    inputGeomMObj = inputGeomPlug.asMObject(om.MDGContext())
    inputMeshFn = om.MFnMesh(inputGeomMObj)
    inputPts = om.MPointArray(numVtx)
    inputMeshFn.getPoints(inputPts, om.MSpace.kObject)

    # get the component offset on all axes for orig shape
    xPoints = om.MPointArray(origPoints)
    yPoints = om.MPointArray(origPoints)
    zPoints = om.MPointArray(origPoints)
    for i in xrange(numVtx):
        xPoints[i].x += 1.0
        yPoints[i].y += 1.0
        zPoints[i].z += 1.0

    # need to turn off other deformers first to move the points
    for node in deformers: mc.setAttr('%s.envelope' %node, 0)
    # get base points
    basePoints = om.MPointArray(numVtx)
    baseItGeo.allPositions(basePoints, om.MSpace.kObject)

    # temporary move the points on each axis and stores the changes
    origItGeo.setAllPositions(xPoints, om.MSpace.kObject)
    baseItGeo.allPositions(xPoints, om.MSpace.kObject)

    origItGeo.setAllPositions(yPoints, om.MSpace.kObject)
    baseItGeo.allPositions(yPoints, om.MSpace.kObject)
    
    origItGeo.setAllPositions(zPoints, om.MSpace.kObject)
    baseItGeo.allPositions(zPoints, om.MSpace.kObject)
    # turn the deformers back on
    for node in deformers: mc.setAttr('%s.envelope' %node, 1)

    # set orig and invert mesh to orig positions
    origItGeo.setAllPositions(origPoints, om.MSpace.kObject)
    invItGeo.setAllPositions(origPoints, om.MSpace.kObject)

    # Get points on corrective mesh
    correctivePoints = om.MPointArray(numVtx)
    corrItGeo.allPositions(correctivePoints, om.MSpace.kObject)

    # Loop over each point
    invPoints = om.MPointArray(origPoints)
    while not invItGeo.isDone():
        i = invItGeo.index()
        delta = (correctivePoints[i] - basePoints[i])
        if (math.fabs(delta.x) < TOL and math.fabs(delta.y) < TOL and math.fabs(delta.z) < TOL):
            invItGeo.next()
            continue

        matrix = om.MMatrix()
        setMatrixRow(matrix, (xPoints[i] - basePoints[i]), 0)
        setMatrixRow(matrix, (yPoints[i] - basePoints[i]), 1)
        setMatrixRow(matrix, (zPoints[i] - basePoints[i]), 2)

        matrix = matrix.inverse()
        offset = delta * matrix
        currPos = invItGeo.position(om.MSpace.kObject)
        pt = currPos + offset
        preDelta = inputPts[i] - origPoints[i] 
        pt -= preDelta # subtract pre deltas
        invPoints.set(pt, i)
        invItGeo.next()

    invItGeo.setAllPositions(invPoints, om.MSpace.kObject)
    return invert