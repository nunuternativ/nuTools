# import maya.cmds as mc
import pymel.core as pm
import maya.OpenMaya as om

from nuTools import controller
reload(controller)
import nuTools.rigTools.baseRig as baseRig
reload(baseRig)

DEFAULT_CTRL_COLOR = 'yellow'
MASTER_CTRL_DEFAULT_SCALE = 3
PLACEMENT_CTRL_DEFAULT_SCALE = 2.5
OFFSET_CTRL_DEFAULT_SCALE = 1

class RigGrp(baseRig.BaseRig):
	def __init__(self, **kwargs):
		super(RigGrp, self).__init__(**kwargs)

	def init_from_grp(self, grp=None):
		pass

	def rig(self):
		# --- create groups
		self.rigGrp = pm.group(em=True, n='rig_grp')
		self.animGrp = pm.group(em=True, n='anim_grp')  # controllers store here
		self.skinGrp = pm.group(em=True, n='skin_grp')  # all the bind joints
		self.utilGrp = pm.group(em=True, n='util_grp')  # everything that has to go with the rig
		self.stillGrp = pm.group(em=True, n='still_grp')  # everything that stays at the origin

		# --- create controllers
		self.masterCtrl = controller.Controller(st='diamond', 
					n='master_ctrl', scale=MASTER_CTRL_DEFAULT_SCALE*self.size)
		self.placementCtrl = controller.Controller(st='roundCenterDirectionalArrow', 
					n='placement_ctrl', scale=PLACEMENT_CTRL_DEFAULT_SCALE*self.size)
		self.offsetCtrl = controller.Controller(st='oneDirectionFatArrow', 
					n='offset_ctrl', scale=OFFSET_CTRL_DEFAULT_SCALE*self.size)
		for ctrl in [self.masterCtrl, self.placementCtrl, self.offsetCtrl]:
			ctrl.setColor(DEFAULT_CTRL_COLOR)
			ctrl.rotateOrder.set(self.rotateOrder)

		# --- parent
		pm.parent(self.placementCtrl, self.masterCtrl)
		pm.parent(self.offsetCtrl, self.placementCtrl)
		pm.parent(self.masterCtrl, self.rigGrp)
		pm.parent(self.stillGrp, self.rigGrp)
		pm.parent([self.animGrp, self.skinGrp, self.utilGrp], self.offsetCtrl)