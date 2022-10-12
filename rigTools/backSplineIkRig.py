import pymel.core as pm
import maya.mel as mel
import maya.OpenMaya as om
from nuTools import misc, config, controller
import nuTools.rigTools.baseRig as baseRig

reload(misc)
reload(config)
reload(controller)
reload(baseRig)


class BackSplineIkRig(baseRig.BaseRig):

	def __init__(self, parent=None, jnts=[], numJnt=5, pin='base', ctrlShp='roundSquare',
		animGrp=None, skinGrp=None, stillGrp=None):
		super(BackSplineIkRig, self).__init__(parent=parent, animGrp=animGrp, skinGrp=skinGrp, stillGrp=stillGrp)
		
		self.jnts = jnts

		if numJnt < 3:
			om.MGlobal.displayWarning('Number of splineIk joint must NOT less than 3.')
			numJnt = 3
		self.numJnt = numJnt

		self.ctrlShp = ctrlShp

		self.crv = None
		self.origCrv = None
		self.ikHndl = None
		self.spJnts = []
		self.ctrls = []
		self.zgrps = []

		self._PIN = pin



	def rig(self):
		if self._PIN == 'base':
			if len(self.jnts) < 3:
				om.MGlobal.displayWarning('Number of joint must NOT less than 3.')
				return

			self.rig_base()

		elif self._PIN == 'both':
			self.rig_both()



	def rig_base(self):
		# create crv
		numFkJnt = len(self.jnts)
		kRange = range(0, numFkJnt)
		cmd = 'self.crv = pm.curve(d=1, p=['
		i = 0
		prevCtrl = None
		for jnt in self.jnts:
			num = str(i+1).zfill(2)
			jnt.rename('%s%s%s_jnt' %(self.elem, num, self.side))


			# draw crv
			position = pm.xform(jnt, q=True, ws=True, t=True)
			positionStr = str('[%s, %s, %s]'%(position[0], position[1], position[2]))
			cmd += positionStr
			if jnt != self.jnts[-1]:
				cmd += ', '

			

			if i < numFkJnt-1:
				# create ctrl
				ctrl = controller.Controller(name='%s%s%s_ctrl' %(self.elem, num, self.side), 
					st=self.ctrlShp, scale=(self.size*3.0), axis='+y')
				ctrl.setColor('yellow')
				if i > 0:	
					ctrl.lockAttr(s=True, v=True)
					ctrl.hideAttr(s=True, v=True)
				else:
					ctrl.lockAttr(v=True)

				zgrp = misc.zgrp(ctrl)[0]
				misc.snapTransform('parent', jnt, zgrp, False, True)
				misc.snapTransform('parent', ctrl, jnt, True, False)
				misc.snapTransform('scale', ctrl, jnt, True, False)

				if prevCtrl:
					pm.parent(zgrp, prevCtrl)
				self.ctrls.append(ctrl)
				self.zgrps.append(zgrp)

			i += 1
			prevCtrl = ctrl

		numCtrl = len(self.ctrls)
		

		# create curve
		cmd += '], k=%s)' %kRange
		exec(cmd)
		pm.rebuildCurve(self.crv, ch=False, rpo=True, rt=0, end=True, kr=False,
			kcp=False, kep=True, kt=False, s=self.numJnt-2, d=3, tol=0.075)
		self.crv.rename('%sSplineIk%s_crv' %(self.elem, self.side))

		# craete orig curve
		self.origCrv = pm.duplicate(self.crv)[0]
		self.origCrv.rename('%sSplineIkOrig%s_crv' %(self.elem, self.side))
		self.origCrv.visibility.set(0)

		# create spline jnts
		self.spJnts = misc.createJntAlongCurve(self.numJnt, crv=self.crv, jointOrient='xyz', 
			elem='%sSpIk' %self.elem, side=self.side, radius=self.size * 0.334)

		self.bindSplineCrv()

		# create spline ik
		self.createSplineIk()
		
		# make squash stretch
		self.connectSqStNodes()
			
		# clean up
		ctrlGrp = pm.group(em=True, n='%sCtrl%s_grp' %(self.elem, self.side))
		pm.parent(self.zgrps[0], ctrlGrp)
		pm.parent(self.origCrv, ctrlGrp)
		if self.animGrp:
			pm.parent(ctrlGrp, self.animGrp)

		skinGrp = pm.group(em=True, n='%sSkin%s_grp' %(self.elem, self.side))
		pm.parent(self.spJnts[0], skinGrp)
		misc.snapTransform('scale', self.ctrls[0], skinGrp, True, False)
		if self.skinGrp:
			pm.parent(skinGrp, self.skinGrp)

		stillGrp = pm.group(em=True, n='%sStill%s_grp' %(self.elem, self.side))
		stillGrp.visibility.set(False)
		pm.parent([self.ikHndl, self.crv], stillGrp)
		if self.stillGrp:
			pm.parent(stillGrp, self.stillGrp)

		if self.parent:
			try:
				misc.snapTransform('parent', self.parent, self.zgrps[0], True, False)
				misc.snapTransform('scale', self.parent, self.zgrps[0], True, False)
			except:
				om.MGlobal.displayWarning('Cannot constraint to parent!')



	def rig_both(self):
		# create crv
		numFkJnt = len(self.jnts)
		kRange = range(0, numFkJnt)
		cmd = 'self.crv = pm.curve(d=1, p=['
		i = 0
		# prevCtrl = None
		for jnt in self.jnts:
			num = str(i+1).zfill(2)
			jnt.rename('%s%s%s_jnt' %(self.elem, num, self.side))


			# draw crv
			position = pm.xform(jnt, q=True, ws=True, t=True)
			positionStr = str('[%s, %s, %s]'%(position[0], position[1], position[2]))
			cmd += positionStr
			if jnt != self.jnts[-1]:
				cmd += ', '

			# if i < numFkJnt-1:
			# create ctrl
			ctrl = controller.Controller(name='%s%s%s_ctrl' %(self.elem, num, self.side), 
				st=self.ctrlShp, scale=(self.size*3.0), axis='+y')
			ctrl.setColor('yellow')

			ctrl.lockAttr(s=True, v=True)
			ctrl.hideAttr(s=True, v=True)

			zgrp = misc.zgrp(ctrl)[0]
			misc.snapTransform('parent', jnt, zgrp, False, True)
			misc.snapTransform('parent', ctrl, jnt, True, False)
			misc.snapTransform('scale', ctrl, jnt, True, False)

			# if prevCtrl:
			# 	pm.parent(zgrp, prevCtrl)
			self.ctrls.append(ctrl)
			self.zgrps.append(zgrp)

			i += 1
			# prevCtrl = ctrl

		numCtrl = len(self.ctrls)
		

		for i in range(numCtrl)[1:-1]:
			num = str(i+1).zfill(2)
			consNode = pm.parentConstraint([self.ctrls[0], self.ctrls[-1]], self.zgrps[i], mo=True)

			defultValue =  float(i) / float(numCtrl - 1)

			followAttr = misc.addNumAttr(self.ctrls[i], 'follow', 'float', min=0, max=1, dv=defultValue)
			revNode = pm.createNode('reverse', n='%s%s%s_rev' %(self.elem, num, self.side))

			pm.connectAttr(followAttr, revNode.inputX)
			pm.connectAttr(revNode.outputX, consNode.attr('%sW0' %self.ctrls[0].nodeName()))
			pm.connectAttr(followAttr, consNode.attr('%sW1' %self.ctrls[-1].nodeName()))


		# create curve
		cmd += '], k=%s)' %kRange
		exec(cmd)
		pm.rebuildCurve(self.crv, ch=False, rpo=True, rt=0, end=True, kr=False,
			kcp=False, kep=True, kt=False, s=self.numJnt-2, d=3, tol=0.075)
		self.crv.rename('%sSplineIk%s_crv' %(self.elem, self.side))

		# craete orig curve
		self.origCrv = pm.duplicate(self.crv)[0]
		self.origCrv.rename('%sSplineIkOrig%s_crv' %(self.elem, self.side))
		self.origCrv.visibility.set(0)

		# create spline jnts
		self.spJnts = misc.createJntAlongCurve(self.numJnt, crv=self.crv, jointOrient='xyz', 
			elem='%sSpIk' %self.elem, side=self.side, radius=self.size * 0.334)


		self.bindSplineCrv()

		# create spline ik
		self.createSplineIk()

		# make squash stretch
		self.connectSqStNodes()

		# clean up
		ctrlGrp = pm.group(em=True, n='%sCtrl%s_grp' %(self.elem, self.side))
		pm.parent(self.zgrps, ctrlGrp)
		pm.parent(self.origCrv, ctrlGrp)

		if self.animGrp:
			pm.parent(ctrlGrp, self.animGrp)

		skinGrp = pm.group(em=True, n='%sSkin%s_grp' %(self.elem, self.side))
		pm.parent(self.spJnts[0], skinGrp)
		misc.snapTransform('scale', self.ctrls[0], skinGrp, True, False)
		if self.skinGrp:
			pm.parent(skinGrp, self.skinGrp)


		stillGrp = pm.group(em=True, n='%sStill%s_grp' %(self.elem, self.side))
		stillGrp.visibility.set(False)
		pm.parent([self.ikHndl, self.crv], stillGrp)
		if self.stillGrp:
			pm.parent(stillGrp, self.stillGrp)

		if self.parent:
			try:
				misc.snapTransform('parent', self.parent, self.zgrps[0], True, False)
				misc.snapTransform('scale', self.parent, self.zgrps[0], True, False)
			except:
				om.MGlobal.displayWarning('Cannot constraint to parent!')



	def bindSplineCrv(self):
		# bind skin
		skinClusterNode = pm.skinCluster(self.jnts, self.crv, tsb=True, mi=3)

		# assign weight to curve
		crvShp = self.crv.getShape(ni=True)
		cvs = pm.PyNode('%s.cv[%s:%s]' %(crvShp.longName(), 0, crvShp.numCVs()-1))

		for cv in cvs:
			dists = {}
			distances = []
			cvPos = cv.getPosition(space='world')
			for jnt in self.jnts:
				distance = misc.getDistanceFromPosition(jnt.getTranslation(space='world'), cvPos)
				dists[distance] = jnt
			distances = sorted(dists.keys())[0:2]

			# unlock all jnts
			for jnt in self.jnts:
				skinClusterNode.setLockWeights(False, influence=jnt)

			# flood weight
			closestJntDist = distances[0]
			pm.skinPercent(skinClusterNode, cv, tv=(dists[closestJntDist], 1.0))

			# only unlock those first 3 jnts of interest
			for k, v in dists.iteritems():
				if k not in distances:
					skinClusterNode.setLockWeights(True, influence=v)

			weightValues = []
			sumDist = distances[0] + distances[1]

			for d in distances:
				if d == 0.00:
					weightValues = [1.0, 0.0]
					break
				else:
					weight = (1.0 / d)/sumDist
					weightValues.append(weight)

			sumWeightValues = weightValues[0] + weightValues[1]
			weightValues = [weightValues[0]/sumWeightValues, weightValues[1]/sumWeightValues]

			# assign weights
			for dist, weight  in zip(distances, weightValues):
				pm.skinPercent(skinClusterNode, cv, tv=(dists[dist], weight))
				if weight == 1.00:
					break
				skinClusterNode.setLockWeights(True, influence=dists[dist])



	def createSplineIk(self):
		self.ikHndl = pm.ikHandle(sj=self.spJnts[0], ee=self.spJnts[-1], c=self.crv, ccv=False,
			scv=False, roc=True, shf=True, tws='linear', cra=True, rtm=False, ce=True, pcv=False,
			sol='ikSplineSolver')[0]
		self.ikHndl.rename('%s%s_ikHndl' %(self.elem, self.side))
		self.ikHndl.attr('visibility').set(False)

		# advance twist
		self.ikHndl.dTwistControlEnable.set(True)
		self.ikHndl.dWorldUpType.set(4)
		self.ikHndl.dWorldUpAxis.set(1)

		self.ikHndl.dWorldUpVectorX.set(0)
		self.ikHndl.dWorldUpVectorY.set(0)
		self.ikHndl.dWorldUpVectorZ.set(1)

		self.ikHndl.dWorldUpVectorEndX.set(0)
		self.ikHndl.dWorldUpVectorEndY.set(0)
		self.ikHndl.dWorldUpVectorEndZ.set(1)

		pm.connectAttr(self.ctrls[0].worldMatrix[0], self.ikHndl.dWorldUpMatrix)
		pm.connectAttr(self.ctrls[-1].worldMatrix[0], self.ikHndl.dWorldUpMatrixEnd)



	def connectSqStNodes(self):
		crvInfo = pm.createNode('curveInfo', n='%s%s_crvInfo' %(self.elem, self.side))
		pm.connectAttr(self.crv.getShape(ni=True).worldSpace[0], crvInfo.inputCurve)

		origCrvInfo = pm.createNode('curveInfo', n='%sOrig%s_crvInfo' %(self.elem, self.side))
		pm.connectAttr(self.origCrv.getShape(ni=True).worldSpace[0], origCrvInfo.inputCurve)

		divScaleMdv = pm.createNode('multiplyDivide', n='%sDivScale%s_mdv' %(self.elem, self.side))
		divScaleMdv.operation.set(2)
		pm.connectAttr(crvInfo.arcLength, divScaleMdv.input1X)
		pm.connectAttr(origCrvInfo.arcLength, divScaleMdv.input2X)



		# make squashStretch
		autoStAttr = misc.addNumAttr(self.ctrls[0], 'autoStretch', 'float', dv=0.0, min=0.0, max=1.0)
		stSwitchBcol = pm.createNode('blendColors', n='%sAutoSt%s_bCol' %(self.elem, self.side))
		pm.connectAttr(divScaleMdv.outputX, stSwitchBcol.color1.color1R)
		pm.connectAttr(autoStAttr, stSwitchBcol.blender)
		stSwitchBcol.color2.color2R.set(1.0)


		sqStAttr = misc.addNumAttr(self.ctrls[0], 'squash', 'float', dv=0.0)

		autoSqAttr = misc.addNumAttr(self.ctrls[0], 'autoSquash', 'float', dv=0.0, min=0.0, max=1.0)
		autoSqSubPma = pm.createNode('plusMinusAverage', n='%sAutoSqSubtract%s_pma' %(self.elem, self.side))
		autoSqSubPma.operation.set(2)
		autoSqSubPma.input1D[0].set(1.0)
		pm.connectAttr(stSwitchBcol.output.outputR, autoSqSubPma.input1D[1])
		

		i = 0
		x = 0.0
		for jnt in self.spJnts:
			num = str(i+1).zfill(2)
			if i > 0:
				tx = jnt.tx.get()

				transMdl = pm.createNode('multDoubleLinear', n='%sTransMult%s%s_mdl' %(self.elem, num, self.side))
				transMdl.input2.set(tx)

				pm.connectAttr(stSwitchBcol.output.outputR, transMdl.input1)
				pm.connectAttr(transMdl.output, jnt.tx)

			defultValue = -4.0*(x**2) + (4.0*x)
			x += 1.0/float(self.numJnt-1)


			sqStAmpAttr = misc.addNumAttr(self.ctrls[0].getShape(ni=True), 'sqAmp%s'%num, 'float', dv=defultValue)

			autoSqMdl = pm.createNode('multDoubleLinear', n='%sAutoSqStAmp%s%s_mdl' %(self.elem, num, self.side))
			pm.connectAttr(autoSqSubPma.output1D, autoSqMdl.input1)
			pm.connectAttr(autoSqAttr, autoSqMdl.input2)


			sqAdl = pm.createNode('addDoubleLinear', n='%sSqSt%s%s_Adl' %(self.elem, num, self.side))
			pm.connectAttr(sqStAttr, sqAdl.input1)
			pm.connectAttr(autoSqMdl.output, sqAdl.input2)

			sqAmpMdl = pm.createNode('multDoubleLinear', n='%sSqStAmp%s%s_mdl' %(self.elem, num, self.side))
			pm.connectAttr(sqAdl.output, sqAmpMdl.input1)
			pm.connectAttr(sqStAmpAttr, sqAmpMdl.input2)

			sqAdl = pm.createNode('addDoubleLinear', n='%sSqSt%s%s_adl' %(self.elem, num, self.side))
			sqAdl.input2.set(1.0)
			pm.connectAttr(sqAmpMdl.output, sqAdl.input1)
			

			pm.connectAttr(sqAdl.output, jnt.sy)
			pm.connectAttr(sqAdl.output, jnt.sz)

			i += 1

