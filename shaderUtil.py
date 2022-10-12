import os
from collections import defaultdict, namedtuple
import  colorsys
import math

import maya.OpenMaya as om
import maya.OpenMayaRender as omr
import pymel.core as pm

from nuTools import misc
reload(misc)

HI_RES = 512
LO_RES = 16

TEXTURE_EXT = 'png'
TEXURE_SUFFIX = '_col'

# distance allow colors to be seen as same color
COL_TOLERANCE = 36  
TRANS_TOLERANCE = 36


Point = namedtuple('Point', ('coords', 'n', 'ct'))
Cluster = namedtuple('Cluster', ('points', 'center', 'n'))

# --- dominant color 
def getRgbCounts(rgbs):
    countDict = defaultdict(int)
    for col in rgbs:
        colStr = str(col)
        countDict[colStr] += 1
    return countDict 

def get_points(rgbs):
    rgbs = sorted(rgbs, reverse=True, key=lambda c: (c[0]+c[1]+c[2])/3)
    rgbCounts = getRgbCounts(rgbs)

    points = []
    for i, col in enumerate(rgbs):
        pt = Point(col, 3, rgbCounts[str(col)])
        points.append(pt)
    return points

def invert_srgb_cc(color):
    cc_col = [0.0, 0.0, 0.0]
    for i in xrange(3):
        if color[i] <= 0.03928:
            cc_col[i] = color[i]/12.92
        else:
            cc_col[i] = math.pow((color[i] + 0.055)/1.055, 2.4)
    return cc_col

def to_srgb_cc(color):
    cc_col = [0.0, 0.0, 0.0]
    for i in xrange(3):
        if color[i] <= 0.03928:
            cc_col[i] = color[i]*12.92
        else:
            cc_col[i] = math.pow((color[i] + 0.055)/1.055, 1.0/2.4)
    return cc_col

def average_cluster_saturate_value(cluster):
    cols = cluster.center.coords
    hsv = colorsys.rgb_to_hsv(cols[0], cols[1], cols[2])
    return len(cluster.points) * ((hsv[1] + hsv[2]) * 0.5)

def get_dominant_color(rgbs, n=3):
    points = get_points(rgbs)
    clusters = kmeans(points, n, 10)

    # sort the clusters
    clusters = sorted(clusters, reverse=True, key=average_cluster_saturate_value)
    rgbs = [map(float, c.center.coords) for c in clusters]

    return rgbs

def euclidean(p1, p2):
    return math.sqrt(sum([(p1.coords[i] - p2.coords[i]) ** 2 for i in xrange(p1.n)]))

def calculate_center(points, n):
    vals = [0.0 for i in xrange(n)]
    plen = 0

    for p in points:
        plen += p.ct
        for i in xrange(n):
            vals[i] += (p.coords[i] * p.ct)

    return Point([(v / plen) for v in vals], n, 1)

def takespread(sequence, num):
    length = float(len(sequence))
    res = []
    for i in xrange(num):
        res.append(sequence[int(math.ceil(i * length / num))])
    return res

def kmeans(points, k, min_diff):
    clusters = [Cluster([p], p, p.n) for p in takespread(points, k)]

    while 1:
        plists = [[] for i in xrange(k)]

        for p in points:
            smallest_distance = float('Inf')
            for i in xrange(k):
                distance = euclidean(p, clusters[i].center)
                if distance < smallest_distance:
                    smallest_distance = distance
                    idx = i
            plists[idx].append(p)
        
        if [] in plists:
            break

        diff = 0
        for i in xrange(k):
            old = clusters[i]
            center = calculate_center(plists[i], old.n)
            new = Cluster(plists[i], center, old.n)
            clusters[i] = new
            diff = max(diff, euclidean(old.center, new.center))

        if diff < min_diff:
            break

    return clusters
    
# --- end dominant color


def getSG(objShp):
    sgs = [sg for sg in (set(pm.listConnections(objShp, d=True, type='shadingEngine')))] 
    return sgs


def getAssignedShader(objShp, getPlug=False):
    ''' get shader assigned to obj '''
    sgs = getSG(objShp)
    shader, sg = None, None
    if not sgs:
        return shader, sg

    if len(sgs)>1:
        om.MGlobal.displayWarning('The object has more than one shadingEngine assigned to it, \
            will use first one: %s' %objShp.nodeName())
    sg = sgs[0]

    inputArgs = {}
    if getPlug == True:
        inputArgs = {'p':True}
    shaders = sg.surfaceShader.inputs(**inputArgs)
    if shaders:
        shader = shaders[0]
    return shader, sg

def getIncrementName(name):
    exit = False
    i = 1
    while not exit:
        incName = '%s%s' %(name, str(i))
        lamberts = pm.ls('%s_tmpShd' %incName, type='lambert')
        if not lamberts:
            return incName
        i += 1

def createFileNode(texturePath, name='obj'):
    name = getIncrementName(name)
    tmpFile = pm.shadingNode('file', asTexture=True, n='%s_file' %(name))
    tmpFile.fileTextureName.set(texturePath)
    return tmpFile

def createTexturePreviewShader(avgRgb, avgTrans, inColor=None, inTrans=None, name='obj'):
    name = getIncrementName(name)
    tmpLambert = pm.shadingNode('lambert', asShader=True, n='%s_tmpShd' %(name))
    
    avgRgb = [avgRgb[0]/255.0, avgRgb[1]/255.0, avgRgb[2]/255.0]
    if inColor:
        pm.connectAttr(inColor.outColor, tmpLambert.color)
        inColor.defaultColor.set(avgRgb)
    else:
        tmpLambert.color.set(avgRgb)

    avgTrans = [avgTrans[0]/255.0, avgTrans[1]/255.0, avgTrans[2]/255.0]
    if inTrans:
        pm.connectAttr(inTrans.outTransparency, tmpLambert.transparency)
    else:
        tmpLambert.transparency.set(avgTrans)

    return tmpLambert

def averageRGBs(rgbList):
    avgRgb = [round(sum(col)/len(col), 2) for col in zip(*rgbList)]

    return avgRgb

def sampleShader_uv(sampleAttr, uCoords, vCoords):
    # get num sample from number of u
    numSamples = uCoords.length()

    useShadowMaps = False
    reuseMaps = False
    cameraMatrix = om.MFloatMatrix()
    points = None

    normals = None
    refPoints =None
    tangentUs = None
    tangentVs = None
    filterSizes = None

    # create the return arguments
    resultColors = om.MFloatVectorArray()
    resultTransparencies = om.MFloatVectorArray()

    # and this is the call to sample the points
    omr.MRenderUtil.sampleShadingNetwork(sampleAttr, 
        numSamples, 
        useShadowMaps, 
        reuseMaps, 
        cameraMatrix, 
        points,
        
        uCoords, 
        vCoords, 

        normals, 
        refPoints, 
        tangentUs, 
        tangentVs, 
        filterSizes,
         
        resultColors, 
        resultTransparencies)

    # and return the sampled colors as a list
    rgbs = []
    trans = []
    # sampledTranspacenyArray = []
    for i in xrange(resultColors.length()):
        # --- result from sample
        resultColVector = resultColors[i]
        resTransVec = resultTransparencies[i]

        # --- rgb list
        rgbs.append((resultColVector.x*255, 
                    resultColVector.y*255, 
                    resultColVector.z*255))

        trans.append((resTransVec.x * 255, 
                    resTransVec.y * 255, 
                    resTransVec.z * 255))

    return rgbs, trans

def getSquareUVCoords(widthHeight):
    uCoords = om.MFloatArray()
    vCoords = om.MFloatArray()

    uMin = 0.0
    vMin = 0.0
    uMax = 1.0
    vMax = 1.0

    uLen = uMax - uMin
    vLen = vMax - vMin

    incU = uLen/(widthHeight-1)
    incV = vLen/(widthHeight-1)

    for vi in xrange(widthHeight):
        v = vMin + (incV*vi)
        for ui in xrange(widthHeight):
            u = uMin + (incU*ui)
            uCoords.append(u)
            vCoords.append(v)

    return uCoords, vCoords

def sampleShader_full(sampleAttr, uCoords, vCoords, numSamples):
    useShadowMaps = False
    reuseMaps = False
    cameraMatrix = om.MFloatMatrix()
    points = None

    normals = None
    refPoints =None
    tangentUs = None
    tangentVs = None
    filterSizes = None

    # create the return arguments
    resultColors = om.MFloatVectorArray()
    resultTransparencies = om.MFloatVectorArray()

    # and this is the call to sample the points
    omr.MRenderUtil.sampleShadingNetwork(sampleAttr, 
        numSamples, 
        useShadowMaps, 
        reuseMaps, 
        cameraMatrix, 
        points,
        
        uCoords, 
        vCoords, 

        normals, 
        refPoints, 
        tangentUs, 
        tangentVs, 
        filterSizes,
         
        resultColors, 
        resultTransparencies)

    # and return the sampled colors as a list
    rgba = []
    rgba_append = rgba.append
    div3 = 1.0/3.0
    g = 1.0/0.4545
    for i in xrange(numSamples):
        # --- result from sample
        resultColVector = resultColors[i]
        resTransVec = resultTransparencies[i]

        # --- flat color
        rgba_append((resultColVector.x**g)*255)
        rgba_append((resultColVector.y**g)*255)
        rgba_append((resultColVector.z**g)*255)

        # average and invert the value to translate from transparency to alpha
        alphaValue = 1.0 - ((resTransVec.x + resTransVec.y + resTransVec.z) * div3)
        rgba_append(alphaValue * 255)

    return rgba

def getMfnMesh(objShpName):
    mSel = om.MSelectionList()
    mSel.add(objShpName)

    objMDagPath = om.MDagPath()
    mSel.getDagPath(0, objMDagPath) 
    objMDagPath.extendToShape()
    mfnMesh = om.MFnMesh(objMDagPath)
    return mfnMesh

def getMeshUV(mfnMesh, uvSetName):
    meshUCoords = om.MFloatArray()
    meshVCoords = om.MFloatArray()

    # get all UVs
    mfnMesh.getUVs(meshUCoords, meshVCoords, uvSetName)

    return meshUCoords, meshVCoords

def getUVBoundingBox(meshUCoords, meshVCoords, widthHeight):
    # get uv bounding box
    uMin, vMin, uMax, vMax = 1.0, 1.0, 0.0, 0.0
    for i in xrange(meshUCoords.length()):
        # u
        if meshUCoords[i] < uMin:
            uMin = meshUCoords[i]
        if meshUCoords[i] > uMax:
            uMax = meshUCoords[i]
        # v
        if meshVCoords[i] < vMin:
            vMin = meshVCoords[i]
        if meshVCoords[i] > vMax:
            vMax = meshVCoords[i]

    uLen = uMax - uMin
    vLen = vMax - vMin

    incU = uLen/(widthHeight-1)
    incV = vLen/(widthHeight-1)

    bbUCoords = om.MFloatArray()
    bbVCoords = om.MFloatArray()
    for vi in xrange(widthHeight):
        v = vMin + (incV*vi)
        for ui in xrange(widthHeight):
            u = uMin + (incU*ui)

            bbUCoords.append(u)
            bbVCoords.append(v)

    return bbUCoords, bbVCoords

def writeSquareImage(rgbaFlatList, outputPath, widthHeight, depth=4):
    filePath, ext = os.path.splitext(outputPath)
    if not filePath or not ext or not os.path.exists(os.path.dirname(outputPath)):
        om.MGlobal.displayError('Invalid output path: %s' %outputPath)
        return

    if len(rgbaFlatList) != (widthHeight*widthHeight*depth):
        om.MGlobal.displayError('Invalid size of rgbaFlatList != widthHeight*widthHeight*depth')
        return

    outMImage = om.MImage()
    outMImage.create(widthHeight, widthHeight, depth, om.MImage.kByte)

    util = om.MScriptUtil()
    util.createFromList(rgbaFlatList, (widthHeight*widthHeight*depth))
    outMImage.setPixels(util.asUcharPtr(), widthHeight, widthHeight)
    
    outMImage.writeToFile(outputPath, ext[1:])  # skip the '.' 

    return outputPath

def checkRGBAEqual(rgba):
    colors, trans = [], []
    for i in xrange(0, len(rgba), 4):
        colors.append((rgba[i], rgba[i+1], rgba[i+2]))
        trans.append(rgba[i+3])

    col_result = False
    col_iterator = iter(colors)
    try:
        firstCol = next(col_iterator)
    except StopIteration:
        col_result = True
    if not col_result:
        col_result = all(misc.getDistanceFromPosition(firstCol, restCol) <= COL_TOLERANCE\
                     for restCol in col_iterator)

    trans_result = False
    trans_iterator = iter(trans)
    try:
        firstTrans = next(trans_iterator)
    except StopIteration:
        trans_result = True
    if not trans_result:
        trans_result = all(abs(firstTrans - restTrans) <= TRANS_TOLERANCE\
                            for restTrans in trans_iterator) 

    return col_result, trans_result

def generatePreviewShader(hiObjs=[], 
                        loObjs=[],
                        textureDir='',
                        doAssign=False,
                        textureExt=TEXTURE_EXT,
                        hiResolution=HI_RES, 
                        loResolution=LO_RES):
    ''' 
    hiObjs = [shadingObjToDoPreviewTexture, ...]
    loObjs = [shadingObjToloObjsColor]

    '''
    if not os.path.exists(textureDir):
        om.MGlobal.displayError('Preview texture directory does not exist: %s' %textureDir)
        return
    if not isinstance(hiObjs, (list, tuple)) :
        om.MGlobal.displayError('Parameter hiObjs must provide list of objects to convert to hi texture shader.')
        return
    if not isinstance(loObjs, (list, tuple)):
        om.MGlobal.displayError('Parameter loObjs must provide list of objects to convert to average color shader.')
        return
    if not hiObjs and not loObjs:
        om.MGlobal.displayError('Parameter hiObjs and loObjs cannot be an empty list.')
        return

    # create ambient light
    amLightShp = pm.shadingNode('ambientLight', asLight=True, n='tempBakeAmbient_lightShape')

    uvCol_tmpShd = {}  # {str([color, tran]):tempLambert}
    shd_Colors = defaultdict(list)  # {shader: [color, tran]}
    toAssignDict = defaultdict(list)  # {tempLambert : [shp, ...]}
    resultDict = {}

    hiUs, hiVs, hiNumSam = None, None, 0
    if hiObjs:
        hiUs, hiVs = getSquareUVCoords(hiResolution)
        hiNumSam = hiResolution * hiResolution

    loUs, loVs, loNumSam = None, None, 0
    if loObjs:
        loUs, loVs = getSquareUVCoords(loResolution)
        loNumSam = loResolution * loResolution

    sourceObjs = hiObjs + loObjs

    for source in sourceObjs:
        srcName = source.nodeName()


        print '---------- %s ----------' %srcName
        srcShp = source.getShape(ni=True)
        if not srcShp:
            errTxt = 'Cannot find shape node'
            om.MGlobal.displayError(errTxt)
            resultDict[srcName] = errTxt
            continue

        srcUvSetName = srcShp.getCurrentUVSetName()
        shader, sg = getAssignedShader(srcShp, getPlug=False)
        if not shader:
            errTxt = 'Cannot find shader assigned'
            om.MGlobal.displayError(errTxt)
            resultDict[srcName] = errTxt
            continue

        shaderName = shader.nodeName().split(':')[-1]  # get rid of namespace
        sgName = sg.nodeName()

        tempLambert = None
        
        # get resolution for this object
        sqUs, sqVs, sqNumSamples = None, None, None
        if source in hiObjs:  # calculate hi resolution
            resolution = hiResolution
            sqUs = hiUs
            sqVs = hiVs
            sqNumSamples = hiNumSam

        elif source in loObjs:  # calculate lo resolution
            resolution = loResolution
            sqUs = loUs
            sqVs = loVs
            sqNumSamples = loNumSam


        outputPath = '%s/preview_%s_%s.%s' %(textureDir, shaderName, resolution, textureExt)
        # get uv coords
        mfnMesh = getMfnMesh(objShpName=srcShp.longName())
        uSam, vSam = getMeshUV(mfnMesh=mfnMesh, 
                            uvSetName=srcUvSetName)
        if not uSam or not vSam:
            errTxt = 'No UV found'
            om.MGlobal.displayError(errTxt)
            resultDict[srcName] = errTxt
            continue

        # in case the mesh UV coords is so great that it exceed 1/4 of the sample
        # we're going to use for sampleShader_full, just reduce to use BB sample
        if mfnMesh.numUVs() > hiNumSam / 4:
            om.MGlobal.displayWarning('Using BB sample')
            uSam, vSam = getUVBoundingBox(uSam, vSam, loResolution)

        # sample by uv to get overall color
        rgbs_uv, trans_uv = sampleShader_uv(sgName, uSam, vSam)

        # average color and trans from colors got from sampling UV
        avgRgb = get_dominant_color(rgbs_uv)[0]
        avgTrans = averageRGBs(trans_uv)

        uv_colors = [avgRgb, avgTrans]
        uv_colors_str = str(uv_colors)  # used as dict key

        # compare uv_colors with colors we had by converting from the same shader
        rgbClosestDist ,transClosestDist = 255, 255
        closestShd = None
        for res, exColTrs in shd_Colors[shader]:
            if res != resolution:
                continue
            exCol = exColTrs[0]
            exTrs = exColTrs[1]

            colorDist = misc.getDistanceFromPosition(exCol, avgRgb)
            tranDist = misc.getDistanceFromPosition(exTrs, avgTrans)
            # print colorDist, tranDist
            if colorDist < rgbClosestDist and tranDist < transClosestDist:
                rgbClosestDist = colorDist
                transClosestDist = tranDist
                closestShd = uvCol_tmpShd[str([exCol, exTrs])]

        # this shader already been converted and has roughly same uv color
        if shader in shd_Colors and rgbClosestDist < COL_TOLERANCE and transClosestDist < TRANS_TOLERANCE: 
            print '%s: re-using shader %s' %(resolution, closestShd.nodeName())
            tempLambert = closestShd

        else:
            rgbaFull = sampleShader_full(sampleAttr=sgName, 
                                        uCoords=sqUs, 
                                        vCoords=sqVs, 
                                        numSamples=sqNumSamples)
            
            # check equal
            colorEqual, transEqual = checkRGBAEqual(rgbaFull)
            inColor = None
            inTrans = None

            # flat color texture
            if not colorEqual:
                # write to file
                texturePath = writeSquareImage(rgbaFull, outputPath, widthHeight=resolution)
                inColor = createFileNode(texturePath, name=shaderName)

            if not transEqual:
                inTrans = inColor
            
            print '%s flatCol=%s flatTrans=%s : using SG %s' %(resolution, 
                                                                colorEqual, 
                                                                transEqual, 
                                                                sgName)
            # create temp texture lambert
            tempLambert = createTexturePreviewShader(avgRgb=avgRgb, 
                                                    avgTrans=avgTrans,
                                                    inColor=inColor, 
                                                    inTrans=inTrans,
                                                    name=shaderName)

            shd_Colors[shader].append([resolution, uv_colors])
            uvCol_tmpShd[uv_colors_str] = tempLambert

        if tempLambert:
            print 'In shadeUtils tempLambert : {0}'.format(tempLambert)
            print 'In shadeUtils srcShp : {0}'.format(srcShp)
            toAssignDict[tempLambert].append(srcShp)
            # toAssignDict[tempLambert].append(srcName)

        resultDict[srcName] = True

    if doAssign == True:
        for shader, destinations in toAssignDict.iteritems():
            sg = pm.sets(renderable=True, noSurfaceShader=True, empty=True, n='%sSG' %shader.nodeName())
            pm.connectAttr(shader.outColor, sg.surfaceShader)
            pm.sets(sg, e=True, nw=True, fe=destinations)   
    
    pm.delete(amLightShp)
    print 'In shadeUtils toAssignDict : {0}'.format(toAssignDict)
    return dict(toAssignDict), resultDict  # {previewShader:[shape, shape, ...], }


