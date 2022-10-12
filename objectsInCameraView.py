import time

import maya.cmds as mc
import maya.OpenMaya as om
import pymel.core as pm

class plane():
    def __init__(self, normalisedVector):
        self.vector = normalisedVector
        self.distance = 0.0
        
    def relativeToPlane(self, point):
        # Converting the point as a vector from the origin to its position
        pointVec= om.MVector(point.x, point.y, point.z)
        val= (self.vector*pointVec) + self.distance

        if val >= 0.0:
            return True
        else:
            return False

class frustum():
    def __init__(self, cameraName):   
        # Initialising selected transforms into its associated dagPaths 
        selectionList = om.MSelectionList()
        objDagPath = om.MDagPath()
        selectionList.add(cameraName)
        selectionList.getDagPath(0, objDagPath)
        self.camera = om.MFnCamera(objDagPath)
        
        self.planes = [] 
        self.nearClip = self.camera.nearClippingPlane()
        self.farClip =  self.camera.farClippingPlane()
        self.aspectRatio = self.camera.aspectRatio()

        left_util = om.MScriptUtil()
        left_util.createFromDouble(0.0)
        ptr0 = left_util.asDoublePtr()
        
        right_util = om.MScriptUtil()
        right_util.createFromDouble(0.0)
        ptr1 = right_util.asDoublePtr()
        
        bot_util = om.MScriptUtil()
        bot_util.createFromDouble(0.0)
        ptr2 = bot_util.asDoublePtr()
        
        top_util = om.MScriptUtil()
        top_util.createFromDouble(0.0)
        ptr3 = top_util.asDoublePtr()

        stat = self.camera.getViewingFrustum(self.aspectRatio, ptr0, ptr1, ptr2, ptr3, False, True)  
        

        left = left_util.getDoubleArrayItem(ptr0, 0)
        right = right_util.getDoubleArrayItem(ptr1, 0)
        bottom = bot_util.getDoubleArrayItem(ptr2, 0)
        top = top_util.getDoubleArrayItem(ptr3, 0)
        
        #  planeA = right plane
        a = om.MVector(right, top, -self.nearClip)
        b = om.MVector(right, bottom, -self.nearClip)
        c = (a ^ b).normal() #  normal of plane = cross product of vectors a and b
        planeA = plane(c)
        self.planes.append(planeA)

        #  planeB = left plane
        a = om.MVector(left, bottom, -self.nearClip)
        b = om.MVector(left, top, -self.nearClip)
        c = (a ^ b).normal()
        planeB = plane(c)
        self.planes.append(planeB)

        # planeC = bottom plane
        a = om.MVector(right, bottom, -self.nearClip)
        b = om.MVector(left, bottom, -self.nearClip)
        c = (a ^ b).normal()
        planeC = plane(c)
        self.planes.append(planeC)
      
        # planeD = top plane
        a = om.MVector(left, top, -self.nearClip)
        b = om.MVector(right, top, -self.nearClip)
        c = (a ^ b).normal()
        planeD = plane(c)
        self.planes.append(planeD)

        # planeE = far plane
        c = om.MVector(0, 0, 1)
        planeE= plane(c)
        planeE.distance= self.farClip
        self.planes.append(planeE)

        # planeF = near plane
        c = om.MVector(0, 0, -1)
        planeF= plane(c)
        planeF.distance = self.nearClip
        self.planes.append(planeF)
        
    def relativeToFrustum(self, pointsArray):
        numPoints= len(pointsArray)
        # numInside= 0
        for j in xrange(6):
            numBehindThisPlane = len([i for i in xrange(numPoints) if not self.planes[j].relativeToPlane(pointsArray[i])])

            # all points were behind one plane, just return False. No need to look further
            if numBehindThisPlane == numPoints:
                return False
            # elif numBehindThisPlane == 0:
                # numInside += 1

        return True

def anyObjectSeen(nodes, cameraName):
    selectionList = om.MSelectionList()
    camDagPath = om.MDagPath()
    selectionList.add(cameraName)
    selectionList.getDagPath(0, camDagPath)
    cameraDagPath = om.MFnCamera(camDagPath)
    camInvWorldMtx = camDagPath.inclusiveMatrixInverse()

    fnCam = frustum(cameraName)
    points = []
    
    for node in nodes:
        selectionList = om.MSelectionList()
        objDagPath = om.MDagPath()
        selectionList.add(node)
        selectionList.getDagPath(0, objDagPath)

        fnDag = om.MFnDagNode(objDagPath)
        obj = objDagPath.node()

        dWorldMtx = objDagPath.exclusiveMatrix()
        bbox = fnDag.boundingBox()
        
        minx = bbox.min().x 
        miny = bbox.min().y 
        minz = bbox.min().z 
        maxx = bbox.max().x 
        maxy = bbox.max().y 
        maxz = bbox.max().z

        # Getting points relative to the cameras transmformation matrix
        points.append(bbox.min() * dWorldMtx * camInvWorldMtx)
        points.append(om.MPoint(maxx, miny, minz) * dWorldMtx * camInvWorldMtx)
        points.append(om.MPoint(maxx, miny, maxz) * dWorldMtx * camInvWorldMtx)
        points.append(om.MPoint(minx, miny, maxz) * dWorldMtx * camInvWorldMtx)
        points.append(om.MPoint(minx, maxy, minz) * dWorldMtx * camInvWorldMtx)
        points.append(om.MPoint(maxx, maxy, minz) * dWorldMtx * camInvWorldMtx)
        points.append(bbox.max() * dWorldMtx * camInvWorldMtx)
        points.append(om.MPoint(minx, maxy, maxz) * dWorldMtx * camInvWorldMtx)
        
        relation = fnCam.relativeToFrustum(points) 
        
        # if any of the object in objects is seen inisde the camera, return True
        if relation:
            return True

    return False

def objectsInCameraView(objects, camera):
    cameraShape = None

    cameraShapes = mc.listRelatives(camera, s=True, f=True)
    if cameraShapes and mc.nodeType(cameraShapes[0]) == 'camera':
        cameraShape = cameraShapes[0]

    result = anyObjectSeen(objects, cameraShape)

    return result

def waitForAllGpuLoad(timeout=30.0):
    allGpuShapes = pm.ls(type='gpuCache')
    if not allGpuShapes:
        print 'No GPU found'
        return

    gpuTrs = [g.getParent() for g in allGpuShapes]
    startTime = time.time()
    exit = False
    while not exit:
        if time.time() - startTime >= timeout:
            print 'Timeout reached waiting for GPU load'
            return

        loading = []
        for tr in gpuTrs:
            bb = tr.getBoundingBox()
            if bb.width() == 0.0 and bb.height() == 0.0 and bb.depth() == 0.0:
                loading.append(tr)

        if loading:
            # print 'waiting for %s' %loading
            gpuTrs = loading
        else:
            exit = True

    print 'All GPU loaded'

def getUnseenReferenceNodes(cameraName, grpName='Geo_Grp', timeRange=[]):
    if not timeRange:
        startTime = int(round(float(pm.playbackOptions(q=True, min=True))))
        endTime = int(round(float(pm.playbackOptions(q=True, max=True))))
    else:
        startTime = int(round(float(timeRange[0])))
        endTime = int(round(float(timeRange[1])))

    # get all refs
    refs = pm.getReferences()
    assets = {}  # {refNode, [geos]}
    for ns, ref in refs.iteritems():
        geoGrpName = '%s:%s' %(ns, grpName)
        if not pm.objExists(geoGrpName):
            continue

        geoGrp = pm.PyNode(geoGrpName)
        if not isinstance(geoGrp, pm.nt.Transform):
            continue

        geos = [node for node in geoGrp.getChildren(ad=True, type='transform') if node.getShape(ni=True)\
                    and isinstance(node.getShape(ni=True), (pm.nt.Mesh, pm.nt.NurbsSurface, pm.nt.GpuCache))]
        if not geos:
            continue

        assets[ref.refNode] = geos

    if assets:
        pm.refresh(suspend=True)
        pm.currentTime(startTime)
        seens = []

        for i in xrange(startTime, endTime + 1):
            # remove what has been seen
            if seens:
                for s in seens:
                    del(assets[s])

            seens = []
            if assets:
                for refNode, geos in assets.iteritems():
                    geoNames = [geo.longName() for geo in geos]
                    result = objectsInCameraView(geoNames, cameraName)
                    if result:
                        seens.append(refNode)
            else:
                break

            # go to next frame
            pm.currentTime(i)

        pm.refresh(suspend=False)
        pm.refresh(f=True)

    result = [refNode.nodeName() for refNode in assets]
    return result

'''
import pymel.core as pm
import sys
sys.path.append('O:/studioTools/maya/python/tool/rig')
from nuTools.util import objectsInCameraView as oic
reload(oic)
pm.openFile('W:/F18/TVS1915/COMMON/LAYOUT/LAY_F18_TVS1915_SQ0080_SH0630.ma', f=True)
oic.waitForAllGpuLoad()

res = oic.getUnseenReferenceNodes('SH0630_CAMERA:MAIN')
print res
'''