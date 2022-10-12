import os
import shutil
import re
import contextlib
import time
import math
from tempfile import mkstemp

import pymel.core as pm
import maya.cmds as mc
import maya.mel as mel
import maya.OpenMaya as om
import maya.mel as mel

from nuTools import misc
# reload(misc)

MAYA_VERSION = mel.eval('getApplicationVersionAsFloat')

class FreezeViewport():
    VP2_NAME = 'vp2Renderer'
    def __init__(self, mode='vp2'): 
        self.mode = mode 

    def __enter__(self):
        if self.mode == 'vp2': 
            # collect auto keyframe setting
            self.resetAutoKey = pm.autoKeyframe(query=True, state=True)
            # turn off auto keyframe
            pm.autoKeyframe(state=False)

            # collect old rederer settings and switch all to VP2
            self.renderers = {}
            for panel in pm.lsUI(editors=True):
                if panel.find('modelPanel') != -1:
                    renderer = pm.modelEditor(panel, q=True, rnm=True)
                    self.renderers[panel] = renderer
                    if renderer != self.VP2_NAME:  # switch to VP2
                        try:
                            pm.modelEditor(panel, e=True, rendererName=self.VP2_NAME)
                        except:
                            pass
            # pause VP2
            if not pm.ogs(query=True, pause=True):
                pm.ogs(pause=True)

        elif self.mode == 'legacy': 
            pm.refresh(su=True)

    def __exit__(self, *args):
        if pm.about(batch=True):
            return
        if self.mode == 'vp2': 
            # un-pause VP2
            if pm.ogs(query=True, pause=True):
                pm.ogs(pause=True)
                
            # restore old settings
            for panel, renderer in self.renderers.iteritems():
                try:
                    pm.modelEditor(panel, e=True, rendererName=renderer)
                except:
                    pass
            pm.autoKeyframe(state=self.resetAutoKey)

        elif self.mode == 'legacy': 
            pm.refresh(su=False)
            pm.refresh(f=True)
        
def getShapes(objs):
    if not isinstance(objs, (list, set, tuple)):
        objs = [objs]

    shps = []
    for obj in objs:
        try:
            shp = mc.listRelatives(obj, shapes=True, f=True, ni=True)[0]
            shps.append(shp)
        except:
            pass

    return shps

def getNodeVisible(node):
    if mc.getAttr('%s.visibility' %node) == False:
        return False

    parentPath = mc.listRelatives(node, f=True, allParents=True)[0]

    splits = parentPath.split('|')
    s = len(splits) + 1
    for p in splits:
        parent = '|'.join(splits[:s])
        if mc.getAttr('%s.visibility' %parent) == False:
            return False
        s -= 1

    return True

def getUserFromEnvVar(title=False):
    """
    Get user name from option variable stored on every machine.
        return: User name(str)
    """

    user = mel.eval('optionVar -q "PTuser"')
    if not user:
        user = 'user'
    if title == True:
        user = user.title()
    return user

def getVersionFromFile(path=''):
    if not path:
        path = pm.sceneName()
        if not path:
            om.MGlobal.displayError('no path found')
            return
    else:
        if not os.path.isfile(path):
            om.MGlobal.displayError('path must be a file')
            return

    vre = re.search(r"(_v\d\d\d)", os.path.basename(path))
    if vre:
        v = vre.group()
        return v[2:]

def genVersion(incSavePath):
    """
    Given a directory path, will find the file with latest version ('_v0xx') and return the increment of 
    the version by one.
        args:
            incSavePath = The directory path to find. (str) 

        return: Incremented version(str)
    """

    version = getLatestVersion(incSavePath, mayaFileOnly=True, getFile=False)
    version += 1
    version = str(version)

    return version.zfill(3)

def getLatestVersion(path, search='', mayaFileOnly=True, getFile=False):
    path = os.path.normpath(path)
    if not os.path.isdir(path):
        om.MGlobal.displayError('path must be a directory')
        return

    version = 0
    num = {}
    try:
        files = (f for f in os.listdir(path) if os.path.isfile(os.path.join(path,f)))
        
        for fName in files:
            if mayaFileOnly == True:
                if not os.path.splitext(fName)[-1] in ['.ma', '.mb']:
                    continue
            if search != '':
                if not search in fName:
                    continue

            vre = re.search(r"(_v\d\d\d)", fName)
            if vre:
                v = vre.group()
                num[int(v[2:])] = fName

        version = max(num.keys())
        if getFile == True:
            return num[version]
    except:
        pass

    return version

def getLatestModFileInDir(path, mayaFileOnly=True, search=''):
    """
    Given the directory, find the latest modified file in that directory.
        args:
            path = The directory path. (str)
            mayaFileOnly = Only consider maya file (.ma, .mb) (bool)
        return:
            The latest file path. (str)
    """

    files = os.walk(path).next()[2]
    filePaths = []

    for f in files:
        filePath = '%s/%s' %(path, f)
        if mayaFileOnly == True:
            if not os.path.splitext(filePath)[-1] in ['.ma', '.mb']:
                continue
        if search != '':
            if seach not in f:
                continue
        filePaths.append(filePath)

    if filePaths:
        filePaths.sort(key=os.path.getmtime, reverse=True)
        return filePaths[0]
    else:
        return path

def removeUnloadRef():
    """
    Remove all references that its status is unloaded.

        return: dict('removed': list of removed references, 
                     'remain': list of the remaining references )
    """

    remainRef, removeRef = [] , []
    for ref in  pm.listReferences():
        if ref.isLoaded() == False:
            removeRef.append(ref.refNode.nodeName())
            ref.remove()
        else:
            remainRef.append(ref)

    return {'removed': removeRef, 'remain': remainRef}

def getAllVisibleGeoInRef(ref):
    nodes = mc.referenceQuery(ref, nodes=True, dp=True)
    geo = []
    geoAppend = geo.append
    objectType = mc.objectType
    listRelatives = mc.listRelatives
    for n in (i for i in nodes if objectType(i)=='transform'):
        shp = listRelatives(n, shapes=True, f=True, ni=True)
        if shp:
            if objectType(shp[0])=='mesh' and getNodeVisible(shp[0])==True:
                tr = '|'.join(shp[0].split('|')[:-1])
                geoAppend(tr)
    return geo

def getTopNodeInRef(ref):
    trs = [n for n in mc.referenceQuery(ref, nodes=True, dp=True) if mc.objectType(n)=='transform']
    sorted_trs = sorted(trs, key=lambda i: len(i))
    return sorted_trs[0]

def getAllVisibleObjectInNodes(nodes, types=['mesh']):
    geo = []
    for n in (i for i in nodes if mc.objectType(i)=='transform'):
        try:
            shp = mc.listRelatives(n, shapes=True, f=True, ni=True)[0]
            if shp and mc.objectType(shp) in types and getNodeVisible(shp)==True:
                # get full path
                fps = mc.ls(n, l=True)
                for fp in fps:
                    if n in fp:
                        geo.append(fp)
        except: 
            pass

    return geo

def getAllGeoInRef(ref):
    nodes = mc.referenceQuery(ref, nodes=True, dp=True)
    geo = []
    for n in [i for i in nodes if mc.objectType(i)=='transform']:
        try:
            shp = mc.listRelatives(n, shapes=True, f=True, ni=True)[0]
            if shp and mc.objectType(shp)=='mesh':
                geo.append(n)
        except: pass

    return geo

def getRefFromObjects(objs=[]):
    refPaths = set()
    for obj in objs:
        try:
            refPath = mc.referenceQuery(obj, f=True)
            refPaths.add(refPath)
        except:
            pass

    return refPaths 

def getFileRefFromObjects(objs=[]):
    fileRefs = set()
    for obj in objs:
        try:
            refPath = pm.referenceQuery(obj, f=True)
            fileRef = pm.FileReference(refPath)
            fileRefs.add(fileRef)
        except:
            pass

    return fileRefs 

def convertSelectionToAllGeoInRef(topGrp='', select=True):
    sels = mc.ls(sl=True, l=True, type='transform')
    refs = getRefFromObjects(sels)

    geos = []
    for ref in refs:
        geo = getAllVisibleGeoInRef(ref)
        if geo:
            if topGrp:
                geo = [g for g in geo if topGrp in g]
            geos.extend(geo)
    if geos:
        if select:
            mc.select(geos, r=True)
        return geos

def convertSelectionToAllCtrlInRef(ctrlSuffix='_ctrl'):
    refs = getFileRefFromObjects(objs=pm.selected())
    if not refs:
        return

    nss = list(set(r.namespace for r in refs))
    if not nss:
        return

    all_ctrls = []
    for ns in nss:
        all_ctrls += mc.ls('%s:*%s' %(ns, ctrlSuffix))
    if all_ctrls:
        mc.select(all_ctrls, r=True)


def removeUnusedNodeFromMaFile(filePath) :
    regexes = [ '.*uiConfigurationScriptNode.*' ,
            '.*delight.*' ,
            '.*mentalray.*' ,
            '.*miDefaultOptions.*' ,
            '.*defaultRenderLayer.*' ,
            '.*renderLayerManager.*' ,
            '.*modelPanel\d+ViewSelectedSet.*',
            '.*lockNode.*',
            'createNode reference.*' ]
    combined = "(" + ")|(".join(regexes) + ")"

    basename = os.path.basename(filePath)
    tmpDir = os.path.normpath(os.path.expanduser("~"))

    # non-existing path to write to
    wFilePath = os.path.join(tmpDir, '%s.write' %basename)
    # wFileHandle, wFilePath = mkstemp()

    with contextlib.nested(open(filePath, 'r'), open(wFilePath, 'w')) as (rid, wid):
        write = True
        bunchSize = 1000
        lines = []
        linesappend = lines.append
        matchkw = re.match
        widwritelines = wid.writelines

        for line in rid:

            # The line is not indented, test for keyword - inverted to write.
            if not line.startswith('    '):  
                write = not matchkw(combined, line)  

            # to write or not
            if write:
                linesappend(line)
                if len(lines) == bunchSize:
                    widwritelines(lines)
                    lines = []
                    linesappend = lines.append

        widwritelines(lines)

    # replace the target with the write file
    shutil.copy2(wFilePath, filePath)
    os.remove(wFilePath)
    
def removeNameSpace(ns):
    try:
        pm.namespace(mv=[ns,':'], f=True)
    except:
        pass

    if ns in  pm.namespaceInfo(lon=True):
        try:
            pm.namespace(rm=ns)
        except:
            pass

def removeNestedNamespaceFromRef(ref):
    nsObj = pm.Namespace(ref.namespace)
    nestedNss = nsObj.listNamespaces(recursive=True)
    if nestedNss:
        for cns in nestedNss[::-1]:
            pm.namespace(mergeNamespaceWithParent=True, removeNamespace=cns)

def removeAllNameSpace():
    allns = pm.listNamespaces()
    if allns:
        removed = set()
        for ns in allns:
            nestedNss = ns.listNamespaces(recursive=True)
            if nestedNss:
                for cns in nestedNss[::-1]:
                    try:
                        pm.namespace(mergeNamespaceWithParent=True, removeNamespace=cns)
                    except:
                        pass
            try:
                pm.namespace(mergeNamespaceWithParent=True, removeNamespace=ns)
                removed.add(ns)
            except:
                pass
    else:
        print '\tNo namespace found.'

def getMayaBinDir():
    paths = os.environ['PATH'].split(';')
    for path in paths:
        search_result = re.search('Maya([0-9]*)/bin$', path)
        if search_result:
            return path

def importAllRefs():
    allRefs = pm.listReferences()
    dRefFiles = [r for r in allRefs if r.isDeferred() == True]
    lRefFiles = [r for r in allRefs if r.isDeferred() == False]

    if lRefFiles or dRefFiles:
        for ref in dRefFiles:
            refPath = ref.path
            ref.remove()
            print '\tRemoved: %s' %refPath

        for ref in lRefFiles:
            try:
                refPath = ref.path
                imp = ref.importContents()
                print '\tImported: %s' %refPath
            except RuntimeError:
                print '\tFailed: %s' %ref
    else:
        print '\tNo reference found.'


def parentPreConsObj():
    deleteGrp = None
    grpName = '|delete_grp'
    try:
        deleteGrp = pm.PyNode(grpName)
    except: 
        print '\tNo %s found.' %grpName
        return

    if deleteGrp:
        for child in deleteGrp.getChildren(type='transform'):
            parent = getParentScaleConsParent(child)
            if parent:
                try :
                    pm.parent(child, parent)
                    print '\tparented: "%s"  to  "%s"' %(child.nodeName(),  parent.nodeName())
                except : pass
        
        pm.delete(deleteGrp)
    print '\t%s has been deleted.' %grpName


def getParentScaleConsParent(obj=None):
    ret = None
    if not obj:
        return None

    #get constraint connect to obj
    pconstraints, sconstraints = None, None
    try:
        pconstraints = [c for c in obj.parentInverseMatrix[0].outputs(t='parentConstraint') if not c.isReferenced()][0]
        sconstraints = [c for c in obj.parentInverseMatrix[0].outputs(t='scaleConstraint') if not c.isReferenced()][0]
    except: pass

    if pconstraints and sconstraints:
        ptargetList = pconstraints.getTargetList()
        stargetList = sconstraints.getTargetList()

        if ptargetList == stargetList:
            pm.delete([pconstraints, sconstraints])
            ret = ptargetList[0]

    return ret 

def connectProxyCtrl(hasNamespace=False, src_suffix='_ctrl', des_suffix='_loc'):
    from pprint import pprint

    res = {'Already Connected':[], 'Connected':[], 'Cannot connect':[], 'No match':[]}
    if hasNamespace == True:
        ns_sep = ':'
        ns_search = '*:'
        proxyCtrls = pm.ls('*:*ProxyConnect*%s' %des_suffix)
    else:
        ns_sep = ''
        ns_search = ''
        proxyCtrls = pm.ls('*ProxyConnect*%s' %des_suffix)

    for proxyCtrl in proxyCtrls:
        proxyCtrlName = proxyCtrl.nodeName()
        
        if hasNamespace == True:
            proxyName = proxyCtrlName.split('%s' %ns_sep)[-1]
        else:
            proxyName = proxyCtrlName

        ctrlKw = proxyName.replace('ProxyConnect', '')
        ctrlKw = ctrlKw.replace(des_suffix, src_suffix)
        ctrls = pm.ls('%s%s' % (ns_search, ctrlKw))
        if not ctrls:
            ctrls = pm.ls(ctrlKw)
        if ctrls:
            ctrl = ctrls[0]
            allAttrs = [a for a in proxyCtrl.listAttr(k=True, s=True, se=True, u=True)]
            for attr in allAttrs:
                attrName = attr.shortName()
                if attr.isDynamic() == True:
                    srcAttr = misc.addNumAttr(ctrl, attrName, attr.type())
                else:
                    srcAttr = ctrl.attr(attrName)

                if not srcAttr.isConnectedTo(attr):
                    try:
                        pm.connectAttr(srcAttr, attr, f=True)
                        res['Connected'].append(proxyCtrlName)
                    except:
                        res['Cannot connect'].append(proxyCtrlName)
                else:
                    res['Already Connected'].append(proxyCtrlName)
        else:
            res['No match'].append(proxyCtrlName)

    pprint(res)
    return res

def connectDualSkeleton(constraint=False, hasNamespace=False, suffix='_jnt'):
    from pprint import pprint
    
    res = {'Already Connected':[], 'Connected':[], 'Cannot connect':[], 'No match':[]}
    if hasNamespace == True:
        ns_sep = ':'
        ns_search = '*:'
        proxyJnts = pm.ls('*:*ProxySkin*%s' %suffix)
    else:
        ns_sep = ''
        ns_search = ''
        proxyJnts = pm.ls('*ProxySkin*%s' %suffix)

    for proxyJnt in proxyJnts :
        proxyJntName = proxyJnt.nodeName()
        
        if hasNamespace == True:
            proxyName = proxyJntName.split('%s' %ns_sep)[-1]
        else:
            proxyName = proxyJntName

        riggedJntKw = proxyName.replace('ProxySkin', '')

        riggedJnts = pm.ls('%s%s' % (ns_search, riggedJntKw))

        if riggedJnts :
            riggedJnt = riggedJnts[0]
            riggedJntName = riggedJnt.nodeName()
            pair = [proxyJntName, riggedJntName]
            # if not all(misc.checkTransformConnected(proxyJnt).values()):
            try :
                if constraint == True:
                    pm.parentConstraint(riggedJnt, proxyJnt, mo=True)
                    pm.scaleConstraint(riggedJnt, proxyJnt, mo=True)
                else:
                    pm.parent(proxyJnt, riggedJnt)
                    proxyJnt.inverseScale.disconnect()
                    children = proxyJnt.getChildren(type='constraint')
                    toDel = []
                    for cons in children:
                        targets = [t for t in cons.getTargetList() if t==riggedJnt]
                        if targets:
                            toDel.append(cons)
                    if toDel:
                        pm.delete(toDel)
                res['Connected'].append(pair)
            except :
                res['Cannot connect'].append(pair)
            # else:
            #     res['Already Connected'].append(riggedJntName)
        else :
            res['No match'].append(proxyJntName)

    pprint(res)
    return res

def setAllPlySmoothPreview(level=1):
    allplys = (m for m in mc.ls(type='mesh', l=True) if mc.displaySmoothness(m, po=True) != level)
    displaySmoothness = mc.displaySmoothness
    for ply in allplys:
        displaySmoothness(ply, po=level)

def getAnimCurveAttachToRef(ref):
    '''
        Get all animCurve node attach to the given reference path.
        @param
            str ref - the reference path. usually with copy number {n}.
    '''
    ctrlTypes = ['transform', 'joint', 'nurbsCurve']
    nodes = (n for n in mc.referenceQuery(ref, nodes=True, dp=True) if mc.objectType(n) in ctrlTypes)   
    animCrvs = []
    animCrvsAppend = animCrvs.append
    listConnections = mc.listConnections
    referenceQuery = mc.referenceQuery
    lockNode = mc.lockNode
    for node in nodes:
        cons = listConnections(node, s=True, d=False, type='animCurve')
        if cons:
            for con in cons:
                # mc.lockNode returns a list for weird reason. use [0] to get to the boolean value inside the list
                if not referenceQuery(con, inr=True) and not lockNode(con, q=True, l=True)[0]: 
                    animCrvsAppend(con)
    return animCrvs

def removeAllRefs():
    refs = pm.listReferences()
    for ref in refs:
        try:
            ref.remove()
        except Exception, e:
            print e 

def getRefInFile(filePath):
    '''
        Get all references currently being reference by reading the .ma file.
        Will read if the line starts with 'file -r '.
        All the reference data will be return
    '''
    refCmd = 'file -r '
    refNsDict = {}
    refs = []

    with open(filePath, 'r') as readFile:
        # boolean var that indicates if 'file -r ' is found yet
        foundRef = False
        cont = False
        text = ''
        # loop through each line
        for line in readFile:
            # if line starts with 'file -r ' and not continuation case from the line before
            if line.startswith(refCmd) or cont == True:
                foundRef = True
                # if this line has ; - the mel command has ended
                if line.endswith(';\n') == True:
                    # if this line ends in 1 line text variable is the line itself
                    if not cont:
                        text = line
                    else:  # else add line to text variable
                        text += line

                    # split the text with ' ' into splits variable
                    splits = text.split()
                    # reset vars
                    text = '' 
                    cont = False

                    # try to get reference elements by spliting string flags
                    try:
                        node = splits[splits.index('-rfn') + 1].split('"')[1::2][0]
                        ns = splits[splits.index('-ns') + 1].split('"')[1::2][0]
                        path = splits[-1].split('"')[1::2][0]
                        
                        # add to dict if key(namespace) exists will just override :)
                        refNsDict[ns] = path
                        
                    except: # if its failed, just continue
                        continue 
                else:  # the mel command does not end within this line
                    text += line  # add line to text variable
                    cont = True
                    continue

            # stop the read if line doesn't start with 'file -r ' anymore
            # and we already read through file referencing lines 
            # and this is not continuation line from the line before
            elif foundRef == True and cont == False:
                break

    # value in oldRefNsDict is our refs
    refs = refNsDict.values()
    return refs


def enableVrayObjIdAttrToSelected(objs=[]):
    if not objs:
        objs = mc.ls(sl=True, l=True)
        if not objs:
            return
    for sel in  objs:
        shps = mc.listRelatives(sel, type='shape', f=True, ni=True)
        if shps:
            if not mc.objExists('%s.vrayObjectID' %sel):
                cmd = 'vray addAttributesFromGroup %s vray_objectID 1; vrayAddAttr %s vrayObjectID;' %(sel, sel)
                mel.eval(cmd)

def transferVrayObjId():
    sels = mc.ls(sl=True, l=True)
    parent = sels[0][1:]
    children = sels[1:]
    if not parent and children:
        return
    enableVrayObjIdAttrToSelected(objs=sels)
    value = mc.getAttr('%s.vrayObjectID' %parent)
    i = 0
    for c in children:
        mc.setAttr('%s.vrayObjectID' %c, int(value))
        i += 1

    print 'ID : %s has been transfer to %s children' %(value, i)

def deleteAllUnknownNodes():
    unknown_nodes = mc.ls(type='unknown')
    i = 0
    if unknown_nodes:
        # unlock them first
        for n in unknown_nodes:
            if mc.lockNode(n, q=True) == True:
                try:
                    mc.lockNode(n, l=False)
                except Exception:
                    continue

        for n in unknown_nodes:
            if mc.objExists(n) == True:
                try:
                    mc.delete(n)
                    i += 1
                except Exception:
                    om.MGlobal.displayError('Unable to delete : %s' %n)

        print '\tDeleted %s unknown node(s).' %i
    else:
        print '\tNo unknown node found.'

def deleteAllTurtleNodes():
    turtle_names = ['TurtleBakeLayerManager', 'TurtleDefaultBakeLayer', 'TurtleRenderOptions', 'TurtleUIOptions']
    deleted = False
    for n in turtle_names:
        if mc.objExists(n) == True:
            # unlock them first
            # if mc.lockNode(n, q=True) == True:
            try:
                mc.lockNode(n, l=False)
            except Exception:
                om.MGlobal.displayError('Unable to unlock : %s' %n)
                continue
            try:
                mc.delete(n)
                deleted = True
            except Exception:
                om.MGlobal.displayError('Unable to delete : %s' %n)

    if deleted == True:
        print '\tTurtle node deleted.'
    else:
        print '\tNo Turtle node deleted.'

    pm.unloadPlugin('Turtle.mll', force=True)

def connectAllMeshInGrp(src=None, des=None):
    # get selection of 2 transform (the geo groups)
    if not src or not des:
        sels = misc.getSel(num=2)
        if len(sels) != 2:
            om.MGlobal.displayError('Invalid selection, you must select source group and destination group.')
            return
        src = sels[0]
        des = sels[1]

    # make sure both selections are not referenced
    if src.isReferenced() == True or des.isReferenced() == True:
        om.MGlobal.displayError('Cannot operate on reference nodes. Import references and try again.')
        return

    # get only polygon transforms under both selections
    src_childs = [c for c in src.getChildren(type='transform', ad=True, ni=True) if misc.checkIfPly(c)==True]
    des_childs = [c for c in des.getChildren(type='transform', ad=True, ni=True) if misc.checkIfPly(c)==True]

    # make sure both selection has exactly same heirachy structure
    if len(src_childs) != len(des_childs):
        om.MGlobal.displayError('%s and %s has different heirachy structure.' %(src_childs, des_childs))
        return

    err = False
    geos = []
    for s, d in zip(src_childs, des_childs):
        src_shp = s.getShape(ni=True)
        des_shp = d.getShape(ni=True)

        pair_geos = [s, src_shp, d, des_shp]
        geos.append(pair_geos)

        # evaluate polygons
        src_plyEval = pm.polyEvaluate(s)
        des_plyEval = pm.polyEvaluate(d)

        del src_plyEval['uvcoord']
        del des_plyEval['uvcoord']

        if src_plyEval != des_plyEval:
            om.MGlobal.displayWarning('%s and %s has different topology.' %(s, d))
            err = True
    
    # if any difference found, just return  
    if err == True:
        return

    for elem in geos:
        s = elem[0]
        src_shp = elem[1]
        d = elem[2]
        des_shp = elem[3]

        s_orig = misc.getOrigShape(obj=s, includeUnuse=False)
        if not s_orig:
            om.MGlobal.displayWarning('Cannot find orig shape for %s' %s.nodeName())
            continue

        # make sure internal attribute pnts are the same or it will shift
        pm.transferAttributes(src_shp, des_shp,
            transferPositions=1, 
            transferNormals=0,
            transferUVs=0,
            transferColors=0,
            sampleSpace=4,
            searchMethod=3,
            flipUVs=0,
            colorBorders=1)
        pm.delete(des_shp, ch=True)

        # reparent orig shape
        orig_shp = des_shp.duplicate(addShape=True)[0]
        orig_shp.rename('%sShapeOrig' %(d.nodeName()))

        s_orig.setIntermediate(False)
        pm.transferAttributes(s_orig, orig_shp,
            transferPositions=1, 
            transferNormals=0,
            transferUVs=0,
            transferColors=0,
            sampleSpace=4,
            searchMethod=3,
            flipUVs=0,
            colorBorders=1)
        pm.delete(orig_shp, ch=True)

        s_orig_outputs = pm.listConnections(s_orig, d=True, s=False, c=True, p=True)
        for o, i in s_orig_outputs:
            attr_sn = o.shortName()
            o_attr = orig_shp.attr(attr_sn)
            pm.connectAttr(o_attr, i, f=True)

        orig_shp.setIntermediate(True)
        s_orig.setIntermediate(True)

        # swap connections
        src_cons = src_shp.inMesh.inputs(p=True)
        if src_cons:
            pm.connectAttr(src_cons[0], des_shp.inMesh, f=True)

        src_outs = pm.listConnections(src_shp.worldMesh, d=True, s=False, c=True, p=True)
        if src_outs:
            for o, i in src_outs:
                attr_sn = o.shortName()
                o_attr = des_shp.attr(attr_sn)
                pm.connectAttr(o_attr, i, f=True)

        print 'Connected: %s >> %s' %(src_cons[0], des_shp.inMesh)

        # disconnect the old mesh inMesh
        src_shp.inMesh.disconnect()

    # src_parent = src.getParent()
    # if src_parent and src_parent != des.getParent():
    #   pm.parent(des, src_parent)

    # pm.delete(src)

def deleteExtraDefaultRenderLayer():
    for node in (n for n in pm.ls(type='renderLayer') if not n.isReferenced()):
        name = node.nodeName()
        match = re.match('defaultRenderLayer[0-9]*$', name)
        if match and name != 'defaultRenderLayer':
            try:
                pm.lockNode(node, l=False)
                pm.delete(node)
            except Exception, e:
                print e
                pass

def deleteUnusedNodes():
    mel.eval('MLdeleteUnused;')


def optimizeSceneSize(option=3):
    mel.eval('cleanUpScene %s' %option)

def uncheckHiddenInOutliner():
    for obj in pm.ls(type='transform'):
        obj.hiddenInOutliner.unlock()
        obj.hiddenInOutliner.set(False)

def lockNodeInHierarchy(parent='Geo_Grp', excepts=['.*_ctrl$'], lock=True):
    try:
        parent = pm.PyNode(parent)
    except:
        return

    for transform in (c for c in parent.getChildren(ad=True) if c.nodeType()=='transform'):
        c_name = transform.nodeName()
        ex = False
        for e in excepts:
            if re.match(e, c_name):
                ex =  True
                break
        if ex == False:
            attrs = transform.listAttr(k=True, se=True, v=True)
            for attr in attrs:
                try:
                    attr.setLocked(lock)
                except:
                    pass

def assignInitialShadingAll(exceptions=[]):
    all_geos = pm.ls(type='mesh')
    if exceptions:
        excps = set()
        for e in exceptions:
            children = e.getChildren(ad=True, type='mesh')
            for c in children:
                excps.add(c)
        excps = list(excps)
        geos = [g for g in all_geos if g not in excps]
    else:
        geos = all_geos
    pm.sets('initialShadingGroup', e=True, nw=True, fe=geos)


def turnOffSmoothMeshPreview(objs=[], heirachy=True):
    if not objs:
        objs = misc.getSel(num='inf')
        if not objs:
            om.MGlobal.displayError('Invalid selection, select one or more joint.')
            return

    if heirachy == True:
        children = []
        for obj in objs:
            children.extend(obj.getChildren(ad=True, type='transform'))

        objs.extend(children)

    n = 0
    for obj in (o for o in objs if o.nodeType()=='transform' and isinstance(o.getShape(ni=True), pm.nt.Mesh)):
        currVal = int(pm.displaySmoothness(obj, q=True, po=True)[0])
        shp = obj.getShape(ni=True)
        if currVal != 1:
            pm.displaySmoothness(shp, po=1)
        
        smoothValue = 1
        if shp.numFaces() > 12000:
            smoothValue = 0
        shp.smoothLevel.set(smoothValue)

        n += 1
        
    print '%s polygon(s) has been set to lowest smooth preview' %n

def turnOffSmoothMeshPreview_All():
    topObjs = pm.ls(assemblies=True, type='transform')
    turnOffSmoothMeshPreview(objs=topObjs, heirachy=True)

def turnOffScaleCompensate_All():
    topObjs = pm.ls(assemblies=True, type='transform')
    turnOffScaleCompensate(objs=topObjs, heirachy=True)

def removeUnusedInfluence_All():
    plys = [i for i in pm.ls(type='transform') if misc.checkIfPly(i)]
    for p in plys:
        skc = misc.findRelatedSkinCluster(p)
        if not skc:
            continue
        
        mel.eval('removeUnusedForSkin(%s, 0)' %skc.nodeName())

def removeExtraCamera():
    allCamShaps = pm.ls(type='camera')
    defaultCams = ['frontShape', 'perspShape', 'sideShape', 'topShape']
    for cam in allCamShaps:
        if cam.nodeName() not in defaultCams:
            camTr = cam.getParent()
            try:
                pm.lockNode(cam, l=False)
                pm.lockNode(camTr, l=False)
                pm.delete(camTr)
            except Exception, e:
                print e

def removeAllSequencerNodes():
    nodes = pm.ls(type=['sequencer', 'shot'])
    if nodes:
        try:
            pm.delete(nodes)
        except Exception, e:
            print e

def removePlugin(pluginName):
    if not pm.pluginInfo(pluginName, q=True, l=True):
        print '%s: is not loaded' %pluginName
    else:
        dependTypes = pm.pluginInfo(pluginName, q=True, dn=True)
        nodes = []
        for t in dependTypes:
            dnodes = pm.ls(type=t)
            for node in dnodes:
                if pm.lockNode(node, q=True):
                    pm.lockNode(node, l=False)
                nodes.append(node)

        if nodes:
            pm.delete(nodes)

        mel.eval('flushUndo;')
        try:
            pm.unloadPlugin(pluginName)
        except Exception, e:
            print e
            print 'Cannot unload %s' %pluginName
    deleteAllUnknownNodes()

def getAllShaders():
    shaders = []
    sgs = pm.ls(type='shadingEngine')
    for sg in sgs:
        if not pm.sets(sg, q=True) or sg.nodeName()=='initialShadingGroup':
            continue
        inputs = sg.surfaceShader.inputs()
        if inputs:
            shaders.append([inputs[0], sg])

    return shaders

def fixSgNames():
    shaders = getAllShaders()
    for shd, sg in shaders:
        try:
            sg.rename('%sSG' %(shd.nodeName()))
        except:
            pass

def fixCMColor():
    shaders = getAllShaders()
    for shd, sg in shaders:
        try:
            colors = shd.color.get()
            shd.color.set(colors[0]**2.2, colors[1]**2.2, colors[2]**2.2)
        except:
            pass

def printEnv(envName='MAYA_SCRIPT_PATH'):
    envStr = mel.eval('getenv %s' %envName)
    envs = envStr.split(';')
    pprint(envs)

def addToEnv(envName, path):
    envStr = mel.eval('getenv "%s"' %envName)
    pluginPaths = envStr.split(';')
    if path not in pluginPaths:
        pluginPaths.append(path)
        envStr = ';'.join(pluginPaths)
        mel.eval('putenv "%s" "%s"' %(envName, envStr))

def duplicate_ref_with_setAttr(objs=[]):
    sels = []
    if not objs:
        objs = pm.selected()
        sels = objs
    refs = getFileRefFromObjects(objs)
    print refs
    new_nss = {}
    for ref in refs:
        edits = ref.getReferenceEdits()
        if not edits:
            continue

        set_attr_edits = [e for e in edits if e.split(' ')[0] == 'setAttr']
        if not set_attr_edits:
            continue

        # duplicate the reference
        old_ns = ref.namespace
        if not old_ns:
            om.MGlobal.displayError('Duplicate Ref only works with reference with namespace, skipping: %s' %ref.refNode.nodeName())
            continue

        m = re.match('(.*?)([0-9]+)$', old_ns)
        if m:
            digit = int(m.group(2))
            digit += 1
            digitStr = str(digit).zfill(3)
            new_ns = '%s%s' %(m.group(1), digitStr)
        else:
            new_ns = '%s1' %(old_ns)
        new_ref = pm.createReference(ref.path, namespace=new_ns)
        new_ns = new_ref.namespace
        new_nss[old_ns] = new_ns

        new_edits = []
        for ed in set_attr_edits:
            splits = ed.split(' ')
            obj = splits[1]
            obj = misc.removeDagPathNamespace(obj)
            obj = misc.addDagPathNamespace(obj, '%s:' %new_ns)
            splits[1] = obj
            new_edits.append(' '.join(splits))

        if new_edits:
            for ed in new_edits:
                try:
                    mel.eval(ed)
                except:
                    pass

    if sels and new_nss:
        to_sel = []
        for old, new in new_nss.iteritems():
            for s in sels:
                if s.namespace()[:-1] == old:
                    objSn = misc.removeDagPathNamespace(s.shortName())
                    new_obj = misc.addDagPathNamespace(objSn, '%s:' %new)
                    if pm.objExists(new_obj):
                        to_sel.append(pm.PyNode(new_obj))
        if to_sel:
            pm.select(to_sel)

def cleanAllNaNAnimCurves(objs=[]):
    if not objs:
        objs = pm.ls()

    for obj in objs:
        crvs = obj.inputs(type='animCurve')
        for crv in crvs:
            if crv.isReferenced():
                continue
            for time, value in zip(pm.keyframe(crv, q=True, tc=True), pm.keyframe(crv, q=True, vc=True)):
                if math.isnan(value) or math.isinf(value):
                    pm.keyframe(crv, e=True, a=True, iub=True, time=time, vc=0.0)

def get_incremental_namespace(namespace, all_namespaces):
    id_match = re.match('(.*?)([0-9]+)$', namespace)
    if id_match:
        numStr = id_match.group(2)
        num = int(numStr)
        
        start_str = id_match.group(1)
        exit = False
        while not exit:
            num += 1
            # print namespace, num
            digit_str = str(num).zfill(len(numStr))
            result_ns = start_str + digit_str
            if result_ns not in all_namespaces:
                exit = True
    else:
        result_ns = ns + '001'
    return result_ns

def move_ref_nested_namespaces():
    mc.namespace(set=':')
    nss = mc.namespaceInfo(lon=True)
    full_nss = mc.namespaceInfo(lon=True, r=True)
    ns_maps = {}  # {old: new}
    for ns in full_nss:
        splits = ns.split(':')
        # we found a nested namespace
        if len(splits) > 1:
            baseName = splits[-1]
            new_ns = get_incremental_namespace(baseName, all_namespaces=nss)
            nss.append(new_ns)

            # collect ref path
            nodes = mc.namespaceInfo(ns, dp=True, lod=True)
            if nodes:
                ref_paths = set()
                for node in nodes:
                    if mc.referenceQuery(node, inr=True):
                        path = mc.referenceQuery(node, f=True)
                        ref_paths.add(path)

                if ref_paths:
                    for ref_path in ref_paths:
                        print 'Changing file namespace: %s ---> %s' %(ref_path, new_ns)
                        mc.file(ref_path, e=True, namespace=new_ns)


    mc.namespace(set=':')