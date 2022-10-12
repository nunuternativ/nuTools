import maya.cmds as mc
import maya.OpenMaya as om
import pymel.core as pm

from nuTools import misc, controller
reload(misc)
reload(controller)
from nuTools import naming
reload(naming)
import nuTools.rigTools.baseRig as baseRig
reload(baseRig)

RADIUS_MULT = 0.1

class RibbonConnector(baseRig.BaseRig):
    def __init__(self, 
                jnts=None,
                ctrlShp='crossCircle',
                ctrlColor='yellow', 
                parent={},
                **kwargs):
        super(RibbonConnector, self).__init__(**kwargs)
        # temp joints
        self.tmpJnts = self.jntsArgs(jnts)

        # setting var
        self.ctrlShp = ctrlShp
        self.ctrlColor = ctrlColor

        self.ctrl = None
        self.ctrlZgrp = None
        self.parent = parent

    def rig(self):
        # --- create the controller
        self.ctrl = controller.Controller(name=naming.NAME(self.elem, self.side, naming.CTRL), 
                    st=self.ctrlShp, scale=(self.size))
        self.ctrl.setColor(self.ctrlColor)
        self.ctrl.rotateOrder.set(self.rotateOrder)

        toLockHide = {'t':False, 'r':True, 's':True, 'v':True}
        misc.lockAttr(self.ctrl, **toLockHide)
        misc.hideAttr(self.ctrl, **toLockHide)

        self.ctrlZgrp = misc.zgrp(self.ctrl, element='CtrlZro', suffix='grp')[0]

        # snap zgrp
        misc.snapTransform('parent', self.tmpJnts, self.ctrlZgrp, False, True)

        # constraint to parent transform
        if self.parent:
            for cons, parent in self.parent.iteritems():
                misc.snapTransform(cons, parent, self.ctrlZgrp, True, False)

        # --- parent to main groups
        pm.parent(self.ctrlZgrp, self.animGrp)

class RibbonBase(baseRig.BaseRig):
    def __init__(self, 
                aimAxis='+x',
                upAxis='+z',
                **kwargs):
        super(RibbonBase, self).__init__(**kwargs)

        # handle basic ribbon attributes
        self.radius = self.size * RADIUS_MULT

        self.aimAxis = aimAxis
        self.aimVec = misc.vectorStr(self.aimAxis)

        self.upAxis = upAxis
        self.upVec = misc.vectorStr(self.upAxis)

        self.otherAxis = misc.crossAxis(self.aimAxis, self.upAxis)
        self.otherVec = misc.vectorStr(self.otherAxis)

    def createSurf(self, crvs):
        self.surf = pm.loft(crvs, d=1, ch=False)[0]
        self.surf.rename(naming.NAME('%sRbn' %self.elem, self.side, naming.NRBS))
        pm.delete(crvs)
        
class RibbonIkRig(RibbonBase):
    def __init__(self, 
                numJnt=5,
                aimAxis='+x',
                upAxis='+z',

                ctrlShp='crossCircle',
                ctrlColor='yellow',
                dtlCtrlShp='circle',
                dtlCtrlColor='lightBlue',
                baseTipCrvShape=None,  # None because we probably constraint this controller
                baseTipCtrlColor='yellow',

                includeBaseTip=False,
                doSquash=False,
                **kwargs):
        if numJnt < 1 or not isinstance(numJnt, int):
            om.MGlobal.displayError('Invalid numJnt, using 5.')
            numJnt = 5
        super(RibbonIkRig, self).__init__(aimAxis=aimAxis,
                                        upAxis=upAxis,
                                        **kwargs)
        
        self.numJnt = numJnt
        self.ctrlShp = ctrlShp
        self.ctrlColor = ctrlColor
        self.dtlCtrlShp = dtlCtrlShp
        self.dtlCtrlColor = dtlCtrlColor
        self.baseTipCrvShape = baseTipCrvShape
        self.baseTipCtrlColor = baseTipCtrlColor

        self.includeBaseTip = includeBaseTip
        self.doSquash = doSquash

        self.baseCtrl = None
        self.midCtrl = None
        self.tipCtrl = None

        # ctrls
        self.dtlCtrls = []
        self.dtlCtrlZgrps = []

        # jnts
        self.baseJnt = None
        self.midJnt = None
        self.tipJnt = None
        self.rbnJnts = []

    def rig(self):
        # --- figure out the axis
        self.rotateOrder = '%s%s%s' %(self.aimAxis[-1], self.otherAxis[-1], self.upAxis[-1]) 
        self.twistRoAxis =  self.aimAxis[-1]
        self.sqshScAxis = (self.upAxis[-1], self.otherAxis[-1])

        # --- main grps
        _name = (self.elem, self.side)
        self.rigCtrlGrp = pm.group(em=True, n=naming.NAME('%sRbnRig' %self.elem, self.side, naming.GRP))
        self.rigStillGrp = pm.group(em=True, n=naming.NAME('%sRbnStill' %self.elem, self.side, naming.GRP))
        self.rigStillGrp.visibility.set(False)

        # parent main grps
        pm.parent(self.rigCtrlGrp, self.animGrp)
        pm.parent(self.rigStillGrp, self.stillGrp)

        # tip position
        tipPos = self.aimVec * self.size

        # --- create nurbs
        aCrv = pm.curve(d=1, p=[(0, 0, 0), 
            (tipPos.x, tipPos.y, tipPos.z)], 
            k=[0, 1])
        bCrv = aCrv.duplicate()[0]
        pm.xform(aCrv, ws=True, t=self.otherVec*0.05)
        pm.xform(bCrv, ws=True, t=self.otherVec*-0.05)

        self.createSurf(crvs=[bCrv, aCrv])
        pm.rebuildSurface(self.surf, ch=0, rpo=1, rt=0, end=1, kr=0, kcp=0, 
            kc=0, su=1, du=1, sv=5, dv=3, tol=0.0001, fr=2, dir=2)
        pm.parent(self.surf, self.rigStillGrp)

        # --- rbn jnt
        if not self.baseTipCrvShape:
            self.baseTipCrvShape = 'locator'
        # base jnt
        self.baseJnt = pm.createNode('joint', n=naming.NAME('%sRbnBase' %self.elem, self.side, naming.JNT))
        self.baseJnt.radius.set(self.radius)
        self.baseJnt.visibility.set(False)
        self.baseCtrl = controller.JointController(name=naming.NAME('%sRbnBase' %self.elem, self.side, naming.CTRL),
                                                st=self.baseTipCrvShape, 
                                                color=self.baseTipCtrlColor, 
                                                scale=(self.size*0.334),
                                                draw=False)
        self.baseCtrl.lockAttr(r=True, s=True, v=True)
        self.baseCtrl.hideAttr(r=True, s=True, v=True)
        self.baseCtrl.rotateOrder.set(self.rotateOrder)

        self.baseOfstGrp = misc.zgrp(self.baseCtrl, element='Ofst', suffix='grp')[0]
        self.baseZroGrp = misc.zgrp(self.baseOfstGrp, element='Zro', remove='Ofst', suffix='grp')[0]
        pm.parent(self.baseZroGrp, self.rigCtrlGrp)

        self.baseAimGrp = pm.group(em=True, n=naming.NAME('%sRbnBaseAim' %self.elem, self.side, naming.GRP))
        # self.baseAimGrp = pm.spaceLocator(n='%sRbnBaseAim%s_loc' %_name)
        self.baseAimGrp.visibility.set(False)
        self.baseAimZroGrp = misc.zgrp(self.baseAimGrp, element='Zro', suffix='grp')[0]
        pm.parent(self.baseAimZroGrp, self.baseCtrl)

        # misc.snapTransform('parent', self.baseAimGrp, self.baseJnt, False, False)
        pm.parent(self.baseJnt, self.baseAimGrp)
        
        # tipJnt
        self.tipJnt = pm.createNode('joint', n=naming.NAME('%sRbnTip' %self.elem, self.side, naming.JNT))
        self.tipJnt.radius.set(self.radius)
        self.tipJnt.visibility.set(False)
        self.tipCtrl = controller.JointController(name=naming.NAME('%sRbnTip' %self.elem, self.side, naming.CTRL),
                                                st=self.baseTipCrvShape, 
                                                color=self.baseTipCtrlColor, 
                                                scale=(self.size*0.334),
                                                draw=False)
        self.tipCtrl.lockAttr(r=True, s=True, v=True)
        self.tipCtrl.hideAttr(r=True, s=True, v=True)
        self.tipCtrl.rotateOrder.set(self.rotateOrder)

        self.tipOfstGrp = misc.zgrp(self.tipCtrl, element='Ofst', suffix='grp')[0]
        self.tipZroGrp = misc.zgrp(self.tipOfstGrp, element='Zro', remove='Ofst', suffix='grp')[0]
        pm.parent(self.tipZroGrp, self.rigCtrlGrp)

        self.tipAimGrp = pm.group(em=True, n=naming.NAME('%sRbnTipAim' %self.elem, self.side, naming.GRP))
        # self.tipAimGrp =  pm.spaceLocator(n='%sRbnTipAim%s_loc' %_name)
        self.tipAimGrp.visibility.set(False)
        self.tipAimZroGrp = pm.group(self.tipAimGrp, n=naming.NAME('%sRbnTipAimZro' %self.elem, self.side, naming.GRP))
        pm.parent(self.tipAimZroGrp, self.tipCtrl)

        # position tip ctrl zgrp
        pm.xform(self.tipZroGrp, ws=True, t=tipPos)

        # misc.snapTransform('parent', self.tipAimGrp, self.tipJnt, False, False)
        misc.snapTransform('parent', self.tipAimGrp, self.tipJnt, False, True)
        pm.parent(self.tipJnt, self.tipAimGrp)

        # if baseTipCrvShape is not passed, hide the shape
        if not self.baseTipCrvShape:
            for ctrl in [self.baseCtrl, self.tipCtrl]:
                ctrl.getShape().intermediateObject.set(True)

        # mid jnt
        self.midJnt = pm.createNode('joint', n=naming.NAME('%sRbnMid' %self.elem, self.side, naming.JNT))
        self.midJnt.radius.set(self.radius)
        self.midJnt.visibility.set(False)
        self.midCtrl = controller.JointController(name=naming.NAME('%sRbnMid' %self.elem, self.side, naming.CTRL),
                                                st=self.ctrlShp, 
                                                color=self.ctrlColor, 
                                                axis=self.aimAxis,
                                                scale=self.size,
                                                draw=False)
        self.midCtrl.lockAttr(s=True, v=True)
        self.midCtrl.hideAttr(s=True, v=True)
        self.midCtrl.rotateOrder.set(self.rotateOrder)

        twstDivAttr = misc.addNumAttr(self.midCtrl, '__twist__', 'double', hide=False)
        baseTwstAttr = misc.addNumAttr(self.midCtrl, 'baseTwist', 'double', dv=0.0)
        tipTwstAttr = misc.addNumAttr(self.midCtrl, 'tipTwist', 'double', dv=0.0)

        # hide autoTwist attr for now, if user use 'attach' method with 'twistTipParent' arg is passed,
        # then show it back up
        autoTwstAttr = misc.addNumAttr(self.midCtrl, 'autoTwist', 'double', min=0.0, max=1.0, dv=1.0)
        autoTwstAttr.setKeyable(False)
        autoTwstAttr.showInChannelBox(False)
        twstDivAttr.lock()

        self.midCtrlShp = self.midCtrl.getShape(ni=True)
        dtlCtrlVisAttr = misc.addNumAttr(self.midCtrlShp, 'detailCtrl_vis', 'long', min=0, max=1, dv=0)
        dtlCtrlVisAttr.setKeyable(False)
        dtlCtrlVisAttr.showInChannelBox(True)

        pm.addAttr(self.midCtrlShp, ln='aimVector', sn='av', at='double3')
        pm.addAttr(self.midCtrlShp, ln='aimVectorX', sn='avx', at='double', p='aimVector')
        pm.addAttr(self.midCtrlShp, ln='aimVectorY', sn='avy', at='double', p='aimVector')
        pm.addAttr(self.midCtrlShp, ln='aimVectorZ', sn='avz', at='double', p='aimVector')
        self.midCtrlShp.aimVector.set(self.aimVec)
        self.midCtrlShp.aimVector.setKeyable(False)
        self.midCtrlShp.aimVector.showInChannelBox(False)

        pm.addAttr(self.midCtrlShp, ln='upVector', sn='uv', at='double3')
        pm.addAttr(self.midCtrlShp, ln='upVectorX', sn='uvx', at='double', p='upVector')
        pm.addAttr(self.midCtrlShp, ln='upVectorY', sn='uvy', at='double', p='upVector')
        pm.addAttr(self.midCtrlShp, ln='upVectorZ', sn='uvz', at='double', p='upVector')
        self.midCtrlShp.upVector.set(self.upVec)
        self.midCtrlShp.upVector.setKeyable(False)
        self.midCtrlShp.upVector.showInChannelBox(False)
        
        self.midOfstGrp = misc.zgrp(self.midCtrl, element='Ofst', suffix='grp')[0]
        self.midAimGrp = misc.zgrp(self.midOfstGrp, element='Aim', remove='Ofst', suffix='grp')[0]
        self.midZroGrp = misc.zgrp(self.midAimGrp, element='Zro', remove='Aim', suffix='grp')[0]
        pm.parent(self.midZroGrp, self.rigCtrlGrp)

        self.midJntOfstGrp = pm.group(em=True, n=naming.NAME('%sRbnMidJntOffset' %self.elem, self.side, naming.GRP))
        pm.parent(self.midJntOfstGrp, self.midCtrl)
        pm.parent(self.midJnt, self.midJntOfstGrp)

        # setup aim
        self.baseAimCons = pm.aimConstraint(self.tipCtrl, self.baseAimZroGrp,
                                        aim=self.aimVec, u=self.upVec,
                                        wut='objectrotation',
                                        wuo=self.baseCtrl,
                                        wu=self.upVec)
        self.tipAimCons = pm.aimConstraint(self.baseCtrl, self.tipAimZroGrp,
                                        aim=(self.aimVec*-1), u=self.upVec,
                                        wut='objectrotation',
                                        wuo=self.tipCtrl,
                                        wu=self.upVec)
        pm.pointConstraint([self.baseCtrl, self.tipCtrl], self.midZroGrp)
        self.midAimCons = pm.aimConstraint(self.tipCtrl, self.midAimGrp,
                                        aim=self.aimVec, u=self.upVec,
                                        wut='objectrotation',
                                        wuo=self.midZroGrp,
                                        wu=self.upVec)

        # connect upVec attr on midCtrl shape to aim cons vector
        pm.connectAttr(self.midCtrlShp.upVector, self.baseAimCons.upVector)
        pm.connectAttr(self.midCtrlShp.upVector, self.baseAimCons.worldUpVector)
        pm.connectAttr(self.midCtrlShp.upVector, self.tipAimCons.upVector)
        pm.connectAttr(self.midCtrlShp.upVector, self.tipAimCons.worldUpVector)
        pm.connectAttr(self.midCtrlShp.upVector, self.midAimCons.upVector)
        pm.connectAttr(self.midCtrlShp.upVector, self.midAimCons.worldUpVector)

        # point on surface group
        self.allPosGrp = pm.group(em=True, n=naming.NAME('%sRbnPos' %self.elem, self.side, naming.GRP))
        pm.parent(self.allPosGrp, self.rigStillGrp)

        # detail ctrl group
        self.dtlCtrlGrp = pm.group(em=True, n=naming.NAME('%sRbnDtlCtrl' %self.elem, self.side, naming.GRP))
        pm.parent(self.dtlCtrlGrp, self.rigCtrlGrp)

        pm.connectAttr(self.midCtrlShp.detailCtrl_vis, self.dtlCtrlGrp.visibility)

        # attach pos groups
        if self.includeBaseTip:
            totalNumJnt = self.numJnt + 2    # include the base and tip rbn jnt
            step = float(1.0/(totalNumJnt-1))
            varyStep = float(6.0/(totalNumJnt-1))
        else:
            totalNumJnt = self.numJnt
            step = float(1.0/(totalNumJnt+1))
            try:
                varyStep = float(6.0/(totalNumJnt-1))
            except ZeroDivisionError:
                varyStep = 0

        posGrps, posNodes, aimNodes = [], [], []
        for i in xrange(totalNumJnt):
            posGrp = pm.group(em=True, n=naming.NAME('%sRbnPos%s' %(self.elem, (i+1)), self.side, naming.GRP))
            
            posNode = pm.createNode('pointOnSurfaceInfo', n=naming.NAME('%sRbn%s' %(self.elem, (i+1)), self.side, naming.POSI))
            posNode.parameterU.set(0.5)

            if self.includeBaseTip:
                paramV = (i)*step
            else:
                paramV = (i + 1)*step
            posNode.parameterV.set(paramV)
            posNode.turnOnPercentage.set(True)
            
            aimCon = pm.createNode('aimConstraint', n=naming.NAME('%sRbnPos%s' %(self.elem, (i+1)), self.side, naming.AIMCON))
            pm.connectAttr(self.surf.worldSpace[0], posNode.inputSurface)
            pm.connectAttr(self.midCtrlShp.aimVector , aimCon.aimVector)
            pm.connectAttr(self.midCtrlShp.upVector , aimCon.upVector)
            pm.connectAttr(posNode.normal, aimCon.worldUpVector)
            pm.connectAttr(posNode.tangentV, aimCon.target[0].targetTranslate)
            pm.connectAttr(posNode.position, posGrp.translate)
            pm.connectAttr(aimCon.constraintRotate, posGrp.rotate)

            pm.parent(posGrp, self.allPosGrp)
            pm.parent(aimCon, posGrp)

            posGrps.append(posGrp)

        # --- twist connections
        self.twstPma = pm.createNode('plusMinusAverage', n=naming.NAME('%sRbnTwst' %self.elem, self.side, naming.PMA))
        pm.connectAttr(self.midCtrl.baseTwist, self.twstPma.input2D[1].input2Dx)
        pm.connectAttr(self.midCtrl.tipTwist, self.twstPma.input2D[1].input2Dy)

        # --- squash pre connections
        if self.doSquash:
            # add attrs
            sqstDivAttr = misc.addNumAttr(self.midCtrl, '__squash__', 'double', hide=False)
            sqstDivAttr.lock()

            sqstAttr = misc.addNumAttr(self.midCtrl, 'squash', 'double', dv=0.0)
            autoSqshAttr = misc.addNumAttr(self.midCtrl, 'autoSquash', 'double', min=0.0, max=1.0, dv=0.0)
            
            defLenAttr = misc.addNumAttr(self.midCtrlShp, 'defaultLen', 'double', v=self.size)
            defLenAttr.setKeyable(False)
            defLenAttr.showInChannelBox(False)
            # defLenAttr.setLocked(True)

            # 3 distance grps 
            basePosGrp = pm.group(em=True, n=naming.NAME('%sRbnBasePos' %self.elem, self.side, naming.GRP))
            midPosGrp = pm.group(em=True, n=naming.NAME('%sRbnMidPos' %self.elem, self.side, naming.GRP))
            tipPosGrp = pm.group(em=True, n=naming.NAME('%sRbnTipPos' %self.elem, self.side, naming.GRP))
            misc.snapTransform('point', self.baseJnt, basePosGrp, False, False)
            misc.snapTransform('point', self.midJnt, midPosGrp, False, False)
            misc.snapTransform('point', self.tipJnt, tipPosGrp, False, False)
            
            pm.parent([basePosGrp, midPosGrp, tipPosGrp], self.rigCtrlGrp)

            # distanceBetween nodes
            uprDist = pm.createNode('distanceBetween', n=naming.NAME('%sRbnUprPos' %self.elem, self.side, naming.DIST))
            pm.connectAttr(basePosGrp.translate, uprDist.point1)
            pm.connectAttr(midPosGrp.translate, uprDist.point2)

            lwrDist = pm.createNode('distanceBetween', n=naming.NAME('%sRbnLwrPos' %self.elem, self.side, naming.DIST))
            pm.connectAttr(midPosGrp.translate, lwrDist.point1)
            pm.connectAttr(tipPosGrp.translate, lwrDist.point2)

            self.lenAdl = pm.createNode('addDoubleLinear', n=naming.NAME('%sRbnLen' %self.elem, self.side, naming.ADL))
            pm.connectAttr(uprDist.distance, self.lenAdl.input1)
            pm.connectAttr(lwrDist.distance, self.lenAdl.input2)

            sqshNormMdv = pm.createNode('multiplyDivide', n=naming.NAME('%sRbnSqshNorm' %self.elem, self.side, naming.MDV))
            sqshPowMdv = pm.createNode('multiplyDivide', n=naming.NAME('%sRbnSqshPow' %self.elem, self.side, naming.MDV))
            sqshDivMdv = pm.createNode('multiplyDivide', n=naming.NAME('%sRbnSqshDiv' %self.elem, self.side, naming.MDV))
            
            sqshNormMdv.operation.set(2)
            pm.connectAttr(self.lenAdl.output, sqshNormMdv.input1X)

            self.midCtrlShp.defaultLen.set(self.lenAdl.output.get())
            pm.connectAttr(self.midCtrlShp.defaultLen, sqshNormMdv.input2X)

            sqshPowMdv.operation.set(3)
            sqshPowMdv.input2X.set(2.0)
            pm.connectAttr(sqshNormMdv.outputX, sqshPowMdv.input1X)

            sqshDivMdv.operation.set(2)
            sqshDivMdv.input1X.set(1.0)
            pm.connectAttr(sqshPowMdv.outputX, sqshDivMdv.input2X)

            # create tmp animCurve and frameCache to calculate squash mult values
            c = pm.createNode('animCurveTU')
            c.addKey(0, 0.0, tangentInType='linear', tangentOutType='linear')
            c.addKey(3, 1.0, tangentInType='flat', tangentOutType='flat')
            c.addKey(6, 0.0, tangentInType='linear', tangentOutType='linear')
            fc = pm.createNode('frameCache')
            pm.connectAttr(c.output, fc.stream)

        # --- create detail controller
        twstPmaBaseTipDict = {0:self.twstPma.output2Dx, (totalNumJnt-1):self.twstPma.output2Dy}

        for i in xrange(totalNumJnt):
            # dtl ctrl
            dtlCtrl = controller.JointController(name=naming.NAME('%sRbnDtl%s' %(self.elem, (i+1)), self.side, naming.CTRL),
                                                st=self.dtlCtrlShp, 
                                                color=self.dtlCtrlColor, 
                                                axis=self.aimAxis,
                                                scale=(self.size*0.75),
                                                draw=False)
            dtlCtrl.lockAttr(v=True)
            dtlCtrl.hideAttr(v=True)
            dtlCtrl.rotateOrder.set(self.rotateOrder)

            # dtlSqshAttr = misc.addNumAttr(dtlCtrl, 'squash', 'double', dv=0.0)

            ofstGrp = misc.zgrp(dtlCtrl, element='Ofst', suffix='grp')[0]
            twstGrp = misc.zgrp(ofstGrp, element='Twst', remove='Ofst', suffix='grp')[0]
            zroGrp = misc.zgrp(twstGrp, element='Zro', remove='Twst', suffix='grp')[0]
            pm.parent(zroGrp, self.dtlCtrlGrp)

            # dtl jnt
            dtlJnt = pm.createNode('joint', n=naming.NAME('%sRbnDtl%s' %(self.elem, (i+1)), self.side, naming.JNT))
            dtlJnt.radius.set(self.radius*0.75)

            # parent dtlJnt to dtlCtrl
            misc.snapTransform('parent', posGrps[i], zroGrp, False, False)
            pm.parent(dtlJnt, dtlCtrl)

            pm.makeIdentity(dtlJnt, n=False, apply=True)
            misc.snapTransform('parent', dtlCtrl, dtlJnt, False, False)

            # connect twist
            if i in twstPmaBaseTipDict:    # if this is the first or the last jnt
                if totalNumJnt == 1:
                    # create mdv if it's the only joint, set mult value to 0.5
                    dtlTwstMdv = pm.createNode('multiplyDivide', n=naming.NAME('%sRbnDtl%sTwst' %(self.elem, (i+1)), self.side, naming.MDV))
                    dtlTwstMdv.input2X.set(0.5)
                    dtlTwstMdv.input2Y.set(0.5)

                    pm.connectAttr(self.twstPma.output2Dx, dtlTwstMdv.input1X)
                    pm.connectAttr(self.twstPma.output2Dy, dtlTwstMdv.input1Y)
                    
                    dtlTwstAdl = pm.createNode('addDoubleLinear', n=naming.NAME('%sRbnDtl%sTwst' %(self.elem, (i+1)), self.side, naming.ADL))
                    pm.connectAttr(dtlTwstMdv.outputX, dtlTwstAdl.input1)
                    pm.connectAttr(dtlTwstMdv.outputY, dtlTwstAdl.input2)
                    pm.connectAttr(dtlTwstAdl.output, twstGrp.attr('r%s' %self.twistRoAxis))
                else:
                    defSqshMultValue = 0.0
                    pm.connectAttr(twstPmaBaseTipDict[i], twstGrp.attr('r%s' %self.twistRoAxis))
            else:
                if self.includeBaseTip:
                    twstMultValue = step*i
                else:
                    twstMultValue = float(1.0/(totalNumJnt-1)) * i
                twstMultInvValue = 1.0 - twstMultValue
                # create mdv if it's not the first or the last
                dtlTwstMdv = pm.createNode('multiplyDivide', n=naming.NAME('%sRbnDtl%sTwst' %(self.elem, (i+1)), self.side, naming.MDV))
                dtlTwstMdv.input2X.set(twstMultInvValue)
                dtlTwstMdv.input2Y.set(twstMultValue)

                pm.connectAttr(self.twstPma.output2Dx, dtlTwstMdv.input1X)
                pm.connectAttr(self.twstPma.output2Dy, dtlTwstMdv.input1Y)
                
                dtlTwstAdl = pm.createNode('addDoubleLinear', n=naming.NAME('%sRbnDtl%sTwst' %(self.elem, (i+1)), self.side, naming.ADL))
                pm.connectAttr(dtlTwstMdv.outputX, dtlTwstAdl.input1)
                pm.connectAttr(dtlTwstMdv.outputY, dtlTwstAdl.input2)

                pm.connectAttr(dtlTwstAdl.output, twstGrp.attr('r%s' %self.twistRoAxis))
                
            # connect squash
            if self.doSquash:
                if i in twstPmaBaseTipDict:
                    # figure out mult value
                    defSqshMultValue = 1.0 if totalNumJnt == 1 else 0.0
                else:
                    # get squash mult from frame cache
                    fc.varyTime.set(varyStep * i)
                    defSqshMultValue = round(fc.varying.get(), 3)

                # add mult attrs at midCtrlShp
                squashAttrName = 'squash%s_mult' %(i+1)
                sqshMultAttr = misc.addNumAttr(self.midCtrlShp, squashAttrName, 'double', min=0, max=1, dv=defSqshMultValue)
                self.midCtrlShp.attr(squashAttrName).setKeyable(False)
                self.midCtrlShp.attr(squashAttrName).showInChannelBox(False)

                dtlSqshMinPma = pm.createNode('plusMinusAverage', n=naming.NAME('%sRbnDtl%sScaSub' %(self.elem, (i+1)), self.side, naming.PMA))
                dtlSqshMinPma.input3D[1].set([-1, -1, -1])
                pm.connectAttr(dtlCtrl.scale, dtlSqshMinPma.input3D[0])
                naming.NAME('%sRbnDtl%sAutoSqshMult' %(self.elem, (i+1)), self.side, naming.MDL)
                autoSqshMdl = pm.createNode('multDoubleLinear', n=naming.NAME('%sRbnDtl%sAutoSqshMult' %(self.elem, (i+1)), self.side, naming.MDL))
                autoSqshSubPma = pm.createNode('plusMinusAverage', n=naming.NAME('%sRbnDtl%sAutoSqshSub' %(self.elem, (i+1)), self.side, naming.PMA))
                autoSqshAdl = pm.createNode('addDoubleLinear', n=naming.NAME('%sRbnDtl%sAutoSqsh' %(self.elem, (i+1)), self.side, naming.ADL))
                autoSqshSubPma.operation.set(2)
                autoSqshSubPma.input1D[0].set(1.0)

                pm.connectAttr(sqshMultAttr, autoSqshSubPma.input1D[1])
                pm.connectAttr(sqshDivMdv.outputX, autoSqshMdl.input1)
                pm.connectAttr(sqshMultAttr, autoSqshMdl.input2)
                pm.connectAttr(autoSqshSubPma.output1D, autoSqshAdl.input1)
                pm.connectAttr(autoSqshMdl.output, autoSqshAdl.input2)

                autoSqshBta = pm.createNode('blendTwoAttr', n=naming.NAME('%sRbnDtl%sAutoSqsh' %(self.elem, (i+1)), self.side, naming.BTA))
                autoSqshBta.input[0].set(1.0)
                pm.connectAttr(self.midCtrl.autoSquash, autoSqshBta.attributesBlender)
                pm.connectAttr(autoSqshAdl.output, autoSqshBta.input[1])

                sqshPma = pm.createNode('plusMinusAverage', n=naming.NAME('%sRbnDtl%sSqsh' %(self.elem, (i+1)), self.side, naming.PMA))
                pm.connectAttr(dtlSqshMinPma.output3D, sqshPma.input3D[0])
                
                for axis in 'xyz':
                    if axis in self.sqshScAxis:
                        pm.connectAttr(self.midCtrl.squash, sqshPma.input3D[1].attr('input3D%s'%axis))
                        pm.connectAttr(autoSqshBta.output, sqshPma.input3D[2].attr('input3D%s'%axis))
                    else:
                        sqshPma.input3D[2].attr('input3D%s' %axis).set(1.0)

                # connect to joint scale
                pm.connectAttr(sqshPma.output3D, dtlJnt.scale)

            else:  # doSquasdh if False, just connect the dtlCtrl scale directly to the dtlJnt
                pm.connectAttr(dtlCtrl.scale, dtlJnt.scale)


            # store to class var
            self.dtlCtrls.append(dtlCtrl)
            self.rbnJnts.append(dtlJnt)

        # delete tmp animCurve and frameCache
        if self.doSquash:
            pm.delete([c, fc])

        # --- skin the surf
        allRbnBindJnts = [self.baseJnt, self.midJnt, self.tipJnt]
        self.skinCluster = pm.skinCluster(allRbnBindJnts, self.surf, 
                                        tsb=True, dr=7, mi=2)
        
        pm.skinPercent(self.skinCluster, self.surf.cv[0:1][0], tv=[self.baseJnt, 1.0])

        pm.skinPercent(self.skinCluster, self.surf.cv[0:1][1], tv=[self.baseJnt, 0.85])
        self.baseJnt.lockInfluenceWeights.set(True)
        pm.skinPercent(self.skinCluster, self.surf.cv[0:1][1], tv=[self.midJnt, 0.15])

        self.lockInf(jnts=allRbnBindJnts, value=False)
        pm.skinPercent(self.skinCluster, self.surf.cv[0:1][2], tv=[self.baseJnt, 0.6])
        self.baseJnt.lockInfluenceWeights.set(True)
        pm.skinPercent(self.skinCluster, self.surf.cv[0:1][2], tv=[self.midJnt, 0.4])

        self.lockInf(jnts=allRbnBindJnts, value=False)
        pm.skinPercent(self.skinCluster, self.surf.cv[0:1][3], tv=[self.baseJnt, 0.2])
        self.baseJnt.lockInfluenceWeights.set(True)
        pm.skinPercent(self.skinCluster, self.surf.cv[0:1][3], tv=[self.midJnt, 0.8])

        self.lockInf(jnts=allRbnBindJnts, value=False)
        pm.skinPercent(self.skinCluster, self.surf.cv[0:1][4], tv=[self.tipJnt, 0.2])
        self.tipJnt.lockInfluenceWeights.set(True)
        pm.skinPercent(self.skinCluster, self.surf.cv[0:1][4], tv=[self.midJnt, 0.8])

        self.lockInf(jnts=allRbnBindJnts, value=False)
        pm.skinPercent(self.skinCluster, self.surf.cv[0:1][5], tv=[self.midJnt, 0.4])
        self.midJnt.lockInfluenceWeights.set(True)
        pm.skinPercent(self.skinCluster, self.surf.cv[0:1][5], tv=[self.tipJnt, 0.6])

        self.lockInf(jnts=allRbnBindJnts, value=False)
        pm.skinPercent(self.skinCluster, self.surf.cv[0:1][6], tv=[self.midJnt, 0.15])
        self.midJnt.lockInfluenceWeights.set(True)
        pm.skinPercent(self.skinCluster, self.surf.cv[0:1][6], tv=[self.tipJnt, 0.85])

        self.lockInf(jnts=allRbnBindJnts, value=False)
        pm.skinPercent(self.skinCluster, self.surf.cv[0:1][7], tv=[self.tipJnt, 1.0])


    def attach(self, base, tip, baseParent, tipTwistParent=None, twistFromBase=False,  upAxis='+y', parentUpAxis='+y'):
        pluginNames = ['matrixNodes.mll', 'quatNodes.mll']

        for pluginName in pluginNames:
            try:
                if not mc.pluginInfo(pluginName, q=True, l=True):
                    mc.loadPlugin(pluginName, qt=True)
            except:
                continue

        if isinstance(base, (str, unicode)):
            base = pm.PyNode(base)
        if isinstance(tip, (str, unicode)):
            tip = pm.PyNode(tip)
        if isinstance(baseParent, (str, unicode)):
            baseParent = pm.PyNode(baseParent)
        if isinstance(tipTwistParent, (str, unicode)):
            tipTwistParent = pm.PyNode(tipTwistParent)

        upVec = misc.vectorStr(upAxis)
        pUpVec = misc.vectorStr(parentUpAxis)

        misc.snapTransform('point', base, self.rigCtrlGrp, False, True)
        pm.delete(pm.aimConstraint(tip, 
                                self.rigCtrlGrp,
                                aim=self.aimVec, u=upVec,
                                wut='objectrotation',
                                wuo=baseParent,
                                wu=pUpVec))

        pm.parentConstraint(baseParent, self.rigCtrlGrp, mo=True)
        pm.pointConstraint(base, self.baseCtrl)
        pm.pointConstraint(tip, self.tipCtrl)

        toLockHide = {'t':True, 'r':True, 's':True, 'v':True}
        misc.lockAttr(self.baseCtrl, **toLockHide)
        misc.lockAttr(self.tipCtrl, **toLockHide)
        
        self.midCtrlShp = self.midCtrl.getShape()

        # set default Len for autoSquash to work properly
        if self.midCtrlShp.hasAttr('defaultLen'):
            self.midCtrlShp.defaultLen.set(self.lenAdl.output.get())

        elemSide = (self.elem, self.side)
        aimAxisCap = self.aimAxis[-1].upper()
        if tipTwistParent:
            # bring back autoTwist
            self.midCtrl.autoTwist.showInChannelBox(True)
            self.midCtrl.autoTwist.setKeyable(True)

            self.autoTwstMdv = pm.createNode('multiplyDivide', n=naming.NAME('%sRbnAutoTwst' %self.elem, self.side, naming.MDV))
            
            pm.connectAttr(self.midCtrl.autoTwist, self.autoTwstMdv.input2X)
            pm.connectAttr(self.midCtrl.autoTwist, self.autoTwstMdv.input2Y)

            pm.connectAttr(self.autoTwstMdv.outputX, self.twstPma.input2D[0].input2Dx)
            pm.connectAttr(self.autoTwstMdv.outputY, self.twstPma.input2D[0].input2Dy)

            self.baseAutoTwstGrp = pm.group(em=True, n=naming.NAME('%sRbnBaseAutoTwst' %self.elem, self.side, naming.GRP))
            self.tipAutoTwstGrp = pm.group(em=True, n=naming.NAME('%sRbnTipAutoTwst' %self.elem, self.side, naming.GRP))

            misc.snapTransform('point', baseParent, self.baseAutoTwstGrp, False, True)
            misc.snapTransform('orient', self.baseJnt , self.baseAutoTwstGrp, False, True)

            misc.snapTransform('point', tipTwistParent, self.tipAutoTwstGrp, False, True)
            misc.snapTransform('orient', self.tipJnt, self.tipAutoTwstGrp, False, True)

            pm.parent(self.baseAutoTwstGrp, baseParent)
            pm.parent(self.tipAutoTwstGrp, tipTwistParent)

        # if twistParent:
            relMultMat = pm.createNode('multMatrix', n=naming.NAME('%sRbnTipAutoTwst' %self.elem, self.side, naming.MMTX))
            pm.connectAttr(self.tipAutoTwstGrp.worldMatrix[0], relMultMat.matrixIn[0])
            pm.connectAttr(self.baseAutoTwstGrp.worldInverseMatrix[0], relMultMat.matrixIn[1])
            
            dcMat = pm.createNode('decomposeMatrix', n=naming.NAME('%sRbnTipAutoTwst' %self.elem, self.side, naming.DMTX))
            pm.connectAttr(relMultMat.matrixSum, dcMat.inputMatrix)

            qte = pm.createNode('quatToEuler', n=naming.NAME('%sRbnTipAutoTwst' %self.elem, self.side, naming.QTE))
            pm.connectAttr(self.midCtrl.rotateOrder, qte.inputRotateOrder)
            pm.connectAttr(dcMat.attr('outputQuat%s' %aimAxisCap), qte.attr('inputQuat%s' %aimAxisCap))
            pm.connectAttr(dcMat.outputQuatW, qte.inputQuatW)
            pm.connectAttr(qte.attr('outputRotate%s' %aimAxisCap), self.autoTwstMdv.input1Y, f=True)

            if twistFromBase:
                self.baseNonRollAutoTwstGrp = pm.group(em=True, n=naming.NAME('%sRbnBaseNonRollAutoTwst' %self.elem, self.side, naming.GRP))
                misc.snapTransform('point', baseParent, self.baseNonRollAutoTwstGrp, False, True)
                misc.snapTransform('orient', self.baseJnt, self.baseNonRollAutoTwstGrp, False, True)

                self.tipNonRollAutoTwstGrp = pm.group(em=True, n=naming.NAME('%sRbnTipNonRollAutoTwst' %self.elem, self.side, naming.GRP))
                misc.snapTransform('point', tipTwistParent, self.tipNonRollAutoTwstGrp, False, True)
                misc.snapTransform('orient', self.tipJnt, self.tipNonRollAutoTwstGrp, False, True)

                # tipTwistParent MUST FOLLOW baseParent in order for twistFromBase to work!
                topParent = baseParent.getParent()
                if topParent:
                    pm.parent(self.baseNonRollAutoTwstGrp, topParent)

                pm.parent(self.tipNonRollAutoTwstGrp, baseParent)

                nrRelMultMat = pm.createNode('multMatrix', n=naming.NAME('%sRbnBaseNonRollAutoTwst' %self.elem, self.side, naming.MMTX))
                pm.connectAttr(self.tipNonRollAutoTwstGrp.worldMatrix[0], nrRelMultMat.matrixIn[0])
                pm.connectAttr(self.baseNonRollAutoTwstGrp.worldInverseMatrix[0], nrRelMultMat.matrixIn[1])
                
                nrDcMat = pm.createNode('decomposeMatrix', n=naming.NAME('%sRbnBaseNonRollAutoTwst' %self.elem, self.side, naming.DMTX))
                pm.connectAttr(nrRelMultMat.matrixSum, nrDcMat.inputMatrix)

                nrQte = pm.createNode('quatToEuler', n=naming.NAME('%sRbnBaseNonRollAutoTwst' %self.elem, self.side, naming.QTE))
                pm.connectAttr(self.midCtrl.rotateOrder, nrQte.inputRotateOrder)
                pm.connectAttr(nrDcMat.attr('outputQuat%s' %aimAxisCap), nrQte.attr('inputQuat%s' %aimAxisCap))
                pm.connectAttr(nrDcMat.outputQuatW, nrQte.inputQuatW)

                invMdl = pm.createNode('multDoubleLinear', n=naming.NAME('%sRbnBaseNonRollAutoTwst' %self.elem, self.side, naming.MDL))
                invMdl.input2.set(-1)
                pm.connectAttr(nrQte.attr('outputRotate%s' %aimAxisCap), invMdl.input1)
                pm.connectAttr(invMdl.output, self.autoTwstMdv.input1X, f=True)

class RibbonRig(RibbonBase):
    '''
    from nuTools.rigTools import ribbonRig as rr
    reload(rr)

    jnts = ['bodyDtl01_tmpJnt', 'bodyDtl02_tmpJnt', 'bodyDtl03_tmpJnt', 'bodyDtl04_tmpJnt', 'bodyDtl05_tmpJnt', 'bodyDtl06_tmpJnt', 'bodyDtl07_tmpJnt', 'bodyDtl08_tmpJnt', 'bodyDtl09_tmpJnt', 'bodyDtl10_tmpJnt']
    ctrlJnts = ['body01_tmpJnt', 'body02_tmpJnt', 'body03_tmpJnt', 'body04_tmpJnt']
    rbnRig = rr.RibbonRig(jnts=jnts,
                    ctrlJnts=ctrlJnts,
                    parent= 'main_ctrl',
                    
                    animGrp = 'Ctrl_Grp',
                    utilGrp = 'Jnt_Grp',
                    stillGrp = 'Still_Grp',
                    
                    aimAxis='+y',
                    upAxis='+x',
                    ctrlShp='crossCircle',
                    ctrlColor='yellow',
                    dtlCtrlShp='circle',
                    dtlCtrlColor='lightBlue',
                    localWorldRig=True)
    rbnRig.rig()
    '''
    def __init__(self, 
                jnts=[],
                ctrlJnts=[],
                aimAxis='+x',
                upAxis='+z',
                ctrlShp='crossCircle',
                ctrlColor='yellow',
                dtlCtrlShp='circle',
                dtlCtrlColor='lightBlue',
                localWorldRig=True,
                **kwargs):
        super(RibbonRig, self).__init__(aimAxis=aimAxis,
                                        upAxis=upAxis,
                                        **kwargs)

        self._tmpJnts = self.jntsArgs(jnts)
        self._ctrlTmpJnts = self.jntsArgs(ctrlJnts)

        self.ctrlShp = ctrlShp
        self.ctrlColor = ctrlColor
        self.dtlCtrlShp = dtlCtrlShp
        self.dtlCtrlColor = dtlCtrlColor
        self.localWorldRig = localWorldRig

        self.jnts = []
        self.ctrlJnts = []
        self.dtlCtrls = []
        self.dtlGCtrls = []
        self.ctrls = []
        self.gCtrls = []

        self.ctrlZgrps = []
        self.ctrlOffsetGrps = []
        self.ctrlSpaceGrps = []

        self.localGrps = []
        self.worldGrps = []
        self.localWorldCons = []

        self.posGrps = []
        self.posNodes = []
        self.aimNodes = []

        # path
        self.pathLocalGrps = []
        self.pathWorldGrps = []

        self.pathCtrls = []
        self.pathCtrlZGrps = []
        self.pathCtrlSpaceGrps = []

        self.stretch_multiplier = []

    def rig(self):
        # --- main grps
        _name = (self.elem, self.side)
        self.rigCtrlGrp = pm.group(em=True, n=naming.NAME('%sRbnRig' %self.elem, self.side, naming.GRP))
        self.rigUtilGrp = pm.group(em=True, n=naming.NAME('%sRbnUtil' %self.elem, self.side, naming.GRP))
        self.rigStillGrp = pm.group(em=True, n=naming.NAME('%sRbnStill' %self.elem, self.side, naming.GRP))
        self.rigStillGrp.visibility.set(False)

        # parent main grps
        pm.parent(self.rigCtrlGrp, self.animGrp)
        pm.parent(self.rigUtilGrp, self.utilGrp)
        pm.parent(self.rigStillGrp, self.stillGrp)

        # constraint to parent
        if self.parent:
            misc.snapTransform('parent', self.parent, self.rigCtrlGrp, True, False)
            misc.snapTransform('scale', self.parent, self.rigCtrlGrp, True, False)

        # detail ctrl group
        self.dtlCtrlGrp = pm.group(em=True, n=naming.NAME('%sRbnDtlCtrl' %self.elem, self.side, naming.GRP))
        pm.parent(self.dtlCtrlGrp, self.rigCtrlGrp)

        # detail joint group
        self.dtlJntGrp = pm.group(em=True, n=naming.NAME('%sRbnDtlJnt' %self.elem, self.side, naming.GRP))
        pm.parent(self.dtlJntGrp, self.rigUtilGrp)

        # create pos jnt
        self.allPosGrp = pm.group(em=True, n=naming.NAME('%sRbnPos' %self.elem, self.side, naming.GRP))
        pm.parent(self.allPosGrp, self.rigStillGrp)

        # --- create curve
        tmpJntLen = len(self._tmpJnts)
        ctrlTmpJntLen = len(self._ctrlTmpJnts)

        cmd = 'aCrv = pm.curve(d=2, p=['
        trs = []
        inb_indices = []
        side_points = []

        for i, tmpJnt in enumerate(self._ctrlTmpJnts):
            tr = tmpJnt.getTranslation(space='world')
            vec = misc.getVector(tmpJnt)[self.otherAxis[-1]]
            vec.normalize()
            vec *= 0.5
            trs.append(tr)

            aVec = vec + pm.dt.Point(tr)
            bVec = (vec * -1) + pm.dt.Point(tr)
            side_points.append((aVec, bVec))
            if i < ctrlTmpJntLen-1:
                next_jnt = self._ctrlTmpJnts[i+1]
                next_tr = next_jnt.getTranslation(space='world')
                mid_pt = ((next_tr - tr) * 0.5) + tr
                trs.append(mid_pt)
                inb_indices.append(len(trs)-1)

                next_vec = misc.getVector(next_jnt)[self.otherAxis[-1]]
                norm_vec = (vec+next_vec)
                norm_vec.normalize()
                norm_vec *= 0.5
                iaVec = norm_vec + mid_pt
                ibVec = (norm_vec * -1) + mid_pt
                side_points.append((iaVec, ibVec))
        positions = []
        for i, tr in enumerate(trs):
            positions.append('(%s, %s, %s)' %(tr[0], tr[1], tr[2]))

        cmd += ','.join(positions)
        cmd += '])'
        # print cmd
        exec(cmd)
        aCrvShp = aCrv.getShape()

        # insert knots
        pm.rebuildCurve(aCrv, ch=False, rpo=1, rt=0, end=1, kr=0, kcp=1, 
                        kep=1, kt=0, s=20, d=2, tol=0.01)

        bCrv = aCrv.duplicate()[0]
        # pm.move(aCrv, self.otherVec*0.5, r=True, os=True)
        # pm.move(bCrv, self.otherVec*-0.5, r=True, os=True)
        v = 0
        for i, pts in enumerate(side_points):
            # print pts
            pm.move(aCrv.cv[i], pts[0], ws=True)
            pm.move(bCrv.cv[i], pts[1], ws=True)

        self.createSurf(crvs=[aCrv, bCrv])
        pm.parent(self.surf, self.rigStillGrp)

        # main surface loop
        for i, tmpJnt in enumerate(self._tmpJnts):
            iName = (self.elem, (i + 1), self.side)
            
            # --- pos grp
            posGrp = pm.group(em=True, n=naming.NAME('%sRbnPos%s' %(self.elem, (i+1)), self.side, naming.GRP))
            posNode = pm.createNode('pointOnSurfaceInfo', n=naming.NAME('%sRbnPos%s' %(self.elem, (i+1)), self.side, naming.POSI))
            self.posNodes.append(posNode)
            self.posGrps.append(posGrp)

            tr = pm.xform(tmpJnt, q=True, ws=True, t=True)
            uvs = misc.getClosestSurfUvFromPoint(self.surf.getShape(), pm.dt.Vector(tr))
            posNode.parameterU.set(uvs[0])
            posNode.parameterV.set(uvs[1])

            aimCon = pm.createNode('aimConstraint', n=naming.NAME('%sRbn%s' %(self.elem, (i+1)), self.side, naming.AIMCON))
            pm.connectAttr(self.surf.worldSpace[0], posNode.inputSurface)
            pm.connectAttr(posNode.normal, aimCon.worldUpVector)
            pm.connectAttr(posNode.tangentV, aimCon.target[0].targetTranslate)
            pm.connectAttr(posNode.position, posGrp.translate)
            pm.connectAttr(aimCon.constraintRotate, posGrp.rotate)

            aimCon.aimVector.set(self.aimVec)
            aimCon.upVector.set(self.upVec)

            pm.parent(posGrp, self.allPosGrp)
            pm.parent(aimCon, posGrp)
            self.aimNodes.append(aimCon)

            # --- dtl jnt
            dtlJnt = tmpJnt.duplicate(po=True, n=naming.NAME('%sDtl%s' %(self.elem, (i+1)), self.side, naming.JNT))[0]
            dtlJntZroGrp = misc.zgrp(dtlJnt, element='JntZro', suffix='grp')[0]


            pm.parent(dtlJntZroGrp, self.dtlJntGrp)
            self.jnts.append(dtlJnt)

            misc.snapTransform('parent', posGrp, dtlJntZroGrp, True, True)

            # --- dtl ctrl
            dtlCtrl = controller.JointController(name=naming.NAME('%sDtl%s' %(self.elem, (i+1)), self.side, naming.CTRL),
                                                st=self.dtlCtrlShp, 
                                                color=self.dtlCtrlColor, 
                                                axis=self.aimAxis,
                                                scale=(self.size*0.75),
                                                draw=False)
            dtlCtrl.lockAttr(v=True)
            dtlCtrl.hideAttr(v=True)
            dtlCtrl.rotateOrder.set(self.rotateOrder)
            dtlCtrlGCtrl = dtlCtrl.addGimbal()
            dtlCtrlZroGrp = misc.zgrp(dtlCtrl, element='CtrlZro', suffix='grp')[0]
            pm.parent(dtlCtrlZroGrp, self.dtlCtrlGrp)

            self.dtlCtrls.append(dtlCtrl)
            self.dtlGCtrls.append(dtlCtrlGCtrl)

            misc.snapTransform('parent', dtlJnt, dtlCtrlZroGrp, False, True)

            misc.snapTransform('parent', posGrp, dtlCtrlZroGrp, True, False)

            misc.snapTransform('parent', dtlCtrlGCtrl, dtlJntZroGrp, False, False)
            misc.snapTransform('scale', dtlCtrlGCtrl, dtlJntZroGrp, False, False)

        localObj = self.rigCtrlGrp
        worldObj = self.animGrp

        for i in xrange(ctrlTmpJntLen):
            tmpCtrlJnt = self._ctrlTmpJnts[i]
            iName = (self.elem, (i + 1), self.side)

            # --- dtl jnt
            ctrlJnt = tmpCtrlJnt.duplicate(po=True, n=naming.NAME('%s%s' %(self.elem, (i+1)), self.side, naming.JNT))[0]
            self.ctrlJnts.append(ctrlJnt)

            if i > 0:
                pm.parent(ctrlJnt, self.ctrlJnts[i-1])
            else:
                pm.parent(ctrlJnt, self.rigUtilGrp)

            # # if this is not the last joint
            # if i < ctrlTmpJntLen - 1:
            # --- dtl ctrl
            ctrl = controller.JointController(name=naming.NAME('%s%s' %(self.elem, (i+1)), self.side, naming.CTRL),
                                                st=self.ctrlShp, 
                                                color=self.ctrlColor, 
                                                axis=self.aimAxis,
                                                scale=(self.size),
                                                draw=False)
            ctrl.lockAttr(s=True, v=True)
            ctrl.hideAttr(s=True, v=True)
            ctrl.rotateOrder.set(self.rotateOrder)
            gCtrl = ctrl.addGimbal()

            ctrlOffsetGrp = misc.zgrp(ctrl, element='Ofst', suffix='grp', preserveHeirachy=True)[0]
            ctrlSpaceGrp = misc.zgrp(ctrlOffsetGrp, element='Space', remove='Ofst', suffix='grp', preserveHeirachy=True)[0]
            ctrlZgrp = misc.zgrp(ctrlSpaceGrp, element='Zro', remove='Space', suffix='grp')[0]
            
            misc.snapTransform('parent', ctrlJnt, ctrlZgrp, False, True)

            if i > 0:
                localObj = self.gCtrls[i-1]
                worldObj = self.rigCtrlGrp
                ctrlParent = self.gCtrls[i-1]
            else:
                ctrlParent = self.rigCtrlGrp

            pm.parent(ctrlZgrp, ctrlParent)

            self.ctrls.append(ctrl)
            self.gCtrls.append(gCtrl)
            self.ctrlZgrps.append(ctrlZgrp)
            self.ctrlOffsetGrps.append(ctrlOffsetGrp)
            self.ctrlSpaceGrps.append(ctrlSpaceGrp)

            misc.snapTransform('parent', gCtrl, ctrlJnt, False, False)

            if self.localWorldRig == True and i > 0:
                localWorldRets = misc.createLocalWorld(objs=[self.ctrls[i], worldObj, localObj, 
                                    self.ctrlSpaceGrps[i]], 
                                    constraintType='parent', 
                                    attrName='follow')
                self.localGrps.append(localWorldRets['local'])
                self.worldGrps.append(localWorldRets['world'])
                self.localWorldCons.append(localWorldRets['constraint'])

        baseCtrlShp = self.ctrls[0].getShape()

        # dtl vis ctrl
        dtlCtrlVisAttr = misc.addNumAttr(baseCtrlShp, 'detailCtrl_vis', 'long', min=0, max=1, dv=0, key=False)
        pm.connectAttr(dtlCtrlVisAttr, self.dtlCtrlGrp.visibility)

        # bind the surface
        self.skinCluster = pm.skinCluster(self.ctrlJnts, self.surf, 
                                        tsb=True, dr=2, mi=2)

        # set skin weights
        numV = self.surf.numCVsInV()
        self.lockInf(jnts=self.ctrlJnts, value=False)
        for u in xrange(2):
            c = 0
            for v in xrange(numV):
                # print v
                if v not in inb_indices:
                    pm.skinPercent(self.skinCluster, self.surf.cv[u][v], tv=[self.ctrlJnts[c], 1.0])
                    c += 1
                else:
                    pm.skinPercent(self.skinCluster, self.surf.cv[u][v], tv=[self.ctrlJnts[c], 0.5])
                    pm.skinPercent(self.skinCluster, self.surf.cv[u][v], tv=[self.ctrlJnts[c-1], 0.5])

    def attach_to_curve(self, curve, localWorldRig=True, ctrlShp='diamond3d'):
        if isinstance(curve, (str, unicode)):
            curve = pm.PyNode(curve)

        # delete old local world
        try: pm.delete(self.localWorldCons) 
        except: pass
        try: pm.delete(self.localGrps) 
        except: pass
        try: pm.delete(self.worldGrps) 
        except: pass

        self.pathCtrlGrp = pm.group(em=True, n=naming.NAME('%sPathCtrl' %self.elem, self.side, naming.GRP))
        pm.parent(self.pathCtrlGrp, self.rigCtrlGrp)

        self.pathStillGrp = pm.group(em=True, n=naming.NAME('%sPathStill' %self.elem, self.side, naming.GRP))
        self.pathStillGrp.visibility.set(False)
        pm.parent(self.pathStillGrp, self.rigStillGrp)

        # create surface
        aTmpCrv = pm.duplicate(curve)[0]
        bTmpCrv = pm.duplicate(curve)[0]

        pm.xform(aTmpCrv, r=True, ws=True, t=(self.otherVec*self.size*0.1))
        pm.xform(bTmpCrv, r=True, ws=True, t=(self.otherVec*self.size*-0.1))
        self.pathSurf = pm.loft([aTmpCrv, bTmpCrv], ss=1, ch=False)[0]
        self.pathSurf.rename(naming.NAME('%sPath' %self.elem, self.side, naming.NRBS))
        self.pathSurf.inheritsTransform.set(False)
        misc.setDisplayType(obj=self.pathSurf, shp=True, disType='reference')
        pm.parent(self.pathSurf, self.rigCtrlGrp)
        pm.delete([aTmpCrv, bTmpCrv])

        # rig the curve
        numU = self.pathSurf.numCVsInU()
        numV = self.pathSurf.numCVsInV()
        for vi in xrange(numV):
            ctrl = controller.JointController(n=naming.NAME('%sPath%s' %(self.elem, (vi+1)), self.side, naming.CTRL),
                                            st=ctrlShp, scale=(self.size*0.3), color='pink')
            misc.lockAttr(ctrl, t=False, r=False, s=True, v=True)
            misc.hideAttr(ctrl, t=False, r=False, s=True, v=True)

            spaceGrp = misc.zgrp(ctrl, element='Space', suffix='grp', preserveHeirachy=True)[0]
            zgrp = misc.zgrp(spaceGrp, element='Zro', suffix='grp', preserveHeirachy=True)[0]

            # snap zgrp
            center = misc.getCenterOfVertices(self.pathSurf.cv[0:(numU-1)][vi])
            pm.xform(zgrp, ws=True, t=center)
            
            self.pathCtrls.append(ctrl)
            self.pathCtrlSpaceGrps.append(spaceGrp)
            self.pathCtrlZGrps.append(zgrp)

            # parent
            if vi > 0:
                ctrlParent = self.pathCtrls[vi-1]
            else:
                ctrlParent = self.pathCtrlGrp
            pm.parent(zgrp, ctrlParent)

            if localWorldRig and vi > 0:
                misc.createLocalWorld(objs=[ctrl, 
                                    self.pathCtrlGrp, 
                                    self.pathCtrls[vi-1], 
                                    spaceGrp], 
                                    constraintType='parent', 
                                    attrName='follow')

        self.pathSkinCluster = pm.skinCluster(self.pathCtrls, self.pathSurf, 
                                        tsb=True, dr=2, mi=2)
        # paint weights for path surface
        for vi in xrange(numV):
            pm.skinPercent(self.pathSkinCluster, self.pathSurf.cv[0:(numU-1)][vi], tv=[self.pathCtrls[vi], 1.0])
  
        # add attr to first ctrl
        misc.addNumAttr(self.ctrls[0], '__path__', 'double', lock=True)
        slideAttr = misc.addNumAttr(self.ctrls[0], 'slide', 'double', dv=0.0, min=0.0)
         # tone down the strength of slide
        slideMdl = pm.createNode('multDoubleLinear', n=naming.NAME('%sPathSlide' %self.elem, self.side, naming.MDL))
        slideMdl.input2.set(0.01)
        pm.connectAttr(slideAttr, slideMdl.input1)

        frontStretchAttr = misc.addNumAttr(self.ctrls[0], 'frontStretch', 'double', dv=0.0)
        backStretchAttr = misc.addNumAttr(self.ctrls[0], 'backStretch', 'double', dv=0.0)
        twAttr = misc.addNumAttr(self.ctrls[0], 'twist', 'double', dv=0.0)
        # twist connections
        for jnt in self.jnts:
            pm.connectAttr(twAttr, jnt.attr('r%s' %(self.aimAxis[-1])))

        ctrlPathAttr = misc.addNumAttr(self.ctrls[0].getShape(), 'pathCtrl_vis', 'long', dv=1, min=0, max=1, key=False)
        pm.connectAttr(ctrlPathAttr, self.pathCtrlGrp.visibility)

        # figure out multiplier for stretch
        posValues = []
        surfShp = self.surf.getShape()
        for ctrl in self.ctrls:
            ctrlPos = ctrl.getTranslation(space='world')
            u, v = misc.getClosestSurfUvFromPoint(surf=surfShp, point=ctrlPos)
            posValues.append(v)

        minVal = min(posValues)
        maxVal = max(posValues)
        valRange = maxVal - minVal
        
        for value in posValues:
            nv = (value - minVal) / valRange
            self.stretch_multiplier.append(nv)

        inv_stretch_multiplier = self.stretch_multiplier[::-1]
        # loop over offset group
        for i, ofGrp in enumerate(self.ctrlOffsetGrps):
            position = ofGrp.getTranslation(space='world')
            rets = misc.createRivetFromPosition_Nurbs(shape=self.pathSurf.getShape(), 
                        position=position, 
                        name=('%s%s' %(self.elem, (i+1)), self.side),
                        aimVector=self.aimVec,
                        upVector=self.upVec*-1)

            # print self.upVec, self.aimVec
            loc = rets['transform']
            node = rets['node']
            locShp = loc.getShape()
            locShp.visibility.set(False)
            pm.parent(loc, self.pathStillGrp)
            # print ofGrp, node.parameterU.get(), node.parameterV.get()
            # create par grp
            parGrp = None
            worldGrp = None
            zroGrp = self.ctrlZgrps[i]
            if i > 0:
                # misc.snapPivot(self.ctrlZgrps[i-1], zroGrp)

                # create world group
                worldGrp = pm.group(em=True, n=naming.NAME('%sPath%sCrvSpace' %(self.elem, (i+1)), self.side, naming.GRP))
                worldGrp.rotateOrder.set(self.rotateOrder)
                misc.snapTransform('parent', zroGrp, worldGrp, False, True)
                pm.parent(worldGrp, zroGrp)
                misc.snapTransform('parent', loc, worldGrp, True, False)
                self.pathWorldGrps.append(worldGrp)

                localParent = self.pathLocalGrps[i-1]
            else:
                localParent = self.rigCtrlGrp

            # create local group
            localGrp = pm.group(em=True, n=naming.NAME('%sPath%sParentSpace' %(self.elem, (i+1)), self.side, naming.GRP))
            localGrp.rotateOrder.set(self.rotateOrder)
            localZroGrp = misc.zgrp(localGrp, element='Zro', suffix='grp')[0]
            misc.snapTransform('parent', ofGrp, localZroGrp, False, True)
            misc.snapTransform('parent', loc, localGrp, True, False)
            pm.parent(localZroGrp, localParent)
            self.pathLocalGrps.append(localGrp)

            # connect slide
            pathPma = pm.createNode('plusMinusAverage', n=naming.NAME('%sPath%sSum' %(self.elem, (i+1)), self.side, naming.PMA))
            pathCmp = pm.createNode('clamp', n=naming.NAME('%sPath%sSum' %(self.elem, (i+1)), self.side, naming.CMP))
            pathCmp.minR.set(0.0)
            pathCmp.maxR.set(1.0)

            pathPma.input1D[0].set(node.parameterV.get())
            pm.connectAttr(slideMdl.output, pathPma.input1D[1])
            pm.connectAttr(pathPma.output1D, pathCmp.inputR) 
            pm.connectAttr(pathCmp.outputR, node.parameterV)

            # connect font stretch
            frStretchMdl = pm.createNode('multDoubleLinear', n=naming.NAME('%sPath%sFrontStch' %(self.elem, (i+1)), self.side, naming.MDL))
            frStretchMdl.input2.set(self.stretch_multiplier[i] * 0.1)
            pm.connectAttr(self.ctrls[0].frontStretch, frStretchMdl.input1)
            pm.connectAttr(frStretchMdl.output, pathPma.input1D[2])

            # connect font stretch
            bkStretchMdl = pm.createNode('multDoubleLinear', n=naming.NAME('%sPath%sBackStch' %(self.elem, (i+1)), self.side, naming.MDL))
            bkStretchMdl.input2.set(inv_stretch_multiplier[i] * -0.1)
            pm.connectAttr(self.ctrls[0].backStretch, bkStretchMdl.input1)
            pm.connectAttr(bkStretchMdl.output, pathPma.input1D[3])

            # connect localWorld
            if i > 0:
                misc.addNumAttr(self.ctrls[i], 'follow', 'double', dv=0.0, min=0.0, max=1.0)

                tbcol = pm.createNode('blendColors', n=naming.NAME('%sPath%sTrLocWor' %(self.elem, (i+1)), self.side, naming.BCOL))
                rbcol = pm.createNode('blendColors', n=naming.NAME('%sPath%sRotLocWor' %(self.elem, (i+1)), self.side, naming.BCOL))
                pm.connectAttr(self.ctrls[i].follow, tbcol.blender)
                pm.connectAttr(self.ctrls[i].follow, rbcol.blender)
                for axis, color in zip('xyz', 'RGB'):
                    pm.connectAttr(localGrp.attr('t%s' %axis), tbcol.attr('color1%s' %color))
                    pm.connectAttr(worldGrp.attr('t%s' %axis), tbcol.attr('color2%s' %color))
                    
                    pm.connectAttr(tbcol.attr('output %s'%color), self.ctrlSpaceGrps[i].attr('t%s' %axis))
                for axis, color in zip('xyz', 'RGB'):
                    pm.connectAttr(localGrp.attr('r%s' %axis), rbcol.attr('color1%s' %color))
                    pm.connectAttr(worldGrp.attr('r%s' %axis), rbcol.attr('color2%s' %color))
                    pm.connectAttr(rbcol.attr('output %s'%color), self.ctrlSpaceGrps[i].attr('r%s' %axis))
            else:
                for axis in 'xyz':
                    pm.connectAttr(localGrp.attr('t%s' %axis), self.ctrlSpaceGrps[i].attr('t%s' %axis))
                    pm.connectAttr(localGrp.attr('r%s' %axis), self.ctrlSpaceGrps[i].attr('r%s' %axis))
                
    def create_sine(self):
        import math

        baseCtrl = self.ctrls[0]
        misc.addNumAttr(baseCtrl, '__sine__', 'double', lock=True)
        upEnvAttr = misc.addNumAttr(baseCtrl, 'sineUp', 'double', dv=0.0, min=0.0, max=1.0)
        sideEnvAttr = misc.addNumAttr(baseCtrl, 'sineSide', 'double', dv=0.0, min=0.0, max=1.0)
        ampAttr = misc.addNumAttr(baseCtrl, 'height', 'double', dv=1.0)
        freqAttr = misc.addNumAttr(baseCtrl, 'frequency', 'double', dv=2.0, min=0.001)
        speedAttr = misc.addNumAttr(baseCtrl, 'speed', 'double', dv=5.0)
        offsetAttr = misc.addNumAttr(baseCtrl, 'offset', 'double', dv=0.0)
        pinAttr = misc.addNumAttr(baseCtrl, 'pin', 'enum', enum='None:Base:Tip:Both:', dv=0, min=0, max=3)

        ctrlShps = []
        for ctrl in self.ctrls:
            ctrlShp = ctrl.getShape()
            misc.addNumAttr(ctrlShp, 'sineAmp', 'double', dv=1.0, key=False)
            ctrlShps.append(ctrlShp.shortName())

        # create expressions
        baseCtrlName = baseCtrl.shortName()
        upAxis = self.upAxis[-1]
        sideAxis = self.otherAxis[-1]
        lenCtrls = len(self.ctrlOffsetGrps)
        # c = 360.0 / (len(self.ctrlOffsetGrps) - 1)
        exp = 'float $ue = {0}.sineUp;'.format(baseCtrlName)
        exp += 'float $se = {0}.sineSide;'.format(baseCtrlName)
        exp += '\nif(($ue > 0.0)||($se > 0.00)) {'

        exp += '\n\tfloat $h = {0}.height;'.format(baseCtrlName)
        exp += '\n\tfloat $f = {0}.frequency;'.format(baseCtrlName)
        exp += '\n\tfloat $s = {0}.speed * time;'.format(baseCtrlName)
        exp += '\n\tfloat $offset = {0}.offset;'.format(baseCtrlName)
        exp += '\n\tint $mode = {0}.pin;'.format(baseCtrlName)
        # none mode
        oneStr = '1,'*lenCtrls
        exp += '\n\tfloat $mults[] = {%s};' %(oneStr[:-1])

        # base pin mode
        mults = []
        exp += '\n\tif($mode == 1) {'
        l = 1.0 / (lenCtrls - 1)
        for i in xrange(lenCtrls):
            x = i*l
            p = -15 * x
            r = 1 + math.pow(1.7, p)
            value = ((2/r)-1) * 1.0007
            value = round(value, 3)
            mults.append(value)
        exp += '$mults = {%s};}' %(','.join([str(m) for m in mults]))

        # tip pin mode
        exp += '\n\telse if($mode == 2) {'
        inv_mults = mults[::-1]
        exp += '$mults = {%s};}' %(','.join([str(m) for m in inv_mults]))

        # both pin mode
        exp += '\n\telse if($mode == 3) {'
        sl = 180.0 / (lenCtrls - 1)
        both_mults = []
        for i in xrange(lenCtrls):
            s = math.sin(math.radians(sl*i))
            s = round(s, 3)
            both_mults.append(s)
        exp += '$mults = {%s};}' %(','.join([str(m) for m in both_mults]))

        for i, ofGrp in enumerate(self.ctrlOffsetGrps):
            ofGrpName = ofGrp.shortName()
            exp += '\n\t{0}.t{1} = sin($s + ({2}*$f) + $offset) * $h * $ue * $mults[{2}] * {3}.sineAmp;'.format(ofGrpName, upAxis, i, ctrlShps[i])
            exp += '\n\t{0}.t{1} = sin($s + ({2}*$f) + $offset) * $h * $se * $mults[{2}] * {3}.sineAmp;'.format(ofGrpName, sideAxis, i, ctrlShps[i])
        exp += '\n}else {'

        for i, ofGrp in enumerate(self.ctrlOffsetGrps):
            ofGrpName = ofGrp.shortName()
            exp += '\n\t{0}.t{1} = 0;'.format(ofGrpName, upAxis)
            exp += '\n\t{0}.t{1} = 0;'.format(ofGrpName, sideAxis)
        exp += '\n}'

        expNode = pm.expression(s=exp, n=naming.NAME('%sSine' %self.elem, self.side, naming.EXP))

