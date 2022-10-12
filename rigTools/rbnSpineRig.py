import pymel.core as pm
import maya.mel as mel
import maya.OpenMaya as om

from nuTools import misc, controller
reload(misc)
reload(controller)

import nuTools.rigTools.baseRig as baseRig
reload(baseRig)

class RbnSpineRig(baseRig.BaseRig):
	def __init__(self, 
				jnts=[], 
				aimAxis='+y', 
				upAxis='+z', 
				worldUpAxis='+z',
				**kwargs):

		super(RbnSpineRig, self).__init__(**kwargs)
		# temp joints
		self.tmpJnts = self.jntsArgs(jnts)

		# axis
		if aimAxis[-1] == upAxis[-1]:
			om.MGlobal.displayError('Aim axis cannot be the same as up axis!')
			return

		self.aimAxis = aimAxis
		self.upAxis = upAxis
		self.worldUpAxis = worldUpAxis

		# curves
		self.lenCrv = None
		self.origLenCrv = None

		# ctrls
		self.fkGCtrls = []
		self.ikGCtrls = []
		self.fkCtrls = [] 
		self.ikCtrls = []

		self.fkBaseCtrl = None
		self.fkBaseGCtrl = None
		self.pelvisCtrl = None
		self.pelvisGCtrl = None

		# grps
		self.fkZgrps = []
		self.ikZgrps = []
		self.dtlZgrps = []

		self.fkBaseCtrlZgrp = None

		# joints
		self.jnts = []
		self.scaJnts = []
		self.rbnJnts = []
		self.rbnLocs = []
		self.rbnRootJnt = None

		# follicles
		self.follicles = []

	def rig(self):
		# --- translate axis from string to vector
		aimAxis = misc.vectorStr(self.aimAxis)
		upAxis = misc.vectorStr(self.upAxis)
		wUpAxis = misc.vectorStr(self.worldUpAxis)

		#--- get class name to use for naming
		elemSide = (self.elem, self.side)

		#--- create main groups
		self.rigCtrlGrp = pm.group(em=True, n='%sRig%s_grp' %elemSide)
		self.rigFkCtrlGrp = pm.group(em=True, n='%sFkCtrl%s_grp' %elemSide)
		self.rigIkCtrlGrp = pm.group(em=True, n='%sIkCtrl%s_grp' %elemSide)
		self.rigDtlCtrlGrp = pm.group(em=True, n='%sDtlCtrl%s_grp' %elemSide)
		pm.parent([self.rigFkCtrlGrp, self.rigIkCtrlGrp, self.rigDtlCtrlGrp], self.rigCtrlGrp)

		self.rigUtilGrp = pm.group(em=True, n='%sUtil%s_grp' %elemSide)
		self.rigRbnJntGrp = pm.group(em=True, n='%sRbnJnt%s_grp' %elemSide)
		# self.rigUtilGrp.visibility.set(False)
		pm.parent(self.rigRbnJntGrp, self.rigUtilGrp)

		self.rigStillGrp = pm.group(em=True, n='%sStill%s_grp' %elemSide)
		self.rigStillGrp.visibility.set(False)

		# --- create setting controller
		self.settingCtrl = controller.Controller(name='%s%s_ctrl' %elemSide, 
					st='stick', scale=(self.size*1.5), axis=self.worldUpAxis)
		self.settingCtrl.lockAttr(t=True, r=True, s=True, v=True)
		self.settingCtrl.hideAttr(t=True, r=True, s=True, v=True)
		fkikAttr = misc.addNumAttr(self.settingCtrl, 'fkIk', 'double', hide=False, min=0, max=1, dv=0)
		autoSqStAttr = misc.addNumAttr(self.settingCtrl, 'autoSquash', 'double', hide=False, min=0, max=1, dv=0)

		# add attribute on setting controller
		settingCtrlShp = self.settingCtrl.getShape()
		detailCtrlVisAttr = misc.addNumAttr(settingCtrlShp, 'detailCtrl_vis', 'long', hide=False, min=0, max=1, dv=0)
		detailCtrlVisAttr.setKeyable(False)
		detailCtrlVisAttr.showInChannelBox(True)
		# sqstDivAttr = misc.addNumAttr(settingCtrlShp, '__squash__', 'double', hide=False, min=0, max=1, dv=0)
		sqst1Attr = misc.addNumAttr(settingCtrlShp, 'squash1_mult', 'double', hide=False, min=0, dv=0)
		sqst2Attr = misc.addNumAttr(settingCtrlShp, 'squash2_mult', 'double', hide=False, min=0, dv=0.5)
		sqst3Attr = misc.addNumAttr(settingCtrlShp, 'squash3_mult', 'double', hide=False, min=0, dv=1)
		sqst4Attr = misc.addNumAttr(settingCtrlShp, 'squash4_mult', 'double', hide=False, min=0, dv=0.5)
		sqst5Attr = misc.addNumAttr(settingCtrlShp, 'squash5_mult', 'double', hide=False, min=0, dv=0)

		# sqstDivAttr.lock()

		# change color and group setting controller
		self.settingCtrl.setColor('green')
		settingCtrlZgrp = misc.zgrp(self.settingCtrl, element='Zro', suffix='grp')[0]

		# create reverse node on fkIk switch attribute and connect
		ikfkRev = pm.createNode('reverse', n='%sIkFk%s_rev' %elemSide)
		pm.connectAttr(self.settingCtrl.fkIk, ikfkRev.inputX)
		pm.connectAttr(settingCtrlShp.detailCtrl_vis, self.rigDtlCtrlGrp.visibility)
		pm.connectAttr(self.settingCtrl.fkIk, self.rigIkCtrlGrp.visibility)
		pm.connectAttr(ikfkRev.outputX, self.rigFkCtrlGrp.visibility)

		# throw setting zgrp to ctrl group
		pm.parent(settingCtrlZgrp, self.rigCtrlGrp)

		#--- loop over each self.tmpJnts to create joint and get curve CV positions
		numJnt = len(self.tmpJnts)
		positions = []
		loftCrv_cmd = 'loftCrv = pm.curve(d=1, p=['  # command for creating loft curve
		lenCrv_cmd = 'self.lenCrv = pm.curve(d=1, p=['  # command for creating loft curve
		i = 0  # counter var
		
		newJnt_parent = self.parent
		for i in xrange(numJnt):
			num = str(i+1).zfill(1)  # number string for naming nodes

			# create a new bind joint, point snap it to given joints
			newJntName = '%s%s%s_jnt' %(self.elem, num, self.side)
			newJnt = pm.duplicate(self.tmpJnts[i], po=True, n=newJntName)[0]
			self.jnts.append(newJnt)

			# scale joint
			newJntScaName = '%s%sSca%s_jnt' %(self.elem, num, self.side)
			newScaJnt = pm.duplicate(self.tmpJnts[i], po=True, n=newJntScaName)[0]
			newScaJnt.radius.set(newJnt.radius.get() * 1.5)
			self.scaJnts.append(newScaJnt)

			pm.parent(newJntScaName, newJntName)
			pm.parent(newJnt, newJnt_parent)

			# parent to upper chain joint
			newJnt_parent = newJnt

			# freeze transform the joint
			pm.makeIdentity(newJnt, apply=True)

			# build loft curve command from joint position
			position = pm.xform(newJnt, q=True, ws=True, t=True)
			positions.append(position)
			positionStr = str('[%s, %s, %s]'%(position[0], position[1], position[2]))
			add_cmd = ''
			if i != numJnt-1:
				add_cmd = ', '

			loftCrv_cmd += '%s%s' %(positionStr, add_cmd)
			if i%2 == 0:
				lenCrv_cmd += '%s%s' %(positionStr, add_cmd)  # len curve command

		# --- find pelvis position by finding the middle point between 0 and 1 joint		
		tmpHipPosLoc = pm.spaceLocator()
		pm.pointConstraint([self.jnts[0], self.jnts[1]], tmpHipPosLoc)
		hipPos = tmpHipPosLoc.getTranslation('world')
		pm.delete(tmpHipPosLoc)


		#--- create fk, ik joints and controllers
		x = 0  # counter var
		elemName = ['pelvis', '%s2' %self.elem, '%s3' %self.elem]
		for i in [n for n in xrange(numJnt) if n%2==0]:  # create controllers on 0, 2, 4 joint only
			xnum = str(x+1).zfill(1)  # number string for naming nodes

			# create rbn bind jnt
			rbnJnt = self.jnts[i].duplicate(po=True)[0]
			rbnJnt.rename('%s%sRbn%s_jnt' %(self.elem, xnum, self.side))
			self.rbnJnts.append(rbnJnt)
			pm.parent(rbnJnt, self.rigRbnJntGrp)

			# create rbnLoc
			rbnLoc = pm.spaceLocator(n='%s%sRbn%s_loc' %(self.elem, xnum, self.side))
			misc.snapTransform('parent', rbnJnt, rbnLoc, False, True)
			rbnLoc.visibility.set(False)
			self.rbnLocs.append(rbnLoc)
			pm.parent(rbnLoc, rbnJnt)

			# if this is not the first joint in the loop
			if i > 0:
				# --- create ik controller
				ikCtrl = controller.Controller(name='%sIk%s_ctrl' %(elemName[x], self.side), 
					st='crossCircle', scale=(self.size), axis=self.aimAxis)

				ikCtrl.setColor('blue')
				ikCtrl.rotateOrder.set(self.rotateOrder)
				ikCtrl.lockAttr(s=True, v=True)
				ikCtrl.hideAttr(s=True, v=True)
				self.ikCtrls.append(ikCtrl)

				# add gimbal
				ikGCtrl = ikCtrl.addGimbal()
				self.ikGCtrls.append(ikGCtrl)

				# create ik zgrp
				ikCtrlZgrp = misc.zgrp(ikCtrl, element='Zro', suffix='grp')[0]
				self.ikZgrps.append(ikCtrlZgrp)

				# parent ik ctrl zgrp to ik controller group
				pm.parent(ikCtrlZgrp, self.rigIkCtrlGrp)

				# --- create fk controller
				fkCtrl = controller.Controller(name='%sFk%s_ctrl' %(elemName[x], self.side), 
					st='crossCircle', scale=(self.size), axis=self.aimAxis)
				fkCtrl.setColor('red')
				fkCtrl.rotateOrder.set(self.rotateOrder)
				fkCtrl.lockAttr(s=True, v=True)
				fkCtrl.hideAttr(s=True, v=True)
				self.fkCtrls.append(fkCtrl)

				# add gimbal
				fkGCtrl = fkCtrl.addGimbal()
				self.fkGCtrls.append(fkGCtrl)

				# create fk zgrp
				fkCtrlZgrp = misc.zgrp(fkCtrl, element='Zro', suffix='grp')[0]
				self.fkZgrps.append(fkCtrlZgrp)
				
				# parent fk ctrl zgrp
				if i == numJnt-1:
					pm.parent(fkCtrlZgrp, self.fkGCtrls[-2])
				else:
					pm.parent(fkCtrlZgrp, self.rigFkCtrlGrp)

				# snap ik and fk conroller zgrp to ribbon joint
				misc.snapTransform('parent', rbnJnt, fkCtrlZgrp, False, True)
				misc.snapTransform('parent', rbnJnt, ikCtrlZgrp, False, True)

				# parent rbn jnt to both ik and fk ctrl and connect to fkIk switch
				parConsNode = pm.parentConstraint([fkGCtrl, ikGCtrl], rbnJnt)
				pm.connectAttr(ikfkRev.outputX, parConsNode.attr('%sW0' %fkGCtrl.nodeName()))
				pm.connectAttr(self.settingCtrl.fkIk, parConsNode.attr('%sW1' %ikGCtrl.nodeName()))

			else:  # the first joint in loop
				# --- create pelvis controller
				self.pelvisCtrl = controller.Controller(name='%s%s_ctrl' %(elemName[x], self.side), 
					st='crossSquare', scale=(self.size), axis=self.aimAxis)
				self.pelvisCtrl.setColor('red')
				self.pelvisCtrl.rotateOrder.set(self.rotateOrder)
				self.pelvisCtrl.lockAttr(s=True, v=True)
				self.pelvisCtrl.hideAttr(s=True, v=True)

				# add gimbal
				self.pelvisGCtrl = self.pelvisCtrl.addGimbal()

				# create zgrp
				self.pelvisCtrlZgrp = misc.zgrp(self.pelvisCtrl, element='Zro', suffix='grp')[0]

				# parent pelvis ctrl zgrp to controller group
				pm.parent(self.pelvisCtrlZgrp, self.rigCtrlGrp)

				# snap orientation of pelvis ctrl zgrp to ribbon joint
				misc.snapTransform('orient', rbnJnt, self.pelvisCtrlZgrp, False, True)
				# set position to hip position
				self.pelvisCtrlZgrp.setTranslation(hipPos)

				# parent first rbn jnt to pelvis gimbal ctrl
				pm.parentConstraint(self.pelvisGCtrl, rbnJnt, mo=True)

			x += 1

		#--- move hip ctrl cv
		numCvs = self.pelvisCtrl.numCVs()
		ctrlShp = self.pelvisCtrl.getShape()
		ctrlCvs = pm.PyNode('%s.cv[%s:%s]' %(ctrlShp.longName(), 0, numCvs-1))
		pm.move(ctrlCvs, (positions[0]-hipPos), r=True)

		#--- add fk base ctrl
		self.fkBaseCtrl = controller.Controller(name='%s1Fk%s_ctrl' %(self.elem, self.side), 
			st='crossCircle', scale=(self.size), axis=self.aimAxis)
		self.fkBaseCtrl.setColor('red')
		self.fkBaseCtrl.rotateOrder.set(self.rotateOrder)
		self.fkBaseCtrl.lockAttr(s=True, v=True)
		self.fkBaseCtrl.hideAttr(s=True, v=True)
		self.fkCtrls.append(self.fkBaseCtrl)

		# add gimbal
		self.fkBaseGCtrl = self.fkBaseCtrl.addGimbal()
		self.fkGCtrls.append(self.fkBaseGCtrl)

		# create zgrp
		self.fkBaseCtrlZgrp = misc.zgrp(self.fkBaseCtrl, element='Zro', suffix='grp')[0]
		self.fkZgrps.append(self.fkBaseCtrlZgrp)

		# snap the controller to place and contraint the fk joint to it
		misc.snapTransform('parent', self.jnts[1], self.fkBaseCtrlZgrp, False, True)

		pm.parent(self.fkBaseCtrlZgrp, self.rigFkCtrlGrp)
		pm.parent(self.fkZgrps[0], self.fkBaseGCtrl)

		#--- point, aim mid ik ctrl
		aimGrp = misc.zgrp(self.ikCtrls[0], suffix='grp', snap=True, preserveHeirachy=True, element='Aim')[0]
		pm.pointConstraint([self.pelvisGCtrl, self.ikCtrls[1]], self.ikZgrps[0], mo=True)
		pm.aimConstraint(self.ikGCtrls[1], aimGrp, aimVector=aimAxis, upVector=upAxis, 
					worldUpType='objectrotation', worldUpVector=wUpAxis, worldUpObject=self.parent, mo=True)

		#--- place setting controller to the first joint and push it further back
		misc.snapTransform('point', self.parent, settingCtrlZgrp, False, True)

		#--- create root jnt
		self.rbnRootJnt = self.jnts[0].duplicate(po=True)[0]
		self.rbnRootJnt.rename('%sRoot%s_jnt' %(self.elem, self.side))
		self.rbnRootJnt.visibility.set(False)
		pm.parent(self.rbnRootJnt, self.rigUtilGrp)
		self.rbnRootJnt.setTranslation(hipPos)

		# create aim up loc for root joint
		upLoc = pm.spaceLocator(n='%sAimUp%s_loc' %elemSide)
		misc.snapTransform('parent', self.pelvisCtrl, upLoc, False, True)
		pm.move(upLoc, upAxis, r=True, os=True)
		pm.parent(upLoc, self.rigStillGrp)
		
		pm.delete(pm.aimConstraint([self.fkGCtrls[0], self.ikGCtrls[0]], self.rbnRootJnt, aimVector=aimAxis, upVector=upAxis, 
					worldUpType=1, worldUpVector=upAxis, worldUpObject=upLoc))
		pm.makeIdentity(self.rbnRootJnt, apply=True)

		# point constraint root joint to pelvis gimbal ctrl
		rootPtNode = pm.pointConstraint(self.pelvisGCtrl, self.rbnRootJnt, mo=True)

		# aim constraint root joint to first fk and ik gimbal ctrl
		rootAimNode = pm.aimConstraint([self.fkGCtrls[0], self.ikGCtrls[0]], self.rbnRootJnt, aimVector=aimAxis, upVector=upAxis, 
					worldUpType=1, worldUpVector=upAxis, worldUpObject=upLoc)
		pm.connectAttr(ikfkRev.outputX, rootAimNode.attr('%sW0' %self.fkGCtrls[0].nodeName()))
		pm.connectAttr(self.settingCtrl.fkIk, rootAimNode.attr('%sW1' %self.ikGCtrls[0].nodeName()))

		misc.snapTransform('parent', self.pelvisGCtrl, upLoc, True, False)

		#--- done with controllers
		pm.parentConstraint(self.pelvisGCtrl, settingCtrlZgrp, mo=True)

		#--- create len curve, orig len curve
		lenCrv_cmd += '], k=%s)' %range(0, 3)
		exec(lenCrv_cmd)
		self.lenCrv.rename('%sLen%s_crv' %elemSide)

		self.origLenCrv = self.lenCrv.duplicate()[0]
		self.origLenCrv.rename('%sOrigLen%s_crv'%elemSide)
		self.origLenCrv.visibility.set(False)

		# connect ribbon locator world position to lenCrv CVs
		lenCrvShp = self.lenCrv.getShape()
		for c in xrange(len(self.rbnLocs)):
			locShp = self.rbnLocs[c].getShape()
			pm.connectAttr(locShp.worldPosition[0], lenCrvShp.controlPoints[c])

		# create loft curve
		loftCrv_cmd += '], k=%s)' %range(0, numJnt)
		exec(loftCrv_cmd)

		#--- create nurbs by duplicating loft curve and loft them
		b_crv = loftCrv.duplicate()[0]
		crossVec = aimAxis.cross(upAxis)
		pm.move(loftCrv, crossVec)
		pm.move(b_crv, crossVec*-1)
		self.surf = pm.loft(loftCrv, b_crv, ch=False)[0]
		self.surf.rename('%s%s_nrbs' %elemSide)

		pm.rebuildSurface(self.surf, ch=0, rpo=1, rt=0, end=1, kr=0, kcp=0, 
			kc=0, su=1, du=3, sv=7, dv=3, tol=0.0001, fr=0, dir=2)
		pm.delete([b_crv, loftCrv])

		#--- create follicle
		self.folGrp = pm.group(em=True, n='%sFol%s_grp' %elemSide)
		self.folGrp.visibility.set(False)
		x, j = 0, 0
		for i in xrange(numJnt):
			num = str(i+1).zfill(1)

			# create detail controller
			dtlCtrl = controller.Controller(name='%sDtl%s%s_ctrl' %(self.elem, num, self.side), 
					st='doubleStick', scale=(self.size*0.75), axis=self.worldUpAxis)
			dtlCtrl.setColor('lightBlue')
			dtlCtrl.lockAttr(v=True)
			dtlCtrl.hideAttr(v=True)
			zgrp = misc.zgrp(dtlCtrl, element='Zro', suffix='grp')[0]
			self.dtlZgrps.append(zgrp)
			misc.snapTransform('parent', self.jnts[i], zgrp, False, True)
			# pm.parent(self.jnts[i], dtlCtrl)
			misc.snapTransform('parent', dtlCtrl, self.jnts[i], True, False)
			# misc.snapTransform('scale', dtlCtrl, self.scaJnts[i], True, False)
			# misc.directConnectTransform(objs=[dtlCtrl, self.scaJnts[i]], t=False, r=False, s=True)
			# create scale pma
			dtlJntScalePma = pm.createNode('plusMinusAverage', n='%sDtl%sScaSub%s_pma' %(self.elem, num, self.side))
			dtlJntScalePma.input3D[2].set(-1.0, -1.0, -1.0)
			pm.connectAttr(dtlCtrl.scale, dtlJntScalePma.input3D[0])
			pm.connectAttr(zgrp.scale, dtlJntScalePma.input3D[1])
			pm.connectAttr(dtlJntScalePma.output3D, self.scaJnts[i].scale)

			pm.parent(zgrp, self.rigDtlCtrlGrp)

			# constraint detail ctrl to follicles
			if i in xrange(1, 4):  # [1, 2, 3]
				xnum = str(x+1).zfill(1)
				jntNameDict = misc.nameSplit(self.jnts[i].nodeName())
				fdict = misc.createFollicleFromPosition_Nurbs(shape=self.surf.getShape(), 
															position=self.jnts[i].getTranslation('world'),
															name=(jntNameDict['elem'], jntNameDict['pos']))
				folTrans = fdict['transform']
				folTrans.rename('%s%s%s_fol' %(self.elem, xnum, self.side))
				pm.parent(folTrans, self.folGrp)
				self.follicles.append(folTrans)
				misc.snapTransform('parent', fdict['transform'], zgrp, True, False)
				misc.snapTransform('scale', self.rigCtrlGrp, fdict['transform'], False, False)
				x += 1
			else:  # i == 0 or i == 4
				if i == 0:
					parCons = pm.parentConstraint(self.pelvisGCtrl, zgrp, mo=True)
				else:
					parCons = pm.parentConstraint([self.fkGCtrls[j], self.ikGCtrls[j]], zgrp, mo=True)
					pm.connectAttr(ikfkRev.outputX, parCons.attr('%sW0' %self.fkGCtrls[j].nodeName()))
					pm.connectAttr(self.settingCtrl.fkIk, parCons.attr('%sW1' %self.ikGCtrls[j].nodeName()))
				j += 1

		pm.parent(self.origLenCrv, self.rigUtilGrp)
		pm.parent([self.lenCrv, self.surf, self.folGrp], self.rigStillGrp)
		
		# --- squash stretch connections
		lenCrvInfo = pm.createNode('curveInfo', n='%sLen%s_cif' %elemSide)
		origLenCrvInfo = pm.createNode('curveInfo', n='%sOrigLen%s_cif' %elemSide)
		autoSqStBcol = pm.createNode('blendColors', n='%sAutoSquash%s_bcol' %elemSide)
		lenDivMdv = pm.createNode('multiplyDivide', n='%sLenDiv%s_mdv' %elemSide)
		lenDivMdv.operation.set(2)

		pm.connectAttr(self.lenCrv.getShape().worldSpace[0], lenCrvInfo.inputCurve)
		pm.connectAttr(self.origLenCrv.getShape().worldSpace[0], origLenCrvInfo.inputCurve)
		pm.connectAttr(self.settingCtrl.autoSquash, autoSqStBcol.blender)
		pm.connectAttr(lenCrvInfo.arcLength, autoSqStBcol.color1R)
		pm.connectAttr(origLenCrvInfo.arcLength, autoSqStBcol.color2R)
		pm.connectAttr(origLenCrvInfo.arcLength, lenDivMdv.input1X)
		pm.connectAttr(autoSqStBcol.outputR, lenDivMdv.input2X)

		subOnePma = pm.createNode('plusMinusAverage', n='%sSubOne%s_pma' %elemSide)
		subOnePma.operation.set(2)
		pm.connectAttr(lenDivMdv.outputX, subOnePma.input1D[0])
		subOnePma.input1D[1].set(1.0)

		for i in xrange(numJnt):
			num = str(i+1).zfill(1)
			mdl = pm.createNode('multDoubleLinear', n='%sSquashMult%s%s_mdl' %(self.elem, num, self.side))
			
			sqstMultAttrName = 'squash%s_mult' %(i+1)
			# sqstMultAttr = misc.addNumAttr(settingCtrlShp, sqstMultAttrName, 'double', hide=False)
			sqstMultAttr = settingCtrlShp.attr(sqstMultAttrName)

			pm.connectAttr(subOnePma.output1D, mdl.input1)
			pm.connectAttr(sqstMultAttr, mdl.input2)

			adl = pm.createNode('addDoubleLinear', n='%sAddOne%s%s_adl' %(self.elem, num, self.side))
			adl.input2.set(1)
			pm.connectAttr(mdl.output, adl.input1)
			for a in 'xyz':
				if a != self.aimAxis[-1]:  # connect squash to all except the aim axis
					pm.connectAttr(adl.output, self.dtlZgrps[i].attr('s%s' %a))

			sqstMultAttr.setKeyable(False)
			sqstMultAttr.showInChannelBox(False)
		
		# --- bind the surfaces
		allRbnBindJnts = self.rbnJnts+[self.rbnRootJnt]
		skc = pm.skinCluster(allRbnBindJnts, self.surf, tsb=True, dr=4, mi=2)

		# apply skin weight values
		self.lockInf(jnts=allRbnBindJnts, value=False)
		pm.skinPercent(skc, self.surf.cv[0:3][0], tv=[self.rbnJnts[0], 1])
		pm.skinPercent(skc, self.surf.cv[0:3][1], tv=[self.rbnJnts[0], 1])

		pm.skinPercent(skc, self.surf.cv[0:3][2], tv=[self.rbnJnts[0], 0.7])
		self.rbnJnts[0].lockInfluenceWeights.set(True)
		pm.skinPercent(skc, self.surf.cv[0:3][2], tv=[self.rbnRootJnt, 0.3])

		self.lockInf(jnts=allRbnBindJnts, value=False)
		pm.skinPercent(skc, self.surf.cv[0:3][3], tv=[self.rbnJnts[1], 0.1])
		self.rbnJnts[1].lockInfluenceWeights.set(True)
		pm.skinPercent(skc, self.surf.cv[0:3][3], tv=[self.rbnRootJnt, 0.9])
		
		self.lockInf(jnts=allRbnBindJnts, value=False)
		pm.skinPercent(skc, self.surf.cv[0:3][4], tv=[self.rbnRootJnt, 0.45])
		self.rbnRootJnt.lockInfluenceWeights.set(True)
		pm.skinPercent(skc, self.surf.cv[0:3][4], tv=[self.rbnJnts[1], 0.55])
		
		self.lockInf(jnts=allRbnBindJnts, value=False)
		pm.skinPercent(skc, self.surf.cv[0:3][5], tv=[self.rbnJnts[1], 0.95])
		self.rbnJnts[1].lockInfluenceWeights.set(True)
		pm.skinPercent(skc, self.surf.cv[0:3][5], tv=[self.rbnJnts[2], 0.05])

		self.lockInf(jnts=allRbnBindJnts, value=False)
		pm.skinPercent(skc, self.surf.cv[0:3][6], tv=[self.rbnJnts[1], 0.8])
		self.rbnJnts[1].lockInfluenceWeights.set(True)
		pm.skinPercent(skc, self.surf.cv[0:3][6], tv=[self.rbnJnts[2], 0.2])

		self.lockInf(jnts=allRbnBindJnts, value=False)
		pm.skinPercent(skc, self.surf.cv[0:3][7], tv=[self.rbnJnts[2], 0.5])
		self.rbnJnts[2].lockInfluenceWeights.set(True)
		pm.skinPercent(skc, self.surf.cv[0:3][7], tv=[self.rbnJnts[1], 0.5])

		self.lockInf(jnts=allRbnBindJnts, value=False)
		pm.skinPercent(skc, self.surf.cv[0:3][8], tv=[self.rbnJnts[1], 0.05])
		self.rbnJnts[1].lockInfluenceWeights.set(True)
		pm.skinPercent(skc, self.surf.cv[0:3][8], tv=[self.rbnJnts[2], 0.95])

		self.lockInf(jnts=allRbnBindJnts, value=False)
		pm.skinPercent(skc, self.surf.cv[0:3][9], tv=[self.rbnJnts[2], 1.0])

		#--- parent to self.parent
		pm.parentConstraint(self.parent, self.rigCtrlGrp, mo=True)
		# pm.scaleConstraint(self.parent, self.rigCtrlGrp, mo=True)

		pm.parentConstraint(self.parent, self.rigUtilGrp, mo=True)
		# pm.scaleConstraint(self.parent, self.rigUtilGrp, mo=True)

		pm.parent(self.rigCtrlGrp, self.animGrp)
		pm.parent(self.rigUtilGrp, self.utilGrp)
		pm.parent(self.rigStillGrp, self.stillGrp)

		ctrlWithGmbls = self.ikCtrls + self.fkCtrls
		ctrlWithGmbls.append(self.pelvisCtrl)
		misc.reShapeGimbalCtrl(ctrls=ctrlWithGmbls)

	def lockInf(self, jnts, value):
		for j in jnts:
			j.lockInfluenceWeights.set(value)