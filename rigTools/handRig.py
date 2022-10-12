# import maya.cmds as mc
import pymel.core as pm

from nuTools import misc, controller
reload(misc)
reload(controller)
import nuTools.rigTools.baseRig as baseRig
reload(baseRig)

FOLD_MULT = -1.0
SPREAD_MULT = 1.0
TWIST_MULT = 1.0

# default index setting
DEFAULT_POSTURES = {'fist': {'bend2':-9, 'bend3':-9, 'bend4':-9, 'side1':0, 'side2':0}, 
					'cup': {'bend2':-1, 'bend3':-1, 'bend4':-1}, 
					'spread': {'side2':-9}, 
					'break': {'side2':-9}, 
					'fold': {'bend2':-9}, 
					'baseCup': {'bend1':-9},  
					'baseSpread': {'side1':-9}, 
					'baseBreak': {'side1':-9}, 
					'baseFold': {'bend1':-9}}

# ------------------------------------------------------------------------------------
# example setting
INDEX_POSTURES = {'fist': {'bend2':-9, 'bend3':-9, 'bend4':-9, 'side1':0, 'side2':0}, 
					'cup': {'bend2':-1}, 
					'spread': {'side2':-9}, 
					'break': {'side2':-9}, 
					'fold': {'bend2':-9}, 
					'baseCup': {'bend1':-1},  
					'baseSpread': {'side1':-9}, 
					'baseBreak': {'side1':-9}, 
					'baseFold': {'bend1':-9}}
MIDDLE_POSTURES = {'fist': {'bend2':-9, 'bend3':-9, 'bend4':-9, 'side1':0, 'side2':0}, 
					'cup': {'bend2':-2.5}, 
					'spread': {'side2':0}, 
					'break': {'side2':-9}, 
					'fold': {'bend2':-9}, 
					'baseCup': {'bend1':-2.5},  
					'baseSpread': {'side1':0}, 
					'baseBreak': {'side1':-9}, 
					'baseFold': {'bend1':-9}}
RING_POSTURES = {'fist': {'bend2':-9, 'bend3':-9, 'bend4':-9, 'side1':0, 'side2':0}, 
					'cup': {'bend2':-3.5}, 
					'spread': {'side2':4.5}, 
					'break': {'side2':-9}, 
					'fold': {'bend2':-9}, 
					'baseCup': {'bend1':-3.5},  
					'baseSpread': {'side1':4.5}, 
					'baseBreak': {'side1':-9}, 
					'baseFold': {'bend1':-9}}
PINKY_POSTURES = {'fist': {'bend2':-9, 'bend3':-9, 'bend4':-9, 'side1':0, 'side2':0}, 
					'cup': {'bend2':-4.5}, 
					'spread': {'side2':9}, 
					'break': {'side2':-9}, 
					'fold': {'bend2':-9}, 
					'baseCup': {'bend1':-4.5},  
					'baseSpread': {'side1':9}, 
					'baseBreak': {'side1':-9}, 
					'baseFold': {'bend1':-9}}
THUMB_POSTURES = {'fist': {'bend1':0, 'bend2':-4.5, 'bend3':-9, 
						'side1':0, 'side2':0, 'side3':0, 
						'twist1':0, 'twist2':0, 'twist3':0,}}

class HandRig(baseRig.BaseRig):
	def __init__(self, 
				jnts=[],
				postureCtrl=None,
				poses=[INDEX_POSTURES, MIDDLE_POSTURES, 
					RING_POSTURES, PINKY_POSTURES, 
					THUMB_POSTURES],
				fingerNames=['index', 'middle', 'ring', 
					'pinky', 'thumb'],
				rootCtrlShp='squareStick',
				ctrlShp='crossCircle',
				rootCtrlColor='lightBlue',
				ctrlColor='red',
				aimAxis='y',
				upAxis='z',
				**kwargs):
		super(HandRig, self).__init__(**kwargs)

		# temp joints
		self.tmpJnts = self.chainArgs(jnts)
		self.fingerNames = fingerNames

		self.aimAxis = aimAxis
		self.upAxis = upAxis
		self.ctrlShp = ctrlShp
		self.rootCtrlShp = rootCtrlShp
		self.rootCtrlColor = rootCtrlColor
		self.ctrlColor = ctrlColor

		self.fingers = []

		self.postureCtrl = postureCtrl
		self.poses = poses

	def chainArgs(self, jnts):
		chains = []
		for chain in jnts:
			joints = []
			for j in chain:
				if isinstance(j, (str, unicode)):
					try:
						j = pm.PyNode(j)
					except:
						pass
				joints.append(j)
			chains.append(joints)

		return chains

	def rig(self):
		_name = (self.elem, self.side)
		self.rigCtrlGrp = pm.group(em=True, n='%sRig%s_grp' %_name)
		pm.parentConstraint(self.parent, self.rigCtrlGrp, mo=True)
		pm.parent(self.rigCtrlGrp, self.animGrp)

		self.rigUtilGrp = pm.group(em=True, n='%sUtil%s_grp' %_name)
		pm.parent(self.rigUtilGrp, self.utilGrp)

		for fingerJnts, fingerPoses, fingerName in zip(self.tmpJnts, self.poses, self.fingerNames):
			fingerRig = FingerRig(jnts=fingerJnts,
				parent=None,
				rootCtrlShp=self.rootCtrlShp,
				ctrlShp=self.ctrlShp,
				rootCtrlColor=self.rootCtrlColor,
				ctrlColor=self.ctrlColor,
				aimAxis=self.aimAxis,
				upAxis=self.upAxis,
				doPostureRig=True,
				postureCtrl=self.postureCtrl,
				postureElem=self.elem,
				poses=fingerPoses,
				elem=fingerName,
				side=self.side,
				size=self.size,
				utilGrp=self.rigUtilGrp
				)
			fingerRig.rig()
			pm.parent(fingerRig.rigCtrlGrp, self.rigCtrlGrp)

			self.fingers.append(fingerRig)

class FingerRig(baseRig.BaseRig):
	def __init__(self, 
				jnts=[],
				rootCtrlShp='squareStick',
				ctrlShp='crossCircle',
				rootCtrlColor='lightBlue',
				ctrlColor='red',
				aimAxis='y',
				upAxis='z',
				doPostureRig=True,
				postureCtrl=None,
				postureElem='hand',
				poses=DEFAULT_POSTURES,
				**kwargs):
		super(FingerRig, self).__init__(**kwargs)

		# temp joints
		self.tmpJnts = self.jntsArgs(jnts)

		self.aimAxis = aimAxis
		self.upAxis = upAxis
		self.ctrlShp = ctrlShp
		self.rootCtrlShp = rootCtrlShp
		self.rootCtrlColor = rootCtrlColor
		self.ctrlColor = ctrlColor

		self.rootCtrl = None
		self.jnts = []
		self.ctrls = []
		# self.gCtrls = []
		self.ctrlZgrps = []
		self.ctrlBendGrps = []
		self.ctrlSdkGrps = []
		self.ctrlTwstGrps = []

		self.doPostureRig = doPostureRig
		self.postureCtrl = postureCtrl
		self.postureElem = postureElem
		self.poses = poses

	def rig(self):
		# --- get class name to use for naming
		_name = (self.elem, self.side)

		# --- axis and rotate order
		aimTran = 't%s' %(self.aimAxis[-1])
		self.bendAxis = misc.crossAxis(self.aimAxis, self.upAxis)[-1]

		self.rotateOrder = '%s%s%s' %(self.bendAxis, self.upAxis, self.aimAxis)

		# --- create main groups
		self.rigCtrlGrp = pm.group(em=True, n='%sRig%s_grp' %_name)
		self.rigUtilGrp = pm.group(em=True, n='%sUtil%s_grp' %_name)

		# --- create the joint
		rad = self.tmpJnts[0].radius.get()
		parentJnt = None
		for i, tmpJnt in enumerate(self.tmpJnts):
			jnt = pm.createNode('joint', n='%s%s%s_jnt' %(self.elem, i+1, self.side))
			misc.snapTransform('parent', tmpJnt, jnt, False, True)
			jnt.radius.set(rad)
			pm.makeIdentity(jnt, apply=True)
			self.jnts.append(jnt)

			if parentJnt:
				pm.parent(jnt, parentJnt)
			parentJnt = jnt

		# --- create detail controllers
		toParent = self.rigCtrlGrp
		for i in xrange(len(self.jnts)-1):
			jnt = self.jnts[i]

			ctrl = controller.Controller(name='%s%s%s_ctrl' %(self.elem, i+1, self.side), 
					st=self.ctrlShp, scale=(self.size*0.5))
			ctrl.setColor(self.ctrlColor)
			ctrl.rotateOrder.set(self.rotateOrder)
			# gCtrl = ctrl.addGimbal()

			toLockHide = {'t':False, 'r':False, 's':True, 'v':True}
			misc.lockAttr(ctrl, **toLockHide)
			misc.hideAttr(ctrl, **toLockHide)

			# get ctrl shape
			ctrlShp = ctrl.getShape(ni=True)

			sdkGrp = misc.zgrp(ctrl, element='Sdk', suffix='grp')[0]
			twstGrp = misc.zgrp(sdkGrp, element='Twst', remove='Sdk', suffix='grp')[0]
			bendGrp = misc.zgrp(twstGrp, element='Bend', remove='Twst', suffix='grp')[0]
			zGrp = misc.zgrp(bendGrp, element='Zro', remove='Bend', suffix='grp')[0]

			# constraint to postion
			misc.snapTransform('parent', jnt, zGrp, False, True)
			pm.parent(zGrp, toParent)

			misc.snapTransform('parent', ctrl, jnt, False, False)
			
			self.ctrls.append(ctrl)
			# self.gCtrls.append(gCtrl)
			self.ctrlTwstGrps.append(twstGrp)
			self.ctrlSdkGrps.append(sdkGrp)
			self.ctrlBendGrps.append(bendGrp)
			self.ctrlZgrps.append(zGrp)

			# create local world only if i=1 (the knuckle)
			# if i == 1:
			# 	misc.createLocalWorld(objs=[ctrl, toParent, self.parent, zGrp], 
			# 		constraintType='orient', attrName='localWorld')

			toParent = ctrl

		# --- add stretch and squash
		c = 0
		stretchPmas, squashPmas = [], []
		for i, ctrl in enumerate(self.ctrls):
			ctrlShp = ctrl.getShape()
			_numName = (self.elem, i+1, self.side)

			if i < len(self.ctrls) - 1:
				tgt = self.ctrlZgrps[i+1]
			else:
				tgt = self.jnts[i+1]

			# - stretch
			aimAxisAttr = self.jnts[i+1].attr(aimTran)
			defaultLenValue = aimAxisAttr.get()

			misc.addNumAttr(ctrl, 'stretch', 'double', dv=0)
			misc.addNumAttr(ctrlShp, 'defaultLen', 'double', dv=defaultLenValue)

			stretchMdl = pm.createNode('multDoubleLinear', n='%sStretch%s%s_mdl' %_numName)
			stretchPma = pm.createNode('plusMinusAverage', n='%sStretch%s%s_pma' %_numName)
			pm.connectAttr(ctrl.stretch, stretchMdl.input1)
			pm.connectAttr(ctrlShp.defaultLen, stretchMdl.input2)
			pm.connectAttr(ctrlShp.defaultLen, stretchPma.input1D.input1D[0])
			pm.connectAttr(stretchMdl.output, stretchPma.input1D.input1D[1])
			pm.connectAttr(stretchPma.output1D, tgt.attr(aimTran))

			stretchPmas.append(stretchPma)

			# hide attrs
			ctrlShp.defaultLen.setKeyable(False)
			ctrlShp.defaultLen.showInChannelBox(False)

			# - squash
			misc.addNumAttr(ctrl, 'squash', 'double', dv=0)
			squashPma = pm.createNode('plusMinusAverage', n='%sSquash%s%s_pma' %_numName)
			squashPma.input1D.input1D[0].set(1.0)
			pm.connectAttr(ctrl.squash, squashPma.input1D.input1D[1])
			pm.connectAttr(squashPma.output1D, self.jnts[i].attr('s%s' %self.upAxis))
			pm.connectAttr(squashPma.output1D, self.jnts[i].attr('s%s' %self.bendAxis))

			squashPmas.append(squashPma)

			if i == len(self.ctrls) - 1:
				# squash tip
				misc.addNumAttr(ctrl, 'squashTip', 'double', dv=0)
				squashTipPma = pm.createNode('plusMinusAverage', n='%sSquash%s%s_pma' %(self.elem, i+2, self.side))
				squashTipPma.input1D.input1D[0].set(1.0)
				pm.connectAttr(ctrl.squashTip, squashTipPma.input1D.input1D[1])
				pm.connectAttr(squashTipPma.output1D, self.jnts[i+1].attr('s%s' %self.upAxis))
				pm.connectAttr(squashTipPma.output1D, self.jnts[i+1].attr('s%s' %self.bendAxis))

				squashPmas.append(squashTipPma)
			
		# --- create root controller
		self.rootCtrl = controller.Controller(name='%s%s_ctrl' %_name, 
					st=self.rootCtrlShp, scale=(self.size), axis=self.upAxis)
		self.rootCtrl.setColor(self.rootCtrlColor)
		self.rootCtrl.lockAttr(t=False, r=False, s=True, v=True)
		self.rootCtrl.hideAttr(t=False, r=False, s=True, v=True)
		
		rootZgrp = misc.zgrp(self.rootCtrl, element='Zro', suffix='grp')[0]
		misc.snapTransform('parent', self.ctrls[0], rootZgrp, False, True)
		pm.parent(rootZgrp, self.rigCtrlGrp)
		pm.parent(self.ctrlZgrps[0], self.rootCtrl)

		fngerDivAttr = misc.addNumAttr(self.rootCtrl, '__finger__', 'double', hide=False)
		fngerDivAttr.lock()
		misc.addNumAttr(self.rootCtrl, 'fold', 'double', hide=False)
		misc.addNumAttr(self.rootCtrl, 'stretch', 'double', hide=False)
		misc.addNumAttr(self.rootCtrl, 'squash', 'double', hide=False)
		rootCtrlShp = self.rootCtrl.getShape()

		# connect detailVis ctrl
		rootCtrlShp = self.rootCtrl.getShape()
		detailCtrlVisAttr = misc.addNumAttr(rootCtrlShp, 'detailCtrl_vis', 'long', hide=False, min=0, max=1, dv=0)
		detailCtrlVisAttr.setKeyable(False)
		detailCtrlVisAttr.showInChannelBox(True)
		pm.connectAttr(detailCtrlVisAttr, self.ctrlZgrps[0].visibility)


		# - connect fold 
		sepAttr = misc.addNumAttr(self.rootCtrl, '__fold__', 'double', hide=False)
		sepAttr.lock()
		sepShpAttr = misc.addNumAttr(rootCtrlShp, '__fold__', 'double', hide=False)
		sepShpAttr.lock()
		foldMultAttr = misc.addNumAttr(rootCtrlShp, 'fold_mult', 'double', hide=False, dv=FOLD_MULT)
		
		for i, grp in enumerate(self.ctrlBendGrps):
			_numName = (self.elem, i+1, self.side)
			foldAttr = misc.addNumAttr(self.rootCtrl, 'fold%s' %(i+1), 'double', hide=False)
			
			foldMdl = pm.createNode('multDoubleLinear', n='%sFold%s%s_mdl' %_numName)
			if i > 0:
				foldAdl = pm.createNode('addDoubleLinear', n='%sFold%s%s_adl' %_numName)
				pm.connectAttr(self.rootCtrl.fold, foldAdl.input1)
				pm.connectAttr(foldAttr, foldAdl.input2)
				pm.connectAttr(foldAdl.output, foldMdl.input1)
			else:
				pm.connectAttr(foldAttr, foldMdl.input1)
			
			pm.connectAttr(foldMultAttr, foldMdl.input2)
			pm.connectAttr(foldMdl.output, grp.attr('r%s' %self.bendAxis))

			foldMultAttr.setKeyable(False)
			foldMultAttr.showInChannelBox(True)

		# - connect spread 
		sepAttr = misc.addNumAttr(self.rootCtrl, '__spread__', 'double', hide=False)
		sepAttr.lock()
		sepShpAttr = misc.addNumAttr(rootCtrlShp, '__spread__', 'double', hide=False)
		sepShpAttr.lock()
		spreadMultAttr = misc.addNumAttr(rootCtrlShp, 'spread_mult', 'double', hide=False, dv=SPREAD_MULT)
		
		for i, grp in enumerate(self.ctrlBendGrps):
			_numName = (self.elem, i+1, self.side)
			spreadAttr = misc.addNumAttr(self.rootCtrl, 'spread%s' %(i+1), 'double', hide=False)
			
			spreadMdl = pm.createNode('multDoubleLinear', n='%sSpread%s%s_mdl' %_numName)
			
			pm.connectAttr(spreadAttr, spreadMdl.input1)
			pm.connectAttr(spreadMultAttr, spreadMdl.input2)
			pm.connectAttr(spreadMdl.output, grp.attr('r%s' %self.upAxis))

			spreadMultAttr.setKeyable(False)
			spreadMultAttr.showInChannelBox(True)

		# - connect twist
		sepAttr = misc.addNumAttr(self.rootCtrl, '__twist__', 'double', hide=False)
		sepAttr.lock()
		sepShpAttr = misc.addNumAttr(rootCtrlShp, '__twist__', 'double', hide=False)
		sepShpAttr.lock()
		twistMultAttr = misc.addNumAttr(rootCtrlShp, 'twist_mult', 'double', hide=False, dv=TWIST_MULT)
		

		for i, grp in enumerate(self.ctrlTwstGrps):
			_numName = (self.elem, i+1, self.side)
			twistAttr = misc.addNumAttr(self.rootCtrl, 'twist%s' %(i+1), 'double', hide=False)
			
			twistMdl = pm.createNode('multDoubleLinear', n='%sTwist%s%s_mdl' %_numName)

			pm.connectAttr(twistAttr, twistMdl.input1)
			pm.connectAttr(twistMultAttr, twistMdl.input2)
			pm.connectAttr(twistMdl.output, grp.attr('r%s' %self.aimAxis))

			twistMultAttr.setKeyable(False)
			twistMultAttr.showInChannelBox(True)

		# - connect stretch
		for i, pma in enumerate(stretchPmas[1:]):
			pm.connectAttr(self.rootCtrl.stretch, pma.input1D.input1D[2])

		# - connect squash
		for i, pma in enumerate(squashPmas[1:]):
			pm.connectAttr(self.rootCtrl.squash, pma.input1D.input1D[2])

		

		# --- parent to main groups
		pm.parent(self.rigCtrlGrp, self.animGrp)

		if self.doPostureRig and self.postureCtrl:
			sepAttr = misc.addNumAttr(self.postureCtrl, '__%s__' %self.postureElem, 'double', hide=False)
			sepAttr.lock()
			postureCtrlShp = self.postureCtrl.getShape()

			posePmas = []
			for i, grp in enumerate(self.ctrlSdkGrps):
				posePma = pm.createNode('plusMinusAverage', n='%s%s%s_pma' %(self.elem, i+1, self.side))
				pm.connectAttr(posePma.output3Dx, grp.rx)
				pm.connectAttr(posePma.output3Dy, grp.ry)
				pm.connectAttr(posePma.output3Dz, grp.rz)
				posePmas.append(posePma)

			axisDict = {'bend':self.bendAxis, 'side':self.upAxis, 'twist':self.aimAxis}
			for pose in sorted(self.poses.keys()):
				valDict = self.poses[pose]
				poseTitle = '%s%s' %(pose[0].upper(), ''.join(pose[1:]))
				misc.addNumAttr(self.postureCtrl, pose, 'double', hide=False)

				sepAttr = misc.addNumAttr(postureCtrlShp, '__%s__' %self.elem, 'double', hide=False)
				sepAttr.lock()

				for k in sorted(valDict.keys()):
					v = valDict[k]
					axName = k[0:-1]
					i = int(k[-1]) - 1
					axis = axisDict[axName]
					axisUpr = axis.upper()

					poseMdv = pm.createNode('multiplyDivide', n='%s%s%s%s_mdv' %(self.elem, i+1, poseTitle, self.side))
					latestIndex = posePmas[i].input3D.evaluateNumElements()

					multAttr = misc.addNumAttr(postureCtrlShp, '%s%s%s%s_mult' %(self.elem, i+1, poseTitle, axName.title()), 
						'double', hide=False, dv=v)
					multAttr.setKeyable(False)
					multAttr.showInChannelBox(True)

					pm.connectAttr(self.postureCtrl.attr(pose), poseMdv.attr('input1%s' %axisUpr))
					pm.connectAttr(multAttr, poseMdv.attr('input2%s' %axisUpr))
					pm.connectAttr(poseMdv.attr('output%s' %axisUpr), posePmas[i].input3D[latestIndex].attr('input3D%s' %axis))

		# constraint to parent transform
		if self.parent:
			pm.parentConstraint(self.parent, self.rigCtrlGrp, mo=True)
			# pm.scaleConstraint(self.parent, self.rigCtrlGrp, mo=True)

		pm.parent(self.jnts[0], self.rigUtilGrp)
		pm.parent(self.rigUtilGrp, self.utilGrp)
