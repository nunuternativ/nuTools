import pymel.core as pm
import maya.mel as mel
import maya.OpenMaya as om
from nuTools import misc, config, controller
import nuTools.rigTools.baseRig as baseRig

# reload(misc)
# reload(config)
# reload(controller)
# reload(baseRig)

class SplineFkRig(baseRig.BaseRig):

	def __init__(self, jnts=[], ctrlJnts=[], degree=2,
				crv=None,
				aimAxis='+y', upAxis='+z', 
				ikAimAxis='+x', ikUpAxis='+z',
				ctrlShp='diamond', ctrlColor='yellow',
				dtlCtrlShp='doubleStick', dtlCtrlColor='lightBlue', 
				upCtrlShp='locator', upCtrlColor='lightBlue',
				createDtlCtrl=True, createUpCtrl=True,
				localWorldRig=True, doSquashStretch=True,
				**kwArgs):
		super(SplineFkRig, self).__init__(jnts=jnts, ctrJnts=ctrlJnts, **kwArgs)
		
		self.tmpJnts = self.jntsArgs(jnts)
		self.ctrlTmpJnts = self.jntsArgs(ctrlJnts)
		self.crv = self.jntsArgs(crv)
		self.upCrv = None

		self.degree = degree
		self.aimAxis = aimAxis
		self.upAxis = upAxis
		self.ikAimAxis = ikAimAxis
		self.ikUpAxis = ikUpAxis

		self.jnts = []
		# self.upJnts = []
		self.upLocs = []
		self.pointLocs = []
		self.pocis = []

		self.ctrlJnts = []
		self.dtlJnts = []
		self.ctrlUpJnts = []
		
		self.ctrls = []
		self.gCtrls = []
		self.ctrlZgrps = []
		self.ctrlSpaceGrps = []
		self.ctrlOffsetGrps = []
		self.upCtrls = []
		self.upCtrlZgrps = []

		self.dtlCtrlOfstGrps = []
		self.dtlCtrlTwstGrps = []
		self.dtlCtrlZroGrps = []

		self.dtlCtrls = []
		self.dtlGCtrls = []

		self.ctrlShp = ctrlShp
		self.ctrlColor = ctrlColor
		self.dtlCtrlShp = dtlCtrlShp
		self.dtlCtrlColor = dtlCtrlColor
		self.upCtrlShp = upCtrlShp
		self.upCtrlColor = upCtrlColor

		self.localWorldRig = localWorldRig
		self.createDtlCtrl = createDtlCtrl
		self.createUpCtrl = createUpCtrl
		self.doSquashStretch = doSquashStretch

	def rig(self):
		self.aimVec = misc.vectorStr(self.aimAxis)
		self.upVec = misc.vectorStr(self.upAxis)

		self.ikAimVec = misc.vectorStr(self.ikAimAxis)
		self.ikUpVec = misc.vectorStr(self.ikUpAxis)

		self.ikOtherAxis = misc.crossAxis(self.ikAimAxis, self.ikUpAxis)

		upVecSize = self.upVec*self.size*0.1
		aimTrans = 't%s' %self.ikAimAxis[-1]

		# --- create groups
		_name = (self.elem, self.side)
		self.rigCtrlGrp = pm.group(em=True, n='%sRig%s_grp' %_name)
		self.rigStillGrp = pm.group(em=True, n='%sStill%s_grp' %_name)
		self.rigUtilGrp = pm.group(em=True, n='%sUtil%s_grp' %_name)

		self.rigJntGrp = pm.group(em=True, n='%sJnt%s_grp' %_name)
		pm.parent(self.rigJntGrp, self.rigUtilGrp)

		self.upLocGrp = pm.group(em=True,  n='%sUpLoc%s_grp' %_name)
		pm.parent(self.upLocGrp, self.rigStillGrp)

		# constraint to parent
		if self.parent:
			misc.snapTransform('parent', self.parent, self.rigCtrlGrp, True, False)
			misc.snapTransform('scale', self.parent, self.rigCtrlGrp, True, False)

			misc.snapTransform('scale', self.rigCtrlGrp, self.rigJntGrp, True, False)

		# --- create spline jnt, up jnt
		jntNum = len(self.tmpJnts)
		tmpCtrlJntLen = len(self.ctrlTmpJnts)
		for i, tmpJnt in enumerate(self.tmpJnts):
			jnt = tmpJnt.duplicate(po=True, n='%s%s%s_jnt' %(self.elem, (i+1), self.side))[0]
			self.jnts.append(jnt)

			if i > 0:
				pm.parent(jnt, self.jnts[i-1])

		# create ctrl up jnts, move it over
		ctrlUpFristJnt = self.ctrlTmpJnts[0].duplicate()[0]
		pm.xform(ctrlUpFristJnt, os=True, r=True, t=upVecSize)
		self.ctrlUpJnts = [ctrlUpFristJnt]
		tmpCtrlUpJntChildren = ctrlUpFristJnt.getChildren(ad=True, type='joint')[::-1]
		self.ctrlUpJnts.extend(tmpCtrlUpJntChildren)
		self.ctrlUpJnts[0].visibility.set(False)

		for i, j in enumerate(self.ctrlUpJnts):
			j.rename('%sUpFk%s%s_jnt' %(self.elem, (i+1), self.side))

		pm.parent(self.ctrlUpJnts[0], self.rigJntGrp)
		pm.parent(self.jnts[0], self.rigJntGrp)

		# --- create curve
		# draw curve cmd
		upTrs = []
		cmd = 'self.crv = pm.curve(d=%s, p=[' %self.degree
		for i, tmpJnt in enumerate(self.ctrlTmpJnts):
			upTr = pm.xform(self.ctrlUpJnts[i], q=True, ws=True, t=True)
			upTrs.append(upTr)

			tr = pm.xform(tmpJnt, q=True, ws=True, t=True)
			cmd += '(%s, %s, %s)' %(tr[0], tr[1], tr[2])

			if i < tmpCtrlJntLen - 1:
				cmd += ','

		cmd += '])'
		if not self.crv:
			exec(cmd)

		# --- up ctrl group
		if self.createUpCtrl == True:
			self.upCtrlGrp = pm.group(em=True, n='%sUpCtrl%s_grp' %_name)
			pm.parent(self.upCtrlGrp, self.rigCtrlGrp)
		else:
			pm.delete(self.ctrlUpJnts)

		# --- create spline ik
		self.ikHndl, self.ikEff = pm.ikHandle(sj=self.jnts[0], ee=self.jnts[-1],
										sol='ikSplineSolver', scv=False, roc=True, pcv=False,
										ccv=False, curve=self.crv)
		self.ikHndl.rename('%s%s_ikHndl' %(self.elem, self.side))

		# setup ik twist
		self.ikHndl.dTwistControlEnable.set(False)
		pm.parent(self.ikHndl, self.rigStillGrp)

		# --- create up ik
		# move the up curve
		self.upCrv = self.crv.duplicate(n='%sUp%s_crv' %(self.elem, self.side))[0]

		for i in xrange(tmpCtrlJntLen):
			pm.xform(self.upCrv.cv[i], ws=True, t=upTrs[i])

		for i in xrange(jntNum):
			loc, pointLoc, npoc, poci = misc.createNearestPointOnCurve(crv=self.upCrv, 
							pointObj=self.jnts[i], pointConstraint=False,
							elem='%s%s' %(self.elem, (i+1)), 
							side=self.side)
			pm.parent(loc, self.upLocGrp)
			pm.parent(pointLoc, self.jnts[i])
			pointLoc.visibility.set(False)

			self.upLocs.append(loc)
			self.pointLocs.append(pointLoc)

		self.crv.rename('%s%s_crv' %(self.elem, self.side))
		self.crv.visibility.set(True)
		
		self.upCrv.rename('%sUp%s_crv' %(self.elem, self.side))
		self.upCrv.visibility.set(False)

		pm.parent(self.crv, self.rigCtrlGrp)
		pm.parent(self.upCrv, self.rigUtilGrp)

		# --- create ctrl joint
		localObj = self.rigCtrlGrp
		worldObj = self.animGrp
		for i, ctrlTmpJnt in enumerate(self.ctrlTmpJnts):
			_iName = (self.elem, (i+1), self.side)

			# create joint
			ctrlJnt = ctrlTmpJnt.duplicate(po=True, n='%s%sFk%s_jnt' %_iName)[0]
			self.ctrlJnts.append(ctrlJnt)
			if i > 0:
				pm.parent(ctrlJnt, self.ctrlJnts[i-1])
				localObj = self.ctrls[i-1]
				worldObj = self.rigCtrlGrp

			# create the controller
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
			misc.snapTransform('parent', ctrlJnt, ctrlZgrp, False, True)

			# gimbal ctrl
			gCtrl = ctrl.addGimbal()
			toCons = gCtrl
			self.gCtrls.append(gCtrl)

			if i > 0:
				pm.parent(ctrlJnt, self.ctrlJnts[i-1])
				localObj = self.gCtrls[i-1]
				worldObj = self.rigCtrlGrp

			self.ctrls.append(ctrl)
			self.ctrlZgrps.append(ctrlZgrp)
			self.ctrlOffsetGrps.append(ctrlOffsetGrp)
			self.ctrlSpaceGrps.append(ctrlSpaceGrp)

			# create constraint
			misc.snapTransform('parent', gCtrl, ctrlJnt, False, False)

			if self.localWorldRig == True and i > 0:
				misc.createLocalWorld(objs=[self.ctrls[i], localObj, worldObj, self.ctrlSpaceGrps[i]], 
								constraintType='parent', attrName='localWorld')

			if self.createUpCtrl == True:
				# --- up ctrl
				upCtrl = controller.Controller(name='%s%sUp%s_ctrl' %_iName, 
					st=self.upCtrlShp, scale=(self.size*0.2))
				upCtrl.setColor(self.upCtrlColor)
				upCtrlZgrp = misc.zgrp(upCtrl, element='Zro', suffix='grp')[0]

				toLockHide = {'t':False, 'r':True, 's':True, 'v':True}
				misc.lockAttr(upCtrl, **toLockHide)
				misc.hideAttr(upCtrl, **toLockHide)

				# snap zgrp
				misc.snapTransform('parent', self.ctrlUpJnts[i] , upCtrlZgrp, False, True)
				misc.snapTransform('parent', self.ctrlJnts[i] , upCtrlZgrp, True, False)
				misc.snapTransform('parent', upCtrl, self.ctrlUpJnts[i], False, False)

				pm.parent(upCtrlZgrp, self.upCtrlGrp)

				self.upCtrls.append(upCtrl)
				self.upCtrlZgrps.append(upCtrlZgrp)
		
		misc.snapTransform('parent', self.gCtrls[0], self.jnts[0], True, False)
		pm.parent(self.ctrlZgrps, self.rigCtrlGrp)
		pm.parent(self.ctrlJnts[0], self.rigJntGrp)
		
		# --- setting ctrl
		self.settingCtrl = controller.Controller(name='%s%s_ctrl' %_name, 
					st='stick', scale=(self.size*1.5), axis=self.upAxis)
		self.settingCtrl.lockAttr(t=True, r=True, s=True, v=True)
		self.settingCtrl.hideAttr(t=True, r=True, s=True, v=True)

		self.settingCtrl.setColor('green')
		settingCtrlZgrp = misc.zgrp(self.settingCtrl, element='Zro', suffix='grp')[0]
		pm.parent(settingCtrlZgrp, self.rigCtrlGrp)

		# place setting controller to the first joint and push it further back
		misc.snapTransform('parent', self.ctrlJnts[0], settingCtrlZgrp, False, False)

		# --- detail controller and up controller visibility attribute
		settingCtrlShp = self.settingCtrl.getShape()
		
		# --- ik slide
		slideAttr = misc.addNumAttr(self.settingCtrl, 'slide', 'double', dv=0)
		pm.connectAttr(slideAttr, self.ikHndl.offset)
		# pm.connectAttr(slideAttr, self.upIkHndl.offset)

		# detail ctrl group
		if self.createDtlCtrl == True:
			self.dtlCtrlGrp = pm.group(em=True, n='%sDtlCtrl%s_grp' %_name)
			pm.parent(self.dtlCtrlGrp, self.rigCtrlGrp)
			dtlCtrlVisAttr = misc.addNumAttr(settingCtrlShp, 'detailCtrl_vis', 'long', min=0, max=1, dv=0)
			dtlCtrlVisAttr.setKeyable(False)
			dtlCtrlVisAttr.showInChannelBox(True)
			# connect detail vis ctrl
			pm.connectAttr(dtlCtrlVisAttr, self.dtlCtrlGrp.visibility)

		if self.createUpCtrl == True:
			upCtrlVisAttr = misc.addNumAttr(settingCtrlShp, 'upCtrl_vis', 'long', min=0, max=1, dv=0)
			upCtrlVisAttr.setKeyable(False)
			upCtrlVisAttr.showInChannelBox(True)
			
			# connect up vis ctrl
			pm.connectAttr(upCtrlVisAttr, self.upCtrlGrp.visibility)

		# --- create detail ctrls
		for i, jnt in enumerate(self.jnts):
			iName = (self.elem, (i + 1), self.side)
			# --- dtl jnt
			dtlJnt = jnt.duplicate(po=True, n='%sDtl%s%s_jnt' %iName)[0]

			# set radius for easy display
			currRadius = jnt.radius.get()
			jnt.radius.set(currRadius*0.5)
			dtlJnt.radius.set(currRadius*1.5)

			pm.parent(dtlJnt, jnt)
			self.dtlJnts.append(dtlJnt)

			aimObj = dtlJnt
			if self.createDtlCtrl == True:
				# --- dtl ctrl
				dtlCtrl = controller.JointController(name='%sDtl%s%s_ctrl' %(self.elem, (i+1), self.side),
													st=self.dtlCtrlShp, 
													color=self.dtlCtrlColor, 
													axis=self.upAxis,
													scale=(self.size*0.75),
													draw=False)
				dtlCtrl.lockAttr(v=True)
				dtlCtrl.hideAttr(v=True)
				dtlCtrl.rotateOrder.set(self.rotateOrder)
				dtlCtrlGCtrl = dtlCtrl.addGimbal()

				dtlCtrlOfstGrp = misc.zgrp(dtlCtrl, element='Ofst', suffix='grp')[0]
				dtlCtrlTwstGrp = misc.zgrp(dtlCtrlOfstGrp, element='Twst', remove='Ofst', suffix='grp')[0]
				dtlCtrlZroGrp = misc.zgrp(dtlCtrlTwstGrp, element='Zro', remove='Twst', suffix='grp')[0]
				pm.parent(dtlCtrlZroGrp, self.dtlCtrlGrp)

				self.dtlCtrls.append(dtlCtrl)
				self.dtlGCtrls.append(dtlCtrlGCtrl)
				self.dtlCtrlOfstGrps.append(dtlCtrlOfstGrp)
				self.dtlCtrlTwstGrps.append(dtlCtrlTwstGrp)
				self.dtlCtrlZroGrps.append(dtlCtrlZroGrp)

				misc.snapTransform('parent', dtlCtrlGCtrl, dtlJnt, False, False)
				misc.snapTransform('scale', dtlCtrlGCtrl, dtlJnt, False, False)

				aimObj = dtlCtrlZroGrp
			
			if i < jntNum - 1:
				misc.snapTransform('point', self.jnts[i], aimObj, False, False)
				pm.aimConstraint(self.jnts[i+1], aimObj, 
										aim=self.aimVec, u=self.upVec,
										wut='object',
										wuo=self.upLocs[i])
			else:
				misc.snapTransform('point', self.jnts[i], aimObj, False, False)
				pm.aimConstraint(self.jnts[i-1], aimObj, 
										aim=(self.aimVec*-1), u=self.upVec,
										wut='object',
										wuo=self.upLocs[i])

		# --- skin the curve 
		if not self.createUpCtrl:
			self.ctrlUpJnts = self.ctrlJnts

		self.skinCluster = pm.skinCluster(self.ctrlJnts, self.crv, tsb=True, dr=2, mi=3)
		self.upSkinCluster = pm.skinCluster(self.ctrlUpJnts, self.upCrv, tsb=True, dr=2, mi=3)

		# set skin weights
		self.lockInf(jnts=self.ctrlJnts, value=False)
		self.lockInf(jnts=self.ctrlUpJnts, value=False)

		# weight the curve
		for i in xrange(tmpCtrlJntLen):
			pm.skinPercent(self.skinCluster, self.crv.cv[i], tv=[self.ctrlJnts[i], 1.0])
			pm.skinPercent(self.upSkinCluster, self.upCrv.cv[i], tv=[self.ctrlUpJnts[i], 1.0])

		# --- parent to groups
		pm.parent(self.rigCtrlGrp, self.animGrp)
		pm.parent(self.rigUtilGrp, self.utilGrp)
		pm.parent(self.rigStillGrp, self.stillGrp)


		# --- create squash stretch
		if self.doSquashStretch == True:
			# add sq st attributes
			sqstDivAttr = misc.addNumAttr(self.settingCtrl, '__squashStretch__', 'double', hide=False, min=0, max=1, dv=0)
			sqstDivAttr.lock()
			stretchAttr = misc.addNumAttr(self.settingCtrl, 'stretch', 'double', dv=0)
			squashAttr = misc.addNumAttr(self.settingCtrl, 'squash', 'double', dv=0)
			autoStretchAttr = misc.addNumAttr(self.settingCtrl, 'autoStretch', 'double', dv=0)
			autoSquashAttr = misc.addNumAttr(self.settingCtrl, 'autoSquash', 'double', dv=0)

			# --- main ik crv
			self.origCrv = pm.duplicate(self.crv, n='%sOrig%s_crv' %_name)[0]
			self.origCrv.visibility.unlock()
			self.origCrv.visibility.set(False)
			self.origCrv.visibility.lock()
			pm.parent(self.origCrv, self.rigJntGrp)

			self.origCrvCif = pm.createNode('curveInfo', n='%sOrig%s_cif' %_name)
			self.crvCif = pm.createNode('curveInfo', n='%s%s_cif' %_name)

			pm.connectAttr(self.origCrv.getShape(ni=True).worldSpace[0], self.origCrvCif.inputCurve)
			pm.connectAttr(self.crv.getShape(ni=True).worldSpace[0], self.crvCif.inputCurve)

			self.autoSqstLenDivMdv = pm.createNode('multiplyDivide', n='%sAutoSqStLenDiv%s_mdv' %_name)
			self.autoSqstLenDivMdv.operation.set(2)
			pm.connectAttr(self.crvCif.arcLength, self.autoSqstLenDivMdv.input1X)
			pm.connectAttr(self.origCrvCif.arcLength, self.autoSqstLenDivMdv.input2X)

			
			autoStretchBta = pm.createNode('blendTwoAttr', n='%sAutoStretch%s_bta' %_name)
			autoStretchBta.input[0].set(1.0)
			pm.connectAttr(autoStretchAttr, autoStretchBta.attributesBlender)
			pm.connectAttr(self.autoSqstLenDivMdv.outputX, autoStretchBta.input[1])

			stretchPma = pm.createNode('plusMinusAverage', n='%sstretchSum%s_pma' %_name)
			pm.connectAttr(autoStretchBta.output, stretchPma.input1D[0])
			pm.connectAttr(stretchAttr, stretchPma.input1D[1])

			i = 0
			for j in self.jnts[1:]:
				tVal = j.attr(aimTrans).get()

				stretchMdl = pm.createNode('multDoubleLinear', n='%sStretch%s%s_mdl' %(self.elem, (i+1), self.side))
				stretchMdl.input2.set(tVal)
				pm.connectAttr(stretchPma.output1D, stretchMdl.input1)
				pm.connectAttr(stretchMdl.output, j.attr(aimTrans))
				i+=1
			
			# --- squash
			# create animCurve and frameCache to calculate squash mult values
			c = pm.createNode('animCurveTU', n='%sSquash%s_animCrvTU' %_name)
			c.addKey(0, 0.0, tangentInType='linear', tangentOutType='linear')
			c.addKey(1, 0.667, tangentInType='smooth', tangentOutType='smooth')
			c.addKey(2, 1.0, tangentInType='flat', tangentOutType='flat')
			c.addKey(3, 0.667, tangentInType='smooth', tangentOutType='smooth')
			c.addKey(4, 0.0, tangentInType='linear', tangentOutType='linear')
			
			autoSquashBta = pm.createNode('blendTwoAttr', n='%sAutoSquash%s_bta' %_name)
			autoSquashBta.input[0].set(1.0)

			pm.connectAttr(autoSquashAttr, autoSquashBta.attributesBlender)
			pm.connectAttr(stretchPma.output1D, autoSquashBta.input[1])

			autoSquashSubOnePma = pm.createNode('plusMinusAverage', n='%sAutoSquashSubOne%s_pma' %_name)
			autoSquashSubOnePma.operation.set(2)
			autoSquashSubOnePma.input1D[0].set(1.0)
			pm.connectAttr(autoSquashBta.output, autoSquashSubOnePma.input1D[1])

			squashSumPma = pm.createNode('plusMinusAverage', n='%ssquashSum%s_pma' %_name)
			pm.connectAttr(squashAttr, squashSumPma.input1D[0])
			pm.connectAttr(autoSquashSubOnePma.output1D, squashSumPma.input1D[1])
			
			i = 0
			varyStep = float(4.0/jntNum)
			squashObj = self.dtlJnts
			if self.createDtlCtrl == True:
				squashObj = self.dtlCtrlZroGrps
			for j in self.jnts:
				_numName = (self.elem, (i+1), self.side)

				fc = pm.createNode('frameCache', n='%sSqst%s%s_fc' %_numName)
				fc.varyTime.set(varyStep * i)
				pm.connectAttr(c.output, fc.stream)

				sqstMdl = pm.createNode('multDoubleLinear', n='%sSquashMult%s%s_mdl' %_numName)
				pm.connectAttr(squashSumPma.output1D, sqstMdl.input1)
				pm.connectAttr(fc.varying, sqstMdl.input2)

				adl = pm.createNode('addDoubleLinear', n='%sAddOne%s%s_adl' %_numName)
				adl.input2.set(1)
				pm.connectAttr(sqstMdl.output, adl.input1)
				for a in 'xyz':
					if a != self.aimAxis[-1]:  # connect squash to all except the aim axis
						pm.connectAttr(adl.output, squashObj[i].attr('s%s' %a))
				i+=1

		# --- set spline jnt draw style to none
		for jnt in self.jnts:
			jnt.drawStyle.set('None')

		# --- hide things
		misc.setDisplayType(obj=self.crv, shp=True, disType='reference')
		self.crv.inheritsTransform.set(False)
		self.upCrv.inheritsTransform.set(False)
		self.rigStillGrp.visibility.set(False)
		self.ikHndl.visibility.set(False)
		self.ctrlJnts[0].visibility.set(False)
		


class SplineFkRig2(baseRig.BaseRig):

	def __init__(self, jnts=[], ctrlJnts=[], degree=2,
				crv=None,
				aimAxis='+y', upAxis='+z', 
				ikAimAxis='+x', ikUpAxis='+z',
				fkCtrlShp='crossCircle', fkCtrlColor='red',
				ikCtrlShp='diamond', ikCtrlColor='blue',
				doSquashStretch=True,
				**kwArgs):
		super(SplineFkRig2, self).__init__(jnts=jnts, ctrJnts=ctrlJnts, **kwArgs)
		
		self.tmpJnts = self.jntsArgs(jnts)
		self.ctrlTmpJnts = self.jntsArgs(ctrlJnts)
		self.crv = self.jntsArgs(crv)
		self.upCrv = None

		self.degree = degree
		self.aimAxis = aimAxis
		self.upAxis = upAxis
		self.ikAimAxis = ikAimAxis
		self.ikUpAxis = ikUpAxis

		self.jnts = []
		# self.upJnts = []
		self.upLocs = []
		self.pointLocs = []
		self.pocis = []

		self.ctrlJnts = []
		self.dtlJnts = []
		self.ctrlUpJnts = []
		
		self.fkCtrls = []
		self.gCtrls = []
		self.fkCtrlZgrps = []

		self.ikCtrls = []
		self.ikCtrlZgrps = []

		self.fkCtrlShp = fkCtrlShp
		self.fkCtrlColor = fkCtrlColor
		self.ikCtrlShp = ikCtrlShp
		self.ikCtrlColor = ikCtrlColor

		self.doSquashStretch = doSquashStretch

	def rig(self):
		self.aimVec = misc.vectorStr(self.aimAxis)
		self.upVec = misc.vectorStr(self.upAxis)

		self.ikAimVec = misc.vectorStr(self.ikAimAxis)
		self.ikUpVec = misc.vectorStr(self.ikUpAxis)

		self.ikOtherAxis = misc.crossAxis(self.ikAimAxis, self.ikUpAxis)

		upVecSize = self.upVec*self.size*0.1
		aimTrans = 't%s' %self.ikAimAxis[-1]

		# --- create groups
		_name = (self.elem, self.side)
		self.rigCtrlGrp = pm.group(em=True, n='%sRig%s_grp' %_name)
		self.rigStillGrp = pm.group(em=True, n='%sStill%s_grp' %_name)
		self.rigUtilGrp = pm.group(em=True, n='%sUtil%s_grp' %_name)

		self.rigJntGrp = pm.group(em=True, n='%sJnt%s_grp' %_name)
		pm.parent(self.rigJntGrp, self.rigUtilGrp)

		self.upLocGrp = pm.group(em=True,  n='%sUpLoc%s_grp' %_name)
		pm.parent(self.upLocGrp, self.rigStillGrp)

		# constraint to parent
		if self.parent:
			misc.snapTransform('parent', self.parent, self.rigCtrlGrp, True, False)
			misc.snapTransform('scale', self.parent, self.rigCtrlGrp, True, False)

			misc.snapTransform('scale', self.rigCtrlGrp, self.rigJntGrp, True, False)

		# --- create spline jnt, up jnt
		jntNum = len(self.tmpJnts)
		tmpCtrlJntLen = len(self.ctrlTmpJnts)
		for i, tmpJnt in enumerate(self.tmpJnts):
			jnt = tmpJnt.duplicate(po=True, n='%s%s%s_jnt' %(self.elem, (i+1), self.side))[0]
			self.jnts.append(jnt)

			if i > 0:
				pm.parent(jnt, self.jnts[i-1])

		# create ctrl up jnts, move it over
		ctrlUpFristJnt = self.ctrlTmpJnts[0].duplicate()[0]
		pm.xform(ctrlUpFristJnt, os=True, r=True, t=upVecSize)
		self.ctrlUpJnts = [ctrlUpFristJnt]
		tmpCtrlUpJntChildren = ctrlUpFristJnt.getChildren(ad=True, type='joint')[::-1]
		self.ctrlUpJnts.extend(tmpCtrlUpJntChildren)
		self.ctrlUpJnts[0].visibility.set(False)

		for i, j in enumerate(self.ctrlUpJnts):
			j.rename('%sUpFk%s%s_jnt' %(self.elem, (i+1), self.side))

		pm.parent(self.ctrlUpJnts[0], self.rigJntGrp)
		pm.parent(self.jnts[0], self.rigJntGrp)

		# --- create curve
		# draw curve cmd
		upTrs = []
		cmd = 'self.crv = pm.curve(d=%s, p=[' %self.degree
		for i, tmpJnt in enumerate(self.ctrlTmpJnts):
			upTr = pm.xform(self.ctrlUpJnts[i], q=True, ws=True, t=True)
			upTrs.append(upTr)

			tr = pm.xform(tmpJnt, q=True, ws=True, t=True)
			cmd += '(%s, %s, %s)' %(tr[0], tr[1], tr[2])

			if i < tmpCtrlJntLen - 1:
				cmd += ','

		cmd += '])'
		if not self.crv:
			exec(cmd)

		pm.delete(self.ctrlUpJnts)

		# --- create spline ik
		self.ikHndl, self.ikEff = pm.ikHandle(sj=self.jnts[0], ee=self.jnts[-1],
										sol='ikSplineSolver', scv=False, roc=True, pcv=False,
										ccv=False, curve=self.crv)
		self.ikHndl.rename('%s%s_ikHndl' %(self.elem, self.side))

		# setup ik twist
		self.ikHndl.dTwistControlEnable.set(False)
		pm.parent(self.ikHndl, self.rigStillGrp)

		# --- create up ik
		# move the up curve
		self.upCrv = self.crv.duplicate(n='%sUp%s_crv' %(self.elem, self.side))[0]

		for i in xrange(tmpCtrlJntLen):
			pm.xform(self.upCrv.cv[i], ws=True, t=upTrs[i])

		for i in xrange(jntNum):
			loc, pointLoc, npoc, poci = misc.createNearestPointOnCurve(crv=self.upCrv, 
							pointObj=self.jnts[i], pointConstraint=False,
							elem='%s%s' %(self.elem, (i+1)), 
							side=self.side)
			pm.parent(loc, self.upLocGrp)
			pm.parent(pointLoc, self.jnts[i])
			pointLoc.visibility.set(False)

			self.upLocs.append(loc)
			self.pointLocs.append(pointLoc)

		self.crv.rename('%s%s_crv' %(self.elem, self.side))
		self.crv.visibility.set(True)
		
		self.upCrv.rename('%sUp%s_crv' %(self.elem, self.side))
		self.upCrv.visibility.set(False)

		pm.parent(self.crv, self.rigCtrlGrp)
		pm.parent(self.upCrv, self.rigUtilGrp)

		# --- create ctrl joint
		for i, ctrlTmpJnt in enumerate(self.ctrlTmpJnts):
			_iName = (self.elem, (i+1), self.side)

			# create joint
			ctrlJnt = ctrlTmpJnt.duplicate(po=True, n='%s%sFk%s_jnt' %_iName)[0]
			self.ctrlJnts.append(ctrlJnt)

			# create the fk controller
			fkCtrl = controller.Controller(name='%s%sFk%s_ctrl' %_iName, 
				st=self.fkCtrlShp, scale=(self.size))
			fkCtrl.setColor(self.fkCtrlColor)
			fkCtrl.rotateOrder.set(self.rotateOrder)
		
			toLockHide = {'t':False, 'r':False, 's':True, 'v':True}
			misc.lockAttr(fkCtrl, **toLockHide)
			misc.hideAttr(fkCtrl, **toLockHide)

			fkCtrlZgrp = misc.zgrp(fkCtrl, element='Zro', remove='Space', suffix='grp')[0]

			# gimbal ctrl
			gCtrl = fkCtrl.addGimbal()
			self.gCtrls.append(gCtrl)

			# create ik controller
			ikCtrl = controller.Controller(name='%s%sIk%s_ctrl' %_iName, 
				st=self.ikCtrlShp, scale=(self.size*0.85))
			ikCtrl.setColor(self.ikCtrlColor)
			ikCtrl.rotateOrder.set(self.rotateOrder)
		
			toLockHide = {'t':False, 'r':False, 's':True, 'v':True}
			misc.lockAttr(ikCtrl, **toLockHide)
			misc.hideAttr(ikCtrl, **toLockHide)

			ikCtrlZgrp = misc.zgrp(ikCtrl, element='Zro', remove='Space', suffix='grp')[0]

			pm.parent(ikCtrlZgrp, gCtrl)
		
			# snap zgrp
			misc.snapTransform('parent', ctrlJnt, fkCtrlZgrp, False, True)


			if i > 0:
				pm.parent(ctrlJnt, self.ctrlJnts[i-1])
				pm.parent(fkCtrlZgrp, self.gCtrls[i-1])


			self.fkCtrls.append(fkCtrl)
			self.fkCtrlZgrps.append(fkCtrlZgrp)
			self.ikCtrls.append(ikCtrl)
			self.ikCtrlZgrps.append(ikCtrlZgrp)


			# create constraint
			misc.snapTransform('parent', ikCtrl, ctrlJnt, False, False)


		
		misc.snapTransform('parent', self.ikCtrls[0], self.jnts[0], True, False)

		pm.parent(self.fkCtrlZgrps[0], self.rigCtrlGrp)
		pm.parent(self.ctrlJnts[0], self.rigJntGrp)
		
		# --- setting ctrl
		self.settingCtrl = controller.Controller(name='%s%s_ctrl' %_name, 
					st='stick', scale=(self.size*1.5), axis=self.upAxis)
		self.settingCtrl.lockAttr(t=True, r=True, s=True, v=True)
		self.settingCtrl.hideAttr(t=True, r=True, s=True, v=True)

		self.settingCtrl.setColor('green')
		settingCtrlZgrp = misc.zgrp(self.settingCtrl, element='Zro', suffix='grp')[0]
		pm.parent(settingCtrlZgrp, self.rigCtrlGrp)

		# place setting controller to the first joint and push it further back
		misc.snapTransform('parent', self.ctrlJnts[0], settingCtrlZgrp, False, False)

		# --- detail controller and up controller visibility attribute
		settingCtrlShp = self.settingCtrl.getShape()
		
		# --- ik slide
		slideAttr = misc.addNumAttr(self.settingCtrl, 'slide', 'double', dv=0)
		pm.connectAttr(slideAttr, self.ikHndl.offset)
		# pm.connectAttr(slideAttr, self.upIkHndl.offset)

		# # detail ctrl group
		# if self.createDtlCtrl == True:
		# 	self.dtlCtrlGrp = pm.group(em=True, n='%sDtlCtrl%s_grp' %_name)
		# 	pm.parent(self.dtlCtrlGrp, self.rigCtrlGrp)
		# 	dtlCtrlVisAttr = misc.addNumAttr(settingCtrlShp, 'detailCtrl_vis', 'long', min=0, max=1, dv=0)
		# 	dtlCtrlVisAttr.setKeyable(False)
		# 	dtlCtrlVisAttr.showInChannelBox(True)
		# 	# connect detail vis ctrl
		# 	pm.connectAttr(dtlCtrlVisAttr, self.dtlCtrlGrp.visibility)

		# if self.createUpCtrl == True:
		# 	upCtrlVisAttr = misc.addNumAttr(settingCtrlShp, 'upCtrl_vis', 'long', min=0, max=1, dv=0)
		# 	upCtrlVisAttr.setKeyable(False)
		# 	upCtrlVisAttr.showInChannelBox(True)
			
		# 	# connect up vis ctrl
		# 	pm.connectAttr(upCtrlVisAttr, self.upCtrlGrp.visibility)

		# # --- create detail ctrls
		for i, jnt in enumerate(self.jnts):
			iName = (self.elem, (i + 1), self.side)
			# --- dtl jnt
			dtlJnt = jnt.duplicate(po=True, n='%sDtl%s%s_jnt' %iName)[0]

			# set radius for easy display
			currRadius = jnt.radius.get()
			jnt.radius.set(currRadius*0.5)
			dtlJnt.radius.set(currRadius*1.5)

			pm.parent(dtlJnt, jnt)
			self.dtlJnts.append(dtlJnt)

			
			if i < jntNum - 1:
				misc.snapTransform('point', self.jnts[i], dtlJnt, False, False)
				pm.aimConstraint(self.jnts[i+1], dtlJnt, 
										aim=self.aimVec, u=self.upVec,
										wut='object',
										wuo=self.upLocs[i])
			else:
				misc.snapTransform('point', self.jnts[i], dtlJnt, False, False)
				pm.aimConstraint(self.jnts[i-1], dtlJnt, 
										aim=(self.aimVec*-1), u=self.upVec,
										wut='object',
										wuo=self.upLocs[i])

		# --- skin the curve 
		self.skinCluster = pm.skinCluster(self.ctrlJnts, self.crv, tsb=True, dr=2, mi=3)
		self.upSkinCluster = pm.skinCluster(self.ctrlJnts, self.upCrv, tsb=True, dr=2, mi=3)

		# set skin weights
		self.lockInf(jnts=self.ctrlJnts, value=False)

		# weight the curve
		for i in xrange(tmpCtrlJntLen):
			pm.skinPercent(self.skinCluster, self.crv.cv[i], tv=[self.ctrlJnts[i], 1.0])
			pm.skinPercent(self.upSkinCluster, self.upCrv.cv[i], tv=[self.ctrlJnts[i], 1.0])

		# --- parent to groups
		pm.parent(self.rigCtrlGrp, self.animGrp)
		pm.parent(self.rigUtilGrp, self.utilGrp)
		pm.parent(self.rigStillGrp, self.stillGrp)


		# --- create squash stretch
		if self.doSquashStretch == True:
			# add sq st attributes
			sqstDivAttr = misc.addNumAttr(self.settingCtrl, '__squashStretch__', 'double', hide=False, min=0, max=1, dv=0)
			sqstDivAttr.lock()
			stretchAttr = misc.addNumAttr(self.settingCtrl, 'stretch', 'double', dv=0)
			squashAttr = misc.addNumAttr(self.settingCtrl, 'squash', 'double', dv=0)
			autoStretchAttr = misc.addNumAttr(self.settingCtrl, 'autoStretch', 'double', dv=0, min=0, max=1)
			autoSquashAttr = misc.addNumAttr(self.settingCtrl, 'autoSquash', 'double', dv=0, min=0, max=1)

			# --- main ik crv
			self.origCrv = pm.duplicate(self.crv, n='%sOrig%s_crv' %_name)[0]
			self.origCrv.visibility.unlock()
			self.origCrv.visibility.set(False)
			self.origCrv.visibility.lock()
			pm.parent(self.origCrv, self.rigJntGrp)

			self.origCrvCif = pm.createNode('curveInfo', n='%sOrig%s_cif' %_name)
			self.crvCif = pm.createNode('curveInfo', n='%s%s_cif' %_name)

			pm.connectAttr(self.origCrv.getShape(ni=True).worldSpace[0], self.origCrvCif.inputCurve)
			pm.connectAttr(self.crv.getShape(ni=True).worldSpace[0], self.crvCif.inputCurve)

			self.autoSqstLenDivMdv = pm.createNode('multiplyDivide', n='%sAutoSqStLenDiv%s_mdv' %_name)
			self.autoSqstLenDivMdv.operation.set(2)
			pm.connectAttr(self.crvCif.arcLength, self.autoSqstLenDivMdv.input1X)
			pm.connectAttr(self.origCrvCif.arcLength, self.autoSqstLenDivMdv.input2X)

			
			autoStretchBta = pm.createNode('blendTwoAttr', n='%sAutoStretch%s_bta' %_name)
			autoStretchBta.input[0].set(1.0)
			pm.connectAttr(autoStretchAttr, autoStretchBta.attributesBlender)
			pm.connectAttr(self.autoSqstLenDivMdv.outputX, autoStretchBta.input[1])

			stretchPma = pm.createNode('plusMinusAverage', n='%sstretchSum%s_pma' %_name)
			pm.connectAttr(autoStretchBta.output, stretchPma.input1D[0])
			pm.connectAttr(stretchAttr, stretchPma.input1D[1])

			i = 0
			for j in self.jnts[1:]:
				tVal = j.attr(aimTrans).get()

				stretchMdl = pm.createNode('multDoubleLinear', n='%sStretch%s%s_mdl' %(self.elem, (i+1), self.side))
				stretchMdl.input2.set(tVal)
				pm.connectAttr(stretchPma.output1D, stretchMdl.input1)
				pm.connectAttr(stretchMdl.output, j.attr(aimTrans))
				i+=1
			
			# --- squash
			# create animCurve and frameCache to calculate squash mult values
			c = pm.createNode('animCurveTU', n='%sSquash%s_animCrvTU' %_name)
			c.addKey(0, 0.0, tangentInType='linear', tangentOutType='linear')
			c.addKey(1, 0.667, tangentInType='smooth', tangentOutType='smooth')
			c.addKey(2, 1.0, tangentInType='flat', tangentOutType='flat')
			c.addKey(3, 0.667, tangentInType='smooth', tangentOutType='smooth')
			c.addKey(4, 0.0, tangentInType='linear', tangentOutType='linear')
			
			autoSquashBta = pm.createNode('blendTwoAttr', n='%sAutoSquash%s_bta' %_name)
			autoSquashBta.input[0].set(1.0)

			pm.connectAttr(autoSquashAttr, autoSquashBta.attributesBlender)
			pm.connectAttr(stretchPma.output1D, autoSquashBta.input[1])

			autoSquashSubOnePma = pm.createNode('plusMinusAverage', n='%sAutoSquashSubOne%s_pma' %_name)
			autoSquashSubOnePma.operation.set(2)
			autoSquashSubOnePma.input1D[0].set(1.0)
			pm.connectAttr(autoSquashBta.output, autoSquashSubOnePma.input1D[1])

			squashSumPma = pm.createNode('plusMinusAverage', n='%ssquashSum%s_pma' %_name)
			pm.connectAttr(squashAttr, squashSumPma.input1D[0])
			pm.connectAttr(autoSquashSubOnePma.output1D, squashSumPma.input1D[1])
			
			i = 0
			varyStep = float(4.0/jntNum)
			for j in self.jnts:
				_numName = (self.elem, (i+1), self.side)

				fc = pm.createNode('frameCache', n='%sSqst%s%s_fc' %_numName)
				fc.varyTime.set(varyStep * i)
				pm.connectAttr(c.output, fc.stream)

				sqstMdl = pm.createNode('multDoubleLinear', n='%sSquashMult%s%s_mdl' %_numName)
				pm.connectAttr(squashSumPma.output1D, sqstMdl.input1)
				pm.connectAttr(fc.varying, sqstMdl.input2)

				adl = pm.createNode('addDoubleLinear', n='%sAddOne%s%s_adl' %_numName)
				adl.input2.set(1)
				pm.connectAttr(sqstMdl.output, adl.input1)
				for a in 'xyz':
					if a != self.aimAxis[-1]:  # connect squash to all except the aim axis
						pm.connectAttr(adl.output, self.dtlJnts[i].attr('s%s' %a))
				i+=1

		# --- set spline jnt draw style to none
		for jnt in self.jnts:
			jnt.drawStyle.set('None')

		# --- hide things
		misc.setDisplayType(obj=self.crv, shp=True, disType='reference')
		self.crv.inheritsTransform.set(False)
		self.upCrv.inheritsTransform.set(False)
		self.rigStillGrp.visibility.set(False)
		self.ikHndl.visibility.set(False)
		self.ctrlJnts[0].visibility.set(False)
		