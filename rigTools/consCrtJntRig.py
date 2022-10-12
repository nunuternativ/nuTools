import pymel.core as pm
import maya.OpenMaya as om

from nuTools import misc, config, controller
import nuTools.rigTools.baseRig as baseRig

reload(misc)
reload(config)
reload(controller)
#reload(rigTools)
reload(baseRig)


class ConsCrtJntRig(baseRig.BaseRig):

	def __init__(self, parent=None, jnt=None, aimAxis='y', upAxis='x', offset=0.1,
				 animGrp=None, utilGrp=None, skinGrp=None, stillGrp=None):
		super(ConsCrtJntRig, self).__init__(parent=parent, animGrp=animGrp, utilGrp=utilGrp, skinGrp=skinGrp, stillGrp=stillGrp)
		
		self.aimAxis = aimAxis
		self.jnt = jnt
		self.upAxis = upAxis
		self.offset = abs(offset)



	def rig(self):
		aimVec = misc.vectorStr(self.aimAxis)

		# duplicate crt jnt
		crtJnt = pm.duplicate(self.jnt, po=True, n='%sCrt%s_jnt' %(self.elem, self.side))[0]
		# create crt skin jnt grp
		crtZgrp = misc.zgrp(crtJnt)	
		crtPgrp = misc.zgrp(crtJnt, suffix="pgrp", preserveHeirachy=True)
		
		# constraint to both the joint and the orig locator
		misc.snapTransform('point', self.jnt, crtPgrp, True, False)
		misc.snapTransform('orient', [self.jnt, self.parent], crtPgrp, True, False)


		# get up vector
		upVec = misc.vectorStr(self.upAxis)
		pm.move(crtJnt, list(upVec*self.offset), r=True, os=True)

		# get current crt jnt trans
		crtTransAttr = crtJnt.attr('t%s' %self.upAxis[-1])
		currTrans = crtTransAttr.get()

		# add crt mult attr to the parent jnt
		crtMultAttr = misc.addNumAttr(self.jnt, '%s%s_crtMult' %(self.elem, self.side), 'float', min=0, dv=0)

		# get rotate axis
		crossVec = aimVec.cross(upVec)
		roAxisStr = misc.strVector(crossVec)[-1]

		# make node connections
		multMdl = pm.createNode('multDoubleLinear', n='%sCrtMult%s_mdl' %(self.elem, self.side))
		pm.connectAttr(self.jnt.attr('r%s' %roAxisStr), multMdl.attr('input1'))

		# divide by 360
		divMdl = pm.createNode('multDoubleLinear', n='%sDivDeg%s_mdl' %(self.elem, self.side))
		divMdl.input2.set(0.00278)
		pm.connectAttr(crtMultAttr, divMdl.input1)
		pm.connectAttr(divMdl.output, multMdl.input2)

		revMdl = pm.createNode('multDoubleLinear', n='%sRev%s_mdl' %(self.elem, self.side))
		revMdl.input2.set(-1)
		pm.connectAttr(multMdl.output, revMdl.input1)

		cond = pm.createNode('condition', n='%sAbs%s_cond' %(self.elem, self.side))
		op = 4
		if currTrans < 0:
			op = 2
		cond.operation.set(op)

		cond.secondTerm.set(0)
		pm.connectAttr(multMdl.output, cond.firstTerm)
		pm.connectAttr(multMdl.output, cond.colorIfFalseR)
		pm.connectAttr(revMdl.output, cond.colorIfTrueR)

		transAdl = pm.createNode('addDoubleLinear', n='%sCrt%s_adl' %(self.elem, self.side))
		transAdl.input2.set(currTrans)
		pm.connectAttr(cond.outColorR, transAdl.input1)

		pm.connectAttr(transAdl.output, crtTransAttr)

		# clean up
		if self.skinGrp:
			pm.parent(crtZgrp, self.skinGrp)