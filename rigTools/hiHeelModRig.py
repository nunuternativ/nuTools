import os
import pymel.core as pm
import maya.mel as mel
from nuTools import misc, config

reload(misc)
reload(config)

__doc__ = '''
from nuTools.rigTools import hiHeelModRig
reload(hiHeelModRig)

# reference in the locators, place them
locs = hiHeelModRig.referenceGuide()
# or
locs = hiHeelModRig.getLocsFromRef(ref='O:/studioTools/maya/python/tool/rig/nuTools/template/TEMPLATE_hiHeelLoc.ma')


# ns = namespace of the referenced base rig
hiHeelModRig.moveRigPivot(locs, ns='frd_teenFMd_rigMaster:')

# select bodyBase_ply, bodyCorrective_ply(from model team) and bodyMod_ply
hiHeelModRig.doInvertMesh(deformed=None, corrective=None, target=None)

'''
print __doc__

def referenceGuide():
    hiHeelTemplateLocs = {}
    locpath = '%s/TEMPLATE_hiHeelLoc.ma' %config.TEMPLATE_DIR
    hiHeelTemplateRef = pm.createReference(locpath, ns='TEMPLATE_hiHeelLoc')
    hiHeelTemplateLocs = getLocsFromRef(ref=hiHeelTemplateRef)
    return hiHeelTemplateLocs

def getLocsFromRef(ref):
    hiHeelTemplateLocs = {}
    hiHeelTemplateRef = pm.FileReference(ref)
    nodes = hiHeelTemplateRef.nodes()
    for side in ['LFT', 'RGT']:
        for elem in ['ball', 'toe', 'footIn', 'footOut', 'heel']:
            elemSide = '%s%s_loc' %(elem, side)
            for n in nodes:
                if n.nodeName().split(':')[-1] == elemSide:
                    hiHeelTemplateLocs[elemSide] = n
                    break
    return hiHeelTemplateLocs

def moveRigPivot(locs, ns='', elem=''):
    doRig(ballLoc=locs['ballLFT_loc'], 
        toeLoc=locs['toeLFT_loc'], 
        footInLoc=locs['footInLFT_loc'], 
        footOutLoc=locs['footOutLFT_loc'], 
        heelLoc=locs['heelLFT_loc'],
        ns=ns,
        elem=elem,
        side='LFT')

    doRig(ballLoc=locs['ballRGT_loc'], 
        toeLoc=locs['toeRGT_loc'], 
        footInLoc=locs['footInRGT_loc'], 
        footOutLoc=locs['footOutRGT_loc'], 
        heelLoc=locs['heelRGT_loc'],
        ns=ns,
        elem=elem,
        side='RGT')


def doRig(ballLoc, toeLoc, footInLoc, footOutLoc, heelLoc, ns='', elem='', side=''):
    argStrs = ['ballLoc', 'toeLoc', 'footInLoc', 'footOutLoc', 'heelLoc']
    args = [ballLoc, toeLoc, footInLoc, footOutLoc, heelLoc]
    for argStr, arg in zip(argStrs, args):
        if isinstance(arg, (str, unicode)):
            exec('%s = pm.PyNode("%s")' %(argStr, arg))
        else:
            exec('%s = arg' %(argStr))

    nsElemSide = (ns, elem, side)
    # ball position
    ankleRollIkPivZroGrp = pm.PyNode('%sankleRollIkPivZro%s%s_grp' %nsElemSide)
    ankleRollIkPivGrp = pm.PyNode('%sankleRollIkPiv%s%s_grp' %nsElemSide)
    ankleRollIkZroCtrl = pm.PyNode('%sankleRollIkZro%s%s_ctrl' %nsElemSide)
    ankleRollIkCtrl = pm.PyNode('%sankleRollIk%s%s_ctrl' %nsElemSide)
    ballIkIkhPivGrp = pm.PyNode('%sballIkIkhPiv%s%s_grp' %nsElemSide)
    toeBendIkPivZroGrp = pm.PyNode('%stoeBendIkPivZro%s%s_grp' %nsElemSide)
    toeBendIkPivGrp = pm.PyNode('%stoeBendIkPiv%s%s_grp' %nsElemSide)
    ballPosPivGrps = [ankleRollIkPivZroGrp, ankleRollIkPivGrp, ankleRollIkZroCtrl, 
                    ankleRollIkCtrl, ballIkIkhPivGrp, toeBendIkPivZroGrp, toeBendIkPivGrp]

    ballIkJnt = pm.PyNode('%sballIk%s%s_jnt' %nsElemSide)
    ankleIkJnt = pm.PyNode('%sankleIk%s%s_jnt' %(nsElemSide))

    # toe position
    toeIkPivZroGrp = pm.PyNode('%stoeIkPivZro%s%s_grp' %nsElemSide)
    toeIkPivGrp = pm.PyNode('%stoeIkPiv%s%s_grp' %nsElemSide)
    toeIkIkhPivGrp = pm.PyNode('%stoeIkIkhPiv%s%s_grp' %nsElemSide)
    toePosPivGrps = [toeIkPivZroGrp, toeIkPivGrp, toeIkIkhPivGrp]

    # foot in out position
    footInIkPivZroGrp = pm.PyNode('%sfootInIkPivZro%s%s_grp' %nsElemSide)
    footInIkPivGrp = pm.PyNode('%sfootInIkPiv%s%s_grp' %nsElemSide)
    footInPosPivGrps = [footInIkPivZroGrp, footInIkPivGrp]

    footOutIkPivZroGrp = pm.PyNode('%sfootOutIkPivZro%s%s_grp' %nsElemSide)
    footOutIkPivGrp = pm.PyNode('%sfootOutIkPiv%s%s_grp' %nsElemSide)
    footOutPosPivGrps = [footOutIkPivZroGrp, footOutIkPivGrp]

    # heel position
    heelIkPivZroGrp = pm.PyNode('%sheelIkPivZro%s%s_grp' %nsElemSide)
    heelIkPivGrp = pm.PyNode('%sheelIkPiv%s%s_grp' %nsElemSide)
    heelPosPivGrps = [heelIkPivZroGrp, heelIkPivGrp]

    # moving ball piv grps
    ballLocTrans = ballLoc.getTranslation('world')
    for grp in ballPosPivGrps:
        diffTrs = ballLocTrans - grp.getTranslation('world')
        pm.xform(grp, r=True, ws=True, piv=diffTrs)

    # moving toe piv grps
    toeLocTrans = toeLoc.getTranslation('world')
    for grp in toePosPivGrps:
        diffTrs = toeLocTrans - grp.getTranslation('world')
        pm.xform(grp, r=True, ws=True, piv=diffTrs)

    # moving foot in piv grps
    footInLocTrans = footInLoc.getTranslation('world')
    for grp in footInPosPivGrps:
        diffTrs = footInLocTrans - grp.getTranslation('world')
        pm.xform(grp, r=True, ws=True, piv=diffTrs)
    footOutLocTrans = footOutLoc.getTranslation('world')
    for grp in footOutPosPivGrps:
        diffTrs = footOutLocTrans - grp.getTranslation('world')
        pm.xform(grp, r=True, ws=True, piv=diffTrs)

    # moving heel piv grps
    heelLocTrans = heelLoc.getTranslation('world')
    for grp in heelPosPivGrps:
        diffTrs = heelLocTrans - grp.getTranslation('world')
        pm.xform(grp, r=True, ws=True, piv=diffTrs)

    # take care of inb jnt
    try:
        # inbPma = pm.PyNode('%sankleProxySkinPlusPosNagScale%s%s_pls' %nsElemSide)
        inbPma = pm.PyNode('%sankleProxySkinPlusPosNegScale%s%s_pma' %nsElemSide)
        inbPma.input3D[2].input3Dx.set(inbPma.input3D[1].input3Dx.get() * -1.0)
    except Exception, e:
        print e
        pm.warning('Failed to fix inb joint scale.')

     # get toe distance
    toeDist = misc.getDistanceFromPosition(ballLocTrans, toeLocTrans)
    toeIkStretchAdl = pm.PyNode('%slegIkToeStretch%s%s_add' %nsElemSide)
    if toeIkStretchAdl.default.get() < 0:
        toeDist *= -1
    toeIkStretchAdl.default.set(toeDist)

    # --- move ball and toe joints
    ballIkJntTrans = ballIkJnt.getTranslation('world')
    pm.xform(ballIkJnt, ws=True, t=ballLocTrans)

    # fix FK ctrls
    toeFkCtrlZroGrp = pm.PyNode('%stoeFkCtrlZro%s%s_grp' %(nsElemSide))
    ankleFkCtrlZroGrp = pm.PyNode('%sankleFkCtrlZro%s%s_grp' %(nsElemSide))
    toeFkCtrlZroGrp = pm.PyNode('%stoeFkCtrlZro%s%s_grp' %(nsElemSide))

    # print 'constraining  %s ---> %s' %(ankleIkJnt, ankleFkCtrlZroGrp)
    # try:
    misc.snapTransform('orient', ankleIkJnt, ankleFkCtrlZroGrp, False, True)
    # except:
        # pass
    # try:
    misc.snapTransform('orient', ballIkJnt, toeFkCtrlZroGrp, False, True)
    # except:
        # pass

    misc.snapTransform('point', ballIkJnt, toeFkCtrlZroGrp, False, True)
    toeFkStretchAdl = pm.PyNode('%stoeFkStretch%s%s_add' %nsElemSide)
    toeFkStretchAdl.default.set(toeDist)


def doInvertMesh(deformed=None, corrective=None, target=None):
    from nuTools.corrective import invertDeformation as ivdf
    reload(ivdf)

    if not deformed or not corrective or not target:
        sels = pm.selected()
        if len(sels) == 3 and all([misc.checkIfPly(s) for s in sels]):
            deformed = sels[0]
            corrective = sels[1]
            target = sels[2]
    else:
        argStrs = ['deformed', 'corrective', 'target']
        args = [deformed, corrective, target]
        for argStr, arg in zip(argStrs, args):
            if isinstance(arg, (str, unicode)):
                exec('%s = pm.PyNode("%s")' %(argStr, arg))
            else:
                exec('%s = arg' %(argStr))

    inverted = ivdf.invertDeformation(base=deformed, 
                    corrective=corrective)

    tmpMesh = target.duplicate(n='hiHeelCorrective_ply')[0]
    tmpMesh.translate.unlock()
    tmpMesh.rotate.unlock()
    tmpMesh.scale.unlock()
    tmpMesh.visibility.unlock()
    tmpMesh.visibility.set(True)
    pm.parent(tmpMesh, w=True)
    pm.delete(tmpMesh, ch=True)

    bsn = pm.blendShape(inverted, tmpMesh, w=(0, -1))
    pm.delete(tmpMesh, ch=True)
    pm.delete(inverted)

    # pm.connectAttr(tmpMesh.getShape(ni=True).outMesh, target.getShape(ni=True).inMesh, f=True)

    return tmpMesh

