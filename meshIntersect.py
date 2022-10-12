# maya modules
import maya.OpenMaya as om
import pymel.core as pm
import maya.mel as mel

# custom modules
from nuTools import misc

def barycentricCoords(meshSrc, meshTgt, debug=False):
    '''
    For each vert in the target mesh, find the closest point on the source mesh,
    and compute the barycentric weights at that point.
 
    Args
        meshSrc
        meshTgt
 
    Return
        weightData      (list of tuples)
    '''
 
    weightData = []
 
    # source mesh
    try:
        selectionList = om.MSelectionList()
        selectionList.add(meshSrc)
        meshSrcDagPath = om.MDagPath()
        selectionList.getDagPath(0, meshSrcDagPath)
    except:
        return
 
    # target mesh
    try:
        selectionList = om.MSelectionList()
        selectionList.add(meshTgt)
        meshTgtDagPath = om.MDagPath()
        selectionList.getDagPath(0, meshTgtDagPath)
    except:
        return
 
    # create mesh iterator
    comp = om.MObject()
    currentFace = om.MItMeshPolygon( meshSrcDagPath, comp )
 
    # get all points from target mesh
    meshTgtMPointArray = om.MPointArray()
    meshTgtMFnMesh = om.MFnMesh(meshTgtDagPath)
    meshTgtMFnMesh.getPoints(meshTgtMPointArray, om.MSpace.kWorld)
 
    # create mesh intersector
    matrix = meshSrcDagPath.inclusiveMatrix() 
    node = meshSrcDagPath.node()
    intersector = om.MMeshIntersector()
    intersector.create( node, matrix )
 
    # create variables to store the returned data
    pointInfo = om.MPointOnMesh()
    uUtil = om.MScriptUtil(0.0)
    uPtr = uUtil.asFloatPtr()
    vUtil = om.MScriptUtil(0.0)
    vPtr = vUtil.asFloatPtr()
    pointArray = om.MPointArray()
    vertIdList = om.MIntArray()
 
    # dummy variable needed in .setIndex()
    dummy = om.MScriptUtil()
    dummyIntPtr = dummy.asIntPtr()
 
    # For each point on the target mesh
    # Find the closest triangle on the source mesh.
    # Get the vertIds and the barycentric coords.
    # 
    for i in range(meshTgtMPointArray.length()):
 
        intersector.getClosestPoint( meshTgtMPointArray[i], pointInfo )
        pointInfo.getBarycentricCoords(uPtr,vPtr)
        u = uUtil.getFloat(uPtr)
        v = vUtil.getFloat(vPtr)
 
        faceId = pointInfo.faceIndex()
        triangleId = pointInfo.triangleIndex()
 
        currentFace.setIndex(faceId, dummyIntPtr)
        currentFace.getTriangle(triangleId, pointArray, vertIdList, om.MSpace.kWorld )
 
        weightData.append(((vertIdList[0], vertIdList[1], vertIdList[2]), (u, v, 1-u-v)))
 
        if debug:
            print  100*':'
            print 'target point id:', i
            print ''
            print 'target point:', meshTgtMPointArray[i][0], meshTgtMPointArray[i][1], meshTgtMPointArray[i][2]
            closestPoint = pointInfo.getPoint()
            print 'closest pos on source:', closestPoint.x, closestPoint.y, closestPoint.z
            print 'source face id:', faceId
            print 'source triangle id:', triangleId
            print 'source vert ids:', vertIdList
            print 'source point0:', pointArray[0].x, pointArray[0].y, pointArray[0].z
            print 'source point1:', pointArray[1].x, pointArray[1].y, pointArray[1].z
            print 'source point2:', pointArray[2].x, pointArray[2].y, pointArray[2].z
            print ''
            print 'barycentric weights:', u, v, 1-u-v
            print ''
 
    return weightData

def isPointInside(intersector, point, matrix):
    ptOnMesh = om.MPointOnMesh()
    intersector.getClosestPoint(point, ptOnMesh)
    resPt = om.MPoint(ptOnMesh.getPoint()) * matrix
    resNm = om.MVector(ptOnMesh.getNormal()) * matrix
    ray = resPt - point
    ray.normalize()
    if ray * resNm > 0:
        return True
    else:
        return False

def getFlippedFaceNormals(meshName):
    pyObj = pm.PyNode(meshName)
    if isinstance(pyObj, pm.nt.Transform):
        pyMesh = pyObj.getShape(ni=True)
    else:
        pyMesh = pyObj

    # create bb mesh
    bbTr = mc.geomToBBox(meshName, ko=True)
    bbPyMesh = pm.PyNode(bbMesh).getShape()

    # create intersector for bb mesh
    bbMObj = bbPyMesh.__apimobject__()
    bbDag = bbPyMesh.__apimdagpath__()
    meshIncMat = bbDag.inclusiveMatrix()
    intersector = om.MMeshIntersector()
    intersector.create(bbMObj, meshIncMat)

    meshDag = pyMesh.__apimdagpath__()
    meshIt = om.MItMeshPolygon(meshDag)

    while not meshIt.isDone():
        index = meshIt.index()
        faceCenter = meshIt.center(om.MSpace.kWorld)
        normal = om.MVector()
        meshIt.getNormal(normal, om.MSpace.kWorld)

        ptOnMesh = om.MPointOnMesh()
        intersector.getClosestPoint(faceCenter, ptOnMesh)
        resPt = om.MPoint(ptOnMesh.getPoint()) * meshIncMat
        resNm = om.MVector(ptOnMesh.getNormal())

        pt = faceCenter + normal

        meshIt.next()
    return False

def get_faces_inside(objs=[], select=True):
    ''' Select all faces that has all of its vertices positioned inside the cage.
        args:
            objs - list(str): last in the list is considered the cage
    '''
    # sanity checks
    meshes = []
    mesh_err_msg = 'Select all mesh objects follow by the cage object.'
    if not objs:
        meshes = [i.getShape(ni=True) for i in misc.getSel(num='inf', selType='transform') if misc.checkIfPly(i)]
        if not meshes or len(meshes) < 2:
            om.MGlobal.displayError(mesh_err_msg)
            return
    else:
        for obj in objs:
            if isinstance(obj, (str, tuple)):
                obj = pm.PyNode(obj)
            if isinstance(obj, pm.nt.Transform):
                shp = obj.getShape(ni=True)
                meshes.append(shp)
    if not meshes or len(meshes) < 2:
        om.MGlobal.displayError(mesh_err_msg)
        return

    cageShp = meshes[-1]
    meshes = meshes[:-1]
    lenMeshes = len(meshes)

    # get cageFn
    cageDag = cageShp.__apimdagpath__()
    cageMobj = cageShp.__apimobject__()

    # get cage BoundingBox
    cageIncMatrix = cageDag.inclusiveMatrix()
    cageDagFn = om.MFnDagNode(cageDag)
    cageMBB = cageDagFn.boundingBox()  # get bounding box in object space
    cageMBB.transformUsing(cageIncMatrix)  # transform the bounding box to world space

    # print progress
    pm.waitCursor(st=True)
    prog_txt = 'Getting faces inside mesh volume...'
    gMainProgressBar = mel.eval('$tmp = $gMainProgressBar')
    pm.progressBar(gMainProgressBar,
                    edit=True,
                    beginProgress=True,
                    isInterruptable=True,
                    status='%s' %(prog_txt),
                    maxValue=100 )

    # create mesh intersector
    intersector = om.MMeshIntersector()
    intersector.create(cageMobj, cageIncMatrix)

    # loop over each mesh
    result = []
    for m, mesh in enumerate(meshes):
        if pm.progressBar(gMainProgressBar, query=True, isCancelled=True):
            return

        meshName = mesh.shortName()
        meshDag = mesh.__apimdagpath__()
        # get all points at once first 
        meshFn = mesh.__apimfn__()
        numFace = meshFn.numPolygons()
        meshPts = om.MPointArray()
        meshFn.getPoints(meshPts, om.MSpace.kWorld)

        # loop over each face
        meshFaceIt = om.MItMeshPolygon(meshDag)
        inside_indices = []
        skip_indices = set()
        while not meshFaceIt.isDone():
            faceIndex = meshFaceIt.index()
            if faceIndex not in skip_indices:
                center = meshFaceIt.center(om.MSpace.kWorld)
                if cageMBB.contains(center):
                    # get vtx indices
                    vtxIndices = om.MIntArray()
                    meshFaceIt.getVertices(vtxIndices)
                    # loop over each point in the face
                    for i in xrange(vtxIndices.length()):
                        vtxId = vtxIndices[i]
                        point = meshPts[vtxId]
                        isInside = isPointInside(intersector, point, cageIncMatrix)
                        if not isInside:
                            # if the point is not inside, this face and the faces 
                            # sharing this vertex are considered outside.
                            # find the connected faces to this vertex and add their indices to skip_indices
                            component = om.MFnSingleIndexedComponent().create(om.MFn.kMeshVertComponent)
                            om.MFnSingleIndexedComponent(component).addElement(vtxId)
                            mitVtx = om.MItMeshVertex(meshDag, component)
                            con_faces_indices = om.MIntArray()
                            mitVtx.getConnectedFaces(con_faces_indices)
                            for ci in xrange(con_faces_indices.length()):
                                cf_id = con_faces_indices[ci]
                                if cf_id != faceIndex:
                                    skip_indices.add(cf_id)
                            break
                    else:  # if all points are inside
                        inside_indices.append(faceIndex)

            # go to next face
            meshFaceIt.next()

        if inside_indices:
            inside_indices = misc.group_range_in_list(inside_indices)
            for i in inside_indices:
                if isinstance(i, (list, tuple)):
                    # if the whole face range is selected, select the shape instead
                    if i[0] == 0 and i[1] == numFace-1:
                        fid = ''
                    else:
                        fid = '.f[%s:%s]' %(i[0], i[1])
                else:
                    fid = '.f[%s]' %i
                result.append('%s%s' %(meshName, fid))

        # add progress
        pm.progressBar(gMainProgressBar, edit=True, step=1)
    pm.progressBar(gMainProgressBar, edit=True, endProgress=True)

    # if select arg is True
    if select:
        pm.undoInfo(openChunk=True)
        # change to face selection mode
        pm.select(cl=True)
        mel.eval('selectType -fc 1; changeSelectMode -component;')
        pm.select(result, r=True)
        pm.undoInfo(closeChunk=True)

    pm.waitCursor(st=False)
    return result

def get_matrix_from_face(mfn_mesh, point, face_id):

    """
    !@Brief Get matrix from point position and face id.
            Take normal, tangent, binormal of all face vertex and average it.

    @type mfn_mesh: om.MFnMesh
    @param mfn_mesh: MFnMesh for get point orientation
    @type point: MFloatPoint
    @param point: Position on face.
    @type face_id: int
    @param face_id: Face id

    @rtype: pymel.Core.datatypes.Matrix
    @return: Matrix found
    """

    #   Get normal
    normals = om.MFloatVectorArray()
    mfn_mesh.getFaceVertexNormals(face_id, normals)
    normal = average_vector_array(normals)

    #   Get tangent
    tangents = om.MFloatVectorArray()
    mfn_mesh.getFaceVertexTangents(face_id, tangents)
    tangent = average_vector_array(tangents)

    #   Get binormal
    binormal = tangent ^ normal
    binormal.normalize()

    #   Force normal perpendicalary
    normal = binormal ^ tangent
    normal.normalize()

    #   Create matrix
    matrix = pm.datatypes.Matrix(
        [binormal.x, binormal.y, binormal.z, 0.0],
        [tangent.x, tangent.y, tangent.z, 0.0],
        [normal.x, normal.y, normal.z, 0.0],
        [point.x, point.y, point.z, 1.0]
    )

    return matrix

def average_vector_array(vector_array):

    """
    !@Brief Average MVector array

    @type vector_array: om.MVectorArray / om.MFloatVectorArray
    :param vector_array: Vector array to average

    @rtype: om.MVector
    @return: Vector average
    """

    if not isinstance(vector_array, (om.MVectorArray, om.MFloatVectorArray)):
        raise BaseException("Invalid argument !!!\n\tArgument must be a MVectorArray.")

    m_vector = om.MVector()
    for idx in xrange(vector_array.length()):
        m_vector += om.MVector(vector_array[idx])

    m_vector /= vector_array.length()
    m_vector.normalize()

    return m_vector
