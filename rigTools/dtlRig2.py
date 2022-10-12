import pymel.core as pm
import maya.OpenMaya as om
import maya.mel as mel
from nuTools import misc as misc
from nuTools import controller as ctr
import nuTools.rigTools.baseRig as baseRig

reload(misc)
reload(baseRig)

class DtlRig2(baseRig.BaseRig):

	def __init__(self, parent, surf=None, wrapMesh=None, skinMesh=None, 
				 num=14, paramVOffset=2, paramU=0.0,
				 ctrlColor='lightBlue', ctrlShape='sphere',
				 animGrp=None, utilGrp=None, skinGrp=None, stillGrp=None, **kwArgs):
		super(DtlRig2, self).__init__(parent, animGrp=animGrp, utilGrp=utilGrp, skinGrp=skinGrp, stillGrp=stillGrp, **kwArgs)

		self.surf = surf
		self.wrapMesh = wrapMesh
		self.skinMesh = skinMesh
		self.num = num
		self.paramVOffset = paramVOffset
		self.paramU = paramU
		self.parent = parent

		self.ctrlColor = ctrlColor
		self.ctrlShape = ctrlShape


	def rig(self):
		size = [self.size, self.size, self.size]

		# attach joints to surface
		paramv = 0
		# ctrl grp 
		ctrlGrp = pm.group(em=True, n='%sDtl%s_grp' %(self.elem, self.side))

		# wrap
		pm.select([self.surf, self.wrapMesh], r=True)
		mel.eval('CreateWrap;')
		wrapNode = pm.listConnections(self.surf.getShape(ni=True), s=True, d=False, type='wrap')[0]
		wrapNode.rename('%sDtlSurf%s_wrap' %(self.elem, self.side))

		# bsh wrapMesh to skinMesh
		if not [n for n in self.skinMesh.listHistory() if n.type() == 'blendShape']:
			pm.blendShape(self.wrapMesh, self.skinMesh, foc=True, w=(0, 1.0), o='local', n='%sInverseSkin%s_bsh' %(self.elem, self.side))

		# holder jnt
		hjnt = pm.createNode('joint', n='%sHolderPos%s_jnt' %(self.elem, self.side))
		hjnt.radius.set(self.size)
		# hjnt.visibility.set(False)

		hzgrp = misc.zgrp(hjnt, suffix='grp', element='Zro', preserveHeirachy=True)[0]
		misc.snapTransform('parent', self.parent, hzgrp, False, False)
		# misc.snapTransform('scale', self.skinGrp, hzgrp, True, False)
		pm.parent(hzgrp, ctrlGrp)

		jnts = [hjnt]
		posGrps = [hzgrp]
		for n in range(self.num):
			counterStr = str(n+1).zfill(2)
			pos = pm.createNode('pointOnSurfaceInfo', n='%sDtl%s%s_posi' %(self.elem, counterStr,  self.side))

			pos.parameterU.set(self.paramU)
			pos.parameterV.set(paramv)
			paramv += self.paramVOffset

			jnt = pm.createNode('joint', n='%sDtl%s%s_jnt' %(self.elem, counterStr, self.side))
			jnt.radius.set(self.size)
			# jnt.visibility.set(False)
			ctrlName = '%sDtl%s%s_ctrl' %(self.elem, counterStr, self.side)
			ctrl = ctr.Controller(n=ctrlName, st=self.ctrlShape, scale=self.size)
			ctrl.setColor(self.ctrlColor)
			ctrl.lockAttr(v=True)
			ctrl.hideAttr(v=True)

			pm.parent(jnt, ctrl)

			zgrp = misc.zgrp(ctrl, suffix='grp', element='Zro', preserveHeirachy=True)[0]
			posGrp = misc.zgrp(zgrp, suffix='grp', element='Pos', preserveHeirachy=True)[0]

			pm.connectAttr(self.surf.getShape(ni=True).worldSpace, pos.inputSurface)
			pm.connectAttr(pos.position, posGrp.translate)

			aimNode = pm.createNode('aimConstraint', n='%sDtl%s%s_aimCons' %(self.elem, counterStr,  self.side))
			aimNode.aimVectorX.set(0)
			aimNode.aimVectorY.set(0)
			aimNode.aimVectorZ.set(1)
			aimNode.upVectorX.set(0)
			aimNode.upVectorY.set(1)
			aimNode.upVectorZ.set(0)
			aimNode.worldUpType.set(3)
			pm.connectAttr(pos.tangentU, aimNode.worldUpVector)
			pm.connectAttr(pos.normal, aimNode.target[0].targetTranslate)

			pm.connectAttr(aimNode.constraintRotateX, posGrp.rotateX)
			pm.connectAttr(aimNode.constraintRotateY, posGrp.rotateY)
			pm.connectAttr(aimNode.constraintRotateZ, posGrp.rotateZ)

			# misc.snapTransform('scale', self.skinGrp, posGrp, True, False)
			pm.parent(aimNode, posGrp)

			# add attr to surf to fine tune u and v param 
			uattr = misc.addNumAttr(self.surf.getShape(ni=True), 'u%s_param' %(n+1), 'float', dv=self.paramU)
			vattr = misc.addNumAttr(self.surf, 'v%s_param' %(n+1), 'float', dv=paramv)

			pm.connectAttr(uattr, pos.parameterU)
			pm.connectAttr(vattr, pos.parameterV)

			pm.parent(posGrp, ctrlGrp)
			jnts.append(jnt)
			posGrps.append(posGrp)

		# bind skin
		skc = misc.findRelatedSkinCluster(self.skinMesh)
		if not skc:
			skc = pm.skinCluster(jnts, self.skinMesh, n='%sDtl%s_skinCluster' %(self.elem, self.side))
		else:
			pm.skinCluster(skc, e=True, ai=jnts)

		# connect invertMatrix to skin cluster
		for jnt, posGrp in zip(jnts, posGrps):
			cons = jnt.worldMatrix[0].outputs(type='skinCluster', p=True)
			indx = None
			for i in cons:
				if i.node().nodeName() == skc.nodeName():
					indx = i.logicalIndex()
					pm.connectAttr(posGrp.worldInverseMatrix[0], skc.bindPreMatrix[indx], f=True)
					break
