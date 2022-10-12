import pymel.core as pm
import maya.OpenMaya as om
from nuTools import misc, config, controller
import nuTools.rigTools.baseRig as baseRig

reload(misc)
reload(config)
reload(controller)
reload(baseRig)

#reload(bRig)


class FollicleJntRig(baseRig.BaseRig):

	def __init__(self, loftCurves=[], uCount=8, vCount=1, offset=0, createCtrl=False, keepHistory=False,
				 animGrp=None, utilGrp=None, skinGrp=None, stillGrp=None):
		super(FollicleJntRig, self).__init__(animGrp=animGrp, utilGrp=utilGrp, skinGrp=skinGrp, stillGrp=stillGrp)

		self.uCount = uCount
		self.vCount = vCount
		self.offset = offset

		self.curves = loftCurves
		self.createCtrl = createCtrl
		self.keepHistory = keepHistory


	def rig(self):
		# if no anim, still and skin grp, create
		posCtrlGrp = None
		if self.createCtrl == True:
			if not self.animGrp:
				self.animGrp = pm.group(em=True, n='%s%sCtrl_grp' %(self.elem, self.side))
			posCtrlGrp = pm.group(em=True, n='%sPosCtrl%s_grp' %(self.elem, self.side))
			pm.parent(posCtrlGrp, self.animGrp)

		if not self.stillGrp:
			self.stillGrp = pm.group(em=True, n='%s%sStill_grp' %(self.elem, self.side))
		self.stillGrp.visibility.set(False)

		if not self.skinGrp:
			self.skinGrp = pm.group(em=True, n='%s%sSkin_grp' %(self.elem, self.side))

		posFolGrp = pm.group(em=True, n='%sPosFol%s_grp' %(self.elem, self.side))
		pm.parent(posFolGrp, self.stillGrp)

		posJntGrp = pm.group(em=True, n='%sPosJnt%s_grp' %(self.elem, self.side))
		pm.parent(posJntGrp, self.skinGrp)

		# loft curves
		degree = self.curves[0].getShape(ni=True).degree()
		surface = pm.loft(self.curves, degree=degree, ch=self.keepHistory)[0]

		# create follicles

		folDict = misc.attatchFollicleToSurface(surface=surface, uCount=self.uCount, vCount=self.vCount, ctrlColor='navyBlue',
									  name='%s%s' %(self.elem, self.side), createJnt=True, createCtrl=self.createCtrl, 
									  size=self.size, folGrp=posFolGrp, utilGrp=posJntGrp, ctrlGrp=posCtrlGrp, offset=self.offset)


		# parent to group
		pm.parent(surface, self.stillGrp)
		











		