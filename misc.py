# system, util modules
import sys, os, re, ctypes, socket, math
from string import ascii_lowercase
from itertools import count, product, islice
from pprint import pprint
from operator import itemgetter
from itertools import groupby

# maya modules
import pymel.core as pm
from maya import OpenMaya as om
import maya.OpenMayaUI as omui
import maya.cmds as mc
import maya.mel as mel

# custom modules
from nuTools import config
reload(config)

from nuTools import naming
reload(naming)

def getSel(selType='transform', num=1):
    """
    Get user selection util.
        args:
            selType = Type of object to filter(string)
            num = Number of return object to expect
        return:
            PyNode, list of PyNode
    """

    # if num == 0:
        # return

    if selType == 'any':
        sels = pm.ls(sl=True)
    else:
        sels = pm.ls(sl=True, type=selType)

    if sels:
        if num == 'inf':
            return sels
        elif num == 1:
            return sels[0]
        else:
            return sels[:num]
    else:
        return []

def getAllPlyInScene(select=False):
    allMeshes = pm.ls(type='mesh')
    ret = set()
    if allMeshes:
        for m in allMeshes:
            ret.add(m.getParent())
        if select == True:
            pm.select(ret)
    return list(ret)

def getNodeType(obj=None):
    """
    Return node type for the given object.
        args:
            obj = the object to get type. *user selection
        return:
            string
    """

    if not obj:
        obj = getSel(selType='any')
    if isinstance(obj, str):
        obj = pm.PyNode(obj)

    return pm.nodeType(obj)

def getColorCode(color):
    colorDict = { 'white': 16,
    'lightGray': 0,
    'darkGray': 2,
    'black': 1, 
    'red': 13, 
    'yellow': 17,
    'darkBlue': 5,
    'blue': 6,
    'lightBlue': 18,
    'skyBlue':28,
    'medBlue':29,
    'green': 14,
    'navyBlue': 15,
    'darkRed': 4,
    'darkBlue': 5,
    'darkGreen': 7,
    'brown': 10,
    'pink': 20,
    'darkPurple': 8,
    'purple': 9,
    'orange':21,
    'lightBrown': 24}

    if color in colorDict.keys():
        return colorDict[color]
    else:
        om.MGlobal.displayWarning('Invalid color name, using yellow as default.')
        return colorDict[17]

def setWireFrameColor(color='red', objs=[], shape=True):
    """
    Set wireframe color for the given objects.
        args:
            color = Color to set. (string)
            objs = Objects to set. (list)
            shape = If true, will set color at object's shape instead of transform. (Bool)
        return: Nothing
    """

    if not objs:
        objs = getSel(selType='any', num='inf')
        if not objs:
            return
    if not isinstance(objs, (list, tuple)):
        objs = [objs]

    for obj in objs:
        try:
            if shape == True:
                obj = obj.getShape(ni=True)
            obj.overrideEnabled.set(True)
            obj.overrideColor.set(getColorCode(color))
        except:
            om.MGlobal.displayWarning('Cannot set wireframe color for  %s' %obj.nodeName())

def titleName(objs=[]):
    if not objs:
        objs = pm.selected()
    if not objs:
        return
    newNames = []
    for obj in objs:
        name = obj.nodeName()
        newName = name[0].upper() + ''.join(name[1:]) 
        obj.rename(newName)
        newNames.append(obj)
    return newNames

def upperName(objs=[]):
    if not objs:
        objs = pm.selected()
    if not objs:
        return
    newNames = []
    for obj in objs:
        name = obj.nodeName().upper()
        obj.rename(name)
        newNames.append(obj)
    return newNames

def lowerName(objs=[]):
    if not objs:
        objs = pm.selected()
    if not objs:
        return
    newNames = []
    for obj in objs:
        name = obj.nodeName().lower()
        obj.rename(name)
        newNames.append(obj)
    return newNames

def getSuffix(obj):
    """
    Get suffix name from type of the object for proper naming.
        args:
            cbj = Object to get suffix.(PyNode) *User selection
        return: The suffix(string)
    """

    if not obj:
        obj = getSel()
    if isinstance(obj, str):
        obj = pm.PyNode(obj)

    nodeType = getNodeType(obj)
    typeDict = config.NODE_TYPE_DICT
    if not nodeType in typeDict.keys():
        if nodeType == 'transform':
            from nuTools import controller as ctrl
            shp = obj.getShape()
            if isinstance(shp, (pm.nt.Mesh)):
                suffix = 'Geo'
            elif isinstance(shp, (pm.nt.NurbsSurface)):
                suffix = 'Nrb'
            elif isinstance(shp, (pm.nt.NurbsCurve)):
                suffix = 'Crv'
            elif isinstance(shp, (ctrl.Controller)):
                suffix = 'Ctrl'
            else:
                suffix = 'Grp'
        else:
            suffix = nodeType   
    else:
        suffix = typeDict[nodeType]
    return suffix

def createNode(typ, elem='', pos=''):
    """
    Create a node and properly name it.
        args:
            typ = The type of node to create.(string)
            elem = Element part to name the node.(string)
            pos = Position part to name the node.(string)
        return: The Node(PyNode)
    """

    typeDict = config.NODE_TYPE_DICT
    nodeType, suffix = '', ''
    for k, v in typeDict.iteritems():
        if typ == v:
            nodeType = k
            suffix = v

    if not nodeType:
        nodeType = typ
        suffix = typ
    nodeName = nameObj(elem, pos, suffix)
    node = pm.createNode(nodeType, n=nodeName)
    return node

def getGimbalCtrl(obj=None):
    """
    Get gimbal_ctrl which is parented and connected via visibility of the given transform(ctrl)
        args:
            obj = A control curve(PyNode)
        return: transform(PyNode)
    """

    if not obj:
        obj = getSel()
    gCtrlAttrs = ['gimbalControl', 'GimbalControl', 'gimbalCtrl', 'GimbalCtrl', 'gimbal_ctrl', 'gimbal_Ctrl', 
    'Gimbal_Ctrl', 'gimbal_control', 'Gimbal_Control', 'gimbal_Control', 'Gimbal_control', 'gimbalCtrlVis', 
    'gimbalVis', 'GimbalCtrlVis', 'GimbalControlVis', 'gimbal_vis', 'gimbal_ctrl_vis', 'gimbal_control_vis', 
    'gimbalCtrl_vis', 'gmblCtrl', 'gmblCtrlVis', 'gmblCtrl_vis']
    gCtrls = []

    objShp = obj.getShape()
    if not objShp:
        return

    for attribute in gCtrlAttrs:
        if not pm.objExists('%s.%s' %(objShp, attribute)):
            continue
        gCtrls = obj.getShape().attr(attribute).outputs()
        break

    if gCtrls:
        gCtrl = gCtrls[0]
        return gCtrl

def reShapeGimbalCtrlAll():
    allCtrls = [i for i in pm.ls('*_ctrl', type='transform') if 'Gmbl' not in i.nodeName()]
    reShapeGimbalCtrl(ctrls=allCtrls)

def reShapeGimbalCtrl(ctrls=[], scaleFactor=1.2):
    """
    Re-shape gimbal control's CVs to match with the current control's shape.
        args:
            ctrls = The parent controls of the gimbal to be re-shape(list(PyNode))
            scaleFactor = The scale of the gimbal control relative to the control.(float)
        return: transform(PyNode)
    """

    if not ctrls:
        ctrls = getSel(num='inf')
        if not ctrls:
            return

    bbCenter = []
    for ctrl in ctrls:
        gimbalCtrl = getGimbalCtrl(ctrl)
        if not gimbalCtrl:
            continue

        # get shape
        try:
            ctrlShp = ctrl.getShape(ni=True)
            gimbalCtrlShp = gimbalCtrl.getShape(ni=True)
            bbCenter = pm.objectCenter(ctrlShp, gl=True)
        except:
            continue

        numCvs = ctrl.numCVs()
        ctrlCvs = pm.PyNode('%s.cv[%s:%s]' %(ctrlShp.longName(), 0, numCvs-1))
        gimbalCtrlCvs = pm.PyNode('%s.cv[%s:%s]' %(gimbalCtrlShp.longName(), 0, numCvs-1))
        for cv in zip(ctrlCvs, gimbalCtrlCvs):
            position = list(cv[0].getPosition(space='world'))
            cv[1].setPosition(position, space='world')

        pm.scale(gimbalCtrlCvs, (scaleFactor, scaleFactor, scaleFactor), p=bbCenter, r=True)
        gimbalCtrlShp.updateCurve()

def parentToGimbal(child=None, parent=None):
    """Parent the child's zgrp to the parent's gimbalCtrl.
        args:
            parent = The parent(PyNode)
            child = The child(PyNode)
    """

    if not child or not parent:
        sels = getSel(num='inf')
        child = sels[0:-1]
        parent = sels[-1]

    childZgrps = []
    for c in child:
        zgrp = c.getParent()

        if not zgrp:
            childZgrps.append(child)
        else:
            childZgrps.append(zgrp)

    parentGCtrl = getGimbalCtrl(parent)
    if not parentGCtrl:
        parentGCtrl = parent

    pm.parent(childZgrps, parentGCtrl)
    pm.select(parent, r=True)

def constraintToGimbal(parent=None, child=None):
    """
        Parent constraint the child's zgrp to the parent's gimbalCtrl.
        args:
            parent = The constraint parent(PyNode)
            child = The constraint child(PyNode)
        return:
            constraint node(PyNode)
    """

    if not child or not parent:
        sels = getSel(num=2)
        parent = sels[0]
        child = sels[1]

    childZgrp = child.getParent()
    if isinstance(childZgrp, pm.nt.Joint) or not childZgrp:
        childZgrp = child
    parentGCtrl = getGimbalCtrl(parent)
    if not parentGCtrl:
        parentGCtrl = parent

    pconNode, sconNode = None, None
    pconNode = pm.parentConstraint(parentGCtrl, childZgrp, mo=True)
    if checkMod('ctrl') == True:
        sconNode = pm.scaleConstraint(parentGCtrl, childZgrp, mo=True)
    pm.select(parent, r=True)
    return pconNode, sconNode

def scaleCtrlVtx(inc=True, percent=0.5, obj=None):
    """
    Scale selected transforms(nurbsCurve) CVs by their pivot up or down.
        args:
        inc = Increse(bool)
        percent = Percentage of operation(float)
    """

    if not obj:
        #get ctrl selected, if one obj returned, put it in a list
        sels = getSel('transform', 'inf')
        if not isinstance(sels, (list,tuple)):
            sels = [sels]
    else:
        sels = [obj]

    #main loop getting all that need to be done
    curves = []
    gCtrlShapes = []
    for sel in sels:
        shapes = sel.getShapes()
        for shp in shapes:
            #get all shape nodes add see if its a curve and not an intermediate obj
            if not shp.isIntermediate() and isinstance(shp, (pm.nt.NurbsCurve)):
                curves.append(shp)
                ctrlTran = shp.getParent()
                gCtrl = getGimbalCtrl(ctrlTran)
                if gCtrl:
                    gCtrlShps = gCtrl.getShapes()
                    gCtrlShapes = filter(lambda x: isinstance(x, (pm.nt.NurbsCurve)), gCtrlShps)
                    curves = curves + gCtrlShapes
            else:
                continue

    #get percentage of scale
    percent = abs(percent)
    if not inc:
        percent = percent * -1

    #get all CV,scale em
    for crv in curves:
        numCvs = crv.numCVs()
        allCvs = pm.PyNode('%s.cv[%s:%s]' %(crv.longName(), 0, numCvs-1))
        scaleFactor = float('%f' %((100.00+percent)*0.01))
        pm.scale(allCvs, scaleFactor, scaleFactor, scaleFactor, os=True, r=True)

def getConParents(obj=None, sel=False):
    """
    Select transform's constraint target(s).
        args:
            sel = To Select or not(bool)
        return: list of transform(PyNode)
    """
    if not obj:
        selection = pm.ls(sl=True, type='transform')
        if len(selection) != 1:
            pm.error('Only select one transform, this script will find and select the constraint parent(s).')
        obj = selection[0]
    toSelect = []

    #get constraint connect to obj
    constraints = obj.parentInverseMatrix[0].outputs(t='constraint')
    if constraints:
        constraint = constraints[0]
        
        #get the targetList
        targetList = constraint.getTargetList()

        #if any, extend the var 'toSelect'
        if targetList:
            toSelect.extend(targetList)

    #try if they can be select?
    if sel==True:
        try:
            pm.select(toSelect)
        except:
            pass

    return toSelect

def addGimbal(tr=None, scale=1.25):
    from nuTools import controller as ctrl
    reload(ctrl)

    if not tr:
        tr = getSel()
        if not tr:
            return
    ctrlShp = tr.getShape()
    if not ctrlShp:
        return

    # --- determind the name
    ctrlName = tr.nodeName()
    np = nameSplit(ctrlName)
    gimbalName = naming.NAME(np['elem'], naming.GIMBAL, np['side'], np['typ'])

    gimbalCtrl = ctrl.Controller(n=gimbalName, color='white')
    gimbalShp = gimbalCtrl.getShape()

    pm.connectAttr(ctrlShp.worldSpace, gimbalShp.create, f=True)
    pm.refresh(f=True)
    gimbalShp.create.disconnect()
    
    snapTransform(method='parent', parents=tr, child=gimbalCtrl, mo=False, delete=True)
    pm.parent(gimbalCtrl, tr)

    numCvs = gimbalShp.numCVs()
    ctrlCvs = pm.PyNode('%s.cv[%s:%s]' %(gimbalShp.longName(), 0, numCvs-1))
    bbCenter = pm.objectCenter(gimbalShp, gl=True)
    pm.scale(ctrlCvs, (scale, scale, scale), p=bbCenter, r=True)

    gCtrlVisAttr = addNumAttr(ctrlShp, 'gimbalControl', 'long', min=0, max=1)
    gCtrlVisAttr.setKeyable(False)
    
    pm.connectAttr(gCtrlVisAttr, gimbalShp.visibility, f=True)
    gimbalCtrl.visibility.lock()
    gimbalCtrl.visibility.setKeyable(False)
    gimbalCtrl.visibility.showInChannelBox(False)

    return gimbalCtrl

def redraw(shape='', obj=None):
    """
    Redraw NURBS curve to a different shape. *User Selection
        args:
            shape = Shape to redraw. (string)
            obj = Transform of the curve. (PyNode)
        return: New redrawn shape. (PyNode)
    """
    if not obj:
        obj = getSel()
    elif isinstance(obj, str):
        obj = pm.PyNode(obj)
    if not obj or not shape:
        return
    if not isinstance(obj.getShape(ni=True), pm.nt.NurbsCurve):
        return

    from nuTools import controller as ctrl
    reload(ctrl)
    
    # draw a new curve
    tmpCrv = ctrl.drawCurve(shapeType=shape, name='tmp_crv01')
    tmpCrv = pm.PyNode(tmpCrv)
    tmpShp = tmpCrv.getShape(ni=True)
    
    # get old shape
    objShp = obj.getShape(ni=True)
    oldShapeName = objShp.nodeName()
    oldGimbal = getGimbalCtrl(obj)
    
    # connect and disconnect curve shp to change curve shape
    pm.connectAttr(tmpShp.worldSpace, objShp.create, f=True)

    # deal with the gimbal control (if one)
    if oldGimbal:
        gimbalShp = oldGimbal.getShape(ni=True)
        pm.connectAttr(tmpShp.worldSpace, gimbalShp.create, f=True)
    pm.refresh(f=True)
    pm.delete(tmpCrv)

def checkMod(check=None):
    """
    Check if modifier button(ctrl, shift, alt and capslock) is pressed.
        args:
            check = ctrl, shift, alt(string)
        return: Dictionary of boolean:
                'alt':bool
                'ctrl':bool
                'sift':bool
    """
    modNum = pm.getModifiers()
    rets = {'shift':False, 'ctrl':False, 'alt':False}
    if check not in rets.keys() and check:
        return

    if modNum & 1 > 0:
        rets['shift'] = True
    if modNum & 4 > 0:
        rets['ctrl'] = True
    if modNum & 8 > 0:
        rets['alt'] = True

    if check:
        return rets[check]
    else:
        return rets

def snapTransform(method='parent', parents=None, child=None, mo=None, delete=None):
    """
    Snap a transform's translation, rotation or both to other transform(s).
        args:
            method = point, orient, parent(string)
        return: none, constraint node(PyNode)
    """

    if not parents or not child:
        sels = getSel(num='inf')
        child = sels[-1]
        parents = sels[0:-1]
        check = True

    maintainOffset = False
    deleteNode = True

    methods =  {'point':pm.pointConstraint, 'orient':pm.orientConstraint, 'parent':pm.parentConstraint, 
                'scale':pm.scaleConstraint, 'parentTranslate':pm.parentConstraint}

    mods = checkMod(None)
    if mo != None:
        maintainOffset = mo
    else:   
        if mods['shift']:
            maintainOffset = True
    if delete != None:
        deleteNode = delete
    else:
        if mods['ctrl']:
            deleteNode = False

    kwArgs = {'mo':maintainOffset}
    if method == 'parentTranslate':
        kwArgs['sr'] = ('x', 'y', 'z')
    conNode = methods[method](parents, child, **kwArgs)
    if deleteNode == True:
        pm.delete(conNode)
    else:
        return conNode

def flipPosName(sels=None, lr=True):
    """
    Replace 'Lft' with 'Rht' or 'Up' with 'Lo' on given object's name.
    Also try to remove #digits in the end in case of duplicating.
        args:
            lr = Lft>Rht or not?(bool)
        return: list of renamed object(s)(PyNode)
    """
    if not sels:
        sels = getSel('any', 'inf')

    if not isinstance(sels,(list, tuple)):
        sels = [sels]
    lrDict = {}
    if checkMod('shift') or lr == False:
        lrDict = {"Up":"Lo", "UP":"LO", "UPR":"LWR", "uppr":"lowr"}
    else:
        lrDict = {"Lft":"Rht", "LFT":"RGT", "_lf_":"_rt_", "L_":"R_"}
    ret = []
    for sel in sels:
        oldName = sel.nodeName().rstrip('1234567890')
        
        doRename = False
        for k, v in lrDict.iteritems():
            if k in oldName:
                newName = oldName.replace(k, v)
                doRename = True
            elif v in oldName:
                newName = oldName.replace(v, k)
                doRename = True

            if doRename:
                pm.rename(sel, newName)
                ret.append(sel)
                break
    return ret

def addOffsetJnt(sels=[], element='', suffix=naming.JNT, radMult=1.50, offset=[]):
    """
    Add an offset joint to selected joint(s).
    Will search and replace name with the argruments provided.
        args:
            search = search for(string)
            replace = replace with(string)
        return: list of offset joint(s)(PyNode)
    """
    if not sels:
        sels = getSel('joint', 'inf')
        if not sels:
            return
    else:
        if isinstance(sels, str):
            sels = pm.PyNode(sels)
            sels = [sels]
        elif isinstance(sels, (list, tuple)):
            sels = filter(lambda x: pm.PyNode(x)), sels
        else:
            sels = [sels]

    posJnts = []

    for sel in sels:
        nParts = nameSplit(sel.nodeName())
        # if oldName.endswith('_jnt'):
        #   newName = oldName.replace(search, replace)
        # else:
        #   newName = '%sOffset' %oldName
        if not suffix:
            if nParts['typ']:
                suffix = nParts['typ']

        newName = naming.NAME((nParts['elem'] + element), nParts['pos'], suffix)

        # jnt = sel.duplicate(po=True, n=newName)[0]
        jnt = pm.createNode('joint', n=newName)
        snapTransform('parent', sel, jnt, False, True)
        pm.parent(jnt, sel.getParent())
        pm.makeIdentity(jnt, apply=True)
        rad = sel.radius.get()
        try:
            jnt.radius.set(rad * radMult)
        except:
            om.MGlobal.displayWarning('Cannot set radius on: %s' %jnt.nodeName())

        roOrder = sel.rotateOrder.get()
        try:
            jnt.rotateOrder.set(roOrder)
        except:
            om.MGlobal.displayWarning('Cannot set rotate order to %s on: %s' %(roOrder, jnt.nodeName()))

        if offset:
            pm.move(jnt, offset, r=True, os=True)

        pm.parent(sel, jnt)
        posJnts.append(jnt)


    return posJnts

def nameObj(*parts, **partsDict):
    """
        Create the right name by the naming convention - elementPOSITION_type.
        args:
            *parts = name part - elment, POSTION, type(string)
            **partsDict = dictionary for parts. ie. [elem:'arm', pos:'LFT', typ:'jnt']
        return: name(string)
    """

    elem, pos, typ = '', '' ,''
    keys = ['elem', 'typ']
    i = 0
    if parts:
        validPartNum = len(filter(lambda x: x is not '', parts))
        if len(parts) < 2 or validPartNum < 2:
            return ''.join(list(parts))
        for part in parts:
            if part.isupper():
                partsDict['pos'] = part
                continue
            elif i < 2 and part:
                partsDict[keys[i]] = part
                i += 1

    for k, v in partsDict.iteritems():
        if k == 'elem' and v:
            elem = v
        elif k == 'pos' and v:
            pos = v
        elif k == 'typ' and v:
            typ = v

    newName = naming.NAME(elem, pos, typ)

    return newName

def duplicateNameDetect(createSet=False, autoRename=False, typ='transform'):
    """
        Check the scene for crashing names.
        args:
            createSet = After checking done, create sets of objects that share the same name.(bool)
            autoRename = To automatically put digits after the name to prevent crashing name.(bool)
            typ = Type of object to search for.(string)
        return: None
    """

    if not typ:
        allObjs = pm.ls()
    else:
        allObjs = pm.ls(type=typ)
    if not allObjs:
        return

    nameDict = {}
    for obj in allObjs:
        nameDict[obj] = obj.nodeName()

    seen = {}
    duplicateObj = {}
    for k,v in nameDict.iteritems():
        #if nodeName is not in the list of values of seen, store it in seen. (obj:name)
        if v not in seen.values():
            seen[k] = v
        #else if the name(v) exists in the list already
        else:
            #seach in seen for the first stored object
            for key, val in seen.iteritems():
                #if the val in seen match v in nameDict. now, we got a crashing names
                if val == v:
                    #put seen obj as the duplicateObj key and duplicate obj as value. (obj:obj)
                    if key not in duplicateObj.keys():
                        duplicateObj[key] = [k]
                    else:
                        duplicateObj[key].append(k)

    #print out result dict  
    pprint(duplicateObj)

    if autoRename:
        for orig, dup in duplicateObj.iteritems():
            i=0
            for obj in (d for d in dup if not d.isReferenced()):
                newName = '%s%.2i' %(orig.nodeName(), i+1)
                obj.rename(newName)
                i+=1

    setList = []
    if createSet:
        for original, duplicate in duplicateObj.iteritems():
            newSet = pm.sets(em=True, n='%s_dupNameSet' %original.nodeName())
            toadd = duplicate
            toadd.insert(0, original)
            pm.sets(newSet, add=toadd)
            setList.append(newSet)

def nameSplit(name, splitter=naming.SEPARATOR):
    """
        Split name into parts. Element, Positon and Type.
        args:
            name = The name to split(string)
            splitter = Character to split(string)
        return: splited name(dictionary):
                'elem': element part of the name
                'pos': position part of the name
                'typ': type part of the name
    """
    parts = name.split(':')[-1].split(splitter)
    position, element, objType = '', '', ''

    lenParts = len(parts)
    if lenParts == 1:
        element = parts[0]
    elif lenParts == 2:
        revElement = parts[0][::-1]

        for i in range(len(revElement)):
            if i < 3:
                if revElement[i].isupper():
                    position += revElement[i]
                else:
                    break
        
        if position != '':
            position = position[::-1]
            element = parts[0].split(position)[0]
        else:
            element = parts[0]

        objType = ''
        if len(parts) > 1:
            objType = parts[-1]
    elif lenParts > 2:
        element = parts[0]
        position = parts[1]
        objType = parts[2]
    retDic = {'elem':element, 'pos':position, 'typ':objType}
    return retDic

def addMsgAttr(obj, attr, multi=False):
    """
        Add message attribute to the given object.
        args:
            obj = Tye object to add attribute.(PyNode)
            attr = The message attribute name.(string)
        return: The new attribute(PyNode)
    """

    if obj.hasAttr(attr):
        if obj.attr(attr).type() == 'message':
            return obj.attr(attr) 
        else:
            pm.error('Same attibute name of other type exists!')

    pm.addAttr(obj, ln=attr, at='message', m=multi)
    newAttr = obj.attr(attr)
    return newAttr

def addStrAttr(obj, attr, txt='', lock=False, multi=False):
    """
        Add string attribute to the given object.
        args:
            obj = Tye object to add attribute.(PyNode)
            attr = The string attribute name.(string)
            txt = The value of the string attribute.(string)
            lock = To lock the new attribute or not? (bool)
        return: The new attribute(PyNode)
    """

    if obj.hasAttr(attr):
        if obj.attr(attr).type() == 'string':
            return obj.attr(attr)
        else:
            pm.error('Same attibute name of other type exists!')

    pm.addAttr(obj, ln=attr, dt='string', m=multi)
    newAttr = obj.attr(attr)

    if txt:
        pm.setAttr(newAttr, txt, type='string')

    newAttr.setLocked(lock)
    
    return newAttr

def addNumAttr(obj, attr, typ, **args):
    """
     Add attribute to a transform(ctrl)
        args:
            obj = Object to addAttr.(PyNode)
            attr = Attribute name.(string)
            typ = Attribute type.(string)
            **args = Other arg such as, dv, min, max, hide, lock, enum. 
        return: attribute(PyNode)
    """
    if typ not in ('float', 'long', 'double', 'bool', 'enum', 'doubleLinear'):
        return
    if typ == 'bool':
        typ = 'long'

    add = True
    if obj.hasAttr(attr):
        # if obj.attr(attr).type() != typ:
        #   pm.error('Attribute name %s of type %s exists!' %(obj.attr(attr).name(), (obj.attr(attr).type())))
        # else:
        #   add = False
        add = False

    attr = attr.strip()
    dv = 0
    minv, maxv, hidev, lockv, keyv, env = None, None, False, False, True, 'Red:Green:Blue:'

    if args:
        for k,v in args.iteritems():
            if k == 'dv':
                dv = v
            elif k == 'min':
                minv = v
            elif k == 'max':
                maxv = v
            elif k == 'hide':
                hidev = v
            elif k == 'lock':
                lockv = v
            elif k == 'key':
                keyv = v
            elif k == 'enum':
                env = v

    if add == True:
        pm.addAttr(obj, ln=attr, at=typ, dv=dv, en=env)


    objAttr = obj.attr(attr)
    objAttr.setLocked(lockv)

    # if objAttr.type() != 'enum':
    try:
        objAttr.setRange(minv, maxv)
    except:
        pass

    objAttr.showInChannelBox(not hidev)
    objAttr.setKeyable(keyv)
    
    return objAttr

def resetChannelBox(obj=None):
    """
    Reset translate, rotate and scale attribute to be default values. *User Selection
        args:
            obj = Object to act on. (PyNode)
        return: Result (bool)
    """

    if not obj:
        obj = getSel()
    cbAttr = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']
    for a in cbAttr:
        attr = obj.attr(a)
        locked = False
        if attr.isLocked() == True and obj.isReferenced() == False:
            attr.unlock()
            locked = True
        try:
            if 's' in a:
                attr.set(1.00)
            else:
                attr.set(0.00)
        except: 
            return False 

        if locked == True:
            attr.lock()
    return True

def dupJntChain(jnt=None, suffixs = ['Fk', 'Ik'], depth=3, constraint=True, radiusMult=1.25):
    """
     Duplicate a joint chain into other different joint chain(s).
        args:
            jnt = The base joint of the joint chain to duplicate *User Selection (string, PyNode)
            suffixs = New chain name(s).(string)
            depth = Depth of children to duplicate.(int)
            constraint = To constraint and connect target weight or not?(bool)
        return: Dictionary of:
                'newChain': new joint chain(s)(Dictionary -suffixs:)(list)(PyNode) 
                'ctrlAttr': target weight attribtue(s)(PyNode)
                'conNode' : constraint node(s)(list)(PyNode)
    """

    if not jnt:
        jnt = getSel('joint', 1)
    elif type(jnt) is str:
        jnt = pm.PyNode(jnt)
    if not jnt:
        pm.error('Invalid selection or name. Select the base of a joint chain or specify the name in the "jnt" parameter.')
    jntChain = jnt.listRelatives(ad=True, type='joint')
    jntChildrenNum = len(jntChain) + 1
    if jntChildrenNum < depth:
        pm.error('Base joint does not has enough children in the chain.')
    jntChain = jntChain[::-1]
    jntChain.insert(0, jnt)
    jntChain = jntChain[0:depth]

    newChainsDict = {}
    for suffix in suffixs:
        parent = ''
        newChains = []
        for j in jntChain:
            jntName = j.nodeName()
            jntOldRadius = j.getRadius()
            nameParts = nameSplit(jntName)
            newName = nameObj('%s%s' %(nameParts['elem'], suffix), nameParts['pos'], nameParts['typ'])
            newJnt = j.duplicate(po=True, rr=False, n=newName)[0]
            newJnt.setRadius(jntOldRadius * radiusMult)
            if parent:
                pm.parent(newJnt, parent)
            parent = newJnt
            newChains.append(newJnt)
        newChainsDict[suffix] = newChains

    retDict = {'ctrlAttr':None, 'newChain':newChainsDict, 'conNode':None }

    if constraint:
        conNodes = []
        ctrlAttrs = {}

        for key in newChainsDict.keys():
            ctrlAttr = addNumAttr(jnt, key, 'double', hide=False, min=0, max=1)
            ctrlAttrs[key] = (ctrlAttr)
            for j, i in zip(newChainsDict[key], jntChain):
                conNode = pm.parentConstraint(j, i, mo=False)
                wAttr = pm.parentConstraint(conNode, q=True, wal=True)[-1]
                pm.connectAttr(ctrlAttr, wAttr)
                if conNode not in conNodes:
                    conNodes.append(conNode)
        retDict['conNode'] = conNodes 
        retDict['ctrlAttr'] = ctrlAttrs

    return retDict

def connectSwitchAttr(ctrlAttr=None, posAttr=None, negAttr=None, elem='', side=''):
    """
     Connect control attribute to 2 other child attributes. 
     When control attribute is on will result one or another child attribute to turn on.
        args:
            ctrlAttr = The controller attribute.(string, PyNode)
            posAttr = The child attribute that directly connect to the control attribute.(string, PyNode)
            negAttr = The child attribute that will behave in reverse of the control attribute.(string, PyNode)
            elem = The name of element part. Used for naming node.(string)
        return: None
    """

    if not ctrlAttr or not posAttr or not negAttr:
        return

    attrDict = {'ctrlAttr':ctrlAttr, 'posAttr':posAttr, 'negAttr':negAttr}
    for k, v in attrDict.iteritems():
        if type(v) is str:
            try:
                attrDict[k] = pm.PyNode(v)
            except Exception, e:
                sel = getSel()
                if not sel.hasAttr(v):
                    attrDict[k] = addNumAttr(sel, v, 'double', hide=False, min=0, max=1)
                else:
                    attrDict[k] = sel.attr(v)

    attrName = attrDict['ctrlAttr'].plugAttr(longName=False, fullPath=False)
    if elem:
        attrName = attrName.title()
    nodeName = naming.NAME((elem, attrName), side, naming.REV)
    revNode = pm.createNode('reverse', n=nodeName)
    pm.connectAttr(attrDict['ctrlAttr'], attrDict['posAttr'], f=True)
    pm.connectAttr(attrDict['ctrlAttr'], revNode.inputX)
    pm.connectAttr(revNode.outputX, attrDict['negAttr'], f=True)

def batchLockAttr(suffix, objs=[], excepts=[], lock=True, t=True, r=True, s=True, v=True, **kwargs):
    """
    Lock/unlock attribute(s) on all nodes in the scene.
        args:
            suffix = The suffix string to search for. ie.'_grp' (str)
            objs = The object to act on. list(PyNode)
            excepts = Act on everything matching the condition except for those matching string in this list. list(str)
            lock = Lock or unlock (bool)
            t, r, s, v = translate, rotate, scale, visibility attributes to act on. (bool)
            kwargs* = other attributes
        return: None
    """

    if suffix:
        objs = pm.ls('*%s' %suffix)

    if not objs:
        objs = getSel(num='inf')
        if not objs:
            return

    for obj in objs:
        if obj.nodeName() in excepts:
            continue
        lockAttr(obj, lock=lock, t=t, r=r, s=s, v=v, **kwargs)

def lockAttr(obj=None, lock=True, t=True, r=True, s=True, v=True, **kwargs):
    """
     Lock attribute handy function.
        args:
            ctrlAttr = Object to lock attribute. *User Selection (PyNode) 
            lock = To lock or unlock.(bool)
            t,r,s,v = Translate, Rotate, Scale, Visibility (bool)
        return: None
    """

    if not obj:
        obj = getSel()
        if not obj:
            return

    if isinstance(obj, (str, unicode)):
        obj = pm.PyNode(obj)

    if t == True:
        # obj.translate.setLocked(lock)
        axis = obj.translate.getChildren()
        for a in axis:
            a.setLocked(lock)
        obj.translate.setLocked(lock)
    if r == True:
        # obj.rotate.setLocked(lock)
        axis = obj.rotate.getChildren()
        for a in axis:
            a.setLocked(lock)
        obj.rotate.setLocked(lock)
    if s == True:
        # obj.scale.setLocked(lock)
        axis = obj.scale.getChildren()
        for a in axis:
            a.setLocked(lock)
        obj.scale.setLocked(lock)
    if v == True:
        obj.visibility.setLocked(lock)

    for k,v in kwargs.iteritems():
        if obj.hasAttr(k) and v == True:
            obj.attr(k).setLocked(lock)

def unlockChannelbox(obj=[], heirachy=True, t=True, r=True, s=True, v=True, **kwargs):
    """
    Unlock attributes to reset the channel box to default values.
        args:
            obj = The object to act on. PyNode
            heirachy = Act on all children under the object heirachy. (bool)
            t, r, s, v = translate, rotate, scale, visibility attributes to act on. (bool)
            kwargs* = other attributes
        return: None
    """

    if not obj:
        obj = getSel(num='inf')
    if not obj:
        return

    toUnlock = []
    if not isinstance(obj, (list, tuple)):
        obj = [obj]

    pyObjs = []
    for o in obj:
        if isinstance(o, (str, unicode)):
            o = pm.PyNode(o)
        pyObjs.append(o)

    if heirachy == True:
        for i in pyObjs:
            children = i.listRelatives(ad=True, type='transform')
            toUnlock.extend(children)
        toUnlock.extend(pyObjs)
        toUnlock = list(set(toUnlock))
    else:
        toUnlock = pyObjs

    for k, v in kwargs.iteritems():
        kwargs[k] = False

    for i in toUnlock:
        lockAttr(i, lock=False, t=t, r=r, s=s, v=v, **kwargs)

def lockChannelbox(obj=None, heirachy=True, t=True, r=True, s=True, v=True, **kwargs):
    """
    Unlock attributes to reset the channel box to default values.
        args:
            obj = The object to act on. PyNode
            heirachy = Act on all children under the object heirachy. (bool)
            t, r, s, v = translate, rotate, scale, visibility attributes to act on. (bool)
            kwargs* = other attributes
        return: None
    """

    if not obj:
        obj = getSel(num='inf')
    if not obj:
        return

    toLock = []
    if not isinstance(obj, (list, tuple)):
        obj = [obj]

    pyObjs = []
    for o in obj:
        if isinstance(o, (str, unicode)):
            o = pm.PyNode(o)
        pyObjs.append(o)

    if heirachy == True:
        for i in pyObjs:
            children = i.listRelatives(ad=True, type='transform')
            toLock.extend(children)
        toLock.extend(pyObjs)
        toUnlock = list(set(toLock))
    else:
        toLock = pyObjs

    for k, v in kwargs.iteritems():
        kwargs[k] = False

    for i in toLock:
        lockAttr(i, lock=True, t=t, r=r, s=s, v=v, **kwargs)

def hideAttr(obj=None, hide=True, t=None, r=None, s=None, v=None, **kwargs):
    """
     Lock attribute handy function.
        args:
            ctrlAttr = Object to hide attribute. *User Selection (PyNode) 
            hide = To hide or unhide.(bool)
            t,r,s,v = Translate, Rotate, Scale, Visibility (bool)
        return: None
    """
    if not obj:
        obj = getSel()

    if isinstance(obj, (str, unicode)):
        obj = pm.PyNode(obj)

    if t:
        axis = obj.translate.getChildren()
        for a in axis:
            a.setKeyable(not hide)
            # a.showInChannelBox(not hide)
    if r:
        axis = obj.rotate.getChildren()
        for r in axis:
            r.setKeyable(not hide)
            # r.showInChannelBox(not hide)
    if s:
        axis = obj.scale.getChildren()
        for s in axis:
            s.setKeyable(not hide)
            # s.showInChannelBox(not hide)
    if v:
        obj.visibility.setKeyable(not hide)
        obj.visibility.showInChannelBox(not hide)
    for k,v in kwargs.iteritems():
        if obj.hasAttr(k):
            obj.attr(k).setKeyable(not v)
            obj.attr(k).showInChannelBox(not v)

def moveGeoToRigPosition(obj=None, x=True, y=False, z=False, freeze=True):
    """
     Move a transform to (possibly) the origin for rigging perpose. 
        args:
            obj = Object to move. *User Selection (PyNode)
            x, y, z = Axis to act on(bool)
            freeze = To freeze transform or not.(bool)
        return: None
    """
    if not obj:
        obj = getSel()
    elif type(obj) is str:
        obj = pm.PyNode(obj)

    cp = pm.objectCenter()
    trans = pm.xform(obj, q=True, t=True)
    movePos = [(trans[0]-cp[0])*x, (trans[1]-cp[1])*y, (trans[2]-cp[2])*z]
    pm.xform(obj, t=movePos, ws=True)
    pm.xform(obj, piv=[0, 0, 0], ws=True)

    if freeze:
        childs = obj.listRelatives(ad=True, type='transform')
        childs.insert(0, obj)
        for child in childs:
            lockAttr(child, lock=False)

    pm.makeIdentity(childs, a=True)

def zgrp(objs=None, suffix='', snap=True, preserveHeirachy=False, element='', remove=''):
    """
    Group an object 
        args:
            objs = Object to group. *User Selection (PyNode)
            suffix = Suffix for group name.(string)
            snap = To snap group to current obj position before parent or not.(bool)
        return: group(PyNode)
    """

    if not objs:
        objs = getSel(num='inf')
        if not objs:
            return 
    else:
        if isinstance(objs, str):
            objs = pm.PyNode(objs)
            objs = [objs]
        elif isinstance(objs, (list, tuple)):
            objs = filter(lambda x: pm.PyNode(x)), objs
        else:
            objs = [objs]
    grps = []
    for obj in objs:
        nameParts = nameSplit(obj.nodeName())
        typ = nameParts['typ']
        # if typ != '':
        #   typ = typ.title()
        if not suffix:
            suffix = typ
        newElem = '%s%s' %(nameParts['elem'], element)
        if remove != '':
            newElem = newElem.replace(remove, '')
        grpName = nameObj(elem=newElem, pos=nameParts['pos'], typ=suffix)
        grp = pm.group(em=True, n=grpName)

        if snap == True:
            snapTransform('parent', obj, grp, False, True)
        if preserveHeirachy == True:
            objParent = obj.getParent()
            if objParent:
                pm.parent(grp, objParent)

        grp.rotateOrder.set(obj.rotateOrder.get())
        pm.parent(obj, grp)
        grps.append(grp)
    return grps

def createScaledSimpleCtrlAtObjectCenter(mult=0.5, localWorldObjs=[], **kwargs):
    sels = getSel(num='inf')

    localObj, worldObj = None, None
    if localWorldObjs:
        if isinstance(localWorldObjs[0], (str, unicode)):
            localObj = pm.PyNode(localWorldObjs[0])  
        else: 
            localObj = localWorldObjs[0]
        if isinstance(localWorldObjs[1], (str, unicode)):
            worldObj = pm.PyNode(localWorldObjs[1])  
        else: 
            worldObj = localWorldObjs[1]

    rets = []
    for sel in sels:
        bb = sel.getBoundingBox(space='object')
        sx = (bb[1][0]-bb[0][0]) * mult
        sy = (bb[1][1]-bb[0][1]) * mult
        sz = (bb[1][2]-bb[0][2]) * mult
        scale = [sx, sy, sz]
        ret = createSimpleCtrl(obj=sel,
                        **kwargs)
        ctrl = ret['ctrl']
        numCvs = ctrl.getShape().numCVs()
        ctrlCvs = pm.PyNode('%s.cv[%s:%s]' %(ctrl.longName(), 0, numCvs-1))
        pm.scale(ctrlCvs, scale, ws=True, a=True)

        if localWorldObjs:
            createLocalWorld(objs=[ctrl, localObj, worldObj, ret['grp']], createGrp=False)
        rets.append(ret)

    return rets

def scaleCtrlToFitBB(mult=0.5):
    sels = getSel(num='inf')
    for sel in sels:
        parents = getConParents()
        if parents:
            ctrl = parents[0]
            ctrlShp = ctrl.getShape()
            if ctrlShp and isinstance(ctrlShp, pm.nt.NurbsCurve):
                bb = sel.getBoundingBox(space='object')
                sx = (bb[1][0]-bb[0][0]) * mult
                sy = (bb[1][1]-bb[0][1]) * mult
                sz = (bb[1][2]-bb[0][2]) * mult
                scale = [sx, sy, sz]
            
                numCvs = ctrlShp.numCVs()
                ctrlCvs = pm.PyNode('%s.cv[%s:%s]' %(ctrl.longName(), 0, numCvs-1))
                pm.scale(ctrlCvs, scale, ws=True, a=True)

def createSimpleCtrl(obj=None, ctrlShp='crossCircle', gimbal=True, name=None, color='yellow', scale=1, axis='+y',
    createJnt=True, rad=1, useCenterPivot=False,
    parCons=True, scaleCons=True, directConnect=False, geoVis=False):
    """
    Place new joint constraint to a controller on a transform pivot or a joint.
        args:
            obj = Transform object to snap to. *User Selection (PyNode)
            ctrlShp = Controller shape. (string)
            gimbal = Add gimbal or not. (bool)
            name = Controller name. (string)
            color = Controller color.(string)
            scale = Controller scale value.(float)
            axis = Controller axis to create. (string)
            rad = Joint radius value.(float)
            parCons = To apply parentConstraint or not.(bool)
            scaleCons = To apply scaleConstraint or not.(bool)
            geoVis = Create geometry visibility connection or not. (bool)
        return: dictionary of:
                    'ctrl' = The controller object.(PyNode)
                    'grp' = The controller group.(PyNode)
                    'jnt' = The joint.(PyNode)
    """

    from nuTools import controller as ctrl

    if not obj:
        obj = getSel()
    elif type(obj) is str:
        obj = pm.PyNode(obj)

    if not obj:
        return

    if not name:
        name = obj.nodeName()
    nameParts = nameSplit(name)

    ctrl = ctrl.Controller(n=naming.NAME(nameParts['elem'], nameParts['pos'], naming.CTRL), 
            st=ctrlShp, scale=scale, axis=axis)
    ctrl.setColor(color)

    parent = ctrl
    if gimbal == True:
        gimbalCtrl = ctrl.addGimbal(scale=scale*1.25)
        parent = gimbalCtrl
    ctrl.lockAttr(v=True)
    ctrl.hideAttr(v=True)

    grp = zgrp(ctrl, element='CtrlZro', suffix='grp')[0]
    if not useCenterPivot:
        snapTransform('parent', obj, grp, delete=True)
    else:
        center = pm.objectCenter(obj)
        pm.xform(grp, a=True, ws=True, t=center)
        snapTransform('orient', obj, grp, delete=True)

    toCons = None
    jnt = None
    objGrp = None
    isJnt = False

    if createJnt == True:
        pm.select(cl=True)
        jnt = pm.joint(n=naming.NAME(nameParts['elem'], nameParts['pos'], naming.JNT), radius=rad)
        snapTransform('parent', ctrl, jnt, delete=True)
        pm.makeIdentity(jnt, a=True)
        toCons = jnt
    else:
        if not isinstance(obj, pm.nt.Joint):
            if obj.isReferenced() == True or directConnect == True:
                toCons = obj
            else:
                objParent = obj.getParent()
                objGrp = zgrp(obj, element='Zro', suffix='grp')[0]
                toCons = objGrp
                if objParent:
                    pm.parent(objGrp, objParent)
        else:
            toCons = obj
            isJnt = True

    if parCons == False and scaleCons == False:
        if directConnect == True:
            pm.connectAttr(parent.translate, toCons.translate, f=True)
            pm.connectAttr(parent.rotate, toCons.rotate, f=True)
            pm.connectAttr(parent.scale, toCons.scale, f=True)
    else:
        if parCons == True:
            snapTransform('parent', parent, toCons, mo=True, delete=False)
        if scaleCons == True:
            snapTransform('scale', parent, toCons, mo=True, delete=False)
        else:
            ctrl.lockAttr(s=True)
            ctrl.hideAttr(s=True)

    if geoVis == True and isJnt == False:
        attrName = 'geo_vis'
        visAttr = addNumAttr(ctrl, attrName, 'long', hide=False, min=0, max=1, dv=1)
        pm.connectAttr(visAttr, toCons.visibility, f=True)

    pm.select(ctrl, r=True)
    return {'ctrl':ctrl, 'grp':grp, 'jnt':jnt, 'objGrp':objGrp}

def unlockNodes(heirachy=True, limit=1000):
    """
    Unlock node(s). If heirachy arg is true, will unlock all the children of selected object.
        args:
            heirachy = If true, unlock all of selected object's children, too. (bool)
            limit = Will warn user if object number exceed the value in this arg. (int)
        return: None
    """

    sels = getSel('any', 'inf')
    objs = []
    if not sels:
        objs = pm.ls()
    else:
        if heirachy == True:
            for sel in sels:
                try:
                    childs = sel.listRelatives(ad=True)
                except:
                    continue
                if childs:
                    objs.extend(childs)
        else:
            objs = sels

    objNum = len(objs)
    if objNum > limit:
        pm.confirmDialog( title='Confirm Unlock?', 
        message='There are %i objects to unlock.\nAre you sure?' %objNum, 
        button=['Yes','No'], defaultButton='Yes', cancelButton='No', dismissString='No' )
    unlockNum = 0
    for obj in objs:
        lock = pm.lockNode(obj, q=True, l=True)[0]
        if lock == True:
            try:
                pm.lockNode(obj, l=False)
            except:
                pass
            unlockNum += 1
    print '%i Nodes Unlocked' %unlockNum,

def selRotateAxis(obj=None):
    """
    Will select the rotate axis of selected object(s)
        args:
            obj = The object. (PyNode)
        return: None
    """

    if not obj:
        objs = getSel('transform', 'inf')

    pm.select(cl=True)

    for obj in objs:
        ra = obj.rotateAxis
        pm.select(ra, add=True)

def selectionToClipboard():
    sels = [str(i.nodeName()) for i in pm.selected()]
    addToClipBoard(str(sels))

def addToClipBoard(data):
    """
    Add data provided to clipboard.
        args:
            data = Data to add to clipboard. (string)
        return: None
    """
    import subprocess
    # command = 'echo | set /p=%s|clip' %str(data).strip()
    # call(command, shell=True)
    if sys.platform == 'win32' or sys.platform == 'cygwin':
        pm.waitCursor(st=True)
        subprocess.Popen(['clip'], stdin=subprocess.PIPE, shell=True).communicate(data)
        pm.waitCursor(st=False)
    else:
        raise Exception('Platform not supported')

def copySceneNameToClipboard(directory=None):
    """
    Add current scene path to the clipboard for easy pasting.
        args:
            directory = If true, only path the current scene folder will be added. 
                        Not the path to the scene itself. (bool)
        return: path added(string)
    """

    sn = pm.sceneName()
    if directory == True:
        sn = '/'.join(sn.split('/')[0:-1])
    elif directory == None: 
        mods = checkMod('ctrl')
        if mods==True:
            sn = '/'.join(sn.split('/')[0:-1])
    addToClipBoard(sn)
    return sn

def printFileNodeDir():
    paths = []
    for node in pm.ls(type='file'):
        path = node.fileTextureName.get()
        print path
        paths.append(path)
    return paths

def batchChangeFileTextureImageDir(source='', des='', oldExt=None, newExt=None, check=True):
    """
    Search and replace texture path on all file node in the scene.
        args:
            source = The texture path to search for. (string)
            des = The texture path to replace with. (string)
            oldExt = The file texture extension to search for. (string)
            newExt = The file texture extension to replace with. (string)
        return: Number of replaced path. (int)
    """

    if source == '':
        return False
    source = cleanPath(source)
    des = cleanPath(des)

    fileNodes = pm.ls(type='file')
    i = 0

    for node in fileNodes:
        currentDir = node.fileTextureName.get()
        newDestination = ''
        if source in currentDir:
            newDestination = currentDir.replace(source, des)
        if newDestination != '':
            if oldExt and newExt:
                splits = newDestination.split('.')
                if len(splits) > 1:
                    ext = splits[-1]
                    if ext == oldExt:
                        newDestination = '%s.%s' %(splits[0:-1][0], newExt)
            if check == True and os.path.exists(newDestination) == False:
                om.MGlobal.displayWarning('%s  :Does not exists!' %newDestination)
                continue
            node.fileTextureName.set(newDestination)
            i+=1
    print '\n%i file node texture directory has been changed.' %i,
    return i

def removeNameSpace(objs=[]):
    """
    Remove all existing nameSpace from given or selected objects.
        args:
            objs = object remove. (PyNode)
            
        return: None
    """

    if not objs:
        objs = getSel(selType='any', num='')
        if not objs:
            return

    i = 0
    f = 0
    for obj in objs:
        objName = obj.nodeName()
        nameSplits = objName.split(':')
        if len(nameSplits) > 1:
            newName = nameSplits[-1]
            f += 1
            try:
                obj.rename(newName)
                i += 1
            except:
                pass    

def removeAllNameSpace():
    # gather all the ns
    allns = []
    for obj in pm.ls():
        namespace = obj.namespace()
        if namespace:
            allns.append(namespace)

    allns = list(set(allns))

    # try to remove the first namespace
    for ns in allns :
        # ns = whole_ns.split(':')[0]
        try :
            pm.namespace(mv=[ns,':'], f=True)
            if ns in  pm.namespaceInfo(lon=True):
                pm.namespace(rm=ns)
            print 'Namespace "%s" removed.'%ns
        except :
            pm.warning('Namespace "%s" is not removable. Possibly from a reference.'%ns)

def batchRemoveName(remove='', allObjs=[]):
    """
    Remove all existing string from name of all object in the scene. Ideal for removing '__pasted' from objects. 
        args:
            remove = String to remove. (string)

        return: None
    """

    if remove == '':
        return False

    if not allObjs:
        allObjs = pm.ls()
    for obj in allObjs:
        objName = obj.nodeName()
        if remove in objName:
            try:
                newName = objName.replace(remove, '')
                obj.rename(newName)
            except:
                print '\nCannot rename %s' %obj,

def snapPivot(parent=None, child=None):
    """
    Snap pivot from one object to another. 
        args:
            child = The transform the pivot will be moved. (PyNode)
            parent = The transform its pivot will be used as the reference point of moving. (PyNode) 

        return: Status(bool)
    """

    if not child or not parent:
        sels = getSel(num=2)
        if not isinstance(sels, (list, tuple)) or len(sels) != 2:
            return
        parent = sels[0]
        child = sels[1]

    parentPivot = pm.xform(parent, q=True, ws=True, rp=True)
    try:
        # child.setRotatePivot(parentPivot, space='world')
        # child.setScalePivot(parentPivot, space='world')
        pm.xform(child, ws=True, preserve=True, piv=parentPivot)
        return True
    except:
        return False

def getCenterOfVertices(components):
    x, y, z = [], [], []
    for c in components:
        xyz = pm.xform(c, q=True, ws=True, t=True)
        x.append(xyz[0])
        y.append(xyz[1])
        z.append(xyz[2])

    mix, miy, miz = min(x), min(y), min(z)
    mxx, mxy, mxz = max(x), max(y), max(z)
    position = [((mxx-mix)*0.5)+mix, ((mxy-miy)*0.5)+miy, ((mxz-miz)*0.5)+miz]
    return position

def snapToComponentCenter(comp=None, child=None):
    """
    Snap the child transform to the center point of the component(s). 
    Will create locator if no child arg is provided.
        args:
            comp = The component(s) - verticies, faces, edges. list((PyNode))
            child = The child(s) object to assign shader to. (PyNode)

        return: Locator created(if one). (PyNode)
    """
    if not comp or not child:
        child = getSel(num='inf')
        #filter out only component
        comp = [c for c in pm.ls(sl=True, l=True, fl=True) if isinstance(c, (pm.MeshFace, pm.MeshVertex, pm.MeshEdge, pm.NurbsCurveCV))]
        if not child:
            child = [pm.spaceLocator()]
        if not comp:
            om.MGlobal.displayError('Select component (vertex, edge, face) to snap a transform to.')
            return
        #convert to vertex
        vtxStrs = pm.polyListComponentConversion(comp, tv=True)
        pm.select(vtxStrs)
        comp = pm.ls(sl=True, fl=True)

    position = getCenterOfVertices(comp)

    for c in child:
        pm.xform(c, t=position, a=True, ws=True)

    pm.select([comp, child])
    return child

def orientToComponentNormals(comp=[], child=None, normalAxis='+y'):
    if not comp or not child:
        child = getSel(num='inf')
        #filter out only component
        comp = [c for c in pm.ls(sl=True, l=True, fl=True) if isinstance(c, (pm.MeshFace, pm.MeshVertex, pm.MeshEdge))]
        if not child or not comp:
            om.MGlobal.displayError('Select polygon component and a transform to orient a transform to.')
            return
        #convert to vertex
        vtxStrs = pm.polyListComponentConversion(comp, tv=True)
        pm.select(vtxStrs)
        comp = pm.ls(sl=True, fl=True)

    # calculate normal vectors
    resultVec = pm.dt.Vector(0, 0, 0)
    for c in comp:
        resultVec += c.getNormal('world')

    # calculate other vectors
    m = -1 if normalAxis.startswith('-') else 1 
    resultVec *= m
    cross1 = resultVec ^ pm.dt.Vector(0, 0, 1)  
    cross1.normalize()
    cross2 = cross1 ^ resultVec
    cross2.normalize()

    # build the matrix
    otherVecs = [cross1, cross2]
    mapAxisDict = {'x':0, 'y':1, 'z':2}
    c = 0
    matrixV = []
    for row in xrange(3):
        if row == mapAxisDict[normalAxis[-1]]:  # matches the normalAxis
            matrixV += [resultVec.x, resultVec.y, resultVec.z, 0]
        else:
            matrixV += [otherVecs[c].x, otherVecs[c].y, otherVecs[c].z, 0]
            c += 1
    matrixV += [0, 0, 0, 1]

    # convert matrix to rotations
    matrixM = om.MMatrix()
    om.MScriptUtil.createMatrixFromList(matrixV , matrixM)
    matrixFn = om.MTransformationMatrix(matrixM)
    rot = matrixFn.eulerRotation()
    rotValues = [pm.dt.degrees(rot.x), 
                pm.dt.degrees(rot.y), 
                pm.dt.degrees(rot.z)]

    # setting the rotations
    for c in child:
        pm.xform(c, ro=rotValues, a=True, ws=True)

def setDisplayType(obj=None, shp=True, disType='normal'):
    """
    Set display type of object(s). *User Selection
        args:
            obj = The object(s) to set. (PyNode)
            child = The child object to assign shader to. (PyNode)

        return: None
    """

    if not obj:
        sels = getSel()
        if isinstance(sels, str):
            sels = [sels]
        obj = sels
        if not obj:
            return
    if shp == True:
        toSet = obj.getShape()
        if not shp:
            return
    else:
        toSet = obj

    toSet.overrideEnabled.set(1)
    if disType == 'normal':
        toSet.overrideDisplayType.set(0)
    elif disType == 'temp' or disType == 'template':
        toSet.overrideDisplayType.set(1)
    elif disType == 'ref' or disType == 'reference':
        toSet.overrideDisplayType.set(2)

def annPointer(pointFrom=None, pointTo=None, ref=True, nameParts=None, constraint=True):
    """
    Create annotation pointer from on point to another.
        args:
            pointFrom = The start point of the annotation. (PyNode)
            pointTo = The end point of the annotation. (PyNode)
            ref = To set the annotation display mode to 'referenced' or not. (bool)
            nameParts = The naming dictionary. ie: {'elem':'upArm', 'pos':'LFT'}, 
                        will result 'upArmPointerLFT_loc'

        return: Dictionary of:
                'ann' = The annotation transform node. (PyNode)
                'loc' = The locator created for the end point. (PyNode)
    """

    if not pointFrom or not pointTo:
        sels = getSel(num=2)
        pointFrom = sels[0]
        pointTo = sels[1] 
        if not pointFrom or not pointTo:
            return

    if not nameParts:
        nameParts = nameSplit(pointTo.nodeName())

    name = (nameParts['elem'], nameParts['pos'])
    locName = '%sPointer%s_loc' %name
    desLoc = pm.spaceLocator()
    desLoc.rename(locName)
    desLoc.visibility.set(False)

    annShp = pm.annotate( desLoc, tx='')
    ann = annShp.getParent()
    annName = '%sPointer%s_ann' %name
    ann.rename(annName)
    if ref == True:
        setDisplayType(ann, disType='ref', shp=True)

    #snap
    snapTransform('parent', pointTo, desLoc, False, True)
    snapTransform('parent', pointFrom, ann, False, True)

    if constraint == True:
        snapTransform('parent', pointTo, desLoc, False, False)
        snapTransform('parent', pointFrom, ann, False, False)
    else:
        pm.parent([desLoc, ann], pointTo)
        pm.pointConstraint(pointFrom, ann)

    retDict = {'ann':ann, 'loc':desLoc}
    return retDict

def getAssignedShader(obj=None):
    if not obj:
        obj = getSel()
        if not obj:
            return

    shp = obj.getShape(ni=True)
    if not shp:
        pm.warning('%s: The object has no shape.' %obj.nodeName())
        return

    sgs = [sg for sg in (set(pm.listConnections(objShp, d=True, type='shadingEngine')))
            if sg.nodeName() != 'initialShadingGroup']
    if not sgs:
        pm.warning('%s: The object has no shading engine connection.' %obj.nodeName())
        return

    if len(sgs)>1:
        pm.warning('%s:The object has more than one shadingEngine assigned to it, will use first one.' %obj.nodeName())

    shaders = sgs[0].surfaceShader.inputs()
    if shaders:
        return shaders[0]

def getShaderAssigned(shp):
    from collections import defaultdict
    # sgOuts = shp.outputs(type='shadingEngine')
    sgOuts = pm.listSets(o=shp, t=1)
    numSgOuts = len(sgOuts)

    if numSgOuts == 0:
        return
    elif numSgOuts == 1:
        sg = sgOuts[0]
        ssSgIns = sg.surfaceShader.inputs()
        shader = None
        if ssSgIns:
            shader = ssSgIns[0]
        resKey = (sg, shader)
        return {resKey:shp}
    else:
        res = defaultdict(list)
        shpLongName = shp.longName()
        for i in shp.instObjGroups.getArrayIndices():
            for o in shp.instObjGroups[i].objectGroups.getArrayIndices():
                for src, des in shp.instObjGroups[i].objectGroups[o].outputs(type='shadingEngine', c=True, p=True):
                    sg = des.node()
                    ssSgIns = sg.surfaceShader.inputs()
                    shader = None
                    if ssSgIns:
                        shader = ssSgIns[0]
                    faces = src.objectGrpCompList.get()
                    resKey = (sg, shader)
                    res[resKey].extend(faces)
        return res

def transferShadeAssign(parent=None, child=None):
    """
    Assingn the shade assigned to the parent to the child.
        args:
            parent = The source object to get shader assigned. (PyNode)
            child = The child object to assign shader to. (PyNode)

        return: None
    """

    if not parent or not child:
        sels = getSel(num='inf')
        parent = sels[0]
        child = sels[1:]
        if not parent or not child:
            return
    if not isinstance(child, (list, tuple)):
        child = [child]

    parentShp = parent.getShape()
    childShp = []
    for c in child:
        cs = c.getShape(ni=True)
        if cs:
            childShp.append(cs)

    if not parentShp or not childShp:
        return

    assignRes = getShaderAssigned(parentShp)
    if not assignRes:
        return False

    numRes = len(assignRes)
    if numRes == 0:
        return False
    else:
        for sgs, assignedObjs in assignRes.iteritems():
            sg = sgs[0]
            if sg.isReferenced() == True:
                addMsgAttr(sg, '_refDuplicate')
                if sg._refDuplicate.inputs():
                    sg = sg._refDuplicate.inputs()[0]
                else:
                    newSg = pm.duplicate(sg, upstreamNodes=True)[0]
                    pm.connectAttr(newSg.message, sg._refDuplicate, f=True)
                    sg = newSg


            result = True
            for c in childShp:
                if isinstance(assignedObjs, list):
                    for f in assignedObjs:
                        fStr = '%s.%s' %(c.longName(), f)
                        try:
                            fNode = pm.PyNode(fStr)
                            pm.sets(sg, e=True, nw=True, fe=fNode)
                            # mel.eval('sets -e -fe %s %s' %(sg.nodeName(), fStr))  
                        except Exception, e:
                            print e
                            result = False
                else:
                    try:
                        pm.sets(sg, e=True, nw=True, fe=c)      
                    except Exception, e:
                        result = False


    return result

def getShaderAssigned2(shp):
    from collections import defaultdict
    # sgOuts = shp.outputs(type='shadingEngine')
    # print sgOuts
    tr = shp.getParent()
    sgOuts = pm.listSets(o=shp, t=1, ets=True)
    numSgOuts = len(sgOuts)

    res = defaultdict(list)
    for sg in sgOuts:
        ssSgIns = sg.surfaceShader.inputs()
        shader = None
        if ssSgIns:
            shader = ssSgIns[0]
        resKey = (sg, shader)
        members = pm.sets(sg, q=True)
        # print members
        for m in members:
            if isinstance(m, pm.MeshFace):
                # print m
                if m.node() == shp:
                    res[resKey].append(m)
            elif isinstance(m, pm.nt.Mesh):
                if m == shp:
                    res[resKey].append(m)
            elif isinstance(m, pm.nt.Transform):
                if m == tr:
                    res[resKey].append(m)
    return res

def transferShadeAssign2(parent=None, child=[]):
    if not parent or not child:
        sels = getSel(num='inf')
        parent = sels[0]
        child = sels[1:]
        if not parent or not child:
            return
    if not isinstance(child, (list, tuple)):
        child = [child]

    parentShps = pm.listRelatives(parent, pa=True, ad=True, typ='mesh', ni=True)
    if not parentShps:
        return 

    pm.undoInfo(openChunk=True)

    numParentShp = len(parentShps)
    chShapes = []
    for ch in child:
        chShps = pm.listRelatives(ch, pa=True, ad=True, typ='mesh', ni=True)
        if len(chShps) == numParentShp:
            chShapes.append([c.shortName() for c in chShps])

    assignments = []
    for shp in parentShps:
        # print shp
        assignRes = getShaderAssigned2(shp)
        # print assignRes
        assignments.append(assignRes)   

    # print assignments
    for i, asg in enumerate(assignments):
        allChShapes = [n[i] for n in chShapes]

        for shdInfo, asgValue in asg.iteritems():
            shader = shdInfo[1].nodeName()
            # toAssign = [str(n) for n in asgValue]
            toAssign = []
            for v in asgValue:
                if isinstance(v, pm.MeshFace):
                    fid = '.f[%s' %(str(v).split('.f[')[-1])
                    toAssign.extend(['%s%s' %(n, fid) for n in allChShapes])
                elif isinstance(v, pm.nt.Mesh) or isinstance(v, pm.nt.Transform):
                    toAssign.extend(allChShapes)

            if toAssign:
                mc.select(toAssign, r=True)
                mc.hyperShade(assign=shader)

    pm.undoInfo(closeChunk=True)

def getPoleVectorPosition(jnts = None, createLoc=False, ro=False, offset=1.25):
    """
    Given 3 joints, will calculate the position to proper place poleVector without poping the chain.
        args:
            jnts = The joint chain. *User Selection (list(PyNode))
            createLoc = To create locator or not. (bool)
            ro = To also calculate the rotation or not. (bool)
            offset = The distance between the chain and the position. (float)

        return: dictionary of:
                'translation' = The calculated translation values in world space. (list(float))
                'rotation' = The calculated rotation values in world space. (list(float))
                'locator' = The locator created (if one). (PyNode)
    """

    if not jnts:
        jnts = getSel(num=3)
        if not jnts or len(jnts) != 3:
            return
    startJnt = jnts[0]
    midJnt = jnts[1]
    endJnt =jnts[2]

    transValues = [0.0, 0.0, 0.0]
    rotValues = [0.0, 0.0, 0.0]

    #get joint translation in world space
    startV = startJnt.getTranslation(space='world')
    midV = midJnt.getTranslation(space='world')
    endV = endJnt.getTranslation(space='world')

    #calculate the translation for pole vector
    startEnd = endV - startV
    startMid = midV - startV
    dotP = startMid * startEnd
    proj = float(dotP) / float(startEnd.length())
    startEndN = startEnd.normal()
    projV = startEndN * proj
    arrowV = startMid - projV
    arrowV.normalize()
    arrowV *= offset
    #the final translation
    finalV = arrowV + midV
    transValues = [finalV.x, finalV.y, finalV.z]

    #calculate the rotation for pole vector
    if ro == True:
        cross1 = startEnd ^ startMid
        cross1.normalize()
        cross2 = cross1 ^ arrowV
        cross2.normalize()
        arrowV.normalize()

        matrixV =   [arrowV.x , arrowV.y , arrowV.z , 0 , 
                    cross1.x ,cross1.y , cross1.z , 0 ,
                    cross2.x , cross2.y , cross2.z , 0,
                    0,0,0,1]
        matrixM = om.MMatrix()
        om.MScriptUtil.createMatrixFromList(matrixV , matrixM)
        matrixFn = om.MTransformationMatrix(matrixM)
        rot = matrixFn.eulerRotation()
        rotValues = [pm.dt.degrees(rot.x), 
                    pm.dt.degrees(rot.y), 
                    pm.dt.degrees(rot.z)]

    loc = None
    if createLoc == True:
        loc = pm.spaceLocator(n='pvPosition_loc01')
        pm.xform(loc, ws=True ,t=transValues, ro=rotValues)

    returnDict = {'translation':transValues, 'rotation':rotValues, 'locator':loc}
    return returnDict

def copyName(parent=None, child=None, shape=True):
    """
    Rename child to be the same name as parent. *User Selection
        args:
            parent = The source of the name.(PyNode)
            child = The child that will be rename to be the same name as parent. (PyNode)
            shape = Rename also the shape node or not. (bool)

        return: result of renaming by comparing child to the parent name. (bool)
    """

    if not parent or not child:
        sels = getSel(num='inf')
        if sels != 2:
            return
        parent = sels[0]
        child = sels[1]

    result = False
    parentName = parent.nodeName()
    child.rename(parentName)
    parentShpName = ''
    if shape == True:
        parentShpName = parent.getShape().nodeName()
        childShp = child.getShape()
        childShp.rename(parentShpName)

    if child.nodeName() == parent.nodeName():
        result = True
    return result

def checkIfPly(obj=None):
    """
    Check if object is a transform of a poly mesh. 
        args:
            obj = The object to check. (PyNode) *User Selection

        return: result (bool)
    """
    ret = False
    if not obj:
        obj = getSel()
        if not obj:
            return ret
    elif not isinstance(obj, pm.nt.Transform):
        return ret 

    
    try: 
        shp = obj.getShape(ni=True)
        if isinstance(shp, pm.nt.Mesh) == True:
            ret = True
    except: pass

    return ret

def setUv(source=None, destination=None):
    """
    Set UV (manually) of the destination mesh to be exactly the same as the source mesh. *User Selection
        user selection:
            1. source transform
            2. destination transform
        args:
            source = The source object. (PyNode)
            destination = The destination object to set. (PyNode)

        return: result (bool)
    """
    if not source or not destination:
        sels = getSel(num='inf')
        if sels < 2:
            return False
        source = sels[0]
        destinations = sels[1:]

    for destination in destinations:
        if checkIfPly(source) == False or checkIfPly(destination) == False :
            return False

        sourceShp = source.getShape(ni=True)
        destinationShp = destination.getShape(ni=True)
        desUvSet = destinationShp.getCurrentUVSetName()

        toSet = None
        origShp = getOrigShape(obj=destination, includeUnuse=False)
        if origShp:
            origShp.setIntermediate(False)
            toSet = origShp
        else:
            toSet = destinationShp

        sourceUvSet = sourceShp.getCurrentUVSetName()
        toSetUvSet = toSet.getCurrentUVSetName()

        try:
            sAssignedUVs = sourceShp.getAssignedUVs(sourceUvSet)
            sUVs = sourceShp.getUVs(sourceUvSet)

            toSet.clearUVs()
            toSet.setUVs(sUVs[0], sUVs[1], toSetUvSet)
            toSet.assignUVs(sAssignedUVs[0], sAssignedUVs[1], toSetUvSet)
        except Exception, e:
            print e
            pass
        
        # delete history
        pm.delete(toSet, ch=True)

        # turn intermediate back on
        if origShp:
            toSet.setIntermediate(True)
        # print sourceShp, toSet

        # force refresh the shape
        pm.dgdirty(destinationShp.inMesh)

        # perform post-check
        # srcUvs = sourceShp.getUVs(uvSet=sourceUvSet)
        # desUvs = toSet.getUVs(uvSet=desUvSet)

        # if srcUvs == desUvs:
        #     return True
        # else:
        #     return False


def copyUv(parent=None, child=None, deleteHistory=True, transferShade=False, rename=False, printRes=True):
    """
    Transfer UV, shder assigned, name from one polygon to others.
        args:
            parent = The source polygon.(PyNode)
            child = The child(s) that will recieve all the transfer. (list(PyNode))
            deleteHistory = To delete history or not. (bool)
            transferShade = To transfer shader assinged to the parent to child(s) or not. (bool)
            rename = To rename the child(s) (also the shape node) to be the same name as the parent or not. (bool)

        return: None
    """


    if not parent or not child:
        sels = getSel(num='inf')
        if sels < 2:
            return
        parent = sels[0]
        child = sels[1:]

    parentShp = parent.getShape(ni=True)
    childShps = []

    try:
        parentUvSetname = parentShp.getCurrentUVSetName()
    except:
        om.MGlobal.displayWarning('No Uv set on %s' %parentShp.nodeName())
        return {'uv':False, 'rename':False, 'shade':False}

    for c in child:
        interm = False
        toTransfer = None
        shp = c.getShape(ni=True)
        origShp = getOrigShape(obj=c, includeUnuse=False)

        if origShp:
            toTransfer = origShp
        if toTransfer:
            toTransfer.setIntermediate(False)
            interm = True
        # just transfer uv to the shape node and leave input history...
        else:
            toTransfer = shp

            if not toTransfer:
                continue

        uvRes, copyRes, shadeRes = False, False, False
        if parentShp and toTransfer:        
            pm.transferAttributes( parentShp, toTransfer,
                                transferPositions=0,
                                transferNormals=0,
                                transferColors=0, 
                                transferUVs=2, 
                                sampleSpace=4 )

            shp.setCurrentUVSetName(parentUvSetname)
            toTransfer.setCurrentUVSetName(parentUvSetname)

            #check for UV transfer result
            pUvs = parentShp.getUVs(uvSet=parentUvSetname)
            cCurrentUvSet = toTransfer.getCurrentUVSetName()
            cUvs = toTransfer.getUVs(uvSet=cCurrentUvSet)

            if pUvs == cUvs:
                uvRes = True

            if rename == True:
                copyRes = copyName(parent=parent, child=c, shape=True)

            if transferShade == True:
                shadeRes = transferShadeAssign(parent=parent, child=c)

            if deleteHistory == True:
                pm.delete(toTransfer, ch=True)
            
            if interm == True:
                toTransfer.setIntermediate(True)

        if printRes == True:
            print('\nFrom  %s  to  %s' %(parentShp, toTransfer)),
            print('\nUV Transfer: %s\nRename: %s\nTransfer Shader: %s' %(uvRes, copyRes, shadeRes))
            if interm == False and deleteHistory == True:
                pm.warning('History deleted on  %s. Check your mesh for lost input(s).' %toTransfer)
    return {'uv':uvRes, 'rename':copyRes, 'shade':shadeRes}

def getCrvCvPosStr(crv=None, copyToClipboard=True, newLine=3):
    """
    Given a NURBS curve, will return all of its CVs world position. *User Selection
        args:
            crv = The source NURBS curve.(PyNode)
            copyToClipboard = To copy the result to clipboard or not? (bool)
            newLine = How many vertex positions until the text get to new line. (int)

        return: CVs position (string(list(tuple)))
    """

    curve = None
    if crv: 
        if isinstance(crv, str):
            curve = pm.PyNode(crv)
        else:
            curve = crv
    else:
        sel = getSel()
        curve = sel
    if not curve:
        return

    crvShp = curve.getShape()
    if not isinstance(crvShp, (pm.nt.NurbsCurve)):
        return False

    numCvs = curve.numCVs()
    crvLongName = curve.longName()
    cvPos = '['
    counter = 1
    getToNewLine = False
    counter = 1

    for i in range(numCvs):
        if counter >= newLine:
            getToNewLine = True
        cv = pm.PyNode('%s.cv[%s]' %(crvLongName, str(i)))
        points = pm.pointPosition(cv, w=True)
        pos = '(%.5f, %.5f, %.5f)' %(points[0], points[1], points[2])
        cvPos += pos
        if i != numCvs-1:
            cvPos += ', '
            if getToNewLine == True:
                cvPos += '\n'
                getToNewLine = False
                counter = 1
            else:
                counter += 1            
        else:
            cvPos += ']'    

    if copyToClipboard == True:
        addToClipBoard(cvPos)

    print cvPos
    return cvPos

def get2dDistance(a, b):
    return math.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2)

def getDistanceFromPosition(aPos, bPos):
    """
    Calculate distance between two given positions.
        args:
            aPos = The A point.(list[x, y, z])
            bPos = The B point.(list[x, y, z])

        return: Distance between.(float)
    """

    ax, ay, az = float(aPos[0]) ,float(aPos[1]), float(aPos[2])
    bx, by, bz = float(bPos[0]) ,float(bPos[1]), float(bPos[2])
    return math.sqrt((ax - bx)**2 + (ay - by)**2 + (az - bz)**2)

def triangleArea(v1, v2, v3):
    c1 = v1 ^ v2
    c2 = v2 ^ v3
    c3 = v3 ^ v1
    vec = []
    vec.append(c1[0] + c2[0] + c3[0])
    vec.append(c1[1] + c2[1] + c3[1])
    vec.append(c1[2] + c2[2] + c3[2])
    area = math.sqrt((vec[0]*vec[0]) + (vec[1]*vec[1]) + (vec[2]*vec[2]))/2.0
    return area

def quadArea(v1, v2, v3, v4):
    a1 = triangleArea(v1, v2, v3)
    a2 = triangleArea(v3, v4, v2)
    return (a1 + a2)

def computePolysetVolume(objs=[]):
    if not objs:
        objs = getSel(num='inf')
        if not objs:
            return

    objs = [i for i in objs if checkIfPly(i)]
    dups = [i for i in pm.duplicate(objs, rr=True)]

    unlockChannelbox(obj=dups, heirachy=True, t=True, r=True, s=True)
    pm.makeIdentity(dups, apply=1, t=1, r=1, s=1)

    totalVolume = 0
    for obj in xrange(len(dups)):
        pobj = dups[obj]
        pobjName = pobj.getShape().longName()
        meshFn = getMfnMesh(pobjName)
        numFaces = meshFn.numPolygons()
        normals = om.MFloatVectorArray()

        for i in xrange(numFaces):
            nm = om.MVector()
            meshFn.getPolygonNormal(i, nm, om.MSpace.kObject)

            nLen = math.sqrt((nm.x*nm.x) + (nm.y*nm.y) + (nm.z*nm.z))

            if nLen > 0.0 and nm.z != 0.0:
                nz = nm.z/nLen
                verts = om.MIntArray()
                meshFn.getPolygonVertices(i, verts)

                nVerts = verts.length()
                val = 0.0
                if nVerts == 3:
                    v1 = om.MPoint()
                    v2 = om.MPoint()
                    v3 = om.MPoint()

                    meshFn.getPoint(verts[0], v1, om.MSpace.kObject)
                    meshFn.getPoint(verts[1], v2, om.MSpace.kObject)
                    meshFn.getPoint(verts[2], v3, om.MSpace.kObject)

                    A = triangleArea(om.MVector(v1), om.MVector(v2), om.MVector(v3))
                    val = A*nz*(v1[2] + v2[2] + v3[2])/3.0
                elif nVerts == 4:
                    v1 = om.MPoint()
                    v2 = om.MPoint()
                    v3 = om.MPoint()
                    v4 = om.MPoint()

                    meshFn.getPoint(verts[0], v1, om.MSpace.kObject)
                    meshFn.getPoint(verts[1], v2, om.MSpace.kObject)
                    meshFn.getPoint(verts[2], v3, om.MSpace.kObject)
                    meshFn.getPoint(verts[3], v4, om.MSpace.kObject)

                    A = quadArea(om.MVector(v1), om.MVector(v2), om.MVector(v3), om.MVector(v4))
                    val = A*nz*(v1[2] + v2[2] + v3[2] + v4[2])/4.0
                
                totalVolume += val

    pm.delete(dups)
    # pm.select(objs, r=True)
    return totalVolume

def findRelatedSkinCluster(obj=None):
    """
    Find the skinCluster node related to the given object.
        args:
            obj = The object to find. (PyNode) *User Selection

        return: skinCluster node(PyNode)
    """

    if not obj:
        obj = getSel()

    
    relatedSkinCluster = None
    shp = obj.getShape(ni=True)
    skcs = shp.listHistory(type='skinCluster')
    if skcs:
        relatedSkinCluster = skcs[0]

    return relatedSkinCluster

def getOrigShape(obj=None, includeUnuse=True):
    """
    Get the orig shape node of given object.
        args:
            obj = The object to find. (PyNode) *User Selection
            includeUnuse = To include the unuse orig shpape node or not. (bool)

        return: Orig shape node(PyNode)
    """

    if not obj:
        obj = getSel()
    shps = obj.getShapes()
    if not shps or len(shps) <= 1:
        return
    usedOrigShps = []
    extraOrigShps = []
    for i, shp in enumerate(shps):
        # intStatus = shp.isIntermediate()
        # if 'Orig' in shp.nodeName() or intStatus == True:
        #   origShps.append(shp)
        ins = shp.inMesh.inputs()
        outs = shp.outMesh.outputs() + shp.worldMesh.outputs()
        if not ins and outs:
            usedOrigShps.append(shp)
        elif not ins and not outs:
            extraOrigShps.append(shp)
    if includeUnuse == True:
        return usedOrigShps + extraOrigShps
    else:
        if len(usedOrigShps) > 1:
            om.MGlobal.displayError('More than one origShape being used.')
        if usedOrigShps:
            return usedOrigShps[0]

def toggleShowOrigShape(objs=[]):
    if not objs:
        objs = getSel(num='inf')
        if not objs:
            return
    for obj in objs:
        shp = obj.getShape()
        origShp = getOrigShape(obj=obj, includeUnuse=False)
        if shp and origShp and shp != origShp:
            currVal = shp.isIntermediate()

            shp.intermediateObject.set(not(currVal))
            origShp.intermediateObject.set(currVal)
    pm.select(objs, r=True)

def cleanUnuseOrigShape(obj=[]):
    """
    Get the orig shape node of given object.
        args:
            obj = The object to find. (PyNode) *User Selection

        return: Deleted unuse orig shape node(s) list(PyNode)
    """

    if not obj:
        obj = getSel(num='inf')
        if isinstance(obj, (list, tuple)) == False:
            obj = [obj]
    unuseOrigNames = []
    for i in obj:
        origShps = getOrigShape(obj=i, includeUnuse=True)
        if origShps:
            for shp in origShps:
                outs = shp.outputs()
                if not outs:
                    unuseOrigNames.append(shp.nodeName())
                    try:
                        shp.setIntermediate(False)
                        pm.delete(shp)
                    except:
                        pass

    return unuseOrigNames

def copySkinWeight(child=[], parent=None, removeUnuse=True, cleanUnuseShp=True):
    """
    Copy skin weight from the parent to child(s). *User Selection(parent, childs...)
        args:
            child = All the children. list(PyNode, str) 
            parent = The parent. (PyNode, str) 
            removeUnuse = Also remove joint(s) that has no influence. (bool) 
            cleanUnuseShp = Also clean unuse orig shape node. (bool) 

        return: The newly created skinCluster node(s). list(PyNode)
    """

    childs = []
    if not child or not parent:
        sels = getSel(num='inf')
        if len(sels) < 2:
            return
        parent = sels[0]
        childs = sels[1:]
    else:
        if isinstance(child, (str, list, tuple)):
            for c in child:
                pyNode = pm.PyNode(c)
                childs.append(pyNode)
        if isinstance(parent, str):
            parent = pm.PyNode(parent)
        if not isinstance(child, (list, tuple)):
            childs = [child]

    if not childs or not parent:
        return

    #get parent's skinCluster, then get all asscociate joints
    sc = findRelatedSkinCluster(parent)

    if not sc:
        pm.error('The parent object has no skinCluster!')

    if checkMod(check='ctrl'):
        removeUnuse = False
    if checkMod(check='shift'):
        cleanUnuseShp = False

    jnts = pm.listConnections(sc, type='joint')
    newScs = []

    for c in childs:
        cSc = findRelatedSkinCluster(c)
        if cSc:
            #add influence
            cJnts = pm.listConnections(cSc, type='joint')
            toAddJnt = list(set(jnts) - set(cJnts))
            pm.skinCluster(c, e=True, ai=toAddJnt)
            newScs.append(cSc)
        else:
            #smooth bind
            cSc = pm.skinCluster(c, jnts, tsb=True)
            newScs.append(cSc)

        #copy skin weight
        pm.copySkinWeights(ss=sc, ds=cSc, noMirror=True, nr=True, 
                        sa='closestPoint', ia='closestJoint')

        if removeUnuse == True:
            nonZeroJnts = pm.skinCluster(cSc, q=True, weightedInfluence =True)
            allInfJnt = pm.skinCluster(cSc, q=True, inf =True)
            toRemove = [jnt for jnt in allInfJnt if jnt not in nonZeroJnts]
            pm.skinCluster(cSc, e=True, ri=toRemove)
            print '\n%s Unused influence removed.' %len(toRemove),

    if cleanUnuseShp == True:
        unuseOrigNames = cleanUnuseOrigShape(childs)
        print '\n%s Unuse orig shape(s) deleted.\n%s' %(len(unuseOrigNames), unuseOrigNames),

    pm.select(parent)
    return newScs

def setJntLockInfluenceWeights(jnts=[], value=False):
    if not jnts:
        jnts = getSel(num='inf', selType='joint')
        if not jnts:
            return
    for j in jnts:
        j.lockInfluenceWeights.set(value)

def getBshNodeFromTransform(obj=None, source=True, search=''):
    """
    Get the blendShape node associated with the given transform object.
        args:
            obj = The object to find. (PyNode) *User Selection
            source = The object is the blendshape target? (bool)
            search = Search for sepecific blendshape node name. (str)

        return: Related blendshapde node(s) list(PyNode)
    """

    if not obj:
        obj = getSel()
    if not obj:
        return

    dVal = not source

    meshes = [i for i in pm.listRelatives(obj, ad=True, type='mesh') if i.isIntermediate() == False]
    his, bshs = [], []

    his = [h for h in pm.listHistory(meshes[0], f=dVal, pdo=True) if h not in his and isinstance(h, pm.nt.BlendShape)]

    if search != '':
        bshs = [h for h in his if search in his]
    else:
        bshs = his

    return bshs

def getConnectedSg(shapeNode=None):
    """
    Given a shape node will find the shading engine assigned to it.
        args:
            shapeNode = The shape node to find. (PyNode) 

        return: The connected shading engine. (PyNode)
    """

    sgs = list(set(pm.listConnections(shapeNode, d=True, type='shadingEngine')))
    if not sgs:
        return
    if len(sgs)>1:
        pm.warning('The object has more than one shadingEngine assigned to it, will use first one.')

    return sgs[0]

def separateReorderMesh():
    """
    Separate the selected face(s) from a mesh and recreate(combine, merge) the mesh to have orderd vertex number
    as the separated components are listed first. Great method for separating huge mesh for doing blendshape. 

        return: list[Separated Geo = The piece cut off
                Recombinded Geo = The newly reordered mesh]
    """

    #get polygon faces selected
    selFaces = filter(lambda x: isinstance(x, (pm.MeshFace)), pm.ls(sl=True, l=True, fl=True))

    #get object selected
    shapeNode = pm.ls(sl=True, o=True)

    #get shade assigned
    sg = getConnectedSg(shapeNode)

    #selection error checking
    if len(shapeNode) != 1:
        pm.error('Polygon face(s) from only one geometry should be selected.')

    #get transform
    try:
        tranNode = shapeNode[0].getParent()
        currentName = tranNode.name()
    except:
        return

    #duplicate object and suffix old one '_old' and hide it..
    oldTranNode = tranNode.duplicate()[0]
    oldTranNode.rename(currentName+'_old')
    pm.hide(oldTranNode)

    #get face number for the head and the body and separate them
    tranNodeBody = tranNode.duplicate()[0]
    numFace = pm.polyEvaluate(shapeNode, f=True)
    headFaceNums = []
    headFace = []
    bodyFaceNums = []
    bodyFace = []

    for face in selFaces:
        parenNum = face.split('.f')[-1]
        num = str(parenNum[1:-1])
        headFaceNums.append(num)
        headFace.append('%s.f[%s]' %(tranNodeBody, num))
    for i in range(numFace) :
        if str(i) not in headFaceNums:
            bodyFaceNums.append(str(i))
            bodyFace.append('%s.f[%s]' %(tranNode, i))
    
    #now, actually delete what we don't need
    pm.delete(bodyFace, headFace)
    #duplicate head geo 
    headGeo = tranNode.duplicate()[0]

    #combine and merge head back to the body to achieve new-re-arranged vert numbers!
    newGeo = pm.polyUnite(tranNode, tranNodeBody, ch=False, n='body_ply')[0]

    pm.polyMergeVertex(newGeo, ch=False, d=0.0001, am=True)

    #reassign shade
    try:
        pm.sets(sg, e=True, nw=True, fe=headGeo.getShape(ni=True))
        pm.sets(sg, e=True, nw=True, fe=newGeo.getShape(ni=True))
        pm.delete(oldTranNode)
        pm.delete([tranNode, tranNodeBody])
    except: pass


    pm.select(cl=True)
    print('Separate and reorder vertex number: Success!')

    return [headGeo, newGeo]

def strVector(vec):
    """
    Convert vector to string.
        args:
            vec = vector to convert. list(x, y, z) or pm.dt.Vector

        return: vector (str)
    """

    if isinstance(vec, pm.dt.Vector) == False:
        try:
            vec = pm.dt.Vector(vec)
        except:
            return
    vec.normalize()

    if vec == pm.dt.Vector(1, 0, 0):
        return '+x'
    elif vec == pm.dt.Vector(0, 1, 0):
        return '+y'
    elif vec == pm.dt.Vector(0, 0, 1):
        return '+z'
    elif vec == pm.dt.Vector(-1, 0, 0):
        return '-x'
    elif vec == pm.dt.Vector(0, -1, 0):
        return '-y'
    elif vec == pm.dt.Vector(0, 0, -1):
        return '-z'
    else:
        return ''

def vectorStr(string, mult=1):
    """
    Convert string to vector.
        args:
            string = string to be converted ('x', 'y', '+z', etc..)

        return: vector 
    """

    if isinstance(string, str) == False:
        try:
            string = str(string)
        except:
            return None

    if string == '+x' or string =='x':
        return pm.dt.Vector(mult, 0, 0)
    elif string == '+y' or string == 'y':
        return pm.dt.Vector(0, mult, 0)
    elif string == '+z' or string == 'z':
        return pm.dt.Vector(0, 0, mult)
    elif string == '-x':
        return pm.dt.Vector(mult*-1, 0, 0)
    elif string == '-y':
        return pm.dt.Vector(0, mult*-1, 0)
    elif string == '-z':
        return pm.dt.Vector(0, 0, mult*-1)
    else:
        return None

def getVector(obj=None):
    if not obj:
        obj = getSel()

    m = obj.worldMatrix.get()
    return {'x':pm.dt.Vector(m[0][0], m[0][1], m[0][2]), 
            'y':pm.dt.Vector(m[1][0], m[1][1], m[1][2]),
            'z':pm.dt.Vector(m[2][0], m[2][1], m[2][2])}

def crossAxis(a, b):
    aVec = vectorStr(a)
    bVec = vectorStr(b)
    cross = aVec.cross(bVec)
    crossStr = strVector(cross)
    return crossStr

def deleteAllTypeInScene(type):
    """
    Delete all objects in the scene by the given type.
        args:
            type = The type to delete. (str)

        return: list(deleted nodes)
    """

    nodes = pm.ls(type=type)
    deletedNodes = []
    for node in nodes:
        try:
            pm.delete(node)
            deletedNodes.append(node.nodeName())
        except:
            om.MGlobal.displayWarning('Cannot delete  %s' %node.nodeName())

    return deletedNodes

def setAllPanelToBB():
    """
    Set all model panel(viewable panel) to display objects in bounding box mode.

        return: None
    """

    allPanels = pm.getPanel(type='modelPanel')
    for panel in allPanels:
        pm.modelEditor(panel, e=True, displayAppearance='boundingBox')
        pm.modelEditor(panel, e=True,  
        df=False, dim=False, ca=False, hs=False, ha=False, ikh=False, j=False, sds=False,
        lt=False, lc=False, ncl=False, npa=False, nr=False, nc=False, str=False, hu=False,
        dy=False, pv=False, pl=False, fl=False, fo=False, dc=False, tx=False, mt=False,
        m=True, ns=True, pm=True )

def getMirroredRotationMatrix(obj=None):
    """
    Create new matrix that has 'mirrored rotation' from the given obj's matrix.
        args:
            objs = The object to calculate. (PyNode) *User Selection

        return: The new 3*3 matrix. (list)
    """

    if not obj:
        obj = getSel()
        if not obj:
            return

    objMatrix = obj.getMatrix(worldSpace=True)
    xMat = objMatrix[0]
    yMat = objMatrix[1]
    zMat = objMatrix[2]
    tMat = objMatrix[3]

    newMatrix = [xMat[0], xMat[1]*-1, xMat[2]*-1,
                 yMat[0], yMat[1]*-1, yMat[2]*-1,
                 zMat[0], zMat[1]*-1, zMat[2]*-1]

    return newMatrix

def setMirrorRotation(objs=[], unparent=True):
    """
    Set rotation axis of one transform to be the 'mirrored' of another using matrix calculation.
        args:
            objs = The objects to copy. The first is the source the second is the destination. list(PyNode)[2] *User Selection
            unparent = Unparent all the children before setting rotation value to avoid popping. (bool)

        return: None
    """

    if not objs:
        objs = getSel(num=2)
        if not objs:
            return

    miMat = getMirroredRotationMatrix(objs[0])
    oldMat = objs[1].getMatrix(worldSpace=True)
    xMat = oldMat[0]
    yMat = oldMat[1]
    zMat = oldMat[2]
    tMat = oldMat[3]


    newMat = [miMat[0], miMat[1], miMat[2], xMat[3],
              miMat[3], miMat[4], miMat[5], yMat[3],
              miMat[6], miMat[7], miMat[8], zMat[3],
              tMat[0], tMat[1], tMat[2], tMat[3]]


    matrixM = om.MMatrix()
    om.MScriptUtil.createMatrixFromList(newMat , matrixM)
    matrixFn = om.MTransformationMatrix(matrixM)
    rot = matrixFn.eulerRotation()
    rotValues = [pm.dt.degrees(rot.x), pm.dt.degrees(rot.y), pm.dt.degrees(rot.z)]

    childs = objs[1].getChildren(type='transform')

    if unparent == True and childs:
        pm.parent(childs, w=True)
        pm.xform(objs[1], ws=True, ro=rotValues)
        pm.parent(childs, objs[1])
    else:
        pm.xform(objs[1], ws=True, ro=rotValues)

    pm.select(objs[1], r=True)

def copyAxisRotation(objs=[], **kwargs):
    """
    Set rotation of one transform to be the exact same as another using matrix calculation.
        args:
            objs = The objects to copy. The first is the source the second is the destination. list(PyNode)[2] *User Selection
            unparent = Unparent all the children before setting rotation value to avoid popping. (bool)

        return: None
    """

    if not objs:
        objs = getSel(num=2)
        if not objs:
            return

    pMat = objs[0].getMatrix(worldSpace=True)
    cMat = objs[1].getMatrix(worldSpace=True)

    newMat = [pMat[0][0], pMat[0][1], pMat[0][2], cMat[0][3],
              pMat[1][0], pMat[1][1], pMat[1][2], cMat[1][3],
              pMat[2][0], pMat[2][1], pMat[2][2], cMat[2][3],
              cMat[3][0], cMat[3][1], cMat[3][2], cMat[3][3]]


    matrixM = om.MMatrix()
    om.MScriptUtil.createMatrixFromList(newMat , matrixM)
    matrixFn = om.MTransformationMatrix(matrixM)
    rot = matrixFn.eulerRotation()
    rotValues = [pm.dt.degrees(rot.x), pm.dt.degrees(rot.y), pm.dt.degrees(rot.z)]

    # currentRot = pm.xform(objs[1], ws=True, q=True, ro=True)

    # childs = objs[1].getChildren()
    # shapes = (pm.nt.Mesh, pm.nt.NurbsCurve, pm.nt.NurbsSurface)

    # if childs:
    #     for c in childs:
    #         if isinstance(c, shapes):
    #             # create temp transform
    #             tempTrans = pm.group(em=True)
    #             # set temp transform to current rotate
    #             pm.xform(tempTrans, ws=True, ro=currentRot)
    #             # parent the shape to temp transform (this should not pop)
    #             pm.parent([c, tempTrans], r=True, s=True)
                
    #             # set the child value
    #             pm.xform(objs[1], ws=True, ro=rotValues)

    #             # parent temp transform to the child
    #             pm.parent(tempTrans, objs[1])
    #             # freeze temp transform
    #             pm.makeIdentity(tempTrans, a=True, r=True, t=True, s=True )
    #             # re-parent shape to where it was
    #             pm.parent([c, objs[1]], r=True, s=True)
    #             pm.delete(tempTrans)
    #         else:
    #             # pm.parent(c, w=True)
    #             pm.xform(objs[1], ws=True, preserve=True, ra=rotValues)
    #             # pm.parent(c, objs[1])

    # else:
    #     pm.xform(objs[1], ws=True, ro=rotValues)
    pm.rotate(objs[1], rotValues, ws=True, pcp=True)
    # pm.xform(objs[1], ws=True, preserve=True, ra=rotValues)
    # pm.select(objs, r=True)

def cleanPath(path):
    """
    Given a directory path, will remove all spaces and unwanted character(s) from it.
        args:
            path = The directory path to clean. (str) 

        return: cleaned path(str)
    """

    #remove unwanted characters
    path = path.strip()
    path = path.replace('"', '')
    path = path.replace('\\', '/')
    path = path.replace('//', '/')
    return path

def convertOsPath(path):
    """
    Given a directory path, will remove all '/' and replace with '\\'.
        args:
            path = The directory path to convert. (str) 

        return: converted path(str)
    """
    
    #remove unwanted characters
    path = path.strip()
    path = path.replace('"', '')
    path = path.replace('/', '\\')
    path = path.replace('//', '\\')
    return path


def writeLog(toWrite, dir, mode):
    """
    Write a text file.
        args:
            toWrite = Data to write. (str)
            dir = The directory to place the written file. (str)
            mode = Mode to write. 'w' to re-write, 'r' to continue writing. (str)
        return:
            The latest file path. (str)
    """

    #write tmp log file
    logfile = open(dir, mode)
    logfile.write(toWrite)
    logfile.close()

    return logfile

def copyPasteSkinWeightVtx(source=None, destination=[]):
    if not source or not destination:
        try:        
            destination = pm.ls(sl=True, fl=True)
            source = pm.PyNode(pm.undoInfo(q=True, undoName=True).split()[-1])
            destination.remove(source)
            destination = convertSelToVtx(sels=destination)
        except:
            return

    pm.select(source, r=True)
    mel.eval('artAttrSkinWeightCopy')

    pm.select(destination, r=True)
    mel.eval('artAttrSkinWeightPaste')

def copySkinWeightVtx(source=None, destination=[]):
    if not source or not destination:
        try:        
            destination = pm.ls(sl=True, fl=True)
            source = pm.PyNode(pm.undoInfo(q=True, undoName=True).split()[-1])
            destination.remove(source)
            destination = convertSelToVtx(sels=destination)
        except:
            return

    sTransform = source.node().getParent()
    skc = findRelatedSkinCluster(sTransform)
    if not skc:
        return

    sInfs = pm.listConnections(skc.matrix, type='joint')
    sSkinValues = pm.skinPercent(skc, source, q=True, v=True)

    infDict = {}
    for inf, val in zip(sInfs, sSkinValues):
        if val != 0:
            infDict[inf] = val

    dSkc, oldSkc = None, None

    for des in destination:
        dTransform = des.node().getParent()
        dSkc = findRelatedSkinCluster(dTransform)
        if dSkc:
            # this is the first vertex or, we've crossed to another polygon
            if dSkc != oldSkc:          
                liwDict = {}
                # get current joints, store lock values and lock them
                dInfs = pm.listConnections(dSkc.matrix, type='joint')
                for j in dInfs:
                    liwDict[j] = j.liw.get()
                    j.liw.set(True)

                # find joint to add influence, if neccessary
                toAddJnt = list(set(infDict.keys()) - set(dInfs))
                if toAddJnt:
                    pm.skinCluster(dSkc, e=True, lw=True, ai=toAddJnt)
                    for j in toAddJnt:
                        liwDict[j] = False

                    dInfs.extend(toAddJnt)
                    print '\nAdded Influnces\n%s\n%s\n' %(dTransform, '\n\t'.join((i.nodeName() for i in toAddJnt)))

            for j in dInfs:
                j.liw.set(False)

            for j, w in infDict.iteritems():
                pm.skinPercent(dSkc, des, tv=(j, w))
                j.liw.set(True)

            for j, v in liwDict.iteritems():
                j.liw.set(v)

        oldSkc = dSkc
        

    pm.select(destination, r=True)

def placeJntAtLoopCenter(rad=1.0):
    global jntPlacedAtLoopCenter
    jnt = None
    loc = snapToComponentCenter()
    if not checkMod('shift'):
        orientToComponentNormals()
    if loc:
        jnt = pm.createNode('joint')
        jnt.radius.set(rad)
        snapTransform('parent', loc, jnt, False, True)
        pm.delete(loc)

    if not checkMod('ctrl'):
        try:
            pm.parent(jnt, jntPlacedAtLoopCenter)
        except: pass
    
    jntPlacedAtLoopCenter = jnt

def connectInMesh(parent=None, childs=[]):
    """
    Connect 'outMesh' of the parent to the 'inMesh' attribute of child(s).
        args:
            parent = The parent transform. PyNode *User Selection
            childs = Childeren to be connected. list(PyNode)
        return:
            Nothing
    """

    if not parent or not childs:
        sels = getSel(num='inf')
        if not sels or len(sels) < 2:
            om.MGlobal.displayError('Select parent then children to connect.')
            return
        parent = sels[0]
        childs = sels[1:]

    if not checkIfPly(parent):
        om.MGlobal.displayError('The parent is not a polygon object.')
        return

    parentShp = parent.getShape(ni=True)

    for c in childs:
        if not checkIfPly(c):
            continue
        cShp = c.getShape(ni=True)
        pm.connectAttr(parentShp.outMesh, c.inMesh, f=True)

def correctShapeName(objs=[]):
    """
    Rename shape node of objs to be 'nodeName' + 'Shape'
        args:
            objs = Objects to rename shape. list(PyNode) *User Selection
        return:
            Nothing
    """

    if not objs:
        objs = getSel(num='inf')
        if not objs:
            return

    for obj in objs:
        name = obj.nodeName()
        try:
            shp = obj.getShape(ni=True)
            shp.rename('%sShape' %name)
        except: pass

def getMfnMesh(obj):
    ''' 
        Return MFnMesh of the given object name.
            args :
                obj = Object name. (str)
            return:
                OpenMaya.MFnMesh of the object

    '''
    try:
        mSel = om.MSelectionList()
        mSel.add(obj)
        dMesh = om.MDagPath()
        mSel.getDagPath(0, dMesh) 
        # dMesh.extendToShape()
        return om.MFnMesh(dMesh)
    except:
        om.MGlobal.displayError('OpenMaya.MDagPath() failed on %s.' % obj)
        return None

def getMDagPath(obj):
    """
    Given mesh name as string, return MDagPath.

    """

    try:
        msl = om.MSelectionList()
        msl.add(obj)
        nodeDagPath = om.MDagPath()
        msl.getDagPath(0, nodeDagPath)
    except:
        return

    return nodeDagPath


def getMObject(obj):
    """
    Given mesh name as string, return MDagPath.

    """

    try:
        msl = om.MSelectionList()
        msl.add(obj)
        nodeDagPath = om.MObject()
        msl.getDependNode(0, nodeDagPath)
    except:
        return

    return nodeDagPath

def getClosestSurfUvFromPoint(surf, point):
    mSel = om.MSelectionList()
    mSel.add(surf.longName())

    surfMObj = om.MObject()
    mSel.getDependNode(0, surfMObj)

    fnSurf = om.MFnNurbsSurface(surfMObj)
    mpoint = om.MPoint(point[0], point[1], point[2])

    putil = om.MScriptUtil()
    putil.createFromDouble(0.0)
    paramU = putil.asDoublePtr()

    vutil = om.MScriptUtil()
    vutil.createFromDouble(0.0)
    paramV = vutil.asDoublePtr()

    fnSurf.closestPoint(mpoint, paramU, paramV, False, 1e-05)
    u = putil.getDouble(paramU)
    v = vutil.getDouble(paramV)

    return u, v

def getClosestMeshUvFromPoint(mesh, position):
    fnMesh = getMfnMesh(obj=mesh.longName())
    mPoint = om.MPoint(position[0], position[1], position[2]) 

    # craete 2FloatArray
    pArray = [0.0, 0.0]
    x1 = om.MScriptUtil()
    x1.createFromList( pArray, 2 )
    uvPoint = x1.asFloat2Ptr()

    # get the first uv set name
    uvSetNames = []
    fnMesh.getUVSetNames(uvSetNames)

    fnMesh.getUVAtPoint(mPoint, uvPoint, om.MSpace.kWorld, uvSetNames[0])
    u = om.MScriptUtil.getFloat2ArrayItem( uvPoint, 0, 0 )
    v = om.MScriptUtil.getFloat2ArrayItem( uvPoint, 0, 1 )

    return u, v

def getParallelEdgesFromClosestPointOnMesh(closestVert, closestFace):

    # get edge pairs
    mesh = closestFace.node()
    closestFaceEdges = [mesh.e[i] for i in closestFace.getEdges()]
    closestVertEdges = closestVert.connectedEdges()

    conEdgesOnFace = [e for e in closestVertEdges if e in closestFaceEdges]

    e1 = conEdgesOnFace[0]
    e1Con = conEdgesOnFace[1]

    parallelEdges = [i for i in closestFaceEdges if i not in (e1, e1Con)]
    if len(parallelEdges) == 1:  # it's a triangle
        e2 = e1Con
    else:
        e2s = [e for e in parallelEdges if e not in e1.connectedEdges()]
        e2 = e2s[0]

    return e1, e2

def getClosestComponentFromPos(mesh=None, pos=[]):
    ''' 
        Get the cloest vertex on a geo from position given.
            User selection:
                1. transform to get positon (locator? grp?)
                2. vertex 
            args :
                pos = The position to calculate. [x, y, z] list(float3)
                mesh = Transform or Mesh to get cloest vertex from position. (PyNode)
            return:
                The closest vertex(PyNode)
    '''

    if not mesh or not pos:
        sels = getSel(num=2)
        if not sels or len(sels) < 2:
            return
        mesh = sels[0]
        pos = sels[1].getRotatePivot(space='world')

    mfnMesh = getMfnMesh(obj=mesh.longName())

    pointA = om.MPoint(pos.x, pos.y, pos.z)
    pointOnMesh = om.MPoint()

    util = om.MScriptUtil()
    util.createFromInt(0)
    idPointer = util.asIntPtr()

    mfnMesh.getClosestPoint(pointA, pointOnMesh, om.MSpace.kWorld, idPointer) 
    fid = util.getInt(idPointer)

    faceVerts = om.MIntArray()
    mfnMesh.getPolygonVertices(fid, faceVerts)

    dists = []
    for vi in xrange(faceVerts.length()):
        vtxPt = om.MPoint()
        vid = faceVerts[vi]
        mfnMesh.getPoint(vid, vtxPt, om.MSpace.kWorld)
        distVec = pointA - vtxPt
        dists.append(distVec.length())

    closestVid = faceVerts[dists.index(min(dists))]
    closestVert = mesh.vtx[closestVid]
    closestFace = mesh.f[fid]

    return closestVert, closestFace

def attachToGeom(objs=[], mode='follicle', attachMethod='parent'):
    if not objs:
        objs = getSel(num='inf')
    try:
        posObj = objs[0:-1]
        geo = objs[-1]
    except:
        om.MGlobal.displayError('Invalid selection or argruments: Select a transform, then a geo.')
        return
    # print geo, posObj
    # shape and position to be passed to working functions
    shape = geo.getShape()
    geomType = shape.nodeType()

    ret = {}
    for obj in posObj:
        # figure out the naming
        spnames = nameSplit(obj.nodeName())
        name = (spnames['elem'], spnames['pos'])

        position = obj.getTranslation('world')
        if mode == 'follicle':
            if geomType == 'mesh':
                ret = createFollicleFromPosition_Mesh(shape=shape, position=position, name=name)
            elif geomType == 'nurbsSurface':
                ret = createFollicleFromPosition_Nurbs(shape=shape, position=position, name=name)
        elif mode == 'rivet':
            if geomType == 'mesh':
                ret = createRivetFromPosition_Mesh(shape=shape, position=position, name=name)
            elif geomType == 'nurbsSurface':
                ret = createRivetFromPosition_Nurbs(shape=shape, position=position, name=name)
        elif mode == 'cMuscleSurfAttach':
            if geomType == 'mesh':
                ret = createSurfAttachFromPosition_Mesh(shape=shape, position=position, name=name)

        # attach posObj
        if attachMethod == 'constraint':
            pm.parentConstraint(ret['transform'], obj, mo=True)
        elif attachMethod == 'parent':
            pm.parent(obj, ret['transform'])

    return ret

def createFollicleFromPosition_Nurbs(shape, position, name):
    u, v = getClosestSurfUvFromPoint(shape, position)
    mnrU, mxrU = shape.minMaxRangeU.get()
    mnrV, mxrV = shape.minMaxRangeV.get()
    u = float(u) / mxrU
    v = float(v) / mxrV
    follicleNode = pm.createNode("follicle")
    follicleNode.simulationMethod.set(0)
    follicleT = pm.listRelatives(follicleNode, parent=True)[0]
    follicleT.rename('%s%s_fol' %name)

    shape.attr("local").connect(follicleNode.attr("inputSurface")) 
    shape.attr("worldMatrix").connect(follicleNode.attr("inputWorldMatrix")) 

    follicleNode.attr("outTranslate").connect(follicleT.attr("translate")) 
    follicleNode.attr("outRotate").connect(follicleT.attr("rotate")) 

    follicleNode.attr("parameterU").set(u) 
    follicleNode.attr("parameterV").set(v) 

    return {"node":follicleNode, "transform":follicleT}

def createFollicleFromPosition_Mesh(shape, position, name): 
    u, v = getClosestMeshUvFromPoint(mesh=shape, position=position)

    follicleNode = pm.createNode("follicle") 
    follicleT = pm.listRelatives(follicleNode, parent=True)[0] 
    follicleT.rename('%s%s_fol' %name)

    shape.attr("outMesh").connect(follicleNode.attr("inputMesh")) 
    shape.attr("worldMatrix").connect(follicleNode.attr("inputWorldMatrix")) 

    follicleNode.attr("outTranslate").connect(follicleT.attr("translate")) 
    follicleNode.attr("outRotate").connect(follicleT.attr("rotate")) 

    follicleNode.attr("parameterU").set(u) 
    follicleNode.attr("parameterV").set(v) 

    return {"node":follicleNode, "transform":follicleT}

def createRivetFromPosition_Mesh(shape, position, name): 
    # get the closest point on mesh and face ID
    closestVert, closestFace = getClosestComponentFromPos(mesh=shape, pos=position)
    e1, e2 = getParallelEdgesFromClosestPointOnMesh(closestVert, closestFace)

    rivetLoc = pm.spaceLocator()
    rivetLoc.rename('%sRivet%s_loc' %name)
    tmpSurf, tmpLoft = pm.loft(e1, e2)

    cfme1 = pm.createNode('curveFromMeshEdge', n=naming.NAME('%s1' %name[0], name[1], naming.CFME))
    cfme2 = pm.createNode('curveFromMeshEdge', n=naming.NAME('%s2' %name[0], name[1], naming.CFME))

    pm.connectAttr(shape.worldMesh[0], cfme1.inputMesh)
    cfme1.edgeIndex[0].set(e1.indices()[0])
    pm.connectAttr(shape.worldMesh[0], cfme2.inputMesh)
    cfme2.edgeIndex[0].set(e2.indices()[0])

    loft = pm.createNode('loft', n=naming.NAME('%sRivet' %name[0], name[1], naming.LOFT))
    pm.connectAttr(cfme1.outputCurve, loft.inputCurve[0])
    pm.connectAttr(cfme2.outputCurve, loft.inputCurve[1])

    pos = pm.createNode('pointOnSurfaceInfo', n=naming.NAME('%sRivet' %name[0], name[1], naming.POSI))
    pm.connectAttr(loft.outputSurface, pos.inputSurface)
    aimNode = pm.createNode('aimConstraint', n=naming.NAME('%sRivet' %name[0], name[1], naming.AIMCON))
    aimNode.aimVector.set([0, 1, 0])
    aimNode.upVector.set([0, 0, 1])
    aimNode.worldUpType.set(3)
    pm.parent(aimNode, rivetLoc)

    pm.connectAttr(pos.position, rivetLoc.translate)
    pm.connectAttr(pos.normal, aimNode.target[0].targetTranslate)
    pm.connectAttr(pos.tangentV, aimNode.worldUpVector)
    pm.connectAttr(aimNode.constraintRotate, rivetLoc.rotate)

    u, v = getClosestSurfUvFromPoint(tmpSurf.getShape(ni=True), position)
    pos.parameterU.set(u)
    pos.parameterV.set(v)

    pm.delete([tmpLoft, tmpSurf])
    return {"node":pos, "transform":rivetLoc}

def createRivetFromPosition_Nurbs(shape, position, name, aimVector=[0, 1, 0], upVector=[0, 0, 1]): 
    rivetLoc = pm.spaceLocator()
    rivetLoc.rename('%sRivet%s_loc' %name)

    pos = pm.createNode('pointOnSurfaceInfo', n=naming.NAME('%sRivet' %name[0], name[1], naming.POSI))
    pm.connectAttr(shape.worldSpace[0], pos.inputSurface)
    aimNode = pm.createNode('aimConstraint', n=naming.NAME('%sRivet' %name[0], name[1], naming.AIMCON))
    aimNode.aimVector.set(aimVector)
    aimNode.upVector.set(upVector)
    aimNode.worldUpType.set(3)
    pm.parent(aimNode, rivetLoc)

    pm.connectAttr(pos.position, rivetLoc.translate)
    pm.connectAttr(pos.tangentV, aimNode.target[0].targetTranslate)
    pm.connectAttr(pos.normal, aimNode.worldUpVector)
    pm.connectAttr(aimNode.constraintRotate, rivetLoc.rotate)

    u, v = getClosestSurfUvFromPoint(shape, position)
    pos.parameterU.set(u)
    pos.parameterV.set(v)
    return {"node":pos, "transform":rivetLoc}

def createSurfAttachFromPosition_Mesh(shape, position, name):
    # get the closest point on mesh and face ID
    closestVert, closestFace = getClosestComponentFromPos(mesh=shape, pos=position)
    e1, e2 = getParallelEdgesFromClosestPointOnMesh(closestVert, closestFace)

    cmsa = pm.createNode('cMuscleSurfAttach', n=naming.NAME(name[0], name[1], '%sShape' %naming.CMSA))
    cmsaTr = cmsa.getParent()
    cmsa.visibility.set(False)
    cmsaTr.rename(naming.NAME(name[0], name[1], naming.CMSA))
    
    cmsa.uLoc.set(0)
    e1ConVerts = e1.connectedVertices()
    vValue = 0 if e1ConVerts[0] == closestVert else 1
    cmsa.vLoc.set(vValue)
    cmsa.edgeIdx1.set(e1.indices()[0])
    cmsa.edgeIdx2.set(e2.indices()[0])

    pm.connectAttr(shape.outMesh, cmsa.surfIn)
    pm.connectAttr(cmsa.outTranslate, cmsaTr.translate)
    pm.connectAttr(cmsa.outRotate, cmsaTr.rotate)

    return {"node":cmsa, "transform":cmsaTr}

def attatchFollicleToSurface(surface=None, uCount=3, vCount=8, name='posRig', createJnt=False, createCtrl=False, 
                            ctrlColor='lightBlue', size=0.1, folGrp=None, jntGrp=None, ctrlGrp=None, offset=0):
    """
    Attatch defined number of row and column of hair follicles to the given surface.
        args:
            surface = The surface to attatch. (PyNode)  *User Selection
            uCount = Number of folllicle in U direction. (int)
            vCount = Number of folllicle in V direction. (int)
            name = Naming for objects. (str)
            createJnt = Create joint or not? (bool)
            createCtrl = Create control curve for joint or not? (bool)
            ctrlColor = The color of the control. (str)
            size = The size of both the joint and control. (float)
            folGrp = Group that follicles will be parented. (PyNode)
            jntGrp = Group that joints will be parented. (PyNode)
            ctrlGrp = Group that controls will be parented. (PyNode)
            offset = Offset value (0.0 - 1.0) of follicle alignment in the up direction. (float) 

        return: dic({'trans':folTrans, 
                     'shps':folShps, 
                     'folGrp':folGrp, 
                     'jntGrp':jntGrp, 
                     'ctrlGrp':ctrlGrp, 
                     'ctrls':ctrls, 
                     'zgrps':zgrps, 
                     'jnts':jnts,
                     'folDict':folDict})
    """
    if not surface:
        surface = getSel()
        if not surface:
            return

    import nuTools.controller as controller

    surfaceShp = surface.getShape()

    if not folGrp:
        folGrp = pm.group(em=True, n='%sPosFol_grp' %name)

    if createJnt == True:
        if not jntGrp:
            jntGrp = pm.group(em=True, n='%sPosJnt_grp' %name)
        
        if createCtrl == True:  
            if not ctrlGrp:
                ctrlGrp = pm.group(em=True, n='%sPosCtrl_grp' %name)


    f, u, v = 0, 0, 0
    oddU, oddV = 1, 1
    uValue, vValue = 0, 0
    uParam = pow(uCount, -1) * 0.5 
    vParam = pow(vCount, -1) * 0.5

    folShps, folTrans = [], []
    jnts, ctrls, zgrps = [], [], []
    folDict = {}

    for v in range(0, vCount):
        vValue = vParam * (oddV+v)
        for u in range(0, uCount):
            folShp = pm.createNode('follicle')
            folTran = folShp.getParent()
            folTran.rename('%sU%iV%i_fol' %(name, u, v))

            folShps.append(folShp)
            folTrans.append(folTran)

            folShp.parameterV.set(vValue)
            uValue = (uParam * (oddU + u) * (1-offset)) + offset
            folShp.parameterU.set(uValue)

            pm.connectAttr(surfaceShp.worldMatrix[0], folShp.inputWorldMatrix, f=True)
            pm.connectAttr(surfaceShp.local, folShp.inputSurface, f=True)
            pm.connectAttr(folShp.outTranslate, folTran.translate, f=True)
            pm.connectAttr(folShp.outRotate, folTran.rotate, f=True)
            pm.parent(folTran, folGrp)

            if u not in folDict.keys():
                folDict[u] = []
            folDict[u].append(folTran)

            if createJnt == True:
                jnt = pm.createNode('joint', n='%sU%iV%i_jnt' %(name, u, v))
                jnt.radius.set(size)
                jzgrp = zgrp(jnt, element='Offset', suffix='grp')
                jnts.append(jnt)

                if createCtrl == True:
                    ctrl = controller.Controller(name='%sU%iV%i_ctrl' %(name, u, v), scale=size, st='crossSphere')
                    ctrl.setColor(ctrlColor)
                    ctrl.lockAttr(v=True)
                    ctrl.hideAttr(v=True)
                    czgrp = zgrp(ctrl, element='Offset', suffix='grp')
                    snapTransform('parent', ctrl, jzgrp, False, False)
                    snapTransform('parent', folTran, czgrp, False, False)

                    ctrls.append(ctrl)
                    zgrps.append(czgrp)
                    jnts.append(jnt)

                    pm.parent(czgrp, ctrlGrp)
                    pm.parent(jzgrp, jntGrp)
                else:
                    snapTransform('parent', folTran, jzgrp, False, False)
                    pm.parent(jzgrp, jntGrp)


            oddU += 1
            f += 1

        oddU = 1
        oddV += 1

    return {'trans':folTrans, 
            'shps':folShps, 
            'folGrp':folGrp, 
            'jntGrp':jntGrp, 
            'ctrlGrp':ctrlGrp, 
            'ctrls':ctrls, 
            'zgrps':zgrps, 
            'jnts':jnts,
            'folDict':folDict}

def getUvBorderEdges(mesh, edges=[], select=True):
    mdag = mesh.__apimdagpath__()
    meshSn = mesh.shortName()

    if edges:
        eIdArray = om.MIntArray()
        for e in edges:
            eIdArray.append(e.index())
        eComponent = om.MFnSingleIndexedComponent()
        eComponent.create(om.MFn.kMeshEdgeComponent)
        eComponent.addElements(eIdArray)
        edgeIt = om.MItMeshEdge(mdag, eComponent.object())
    else:
        edgeIt = om.MItMeshEdge(mdag)
    
    borderEdges = set()
    toSels = []
    while not edgeIt.isDone():
        vtx1 = edgeIt.index(0)
        vtx2 = edgeIt.index(1)

        conFaces = om.MIntArray()
        edgeIt.getConnectedFaces(conFaces)
        conFaces = list(conFaces)

        vtxIdArray = om.MIntArray()
        vtxIdArray.append(vtx1)
        vtxIdArray.append(vtx2)
      
        vtxComponent = om.MFnSingleIndexedComponent()
        vtxComponent.create(om.MFn.kMeshVertComponent)
        vtxComponent.addElements( vtxIdArray)
        
        vtxIt = om.MItMeshVertex(mdag, vtxComponent.object())
        while not vtxIt.isDone():
            uvIndices = om.MIntArray()
            vtxIt.getUVIndices(uvIndices, 'map1')
            uvIndices = list(uvIndices)

            uArray = om.MFloatArray()
            vArray = om.MFloatArray()
            faceIds = om.MIntArray()
            vtxIt.getUVs(uArray, vArray, faceIds, 'map1')
            faceIds = list(faceIds)

            uvIds = set()
            for cf in conFaces:
                faceOrder = faceIds.index(cf)
                uvId = uvIndices[faceOrder]
                uvIds.add(uvId)

            if len(uvIds) > 1:
                index = edgeIt.index()
                borderEdges.add(index)
                toSels.append('%s.e[%s]' %(meshSn, index))
                break
            vtxIt.next()
        edgeIt.next()

    if select and toSels:
        mc.select(toSels, r=True)
    return list(borderEdges)
        
def createLocalWorld(objs=[], constraintType='parent', attrName='localWorld', createGrp=True):
    ''' 
        Given the controller, local object and world object, the function create local_world rig for swapping between the 2 parents.
            User selection:
                1. Controller (to add attribute on)
                2. Local Object (the parent when localWorld is set to 0)
                3. World Object (the parent when localWorld is set to 1)
                4. Group (the transform to be constraint)
            args :
                objs = The list of objects (ctrl, localObj, worldObj) list(PyNode)
                attrName = The name of the switch attribute to be add. (str)
            return:
                Nothing
    '''

    if not objs or len(objs) != 4:
        objs = getSel(num=4)
        if len(objs) != 4:
            om.MGlobal_displayError('Select objects by this following order - 1.ctrl 2.local object 3.world object.')
            return

    ctrl = objs[0]
    locObj = objs[1]
    worObj = objs[2]
    consGrp = objs[3]

    try:
        attr = addNumAttr(ctrl, attrName, 'double', hide=False, key=True, min=0, max=1)
    except Exception, e:
        print e
        om.MGlobal_displayError('Cannot add attribute "%s" to the ctrl "%s".' %(attrName, ctrl.nodeName()))
        return

    # consGrp = zgrp(ctrl, element='LocWor', suffix='grp', snap=True, preserveHeirachy=True)
    nd = nameSplit(ctrl.nodeName())
    if createGrp:
        locGrp = pm.group(em=True, n=naming.NAME('%sLocal' %nd['elem'], nd['pos'], naming.GRP))
        locGrp.visibility.set(False)

        worGrp = pm.group(em=True, n=naming.NAME('%sWorld' %nd['elem'], nd['pos'], naming.GRP))
        worGrp.visibility.set(False)

        consGrpParent = consGrp.getParent()
        pm.parent([locGrp, worGrp], consGrpParent)

        snapTransform('parent', consGrp, locGrp, False, True)
        snapTransform('parent', consGrp, worGrp, False, True)

        # if consGrpParent != locObj:
        #   snapTransform(constraintType, locObj, locGrp, True, False)
        locParents = locGrp.getAllParents() + []
        doConstraint = True
        if locObj in locParents:
            locObjIndex = locParents.index(locObj)
            parents_to_check = locParents[:locObjIndex] + [locObj]
            for p in parents_to_check:
                if getConParents(p):
                    break
            else:
                doConstraint = False

        if doConstraint:
            snapTransform(constraintType, locObj, locGrp, True, False)
        snapTransform(constraintType, worObj, worGrp, True, False)
    else:
        locGrp = locObj
        worGrp = worObj

    
    consNode = snapTransform(constraintType, [locGrp, worGrp], consGrp, True, False)
    if constraintType in ['parent', 'orient']:
        consNode.interpType.set(2)

    attr = ctrl.attr(attrName)
    locAttr = consNode.attr('%sW0' %locGrp.nodeName().split(':')[-1])
    worAttr = consNode.attr('%sW1' %worGrp.nodeName().split(':')[-1])
    nameParts = nameSplit(ctrl.nodeName())

    connectSwitchAttr(ctrlAttr=attr, posAttr=worAttr, negAttr=locAttr, elem=nameParts['elem'], side=nameParts['pos'])
    return {'local':locGrp, 'world':worGrp, 'constraint':consNode}

def matchLocalWorld(ctrl=None, attr='localWorld'):
    ''' 
        Toggle localWorld attribute while maintaining the rigged object position.
            User selection: Controller (with localWorld attribute on it)
            args :
                ctrl = The controller (PyNode)
                attr = The name of the switch attribute to be add. (str)
            return:
                Nothing
    '''

    if not ctrl:
        ctrl = getSel()
        if not ctrl:
            om.MGlobal_displayWarning('Cannot find localWorld control object.')
            return

    if not ctrl.hasAttr(attr):
        om.MGlobal_displayWarning('%s  has no attibute named  %s.' %(ctrl.nodeName(), attr))
        return
    else:
        ctrlAttr = ctrl.attr(attr)
        currentLocalWorldValue = ctrlAttr.get()
        ctrlAttrOutputs = ctrlAttr.outputs()
        if not ctrlAttrOutputs:
            om.MGlobal_displayWarning('Cannot find localWorld control attribute on  %s.' %(ctrl.nodeName()))
            return

        for output in [node for node in ctrlAttrOutputs if pm.nodeType(node) in ['parentConstraint', 'orientConstraint', 'pointConstraint']]:
            targetList = output.getTargetList()
            if len(targetList) != 2:
                continue
            else:
                consNode = output
                break

    if not consNode:
        om.MGlobal_displayWarning('Cannot find localWorld constraint node.')
        return


    ctrlParent = ctrl.getParent()

    tmpZgrp = pm.group(em=True, n='_TMPGRP_%s' %ctrlParent.nodeName())
    tmpCtrl = pm.group(em=True, n='_TMPCTRL_%s' %ctrl.nodeName())
    pm.parent(tmpCtrl, tmpZgrp)

    snapTransform('parent', ctrlParent, tmpZgrp, False, True)
    snapTransform('parent', ctrl, tmpCtrl, False, True)

    newTransValue = pm.xform(tmpCtrl, q=True, ws=True, t=True)
    newRotValue = pm.xform(tmpCtrl, q=True, ws=True, ro=True)

    newValue = 1 - currentLocalWorldValue
    ctrlAttr.set(newValue)

    
    try:
        pm.xform(ctrl, ws=True, t=newTransValue)
    except:
        om.MGlobal.displayWarning('Cannot set translate values.')
        pass

    try:
        pm.xform(ctrl, ws=True, ro=newRotValue)
    except:
        om.MGlobal.displayWarning('Cannot set rotate values.')
        pass


    pm.delete(tmpZgrp)
    pm.select(ctrl, r=True)

def createJntAlongCurve(num, crv=None, jointOrient='yzx', elem='', side='', radius=1.00):
    ''' 
        Draw a specified number of joints evenly on to the position along the curve.
            User selection: Curve (transform) 
            args :
                num = The number of joints to draw. (int)
                crv = The curve to draw joint on. (PyNode)
                jointOrient = The orientation of the joints. (str) (xyz, yzx, zxy,..)
                elem = The element for naming. (str)
                side = The side for naming. (str)
                radius = The joint radius to set. (float)
            return:
                Joints (PyNode)
    '''

    if not crv:
        crv = getSel()
        if not crv:
            return

    try:
        crvShp = crv.getShape(ni=True)
        if isinstance(crvShp, pm.nt.NurbsCurve) == False:
            return
    except:
        return

    if not elem:
        elem = crv.nodeName()

    # pm.rebuildCurve(crv, ch=False, rpo=True, rt=4, end=True, kr=True,
    # kcp=False, kep=True, kt=False, s=4, d=3, tol=0.05)

    secAxis = '%sup' %(jointOrient[1])

    pocif = pm.createNode('pointOnCurveInfo', n=naming.NAME(elem, side, naming.POCI))
    pocif.turnOnPercentage.set(True)
    pm.connectAttr(crvShp.worldSpace[0], pocif.inputCurve, f=True)

    jnts = []

    for i in range(0, num):
        value = float(i)/float(num-1)
        pocif.parameter.set(value)
        trans = pocif.position.get()
        jnt = pm.joint(position=trans, rad=radius, n=naming.NAME((elem, str(i+1).zfill(2)), side, naming.JNT))
        jnts.append(jnt)

    for i in range(len(jnts)):
        if i == len(jnts) - 1:
            jnts[i].jointOrient.set([0,0,0])
            break

        pm.joint(jnts[i], e=True, zso=True, oj=jointOrient, sao=secAxis)
        
    return jnts

def randomSetAttr(objs=[], attr='translate', min=[-1.0, -1.0, -1.0], max=[1.0, 1.0, 1.0]):
    ''' 
        Randomly set 3 float values on a attribute. 
            args :
                objs = The list of objects to set. list(PyNode) *User Selection
                attr = The name of the switch attribute to be set. (str)
                min = The minimum value to random. list(float3)
                min = The maximum value to random. list(float3)
            return:
                Nothing
    '''
    if not objs:
        objs = getSel(num='inf')
        if not objs:
            return

    import random


    for obj in objs:
        randX = random.uniform(min[0], max[0])
        randY = random.uniform(min[1], max[1])
        randZ = random.uniform(min[2], max[2])
        try:
            obj.attr(attr).set([randX, randY, randZ])
        except:
            pass

def convertSelToVtx(sels=None):
    ''' 
        Convert selection from transform, mesh, vertex, face, edge to vertices.  *User Selection
            return:
                The vertices. list(PyNode)
    '''
    if not sels:
        sels = pm.ls(sl=True, fl=True)

    typesToAdd = (pm.nt.Transform, pm.nt.Mesh, pm.MeshVertex, pm.MeshFace, pm.MeshEdge)

    result = []
    for sel in [s for s in sels if isinstance(s, typesToAdd)]:
        if isinstance(sel, pm.nt.Transform):
            shp = sel.getShape(ni=True)
            result.append(shp.vtx)
        elif isinstance(sel, pm.nt.Mesh):
            result.append(sel.vtx)
        elif isinstance(sel, (pm.MeshFace ,pm.MeshEdge)):
            vert = [pm.MeshVertex(v) for v in pm.polyListComponentConversion(sel, tv=True)]
            result.extend(vert)
        elif isinstance(sel, pm.MeshVertex):
            result.append(sel)

    return result

def addDeformerMember(deformerName):
    ''' 
        Add selected component(vertex, face, edge)/object(mesh/transform) to the deformer membership. *User Selection
            args :
                deformerName = The name of deformer to add.
            return:
                Nothing
    '''

    sels = convertSelToVtx()
    if not sels:
        return

    deformerNode = pm.PyNode(deformerName)
    memberSet = deformerNode.message.outputs(type='objectSet')[0]
        
    for sel in sels:
        try:
            # pm.sets(memberSet, sel, fe=True)
            memberSet.add(sel)
        except: pass

def removeDeformerMember(deformerName):
    ''' 
        Remove selected component(vertex, face, edge)/object(mesh/transform) to the deformer membership. *User Selection
            args :
                deformerName = The name of deformer to remove.
            return:
                Nothing
    '''

    sels = convertSelToVtx()
    if not sels:
        return

    deformerNode = pm.PyNode(deformerName)
    memberSet = deformerNode.message.outputs(type='objectSet')[0]
    
    for sel in sels:
        # pm.select(sel)
        try:
            # pm.sets(sel, memberSet, rm=True)
            memberSet.remove(sel)
        except: pass

def dupRiggedJntChains(jnts=[], elem=''):
    if not jnts:
        jnts = getSel(selType='joint', num='inf')
        if not jnts:
            return

    newJnts = []
    for j in jnts:
        newJnt = pm.duplicate(j)[0]
        childs = newJnt.getChildren(ad=True)
        if not childs:
            continue
        for c in childs:
            if isinstance(c, pm.nt.Joint) == False:
                pm.delete(c)
                continue

            if elem:
                parts = nameSplit(newJnt.nodeName())
                newName = naming.NAME(parts['elem'], elem, parts['pos'], parts['typ'])
                newJnt.rename(newName)

        newJnts.append(newJnt)

    return newJnts

def assignAllMeshesToLambert():
    lambert = pm.nt.Lambert('lambert1')
    for s in [i for i in pm.ls(type='transform') if isinstance(i.getShape(ni=True), (pm.nt.Mesh, pm.nt.NurbsSurface))]:
        try:
            pm.select(s, r=True)
            pm.hyperShade(s, assign=lambert)
        except: pass

def createSkinClusterJntSet(obj=None, setName=''):
    if not obj:
        obj = getSel()
        if not obj or checkIfPly(obj) == False:
            om.MGlobal.displayError('Select a skinned mesh transform.')
            return

    sk = findRelatedSkinCluster(obj)
    if sk:
        jnts = sk.getInfluence()
        if not setName:
            setName = '%sInfJnt_Set' %obj.nodeName()
        jnts = sorted(jnts)
        sets = pm.sets(jnts, n=setName)
        return sets
    else:
        om.MGlobal.displayError('Cannot find skinCluster node on : %s' %obj.nodeName())
        return None

def getDAG(name, nameSpace='', shapeType=''):
    if nameSpace == '':
        ns = '|*:'
    elif nameSpace == None:
        ns = ''
    else:
        ns = nameSpace

    longNameSplits = name.split('|')
    name = '%s' %ns.join(longNameSplits)

    obj = None
    objs = pm.ls(name, l=True, type='transform')

    if objs != []:
        obj = objs[0]
    else:
        return None

    shp = obj.getShape(ni=True)
    if shapeType:
        if not shp:
            return None
        if isinstance(shp, shapeType):
            return obj
    if shapeType == '':
        return obj
    if shapeType == None:
        if shp:
            return None
        else:
            return obj

def checkTransformConnected(obj):
    res = {obj.translate:False, obj.rotate:False, obj.scale:False}

    for attr in res:
        if attr.inputs():
            res[attr] = True
        else:
            connectedCAttr =  [c for c in attr.getChildren() if c.inputs()]
            if len(connectedCAttr) == 3:
                res[attr] = True
    return res

def hasCleanChannelBox(obj):
    default_values = {'t':0.0, 'r':0.0, 's':1.0}
    result = True
    for attr in 'trs':
        attrCons = obj.attr(attr).inputs()
        if attrCons:
            result = True
            break
        for axis in 'xyz':
            axisAttr = obj.attr('%s%s' %(attr, axis))
            axisCons = axisAttr.inputs()
            value = axisAttr.get()
            if axisCons or value != default_values[attr]:
                result = True
                break
        if result:
            break
    return result

def resetCtrlTransform(objs=[]) :
    if not objs:
        objs = getSel(num='inf')
        if not objs:
            return

    for obj in objs:
        offsetGrp = obj.getParent()
        if not offsetGrp:
            om.MGlobal.displayWarning('%s has no parent. Continue.' %obj.nodeName())
            continue

        # checkRes = checkTransformConnected(offsetGrp)
        # if True in checkRes.values():
        #   om.MGlobal.displayWarning('%s  transform has incoming connection(s). Continue.' %obj.nodeName())
        #   continue

        srcMtx = obj.getMatrix()
        grpMtx = offsetGrp.getMatrix()
        resultMtx = srcMtx * grpMtx

        offsetGrp.setMatrix(resultMtx)
        resetChannelBox(obj)

        if isinstance(obj, pm.nt.Joint) == True:
            obj.jointOrient.set([0.0, 0.0, 0.0])

def resetJointOrient(objs=[]):
    if not objs:
        objs = getSel(num='inf', selType='joint')
        if not objs:
            return

    for obj in objs:
        roEu = obj.getRotation()
        roMat = pm.dt.Matrix(roEu)

        oriQr = obj.getOrientation()
        oriMat = oriQr.asMatrix()

        resMat = roMat * oriMat

        newEu = pm.dt.EulerRotation()
        resEu = newEu.decompose(resMat, obj.rotateOrder.get())
        oriValues = [pm.dt.degrees(resEu.x), 
                    pm.dt.degrees(resEu.y), 
                    pm.dt.degrees(resEu.z)]
        obj.rotate.set([0,0,0])
        obj.jointOrient.set(oriValues)

def switchOutputConnection(aAttr, bAttr):
    try:
        outputA = pm.listConnections(aAttr, d=True, p=True)
    except:
        return

    for attr in outputA:
        pm.connectAttr(bAttr, attr, f=True )

def rearrangeGeoGrp(geoGrp=None):
    if not geoGrp:
        geoGrp = getSel()
        if not geoGrp:
            om.MGlobal.displayError('Select a geo group.')
            return
    exit = False
    grps = [geoGrp]
    while not exit:
        nextGrps = []
        for grp in grps:
            children = grp.getChildren(type='transform')
            if not children:
                om.MGlobal.displayWarning('%s : is an empty group.' %grp.longName())

            # seperate grps and plys
            cgrps, plys, refGrps, refPlys = [], [], [], []
            for c in children:
                if c.isReferenced() == True:
                    if checkIfPly(c) == True:
                        refPlys.append(c)
                    else:
                        refGrps.append(c)
                else:
                    if checkIfPly(c) == True:
                        plys.append(c)
                    else:
                        cgrps.append(c)
                        nextGrps.append(c)

            plys = sorted(plys, key=lambda x: x.nodeName().split(':')[-1])
            cgrps = sorted(cgrps, key=lambda x: x.nodeName().split(':')[-1])
            refPlys = sorted(refPlys, key=lambda x: x.nodeName().split(':')[-1])
            refGrps = sorted(refGrps, key=lambda x: x.nodeName().split(':')[-1])
            plys.extend(cgrps)
            plys.extend(refPlys)
            plys.extend(refGrps)
            for i, item in enumerate(plys):
                currentIndx = grp.getChildren(type='transform').index(item)
                pm.reorder(item, r=((currentIndx * -1) + i))

        if nextGrps:
            grps = nextGrps
        else:
            exit = True 

def resetSelectAttrToDefault():
    sel = getSel(selType='any')
    attrs = mc.channelBox('mainChannelBox', q=True, sma=True)
    for attr in attrs:
        attrFullName = '%s.%s' %(sel.longName(), attr)
        dv = mel.eval('addAttr -q -dv "%s";' %attrFullName)
        mc.setAttr(attrFullName, dv)

def splitJnt(num, jnts=[], leaf=False):
    if not jnts:
        jnts = getSel(selType='joint', num='inf')
        if not jnts:
            om.MGlobal.displayError('Select at least 1 joint(with child joint) then try again.')
            return

    stval = 1.0/(num+1)
    childJnt = None
    for j in jnts:
        try:
            childJnt = j.getChildren(type='joint')[0]
        except IndexError:
            continue

        n = 1
        lastjnt = j
        for i in xrange(num):
            newJnt = j.duplicate(po=True)[0]
            pnode = pm.pointConstraint([j, childJnt], newJnt)
            stattr = pnode.attr('%sW0' %j.nodeName().split(':')[-1])
            endattr = pnode.attr('%sW1' %childJnt.nodeName().split(':')[-1])
            setval = (stval*n)
            endval = 1.0 - setval

            stattr.set(endval)
            endattr.set(setval)
            pm.delete(pnode)

            if leaf == True:
                pm.parent(newJnt, j)
            else:
                pm.parent(newJnt, lastjnt)
                if i == (num - 1):
                    pm.parent(childJnt, newJnt)
                lastjnt = newJnt

            n += 1

def toggleJntPlySelLasso():
    jval = pm.selectType(q=True, joint=True)
    if jval == True:
        pm.selectType(joint=False)
        mel.eval('setToolTo "SelectLasso";')
    else:
        pm.selectType(joint=True)
        mel.eval('setToolTo "moveSuperContext";')

def directConnectTransform(objs=[], t=True, r=True, s=True, force=False):
    if not objs:
        objs = getSel(num='inf')
        if not objs:
            om.MGlobal.displayError('Select two transforms.')
            return

    # check mod to override
    mods = checkMod()
    if any(mods.values()) and not force:
        t = mods['shift']
        r = mods['ctrl']
        s = mods['alt']

    vals = {'translate':t, 'rotate':r, 'scale':s}
    for at, val in vals.iteritems():
        if val == True:
            for axis in 'XYZ':
                try:
                    pm.connectAttr(objs[0].attr('%s%s' %(at, axis)), objs[1].attr('%s%s' %(at, axis)), f=True)
                except:
                    om.MGlobal.displayWarning('Cannot connect %s.%s%s to %s.%s%s' %(objs[0].nodeName(), at, axis, objs[1].nodeName(), at, axis))

def getNurbsParameterFromPoint(crv=None, point=None, createLoc=False, elem='', side='', mode='motionPath'):
    if not crv or not point:
        sels = getSel(num=2)
        if len(sels) != 2 or not sels:
            return
        crv = sels[0].longName()
        point = sels[1].getTranslation('world')
     
    mSel = om.MSelectionList()
    mSel.add(crv)
    dag = om.MDagPath()
    mSel.getDagPath(0, dag)
    dag.extendToShape()

    fnCrv = om.MFnNurbsCurve(dag)
    pt = om.MPoint(point[0], point[1], point[2])
    mutil = om.MScriptUtil()
    mutil.createFromDouble(0.0)
    paramPtr = mutil.asDoublePtr()
    fnCrv.closestPoint(pt, paramPtr, 1.0e-3, om.MSpace.kWorld)
    paramValue = mutil.getDouble(paramPtr)

    if createLoc:
        if isinstance(createLoc, bool):
            loc = pm.spaceLocator(name=naming.NAME((elem, 'Poci'), side, naming.LOC))
            loc.setTranslation(point, 'world')
        else:
            loc = createLoc

        crv = pm.PyNode(crv)
        crvShp = crv.getShape(ni=True)

        if mode == 'motionPath':
            node = pm.createNode('motionPath', name=naming.NAME(elem, side, naming.MP))
            # calculate percentage lenght
            percentValue = paramValue / crvShp.maxValue.get()
            node.uValue.set(percentValue)
            node.fractionMode.set(True)

            pm.connectAttr(crvShp.worldSpace[0], node.geometryPath)
            pm.connectAttr(node.allCoordinates, loc.translate)
            pm.connectAttr(node.rotate, loc.rotate)
        elif mode == 'pointOnCurveInfo':
            node = pm.createNode('pointOnCurveInfo', name=naming.NAME(elem, side, naming.POCI))
            node.parameter.set(paramValue)
            node.turnOnPercentage.set(False)

            pm.connectAttr(crvShp.worldSpace[0], node.inputCurve)
            pm.connectAttr(node.position, loc.translate)

        pm.select(crv, r=True)
        return loc, node
    else:
        return paramValue

def createNearestPointOnCurve(crv=None, pointObj=None, pointConstraint=False, elem='', side=''):
    '''
        Given a curve and a transform, create a locator that sticks to the curve
        and will always trying its best to stay close to the transform.
    '''

    if not crv or not pointObj:
        sels = getSel(num=2)
        if len(sels) != 2 or not sels:
            return
        crv = sels[0]
        pointObj = sels[1]

    loc = pm.spaceLocator(name=naming.NAME((elem, 'Poci'), side, naming.LOC))
    pointLoc = pm.spaceLocator(name=naming.NAME((elem, 'Pnt'), side, naming.LOC))
    snapTransform('point', pointObj, pointLoc, False, pointConstraint)
    crvShp = crv.getShape(ni=True)

    npoc = pm.createNode('nearestPointOnCurve', name=naming.NAME(elem, side, naming.NPOC))
    pm.connectAttr(crvShp.worldSpace[0], npoc.inputCurve)
    pm.connectAttr(pointLoc.getShape().worldPosition[0], npoc.inPosition)

    poci = pm.createNode('pointOnCurveInfo', name=naming.NAME(elem, side, naming.POCI))
    poci.turnOnPercentage.set(False)
    pm.connectAttr(crvShp.worldSpace[0], poci.inputCurve)
    pm.connectAttr(npoc.parameter, poci.parameter)

    pm.connectAttr(poci.position, loc.translate)

    pm.select(crv, r=True)
    return loc, pointLoc, npoc, poci

def setJntDrawStyleInHeirachy(drawStyle='None'):
    validDrawStyle = ['Bone', 'Multi-child as Box', 'None', 0, 1, 2]
    if drawStyle not in validDrawStyle:
        om.MGlobal.displayError('Draw style must be %s' %validDrawStyle)
        return
    sels = getSel(num='inf')
    if not sels:
        om.MGlobal.displayError('Please select a transform')
        return

    for s in sels:
        children = s.getChildren(ad=True, type='joint')
        if s.nodeType() == 'joint':
            children.insert(0, s)
        for c in children:
            c.drawStyle.set(drawStyle)

def getAllChildrenOfType(objs=[], objType='joint'):
    if not objs:
        objs = getSel(num='inf')
        if not objs:
            return

    rets = []
    for obj in objs:
        children = obj.getChildren(ad=True, type=objType)
        if obj.type() == objType:
            rets.insert(0, obj)
        rets.extend(children)

    return rets[::-1]

def turnOffScaleCompensate(objs=[], heirachy=True, value=False):
    if not objs:
        objs = getSel(num='inf')
        if not objs:
            om.MGlobal.displayError('Invalid selection, select one or more joint.')
            return

    if heirachy == True:
        children = []
        for obj in objs:
            children.extend(obj.getChildren(ad=True, type='joint'))

        objs.extend(children)

    n = 0
    for obj in (o for o in objs if o.nodeType()=='joint'):
        currVal = obj.segmentScaleCompensate.get()
        if currVal != value:
            obj.segmentScaleCompensate.set(value)
            n += 1
    print '%s joints segmentScaleCompensate has been set to %s.' %(n, value)

def cleanRiggedSkeleton(objs=[]):
    if not objs:
        objs = getSel(num='inf')
        if not objs:
            return

    toDel = []
    for obj in objs:
        children = getAllChildrenOfType(objType='joint')
        for c in obj.getChildren(ad=True):
            if c not in children and not [i for i in c.getChildren(ad=True) if i.type()=='joint']:
                toDel.append(c)
    pm.delete(toDel)

def snapSkeleton(namespace='', searchFor='ProxySkin', objs=[]):
    if not objs:
        objs = getAllChildrenOfType(objs=pm.selected(), objType='joint')
        if not objs:
            return

    for jnt in objs:
        searchName = jnt.nodeName().replace(searchFor, '')
        lsObj = pm.ls('%s%s' %(namespace, searchName))

        if lsObj:
            snapTransform('parent', lsObj[0], jnt, False, True)
            pm.makeIdentity(jnt, a=True, r=True, t=True, s=True )

def getUvCenter(ids=[], mesh=None):
    if not ids or not mesh:
        sels = [i for i in pm.selected() if isinstance(i, pm.MeshUV)]
        if not sels:
            return
        ids = [p.indices()[0] for p in sels]
        mesh = sels[0].node()

    us, vs = [], []
    for i in ids:
        uvPos = mesh.getUV(i)
        us.append(uvPos[0])
        vs.append(uvPos[1])

    miu, miv = min(us), min(vs)
    mxu, mxv = max(us), max(vs)
    centerUv = [(((mxu-miu)*0.5)+miu), (((mxv-miv)*0.5)+miv)]

    return centerUv

def getUVDistance(pointA=[], pointB=[]):
    if not pointA or not pointB:
        sels = [i for i in pm.selected() if isinstance(i, pm.MeshUV)]
        if not sels or len(sels) != 2:
            return
        mesh = sels[0].node()
        pointA = mesh.getUV(sels[0].indices()[0])
        pointB = mesh.getUV(sels[0].indices()[0])

    ax, ay = float(pointA[0]) ,float(pointA[1])
    bx, by = float(pointB[0]) ,float(pointB[1])
    return (((ax-bx)**2) + ((ay-by)**2)) **0.5

def generate2DRotateCompensateAnimCrv(origin=[0.5, 0.5], rotatePivot=[0.6, 0.6]):
    diff = [(rotatePivot[0] - origin[0]), (rotatePivot[1] - origin[1])]

    oLoc = pm.spaceLocator()
    pm.xform(oLoc, ws=True, t=[diff[0], diff[1], 0])

    cLoc = pm.spaceLocator()
    cLoc.localPosition.set([diff[0], diff[1], 0.0])

    pm.parentConstraint(oLoc, cLoc, mo=True)

    x_crv = pm.createNode('animCurveTU', n='x_crv')
    x_crv.preInfinity.set(3)
    x_crv.postInfinity.set(3)

    y_crv = pm.createNode('animCurveTU', n='y_crv')
    y_crv.preInfinity.set(3)
    y_crv.postInfinity.set(3)

    for angle in range(0, 361):
        oLoc.rotateZ.set(angle)
        x = cLoc.tx.get()
        y = cLoc.ty.get()
        x_crv.addKey(angle, x, tangentInType='linear', tangentOutType='linear')
        y_crv.addKey(angle, y, tangentInType='linear', tangentOutType='linear')
    
    pm.delete([oLoc, cLoc])

    return x_crv, y_crv

def generate2DScaleCompensateAnimCrv(origin=[0.0, 0.0], rotatePivot=[0.6, 0.6]):
    diff = [(rotatePivot[0] - origin[0]), (rotatePivot[1] - origin[1])]

    oLoc = pm.spaceLocator()
    pm.xform(oLoc, ws=True, t=[diff[0], diff[1], 0])

    cLoc = pm.spaceLocator()
    cLoc.localPosition.set([diff[0], diff[1], 0.0])

    pm.parentConstraint(oLoc, cLoc, mo=True)

    x_crv = pm.createNode('animCurveTU', n='x_crv')
    x_crv.preInfinity.set(4)
    x_crv.postInfinity.set(4)

    y_crv = pm.createNode('animCurveTU', n='y_crv')
    y_crv.preInfinity.set(4)
    y_crv.postInfinity.set(4)

    for value in [-1, 0, 1]:
        oLoc.scaleX.set(value)
        oLoc.scaleY.set(value)
        x = cLoc.tx.get()
        y = cLoc.ty.get()
        x_crv.addKey(value, -x, tangentInType='linear', tangentOutType='linear')
        y_crv.addKey(value, -y, tangentInType='linear', tangentOutType='linear')
    
    pm.delete([oLoc, cLoc])

    return x_crv, y_crv

def refreshAllFileNodeSequence(ns=''):
    if not ns:
        sel = getSel(num=1, selType='any')
        if sel:
            ns = sel.namespace()
        else:
            om.MGlobal.displayError('Select any part of a character.')
            return

    fileNodes = pm.ls('%s*' %ns, type='file')
    for f in fileNodes:
        if f.useFrameExtension.get() == True:
            path = f.fileTextureName.get()
            dirname = os.path.dirname(path)
            basename = os.path.basename(path)
            imgs = [i for i in os.listdir(dirname) \
                    if os.path.splitext(i)[-1] in ['.png', '.jpg', '.tif']\
                    and i.startswith(basename.split('.')[0])]
            f.useHardwareTextureCycling.set(False)
            f.useHardwareTextureCycling.set(True)
            f.startCycleExtension.set(1)
            f.endCycleExtension.set(len(imgs))

def alphabetIter(seq=ascii_lowercase):
    for n in count(1):
        for s in product(seq, repeat=n):
            yield ''.join(s)

def make2VertSym(verts=[]):
    if not verts:
        verts = [i for i in pm.selected() if isinstance(i, (pm.MeshVertex, pm.NurbsCurveCV))]
        if len(verts) != 2:
            return

    src_trans = pm.xform(verts[0], q=True, ws=True, t=True)

    pm.xform(verts[1], ws=True, t=[src_trans[0]*-1.0000, src_trans[1], src_trans[2]])

def pipeAttr(source=None, destination=None, attrs=[], replace=[], keepValue=True):
    if not source or not attrs:
        sels = getSel(num=2)
        source = sels[0]
        destination = sels[1]

        # get hilighted attrs from channelbox
        channelBox = mel.eval('global string $gChannelBoxName; $temp=$gChannelBoxName;')
        attrs = mc.channelBox(channelBox, q=True, sma=True)

    for attrName in attrs:
        desAttr = destination.attr(attrName)

        if len(replace) == 2:
            attrName = attrName.replace(replace[0], replace[1])
        srcAttr = addNumAttr(source, attrName, desAttr.type())
        
        srcAttr.setMin(desAttr.getMin())
        srcAttr.setMax(desAttr.getMax())

        if keepValue == True:
            srcAttr.set(desAttr.get())

        pm.connectAttr(srcAttr, desAttr, f=True)

def insertConnection(source=None, destination=None, attrs=[], attrPrefix=''):
    if not source or not destination or not attrs:
        sels = getSel(num=2)
        destination = sels[0]
        source = sels[1]

        # get hilighted attrs from channelbox
        channelBox = mel.eval('global string $gChannelBoxName; $temp=$gChannelBoxName;')
        attrs = mc.channelBox(channelBox, q=True, sma=True)

    if not source or not destination or not attrs:
        return

    sourceObjName = source.nodeName().split(':')[-1]
    for an in attrs:
        sourceAttr = source.attr(an)
        newName = '%s%s__%s' %(attrPrefix, sourceObjName, sourceAttr.longName())
        desAttr = addNumAttr(destination, newName, sourceAttr.type())

        # replace old connection with the new one
        outs = sourceAttr.outputs(p=True)
        pm.connectAttr(sourceAttr, desAttr, f=True)
        print 'Connected: %s to %s' %(sourceAttr.name(), desAttr.name())
        for o in [i for i in outs if i.node() != destination]:
            pm.connectAttr(desAttr, o, f=True)
            print 'Reconnect: %s to %s' %(desAttr.name(), o.name())

def connectCtrlInvScale(sels=[]):
    if not sels:
        sels = getSel(num=2)

    nsp = nameSplit(sels[0].nodeName())

    mdvName = naming.NAME(nsp['elem'], 'InvScale', nsp['pos'], naming.MDV)
    mdv = pm.createNode('multiplyDivide', n=mdvName)

    mdv.operation.set(2)
    mdv.input1.set([1,1,1])

    pm.connectAttr(sels[0].scale, mdv.input2)
    pm.connectAttr(mdv.output, sels[1].scale)

    stAttr = addNumAttr(sels[0].getShape(), 'ctrlStrength', 'float', dv=1, min=0, h=False, k=False)
    stAttr.setKeyable(False)
    stAttr.showInChannelBox(True)

    for sc in ('sx', 'sy', 'sz'):
        sels[0].attr(sc).unlock()
        pm.connectAttr(stAttr, sels[0].attr(sc))
        sels[0].attr(sc).lock()

def fitTurnTableCamera(obj=None, camera='persp', fitFactor=0.5, tiltAngle=-15):
    if not obj:
        obj = getSel()
        if not obj:
            return
    else:
        try:
            obj = pm.PyNode(obj)
        except pm.MayaNodeError:
            return

    if not camera:
        pan = pm.getPanel(withFocus=True)
        camera = pm.windows.modelPanel(pan, query=True, camera=True)
    try:
        camera = pm.PyNode(camera)
    except pm.MayaNodeError:
        return

    bb = obj.getBoundingBox('world')

    centerPt = bb.center()

    maxBB = bb.max()
    maxBBVec = maxBB - pm.dt.Point([0, 0, 0])
    maxBBLen = maxBBVec.length()

    minBB = bb.min()
    minBBVec = minBB - pm.dt.Point([0, 0, 0])
    minBBLen = minBBVec.length()

    bbLen = minBBLen + maxBBLen
    # focalLen = camera.focalLength.get()
    # hFilmApt = camera.horizontalFilmAperture.get()

    zDist = bbLen * distanceFactor
    zVec = pm.dt.Point([0, centerPt.y, zDist]) - pm.dt.Point([0, 0, 0])

    tiltRadians = pm.dt.radians(tiltAngle)
    tiltVec = zVec.rotateBy([tiltRadians, 0, 0])
    camPosition = [tiltVec.x, tiltVec.y, tiltVec.z]
    pm.xform(camera, ws=True, t=camPosition)
    camera.rotate.set([tiltAngle, 0, 0])
    camera.centerOfInterest.set(zDist)

def placeJntAtObjPivot(objs=[], num=2, axis='y', offset=1.0, radius=0.1):
    if not objs:
        objs = getSel(num='inf')
        if not objs:
            return
    for obj in objs:
        jnt = pm.createNode('joint')
        jnt.radius.set(radius)
        snapTransform('parent', obj, jnt, False, True)
        if num > 1:
            tipJnt = jnt.duplicate()[0]
            pm.parent(tipJnt, jnt)
            tipJnt.attr('t%s' %(axis)).set(offset)

            inbNum = num - 2
            if inbNum > 0:
                splitJnt(inbNum, jnts=[jnt], leaf=False)

def resetSkinClusterJnt(skinCluster):
    if isinstance(skinCluster, (str, unicode)):
        skinCluster = pm.PyNode(skinCluster)

    for attr in skinCluster.matrix.elements():
        matAttr = skinCluster.attr(attr)
        index = matAttr.index()
        inputs = matAttr.inputs()
        if inputs:
            jnt = inputs[0]
            
            wim = jnt.worldInverseMatrix[0].get()
            pm.skinCluster(skinCluster, e=True, moveJointsMode=True)
            skinCluster.bindPreMatrix[index].set(wim)
            pm.skinCluster(skinCluster, e=True, moveJointsMode=False)

def resetAllSkinClusterJnt(objs=[]):
    if not objs:
        objs = getSel(num='inf')

    objs = [g for g in objs if checkIfPly(g)]
    for obj in objs:
        skinCluster = findRelatedSkinCluster(obj)
        if skinCluster:
            resetSkinClusterJnt(skinCluster)


def resetAllSkinClusterCmd(objs=[]):
    from nuTools.pipeline import pipeTools
    reload(pipeTools)
    packagePath = os.path.dirname(__file__.replace('\\', '/'))
    pluginPath = '%s/plugins' %(packagePath)
    pipeTools.addToEnv('MAYA_PLUG_IN_PATH', pluginPath)
    pluginName = 'resetSkinClusterJntCmd.py'
    if not pm.pluginInfo(pluginName, q=True, l=True):
        pm.loadPlugin(pluginName, qt=True)

    sels = getSel(num='inf')
    if not objs:
        objs = sels

    objs = [g for g in objs if checkIfPly(g)]
    for obj in objs:
        skinCluster = findRelatedSkinCluster(obj)
        if skinCluster:
            pm.select(obj, r=True)
            pm.resetSkinClusterJnt()

    if sels:
        pm.select(sels, r=True)

def getCoordsInCam(point, cameraName):
    selList = om.MSelectionList()
    selList.add(cameraName) 

    cameraDagPath = om.MDagPath()
    selList.getDagPath(0, cameraDagPath)
    point = om.MPoint(point[0], ppointt[1], point[2])

    cameraInverseWorldMatrix = cameraDagPath.inclusiveMatrixInverse()
    fnCamera = om.MFnCamera(cameraDagPath)
    projectionMatrix = om.MMatrix(fnCamera.projectionMatrix().matrix)

    pjp = (point * cameraInverseWorldMatrix) * projectionMatrix

    resultX = ((pjp.x / pjp.w) / 2 + 0.5) 
    resultY = ((pjp.y / pjp.w) / 2 + 0.5) 

    print resultX, resultY

def resetParentConstraintOffset(objs=[]):
    if not objs:
        objs = getSel(selType='parentConstraint', num='inf')
    if not objs:
        return

    # iterate each constraint selected
    for obj in objs:
        # find targets
        targetLists = obj.getTargetList()

        # only work on the first parent constraint target
        if len(targetLists) == 1:
            # find the child
            children = [c for c in list(set(obj.outputs())) if c != obj]
            if children:
                child = children[0]
                # set nodeState to "hasNoEffect"
                obj.nodeState.set(1)

                # snap the pivot
                snapPivot(targetLists[0], child)
                
                # copy rotation
                copyAxisRotation([targetLists[0], child])

                # "update" constraint offset
                pm.parentConstraint(targetLists[0], child, e=True, mo=True)

                # set nodeState to "normal"
                obj.nodeState.set(0)

def removeDagPathNamespace(path):
    root = False
    if path.startswith('|'):
        root = True
        path = path[1:]
    splits = path.split('|')
    cleaned_elems = []
    for s in splits:
        if '.f[' in s:
            fSplit = s.split('.f[')
            elem = fSplit[0]
            fidx = '.f[%s' %fSplit[1]
        else:
            elem = s
            fidx = ''

        elem = '%s%s' %(elem.split(':')[-1], fidx)
        cleaned_elems.append(elem)

    result = '|'.join(cleaned_elems)
    if root:
        result = '|%s' %(result)
    return result

def addDagPathNamespace(path, namespace):
    root = False
    if path.startswith('|'):
        root = True
        path = path[1:]
    splits = path.split('|')

    result = '|'.join(['%s%s' %(namespace, s) for s in splits])
    if root:
        result = '|%s' %(result)
    return result

def replaceDagPathNamespace(path, namespace):
    root = False
    if path.startswith('|'):
        root = True
        path = path[1:]
    splits = path.split('|')
    parts = []
    for s in splits:
        ns_splits = s.split(':')
        if len(ns_splits) > 1:
            parts.append('{}:{}'.format(namespace, ns_splits[-1]))
        else:
            parts.append(s)
    result = '|'.join(parts)
    if root:
        result = '|%s' %(result)
    return result

def group_range_in_list(num_list):
    new_list = []
    for k, g in groupby(enumerate(num_list), lambda (i,x): i-x):
        group = map(itemgetter(1), g)
        if len(group) > 1:
            elem = (group[0], group[-1])
        else:
            elem = group[0]
        new_list.append(elem)
    return new_list

def component_range_merge(geoName, inputList, componentType='face'):
    result = []
    for a, b in groupby(enumerate(inputList), lambda (x, y): y - x):
        b = list(b)
        if b[0][1] == b[-1][1]:
            num = str(b[0][1])
        else:
            num = '%s:%s' %(b[0][1], b[-1][1])
        if componentType == 'face':
            result.append('%s.f[%s]' %(geoName, num))
        elif componentType == 'vertex':
            result.append('%s.vtx[%s]' %(geoName, num))
        elif componentType == 'edge':
            result.append('%s.e[%s]' %(geoName, num))
        elif componentType == 'uv':
            result.append('%s.map[%s]' %(geoName, num))
    return result

def printMatrix(matrix):
    result = '% .06f, % .06f, % .06f, % .06f,\n% .06f, % .06f, % .06f, % .06f,\n% .06f, % .06f,% .06f, % .06f,\n% .06f, % .06f, % .06f, % .06f,\n'
    print result %(matrix(0, 0), matrix(0, 1), matrix(0, 2), matrix(0, 3), matrix(1, 0), matrix(1, 1), 
        matrix(1, 2), matrix(1, 3), matrix(2, 0), matrix(2, 1), matrix(2, 2 ), matrix(2, 3), matrix(3, 0), 
        matrix(3, 1), matrix(3, 2), matrix(3, 3)) 

def getCurrentCam():
    view = omui.M3dView.active3dView()
    cam = om.MDagPath()
    view.getCamera(cam)
    camPath = cam.fullPathName()
    return camPath

def getCurrentViewportRenderer():
    view = omui.M3dView.active3dView()
    return view.rendererString()

def getRelativeBBScale(bb1, bb2):
    bb1_w = bb1.width()
    bb1_h = bb1.height()
    bb1_d = bb1.depth()

    bb2_w = bb2.width()
    bb2_h = bb2.height()
    bb2_d = bb2.depth()

    try:
        res_w = abs(bb2_w / bb1_w)
    except ZeroDivisionError:
        res_w = 0
    try:
        res_h = abs(bb2_h / bb1_h)
    except ZeroDivisionError:
        res_h = 0
    try:
        res_d = abs(bb2_d / bb1_d)
    except ZeroDivisionError:
        res_d = 0

    return (res_w, res_h, res_d)

def findSameTopology(obj=None, select=True):
    if not obj:
        obj = getSel()
        if not obj:
            return

    objShp = obj.getShape(ni=True)
    if not objShp or objShp.type() != 'mesh':
        return

    same_objs = []
    for tr in pm.ls(type='transform'):
        if tr == obj:
            continue
        shp = tr.getShape(ni=True)
        if shp and shp.type() == 'mesh':
            check_result = checkTopology(obj1=obj, obj2=tr)
            if check_result:
                same_objs.append(tr)
    if select and same_objs:
        toSel = [obj] + same_objs
        pm.select(toSel, r=True)

    return same_objs

def checkTopology(obj1, obj2):
    mSel = om.MSelectionList()
    mSel.add(obj1.longName())
    mSel.add(obj2.longName())

    dMesh1 = om.MDagPath()
    mSel.getDagPath(0, dMesh1) 
    dMesh1.extendToShape()
    mfnA = om.MFnMesh(dMesh1)

    dMesh2 = om.MDagPath()
    mSel.getDagPath(1, dMesh2) 
    dMesh2.extendToShape()
    mfnB = om.MFnMesh(dMesh2)

    aa1 = om.MIntArray()
    aa2 = om.MIntArray()

    ba1 = om.MIntArray()
    ba2 = om.MIntArray()

    mfnA.getVertices(aa1, aa2)
    mfnB.getVertices(ba1, ba2)  

    if len(aa1) != len(ba1):
        return False

    fi = 0
    for ai, bi in zip(aa1, ba1):
        if ai != bi:
            return False
        sliceAA2 = aa2[fi:fi+ai]
        sliceBA2 = ba2[fi:fi+ai]

        for v in sliceAA2:
            if v not in sliceBA2:
                return False
        fi += ai

    return True