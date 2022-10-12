from collections import defaultdict

import pymel.core as pm
import maya.cmds as mc
import maya.OpenMaya as om
import maya.mel as mel

from nuTools import misc
reload(misc)

from nuTools.util import meshIntersect
reload(meshIntersect)

def getBlendShapeDeltas(blendShapeNode, index=0, geoIndex=0, inbWeight=1.0):
    ittidx = (inbWeight * 1000) + 5000
    inputPointsTargets = blendShapeNode.inputTarget[geoIndex].inputTargetGroup[index].inputTargetItem[ittidx].inputPointsTarget.get()
    inputComponentsTargets = blendShapeNode.inputTarget[geoIndex].inputTargetGroup[index].inputTargetItem[ittidx].inputComponentsTarget.get()

    return inputPointsTargets, inputComponentsTargets

def getBlendShapeDeltas_api(blendShapeNode, index=0, geoIndex=0, inbWeight=1.0):
    bsNodeObj = om.MObject()
    sel = om.MSelectionList()
    sel.add(blendShapeNode, 0)
    sel.getDependNode(0, bsNodeObj)

    ittidx = int((inbWeight * 1000) + 5000)
    # gets the plug for the inputTargetItem[] compound attribute and ...
    dgFn = om.MFnDependencyNode(bsNodeObj)
    plug = dgFn.findPlug('inputTarget').elementByPhysicalIndex(geoIndex).child(0).elementByPhysicalIndex(index).child(0).elementByLogicalIndex(ittidx)

    # if not connected, retrieves the deltas and the affected component list
    try:
        inputPointsTarget = plug.child(1).asMObject()
        inputComponentsTarget = plug.child(2).asMObject()
    except RuntimeError:
        return
    
    # to read the offset data, I had to use a MFnPointArrayData
    fnPoints = om.MFnPointArrayData(inputPointsTarget)
    targetPoints = fnPoints.array()
    
    # read the component list data was the trickiest part, since I had to use MFnSingleIndexedComponent to extract (finally), an MIntArray
    # with the indices of the affected vertices
    componentList = om.MFnComponentListData(inputComponentsTarget)
    targetIndices = om.MIntArray()
    for i in xrange(componentList.length()):
        comp = componentList[i]
        fnComp = om.MFnSingleIndexedComponent(comp)  # sometimes get vtx[1] or vtx[1:5] so need another loop
        for ii in xrange(fnComp.elementCount()):
            targetIndices.append(fnComp.element(ii))

    # construct a dict
    result = {}
    for i in xrange(targetPoints.length()):
        result[targetIndices[i]] = (targetPoints[i].x, targetPoints[i].y, targetPoints[i].z)

    return result

def getUnusedBlendShapeIndex(blendShapeNode, thresold=1e-04):
    unusedIndex = []
    geoIndices = blendShapeNode.inputTarget.getArrayIndices()

    for wi in blendShapeNode.inputTarget[0].inputTargetGroup.getArrayIndices():
        inUse = False
        for gi in geoIndices:
            # inputPts = blendShapeNode.inputTarget[gi].inputTargetGroup[wi].inputTargetItem[6000].inputPointsTarget.get()
            deltas = getBlendShapeDeltas_api(blendShapeNode=blendShapeNode.nodeName(), index=wi, geoIndex=gi, inbWeight=1.0)
            if deltas:
                for pt in deltas.values():
                    if abs(pt[0]) > thresold or abs(pt[1]) > thresold or abs(pt[2]) > thresold:
                        inUse = True
                        break
            if inUse:
                break
        else:
            unusedIndex.append(wi)

    return unusedIndex

def cleanUnusedBlendShapeTarget(blendShapeNode=None, thresold=1e-04):
    blendShapeNode = getBlendShapeNodeFromSel(blendShapeNode)
    if not blendShapeNode:
        return
    unusedIndices = getUnusedBlendShapeIndex(blendShapeNode, thresold)
    for i in unusedIndices:
        bshName = pm.aliasAttr(blendShapeNode.w[i], q=True)
        mel.eval('blendShapeDeleteTargetGroup "%s" %s;' %(blendShapeNode.nodeName(), i))
        print '%s deleted' %bshName

def getBlendShapeNodeFromSel(blendShapeNode=None):
    if not blendShapeNode:
        sel = misc.getSel(selType='any')
        bshInHis = [n for n in pm.listHistory(sel) if n.nodeType()=='blendShape']
        if bshInHis:
            return bshInHis[0]
    if isinstance(blendShapeNode, (str, unicode)):
        blendShapeNode = pm.nt.BlendShape(blendShapeNode)
    return blendShapeNode

def getBlendShapeAttr(blendShapeNode=None, index=None, geoIndex=0):
    blendShapeNode = getBlendShapeNodeFromSel(blendShapeNode)
    if not blendShapeNode:
        return None, None

    baseShp = blendShapeNode.getBaseObjects()[geoIndex]
    numVtx = baseShp.numVertices()

    # getting master weight for the blendshape node
    if index == None:
        wAttr = blendShapeNode.inputTarget[geoIndex].baseWeights
    else:  # getting specific target attrs
        wAttr = blendShapeNode.inputTarget[geoIndex].inputTargetGroup[index].targetWeights

    return wAttr, numVtx

def inverseBlendShapeWeight(blendShapeNode=None, index=None, geoIndex=0):
    wAttr, numVtx = getBlendShapeAttr(blendShapeNode=blendShapeNode, index=index, geoIndex=geoIndex)
    if not wAttr:
        return

    # check sels
    itVtx = xrange(numVtx)

    vtxIndex = list(set([v.indices()[0] for v in pm.selected(fl=True) if isinstance(v, pm.MeshVertex)]))
    if vtxIndex:
        itVtx = vtxIndex

    for n in itVtx:
        currVal = wAttr[n].get()
        newVal = 1.0-currVal
        wAttr[n].set(newVal)

def getBlendShapeWeight(blendShapeNode=None, index=None, geoIndex=0):
    wAttr, numVtx = getBlendShapeAttr(blendShapeNode=blendShapeNode, index=index, geoIndex=geoIndex)
    if not wAttr:
        return

    # res = []
    # for n in xrange(numVtx):
    #     w = wAttr[n].get()
    #     res.append(w)
    res = wAttr.get()
    if not res:
        res = [0.0]*numVtx
    return res

def setBlendShapeWeight(weight=[], blendShapeNode=None, index=None, geoIndex=0):
    blendShapeNode = getBlendShapeNodeFromSel(blendShapeNode)
    if not blendShapeNode:
        return
    baseShp = blendShapeNode.getBaseObjects()[geoIndex]
    numVtx = baseShp.numVertices()
    bshNodeName = blendShapeNode.nodeName()
    originalWeights = getBlendShapeWeight(blendShapeNode=blendShapeNode, index=index, geoIndex=geoIndex)

    commands = []
    if index == None:
        for n in xrange(numVtx):
            if originalWeights[n] == weight[n]:
                continue
            try:
                commands.append('setAttr %s.inputTarget[%s].baseWeights[%s] %s' %(bshNodeName, geoIndex, n, weight[n]))
            except:
                pass
    else:
        for n in xrange(numVtx):
            if originalWeights[n] == weight[n]:
                continue
            try:
                commands.append('setAttr %s.inputTarget[%s].inputTargetGroup[%s].targetWeights[%s] %s' %(bshNodeName, geoIndex, index, n, weight[n]))
            except:
                pass
                
    cmd = ';'.join(commands)
    mel.eval(cmd)

def getNormalizeSkinClusterWeights(skinCluster=None, joints=[], stillJnt=None):
    skinMesh = None
    if not skinCluster or not stillJnt:
        # get selection
        sels = misc.getSel(num='inf')
        if not sels or len(sels) < 3:
            om.MGlobal.displayError('Invalid selection!')
            return
        if misc.checkIfPly(sels[0]) == True:
            skinMesh = sels[0]
            skinCluster = misc.findRelatedSkinCluster(skinMesh)
        if not skinCluster:
            om.MGlobal.displayError('Cannot find skinCluster node on %s' %sels[0].nodeName())
            return
        if all([isinstance(s, pm.nt.Joint) for s in sels[1:-1]]):
            joints = sels[1:-1]

        if isinstance(sels[-1], pm.nt.Joint):
            stillJnt = sels[-1]

        if not joints or not stillJnt:
            om.MGlobal.displayError('Select mesh, joints and still joint.')
            return

    # convert string to py node - just in case
    if isinstance(skinCluster, (str, unicode)):
        skinCluster = pm.PyNode(skinCluster)
        if not isinstance(skinCluster, pm.nt.SkinCluster):
            om.MGlobal.displayError('%s is not a skinCluster.' %skinCluster.nodeName())
            return
    tmps = []
    for j in joints:
        if isinstance(j, (str, unicode)):
            j = pm.PyNode(j)
        tmps.append(j)
    joints = tmps
            
    if isinstance(stillJnt, (str, unicode)):
        stillJnt = pm.PyNode(stillJnt)
        if not isinstance(stillJnt, pm.nt.Joint):
            om.MGlobal.displayError('%s is not a joint.' %stillJnt.nodeName())
            return

    if not skinMesh:
        skinShp = skinCluster.getGeometry()[0]
        skinMesh = skinShp.getParent()
    else:
        skinShp = skinMesh.getShape(ni=True)

    jnts = skinCluster.getInfluence()
    if stillJnt not in jnts or not [j for j in joints if j in jnts]:
        om.MGlobal.displayError('Selected joint in not an influence in %s.' %skinCluster.nodeName())
        return

    orderDict = {}  # {index in user list: index in inf list}
    stillIndx = jnts.index(stillJnt)
    numVerts = skinShp.numVertices()
    infJnts = list(jnts)
    del infJnts[stillIndx]

    for i, j in enumerate(joints):
        orderDict[i] = infJnts.index(j)  

    weights = [] 
    for n in xrange(len(jnts) - 1):
        newList = list()
        weights.append(newList)

    skcName = skinCluster.nodeName()
    skinShapeName = skinShp.shortName()
    for i in xrange(numVerts):
        # vtx = skinShp.vtx[i]
        vtx = '%s.vtx[%s]' %(skinShapeName, i)
        weightValues = mc.skinPercent(skcName, vtx, q=True, v=True)
        stillJntWeight = weightValues[stillIndx]
        remainWeight = 1.0 - stillJntWeight

        del weightValues[stillIndx]
        
        # calculate normalized values without still jnt 
        for a, v in enumerate(weightValues):
            newWeight = 0.0
            if remainWeight > 0.0:
                # newWeight = (stillJntWeight*(float(v/remainWeight))) + v
                newWeight = v/remainWeight
            weights[a].append(newWeight)
    # reorder
    ret = []
    for i, v in orderDict.iteritems():
        ret.append(weights[v])

    return ret

def addBshTarget(sels=[], bshNode=''):
    if not sels:
        sels = pm.selected()
    if not sels or sels < 2:
        return
    baseObj = sels[-1]
    targets = sels[:-1]
    allGeos = baseObj.getChildren(ad=True, type='mesh')
    bshs = [n for n in allGeos[0].listHistory() if n.nodeType()=='blendShape']
    
    if bshNode:
        for n in bshs:
            if n.nodeName() == bshNode:
                bshNode = n
                break
    else:
        bshNode = bshs[0]
       
    bshNodeName = bshNode.nodeName()
    index = max(bshNode.weightIndexList()) + 1
    for t in targets:
        pm.blendShape(bshNode, e=True, t=(baseObj, index, t, 1.0))
        index += 1
        print 'Added %s to %s at index %s' %(t.nodeName(), bshNodeName, index)

def getBshInbtweens(blendShapeNode, index=0, geoIndex=0):
    if isinstance(blendShapeNode, (str, unicode)):
        blendShapeNode = pm.PyNode(blendShapeNode)
    inputTargetGrp = blendShapeNode.inputTarget[geoIndex].inputTargetGroup[index]
    arrayNums = inputTargetGrp.inputTargetItem.getArrayIndices()
    inb_weights = []
    for n in arrayNums:
        inb_weight = (n-5000.0)/1000
        inb_weights.append(inb_weight)

    return inb_weights

def turnOffBshEdits(blendShapeNodes=[]):
    bshs = []
    if not blendShapeNodes:
        bshs = pm.ls(type='blendShape')
    else:
        for node in blendShapeNodes:
            if pm.objExists(node) and pm.nodeType(node) == 'blendShape':
                pyNode = pm.PyNode(node)
                bshs.append(pyNode)
            else:
                om.MGlobal.displayWarning('Skipping: %s' %node)
    if not bshs:
        return

    for bsh in bshs:
        editting = bsh.inputTarget[0].sculptTargetIndex.get()
        if editting != -1:
            pm.sculptTarget(bsh, e=True, target=editting)
            bsh.inputTarget[editting].sculptTargetIndex.set(-1)

def mirrorBlendShapeWeights(blendShapeNode=None, index='all', geoIndex='all', mirrorAcross='YZ', positiveToNegative=True):
    blendShapeNode = getBlendShapeNodeFromSel(blendShapeNode)
    if not blendShapeNode:
        return

    pm.undoInfo(openChunk=True)
    sels = pm.selected()

    # index
    if index == 'all':
        index = [None] + range(blendShapeNode.getWeightCount())
    elif isinstance(geoIndex, int):
        index = [index]

    # geo index
    allGeos = blendShapeNode.getBaseObjects()
    if geoIndex == 'all':
        geoIndex = blendShapeNode.getGeometryIndices()
    elif isinstance(geoIndex, int):
        geoIndex = [geoIndex]

    # collect mirror data
    mirrorAxis = 0
    for i, l in enumerate('XYZ'):
        if l not in mirrorAcross:
            mirrorAxis = i
            break

    # create tmp geo grp
    tmpGrp = pm.group(em=True, n='mirrorBshTmp_grp')
    tmpGrpName = tmpGrp.shortName()
    miScale = [1.0, 1.0, 1.0]
    miScale[mirrorAxis] = -1.0
    tmpGrp.scale.set(miScale)

    # collect original data
    geoData = []
    for gi in geoIndex:
        # get bsh weights
        origWeights = {}
        for wi in index:
            weightAtIndex = getBlendShapeWeight(blendShapeNode=blendShapeNode, index=wi, geoIndex=gi)
            origWeights[wi] = weightAtIndex

        # flip geos
        geoTr = allGeos[gi].getParent()
        origShp = misc.getOrigShape(obj=geoTr, includeUnuse=False)
        tmpTr = pm.polyCube(ch=False)[0]
        pm.matchTransform(tmpTr, geoTr, pos=True, rot=True, scl=True)
        tmpGeo = tmpTr.getShape()
        pm.connectAttr(origShp.outMesh, tmpGeo.inMesh)

        mel.eval('parent -r "%s" "%s";' %(tmpTr.shortName(), tmpGrpName))

        # get vertex points
        points = om.MPointArray()
        srcFn = allGeos[gi].__apimfn__()
        srcFn.getPoints(points, om.MSpace.kWorld)

        # get barycentric data
        baryCentricData = meshIntersect.barycentricCoords(tmpGeo.shortName(), origShp.shortName())

        geoData.append((gi, points, baryCentricData, origWeights))
    pm.delete(tmpGrp)

    for gi, points, baryCentricData, origWeights in geoData:
        weightDict = defaultdict(list)
        for pi in xrange(points.length()):
            pt = points[pi]

            # get barycentric data
            indices, multiplier = baryCentricData[pi]

            if positiveToNegative:
                isOnTargetSide = pt[mirrorAxis] < 0.0
            else:
                isOnTargetSide = pt[mirrorAxis] > 0.0

            # print pi
            for wi, weights in origWeights.iteritems():
                weightValue = 0.0
                if isOnTargetSide:  # it's the target side
                    for ind, m in zip(indices, multiplier):
                        weightValue += weights[ind]*m

                else: # it's the source side
                    # print pi, weights
                    weightValue = weights[pi]

                weightDict[wi].append(weightValue)

        # set the weights
        for wi, resultWeights in weightDict.iteritems():
            setBlendShapeWeight(weight=resultWeights, 
                blendShapeNode=blendShapeNode, 
                index=wi, geoIndex=gi)
    if sels:
        pm.select(sels, r=True)
    pm.undoInfo(closeChunk=True)

