# import maya.cmds as mc
import pymel.core as pm

from nuTools import misc, controller
reload(misc)
reload(controller)
import nuTools.rigTools.baseRig as baseRig
# reload(singleJntRig)

class SingleIkRig(baseRig.BaseRig):
	def __init__(self, 
			jnts=[],
			aimAxis='y',
			upAxis='x',
			createTipCtrl=True,
			ctrlShp='diamond',
			ctrlColor='blue',
			baseCtrlShp='locator',
			baseCtrlColor='blue',
			pvCtrlShp='locator',
			pvCtrlColor='blue',
			tipCtrlShp='crossCircle',
			tipCtrlColor='lightBlue',
			**kwargs):
		super(SingleIkRig, self).__init__(**kwargs)
		# temp joints
		self.tmpJnts = self.jntsArgs(jnts)

		self.ctrlShp = ctrlShp
		self.ctrlColor = ctrlColor
		self.baseCtrlShp = baseCtrlShp
		self.baseCtrlColor = baseCtrlColor
		self.pvCtrlShp = pvCtrlShp
		self.pvCtrlColor = pvCtrlColor
		self.tipCtrlShp = tipCtrlShp
		self.tipCtrlColor = tipCtrlColor

		self.createTipCtrl = createTipCtrl

		# axis
		self.aimAxis = aimAxis
		self.upAxis = upAxis

		# joints
		self.jnts = []

		# controllers
		self.ikCtrls = []
		self.ikGCtrls = []

		# groups
		self.ikCtrlZgrps = []
		self.ikCtrlOfstGrps = []

		# Iks
		self.ikHndls = []
		self.ikEffs = []
		self.ikHndlZgrps = []

	def rig(self):
		# --- translate axis from string to vector
		aimVec = misc.vectorStr(self.aimAxis)
		upVec = misc.vectorStr(self.upAxis)

		aimTran = 't%s' %(self.aimAxis[-1])
		aimScale = 's%s' %(self.aimAxis[-1])
		self.bendAxis = misc.crossAxis(self.aimAxis, self.upAxis)[-1]
		

		# --- get class name to use for naming
		_name = (self.elem, self.side)

		# --- create main groups
		self.rigCtrlGrp = pm.group(em=True, n='%sRig%s_grp' %_name)
		self.rigUtilGrp = pm.group(em=True, n='%sUtil%s_grp' %_name)
		self.rigIkhGrp = pm.group(em=True, n='%sIkh%s_grp' %_name)
		self.rigIkhGrp.visibility.set(False)
		pm.parent([self.rigIkhGrp], self.rigUtilGrp)

		# duplicate joint from tmpJnt
		upJnt = pm.duplicate(self.tmpJnts[0], po=True, n='%sUpr%s_jnt' %(self.elem, self.side))[0]
		lwrJnt = pm.duplicate(self.tmpJnts[1], po=True, n='%sLwr%s_jnt' %(self.elem, self.side))[0]
		endJnt = pm.duplicate(self.tmpJnts[2], po=True, n='%sEnd%s_jnt' %(self.elem, self.side))[0]

		# parent into fk chain
		pm.parent(endJnt, lwrJnt)
		pm.parent(lwrJnt, upJnt)
		pm.parent(upJnt, self.rigUtilGrp)

		self.jnts = [upJnt, lwrJnt, endJnt]
			
		# freeze it
		pm.makeIdentity(upJnt, apply=True)

		# ------ IK rig
		# --- legRoot ik ctrl
		baseIkCtrl = controller.JointController(name='%sIkBase%s_ctrl' %(_name),
										st=self.baseCtrlShp, scale=self.size)
		baseIkCtrl.setColor(self.baseCtrlColor)
		baseIkCtrl.lockAttr(r=True, s=True, v=True)
		baseIkCtrl.hideAttr(r=True, s=True, v=True)
		baseIkCtrlOfstGrp = misc.zgrp(baseIkCtrl, element='Ofst', suffix='grp')[0]	
		baseIkCtrlZgrp = misc.zgrp(baseIkCtrlOfstGrp, element='Zro', suffix='grp')[0]	

		# --- leg pv ctrl
		pvIkCtrl = controller.JointController(name='%sIkPv%s_ctrl' %(_name),
										st=self.pvCtrlShp, scale=self.size*0.334)
		pvIkCtrl.setColor(self.pvCtrlColor)
		pvIkCtrl.lockAttr(r=True, s=True, v=True)
		pvIkCtrl.hideAttr(r=True, s=True, v=True)
		# pinAttr = misc.addNumAttr(pvIkCtrl, 'pin', 'double', min=0, max=1, dv=0)

		pvIkCtrlOfstGrp = misc.zgrp(pvIkCtrl, element='Ofst', suffix='grp')[0]
		pvIkCtrlZgrp = misc.zgrp(pvIkCtrlOfstGrp, element='Zro', suffix='grp')[0]
		# pvIkCtrlLocWorAttr = misc.addNumAttr(pvIkCtrl, 'localWorld', 'double', min=0, max=1, dv=0)
	
		# --- legIK ctrl
		mainIkCtrl = controller.JointController(name='%sIk%s_ctrl' %(_name),
										st=self.ctrlShp, scale=self.size)
		mainIkCtrlShp = mainIkCtrl.getShape()
		mainIkCtrl.rotateOrder.set(self.rotateOrder)
		mainIkCtrl.setColor(self.ctrlColor)
		# mainIkGCtrl = mainIkCtrl.addGimbal()
		mainIkCtrlOfstGrp = misc.zgrp(mainIkCtrl, element='Ofst', suffix='grp')[0]
		mainIkCtrlZgrp = misc.zgrp(mainIkCtrlOfstGrp, element='Zro', suffix='grp')[0]

		# add attributes
		ikCtrlLocWorAttr = misc.addNumAttr(mainIkCtrl, 'localWorld', 'double', min=0, max=1, dv=1)
		ikCtrlSepAttr = misc.addNumAttr(mainIkCtrl, '__ik__', 'double', hide=False, min=0, max=1, dv=0)
		ikCtrlSepAttr.lock()
		twistAttr = misc.addNumAttr(mainIkCtrl, 'twist', 'double')
		autoStretchAttr = misc.addNumAttr(mainIkCtrl, 'autoStretch', 'double', min=0, max=1, dv=0)

		# add to ik ctrl shape
		pvCtrlVisAttr = misc.addNumAttr(mainIkCtrlShp, 'pvCtrl_vis', 'double', key=False, hide=False, dv=0)

		defaultLenValue = self.jnts[1].attr(aimTran).get()
		defLenAttr = misc.addNumAttr(mainIkCtrlShp, 'defaultLen', 'double', key=False, hide=True, dv=abs(defaultLenValue))
		defLenAttr.setKeyable(False)
		defLenAttr.showInChannelBox(False)
		defLenAttr.setLocked(True)

		# --- store ik controllers to list
		self.ikCtrls = [baseIkCtrl, pvIkCtrl, mainIkCtrl]
		self.ikCtrlOfstGrps = [baseIkCtrlOfstGrp, pvIkCtrlOfstGrp, mainIkCtrlOfstGrp]
		self.ikCtrlZgrps = [baseIkCtrlZgrp, pvIkCtrlZgrp, mainIkCtrlZgrp]

		# --- position ik ctrls
		legLen = misc.getDistanceFromPosition(self.jnts[0].getTranslation('world'), self.jnts[1].getTranslation('world'))

		misc.snapTransform('point', self.jnts[0], self.ikCtrlZgrps[0], False, True)
		misc.snapTransform('point', self.jnts[0], self.ikCtrlZgrps[1], False, True)

		pm.xform(self.ikCtrlZgrps[1], r=True, os=True, t=(upVec*self.size))

		misc.snapTransform('point', self.jnts[1], self.ikCtrlZgrps[2], False, True)
		misc.snapTransform('orient', self.jnts[1], self.ikCtrls[2], False, True)
		pm.makeIdentity(self.ikCtrls[2], apply=True, t=True, r=True, s=True)

		# lock the main ik ctrl
		mainIkCtrl.lockAttr(r=False, s=False, v=True)
		mainIkCtrl.hideAttr(r=False, s=False, v=True)

		# throw ik ctrl zgrp to ik ctrl grp
		pm.parent(self.ikCtrlZgrps, self.rigCtrlGrp)

		# point ik base to ik base ctrl
		misc.snapTransform('point', self.ikCtrls[0], self.jnts[0], True, False)

		# ---- create Ik handle
		ikHndl, ikEff = pm.ikHandle(sj=self.jnts[0], ee=self.jnts[1], sol='ikRPsolver', n='%s%s_ikHndl' %_name)
		ikHndlZgrp = misc.zgrp(ikHndl, element='Zro', suffix='grp')[0]

		tipIkHndl, tipIkEff = pm.ikHandle(sj=self.jnts[1], ee=self.jnts[2], sol='ikRPsolver', n='%sTip%s_ikHndl' %_name)
		tipIkHndlZgrp = misc.zgrp(tipIkHndl, element='Zro', suffix='grp')[0]

		self.ikHndls = [ikHndl, tipIkHndl]
		self.ikEffs = [ikEff, tipIkEff]
		self.ikHndlZgrps = [ikHndlZgrp, tipIkHndlZgrp]
		pm.parent(self.ikHndlZgrps, self.rigIkhGrp)

		self.ikPosGrp = pm.group(em=True, n='%sIkHndlPiv%s_grp' %_name)
		# self.tipIkPivGrp = pm.group(em=True, n='%sTipIkHndlPiv%s_grp' %_name)
		misc.snapTransform('point', self.ikHndls[0], self.ikPosGrp, False, True)
		# misc.snapTransform('point', self.ikHndls[1], self.tipIkPivGrp, False, True)

		self.ikScaleGrp = pm.group(em=True, n='%sIkScale%s_grp' %_name)
		misc.snapTransform('parent', self.jnts[1], self.ikScaleGrp, False, True)
		pm.connectAttr(mainIkCtrl.scale, self.ikScaleGrp.scale)
		pm.connectAttr(mainIkCtrl.scale, self.jnts[1].scale)

		# pm.parent([self.ikPosGrp, self.tipIkPivGrp], self.ikScaleGrp)
		pm.parent(self.ikPosGrp, self.ikScaleGrp)
		pm.parent(self.ikScaleGrp, mainIkCtrl)

		misc.snapTransform('parent', self.ikPosGrp, self.ikHndlZgrps[0], False, False)
		misc.snapTransform('parent', self.ikPosGrp, self.ikHndlZgrps[1], True, False)
		# misc.snapTransform('parent', self.tipIkPivGrp, self.ikHndlZgrps[1], False, False)

		# --- polevector constriant
		pm.poleVectorConstraint(self.ikCtrls[1], self.ikHndls[0])
		pvShiftValue = self.jnts[0].attr('r%s' %self.aimAxis[-1]).get()

		# --- add pv annotation line
		annDict = misc.annPointer(pointFrom=self.jnts[0], pointTo=self.ikCtrls[1], 
				ref=True, constraint=True)
		annGrp = pm.group(em=True, n='%sAnnPointer%s_grp' %_name)
		pm.parent([annDict['ann'], annDict['loc']], annGrp)
		pm.parent(annGrp, self.rigCtrlGrp)

		pm.connectAttr(pvCtrlVisAttr, pvIkCtrlZgrp.visibility)
		pm.connectAttr(pvCtrlVisAttr, annGrp.visibility)

		# --- ik ctrl and pv ik ctrl local world
		misc.createLocalWorld(objs=[self.ikCtrls[2], self.ikCtrls[0], self.animGrp, self.ikCtrlZgrps[2]], constraintType='parent', attrName='localWorld')
		# misc.createLocalWorld(objs=[self.ikCtrls[1], self.ikCtrls[2], self.animGrp, self.ikCtrlZgrps[1]], constraintType='parent', attrName='localWorld')

		# --- connect twist
		twistMultValue = 1.0 if defaultLenValue > 0.0 else -1.0

		ikTwstMdl = pm.createNode('multDoubleLinear', n='%sIkTwist%s_mdl' %_name)
		ikTwstMdl.input2.set(twistMultValue)
		pm.connectAttr(self.ikCtrls[2].twist, ikTwstMdl.input1)

		ikTwstAdl = pm.createNode('addDoubleLinear', n='%sIkTwist%s_adl' %_name)
		pm.connectAttr(ikTwstMdl.output, ikTwstAdl.input1)
		ikTwstAdl.input2.set(pvShiftValue * -1)

		pm.connectAttr(ikTwstAdl.output, self.ikHndls[0].twist)

		# --- create position groups
		baseIkPosGrp = pm.group(em=True, n='%sIkBasePos%s_grp' %_name)
		misc.snapTransform('point', self.ikCtrls[0], baseIkPosGrp, False, False)

		ikPosGrp = pm.group(em=True, n='%sIkPos%s_grp' %_name)
		misc.snapTransform('point', self.ikHndlZgrps[0], ikPosGrp, False, False)
		pm.parent([baseIkPosGrp, ikPosGrp], self.rigCtrlGrp)

		# make value absoulute
		ikAbsPowMdv = pm.createNode('multiplyDivide', n='%sIkAbsPow%s_mdv' %_name)
		ikAbsPowMdv.operation.set(3)
		ikAbsPowMdv.input2X.set(2)
		pm.connectAttr(mainIkCtrlShp.defaultLen, ikAbsPowMdv.input1X)

		ikAbsSqrtMdv = pm.createNode('multiplyDivide', n='%sIkAbsSqrt%s_mdv' %_name)
		ikAbsSqrtMdv.operation.set(3)
		ikAbsSqrtMdv.input2X.set(0.5)
		pm.connectAttr(ikAbsPowMdv.outputX, ikAbsSqrtMdv.input1X)

		ikDist = pm.createNode('distanceBetween', n='%sIkAutoStretchIk%s_dist' %_name)
		pm.connectAttr(baseIkPosGrp.translate, ikDist.point1)
		pm.connectAttr(ikPosGrp.translate, ikDist.point2)

		autoStchDivOrigMdv = pm.createNode('multiplyDivide', n='%sIkAutoStretchDivOrig%s_mdv' %_name)
		autoStchDivOrigMdv.operation.set(2)
		pm.connectAttr(ikDist.distance, autoStchDivOrigMdv.input1X)
		pm.connectAttr(mainIkCtrlShp.defaultLen, autoStchDivOrigMdv.input2X)

		autoStchBta = pm.createNode('blendTwoAttr', n='%sIkAutoStretch%s_bta' %_name)
		pm.connectAttr(self.ikCtrls[2].autoStretch, autoStchBta.attributesBlender)
		autoStchBta.input[0].set(1.0)
		autoStchBta.input[1].set(9999.0)

		autoStchCmp = pm.createNode('clamp', n='%sIkAutoStretch%s_cmp' %_name)
		pm.connectAttr(autoStchBta.output, autoStchCmp.maxR)
		pm.connectAttr(autoStchDivOrigMdv.outputX, autoStchCmp.inputR)

		# --- connect to ik joint
		pm.connectAttr(autoStchCmp.outputR, self.jnts[0].attr(aimScale))


		# --- tip ctrl
		if self.createTipCtrl:
			tipJnt = pm.duplicate(self.tmpJnts[2], po=True, n='%sTip%s_jnt' %(self.elem, self.side))[0]
			tipJnt.radius.set(endJnt.radius.get() * 1.2)
			pm.parent(tipJnt, endJnt)

			self.jnts.append(tipJnt)

			tipCtrl = controller.JointController(name='%sIkTip%s_ctrl' %(_name),
										st=self.tipCtrlShp, scale=self.size)
			tipCtrl.rotateOrder.set(self.rotateOrder)
			tipCtrl.setColor(self.ctrlColor)
			tipCtrlOfstGrp = misc.zgrp(tipCtrl, element='Ofst', suffix='grp')[0]
			tipCtrlZgrp = misc.zgrp(tipCtrlOfstGrp, element='Zro', suffix='grp')[0]

			misc.snapTransform('parent', tipJnt, tipCtrlZgrp, False, True)
			pm.parent(tipCtrlZgrp, self.ikScaleGrp)
			misc.directConnectTransform(objs=[tipCtrl, tipJnt], t=True, r=False, s=False, force=True)
			misc.snapTransform('orient', tipCtrl, tipJnt, False, False)
			# pm.parent(self.tipIkPivGrp, tipCtrl)

			self.ikCtrls.append(tipCtrl)
			pm.connectAttr(tipCtrl.scale, tipJnt.scale)

			tipCtrl.lockAttr(v=True)
			tipCtrl.hideAttr(v=True)

		# parent main grps
		self.parentCons =  misc.snapTransform('parent', self.parent, self.rigCtrlGrp, True, False)
			
		pm.parent(self.rigCtrlGrp, self.animGrp)
		pm.parent(self.rigUtilGrp, self.utilGrp)