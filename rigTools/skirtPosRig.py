import pymel.core as pm
import maya.OpenMaya as om
from nuTools import misc, config, controller
import nuTools.rigTools.baseRig as baseRig

reload(misc)
reload(config)
reload(controller)
reload(baseRig)


class SkirtPosRig(baseRig.BaseRig):

	def __init__(self, tempRoot=None, parent=None, animGrp=None, jntGrp=None, skinGrp=None, stillGrp=None, uCount=3, vCount=8, offset=0):
		super(SkirtPosRig, self).__init__(parent=parent, animGrp=animGrp, jntGrp=jntGrp, skinGrp=skinGrp, stillGrp=stillGrp)

		self.rigTempRoot = tempRoot

		self.nodes = []
		self.loftNode = None
		self.surface = None
		self.hipLoc = None
		self.upLegLFTLoc = None
		self.upLegRHTLoc = None

		self.uCount = uCount
		self.vCount = vCount
		self.offset = offset

		self.analyzeTempRoot()


	def analyzeTempRoot(self):
		try:
			self.surfaces = self.rigTempRoot.surfaces.outputs()
			self.hipLoc = self.rigTempRoot.hip_loc.outputs()[0]
			self.upLegLFTLoc = self.rigTempRoot.upLegLFT_loc.outputs()[0]
			self.upLegRHTLoc = self.rigTempRoot.upLegRHT_loc.outputs()[0]
			self.nodes = self.rigTempRoot.nodes.outputs()
			self.loftNodes = self.rigTempRoot.loftNodes.outputs()
		except:
			om.MGlobal.displayError('Invalid Rig Template Root')


	def rig(self):
		# if no anim, still and skin grp, create
		if not self.animGrp:
			self.animGrp = pm.group(em=True, n='%s%sCtrl_grp' %(self.elem, self.side))

		if not self.stillGrp:
			self.stillGrp = pm.group(em=True, n='%s%sStill_grp' %(self.elem, self.side))
		self.stillGrp.visibility.set(False)

		if not self.skinGrp:
			self.skinGrp = pm.group(em=True, n='%s%sSkin_grp' %(self.elem, self.side))

		skinConsGrp = pm.group(em=True, n='%s%sSkinCons_grp' %(self.elem, self.side))
		pm.parent(skinConsGrp, self.skinGrp)

		pelvisConsGrp = pm.group(em=True, n='%s%sPelvisCons_grp' %(self.elem, self.side))
		pm.parent(pelvisConsGrp, self.animGrp)

		
		skinSurfGrp = pm.group(em=True, n='%sSkinSurf%s_grp' %(self.elem, self.side))
		buffSurfGrp = pm.group(em=True, n='%sBuffSurf%s_grp' %(self.elem, self.side))

		buffSurfGrp.visibility.set(False)
		pm.parent([skinSurfGrp, buffSurfGrp], self.stillGrp)

		#root ctrl
		rootCtrl = controller.Controller(name='%sRoot%s_ctrl' %(self.elem, self.side), st='crossCircle', axis='+y', scale=self.size*10)
		rootCtrl.setColor('lightBlue')
		rootCtrl.lockAttr(v=True)
		rootCtrl.hideAttr(v=True)
		rootCtrlZgrp = misc.zgrp(rootCtrl)

		#add posDetail vis ctrl attr
		rootCtrlShp = rootCtrl.getShape()
		misc.addNumAttr(rootCtrlShp, 'detail_vis', 'long', min=0, max=1, dv=1)

		misc.snapTransform('parent', self.hipLoc, rootCtrlZgrp, False, True)
		pm.parent(rootCtrlZgrp, pelvisConsGrp)

		#parent, scale cons skin_grp, jnt_grp to rootCtrl
		misc.snapTransform('parent', rootCtrl, skinConsGrp, True, False)
		misc.snapTransform('scale', rootCtrl, skinConsGrp, True, False)

		if self.parent:
			misc.snapTransform('parent', self.parent, rootCtrlZgrp, True, False )

		#left ctrl
		lftCtrl = controller.Controller(name='%sLeft%s_ctrl' %(self.elem, self.side), st='negStick', axis='+y', scale=self.size*8)
		lftCtrl.setColor('lightBlue')
		lftCtrl.lockAttr(v=True)
		lftCtrl.hideAttr(v=True)
		lftCtrlZgrp = misc.zgrp(lftCtrl)

		misc.snapTransform('parent', self.upLegLFTLoc, lftCtrlZgrp, False, True)
		pm.parent(lftCtrlZgrp, rootCtrl)

		#right ctrl
		rhtCtrl = controller.Controller(name='%sRight%s_ctrl' %(self.elem, self.side), st='posStick', axis='+y', scale=self.size*8)
		rhtCtrl.setColor('lightBlue')
		rhtCtrl.lockAttr(v=True)
		rhtCtrl.hideAttr(v=True)
		rhtCtrlZgrp = misc.zgrp(rhtCtrl)

		misc.snapTransform('parent', self.upLegRHTLoc, rhtCtrlZgrp, False, True)
		pm.parent(rhtCtrlZgrp, rootCtrl)

		# hip buffer jnt
		hipBuffJnt = pm.createNode('joint', n='%sHipBuff%s_jnt' %(self.elem, self.side))
		misc.snapTransform('parent', self.hipLoc, hipBuffJnt, False, True)
		hipBuffJnt.radius.set(self.size * 1.2)
		pm.makeIdentity(hipBuffJnt, a=True)
		pm.parent(hipBuffJnt, self.stillGrp)
		

		bufferSurfaces = []
		buffJnts = []
		buffCtrls = []

		posFolGrp = pm.group(em=True, n='%sPosFol%s_grp' %(self.elem, self.side))
		pm.parent(posFolGrp, self.stillGrp)

		posJntGrp = pm.group(em=True, n='%sPosJnt%s_grp' %(self.elem, self.side))
		pm.parent(posJntGrp, skinConsGrp)

		posCtrlGrp = pm.group(em=True, n='%sPosCtrl%s_grp' %(self.elem, self.side))
		pm.parent(posCtrlGrp, rootCtrl)
		pm.connectAttr(rootCtrlShp.attr('detail_vis'), posCtrlGrp.visibility, f=True)


		s = 0
		# create follicles
		for surf in self.surfaces:
			surfNumStr = str(s).zfill(1)
			folDict = misc.attatchFollicleToSurface(surface=surf, uCount=self.uCount, vCount=self.vCount, ctrlColor='navyBlue',
										  name='%s%s%s' %(self.elem, surfNumStr, self.side), createJnt=True, createCtrl=True, size=self.size, 
										  folGrp=posFolGrp, jntGrp=posJntGrp, ctrlGrp=posCtrlGrp, offset=self.offset)


			#connect detail vis
			
			#delete history
			pm.parent(surf, w=True)
			pm.delete(surf, ch=True)
			surf.overrideEnabled.set(False)

			#rename the surf
			surf.rename('%sSkin%s%s_nrbs' %(self.elem, surfNumStr, self.side))

			# duplicate buffer surface
			buffSurf = pm.duplicate(surf, n='%sBuffer%s%s_nrbs' %(self.elem, surfNumStr, self.side))[0]
			bufferSurfaces.append(buffSurf)

			# parent to group
			pm.parent(surf, skinSurfGrp)
			pm.parent(buffSurf, buffSurfGrp)
			

			#buffer jnts
			firstRowFols = folDict['folDict'][0]
			for i in range(len(firstRowFols)):
				numStr = str(i+1).zfill(2)
				
				# create buff jnt
				buffJnt = pm.createNode('joint', n='%sBuff%s%s_jnt' %(self.elem, numStr, self.side))
				misc.snapTransform('parent', firstRowFols[i], buffJnt, False, True)
				buffJnt.radius.set(self.size)
				pm.parent(buffJnt, hipBuffJnt)
				pm.makeIdentity(buffJnt, a=True)
				buffJnts.append(buffJnt)

				misc.addOffsetJnt(sels=[buffJnt], radMult=0.0)
				pm.makeIdentity(buffJnt, a=True)

				# create controller
				ctrl = controller.Controller(name='%sBase%s%s_ctrl' %(self.elem, numStr, self.side), st='arrowStick', axis='-y', scale=self.size)
				ctrl.setColor('lightBlue')
				ctrl.lockAttr(v=True)
				ctrl.hideAttr(v=True)
				ctrlZgrp = misc.zgrp(ctrl)

				misc.snapTransform('parent', firstRowFols[i], ctrlZgrp, False, True)

				pm.connectAttr(ctrl.translate, buffJnt.translate)
				pm.connectAttr(ctrl.rotate, buffJnt.rotate)
				pm.connectAttr(ctrl.scale, buffJnt.scale)

				#parent to ctrl
				currTrans = pm.xform(ctrlZgrp, q=True, ws=True, t=True)
				if currTrans[0] > 0:
					pm.parent(ctrlZgrp, lftCtrl)
				elif currTrans[0] < 0:
					pm.parent(ctrlZgrp, rhtCtrl)
				else:
					pm.parent(ctrlZgrp, rootCtrl)

			s += 1

		
		# create skin joints

		hipSkinJnt = pm.createNode('joint', n='%sHip%s_jnt' %(self.elem, self.side))
		misc.snapTransform('parent', self.hipLoc, hipSkinJnt, False, True)
		hipSkinJnt.radius.set(self.size)

		upLegSkinLftJnt = pm.createNode('joint', n='%sUpLegLeft%s_jnt' %(self.elem, self.side))
		misc.snapTransform('parent', self.upLegLFTLoc, upLegSkinLftJnt, False, True)
		upLegSkinLftJnt.radius.set(self.size)

		upLegSkinRhtJnt = pm.createNode('joint', n='%sUpLegRight%s_jnt' %(self.elem, self.side))
		misc.snapTransform('parent', self.upLegRHTLoc, upLegSkinRhtJnt, False, True)
		upLegSkinRhtJnt.radius.set(self.size)

		pm.parent([upLegSkinLftJnt, upLegSkinRhtJnt], hipSkinJnt)
		pm.parent(hipSkinJnt, skinConsGrp)
		pm.makeIdentity([hipSkinJnt, upLegSkinLftJnt, upLegSkinRhtJnt], a=True)

		# constraint to ctrl
		misc.snapTransform('parent', lftCtrl, upLegSkinLftJnt, False, False)
		misc.snapTransform('scale', lftCtrl, upLegSkinLftJnt, False, False)

		misc.snapTransform('parent', rhtCtrl, upLegSkinRhtJnt, False, False)
		misc.snapTransform('scale', rhtCtrl, upLegSkinRhtJnt, False, False)

		#value jnt
		upLegValueLftJnt = pm.duplicate(upLegSkinLftJnt, n='%sUpLegValueLeft%s_jnt' %(self.elem, self.side))[0]
		upLegValueRhtJnt = pm.duplicate(upLegSkinRhtJnt, n='%sUpLegValueRight%s_jnt' %(self.elem, self.side))[0]

		upLegValueLftJnt.radius.set(self.size * 1.2)
		upLegValueLftJnt.visibility.set(False)

		upLegValueRhtJnt.radius.set(self.size * 1.2)
		upLegValueRhtJnt.visibility.set(False)

		#create leg follow switching
		followLftAttr = misc.addNumAttr(lftCtrl, 'follow', 'float', min=0, max=1)
		consLftNode = misc.snapTransform('parent', [hipSkinJnt, upLegValueLftJnt], lftCtrlZgrp, True, False)
		posAttr = consLftNode.attr('%sW1' %upLegValueLftJnt.nodeName())
		negAttr = consLftNode.attr('%sW0' %hipSkinJnt.nodeName())

		misc.connectSwitchAttr(ctrlAttr=followLftAttr, 
							   posAttr=posAttr, 
							   negAttr=negAttr, 
							   elem='%s%s' %(self.elem, self.side))



		followRhtAttr = misc.addNumAttr(rhtCtrl, 'follow', 'float', min=0, max=1) 
		consRhtNode = misc.snapTransform('parent', [hipSkinJnt, upLegValueRhtJnt], rhtCtrlZgrp, True, False)
		posAttr = consRhtNode.attr('%sW1' %upLegValueRhtJnt.nodeName())
		negAttr = consRhtNode.attr('%sW0' %hipSkinJnt.nodeName())

		misc.connectSwitchAttr(ctrlAttr=followRhtAttr, 
							   posAttr=posAttr, 
							   negAttr=negAttr, 
							   elem='%s%s' %(self.elem, self.side))

		#create blendshape from buffer to skin surface grp
		bshNode = pm.blendShape(buffSurfGrp, skinSurfGrp, n='%sSurf%s_bsh' %(self.elem, self.side), w=[0, 1.0])


		# lastly, delete the tempRoot
		pm.delete(self.rigTempRoot)










		