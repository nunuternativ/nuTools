import re

import maya.OpenMaya as om
import maya.cmds as mc
import pymel.core as pm

from nuTools import misc

def getSoftSelection(opacityMult=1.0):
    result = {}

    # if soft select isn't on, return
    if not mc.softSelect(q=True, sse=True):
        return result
        
    richSel = om.MRichSelection()
    try:
        # get currently active soft selection
        om.MGlobal.getRichSelection(richSel)
    except:
        raise Exception('Error getting soft selection.')

    richSelList = om.MSelectionList()
    richSel.getSelection(richSelList)
    selCount = richSelList.length()

    for x in xrange(selCount):
        shapeDag = om.MDagPath()
        shapeComp = om.MObject()
        try:
            richSelList.getDagPath(x, shapeDag, shapeComp)
        except RuntimeError:
            # nodes like multiplyDivides will error
            continue
        
        compOpacities = {}
        compFn = om.MFnSingleIndexedComponent(shapeComp)
        try:
            # get the secret hidden opacity value for each component (vert, cv, etc)
            for i in xrange(compFn.elementCount()):
                weight = compFn.weight(i)
                compOpacities[compFn.element(i)] = weight.influence() * opacityMult
        except Exception, e:
            print e.__str__()
            print 'Soft selection appears invalid, skipping for shape "%s".' % shapeDag.partialPathName()

        result[shapeDag.fullPathName()] = compOpacities
        
    return result

def select_fk_ctrls(obj=None, seperator='_', filter=[]):
    if not obj:
        obj = misc.getSel()
    objName = obj.nodeName().split(':')[-1]
    ns = obj.namespace()
    splits = objName.split(seperator)
    len_splits = len(splits)
    if len_splits not in (2, 3):
        om.MGlobal.displayError('Invalid naming convention!')
        return

    elem = splits[0]
    typ = splits[-1]
    side = ''
    if len_splits == 3:
        side = '_%s_' %splits[1]

    search_result = re.search(r'\d+', elem)
    if search_result:
        digit = search_result.group()
        endStr = objName.split(digit)[-1]
        start, end = search_result.span()
        founds = pm.ls('%s%s*%s' %(ns, elem[:start], endStr))
        # print '%s%s*%s' %(ns, elem[:start], endStr)
        if founds:
            toSel = []
            if not filter:
                for f in sorted(founds, key=lambda x: x.nodeName()):
                    fName = f.nodeName()
                    fSearch = re.match(r'%s%s\d+%s' %(ns, elem[:start], endStr), fName)
                    if fSearch:
                        toSel.append(f)
            else:
                for f in sorted(founds, key=lambda x: x.nodeName()):
                    fName = f.nodeName()
                    for s in filter: 
                        fSearch = re.match(r'%s%s%s%s' %(ns, elem[:start], s, endStr), fName)
                        if fSearch:
                            toSel.append(f)
            if toSel:
                pm.select(toSel, r=True)
                return founds

