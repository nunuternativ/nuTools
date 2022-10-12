import maya.cmds as mc
import pymel.core as pm

from nuTools import misc, controller
reload(misc)
reload(controller)
import nuTools.rigTools.baseRig as baseRig
# reload(baseRig)

class EyeBallRig(baseRig.BaseRig):
	def __init__(self, 
				jnts=[],  # [eyeJnt, eyeAimJnt]
				tipParent = [],  # [eyeCtrl parent, targetCtrl parent]

				aimAxis='+z',
				upAxis='+y',
				worldUpAxis='+y',
				ctrlShp='crossSphere',
				ctrlColor='lightBlue', 
				targetCtrlShp='locator',
				targetCtrlColor='lightBlue',
				
				softEyeValue=0.1,
				doEyeLid=True,
				**kwargs):

		super(EyeBallRig, self).__init__(**kwargs)

		# temp joints
		self.tmpJnts = self.jntsArgs(jnts) 
		self.tipParent = self.jntsArgs(tipParent)

		# setting var
		self.ctrlShp = ctrlShp
		self.ctrlColor = ctrlColor
		self.targetCtrlShp = targetCtrlShp
		self.targetCtrlColor = targetCtrlColor

		self.softEyeValue = softEyeValue
		self.doEyeLid = doEyeLid

		self.aimAxis = aimAxis
		self.upAxis = upAxis
		self.worldUpAxis = worldUpAxis

		self.jnts = None
		self.lidJnt = None

		self.ctrl = None
		self.ctrlZgrp = None
		self.targetCtrl = None
		self.targetCtrlZgrp = None

		self.rigCtrlGrp = None
		self.rigSkinGrp = None

	def rig(self):
		# --- get class name to use for naming
		_name = (self.elem, self.side)
		rad = self.tmpJnts[0].radius.get()

		# axis
		aimVec = misc.vectorStr(self.aimAxis)
		upVec = misc.vectorStr(self.upAxis)
		wUpVec = misc.vectorStr(self.worldUpAxis)

		# --- create main groups
		self.rigCtrlGrp = pm.group(em=True, n='%sRig%s_grp' %_name)
		self.rigUtilGrp = pm.group(em=True, n='%sUtil%s_grp' %_name)

		# --- create the joint
		self.jnts = self.tmpJnts[0].duplicate(po=True, n='%s%s_jnt' %_name)[0]
		self.jnts.radius.set(rad)
		pm.makeIdentity(self.jnts, apply=True)

		# --- create the controller
		self.ctrl = controller.Controller(name='%s%s_ctrl' %_name, 
					st=self.ctrlShp, scale=(self.size))
		self.ctrl.setColor(self.ctrlColor)
		self.ctrl.rotateOrder.set(self.rotateOrder)
		self.ctrlZgrp = misc.zgrp(self.ctrl, element='Zro', suffix='grp', preserveHeirachy=True)[0]
		misc.snapTransform('parent', self.jnts, self.ctrlZgrp, False, True)
		pm.parent(self.ctrlZgrp, self.rigCtrlGrp)

		# --- orient constraint
		misc.snapTransform('parent', self.ctrl, self.jnts, False, False)
		misc.snapTransform('scale', self.ctrl, self.jnts, False, False)
		

		# --- setup aim
		self.targetCtrl = controller.Controller(name='%sTarget%s_ctrl' %_name, 
					st=self.targetCtrlShp, scale=(self.size*0.3))
		self.targetCtrl.setColor(self.targetCtrlColor)
		self.targetCtrl.rotateOrder.set(self.rotateOrder)
		self.targetCtrlZgrp = misc.zgrp(self.targetCtrl, element='Zro', suffix='grp', preserveHeirachy=True)[0]
		misc.snapTransform('parent', self.jnts, self.targetCtrlZgrp, False, True)

		# pm.xform(self.targetCtrlZgrp, os=True, r=True, t=(aimVec*self.size*4))
		misc.snapTransform('point', self.tmpJnts[1], self.targetCtrlZgrp, False, True)
		pm.aimConstraint(self.targetCtrl, self.ctrlZgrp, aimVector=aimVec, upVector=upVec, 
					worldUpType='objectrotation', worldUpVector=wUpVec, worldUpObject=self.parent, mo=True)

		

		# eyelid
		if self.doEyeLid == True:
			self.lidJnt = self.jnts.duplicate(po=True, n='%sLid%s_jnt' %_name)[0]
			self.lidJnt.radius.set(rad*1.25)
			pm.makeIdentity(self.lidJnt, apply=True)
			
			pm.xform(self.lidJnt, os=True, r=True, t=(aimVec*self.size*0.0001))
			misc.snapTransform('point', self.ctrl, self.lidJnt, True, False)
			softEyeCons = misc.snapTransform('orient', [self.ctrl, self.parent], self.lidJnt, True, False)
			softEyeCons.interpType.set(2)
			misc.snapTransform('scale', self.ctrl, self.lidJnt, False, False)

			softEyeAttr = misc.addNumAttr(self.ctrl, 'softEye', 'double', min=0, max=1, dv=self.softEyeValue)
			misc.connectSwitchAttr(ctrlAttr=softEyeAttr, posAttr=softEyeCons.w0, negAttr=softEyeCons.w1, elem='%sSoftEye' %self.elem, side=self.side)

			pm.parent(self.lidJnt, self.rigUtilGrp)
			
		# --- ann pointer 
		annRets = misc.annPointer(pointFrom=self.ctrl, pointTo=self.targetCtrl, 
					ref=True, 
					nameParts={'elem':self.elem, 'pos':self.side}, 
					constraint=False)

		pm.parent(annRets['loc'], self.targetCtrl)
		pm.parent(annRets['ann'], self.ctrl)

		toLockHide = {'t':False, 'r':False, 's':False, 'v':True}
		misc.lockAttr(self.ctrl, **toLockHide)
		misc.hideAttr(self.ctrl, **toLockHide)

		toLockHide = {'t':False, 'r':True, 's':True, 'v':True}
		misc.lockAttr(self.targetCtrl, **toLockHide)
		misc.hideAttr(self.targetCtrl, **toLockHide)

		toLockHide = {'t':True, 'r':True, 's':True, 'v':True}
		misc.lockAttr(annRets['loc'], **toLockHide)
		misc.hideAttr(annRets['loc'], **toLockHide)
		misc.lockAttr(annRets['ann'], **toLockHide)
		misc.hideAttr(annRets['ann'], **toLockHide)

		# --- just parent everything into the hierarchy
		pm.parent(self.rigCtrlGrp, self.animGrp)
		pm.parent(self.jnts, self.rigUtilGrp)
		pm.parent(self.rigUtilGrp, self.utilGrp)

		if self.parent:
			pm.parentConstraint(self.parent, self.rigCtrlGrp, mo=True)

		if self.tipParent:	
			pm.parent(self.targetCtrlZgrp, self.tipParent)
			

