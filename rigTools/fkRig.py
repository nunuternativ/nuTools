# import maya.cmds as mc
import pymel.core as pm

from nuTools import misc, controller
reload(misc)
reload(controller)
import nuTools.rigTools.singleJntRig as singleJntRig
# reload(singleJntRig)

class FkRig(singleJntRig.SingleJntRig):
	def __init__(self, 
				jnts=[],
				aimAxis='y',
				addGimbal=True,
				ctrlShp='crossCircle',
				ctrlColor='red',
				localWorldRig=False,
				doStretch=True,
				doSquash=True,
				**kwargs):
		super(FkRig, self).__init__(jnts=jnts,
				addGimbal=addGimbal,
				ctrlShp=ctrlShp,
				ctrlColor=ctrlColor, 
				**kwargs)

		self.aimAxis = aimAxis

		self.localWorldRig = localWorldRig
		self.doStretch = doStretch
		self.doSquash = doSquash
		self.ctrlShp = ctrlShp

		self.jnts = []
		self.tmpJnts = self.jntsArgs(jnts)
		self.scaJnts = []
		self.ctrls = []
		self.gCtrls = []
		self.ctrlZgrps = []
		self.ctrlOffsetGrps = []
		self.ctrlSpaceGrps = []

	def rig(self):
		# --- create main groups
		self.rigCtrlGrp = pm.group(em=True, n='%sRig%s_grp' %(self.elem, self.side))
		numJnt = len(self.tmpJnts)
		tAimAx = 't%s' %self.aimAxis[-1]
		sqshAxs = ['s%s'%a for a in 'xyz' if a!= self.aimAxis[-1]]

		for i in xrange(numJnt):
			# --- create the joint
			_iName = (self.elem, (i+1), self.side)
			# jnt = pm.createNode('joint', n='%s%s%s_jnt' %_iName)
			jnt = self.tmpJnts[i].duplicate(po=True, n='%s%s%s_jnt' %_iName)[0]
			misc.snapTransform('parent', self.tmpJnts[i], jnt, False, True)
			jnt.radius.set(self.tmpJnts[i].radius.get())
			pm.makeIdentity(jnt, apply=True)
			self.jnts.append(jnt)

			if self.doSquash:
				scaJnt = pm.duplicate(jnt, po=True, n='%s%sSca%s_jnt' %_iName)[0]
				scaJnt.radius.set(jnt.radius.get()*2)
				pm.parent(scaJnt, jnt)
				self.scaJnts.append(scaJnt)

			# if this is not the last joint
			if i != numJnt - 1:
				# --- create the controller
				ctrl = controller.Controller(name='%s%s%s_ctrl' %_iName, 
							st=self.ctrlShp, scale=(self.size))
				ctrl.setColor(self.ctrlColor)
				ctrl.rotateOrder.set(self.rotateOrder)
			
				toLockHide = {'t':False, 'r':False, 's':True, 'v':True}
				misc.lockAttr(ctrl, **toLockHide)
				misc.hideAttr(ctrl, **toLockHide)

				ctrlOffsetGrp = misc.zgrp(ctrl, element='Ofst', suffix='grp', preserveHeirachy=True)[0]
				ctrlSpaceGrp = misc.zgrp(ctrlOffsetGrp, element='Space', remove='Ofst', suffix='grp', preserveHeirachy=True)[0]
				ctrlZgrp = misc.zgrp(ctrlSpaceGrp, element='Zro', remove='Space', suffix='grp')[0]
				
				# snap zgrp
				misc.snapTransform('parent', jnt, ctrlZgrp, False, True)

				if i > 0:
					pm.parent(ctrlZgrp, toCons)
				else:
					pm.parent(ctrlZgrp, self.rigCtrlGrp)

				toCons = ctrl
				if self.addGimbal == True:
					gCtrl = ctrl.addGimbal()
					toCons = gCtrl
					self.gCtrls.append(gCtrl)

				# create constraint
				misc.snapTransform('parent', toCons, jnt, False, False)

				self.ctrls.append(ctrl)
				self.ctrlZgrps.append(ctrlZgrp)
				self.ctrlOffsetGrps.append(ctrlOffsetGrp)
				self.ctrlSpaceGrps.append(ctrlSpaceGrp)

				
			# parent jnt
			if i > 0:
				pm.parent(jnt, self.jnts[i-1])
		numCtrls = len(self.ctrls)
		# --- add stretch
		if self.doStretch:
			for i in xrange(numCtrls):
				_iName = (self.elem, (i+1), self.side)
				ctrlShp = self.ctrls[i].getShape(ni=True)

				if i != numCtrls - 1:
					aimAxisAttr = self.ctrlZgrps[i+1].attr(tAimAx)
				else:
					aimAxisAttr = self.jnts[i+1].attr(tAimAx)

				defaultLenValue = aimAxisAttr.get()
				stretchAttr = misc.addNumAttr(self.ctrls[i], 'stretch', 'double', dv=0)
				defaultLenAttr = misc.addNumAttr(ctrlShp, 'defaultLen', 'double', dv=defaultLenValue)

				stretchMdl = pm.createNode('multDoubleLinear', n='%sStretch%s%s_mdl' %_iName)
				stretchAdl = pm.createNode('addDoubleLinear', n='%sStretch%s%s_adl' %_iName)
				pm.connectAttr(stretchAttr, stretchMdl.input1)
				pm.connectAttr(defaultLenAttr, stretchMdl.input2)
				pm.connectAttr(defaultLenAttr, stretchAdl.input1)
				pm.connectAttr(stretchMdl.output, stretchAdl.input2)
				pm.connectAttr(stretchAdl.output, aimAxisAttr)

				# hide attrs
				defaultLenAttr.setKeyable(False)
				defaultLenAttr.showInChannelBox(False)

		# --- add squash
		if self.doSquash:
			for i in xrange(numCtrls):
				_iName = (self.elem, (i+1), self.side)

				squashAttr = misc.addNumAttr(self.ctrls[i], 'squash', 'double', dv=0)
				squashAdl = pm.createNode('addDoubleLinear', n='%sSquash%s%s_adl' %_iName)
				squashAdl.input2.set(1.0)
				pm.connectAttr(squashAttr, squashAdl.input1)
				for ax in sqshAxs:
					pm.connectAttr(squashAdl.output, self.scaJnts[i].attr(ax))

				if i == numCtrls - 1:
					squashTipAttr = misc.addNumAttr(self.ctrls[i], 'squashTip', 'double', dv=0)
					squashTipAdl = pm.createNode('addDoubleLinear', n='%sSquashTip%s_adl' %(self.elem, self.side))
					squashTipAdl.input2.set(1.0)
					pm.connectAttr(squashTipAttr, squashTipAdl.input1)
					for ax in sqshAxs:
						pm.connectAttr(squashTipAdl.output, self.scaJnts[i+1].attr(ax))

		# --- do local world
		if self.localWorldRig == True:
			misc.createLocalWorld(objs=[self.ctrls[0], self.rigCtrlGrp, self.animGrp, self.ctrlSpaceGrps[0]], 
								constraintType='orient', attrName='localWorld')

		# constraint to parent transform
		if self.parent:
			pm.parentConstraint(self.parent, self.rigCtrlGrp, mo=True)
			pm.scaleConstraint(self.parent, self.rigCtrlGrp, mo=True)
			pm.parent(self.jnts[0], self.parent)
		else:
			pm.parent(self.jnts[0], self.utilGrp)

		# --- parent to main groups
		pm.parent(self.rigCtrlGrp, self.animGrp)
