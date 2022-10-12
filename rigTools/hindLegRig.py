import pymel.core as pm
import maya.mel as mel

from nuTools import misc, controller
reload(misc)
reload(controller)
import nuTools.rigTools.baseRig as baseRig
reload(baseRig)

class HindLegRig(baseRig.BaseRig):
	def __init__(self, 
				jnts=[],
				aimAxis='y',
				upAxis='z',
				fkRotateOrder='yzx',
				ikRotateOrder='xzy',
				createFootRig=True,
				**kwargs):
		super(HindLegRig, self).__init__(**kwargs)
		# temp joints
		self.tmpJnts = self.jntsArgs(jnts)

		# axis
		self.aimAxis = aimAxis
		self.upAxis = upAxis
		self.fkRotateOrder = fkRotateOrder
		self.ikRotateOrder = ikRotateOrder
		self.createFootRig = createFootRig

		# joints
		self.jnts = []
		self.fkJnts = []
		self.ikJnts = []
		self.ikHindJnts = []

		# controllers
		self.settingCtrl = []
		self.fkCtrls = []
		self.fkGCtrls = []
		self.ikCtrls = []
		self.ikGCtrls = []

		# groups
		self.fkCtrlZgrps = []
		self.fkCtrlOfstGrps = []
		self.ikCtrlZgrps = []
		self.ikCtrlOfstGrps = []

		# Iks
		self.ikHndls = []
		self.ikEffs = []
		self.ikHndlZgrps = []

	def rig(self):
		# --- translate axis from string to vector
		# aimAxis = misc.vectorStr(self.aimAxis)
		aimTran = 't%s' %(self.aimAxis[-1])
		aimRot = 'r%s' %self.aimAxis
		upRot =  'r%s' %self.upAxis

		# upAxis = misc.vectorStr(self.upAxis)
		self.bendAxis = misc.crossAxis(self.aimAxis, self.upAxis)[-1]
		bendRot = 'r%s' %self.bendAxis

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
		fkikAttr = misc.addNumAttr(self.settingCtrl, 'fkIk', 'double', hide=False, min=0, max=1, dv=1.0)
		
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
		pos = ['Upr', 'Knee', 'Hock', 'Ankle', 'Ball', 'Toe']
		jlst = ['self.jnts', 'self.fkJnts', 'self.ikJnts']
		glst = [ 'self.rigUtilGrp', 'self.rigFkCtrlGrp', 'self.rigIkCtrlGrp']
		rad = self.tmpJnts[0].radius.get()
		m = 1.0  # radius multiplier
		for e in xrange(3):
			# duplicate joint from tmpJnt
			upJnt = pm.duplicate(self.tmpJnts[0], po=True, n='%s%s%s%s_jnt' %(self.elem, pos[0], jntElems[e], self.side))[0]
			kneeJnt = pm.duplicate(self.tmpJnts[1], po=True, n='%s%s%s%s_jnt' %(self.elem, pos[1], jntElems[e], self.side))[0]
			hockJnt = pm.duplicate(self.tmpJnts[2], po=True, n='%s%s%s%s_jnt' %(self.elem, pos[2], jntElems[e], self.side))[0]
			ankleJnt = pm.duplicate(self.tmpJnts[3], po=True, n='%s%s%s%s_jnt' %(self.elem, pos[3], jntElems[e], self.side))[0]
			ballJnt = pm.duplicate(self.tmpJnts[4], po=True, n='%s%s%s%s_jnt' %(self.elem, pos[4], jntElems[e], self.side))[0]
			toeJnt = pm.duplicate(self.tmpJnts[5], po=True, n='%s%s%s%s_jnt' %(self.elem, pos[5], jntElems[e], self.side))[0]

			# parent into fk chain
			pm.parent(toeJnt, ballJnt)
			pm.parent(ballJnt, ankleJnt)
			pm.parent(ankleJnt, hockJnt)
			pm.parent(hockJnt, kneeJnt)
			pm.parent(kneeJnt, upJnt)
			
			# set radius
			for j in [upJnt, kneeJnt, hockJnt, ankleJnt, ballJnt, toeJnt]:
				j.radius.set(rad*m)

			# freeze it
			pm.makeIdentity(upJnt, apply=True)

			# store to list
			exec('%s = [upJnt, kneeJnt, hockJnt, ankleJnt, ballJnt, toeJnt]' %jlst[e])
			# exec('pm.parent(upJnt, %s)' %glst[e])
			if e > 0:
				# hide ik/fk jnts
				upJnt.visibility.set(False)

			# connect scale
			pm.connectAttr(self.settingCtrl.size, ankleJnt.scaleX)
			pm.connectAttr(self.settingCtrl.size, ankleJnt.scaleY)
			pm.connectAttr(self.settingCtrl.size, ankleJnt.scaleZ)

			pm.parent(upJnt, self.rigUtilGrp)
			

			m *= 0.5

		# add zro joint to ik and fk chain
		# zroFkJnts = misc.addOffsetJnt(sels=self.fkJnts, element='Zro')
		# zroIkJnts = misc.addOffsetJnt(sels=self.ikJnts, element='Zro')

		# --- parent and scale constraint main joint to both ik and fk joint
		for j in xrange(6):
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
		misc.snapTransform('parent', self.jnts[3], settingCtrlZgrp, False, False)

		# ------ FK rig
		for i in xrange(5):
			# FK controller shape
			if i == 4:
				fkCtrlShp = 'halfCrossCircle'
			else:
				fkCtrlShp = 'crossCircle'

			fkCtrl = controller.JointController(name='%s%sFk%s_ctrl' %(self.elem, pos[i], self.side),
										st=fkCtrlShp, scale=self.size)
			fkCtrl.rotateOrder.set(self.fkRotateOrder)
			fkCtrl.setColor('red')
			fkCtrl.lockAttr(t=False, s=True, v=True)
			fkCtrl.hideAttr(t=False, s=True, v=True)

			fkGCtrl = fkCtrl.addGimbal()

			fkCtrlOfst = misc.zgrp(fkCtrl, element='Ofst', suffix='grp')[0]
			fkCtrlZgrp = misc.zgrp(fkCtrlOfst, element='Zro', suffix='grp')[0]

			self.fkGCtrls.append(fkGCtrl)
			self.fkCtrls.append(fkCtrl)
			self.fkCtrlOfstGrps.append(fkCtrlOfst)
			self.fkCtrlZgrps.append(fkCtrlZgrp)

			parent = self.rigFkCtrlGrp
			if i > 0:
				parent = self.fkGCtrls[i-1]

			pm.parent(fkCtrlZgrp, parent)

			misc.snapTransform('parent', self.fkJnts[i], fkCtrlZgrp, False, True)
			misc.snapTransform('parent', fkGCtrl, self.fkJnts[i], False, False)

		# foot scale
		fkFootScaleGrp = pm.group(em=True, n='%sFootFkScale%s_grp' %_name)
		misc.snapTransform('parent', self.fkJnts[3], fkFootScaleGrp, False, True)
		pm.parent(fkFootScaleGrp, self.fkGCtrls[3])
		pm.parent(self.fkCtrlZgrps[4], fkFootScaleGrp)
		pm.connectAttr(self.settingCtrl.size, fkFootScaleGrp.scaleX)
		pm.connectAttr(self.settingCtrl.size, fkFootScaleGrp.scaleY)
		pm.connectAttr(self.settingCtrl.size, fkFootScaleGrp.scaleZ)

		# --- connect Fk stretch
		ctrlPos = ['Upr', 'Mid', 'Lwr']
		defaultLenAttrs, defaultDistAttrs = [], []
		for i in xrange(3):
			# add default len attr
			defaultLenValue = self.fkJnts[i+1].attr(aimTran).get()
			defLenAttr = misc.addNumAttr(settingCtrlShp, 'defaultLen%s' %(ctrlPos[i]), 'double', key=False, hide=True, dv=defaultLenValue)

			defaultDistValue = misc.getDistanceFromPosition(self.fkJnts[i].getTranslation('world'), self.fkJnts[i+1].getTranslation('world'))
			# print defaultDistValue
			defDistAttr = misc.addNumAttr(settingCtrlShp, 'defaultDist%s' %(ctrlPos[i]), 'double', key=False, hide=True, dv=defaultDistValue)

			# stretchAmpMdl = pm.createNode('multDoubleLinear', n='%s%sFkStretchAmp%s_mdl' %(self.elem, pos[i], self.side))
			stretchMdl = pm.createNode('multDoubleLinear', n='%s%sFkStretch%s_mdl' %(self.elem, ctrlPos[i], self.side))
			stretchAdl = pm.createNode('addDoubleLinear', n='%s%sFkStretch%s_adl' %(self.elem, ctrlPos[i], self.side))
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

			# defDistAttr.setKeyable(False)
			# defDistAttr.showInChannelBox(False)
			# defDistAttr.setLocked(True)
			defaultDistAttrs.append(defDistAttr)

		# --- local world for upLeg
		# misc.addNumAttr(self.fkCtrls[i], 'localWorld', 'double', dv=1.0)
		misc.createLocalWorld(objs=[self.fkCtrls[0], self.rigFkCtrlGrp, self.animGrp, self.fkCtrlZgrps[0]], 
			constraintType='orient', attrName='localWorld')

		# --- create default len attrs on setting ctrl shape
		defLimbLenAttr = misc.addNumAttr(settingCtrlShp, 'defaultLen', 'double', key=False, hide=True, dv=defaultLenValue)
		defLenPma = pm.createNode('plusMinusAverage', n='%sDefaultLen%s_pma' %_name)
		pm.connectAttr(defaultLenAttrs[0], defLenPma.input1D[0])
		pm.connectAttr(defaultLenAttrs[1], defLenPma.input1D[1])
		pm.connectAttr(defaultLenAttrs[2], defLenPma.input1D[2])
		pm.connectAttr(defLenPma.output1D, defLimbLenAttr)

		defLimbLenAttr.setKeyable(False)
		defLimbLenAttr.showInChannelBox(False)
		defLimbLenAttr.setLocked(True)

		# --- create default dist attrs on setting ctrl shape
		# abs values
		defDistAbsPowMdv = pm.createNode('multiplyDivide', n='%sDefaultDistAbsPow%s_mdv' %_name)
		defDistAbsPowMdv.operation.set(3)
		pm.connectAttr(defaultLenAttrs[0], defDistAbsPowMdv.input1X)
		pm.connectAttr(defaultLenAttrs[1], defDistAbsPowMdv.input1Y)
		pm.connectAttr(defaultLenAttrs[2], defDistAbsPowMdv.input1Z)
		defDistAbsPowMdv.input2.set([2, 2, 2])

		defDistAbsSqrtMdv = pm.createNode('multiplyDivide', n='%sDefaultDistAbsSqrt%s_mdv' %_name)
		defDistAbsSqrtMdv.operation.set(3)
		pm.connectAttr(defDistAbsPowMdv.outputX, defDistAbsSqrtMdv.input1X)
		pm.connectAttr(defDistAbsPowMdv.outputY, defDistAbsSqrtMdv.input1Y)
		pm.connectAttr(defDistAbsPowMdv.outputZ, defDistAbsSqrtMdv.input1Z)
		defDistAbsSqrtMdv.input2.set([0.5, 0.5, 0.5])

		defDistStchMdv = pm.createNode('multiplyDivide', n='%sDefaultDistStrech%s_mdv' %_name)
		pm.connectAttr(defDistAbsSqrtMdv.outputX, defDistStchMdv.input1X)
		pm.connectAttr(defDistAbsSqrtMdv.outputY, defDistStchMdv.input1Y)
		pm.connectAttr(defDistAbsSqrtMdv.outputZ, defDistStchMdv.input1Z)
		
		defDistStchPma = pm.createNode('plusMinusAverage', n='%sDefaultDistStrech%s_pma' %_name)
		pm.connectAttr(defDistAbsSqrtMdv.outputX, defDistStchPma.input3D[0].input3Dx)
		pm.connectAttr(defDistAbsSqrtMdv.outputY, defDistStchPma.input3D[0].input3Dy)
		pm.connectAttr(defDistAbsSqrtMdv.outputZ, defDistStchPma.input3D[0].input3Dz)

		pm.connectAttr(defDistStchMdv.outputX, defDistStchPma.input3D[1].input3Dx)
		pm.connectAttr(defDistStchMdv.outputY, defDistStchPma.input3D[1].input3Dy)
		pm.connectAttr(defDistStchMdv.outputZ, defDistStchPma.input3D[1].input3Dz)

		pm.connectAttr(defDistStchPma.output3Dx, defaultDistAttrs[0])
		pm.connectAttr(defDistStchPma.output3Dy, defaultDistAttrs[1])
		pm.connectAttr(defDistStchPma.output3Dz, defaultDistAttrs[2])

		defLimbDistAttr = misc.addNumAttr(settingCtrlShp, 'defaultDist', 'double', key=False, hide=True, dv=defaultLenValue)
		defDistPma = pm.createNode('plusMinusAverage', n='%sDefaultDist%s_pma' %_name)
		pm.connectAttr(defDistStchPma.output3Dx, defDistPma.input1D[0])
		pm.connectAttr(defDistStchPma.output3Dy, defDistPma.input1D[1])
		pm.connectAttr(defDistStchPma.output3Dz, defDistPma.input1D[2])
		pm.connectAttr(defDistPma.output1D, defLimbDistAttr)

		defLimbDistAttr.setKeyable(False)
		defLimbDistAttr.showInChannelBox(False)
		defLimbDistAttr.setLocked(True)

		# ------ IK rig
		# --- legRoot ik ctrl
		baseIkCtrl = controller.JointController(name='%sIkBase%s_ctrl' %(_name),
										st='locator', scale=self.size)
		baseIkCtrl.setColor('blue')
		baseIkCtrl.lockAttr(r=True, s=True, v=True)
		baseIkCtrl.hideAttr(r=True, s=True, v=True)
		baseIkCtrlOfstGrp = misc.zgrp(baseIkCtrl, element='Ofst', suffix='grp')[0]	
		baseIkCtrlZgrp = misc.zgrp(baseIkCtrlOfstGrp, element='Zro', suffix='grp')[0]	

		# --- leg pv ctrl
		pvIkCtrl = controller.JointController(name='%sIkPv%s_ctrl' %(_name),
										st='3dDiamond', scale=self.size*0.334)
		pvIkCtrl.setColor('blue')
		pvIkCtrl.lockAttr(r=True, s=True, v=True)
		pvIkCtrl.hideAttr(r=True, s=True, v=True)
		pvIkCtrlOfstGrp = misc.zgrp(pvIkCtrl, element='Ofst', suffix='grp')[0]
		pvIkCtrlZgrp = misc.zgrp(pvIkCtrlOfstGrp, element='Zro', suffix='grp')[0]
		pvIkCtrlLocWorAttr = misc.addNumAttr(pvIkCtrl, 'localWorld', 'double', min=0, max=1, dv=0)
		# pinAttr = misc.addNumAttr(pvIkCtrl, 'pin', 'double', min=0, max=1, dv=0)

		# --- legIK ctrl
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
		autoStretchAttr = misc.addNumAttr(mainIkCtrl, 'autoStretch', 'double', min=0, max=1, dv=0)
		upperStchAttr = misc.addNumAttr(mainIkCtrl, 'upperStretch', 'double')
		midStchAttr = misc.addNumAttr(mainIkCtrl, 'midStretch', 'double')
		lowerStchAttr = misc.addNumAttr(mainIkCtrl, 'lowerStretch', 'double')
		# softIkAttr = misc.addNumAttr(mainIkCtrl, 'softIk', 'double', min=0, max=1, dv=0)

		ikCtrlHindSepAttr = misc.addNumAttr(mainIkCtrl, '__hind__', 'double', hide=False, min=0, max=1, dv=0)
		ikCtrlHindSepAttr.lock()
		# misc.addNumAttr(mainIkCtrl, 'autoFlex', 'double', min=0, max=1, dv=0)
		misc.addNumAttr(mainIkCtrl, 'hindFlex', 'double')
		misc.addNumAttr(mainIkCtrl, 'hindBend', 'double')

		# --- store ik controllers to list
		self.ikCtrls = [baseIkCtrl, pvIkCtrl, mainIkCtrl]
		self.ikCtrlOfstGrps = [baseIkCtrlOfstGrp, pvIkCtrlOfstGrp, mainIkCtrlOfstGrp]
		self.ikCtrlZgrps = [baseIkCtrlZgrp, pvIkCtrlZgrp, mainIkCtrlZgrp]

		# --- position ik ctrls
		upLegLen = misc.getDistanceFromPosition(self.ikJnts[0].getTranslation('world'), self.ikJnts[1].getTranslation('world'))
		lwrLegLen = misc.getDistanceFromPosition(self.ikJnts[1].getTranslation('world'), self.ikJnts[2].getTranslation('world'))
		legLen = upLegLen + lwrLegLen

		misc.snapTransform('point', self.ikJnts[0], self.ikCtrlZgrps[0], False, True)
		pvPosRet = misc.getPoleVectorPosition(jnts=self.ikJnts[0:3], createLoc=False, ro=False, offset=(1.25*legLen))
		pm.xform(self.ikCtrlZgrps[1], ws=True, t=pvPosRet['translation'])

		misc.snapTransform('point', self.ikJnts[3], self.ikCtrlZgrps[2], False, True)
		misc.snapTransform('orient', self.ikJnts[3], self.ikCtrls[2], False, True)
		pm.makeIdentity(self.ikCtrls[2], apply=True, t=True, r=True, s=True)

		mainIkCtrl.lockAttr(r=False, s=True, v=True)
		mainIkCtrl.hideAttr(r=False, s=True, v=True)

		# throw ik ctrl zgrp to ik ctrl grp
		pm.parent(self.ikCtrlZgrps, self.rigIkCtrlGrp)

		# point ik base to ik base ctrl
		misc.snapTransform('point', self.ikCtrls[0], self.ikJnts[0], True, False)

		# --- create hind Ik handle
		for i in xrange(4):
			# duplicate joint from tmpJnt
			hJnt = pm.duplicate(self.ikJnts[i], po=True, n='%sHind%s%s_jnt' %(self.elem, pos[i], self.side))[0]

			if i > 0:
				parentTo = self.ikHindJnts[i-1]
			else:
				parentTo = self.rigUtilGrp

			pm.parent(hJnt, parentTo)

			self.ikHindJnts.append(hJnt)

		# mel.eval('ikSpringSolver;')
		hIkHndl, hIkEff = pm.ikHandle(sj=self.ikHindJnts[0], ee=self.ikHindJnts[3], sol='ikRPsolver', n='%sHind%s_ikHndl' %_name)
		# hIkHndl.splineIkOldStyle.set(True)
		hIkHndlZgrp = misc.zgrp(hIkHndl, element='Zro', suffix='grp')[0]
		pm.parent(hIkHndlZgrp, self.rigIkhGrp)

		# ---- create Ik handle
		upIkHndl, upIkEff = pm.ikHandle(sj=self.ikJnts[0], ee=self.ikJnts[2], sol='ikRPsolver', n='%sHock%s_ikHndl' %_name)
		midIkHndl, midIkEff = pm.ikHandle(sj=self.ikJnts[2], ee=self.ikJnts[3], sol='ikRPsolver', n='%sAnkle%s_ikHndl' %_name)
		lowIkHndl, lowIkEff = pm.ikHandle(sj=self.ikJnts[3], ee=self.ikJnts[4], sol='ikRPsolver', n='%sBall%s_ikHndl' %_name)
		tipIkHndl, tipIkEff = pm.ikHandle(sj=self.ikJnts[4], ee=self.ikJnts[5], sol='ikRPsolver', n='%sToe%s_ikHndl' %_name)

		ikHndlZgrp = misc.zgrp(upIkHndl, element='Zro', suffix='grp')[0]
		midIkHndlZgrp = misc.zgrp(midIkHndl, element='Zro', suffix='grp')[0]
		lowIkHndlZgrp = misc.zgrp(lowIkHndl, element='Zro', suffix='grp')[0]
		tipIkHndlZgrp = misc.zgrp(tipIkHndl, element='Zro', suffix='grp')[0]

		self.ikHndls = [upIkHndl, midIkHndl, lowIkHndl, tipIkHndl]
		self.ikEffs = [upIkEff, midIkEff, lowIkEff, tipIkEff]
		self.ikHndlZgrps = [ikHndlZgrp, midIkHndlZgrp, lowIkHndlZgrp, tipIkHndlZgrp]
		pm.parent(self.ikHndlZgrps, self.rigIkhGrp)

		misc.snapTransform('point', self.ikCtrls[0], self.ikHindJnts[0], True, False)

		# --- ik piv groups
		self.lowHindIkPosGrp = pm.group(em=True, n='%sHockHindIkHndlPiv%s_grp' %_name)
		misc.snapTransform('point', self.ikHndls[0], self.lowHindIkPosGrp, False, True)

		self.ankleHindIkPosGrp = pm.group(em=True, n='%sAnkleHindIkHndlPiv%s_grp' %_name)
		misc.snapTransform('point', self.ikHndls[1], self.ankleHindIkPosGrp, False, True)

		self.flexIkPosGrp = pm.group(em=True, n='%sFlexIkHndlPiv%s_grp' %_name)
		flexIkPosGrpZGrp = misc.zgrp(self.flexIkPosGrp, element='Zro', suffix='grp')[0]
		misc.snapTransform('parent', self.ikHindJnts[3], flexIkPosGrpZGrp, False, True)

		pm.parent(self.lowHindIkPosGrp, self.flexIkPosGrp)
		pm.parent(flexIkPosGrpZGrp, self.ikHindJnts[2])
		pm.parent(self.ankleHindIkPosGrp, self.ikHindJnts[3])

		self.ankleIkPivGrp = pm.group(em=True, n='%sAnkleIkHndlPiv%s_grp' %_name)
		self.lowIkPivGrp = pm.group(em=True, n='%sBallIkHndlPiv%s_grp' %_name)
		self.tipIkPivGrp = pm.group(em=True, n='%sToeIkHndlPiv%s_grp' %_name)
		
		misc.snapTransform('point', self.ikHndls[1], self.ankleIkPivGrp, False, True)
		misc.snapTransform('point', self.ikHndls[2], self.lowIkPivGrp, False, True)
		misc.snapTransform('point', self.ikHndls[3], self.tipIkPivGrp, False, True)

		ikFootScaleGrp = pm.group(em=True, n='%sFootIkScale%s_grp' %_name)
		misc.snapTransform('parent', self.ikJnts[3], ikFootScaleGrp, False, True)
		pm.connectAttr(self.settingCtrl.size, ikFootScaleGrp.scaleX)
		pm.connectAttr(self.settingCtrl.size, ikFootScaleGrp.scaleY)
		pm.connectAttr(self.settingCtrl.size, ikFootScaleGrp.scaleZ)

		pm.parent([self.lowIkPivGrp, self.tipIkPivGrp], ikFootScaleGrp)
		pm.parent(self.ankleIkPivGrp, mainIkGCtrl)
		pm.parent(ikFootScaleGrp, mainIkGCtrl)

		misc.snapTransform('parent', self.lowHindIkPosGrp, self.ikHndlZgrps[0], False, False)
		misc.snapTransform('parent', self.ankleHindIkPosGrp, self.ikHndlZgrps[1], False, False)
		misc.snapTransform('parent', self.lowIkPivGrp, self.ikHndlZgrps[2], False, False)
		misc.snapTransform('parent', self.tipIkPivGrp, self.ikHndlZgrps[3], False, False)

		misc.snapTransform('parent', self.ankleIkPivGrp, hIkHndlZgrp, False, False)

		# toLockHide = {'t':True, 'r':True, 's':True, 'v':True}
		# misc.lockAttr(self.ikPosGrp, **toLockHide)
		# misc.hideAttr(self.ikPosGrp, **toLockHide)
		# misc.lockAttr(self.tipIkPivGrp, **toLockHide)
		# misc.hideAttr(self.tipIkPivGrp, **toLockHide)

		# --- polevector constriant
		pm.poleVectorConstraint(self.ikCtrls[1], self.ikHndls[0])
		pm.poleVectorConstraint(self.ikCtrls[1], hIkHndl)

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
		pm.connectAttr(ikTwstMdl.output, hIkHndl.twist)

		# --- hind leg rig
		# pm.connectAttr(mainIkCtrl.hindFlex, self.flexIkPosGrp.attr(bendRot))
		pm.connectAttr(mainIkCtrl.hindBend, self.flexIkPosGrp.attr(upRot))

		###################
		# auto hind flex

		# --- create position groups
		baseIkPosGrp = pm.group(em=True, n='%sIkBasePos%s_grp' %_name)
		misc.snapTransform('point', self.ikCtrls[0], baseIkPosGrp, False, False)

		pvIkPosGrp = pm.group(em=True, n='%sIkPvPos%s_grp' %_name)
		misc.snapTransform('point', self.ikCtrls[1], pvIkPosGrp, False, False)

		ikPosGrp = pm.group(em=True, n='%sIkPos%s_grp' %_name)
		misc.snapTransform('point', mainIkGCtrl, ikPosGrp, False, False)
		pm.parent([baseIkPosGrp, pvIkPosGrp, ikPosGrp], self.rigIkCtrlGrp)

		# --- connect  auto stertch
		ikDist = pm.createNode('distanceBetween', n='%sIkAutoStretchIk%s_dist' %_name)
		pm.connectAttr(baseIkPosGrp.translate, ikDist.point1)
		pm.connectAttr(ikPosGrp.translate, ikDist.point2)

		autoStchDivOrigMdv = pm.createNode('multiplyDivide', n='%sIkAutoStretchDivOrig%s_mdv' %_name)
		autoStchDivOrigMdv.operation.set(2)
		pm.connectAttr(ikDist.distance, autoStchDivOrigMdv.input1X)
		pm.connectAttr(settingCtrlShp.defaultDist, autoStchDivOrigMdv.input2X)

		autoStchCond = pm.createNode('condition', n='%sIkAutoStretch%s_cond' %_name)
		autoStchCond.operation.set(2)
		autoStchCond.colorIfFalseR.set(1.0)
		pm.connectAttr(ikDist.distance, autoStchCond.firstTerm)
		pm.connectAttr(settingCtrlShp.defaultDist, autoStchCond.secondTerm)
		pm.connectAttr(autoStchDivOrigMdv.outputX, autoStchCond.colorIfTrueR)

		autoStchBta = pm.createNode('blendTwoAttr', n='%sIkAutoStretch%s_bta' %_name)
		autoStchBta.input[0].set(1.0)
		pm.connectAttr(self.ikCtrls[2].autoStretch, autoStchBta.attributesBlender)
		pm.connectAttr(autoStchCond.outColorR, autoStchBta.input[1])

		# --- connect manual stretch
		stchMdv = pm.createNode('multiplyDivide', n='%sIkStretch%s_mdv' %_name)
		pm.connectAttr(self.ikCtrls[2].upperStretch, stchMdv.input1X)
		pm.connectAttr(self.ikCtrls[2].midStretch, stchMdv.input1Y)
		pm.connectAttr(self.ikCtrls[2].lowerStretch, stchMdv.input1Z)
		pm.connectAttr(settingCtrlShp.defaultLenUpr, stchMdv.input2X)
		pm.connectAttr(settingCtrlShp.defaultLenMid, stchMdv.input2Y)
		pm.connectAttr(settingCtrlShp.defaultLenLwr, stchMdv.input2Z)

		pm.connectAttr(self.ikCtrls[2].upperStretch, defDistStchMdv.input2X)
		pm.connectAttr(self.ikCtrls[2].midStretch, defDistStchMdv.input2Y)
		pm.connectAttr(self.ikCtrls[2].lowerStretch, defDistStchMdv.input2Z)

		# --- combine auto stretch and manual stretch together
		ikStchPma = pm.createNode('plusMinusAverage', n='%sIkStretch%s_pma' %_name)
		pm.connectAttr(settingCtrlShp.defaultLenUpr, ikStchPma.input3D[0].input3Dx)
		pm.connectAttr(settingCtrlShp.defaultLenMid, ikStchPma.input3D[0].input3Dy)
		pm.connectAttr(settingCtrlShp.defaultLenLwr, ikStchPma.input3D[0].input3Dz)
		pm.connectAttr(stchMdv.outputX, ikStchPma.input3D[1].input3Dx)
		pm.connectAttr(stchMdv.outputY, ikStchPma.input3D[1].input3Dy)
		pm.connectAttr(stchMdv.outputZ, ikStchPma.input3D[1].input3Dz)

		autoStchMultLenMdv = pm.createNode('multiplyDivide', n='%sIkAutoStretchMultLen%s_mdv' %_name)
		pm.connectAttr(autoStchBta.output, autoStchMultLenMdv.input1X)
		pm.connectAttr(autoStchBta.output, autoStchMultLenMdv.input1Y)
		pm.connectAttr(autoStchBta.output, autoStchMultLenMdv.input1Z)
		pm.connectAttr(ikStchPma.output3Dx, autoStchMultLenMdv.input2X)
		pm.connectAttr(ikStchPma.output3Dy, autoStchMultLenMdv.input2Y)
		pm.connectAttr(ikStchPma.output3Dz, autoStchMultLenMdv.input2Z)

		# --- connect ik lock
		# ikUprLockDist = pm.createNode('distanceBetween', n='%sIkUprLock%s_dist' %_name)
		# pm.connectAttr(baseIkPosGrp.translate, ikUprLockDist.point1)
		# pm.connectAttr(pvIkPosGrp.translate, ikUprLockDist.point2)

		# ikLwrLockDist = pm.createNode('distanceBetween', n='%sIkLwrLock%s_dist' %_name)
		# pm.connectAttr(pvIkPosGrp.translate, ikLwrLockDist.point1)
		# pm.connectAttr(ikPosGrp.translate, ikLwrLockDist.point2)

		# ikLockDivLenMdv = pm.createNode('multiplyDivide', n='%sIkLockDivLen%s_mdv' %_name)
		# ikLockDivLenMdv.operation.set(2)
		# pm.connectAttr(ikUprLockDist.distance, ikLockDivLenMdv.input1X)
		# pm.connectAttr(ikLwrLockDist.distance, ikLockDivLenMdv.input1Y)
		# pm.connectAttr(settingCtrlShp.defaultLenUpr, ikLockDivLenMdv.input2X)
		# pm.connectAttr(settingCtrlShp.defaultLenLwr, ikLockDivLenMdv.input2Y)

		# ikLockMultLenMdv = pm.createNode('multiplyDivide', n='%sIkLockMultLen%s_mdv' %_name)
		# pm.connectAttr(ikLockDivLenMdv.outputX, ikLockMultLenMdv.input1X)
		# pm.connectAttr(ikLockDivLenMdv.outputY, ikLockMultLenMdv.input1Y)
		# pm.connectAttr(settingCtrlShp.defaultLenUpr, ikLockMultLenMdv.input2X)
		# pm.connectAttr(settingCtrlShp.defaultLenLwr, ikLockMultLenMdv.input2Y)

		# # connect blend colors for lock
		# ikLockBcol = pm.createNode('blendColors', n='%sIkLock%s_bco' %_name)
		# pm.connectAttr(self.ikCtrls[1].pin, ikLockBcol.blender)
		# pm.connectAttr(ikLockMultLenMdv.outputX, ikLockBcol.color1R)
		# pm.connectAttr(ikLockMultLenMdv.outputY, ikLockBcol.color1G)
		# pm.connectAttr(ikStchPma.output2D.output2Dx, ikLockBcol.color2R)
		# pm.connectAttr(ikStchPma.output2D.output2Dy, ikLockBcol.color2G)

		# # --- connect to ik joint
		# pm.connectAttr(ikLockBcol.outputR, self.ikJnts[1].attr(aimTran))
		# pm.connectAttr(ikLockBcol.outputG, self.ikJnts[2].attr(aimTran))

		pm.connectAttr(autoStchMultLenMdv.outputX, self.ikJnts[1].attr(aimTran))
		pm.connectAttr(autoStchMultLenMdv.outputY, self.ikJnts[2].attr(aimTran))
		pm.connectAttr(autoStchMultLenMdv.outputZ, self.ikJnts[3].attr(aimTran))

		pm.connectAttr(autoStchMultLenMdv.outputX, self.ikHindJnts[1].attr(aimTran))
		pm.connectAttr(autoStchMultLenMdv.outputY, self.ikHindJnts[2].attr(aimTran))
		pm.connectAttr(autoStchMultLenMdv.outputZ, self.ikHindJnts[3].attr(aimTran))

		# --- do auto flex
		# find vector of knee
		vec1 = self.ikCtrls[1].getTranslation('world') - self.ikCtrls[2].getTranslation('world')
		vec2 = self.ikCtrls[0].getTranslation('world') - self.ikCtrls[2].getTranslation('world')
		vec2Dot = vec1.dot(vec2.normal())
		vec2Proj = vec2.normal() * vec2Dot
		kneeDir = vec1 - vec2Proj
		kneeDir.normalize()
		pointZPos = kneeDir.dot(pm.dt.Vector(0, 0, 1))
		ampMult = int(round(pointZPos))

		mainIkCtrlShp = mainIkCtrl.getShape()
		misc.addNumAttr(mainIkCtrlShp, 'ikStage', 'double', key=False, min=0, max=1, dv=1)
		misc.addNumAttr(mainIkCtrlShp, 'autoFlexMult1', 'double', key=False, dv=(ampMult * 40))
		misc.addNumAttr(mainIkCtrlShp, 'autoFlexMult2', 'double', key=False, dv=(ampMult * 60))
		misc.addNumAttr(mainIkCtrlShp, 'autoFlexMult3', 'double', key=False, dv=(ampMult * 80))
		misc.addNumAttr(mainIkCtrlShp, 'autoFlexMult4', 'double', key=False, dv=(ampMult * 90))

		# misc.addNumAttr(mainIkCtrlShp, 'autoFlexAmp', 'double', dv=defHindAmp, key=False, hide=True)
		# misc.addNumAttr(mainIkCtrlShp, 'autoFlexLimit', 'double', min=0, dv=45.0, key=False, hide=True)

		self.hindIkBasePosGrp = pm.group(em=True, n='%sIkHindBasePos%s_grp' %_name)
		misc.snapTransform('point', self.ikHindJnts[0], self.hindIkBasePosGrp, False, False)
		pm.parent(self.hindIkBasePosGrp, self.rigUtilGrp)

		self.hindIkTipPosGrp = pm.group(em=True, n='%sIkHindTipPos%s_grp' %_name)
		misc.snapTransform('point', self.ikHindJnts[2], self.hindIkTipPosGrp, False, False)
		pm.parent(self.hindIkTipPosGrp, self.rigUtilGrp)

		self.ikHindAutoFlexDist = pm.createNode('distanceBetween', n='%sIkHindAutoFlex%s_dist' %_name)
		
		pm.connectAttr(self.hindIkBasePosGrp.translate, self.ikHindAutoFlexDist.point1)
		pm.connectAttr(self.hindIkTipPosGrp.translate, self.ikHindAutoFlexDist.point2)


		self.ikHindAutoFlexMdv = pm.createNode('multiplyDivide', n='%sIkHindAutoFlex%s_mdv' %_name)
		self.ikHindAutoFlexMdv.operation.set(2)
		pm.connectAttr(self.ikHindAutoFlexDist.distance, self.ikHindAutoFlexMdv.input1X)
		self.ikHindAutoFlexMdv.input2X.set(self.ikHindAutoFlexDist.distance.get())
		pm.connectAttr(self.ikHindAutoFlexMdv.outputX, mainIkCtrlShp.ikStage)
		mainIkCtrlShp.ikStage.lock()

		# create remap value
		self.legIkLAutoFlexRmv = pm.createNode('remapValue', n='%sIkHindFlex%s_rmv' %_name)

		pm.connectAttr(self.ikHindAutoFlexMdv.outputX, self.legIkLAutoFlexRmv.inputValue)
		self.legIkLAutoFlexRmv.value[0].value_Position.set(1.0)
		self.legIkLAutoFlexRmv.value[0].value_FloatValue.set(0.0)	
		self.legIkLAutoFlexRmv.value[0].value_Interp.set(1)

		self.legIkLAutoFlexRmv.value[1].value_Position.set(0.75)
		pm.connectAttr(mainIkCtrlShp.autoFlexMult1, self.legIkLAutoFlexRmv.value[1].value_FloatValue)
		self.legIkLAutoFlexRmv.value[1].value_Interp.set(3)

		self.legIkLAutoFlexRmv.value[2].value_Position.set(0.5)	
		pm.connectAttr(mainIkCtrlShp.autoFlexMult2, self.legIkLAutoFlexRmv.value[2].value_FloatValue)
		self.legIkLAutoFlexRmv.value[2].value_Interp.set(3)

		self.legIkLAutoFlexRmv.value[3].value_Position.set(0.25)	
		pm.connectAttr(mainIkCtrlShp.autoFlexMult3, self.legIkLAutoFlexRmv.value[3].value_FloatValue)
		self.legIkLAutoFlexRmv.value[3].value_Interp.set(3)

		self.legIkLAutoFlexRmv.value[4].value_Position.set(0.0)
		pm.connectAttr(mainIkCtrlShp.autoFlexMult4, self.legIkLAutoFlexRmv.value[4].value_FloatValue)
		self.legIkLAutoFlexRmv.value[4].value_Interp.set(2)

		self.legIkLFlexAdl = pm.createNode('addDoubleLinear', n='%sIkHindAutoFlex%s_adl' %_name)
		pm.connectAttr(self.legIkLAutoFlexRmv.outValue, self.legIkLFlexAdl.input1)
		pm.connectAttr(mainIkCtrl.hindFlex, self.legIkLFlexAdl.input2)
		pm.connectAttr(self.legIkLFlexAdl.output, self.flexIkPosGrp.attr(bendRot))

		# foot roll rig
		if self.createFootRig == True:
			ikCtrlFootSepAttr = misc.addNumAttr(mainIkCtrl, '__foot__', 'double', hide=False, min=0, max=1, dv=0)
			ikCtrlFootSepAttr.lock()

			misc.addNumAttr(mainIkCtrl, 'toeRoll', 'double')
			misc.addNumAttr(mainIkCtrl, 'ballRoll', 'double')
			misc.addNumAttr(mainIkCtrl, 'heelRoll', 'double')

			misc.addNumAttr(mainIkCtrl, 'toeTwist', 'double')
			misc.addNumAttr(mainIkCtrl, 'ballTwist', 'double')
			misc.addNumAttr(mainIkCtrl, 'heelTwist', 'double')

			misc.addNumAttr(mainIkCtrl, 'toeBend', 'double')
			misc.addNumAttr(mainIkCtrl, 'footRock', 'double')

			ballTwstIkPivGrp = pm.group(em=True, n='%sBallTwstIkPiv%s_grp' %_name)
			ballTwstIkPivZroGrp = misc.zgrp(ballTwstIkPivGrp, element='Zro', suffix='grp')[0]
			misc.snapTransform('parent', self.tmpJnts[4], ballTwstIkPivZroGrp, False, True)
			pm.parent(ballTwstIkPivZroGrp, ikFootScaleGrp)

			toeIkPivGrp = pm.group(em=True, n='%sToeIkPiv%s_grp' %_name)
			toeIkPivZroGrp = misc.zgrp(toeIkPivGrp, element='Zro', suffix='grp')[0]
			misc.snapTransform('parent', self.tmpJnts[5], toeIkPivZroGrp, False, True)
			pm.parent(toeIkPivZroGrp, ballTwstIkPivGrp)

			heelIkPivGrp = pm.group(em=True, n='%sHeelIkPiv%s_grp' %_name)
			heelIkPivZroGrp = misc.zgrp(heelIkPivGrp, element='Zro', suffix='grp')[0]
			misc.snapTransform('parent', self.tmpJnts[6], heelIkPivZroGrp, False, True)
			pm.parent(heelIkPivZroGrp, toeIkPivGrp)

			footInIkPivGrp = pm.group(em=True, n='%sFootInIkPiv%s_grp' %_name)
			footInIkPivZroGrp = misc.zgrp(footInIkPivGrp, element='Zro', suffix='grp')[0]
			misc.snapTransform('parent', self.tmpJnts[7], footInIkPivZroGrp, False, True)
			pm.parent(footInIkPivZroGrp, heelIkPivGrp)
			# set min limit
			rotLimitMinName = 'rotateMin%s' %self.aimAxis.upper()
			footInIkPivGrp.setLimited(rotLimitMinName, True)
			footInIkPivGrp.setLimit(rotLimitMinName, 0.0)

			footOutIkPivGrp = pm.group(em=True, n='%sFootOutIkPiv%s_grp' %_name)
			footOutIkPivZroGrp = misc.zgrp(footOutIkPivGrp, element='Zro', suffix='grp')[0]
			misc.snapTransform('parent', self.tmpJnts[8], footOutIkPivZroGrp, False, True)
			pm.parent(footOutIkPivZroGrp, footInIkPivGrp)
			# set max limit
			rotLimitMaxName = 'rotateMax%s' %self.aimAxis.upper()
			footOutIkPivGrp.setLimited(rotLimitMaxName, True)
			footOutIkPivGrp.setLimit(rotLimitMaxName, 0.0)

			ballRollIkPivGrp = pm.group(em=True, n='%sBallRollIkPiv%s_grp' %_name)
			ballRollIkPivZroGrp = misc.zgrp(ballRollIkPivGrp, element='Zro', suffix='grp')[0]
			misc.snapTransform('parent', self.tmpJnts[4], ballRollIkPivZroGrp, False, True)
			pm.parent(ballRollIkPivZroGrp, footOutIkPivGrp)

			pm.parent([self.ankleIkPivGrp, self.lowIkPivGrp], ballRollIkPivGrp)

			toeBendIkPivGrp = pm.group(em=True, n='%sToeBendIkPiv%s_grp' %_name)
			toeBendIkPivZroGrp = misc.zgrp(toeBendIkPivGrp, element='Zro', suffix='grp')[0]
			misc.snapTransform('parent', self.tmpJnts[4], toeBendIkPivZroGrp, False, True)
			pm.parent(toeBendIkPivZroGrp, footOutIkPivGrp)

			pm.parent(self.tipIkPivGrp, toeBendIkPivGrp)

			# connect attrs
			pm.connectAttr(mainIkCtrl.toeRoll, toeIkPivGrp.attr(bendRot))
			pm.connectAttr(mainIkCtrl.ballRoll, ballRollIkPivGrp.attr(bendRot))
			pm.connectAttr(mainIkCtrl.heelRoll, heelIkPivGrp.attr(bendRot))

			pm.connectAttr(mainIkCtrl.toeTwist, toeIkPivGrp.attr(upRot))
			pm.connectAttr(mainIkCtrl.ballTwist, ballTwstIkPivGrp.attr(upRot))
			pm.connectAttr(mainIkCtrl.heelTwist, heelIkPivGrp.attr(upRot))

			pm.connectAttr(mainIkCtrl.footRock, footInIkPivGrp.attr(aimRot))
			pm.connectAttr(mainIkCtrl.footRock, footOutIkPivGrp.attr(aimRot))

			pm.connectAttr(mainIkCtrl.toeBend, toeBendIkPivGrp.attr(bendRot))

