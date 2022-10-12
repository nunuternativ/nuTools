from math import e as e_cons

import pymel.core as pm

from nuTools import misc, controller
reload(misc)
reload(controller)
import nuTools.rigTools.baseRig as baseRig
reload(baseRig)

class ArmRig(baseRig.BaseRig):
	def __init__(self, 
				jnts=[],
				aimAxis='y',
				fkRotateOrder='yxz',
				ikRotateOrder='zxy',
				**kwargs):
		super(ArmRig, self).__init__(**kwargs)
		# temp joints
		self.tmpJnts = self.jntsArgs(jnts)

		# axis
		self.aimAxis = aimAxis
		self.fkRotateOrder = fkRotateOrder
		self.ikRotateOrder = ikRotateOrder

		# joints
		self.jnts = []
		self.fkJnts = []
		self.ikJnts = []

		# controllers
		self.settingCtrl = []
		self.fkCtrls = []
		self.fkGCtrls = []
		self.ikCtrls = []
		self.ikGCtrls = []

		# groups
		self.fkCtrlOfstGrps = []
		self.fkCtrlZgrps = []

		self.ikCtrlOfstGrps = []
		self.ikCtrlZgrps = []

		# Iks
		self.ikHndls = []
		self.ikEffs = []
		self.ikHndlZgrps = []

	def rig(self):
		# --- translate axis from string to vector
		aimAxis = misc.vectorStr(self.aimAxis)
		aimTran = 't%s' %(self.aimAxis[-1])

		# --- get class name to use for naming
		_name = (self.elem, self.side)

		# --- create main groups
		self.rigCtrlGrp = pm.group(em=True, n='%sRig%s_grp' %_name)
		self.rigFkCtrlGrp = pm.group(em=True, n='%sFkCtrl%s_grp' %_name)
		self.rigIkCtrlGrp = pm.group(em=True, n='%sIkCtrl%s_grp' %_name)
		pm.parent([self.rigFkCtrlGrp, self.rigIkCtrlGrp], self.rigCtrlGrp)

		self.rigUtilGrp = pm.group(em=True, n='%sUtil%s_grp' %_name)
		self.rigIkhGrp = pm.group(em=True, n='%sIkh%s_grp' %_name)
		# self.rigUtilGrp.visibility.set(False)
		self.rigIkhGrp.visibility.set(False)
		pm.parent([self.rigIkhGrp], self.rigUtilGrp)

		# self.rigSkinGrp = pm.group(em=True, n='%sSkin%s_grp' %_name)
		# self.rigStillGrp = pm.group(em=True, n='%sStill%s_grp' %_name)
		# self.rigStillGrp.visibility.set(False)

		# parent main grps
		pm.parent(self.rigCtrlGrp, self.animGrp)
		pm.parent(self.rigUtilGrp, self.utilGrp)
		# pm.parent(self.rigStillGrp, self.stillGrp)
		self.parentCons =  misc.snapTransform('parent', self.parent, self.rigCtrlGrp, True, False)

		# --- create setting controller
		self.settingCtrl = controller.Controller(name='%sSetting%s_ctrl' %_name, 
					st='stick', 
					axis='-z',
					color='green', 
					scale=(self.size))
		self.settingCtrl.lockAttr(t=True, r=True, s=True, v=True)
		self.settingCtrl.hideAttr(t=True, r=True, s=True, v=True)
		sizeAttr = misc.addNumAttr(self.settingCtrl, 'size', 'double', hide=False, dv=1.0)
		fkikAttr = misc.addNumAttr(self.settingCtrl, 'fkIk', 'double', hide=False, min=0, max=1, dv=0.0)
		
		# add attribute on setting controller
		settingCtrlShp = self.settingCtrl.getShape()
		# misc.addNumAttr(settingCtrlShp, 'stretchAmp', 'double', hide=False, min=0, max=1, dv=0.1)

		# group setting controller
		settingCtrlZgrp = misc.zgrp(self.settingCtrl, element='Zro', suffix='grp')[0]
		misc.snapTransform('parent', self.tmpJnts[2], settingCtrlZgrp, False, True)

		# create reverse node on fkIk switch attribute and connect
		ikfkRev = pm.createNode('reverse', n='%sIkFk%s_rev' %_name)
		pm.connectAttr(fkikAttr, ikfkRev.inputX)
		pm.connectAttr(fkikAttr, self.rigIkCtrlGrp.visibility)
		pm.connectAttr(ikfkRev.outputX, self.rigFkCtrlGrp.visibility)

		# --- create main, fk and ik jnts
		jntElems = ['', 'Fk', 'Ik']
		pos = ['Upr', 'Elbow', 'Wrist', 'Hand']
		jlst = ['self.jnts', 'self.fkJnts', 'self.ikJnts']
		glst = [ 'self.rigUtilGrp', 'self.rigFkCtrlGrp', 'self.rigIkCtrlGrp']
		rad = self.tmpJnts[0].radius.get()
		m = 1.0  # radius multiplier
		for e in xrange(3):
			# duplicate joint from tmpJnt
			upJnt = pm.duplicate(self.tmpJnts[0], po=True, n='%s%s%s%s_jnt' %(self.elem, pos[0], jntElems[e], self.side))[0]
			elbowJnt = pm.duplicate(self.tmpJnts[1], po=True, n='%s%s%s%s_jnt' %(self.elem, pos[1], jntElems[e], self.side))[0]
			wristJnt = pm.duplicate(self.tmpJnts[2], po=True, n='%s%s%s%s_jnt' %(self.elem, pos[2], jntElems[e], self.side))[0]
			handJnt = pm.duplicate(self.tmpJnts[3], po=True, n='%s%s%s%s_jnt' %(self.elem, pos[3], jntElems[e], self.side))[0]

			# parent into fk chain
			pm.parent(handJnt, wristJnt)
			pm.parent(wristJnt, elbowJnt)
			pm.parent(elbowJnt, upJnt)
			
			# set radius
			for j in [upJnt, elbowJnt, wristJnt, handJnt]:
				j.radius.set(rad*m)

			# freeze it
			pm.makeIdentity(upJnt, apply=True)

			# store to list
			exec('%s = [upJnt, elbowJnt, wristJnt, handJnt]' %jlst[e])
			# exec('pm.parent(upJnt, %s)' %glst[e])

			if e > 0:
				# hide ik/fk jnts
				upJnt.visibility.set(False)

			# connect scale
			pm.connectAttr(self.settingCtrl.size, wristJnt.scaleX)
			pm.connectAttr(self.settingCtrl.size, wristJnt.scaleY)
			pm.connectAttr(self.settingCtrl.size, wristJnt.scaleZ)
			
			pm.parent(upJnt, self.rigUtilGrp)

			m *= 0.5

		# add zro joint to ik and fk chain
		# zroFkJnts = misc.addOffsetJnt(sels=self.fkJnts, element='Zro')
		# zroIkJnts = misc.addOffsetJnt(sels=self.ikJnts, element='Zro')

		# --- parent and scale constraint main joint to both ik and fk joint
		for j in xrange(3):
			parConsNode = pm.parentConstraint([self.fkJnts[j], self.ikJnts[j]], self.jnts[j])
			# connect parent cons
			pm.connectAttr(ikfkRev.outputX, parConsNode.attr('%sW0' %self.fkJnts[j].nodeName()))
			pm.connectAttr(self.settingCtrl.fkIk, parConsNode.attr('%sW1' %self.ikJnts[j].nodeName()))

			# scConsNode = pm.scaleConstraint([self.fkJnts[j], self.ikJnts[j]], self.jnts[j])
			# connect scale cons
			# pm.connectAttr(ikfkRev.outputX, scConsNode.attr('%sW0' %self.fkJnts[j].nodeName()))
			# pm.connectAttr(self.settingCtrl.fkIk, scConsNode.attr('%sW1' %self.ikJnts[j].nodeName()))

		# throw setting zgrp to ctrl group
		pm.parent(settingCtrlZgrp, self.rigCtrlGrp)
		misc.snapTransform('parent', self.jnts[2], settingCtrlZgrp, False, False)

		# ------ FK rig
		for i in xrange(3):
			fkCtrl = controller.JointController(name='%s%sFk%s_ctrl' %(self.elem, pos[i], self.side),
										st='crossCircle', scale=self.size)
			fkCtrl.rotateOrder.set(self.fkRotateOrder)
			fkCtrl.setColor('red')
			
			fkGCtrl = fkCtrl.addGimbal()

			fkCtrlOfst = misc.zgrp(fkCtrl, element='Ofst', suffix='grp')[0]
			fkCtrlZgrp = misc.zgrp(fkCtrlOfst, element='Zro', suffix='grp')[0]

			self.fkGCtrls.append(fkGCtrl)
			self.fkCtrls.append(fkCtrl)
			self.fkCtrlOfstGrps.append(fkCtrlOfst)
			self.fkCtrlZgrps.append(fkCtrlZgrp)

			parent = self.rigFkCtrlGrp
			if i > 0:
				misc.snapTransform('parent', self.fkJnts[i], fkCtrlZgrp, False, True)
				parent = self.fkGCtrls[i-1]
			else:
				misc.snapTransform('point', self.fkJnts[i], fkCtrlZgrp, False, True)
				misc.snapTransform('orient', self.fkJnts[i], fkCtrl, False, True)
				pm.makeIdentity(fkCtrl, apply=True, t=True, r=True, s=True)

			pm.parent(fkCtrlZgrp, parent)
			misc.snapTransform('parent', fkGCtrl, self.fkJnts[i], False, False)

			fkCtrl.lockAttr(t=False, s=True, v=True)
			fkCtrl.hideAttr(t=False, s=True, v=True)

		# --- connect Fk stretch
		pos = ['Upr', 'Lwr']
		defaultLenAttrs, stretchLenAttrs = [], []
		for i in xrange(2):
			# add default len attr
			defaultLenValue = self.fkJnts[i+1].attr(aimTran).get()
			defLenAttr = misc.addNumAttr(settingCtrlShp, 'defaultLen%s' %(pos[i]), 'double', key=False, hide=True, dv=defaultLenValue)

			stretchLenValue = misc.getDistanceFromPosition(self.fkJnts[i].getTranslation('world'), self.fkJnts[i+1].getTranslation('world'))
			stretchLenAttr = misc.addNumAttr(settingCtrlShp, 'stretchLen%s' %(pos[i]), 'double', key=False, hide=True, dv=stretchLenValue)

			# stretchAmpMdl = pm.createNode('multDoubleLinear', n='%s%sFkStretchAmp%s_mdl' %(self.elem, pos[i], self.side))
			stretchMdl = pm.createNode('multDoubleLinear', n='%s%sFkStretch%s_mdl' %(self.elem, pos[i], self.side))
			stretchAdl = pm.createNode('addDoubleLinear', n='%s%sFkStretch%s_adl' %(self.elem, pos[i], self.side))
			misc.addNumAttr(self.fkCtrls[i], 'stretch', 'double')

			# pm.connectAttr(self.fkCtrls[i].stretch, stretchAmpMdl.input1)
			# pm.connectAttr(settingCtrlShp.stretchAmp, stretchAmpMdl.input2)
			pm.connectAttr(self.fkCtrls[i].stretch, stretchMdl.input1)
			pm.connectAttr(defLenAttr, stretchMdl.input2)
			pm.connectAttr(defLenAttr, stretchAdl.input1)
			pm.connectAttr(stretchMdl.output, stretchAdl.input2)
			pm.connectAttr(stretchAdl.output, self.fkCtrlZgrps[i+1].attr(aimTran))

			defLenAttr.setKeyable(False)
			defLenAttr.showInChannelBox(False)
			defLenAttr.setLocked(True)
			defaultLenAttrs.append(defLenAttr)

			stretchLenAttr.setKeyable(False)
			stretchLenAttr.showInChannelBox(False)
			# stretchLenAttr.setLocked(True)
			stretchLenAttrs.append(stretchLenAttr)

		# --- local world for uparm
		# misc.addNumAttr(self.fkCtrls[i], 'localWorld', 'double', dv=1.0)
		misc.createLocalWorld(objs=[self.fkCtrls[0], self.rigFkCtrlGrp, self.animGrp, self.fkCtrlZgrps[0]], 
			constraintType='orient', attrName='localWorld')

		# --- create default len attrs on setting ctrl shape
		defLimbLenAttr = misc.addNumAttr(settingCtrlShp, 'defaultLen', 'double', key=False, hide=True, dv=defaultLenValue)
		defLenAdl = pm.createNode('addDoubleLinear', n='%sDefaultLen%s_adl' %_name)
		pm.connectAttr(defaultLenAttrs[0], defLenAdl.input1)
		pm.connectAttr(defaultLenAttrs[1], defLenAdl.input2)
		pm.connectAttr(defLenAdl.output, defLimbLenAttr)

		defLimbLenAttr.setKeyable(False)
		defLimbLenAttr.showInChannelBox(False)
		defLimbLenAttr.setLocked(True)

		# --- create default dist attrs on setting ctrl shape
		stretchLenAttr = misc.addNumAttr(settingCtrlShp, 'stretchLen', 'double', key=False, hide=True, dv=defaultLenValue)
		stretchLenAdl = pm.createNode('addDoubleLinear', n='%sstretchLen%s_adl' %_name)
		pm.connectAttr(stretchLenAttrs[0], stretchLenAdl.input1)
		pm.connectAttr(stretchLenAttrs[1], stretchLenAdl.input2)
		pm.connectAttr(stretchLenAdl.output, stretchLenAttr)

		stretchLenAttr.setKeyable(False)
		stretchLenAttr.showInChannelBox(False)
		stretchLenAttr.setLocked(True)

		# ------ IK rig
		# --- armRoot ik ctrl
		baseIkCtrl = controller.JointController(name='%sIkBase%s_ctrl' %(_name),
										st='locator', scale=self.size)
		baseIkCtrl.setColor('blue')
		baseIkCtrl.lockAttr(r=True, s=True, v=True)
		baseIkCtrl.hideAttr(r=True, s=True, v=True)
		baseIkCtrlOfstGrp = misc.zgrp(baseIkCtrl, element='Ofst', suffix='grp')[0]	
		baseIkCtrlZgrp = misc.zgrp(baseIkCtrlOfstGrp, element='Zro', suffix='grp')[0]	

		# --- arm pv ctrl
		pvIkCtrl = controller.JointController(name='%sIkPv%s_ctrl' %(_name),
										st='diamond3d', scale=self.size*0.334)
		pvIkCtrl.setColor('blue')
		pvIkCtrl.lockAttr(r=True, s=True, v=True)
		pvIkCtrl.hideAttr(r=True, s=True, v=True)
		pinAttr = misc.addNumAttr(pvIkCtrl, 'pin', 'double', min=0, max=1, dv=0)
		
		pvIkCtrlOfstGrp = misc.zgrp(pvIkCtrl, element='Ofst', suffix='grp')[0]
		pvIkCtrlZgrp = misc.zgrp(pvIkCtrlOfstGrp, element='Zro', suffix='grp')[0]
		pvIkCtrlLocWorAttr = misc.addNumAttr(pvIkCtrl, 'localWorld', 'double', min=0, max=1, dv=0)
		

		# --- armIK ctrl
		mainIkCtrl = controller.JointController(name='%sIk%s_ctrl' %(_name),
										st='diamond', scale=self.size)
		mainIkCtrl.rotateOrder.set(self.ikRotateOrder)
		mainIkCtrl.setColor('blue')
		mainIkGCtrl = mainIkCtrl.addGimbal()
		
		mainIkCtrlOfstGrp = misc.zgrp(mainIkCtrl, element='Ofst', suffix='grp')[0]
		mainIkCtrlZgrp = misc.zgrp(mainIkCtrlOfstGrp, element='Zro', suffix='grp')[0]

		# add attributes
		ikCtrlLocWorAttr = misc.addNumAttr(mainIkCtrl, 'localWorld', 'double', min=0, max=1, dv=1)
		ikCtrlSepAttr = misc.addNumAttr(mainIkCtrl, '__ik__', 'double', hide=False, min=0, max=1, dv=0)
		ikCtrlSepAttr.lock()
		twistAttr = misc.addNumAttr(mainIkCtrl, 'twist', 'double')
		softnessAttr = misc.addNumAttr(mainIkCtrl, 'softness', 'double', min=0, max=1, dv=0)
		autoStretchAttr = misc.addNumAttr(mainIkCtrl, 'autoStretch', 'double', min=0, max=1, dv=0)
		upperStchAttr = misc.addNumAttr(mainIkCtrl, 'upperStretch', 'double')
		lowerStchAttr = misc.addNumAttr(mainIkCtrl, 'lowerStretch', 'double')
		# softIkAttr = misc.addNumAttr(mainIkCtrl, 'softIk', 'double', min=0, max=1, dv=0)

		# --- store ik controllers to list
		self.ikCtrls = [baseIkCtrl, pvIkCtrl, mainIkCtrl]
		self.ikCtrlOfstGrps = [baseIkCtrlOfstGrp, pvIkCtrlOfstGrp, mainIkCtrlOfstGrp]
		self.ikCtrlZgrps = [baseIkCtrlZgrp, pvIkCtrlZgrp, mainIkCtrlZgrp]

		# --- position ik ctrls
		upArmLen = misc.getDistanceFromPosition(self.ikJnts[0].getTranslation('world'), self.ikJnts[1].getTranslation('world'))
		lwrArmLen = misc.getDistanceFromPosition(self.ikJnts[1].getTranslation('world'), self.ikJnts[2].getTranslation('world'))
		armLen = upArmLen + lwrArmLen

		misc.snapTransform('point', self.ikJnts[0], self.ikCtrlZgrps[0], False, True)
		pvPosRet = misc.getPoleVectorPosition(jnts=self.ikJnts[0:3], createLoc=False, ro=False, offset=(1.25*armLen))
		pm.xform(self.ikCtrlZgrps[1], ws=True, t=pvPosRet['translation'])

		misc.snapTransform('point', self.ikJnts[2], self.ikCtrlZgrps[2], False, True)
		misc.snapTransform('orient', self.ikJnts[2], self.ikCtrls[2], False, True)
		pm.makeIdentity(self.ikCtrls[2], apply=True, t=True, r=True, s=True)

		# lock the main ik
		mainIkCtrl.lockAttr(r=False, s=True, v=True)
		mainIkCtrl.hideAttr(r=False, s=True, v=True)

		# throw ik ctrl zgrp to ik ctrl grp
		pm.parent(self.ikCtrlZgrps, self.rigIkCtrlGrp)

		# point ik base to ik base ctrl
		misc.snapTransform('point', self.ikCtrls[0], self.ikJnts[0], True, False)

		# ---- create Ik handle
		ikHndl, ikEff = pm.ikHandle(sj=self.ikJnts[0], ee=self.ikJnts[2], sol='ikRPsolver', n='%sWrist%s_ikHndl' %_name)
		tipIkHndl, tipIkEff = pm.ikHandle(sj=self.ikJnts[2], ee=self.ikJnts[3], sol='ikRPsolver', n='%sHand%s_ikHndl' %_name)

		ikHndlZgrp = misc.zgrp(ikHndl, element='Zro', suffix='grp')[0]
		tipIkHndlZgrp = misc.zgrp(tipIkHndl, element='Zro', suffix='grp')[0]

		self.ikHndls = [ikHndl, tipIkHndl]
		self.ikEffs = [ikEff, tipIkEff]
		self.ikHndlZgrps = [ikHndlZgrp, tipIkHndlZgrp]
		pm.parent(self.ikHndlZgrps, self.rigIkhGrp)

		# --- ik piv groups
		ikPivGrp = pm.group(em=True, n='%sWristIkHndlPiv%s_grp' %_name)
		tipIkPivGrp = pm.group(em=True, n='%sHandIkHndlPiv%s_grp' %_name)
		
		misc.snapTransform('point', self.ikHndls[0], ikPivGrp, False, True)
		misc.snapTransform('point', self.ikHndls[1], tipIkPivGrp, False, True)
		pm.parent([ikPivGrp, tipIkPivGrp], misc.getGimbalCtrl(obj=self.ikCtrls[2]))
		misc.snapTransform('parent', ikPivGrp, self.ikHndlZgrps[0], False, False)
		misc.snapTransform('parent', tipIkPivGrp, self.ikHndlZgrps[1], False, False)

		# toLockHide = {'t':True, 'r':True, 's':True, 'v':True}
		# misc.lockAttr(ikPivGrp, **toLockHide)
		# misc.hideAttr(ikPivGrp, **toLockHide)
		# misc.lockAttr(tipIkPivGrp, **toLockHide)
		# misc.hideAttr(tipIkPivGrp, **toLockHide)

		# --- polevector constriant
		pm.poleVectorConstraint(self.ikCtrls[1], self.ikHndls[0])

		# --- add pv annotation line
		annDict = misc.annPointer(pointFrom=self.ikJnts[1], pointTo=self.ikCtrls[1], 
				ref=True, constraint=True)
		annGrp = pm.group(em=True, n='%sAnnPointer%s_grp' %_name)
		pm.parent([annDict['ann'], annDict['loc']], annGrp)
		pm.parent(annGrp, self.rigIkCtrlGrp)

		# --- ik ctrl and pv ik ctrl local world
		misc.createLocalWorld(objs=[self.ikCtrls[2], self.ikCtrls[0], self.animGrp, self.ikCtrlZgrps[2]], constraintType='parent', attrName='localWorld')
		misc.createLocalWorld(objs=[self.ikCtrls[1], self.ikCtrls[2], self.animGrp, self.ikCtrlZgrps[1]], constraintType='parent', attrName='localWorld')

		# --- connect twist
		if defaultLenAttrs[0].get() > 0.0:
			twistMultValue = 1.0
		else:
			twistMultValue = -1.0
		ikTwstMdl = pm.createNode('multDoubleLinear', n='%sIkTwist%s_mdl' %_name)
		ikTwstMdl.input2.set(twistMultValue)
		pm.connectAttr(self.ikCtrls[2].twist, ikTwstMdl.input1)
		pm.connectAttr(ikTwstMdl.output, self.ikHndls[0].twist)

		# --- create position groups
		baseIkPosGrp = pm.group(em=True, n='%sIkBasePos%s_grp' %_name)
		misc.snapTransform('point', self.ikCtrls[0], baseIkPosGrp, False, False)
		pvIkPosGrp = pm.group(em=True, n='%sIkPvPos%s_grp' %_name)
		misc.snapTransform('point', self.ikCtrls[1], pvIkPosGrp, False, False)
		ikPosGrp = pm.group(em=True, n='%sIkPos%s_grp' %_name)
		misc.snapTransform('point', self.ikHndlZgrps[0], ikPosGrp, False, False)
		pm.parent([baseIkPosGrp, pvIkPosGrp, ikPosGrp], self.rigIkCtrlGrp)

		# --- connect manual stretch
		stchMdv = pm.createNode('multiplyDivide', n='%sIkStretch%s_mdv' %_name)
		pm.connectAttr(self.ikCtrls[2].upperStretch, stchMdv.input1X)
		pm.connectAttr(self.ikCtrls[2].lowerStretch, stchMdv.input1Y)
		pm.connectAttr(settingCtrlShp.defaultLenUpr, stchMdv.input2X)
		pm.connectAttr(settingCtrlShp.defaultLenLwr, stchMdv.input2Y)

		# --- connect  auto stertch
		# --- combine auto stretch and manual stretch together
		ikStchPma = pm.createNode('plusMinusAverage', n='%sIkStretch%s_pma' %_name)
		pm.connectAttr(stchMdv.outputX, ikStchPma.input2D[0].input2Dx)
		pm.connectAttr(stchMdv.outputY, ikStchPma.input2D[0].input2Dy)
		pm.connectAttr(settingCtrlShp.defaultLenUpr, ikStchPma.input2D[1].input2Dx)
		pm.connectAttr(settingCtrlShp.defaultLenLwr, ikStchPma.input2D[1].input2Dy)
	

		# make value absoulute
		ikAbsPowMdv = pm.createNode('multiplyDivide', n='%sIkAbsPow%s_mdv' %_name)
		ikAbsPowMdv.operation.set(3)
		ikAbsPowMdv.input2X.set(2)
		ikAbsPowMdv.input2Y.set(2)
		pm.connectAttr(ikStchPma.output2D.output2Dx, ikAbsPowMdv.input1X)
		pm.connectAttr(ikStchPma.output2D.output2Dy, ikAbsPowMdv.input1Y)

		ikAbsSqrtMdv = pm.createNode('multiplyDivide', n='%sIkAbsSqrt%s_mdv' %_name)
		ikAbsSqrtMdv.operation.set(3)
		ikAbsSqrtMdv.input2X.set(0.5)
		ikAbsSqrtMdv.input2Y.set(0.5)
		pm.connectAttr(ikAbsPowMdv.outputX, ikAbsSqrtMdv.input1X)
		pm.connectAttr(ikAbsPowMdv.outputY, ikAbsSqrtMdv.input1Y)

		pm.connectAttr(ikAbsSqrtMdv.outputX, settingCtrlShp.stretchLenUpr)
		pm.connectAttr(ikAbsSqrtMdv.outputY, settingCtrlShp.stretchLenLwr)

		ikDist = pm.createNode('distanceBetween', n='%sIkAutoStretchIk%s_dist' %_name)
		pm.connectAttr(baseIkPosGrp.translate, ikDist.point1)
		pm.connectAttr(ikPosGrp.translate, ikDist.point2)

		autoStchDivOrigMdv = pm.createNode('multiplyDivide', n='%sIkAutoStretchDivOrig%s_mdv' %_name)
		autoStchDivOrigMdv.operation.set(2)
		pm.connectAttr(ikDist.distance, autoStchDivOrigMdv.input1X)
		# pm.connectAttr(settingCtrlShp.stretchLen, autoStchDivOrigMdv.input2X)

		autoStchCond = pm.createNode('condition', n='%sIkAutoStretch%s_cond' %_name)
		autoStchCond.operation.set(2)
		autoStchCond.colorIfFalseR.set(1.0)
		pm.connectAttr(ikDist.distance, autoStchCond.firstTerm)
		# pm.connectAttr(settingCtrlShp.stretchLen, autoStchCond.secondTerm)
		pm.connectAttr(autoStchDivOrigMdv.outputX, autoStchCond.colorIfTrueR)

		autoStchBta = pm.createNode('blendTwoAttr', n='%sIkAutoStretch%s_bta' %_name)
		# autoStchBta.input[0].set(1.0)
		pm.connectAttr(self.ikCtrls[2].autoStretch, autoStchBta.attributesBlender)
		pm.connectAttr(autoStchCond.outColorR, autoStchBta.input[1])

		autoStchMultLenMdv = pm.createNode('multiplyDivide', n='%sIkAutoStretchMultLen%s_mdv' %_name)
		pm.connectAttr(autoStchBta.output, autoStchMultLenMdv.input1X)
		pm.connectAttr(autoStchBta.output, autoStchMultLenMdv.input1Y)
		pm.connectAttr(ikStchPma.output2D.output2Dx, autoStchMultLenMdv.input2X)
		pm.connectAttr(ikStchPma.output2D.output2Dy, autoStchMultLenMdv.input2Y)

		# --- connect softness
		ikSoftInvMdl = pm.createNode('multDoubleLinear', n='%sIkSoftInv%s_mdl' %_name)
		ikSoftInvMdl.input2.set(-1)
		pm.connectAttr(softnessAttr, ikSoftInvMdl.input1)

		ikSoftZeroCond = pm.createNode('condition', n='%sIkSoftZero%s_cond' %_name)
		ikSoftZeroCond.secondTerm.set(0)
		ikSoftZeroCond.operation.set(2)
		ikSoftZeroCond.colorIfFalseG.set(1)
		pm.connectAttr(softnessAttr, ikSoftZeroCond.firstTerm)
		pm.connectAttr(settingCtrlShp.stretchLen, ikSoftZeroCond.colorIfTrueR)
		pm.connectAttr(ikDist.distance, ikSoftZeroCond.colorIfFalseR)
		pm.connectAttr(softnessAttr, ikSoftZeroCond.colorIfTrueG)

		ikSoftSumLenPma = pm.createNode('plusMinusAverage', n='%sIkSoftSumLen%s_pma' %_name)
		ikSoftSumLenPma.input2D[1].input2Dy.set(1)
		pm.connectAttr(ikSoftInvMdl.output, ikSoftSumLenPma.input2D[0].input2Dx)
		pm.connectAttr(ikSoftZeroCond.outColorR, ikSoftSumLenPma.input2D[1].input2Dx)
		pm.connectAttr(softnessAttr, ikSoftSumLenPma.input2D[0].input2Dy)

		ikSoftSubDistPma = pm.createNode('plusMinusAverage', n='%sIkSoftSubDist%s_pma' %_name)
		ikSoftSubDistPma.operation.set(2)
		pm.connectAttr(ikSoftSumLenPma.output2D.output2Dx, ikSoftSubDistPma.input1D[0])
		pm.connectAttr(ikDist.distance, ikSoftSubDistPma.input1D[1])

		ikSoftDivMdv = pm.createNode('multiplyDivide', n='%sIkSoftDiv%s_mdv' %_name)
		ikSoftDivMdv.operation.set(2)
		pm.connectAttr(ikSoftSubDistPma.output1D, ikSoftDivMdv.input1X)
		pm.connectAttr(ikSoftZeroCond.outColorG, ikSoftDivMdv.input2X)

		ikSoftPowEMdv = pm.createNode('multiplyDivide', n='%sIkSoftPowE%s_mdv' %_name)
		ikSoftPowEMdv.operation.set(3)
		ikSoftPowEMdv.input1X.set(e_cons)
		pm.connectAttr(ikSoftDivMdv.outputX, ikSoftPowEMdv.input2X)

		ikSoftMultMdl = pm.createNode('multDoubleLinear', n='%sIkSoftMult%s_mdl' %_name)
		pm.connectAttr(ikSoftPowEMdv.outputX, ikSoftMultMdl.input1)
		pm.connectAttr(softnessAttr, ikSoftMultMdl.input2)

		ikSoftNegCond = pm.createNode('condition', n='%sIkSoftNeg%s_cond' %_name)
		ikSoftNegCond.secondTerm.set(0)
		ikSoftNegCond.operation.set(4)
		ikSoftNegCond.colorIfFalseR.set(0)
		pm.connectAttr(ikSoftDivMdv.outputX, ikSoftNegCond.firstTerm)
		pm.connectAttr(ikSoftMultMdl.output, ikSoftNegCond.colorIfTrueR)

		ikSoftSubLenPma = pm.createNode('plusMinusAverage', n='%sIkSoftSubLen%s_pma' %_name)
		ikSoftSubLenPma.operation.set(2)
		pm.connectAttr(settingCtrlShp.stretchLen, ikSoftSubLenPma.input1D[0])
		pm.connectAttr(ikSoftNegCond.outColorR, ikSoftSubLenPma.input1D[1])
		pm.connectAttr(ikSoftSubLenPma.output1D, autoStchCond.secondTerm)
		pm.connectAttr(ikSoftSubLenPma.output1D, autoStchDivOrigMdv.input2X)

		ikSoftLimCmp = pm.createNode('clamp', n='%sIkSoftLim%s_cmp' %_name)
		ikSoftLimCmp.minR.set(0)
		pm.connectAttr(autoStchCond.outColorR, ikSoftLimCmp.inputR)
		pm.connectAttr(ikSoftSumLenPma.output2D.output2Dy, ikSoftLimCmp.maxR)
		pm.connectAttr(ikSoftLimCmp.outputR, autoStchBta.input[0])

		# --- connect ik lock
		ikUprLockDist = pm.createNode('distanceBetween', n='%sIkUprLock%s_dist' %_name)
		pm.connectAttr(baseIkPosGrp.translate, ikUprLockDist.point1)
		pm.connectAttr(pvIkPosGrp.translate, ikUprLockDist.point2)

		ikLwrLockDist = pm.createNode('distanceBetween', n='%sIkLwrLock%s_dist' %_name)
		pm.connectAttr(pvIkPosGrp.translate, ikLwrLockDist.point1)
		pm.connectAttr(ikPosGrp.translate, ikLwrLockDist.point2)

		ikLockRevMdv = pm.createNode('multiplyDivide', n='%sIkLockRev%s_mdv' %_name)
		ikLockRevMdv.input2X.set(twistMultValue)
		ikLockRevMdv.input2Y.set(twistMultValue)
		pm.connectAttr(settingCtrlShp.defaultLenUpr, ikLockRevMdv.input1X)
		pm.connectAttr(settingCtrlShp.defaultLenLwr, ikLockRevMdv.input1Y)

		ikLockDivLenMdv = pm.createNode('multiplyDivide', n='%sIkLockDivLen%s_mdv' %_name)
		ikLockDivLenMdv.operation.set(2)
		pm.connectAttr(ikUprLockDist.distance, ikLockDivLenMdv.input1X)
		pm.connectAttr(ikLwrLockDist.distance, ikLockDivLenMdv.input1Y)
		pm.connectAttr(ikLockRevMdv.outputX, ikLockDivLenMdv.input2X)
		pm.connectAttr(ikLockRevMdv.outputY, ikLockDivLenMdv.input2Y)

		ikLockMultLenMdv = pm.createNode('multiplyDivide', n='%sIkLockMultLen%s_mdv' %_name)
		pm.connectAttr(ikLockDivLenMdv.outputX, ikLockMultLenMdv.input1X)
		pm.connectAttr(ikLockDivLenMdv.outputY, ikLockMultLenMdv.input1Y)
		pm.connectAttr(settingCtrlShp.defaultLenUpr, ikLockMultLenMdv.input2X)
		pm.connectAttr(settingCtrlShp.defaultLenLwr, ikLockMultLenMdv.input2Y)

		# connect blend colors for lock
		ikLockBcol = pm.createNode('blendColors', n='%sIkLock%s_bco' %_name)
		pm.connectAttr(self.ikCtrls[1].pin, ikLockBcol.blender)
		pm.connectAttr(ikLockMultLenMdv.outputX, ikLockBcol.color1R)
		pm.connectAttr(ikLockMultLenMdv.outputY, ikLockBcol.color1G)
		pm.connectAttr(autoStchMultLenMdv.outputX, ikLockBcol.color2R)
		pm.connectAttr(autoStchMultLenMdv.outputY, ikLockBcol.color2G)

		# --- connect to ik joint
		pm.connectAttr(ikLockBcol.outputR, self.ikJnts[1].attr(aimTran))
		pm.connectAttr(ikLockBcol.outputG, self.ikJnts[2].attr(aimTran))