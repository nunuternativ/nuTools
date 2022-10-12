import maya.cmds as mc
import pymel.core as pm

from nuTools import misc, controller
reload(misc)
reload(controller)
import nuTools.rigTools.baseRig as baseRig
# reload(baseRig)

class SingleJntRig(baseRig.BaseRig):
	def __init__(self, 
				jnts=None,
				addGimbal=True,
				createJnt=True,
				localWorldRig=False,
				ctrlShp='crossCircle',
				ctrlColor='yellow', 
				cons=['parent', 'scale'],
				**kwargs):

		super(SingleJntRig, self).__init__(**kwargs)

		# temp joints
		self.tmpJnts = self.jntsArgs(jnts)

		# setting var
		self.addGimbal = addGimbal
		self.createJnt = createJnt
		self.ctrlShp = ctrlShp
		self.ctrlColor = ctrlColor
		self.cons = cons
		self.localWorldRig = localWorldRig

		self.jnts = None

		self.ctrl = None
		self.gimbalCtrl = None
		self.ctrlZgrp = None
		self.constraints = {}

		self.rigCtrlGrp = None
		self.rigSkinGrp = None

	def rig(self):
		# --- get class name to use for naming
		_name = (self.elem, self.side)

		# --- create main groups
		self.rigCtrlGrp = pm.group(em=True, n='%sRig%s_grp' %_name)

		# --- create the controller
		self.ctrl = controller.Controller(name='%s%s_ctrl' %_name, 
					st=self.ctrlShp, scale=(self.size))
		self.ctrl.setColor(self.ctrlColor)
		self.ctrl.rotateOrder.set(self.rotateOrder)

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

		toCons = self.ctrl
		if self.addGimbal == True:
			self.gimbalCtrl = self.ctrl.addGimbal()
			toCons = self.gimbalCtrl

		self.ctrlZgrp = misc.zgrp(self.ctrl, element='Zro', suffix='grp', preserveHeirachy=True)[0]
		pm.parent(self.ctrlZgrp, self.rigCtrlGrp)
		misc.snapTransform('parent', self.tmpJnts, self.ctrlZgrp, False, True)

		# --- create the joint
		if self.createJnt:
			self.rigUtilGrp = pm.group(em=True, n='%sUtil%s_grp' %_name)

			self.jnts = self.tmpJnts.duplicate(po=True, n='%s%s_jnt' %_name)[0]
			self.jnts.radius.set(self.tmpJnts.radius.get())
			pm.makeIdentity(self.jnts, apply=True)

			for c in self.cons:
				self.constraints[c] = misc.snapTransform(c, toCons, self.jnts, False, False)

			pm.parent(self.jnts, self.rigUtilGrp)
			pm.parent(self.rigUtilGrp, self.utilGrp)

		# --- do local world
		if self.localWorldRig:
			self.ctrlSpaceGrp = misc.zgrp(self.ctrl, element='Space', suffix='grp', preserveHeirachy=True)[0]
			misc.createLocalWorld(objs=[self.ctrl, self.localWorldRig[1], self.localWorldRig[2], self.ctrlSpaceGrp], 
								constraintType=self.localWorldRig[0], attrName='localWorld')
		
		# --- connect to parent
		if self.parent:
			pm.parentConstraint(self.parent, self.rigCtrlGrp, mo=True)
		pm.parent(self.rigCtrlGrp, self.animGrp)

		
