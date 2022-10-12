# import maya.cmds as mc
import pymel.core as pm

from nuTools import misc, controller
reload(misc)
reload(controller)
import nuTools.rigTools.singleJntRig as singleJntRig
# reload(singleJntRig)

class DoubleJntRig(singleJntRig.SingleJntRig):
	def __init__(self, 
				jnts=[],
				aimAxis='y',
				addGimbal=True,
				ctrlShp='crossCircle',
				ctrlColor='red', 
				cons=['parent', 'scale'],
				localWorldRig=False,
				doStretch=True,
				addScaJnt=True,
				worldOrient=True,
				**kwargs):
		super(DoubleJntRig, self).__init__(jnts=jnts,
				addGimbal=addGimbal,
				ctrlShp=ctrlShp,
				ctrlColor=ctrlColor, 
				cons=cons, 
				**kwargs)
		
		self.aimAxis = aimAxis
		self.scaJnts = None
		self.localWorldRig = localWorldRig
		self.doStretch = doStretch
		self.addScaJnt = addScaJnt
		self.worldOrient = worldOrient

	def rig(self):
		# --- get class name to use for naming
		_name = (self.elem, self.side)

		# --- create main groups
		self.rigCtrlGrp = pm.group(em=True, n='%sRig%s_grp' %_name)
		self.rigUtilGrp = pm.group(em=True, n='%sUtil%s_grp' %_name)

		# --- create the joint
		# baseJnt = pm.createNode('joint', n='%s1%s_jnt' %_name)
		baseJnt = self.tmpJnts[0].duplicate(po=True, n='%s1%s_jnt' %_name)[0]
		misc.snapTransform('parent', self.tmpJnts[0], baseJnt, False, True)
		baseJnt.radius.set(self.tmpJnts[0].radius.get())
		pm.makeIdentity(baseJnt, apply=True)

		if self.addScaJnt:
			scaJnt = pm.duplicate(baseJnt, po=True, n='%s1Sca%s_jnt' %_name)[0]
			scaJnt.radius.set(baseJnt.radius.get()*2)
			pm.parent(scaJnt, baseJnt)

		# tipJnt = pm.createNode('joint', n='%s2%s_jnt' %_name)
		tipJnt = self.tmpJnts[1].duplicate(po=True, n='%s2%s_jnt' %_name)[0]
		misc.snapTransform('parent', self.tmpJnts[1], tipJnt, False, True)
		tipJnt.radius.set(self.tmpJnts[1].radius.get())
		pm.makeIdentity(tipJnt, apply=True)

		pm.parent(tipJnt, baseJnt)
		self.jnts = [baseJnt, tipJnt]

		# --- create the controller
		self.ctrl = controller.JointController(name='%s%s_ctrl' %_name, 
					st=self.ctrlShp, scale=(self.size))
		self.ctrl.setColor(self.ctrlColor)
		self.ctrl.rotateOrder.set(self.rotateOrder)
		

		toCons = self.ctrl
		if self.addGimbal == True:
			self.gimbalCtrl = self.ctrl.addGimbal()
			toCons = self.gimbalCtrl

		self.ctrlZgrp = misc.zgrp(self.ctrl, element='Zro', suffix='grp', preserveHeirachy=True)[0]

		pm.parent(self.ctrlZgrp, self.rigCtrlGrp)

		# --- add stretch
		if self.doStretch:
			ctrlShp = self.ctrl.getShape(ni=True)
			aimAxisAttr = self.jnts[1].attr('t%s' %self.aimAxis)
			defaultLenValue = aimAxisAttr.get()
			stretchAttr = misc.addNumAttr(self.ctrl, 'stretch', 'double', dv=0)
			# stretchAmpAttr = misc.addNumAttr(ctrlShp, 'stretchAmp', 'double', dv=0.1)
			defaultLenAttr = misc.addNumAttr(ctrlShp, 'defaultLen', 'double', dv=defaultLenValue)

			stretchMdl = pm.createNode('multDoubleLinear', n='%sStretch%s_mdl' %_name)
			stretchAdl = pm.createNode('addDoubleLinear', n='%sStretch%s_adl' %_name)
			pm.connectAttr(stretchAttr, stretchMdl.input1)
			pm.connectAttr(defaultLenAttr, stretchMdl.input2)
			pm.connectAttr(defaultLenAttr, stretchAdl.input1)
			pm.connectAttr(stretchMdl.output, stretchAdl.input2)
			pm.connectAttr(stretchAdl.output, aimAxisAttr)

			# hide attrs
			# stretchAmpAttr.setKeyable(False)
			# stretchAmpAttr.showInChannelBox(False)
			defaultLenAttr.setKeyable(False)
			defaultLenAttr.showInChannelBox(False)

		# --- do local world
		if self.localWorldRig:
			self.ctrlSpaceGrp = misc.zgrp(self.ctrl, element='Space', suffix='grp', preserveHeirachy=True)[0]
			misc.createLocalWorld(objs=[self.ctrl, self.localWorldRig[1], self.localWorldRig[2], self.ctrlSpaceGrp], 
								constraintType=self.localWorldRig[0], attrName='localWorld')

		# snap zgrp
		if self.worldOrient == True:
			misc.snapTransform('point', baseJnt, self.ctrlZgrp, False, True)
			misc.snapTransform('orient', baseJnt, self.ctrl, False, True)

			pm.makeIdentity(self.ctrl, apply=True, t=True, r=True, s=True)
		else:
			misc.snapTransform('parent', baseJnt, self.ctrlZgrp, False, True)

		for c in self.cons:
			consChild = baseJnt
			if c == 'scale' and self.addScaJnt == True:
				consChild = scaJnt
			self.constraints[c] = misc.snapTransform(c, toCons, consChild, False, False)

		# lock hide attrs on controller
		tVal = True
		if 'parent' in self.cons or 'point' in self.cons:
			tVal = False

		rVal = True
		if 'parent' in self.cons or 'orient' in self.cons:
			rVal = False

		sVal = True
		if 'scale' in self.cons:
			sVal = False

		toLockHide = {'t':tVal, 'r':rVal, 's':sVal, 'v':True}
		misc.lockAttr(self.ctrl, **toLockHide)
		misc.hideAttr(self.ctrl, **toLockHide)

		# --- connect to parent
		if self.parent:
			pm.parentConstraint(self.parent, self.rigCtrlGrp, mo=True)
		pm.parent(self.rigCtrlGrp, self.animGrp)

		pm.parent(baseJnt, self.rigUtilGrp)
		pm.parent(self.rigUtilGrp, self.utilGrp)
		
