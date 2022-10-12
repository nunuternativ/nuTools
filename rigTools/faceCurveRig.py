import sys, os
from collections import defaultdict

from Qt import wrapInstance, QtGui, QtCore, QtWidgets
import pymel.core as pm
import maya.mel as mel
import maya.OpenMaya as om

from nuTools import misc, controller
reload(misc)
reload(controller)

import nuTools.rigTools.baseRig as baseRig
reload(baseRig)
from rftool.utils.ui import maya_win
from rf_utils.ui import load as loadUi

_uiName = 'FaceCurveRigUI'
moduleDir = os.path.dirname(sys.modules[__name__].__file__)

class FaceCurveRigUI(QtWidgets.QMainWindow):
    
    def __init__(self, parent):
        super(FaceCurveRigUI, self).__init__(parent)

        uiFile = '%s\\ui\\faceCurveRig.ui' %moduleDir
        self.ui = loadUi.setup_ui_maya(uiFile, parent=parent)
        self.ui.rig_pushButton.clicked.connect(self.rig)
        self.ui.show()

    def getArgsFromUi(self):
        kwargs = {'headJnt' : str(self.ui.headJnt_lineEdit.text()), 
            'headGeo' : str(self.ui.headGeo_lineEdit.text()), 

            'eyebrowCrv' : str(self.ui.ebCrv_lineEdit.text()), 
            'eyebrowGeo' : str(self.ui.ebGeo_lineEdit.text()), 
            'eyebrowPatch' : str(self.ui.ebPatch_lineEdit.text()), 

            'eyelashCrvs' : str(self.ui.eyelashCrv_lineEdit.text()).split(' '), 
            'eyelashGeos' : str(self.ui.eyelashGeo_lineEdit.text()).split(' '), 

            'eyeballTmpLoc' : str(self.ui.eyeballLoc_lineEdit.text()), 

            'cheekUprCrv' : str(self.ui.cheekUprCrv_lineEdit.text()), 

            'cheekCrv' : str(self.ui.cheekLwrCrv_lineEdit.text()), 
            'lipUprCrv' : str(self.ui.lipUprCrv_lineEdit.text()), 
            'lipLwrCrv' : str(self.ui.lipLwrCrv_lineEdit.text()), 

            'size' : float(self.ui.size_doubleSpinBox.value()) }
        print kwargs
        return kwargs

    def rig(self):
        kwargs = self.getArgsFromUi()
        rigObj = FaceCurveRig(**kwargs)
        rigObj.rig()

class FaceCurveRig(baseRig.BaseRig):
    """from nuTools.rigTools import faceCurveRig as fcr
    reload(fcr)

    # from top to bottom
    # head, eyebrow, eyelashes, eyeball, cheekUpr, mouth&cheeks
    fcrObj = fcr.FaceCurveRig(headJnt ='headBshRig_jnt',
                            headGeo ='BodyBshRig_Geo',

                            eyebrowCrv ='ebLFT_crv',
                            eyebrowGeo ='EyebrowBshRig_Geo',
                            eyebrowPatch = 'BodyEbPatch_Geo',

                            eyelashCrvs =['eyelashUpperPosLFT_crv'],
                            eyelashGeos =['EyelashBshRig_Geo'],

                            eyeballTmpLoc ='eyeBallTmpLFT_loc',

                            cheekUprCrv = 'cheekUprLFT_crv',

                            cheekCrv = 'cheekLFT_crv',
                            lipUprCrv = 'lipUprLFT_crv',
                            lipLwrCrv = 'lipLwrLFT_crv',
                            size = 0.1)
    fcrObj.rig()
    """
    def __init__(self, 
                eyebrowCrv='ebLFT_crv',
                cheekUprCrv='cheekUprLFT_crv',
                cheekCrv='cheekLFT_crv',
                lipUprCrv='lipUprLFT_crv',
                lipLwrCrv='lipLwrLFT_crv',
                headJnt='headBshRig_jnt',

                headGeo='headBshRig_ply',
                eyebrowGeo='eyebrowBshRig_ply',
                eyelashGeos='eyelashBshRig_ply',

                eyeballTmpLoc='eyeBallTmpLFT_loc',
                eyebrowPatch = 'eyebrowPatchBshRig_ply',
                eyelashCrvs = ['eyelashPosLFT_crv'],

                ctrlShp='cube',
                ctrlColor='lightBlue',
                **kwargs):

        super(FaceCurveRig, self).__init__(**kwargs)

        self.curveNames = ['eyebrow', 'cheekUpr', 'cheek', 'lipUpr', 'lipLwr'] 
        self.eyebrowCrvs = self.jntsArgs(eyebrowCrv)
        self.cheekUprCrvs = self.jntsArgs(cheekUprCrv)
        self.cheekCrvs = self.jntsArgs(cheekCrv)
        self.lipUprCrvs = self.jntsArgs(lipUprCrv)
        self.lipLwrCrvs = self.jntsArgs(lipLwrCrv)

        self.headJnt = self.jntsArgs(headJnt)
        
        # geos
        self.headGeo = self.jntsArgs(headGeo)
        self.eyebrowGeo = self.jntsArgs(eyebrowGeo)
        self.eyelashGeos = self.jntsArgs(eyelashGeos)

        self.eyeballTmpLoc = self.jntsArgs(eyeballTmpLoc)
        self.eyebrowPatch = self.jntsArgs(eyebrowPatch)
        self.eyelashCrvs = self.jntsArgs(eyelashCrvs)

        # misc vars
        self.LFT = 'LFT'
        self.RGT = 'RGT'
        self.sides = (self.LFT, self.RGT)

        self.ctrlShp = ctrlShp
        self.ctrlColor = ctrlColor

    def rig(self):
        pm.undoInfo(openChunk=True)
        jntGrp = self.headJnt.getParent()
        if not jntGrp:
            jntGrp = pm.group(em=True, n='headBshJnt_grp')

        # mirror curves
        leftCurves = [self.eyebrowCrvs, self.cheekUprCrvs, self.cheekCrvs, 
                    self.lipUprCrvs, self.lipLwrCrvs]

        loftCrvs = []
        for name, crv in zip(self.curveNames, [c for c in leftCurves]):
            if not crv:
                om.MGlobal.displayWarning('Skipping: %s' %name)
                continue

            pm.rebuildCurve(crv, ch=False, rpo=1, rt=0, end=1, kr=0, kcp=1, kep=1, kt=0, s=4, d=1, tol=0.01)
            numCv = crv.numCVs()
            crvShp = crv.getShape()
            v = 1.0 / (numCv-1)
            circles = []
            for i in xrange(numCv):
                circle = pm.circle(c=(0, 0, 0), nr=(1, 0, 0), sw=360, r=(self.size*0.1), d=1, ut=0, tol=0.01, s=8, ch=False)[0]

                node = pm.createNode('motionPath', name='%s%s%s_mp' %(name, (i+1), self.LFT))
                node.uValue.set((v*i))
                node.fractionMode.set(True)
                node.frontAxis.set(0)  # front axis x
                node.upAxis.set(1)  # up axis z
                node.worldUpVector.set([0, 1, 0])
                node.worldUpType.set(2)
                pm.connectAttr(self.headJnt.worldMatrix[0], node.worldUpMatrix)

                pm.connectAttr(crvShp.worldSpace[0], node.geometryPath)
                pm.connectAttr(node.allCoordinates, circle.translate)
                pm.connectAttr(node.rotate, circle.rotate)
                circles.append(circle)

            surfaceTr = pm.loft(circles, ch=False, u=1, c=0, ar=1, d=1, ss=1, rn=0, po=0, rsn=True)[0]
            surfaceTr.rename('%s%s_nrbs' %(name, self.LFT))
            pm.makeIdentity(surfaceTr, apply=True)

            newSufaceTr = surfaceTr.duplicate()[0]
            newSufaceTr.rename(surfaceTr.nodeName().replace(self.LFT, self.RGT))
            pm.scale(newSufaceTr, (-1, 1, 1), p=[0, 0, 0])
            pm.makeIdentity(newSufaceTr, apply=True)
            pm.reverseSurface(newSufaceTr, ch=False)

            surfaces = [surfaceTr, newSufaceTr]
            exec('self.%sCrvs = surfaces' %(name))
            
            pm.delete(circles)
            loftCrvs.append(crv)
            pm.delete(surfaces, ch=True)

            misc.setDisplayType(obj=surfaceTr, shp=True, disType='reference')
            misc.setDisplayType(obj=newSufaceTr, shp=True, disType='reference')
            pm.parent(surfaces, jntGrp)

            for surf in surfaces:
                center = surf.boundingBox().center()
                pm.xform(surf, piv=center)
                surf.visibility.set(False)

        pm.delete(loftCrvs)
        
        # mirror joints
        if self.eyeballTmpLoc:
            self.lidUprLFTJnt = pm.createNode('joint', n='eyeLidUprLFT_jnt')
            self.lidUprLFTJnt.radius.set(self.size*0.5)
            misc.snapTransform('parent', self.eyeballTmpLoc, self.lidUprLFTJnt, False, True)
            pm.makeIdentity(self.lidUprLFTJnt, apply=True)

            self.lidLwrLFTJnt = self.lidUprLFTJnt.duplicate()[0]
            self.lidLwrLFTJnt.radius.set(self.size*0.75)
            self.lidLwrLFTJnt.rename('eyeLidLwrLFT_jnt')
            pm.move(self.lidLwrLFTJnt, (0, -0.0001, 0), os=True, r=True)

            self.lidUprRGTJnt = pm.PyNode(pm.mirrorJoint(self.lidUprLFTJnt, mirrorYZ=True, mirrorBehavior=True, sr=self.sides)[0])
            self.lidLwrRGTJnt = pm.PyNode(pm.mirrorJoint(self.lidLwrLFTJnt, mirrorYZ=True, mirrorBehavior=True, sr=self.sides)[0])

            pm.parent([self.lidUprLFTJnt, self.lidLwrLFTJnt, self.lidUprRGTJnt, self.lidLwrRGTJnt], self.headJnt)
            self.lidUprJnts = [self.lidUprLFTJnt, self.lidUprRGTJnt]
            self.lidLwrJnts = [self.lidLwrLFTJnt, self.lidLwrRGTJnt]

            pm.delete(self.eyeballTmpLoc)

        # cluster groups
        clsGrp = pm.group(em=True, n='faceCrvCtrl_grp')

        # --- eyebrows
        if self.eyebrowCrvs:
            ebClsGrp = pm.group(em=True, n='faceCrvEbCtrl_grp')
            misc.snapTransform('point', self.eyebrowCrvs, ebClsGrp, False, True)
            pm.parent(ebClsGrp, clsGrp)
            pm.makeIdentity(ebClsGrp, apply=True)

            ebAllCtrl = controller.Controller(n='ebAll_ctrl', 
                                    axis='+z',
                                    st='roundCenterDirectionalArrow', 
                                    color='yellow', 
                                    scale=self.size*1.5)
            ebAllCtrlZgrp = misc.zgrp(ebAllCtrl, element='Zro', suffix='grp')[0]
            misc.snapTransform('parent', ebClsGrp, ebAllCtrlZgrp, False, True)
            pm.move(ebAllCtrl.cv[0:ebAllCtrl.numCVs()-1], (0, 0, self.size*2), r=True)
            pm.parent(ebAllCtrlZgrp, clsGrp)
            pm.parent(ebClsGrp, ebAllCtrl)
            misc.lockAttr(ebAllCtrl, t=False, r=False, s=False, v=True)
            misc.hideAttr(ebAllCtrl, t=False, r=False, s=False, v=True)

            # create clusters on curve
            clstr, clsHndl = self.createCluster([self.eyebrowCrvs[0].cv[0:8][0], self.eyebrowCrvs[1].cv[0:8][0]])

            clsHndl.rename('ebMid_clsHndl')
            pm.parent(clsHndl, ebClsGrp)
            ebCls = {'mid':clsHndl, self.LFT:[], self.RGT:[]}
            for crv, side in zip(self.eyebrowCrvs, self.sides):
                numCv = crv.numSpansInV()
                for i in xrange(1, numCv+1):
                    clstr, clsHndl = self.createCluster([crv.cv[0:8][i]])
                    clsHndl.rename('eb%s%s_clsHndl' %((i), side))

                    ebCls[side].append(clsHndl)
                    pm.parent(clsHndl, ebClsGrp)

            for l, r in zip(ebCls[self.LFT], ebCls[self.RGT]):
                self.connectMirror(l, r)

        # --- eyebrows
        if all([self.lipUprCrvs, self.lipLwrCrvs, self.cheekCrvs]):

            lipsClsGrp = pm.group(em=True, n='faceCrvLipsCtrl_grp')
            misc.snapTransform('point', self.lipUprCrvs + self.lipLwrCrvs, lipsClsGrp, False, True)
            pm.parent(lipsClsGrp, clsGrp)
            pm.makeIdentity(lipsClsGrp, apply=True)

            lipsAllCtrl = controller.Controller(n='lipsAll_ctrl', 
                                    axis='+z',
                                    st='roundCenterDirectionalArrow', 
                                    color='yellow', 
                                    scale=self.size*1.5)
            lipsAllCtrlZgrp = misc.zgrp(lipsAllCtrl, element='Zro', suffix='grp')[0]
            misc.snapTransform('parent', lipsClsGrp, lipsAllCtrlZgrp, False, True)
            pm.move(lipsAllCtrl.cv[0:lipsAllCtrl.numCVs()-1], (0, 0, self.size*2), r=True)
            pm.parent(lipsAllCtrlZgrp, clsGrp)
            pm.parent(lipsClsGrp, lipsAllCtrl)
            misc.lockAttr(lipsAllCtrl, t=False, r=False, s=False, v=True)
            misc.hideAttr(lipsAllCtrl, t=False, r=False, s=False, v=True)

            cheekClsGrp = pm.group(em=True, n='faceCrvCheekCtrl_grp')
            pm.parent(cheekClsGrp, clsGrp)

            # lips upr
            clstr, clsHndl = self.createCluster([self.lipUprCrvs[0].cv[0:8][0], self.lipUprCrvs[1].cv[0:8][0]])
            clsHndl.rename('lipUprMid_clsHndl')
            pm.parent(clsHndl, lipsClsGrp)
            lipUprCls = {'mid':clsHndl, self.LFT:[], self.RGT:[]}
            lipUprNumCv = self.lipUprCrvs[0].numSpansInV()
            for crv, side in zip(self.lipUprCrvs, self.sides):
                for i in xrange(1, lipUprNumCv):  # leave out the last cv
                    clstr, clsHndl = self.createCluster([crv.cv[0:8][i]])
                    clsHndl.rename('lipUpr%s%s_clsHndl' %((i), side))

                    lipUprCls[side].append(clsHndl)
                    pm.parent(clsHndl, lipsClsGrp)

            for l, r in zip(lipUprCls[self.LFT], lipUprCls[self.RGT]):
                self.connectMirror(l, r)

            # lips lwr
            clstr, clsHndl = self.createCluster([self.lipLwrCrvs[0].cv[0:8][0], self.lipLwrCrvs[1].cv[0:8][0]])
            clsHndl.rename('lipLwrMid_clsHndl')
            pm.parent(clsHndl, lipsClsGrp)
            lipLwrCls = {'mid':clsHndl, self.LFT:[], self.RGT:[]}
            lipLwrNumCv = self.lipLwrCrvs[0].numSpansInV()
            for crv, side in zip(self.lipLwrCrvs, self.sides):
                for i in xrange(1, lipLwrNumCv):  # leave out the last cv
                    clstr, clsHndl = self.createCluster([crv.cv[0:8][i]])
                    clsHndl.rename('lipLwr%s%s_clsHndl' %((i), side))

                    lipLwrCls[side].append(clsHndl)
                    pm.parent(clsHndl, lipsClsGrp)

            for l, r in zip(lipLwrCls[self.LFT], lipLwrCls[self.RGT]):
                self.connectMirror(l, r)

            # mouth Crnr
            mouthCrnrCls = {self.LFT:None, self.RGT:None}
            for i, side in enumerate(self.sides):
                clstr, clsHndl = self.createCluster([self.lipUprCrvs[i].cv[0:8][lipUprNumCv], 
                                            self.lipLwrCrvs[i].cv[0:8][lipLwrNumCv], 
                                            self.cheekCrvs[i].cv[0:8][0]])
                clsHndl.rename('mouthCrnr%s_clsHndl' %side)
                mouthCrnrCls[side] = clsHndl
                pm.parent(clsHndl, lipsClsGrp)
            self.connectMirror(mouthCrnrCls[self.LFT], mouthCrnrCls[self.RGT])

            # cheek
            cheekCls = {self.LFT:[], self.RGT:[]}
            numCv = self.cheekCrvs[0].numSpansInV()
            for crv, side in zip(self.cheekCrvs, self.sides):
                for i in xrange(1, numCv+1):
                    clstr, clsHndl = self.createCluster([crv.cv[0:8][i]])
                    clsHndl.rename('cheek%s%s_clsHndl' %((i), side))

                    cheekCls[side].append(clsHndl)
                    pm.parent(clsHndl, cheekClsGrp)

            for l, r in zip(cheekCls[self.LFT], cheekCls[self.RGT]):
                self.connectMirror(l, r)

        # uprCheek 
        if self.cheekUprCrvs:
            cheekUprClsGrp = pm.group(em=True, n='faceCrvCheekUprCtrl_grp')
            pm.parent(cheekUprClsGrp, clsGrp)

            cheekUprCls = {self.LFT:[], self.RGT:[]}
            numCv = self.cheekUprCrvs[0].numSpansInV()
            for crv, side in zip(self.cheekUprCrvs, self.sides):
                for i in xrange(0, numCv+1):
                    clstr, clsHndl = self.createCluster([crv.cv[0:8][i]])
                    clsHndl.rename('cheekUpr%s%s_clsHndl' %((i+1), side))

                    cheekUprCls[side].append(clsHndl)
                    pm.parent(clsHndl, cheekUprClsGrp)

            for l, r in zip(cheekUprCls[self.LFT], cheekUprCls[self.RGT]):
                self.connectMirror(l, r)


        eyelashClsGrp = pm.group(em=True, n='faceCrvEyelashCtrl_grp')
        pm.parent(eyelashClsGrp, clsGrp)

        # bind skin
        self.headGeoDQ = pm.duplicate(self.headGeo, n='%sDQ' %self.headGeo.nodeName())
        skcDQ = pm.skinCluster([self.headJnt, self.headGeoDQ], tsb=True)
        skcDQ.skinningMethod.set(1)
        pm.skinCluster(skcDQ, e=True, ai=[self.lidUprLFTJnt, self.lidLwrLFTJnt,
                                        self.lidUprRGTJnt, self.lidLwrRGTJnt], 
                                        lw=True)

        # self.bsn = pm.blendShape(self.headGeoDQ, self.headGeo)[0]
        # self.bsn.w[0].set(1)
        skc = pm.skinCluster([self.headJnt, self.headGeo], tsb=True)

        # add curves as influence object
        crvs = [self.eyebrowCrvs, self.cheekUprCrvs, self.cheekCrvs, 
                    self.lipUprCrvs, self.lipLwrCrvs]
        crvs = [c for c in crvs if c]
        allCrvs = [item for sublist in crvs for item in sublist]  # merge list in list into flat list
        for crv in [c for c in allCrvs if c]:  # skip the None object
            baseCrv = crv.duplicate()[0]
            baseCrv.rename('%sBase' %crv.nodeName())
            pm.skinCluster(skc, e=True, lw=True, ug=True, dr=4, ps=0, ns=10, wt=0,
                        ai=crv, bsh=baseCrv.getShape())
        skc.useComponents.set(True)

        # wrap eyebrows
        if self.eyebrowCrvs and self.eyebrowGeo and self.eyebrowPatch:
            pm.select([self.eyebrowPatch, self.headGeo], r=True)
            mel.eval('CreateWrap;')
            self.eyebrowPatch.visibility.set(False)

            pm.select([self.eyebrowGeo, self.eyebrowPatch], r=True)
            mel.eval('CreateWrap;')

        # eyelash curve
        if self.eyelashCrvs and self.eyelashGeos:
            lidUprLwrJnts = [self.lidUprJnts, self.lidLwrJnts]
            lidElems = ['Upr', 'Lwr']
            eyelashCtrls = []
            for eyeLashCrv, eyelidJnts, elem in zip(self.eyelashCrvs, lidUprLwrJnts, lidElems):
                eyeLashLFTCrv = eyeLashCrv
                pm.delete(eyeLashLFTCrv, ch=True)

                # mirror the curve
                eyeLashRGTCrv = eyeLashLFTCrv.duplicate()[0]
                eyeLashRGTCrv.rename(eyeLashLFTCrv.nodeName().replace(self.LFT, self.RGT))
                numCv = eyeLashLFTCrv.numCVs()
                allCvs = eyeLashRGTCrv.cv[0:(numCv-1)]
                pm.scale(allCvs, (-1, 1, 1), p=[0, 0, 0])

                lrCrvs = [eyeLashLFTCrv, eyeLashRGTCrv]
                for crv in lrCrvs:
                    # rebuild the curve first
                    pm.rebuildCurve(crv, ch=False, rpo=1, rt=0, end=1, kr=0, kcp=1, kep=1, kt=0, s=4, d=1, tol=0.01)
                    
                    # center the curve pivot
                    crv.visibility.set(True)
                    center = crv.boundingBox().center()
                    pm.xform(crv, piv=center)
                    crv.visibility.set(False)
                    pm.parent(crv, jntGrp)

                pm.select([eyeLashLFTCrv, self.headGeoDQ], r=True)
                mel.eval('CreateWrap;')
                eyeLashLFTCrv.visibility.set(False)

                pm.select([eyeLashRGTCrv, self.headGeoDQ], r=True)
                mel.eval('CreateWrap;')
                eyeLashRGTCrv.visibility.set(False)

                eyelashSideCtrls = []
                for c, crv in enumerate(lrCrvs):
                    side = self.sides[c]
                    lidJnt = eyelidJnts[c]
                    crvShp = crv.getShape(ni=True)
                    for i in xrange(numCv+1):
                        ctrl = controller.JointController(n='eyelash%s%s%s_ctrl' %(elem, (i+1), side), 
                                        axis='+y',
                                        st='locator', 
                                        color='blue', 
                                        scale=self.size*0.3)
                        ctrlZgrp = misc.zgrp(ctrl, element='Zro', suffix='grp')[0]
                        misc.lockAttr(ctrl, t=False, r=False, s=False, v=True)
                        misc.hideAttr(ctrl, t=False, r=False, s=False, v=True)

                        node = pm.createNode('motionPath', name='eyelash%s%s%s_mp' %(elem, (i+1), side))
                        node.uValue.set((float(i)/(numCv-1)))
                        node.fractionMode.set(False)
                        node.frontAxis.set(0)  # front axis x
                        node.upAxis.set(2)  # up axis z
                        node.worldUpVector.set([0, 0, 1])
                        node.worldUpType.set(2)
                        pm.connectAttr(lidJnt.worldMatrix[0], node.worldUpMatrix)

                        pm.connectAttr(crvShp.worldSpace[0], node.geometryPath)
                        pm.connectAttr(node.allCoordinates, ctrlZgrp.translate)
                        pm.connectAttr(node.rotate, ctrlZgrp.rotate)

                        pm.parent(ctrlZgrp, eyelashClsGrp)
                        eyelashSideCtrls.append(ctrl)

                eyelashCtrls.append(eyelashSideCtrls)
                misc.setDisplayType(obj=eyeLashLFTCrv, shp=True, disType='reference')
                misc.setDisplayType(obj=eyeLashRGTCrv, shp=True, disType='reference')

            for ctrls, geo in zip(eyelashCtrls, self.eyelashGeos):
                eyelashSkc = pm.skinCluster([ctrls, geo], tsb=True)

        pm.parent(self.headJnt, jntGrp)

        pm.undoInfo(closeChunk=True)

    def connectMirror(self, left, right):
        trmdv = pm.createNode('multiplyDivide', n='%sMirrorTR_mdv' %left.nodeName().split('_')[0])
        trmdv.input2.set([-1, -1, -1])
        pm.connectAttr(left.tx, trmdv.input1X)
        pm.connectAttr(trmdv.outputX, right.tx)

        pm.connectAttr(left.ty, right.ty)
        pm.connectAttr(left.tz, right.tz)

        pm.connectAttr(left.rx, right.rx)
        pm.connectAttr(left.ry, trmdv.input1Y)
        pm.connectAttr(trmdv.outputY, right.ry)
        pm.connectAttr(left.rz, trmdv.input1Z)
        pm.connectAttr(trmdv.outputZ, right.rz)

        # smdl = pm.createNode('multDoubleLinear', n='%sMirrorScale_mdl' %left.nodeName().split('_')[0])
        # smdl.input2.set(-1)
        # pm.connectAttr(left.sx, smdl.input1)
        # pm.connectAttr(smdl.output, right.sx)
        pm.connectAttr(left.sx, right.sx)
        pm.connectAttr(left.sy, right.sy)
        pm.connectAttr(left.sz, right.sz)

        misc.lockAttr(right, t=True, r=True, s=True, v=True)
        misc.hideAttr(right, t=True, r=True, s=True, v=True)

    def createCluster(self, cvs):
        clstr, clsHndl = pm.cluster(cvs)
        ctrl = controller.Controller(n='%s_ctrl' %cvs[0].node().nodeName(),
                st=self.ctrlShp, color=self.ctrlColor, scale=self.size*0.2)
        ctrlShp = ctrl.getShape()

        tmpLoc = pm.spaceLocator()
        misc.snapTransform('point', clsHndl, tmpLoc, False, True)
        pm.parent(ctrlShp, clsHndl, r=True, s=True)
        numCvs = ctrlShp.numCVs()
        pm.move(ctrlShp.cv[0:numCvs-1], tmpLoc.getTranslation('world'), r=True)
        pm.delete([tmpLoc, ctrl])

        clsHndlShp = clsHndl.getShape()
        clsHndlShp.visibility.set(False)
        clsHndlShp.hiddenInOutliner.set(True)

        misc.lockAttr(clsHndl, t=False, r=False, s=False, v=True)
        misc.hideAttr(clsHndl, t=False, r=False, s=False, v=True)

        return clstr, clsHndl

             
def show():
    try:
        maya_win.deleteUI(_uiName)
    except Exception, e:
        print e 
    
    myApp = FaceCurveRigUI(parent=maya_win.getMayaWindow())

    return myApp

