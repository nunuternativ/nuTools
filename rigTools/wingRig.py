import pymel.core as pm
import maya.OpenMaya as om

from nuTools import misc, controller
reload(misc)
reload(controller)
import nuTools.rigTools.baseRig as baseRig
reload(baseRig)

class WingRig(baseRig.BaseRig):
	def __init__(self, 
				jnts=[], 
				parents=[],
				crvJnts=[],
				ctrlObj=None,
				crv=None,
				baseCrv=None,
				tipCrvs=[],
				tipCrvInfo={},
				aimAxis='+y',
				upAxis='+z',
				ctrlAimAxis='-z',
				ctrlUpAxis='-y',
				name='wing',
				partNames=['upArm', 'forearm', 'wrist', 'finger'],
				ctrlShp='circle',
				ctrlColor='lightBlue',
				crvCtrlShp='keyHole',
				crvCtrlColor='blue',
				crvBaseCtrlShp='locator',
				crvBaseCtrlColor='orange',
				**kwargs):
		super(WingRig, self).__init__(**kwargs)

		self.tmpJnts = self.nestedJntArgs(jnts)  # [(jnt, jnt, ...), ]
		self.partNames = partNames
		self.parents = self.jntsArgs(parents) 
		self.crvTmpJnts = self.jntsArgs(crvJnts)
		self.ctrlObj = self.jntsArgs(ctrlObj)
		self.crv = self.jntsArgs(crv)
		self.baseCrv = self.jntsArgs(baseCrv)
		self.tipCrvInfo = tipCrvInfo
		self.tipCrvs = self.jntsArgs(tipCrvs)

		self.aimAxis = aimAxis
		self.upAxis = upAxis
		self.ctrlAimAxis = ctrlAimAxis
		self.ctrlUpAxis = ctrlUpAxis

		self.name = name

		self.ctrlShp = ctrlShp
		self.ctrlColor = ctrlColor
		self.crvCtrlShp = crvCtrlShp
		self.crvCtrlColor = crvCtrlColor
		self.crvBaseCtrlShp = crvBaseCtrlShp
		self.crvBaseCtrlColor = crvBaseCtrlColor

		self.jnts =[]
		self.crvJnts = []
		self.crvTipJnts = []
		self.ikJnts = []
		self.ikHndls = []
		self.ikEffs = []
		self.tipCrvIkHndls = []
		self.tipCrvIkEffs = []

		self.zJnts = []
		self.bendJnts = []
		self.twstJnts = []
		self.sdkJnts = []

		self.crvJntZgrps = []
		self.crvJntSdkGrps = []

		self.partGrps = []
		self.upLocGrps = []
		self.dtlGrps = []

	def nestedJntArgs(self, jnts):
		if not jnts:
			return

		rets = []
		for chain in jnts:
			joints = []
			if isinstance(chain, (list, tuple)):
				for c in chain:
					if isinstance(c, (str, unicode)):
						try:
							c = pm.PyNode(c)
						except Exception, e:
							print e
							pass

					if isinstance(c, pm.PyNode):
						joints.append(c)

				rets.append(joints)

		return rets

	def rig(self):
		# axis 
		self.aimVec = misc.vectorStr(self.aimAxis)
		self.upVec = misc.vectorStr(self.upAxis)
		self.otherAxis = misc.crossAxis(self.aimAxis, self.upAxis)
		self.otherVec = misc.vectorStr(self.otherAxis)

		self.ctrlAimVec = misc.vectorStr(self.ctrlAimAxis)
		self.ctrlUpVec = misc.vectorStr(self.ctrlUpAxis)
		self.ctrlOtherAxis = misc.crossAxis(self.ctrlAimAxis, self.ctrlUpAxis)
		self.ctrlOtherVec = misc.vectorStr(self.ctrlOtherAxis)

		self.rotateOrder = '%s%s%s' %(self.aimAxis[-1], self.otherAxis[-1], self.upAxis[-1])
		self.fkRotateOrder = '%s%s%s' %(self.upAxis[-1], self.otherAxis[-1], self.aimAxis[-1])

		if self.aimAxis.startswith('-'):
			inverseFront = True
		else:
			inverseFront = False

		if self.upAxis.startswith('-'):
			inverseUp = True
		else:
			inverseUp = False

		_elemSide = (self.elem, self.side)
		self.rigCtrlGrp = pm.group(em=True, n='%sRig%s_grp' %_elemSide)
		# self.rigUtilGrp = pm.group(em=True, n='%sUtil%s_grp' %_elemSide)

		# self.ikHndlGrp = pm.group(em=True, n='%sIkHndl%s_grp' %_elemSide)
		# pm.parent(self.ikHndlGrp, self.rigUtilGrp)

		self.pociLocGrp = pm.group(em=True, n='%sPociLoc%s_grp' %_elemSide)
		self.pociLocGrp.visibility.set(False)
		
		self.baseLocGrp = pm.group(em=True, n='%sBaseLoc%s_grp' %_elemSide)
		self.baseLocGrp.visibility.set(False)


		self.rigStillGrp = pm.group(em=True, n='%sStill%s_grp' %_elemSide)
		pm.parent([self.pociLocGrp, self.baseLocGrp], self.rigStillGrp)

		# rename and store the curve
		self.crv.rename('%s%s_crv' %(self.elem, self.side))
		crvMinMaxs = self.crv.getShape(ni=True).minMaxValue.get()
		pm.parent(self.crv, self.rigStillGrp)
		
		# make sure part name is correct
		numTmpJnt = len(self.tmpJnts)
		numCrvTmpJnt = len(self.crvTmpJnts)
		partNames = []
		for p in self.partNames:
			titlePartName = '%s%s' %(p[0].upper(), p[1:])
			partNames.append(titlePartName)

		# create the base crv if not provided
		numParent = len(self.parents)

		# if no control object, create one
		if not self.ctrlObj:
			self.ctrlObj = controller.Controller(name='%sSetting%s_ctrl' %(self.name, self.side), 
					st='stick', 
					axis=self.upAxis,
					color='green', 
					scale=(self.size))
			self.ctrlObj.lockAttr(t=True, r=True, s=True, v=True)
			self.ctrlObj.hideAttr(t=True, r=True, s=True, v=True)

			ctrlObjZgrp = misc.zgrp(self.ctrlObj, element='Zro', suffix='grp')[0]
			misc.snapTransform('parent', self.parents[0], ctrlObjZgrp, False, False)
			pm.parent(ctrlObjZgrp, self.rigCtrlGrp)

		# --- add control attribute on ctrl obj
		sepAttr = misc.addNumAttr(self.ctrlObj, '__%s__' %self.name, 'double')
		sepAttr.lock()
		fanAttr = misc.addNumAttr(self.ctrlObj, 'fan', 'double')
		curlAttr = misc.addNumAttr(self.ctrlObj, 'curl', 'double')
		bankAttr = misc.addNumAttr(self.ctrlObj, 'bank', 'double')
		twistAttr = misc.addNumAttr(self.ctrlObj, 'twist', 'double')
		foldAttr = misc.addNumAttr(self.ctrlObj, 'fold', 'double', min=0, max=10, dv=0)

		# crv jnt controllers
		for t in xrange(numCrvTmpJnt):
			_chainName = (self.elem, partNames[t], self.side)

			# part grp
			partGrp = pm.group(em=True, n='%s%sJnt%s_grp' %_chainName)
			misc.snapTransform('parent', self.parents[t], partGrp, False, False)
			pm.parent(partGrp, self.rigCtrlGrp)

			jnt = self.crvTmpJnts[t].duplicate(n='%s%s%s_ctrl' %_chainName)[0]

			tipJnt = jnt.getChildren(type='joint')[0]
			tipJnt.rename('%s%sTip%s_jnt' %_chainName)

			jnt.rotateOrder.set(self.rotateOrder)

			zCrvJnt = misc.zgrp(jnt, element='Zro', suffix='grp', preserveHeirachy=True)[0]
			sdkCrvJnt = misc.zgrp(jnt, element='Sdk', suffix='grp', preserveHeirachy=True)[0]
			misc.lockAttr(jnt, t=False, r=False, s=True, v=True, radius=True)
			misc.hideAttr(jnt, t=False, r=False, s=True, v=True, radius=True)
			pm.parent(zCrvJnt, partGrp)

			# create crv ctrl
			crvCtrl = controller.JointController(shapeType=self.crvCtrlShp, 
												axis=self.aimAxis,
												scale=self.size*0.5, 
												color=self.crvCtrlColor,
												joint=jnt.longName(),
												draw=True)

			if t <= numTmpJnt - 1:
				crvCtrlShp = crvCtrl.getShape()
				dtlCtrlVisAttr = misc.addNumAttr(crvCtrlShp, 'detailCtrl_vis', 'long', min=0, max=1, dv=0)

				# up loc grp
				upLocGrp = pm.group(em=True, n='%s%sUpLoc%s_grp' %_chainName)
				upLocGrp.visibility.set(False)
				pm.parent(upLocGrp, partGrp)

				# dtl grp
				dtlGrp = pm.group(em=True, n='%s%sDtl%s_grp' %_chainName)
				pm.parent(dtlGrp, partGrp)
				pm.connectAttr(dtlCtrlVisAttr, dtlGrp.visibility)

				self.upLocGrps.append(upLocGrp)
				self.dtlGrps.append(dtlGrp)

			self.partGrps.append(partGrp)
			self.crvJnts.append(crvCtrl)
			self.crvTipJnts.append(tipJnt)
			self.crvJntZgrps.append(zCrvJnt)
			self.crvJntSdkGrps.append(sdkCrvJnt)

		# --- crv jnt controllers motion path
		if self.tipCrvInfo:
			self.tipPociLocGrp = pm.group(em=True, n='%sTipLoc%s_grp' %_elemSide)
			self.tipPociLocGrp.visibility.set(False)
			pm.parent(self.tipPociLocGrp, self.rigStillGrp)

			c = 0
			for pis, jis in self.tipCrvInfo:
				tipCrv = self.tipCrvs[c]
				pm.parent(tipCrv, self.rigStillGrp)
				# tipCrv.rename('%sTip%s%s_crv' %(self.elem, (i+1), self.side))
				tipCrvName = tipCrv.longName()

				# create ik joints and attach the ik to motion path
				for ji in jis:
					_chainName = (self.elem, partNames[ji], self.side)
					rad = self.crvJnts[ji].radius.get() * 1.5

					aimBaseJnt = self.crvJnts[ji].duplicate(po=True, n='%s%sAimBase%s_jnt' %_chainName)[0]
					aimTipJnt = self.crvTipJnts[ji].duplicate(po=True, n='%s%sAimTip%s_jnt' %_chainName)[0]
					pm.parent(aimTipJnt, aimBaseJnt)
					pm.parent(aimBaseJnt, self.partGrps[ji])
					
					misc.lockAttr(aimBaseJnt, lock=False, t=True, r=True, s=True, v=True, radius=True)
					misc.hideAttr(aimBaseJnt, lock=False, t=True, r=True, s=True, v=True, radius=True)
					misc.lockAttr(aimTipJnt, lock=False, t=True, r=True, s=True, v=True, radius=True)
					misc.hideAttr(aimTipJnt, lock=False, t=True, r=True, s=True, v=True, radius=True)

					aimBaseJnt.radius.set(rad)
					aimTipJnt.radius.set(rad)

					# do not draw ik joints
					aimBaseJnt.drawStyle.set(2)
					aimTipJnt.drawStyle.set(2)

					# create loc
					loc, poci = misc.getNurbsParameterFromPoint(crv=tipCrvName, 
							point=aimTipJnt.getTranslation('world'), createLoc=True, 
							elem='%s%s' %(self.elem, partNames[ji]), side=self.side, 
							mode='pointOnCurveInfo')
					loc.getShape().localScale.set([0.05,0.05,0.05])
					pm.parent(loc, self.tipPociLocGrp)

					# up loc
					upLoc = pm.spaceLocator(n='%s%sUpVec%s_loc' %_chainName)
					upLoc.getShape().localScale.set([0.05,0.05,0.05])
					upLoc.visibility.set(False)
					misc.snapTransform('parent', aimBaseJnt, upLoc, False, True)
					pm.parent(upLoc, self.partGrps[ji])

					aimCons = pm.aimConstraint(loc, aimBaseJnt, 
								aim=self.ctrlAimVec, u=self.ctrlUpVec,
								wut='objectrotation', wu=self.ctrlUpVec,
								wuo=upLoc)
					pm.delete(aimCons)
					pm.makeIdentity(aimBaseJnt, a=True, t=True, r=True, s=True)
					pm.aimConstraint(loc, aimBaseJnt, 
						aim=self.ctrlAimVec, u=self.ctrlUpVec,
						wut='objectrotation', wu=self.ctrlUpVec,
						wuo=upLoc)

					pm.parent(self.crvJntZgrps[ji], aimBaseJnt)

				# weight the crv, if not already weighted
				if not misc.findRelatedSkinCluster(tipCrv):
					parentJnts = [self.parents[p] for p in pis]
					tipSkinCluster = pm.skinCluster(parentJnts, tipCrv, tsb=True, dr=2, mi=3)
					misc.setDisplayType(tipCrv, disType='reference')

					# lock skin weights
					self.lockInf(jnts=parentJnts, value=False)

					# weight the curve
					try:
						for i in xrange(len(parentJnts)):
							pm.skinPercent(tipSkinCluster, tipCrv.cv[i], tv=[parentJnts[i], 1.0])
					except IndexError, e:
						om.MGlobal.displayError('Error applying skin weight for %s' %tipCrvName)

				c += 1

		# --- create jnts
		pocValues = []
		for t, tmpJnts in enumerate(self.tmpJnts):  # tmpJnts = (topJnt, topJnt, ...)
			alp_iter = misc.alphabetIter()

			# add control attr to crv jnt ctrl
			partSepAttr = misc.addNumAttr(self.crvJnts[t], '__%s%s__' %(self.name, partNames[t]), 'double')
			partSepAttr.lock()
			partFanAttr = misc.addNumAttr(self.crvJnts[t], 'fan', 'double')
			partCurlAttr = misc.addNumAttr(self.crvJnts[t], 'curl', 'double')
			partBankAttr = misc.addNumAttr(self.crvJnts[t], 'bank', 'double')
			partTwistAttr = misc.addNumAttr(self.crvJnts[t], 'twist', 'double')
			
			# find max number of children joint in a chain
			nums = set()
			for i, topTmpJnt in enumerate(tmpJnts):
				n = len(topTmpJnt.getChildren(ad=True, type='joint'))
				nums.add(n)

			maxNums = range(sorted(list(nums))[-1])

			# add dtl attrs
			curlSepAttr = misc.addNumAttr(self.crvJnts[t], '__curl__', 'double')
			curlSepAttr.lock()
			for i in maxNums:
				dtlCurlAttr = misc.addNumAttr(self.crvJnts[t], 'curl%s' %(i+1), 'double')

			bankSepAttr = misc.addNumAttr(self.crvJnts[t], '__bank__', 'double')
			bankSepAttr.lock()
			for i in maxNums:
				dtlBankAttr = misc.addNumAttr(self.crvJnts[t], 'bank%s' %(i+1), 'double')

			twistSepAttr = misc.addNumAttr(self.crvJnts[t], '__twist__', 'double')
			twistSepAttr.lock()
			for i in maxNums:
				dtlTwistAttr = misc.addNumAttr(self.crvJnts[t], 'twist%s' %(i+1), 'double')

			# loop thru each feather top joint
			uValues = []
			partJnts, partZJnts, partBendJnts, partTwstJnts, partSdkJnts = [], [], [], [], []
			partCurlPmas, partBankPmas, partTwistPmas = [], [], []
			for i, topTmpJnt in enumerate(tmpJnts):
				alp = alp_iter.next().upper()
				_chainName = (self.elem, partNames[t], alp, self.side)

				jnt = topTmpJnt.duplicate()[0]
				children = jnt.getChildren(ad=True, type='joint')
				jntChains = [jnt]
				jntChains.extend(children[::-1])

				# create ik jnts
				aimBaseJnt = jntChains[0].duplicate(po=True, n='%s%s%sAimBase%s_jnt' %_chainName)[0]
				aimTipJnt = jntChains[-1].duplicate(po=True, n='%s%s%sAimTip%s_jnt' %_chainName)[0]

				pm.parent(aimBaseJnt, self.dtlGrps[t])
				pm.parent(aimTipJnt, aimBaseJnt)
				
				# do not draw ik joints
				aimBaseJnt.drawStyle.set(2)
				aimTipJnt.drawStyle.set(2)
				self.ikJnts.append([aimBaseJnt, aimTipJnt])

				# loop thru each joint in a feather
				numJntChains = len(jntChains)
				zJnts, bendJnts, twstJnts, sdkJnts = [], [], [], []
				curlPmas, bankPmas, twistPmas = [], [], []
				for c in xrange(numJntChains):
					_jntName = (self.elem, partNames[t], alp, (c+1), self.side)

					if c != numJntChains - 1:
						# rename fk jnts
						jntChains[c].rename('%s%s%s%s%s_ctrl' %_jntName)

						# create zgrp and sdk group for joints
						zJnt = misc.addOffsetJnt(jntChains[c], element='Zro', suffix='jnt')[0]
						bendJnt = misc.addOffsetJnt(jntChains[c], element='Bend', suffix='jnt')[0]
						twstJnt = misc.addOffsetJnt(jntChains[c], element='Twst', suffix='jnt')[0]
						sdkJnt = misc.addOffsetJnt(jntChains[c], element='Sdk', suffix='jnt')[0]

						jntChains[c].rotateOrder.set(self.fkRotateOrder)

						# # do not draw zJnt and sdkJnt
						zJnt.drawStyle.set(2)
						bendJnt.drawStyle.set(2)
						twstJnt.drawStyle.set(2)
						sdkJnt.drawStyle.set(2)

						# create fk ctrl
						jntCtrl = controller.JointController(shapeType=self.ctrlShp, 
															axis=self.aimAxis,
															scale=self.size*0.2, 
															color=self.ctrlColor,
															joint=jntChains[c].longName(),
															draw=True)

						zJnts.append(zJnt)
						bendJnts.append(bendJnt)
						twstJnts.append(twstJnt)
						sdkJnts.append(sdkJnt)

						# connect curl 
						# curl plus minus average
						curlPma = pm.createNode('plusMinusAverage', n='%s%s%s%sCurl%s_pma' %_jntName)
						pm.connectAttr(curlAttr, curlPma.input1D[0])
						pm.connectAttr(partCurlAttr, curlPma.input1D[1])
						pm.connectAttr(self.crvJnts[t].attr('curl%s' %(c+1)), curlPma.input1D[2])
						pm.connectAttr(curlPma.output1D, bendJnt.attr('r%s' %self.otherAxis[-1]))

						# connect bank
						# bank plus minus average
						bankPma = pm.createNode('plusMinusAverage', n='%s%s%s%sBank%s_pma' %_jntName)
						pm.connectAttr(bankAttr, bankPma.input1D[0])
						pm.connectAttr(partBankAttr, bankPma.input1D[1])
						pm.connectAttr(self.crvJnts[t].attr('bank%s' %(c+1)), bankPma.input1D[2])
						pm.connectAttr(bankPma.output1D, bendJnt.attr('r%s' %self.upAxis[-1]))
						
						# connect twist
						# twist plus minus average
						twistPma = pm.createNode('plusMinusAverage', n='%s%s%s%sTwist%s_pma' %_jntName)
						pm.connectAttr(twistAttr, twistPma.input1D[0])
						pm.connectAttr(partTwistAttr, twistPma.input1D[1])
						pm.connectAttr(self.crvJnts[t].attr('twist%s' %(c+1)), twistPma.input1D[2])
						pm.connectAttr(twistPma.output1D, twstJnt.attr('r%s' %self.aimAxis[-1]))

						curlPmas.append(curlPma)
						bankPmas.append(bankPma)
						twistPmas.append(twistPma)
					else:
						# rename fk jnts
						jntChains[c].rename('%s%s%s%s%s_jnt' %_jntName)

					# lock hide attribute on joints
					misc.lockAttr(jntChains[c], t=False, r=False, s=False, v=True, radius=True)
					misc.hideAttr(jntChains[c], t=False, r=False, s=False, v=True, radius=True)
				
				partJnts.append(jntChains)
				partBendJnts.append(bendJnts)
				partZJnts.append(zJnts)
				partTwstJnts.append(twstJnts)
				partSdkJnts.append(sdkJnts)	

				partCurlPmas.append(curlPmas)
				partBankPmas.append(bankPmas)
				partTwistPmas.append(twistPmas)	

				# create loc
				loc, poci = misc.getNurbsParameterFromPoint(crv=self.crv.longName(), 
						point=aimTipJnt.getTranslation('world'), createLoc=True, 
						elem='%s%s%s' %(self.elem, partNames[t], alp), side=self.side,
						mode='pointOnCurveInfo')
				loc.getShape().localScale.set([0.05,0.05,0.05])
				pm.parent(loc, self.pociLocGrp)

				# up loc
				upLoc = pm.spaceLocator(n='%s%s%sUpVec%s_loc' %_chainName)
				upLoc.getShape().localScale.set([0.05,0.05,0.05])
				misc.snapTransform('parent', aimBaseJnt, upLoc, False, True)
				pm.parent(upLoc, self.upLocGrps[t])

				aimCons = pm.aimConstraint(loc, aimBaseJnt, 
								aim=self.aimVec, u=self.upVec,
								wut='objectrotation', wu=self.upVec,
								wuo=upLoc)
				pm.delete(aimCons)
				pm.makeIdentity(aimBaseJnt, a=True, t=True, r=True, s=True)
				pm.aimConstraint(loc, aimBaseJnt, 
								aim=self.aimVec, u=self.upVec,
								wut='objectrotation', wu=self.upVec,
								wuo=upLoc)
				pm.parent(zJnts[0], aimBaseJnt)

				# connect control attribute
				# fan
				currU = poci.parameter.get()
				fanPma = pm.createNode('plusMinusAverage', n='%s%s%sFan%s_pma' %_chainName)
				fanPma.input1D[0].set(currU)
				pm.connectAttr(partFanAttr, fanPma.input1D[1])
				pm.connectAttr(fanAttr, fanPma.input1D[2])

				fanCmp = pm.createNode('clamp', n='%s%s%sFan%s_cmp' %_chainName)
				fanCmp.minR.set(crvMinMaxs[0])
				fanCmp.maxR.set(crvMinMaxs[1])
				pm.connectAttr(fanPma.output1D, fanCmp.inputR)
				pm.connectAttr(fanCmp.outputR, poci.parameter)

				uValues.append(currU)

				# base loc
				if self.baseCrv:
					baseLoc, basePoci = misc.getNurbsParameterFromPoint(crv=self.baseCrv.longName(), 
							point=aimBaseJnt.getTranslation('world'), createLoc=True, 
							elem='%s%s%sBase' %(self.elem, partNames[t], alp), side=self.side,
							mode='pointOnCurveInfo')
					baseLoc.getShape().localScale.set([0.05,0.05,0.05])
					# baseMp.follow.set(False)
					pm.parent(baseLoc, self.baseLocGrp)
					pm.pointConstraint(baseLoc, aimBaseJnt, mo=True)

			self.jnts.append(partJnts)
			self.zJnts.append(partZJnts)
			self.bendJnts.append(partBendJnts)
			self.twstJnts.append(partTwstJnts)
			self.sdkJnts.append(partSdkJnts)

			pocValues.append(uValues)

		# --- bind the curve
		self.skinCluster = pm.skinCluster(self.crvTipJnts, self.crv, tsb=True, dr=2, mi=3)
		misc.setDisplayType(self.crv, disType='reference')

		# lock skin weights
		self.lockInf(jnts=self.crvTipJnts, value=False)

		# weight the curve
		try:
			for i in xrange(numCrvTmpJnt):
				pm.skinPercent(self.skinCluster, self.crv.cv[i], tv=[self.crvTipJnts[i], 1.0])
		except IndexError, e:
			om.MGlobal.displayError('Error applying skin weight for %s' %self.crv.nodeName())

		# --- skin base crv
		if self.baseCrv:
			if not misc.findRelatedSkinCluster(self.baseCrv):
				# create base curve joints
				baseCrvJnts = []
				for t, parent in enumerate(self.parents):
					_baseName = (self.name, partNames[t], self.side)
					baseCrvJnt = parent.duplicate(po=True, n='%s%sBase%s_ctrl' %_baseName)[0]
					# create crv ctrl
					crvCtrl = controller.JointController(shapeType=self.crvBaseCtrlShp, 
															scale=self.size*0.5, 
															color=self.crvBaseCtrlColor,
															joint=baseCrvJnt.longName(),
															draw=True)

					zCrvJnt = misc.zgrp(baseCrvJnt, element='Zro', suffix='grp', preserveHeirachy=True)[0]
					sdkCrvJnt = misc.zgrp(baseCrvJnt, element='Sdk', suffix='grp', preserveHeirachy=True)[0]
					misc.lockAttr(baseCrvJnt, t=False, r=True, s=True, v=True, radius=True)
					misc.hideAttr(baseCrvJnt, t=False, r=True, s=True, v=True, radius=True)
					pm.parent(zCrvJnt, self.partGrps[t])

					baseCrvJnts.append(baseCrvJnt)


				self.baseSkinCluster = pm.skinCluster(baseCrvJnts, self.baseCrv, tsb=True, dr=2, mi=2)
				misc.setDisplayType(self.baseCrv, disType='reference')

				# lock skin weights
				self.lockInf(jnts=baseCrvJnts, value=False)

				# weight the base curve 
				try:
					for i in xrange(numParent):
						pm.skinPercent(self.baseSkinCluster, self.baseCrv.cv[i], tv=[baseCrvJnts[i], 1.0])
				except IndexError, e:
					om.MGlobal.displayError('Error applying skin weight for %s' %self.baseCrv.nodeName())

				# self.baseCrv.rename('%sBase%s_crv' %(self.elem, self.side))
				pm.parent(self.baseCrv, self.stillGrp)

		if self.animGrp:
			pm.parent(self.rigCtrlGrp, self.animGrp)
		pm.parent(self.rigStillGrp, self.stillGrp)
		
