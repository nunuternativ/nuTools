import maya.cmds as mc
from maya.api import OpenMaya as om
import pymel.core as pm

from nuTools import misc, controller
reload(misc)
reload(controller)
import nuTools.rigTools.baseRig as baseRig
reload(baseRig)


class SkirtVectorRig(baseRig.BaseRig):
	def __init__(self, 
				jnts=[],
				coreJnt=None,
				parent=None,
				aimAxis='y',
				bendAxis='x',
				**kwargs):
		super(SkirtVectorRig, self).__init__(**kwargs)

		self.tmpJnts = self.jntsArgs(jnts)
		self.coreJnt = self.jntsArgs(coreJnt)

		self.parent = parent
		self.aimAxis = aimAxis
		self.bendAxis = bendAxis

	def rig(self):
		elemSide = (self.elem, self.side)

		# create orig leg locs
		self.origBaseLoc = pm.spaceLocator(n='%sOrigBase%s_loc' %elemSide)
		self.origTipLoc = pm.spaceLocator(n='%sOrigTip%s_loc' %elemSide)

		misc.snapTransform('parent', coreJnt, self.origBaseLoc, False, True)
		misc.snapTransform('parent', self.origBaseLoc, self.origTipLoc, False, True)
		pm.xform(self.origTipLoc, r=True, t=)
		
