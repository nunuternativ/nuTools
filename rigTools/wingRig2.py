import pymel.core as pm

from nuTools import misc, controller
reload(misc)
reload(controller)

import nuTools.rigTools.baseRig as baseRig
reload(baseRig)

# jnts = [j1, j2, j3, ...]
# jntInfo = [{'mainJnts': [0, 3], 'childJnts': [1, 2], 'weights':[(0.667, 0.334), ()] }, ...]
# jntInfo = [{'mainJnts': [0, 3], 'childJnts': [1, 2], 'weights':{1:[('point', (w1, w2), (offset)), ()], 2:[(), ()]}, ...]

# parents = [p1, p2, p3, p4]
# parentInfo = [{'parent':([0], 0)},
# 				{'parentTranslate': ([0, 2], 3), 'orient':([0, 2], 3)}, ...]

# names = ['upArm', 'elbow', 'wrist', 'finger']
# sectionNames = ['tertial', 'secondary', 'primary'] 

class WingRig2(baseRig.BaseRig):
	def __init__(self, 
				jnts=[],
				jntInfo=[],
				parents=[],
				parentInfo=[],

				names = ['upArm', 'elbow', 'wrist', 'finger'],
				aimAxis='+y',
				upAxis='+z',
				ctrlShp='crossCircle',
				ctrlColor='red',
				mainCtrlShp='keyHole',
				mainCtrlColor='yellow',
				**kwargs):
		super(WingRig2, self).__init__(**kwargs)

		self.tmpJnts = self.jntsArgs(jnts)
		self.jntInfo = jntInfo
		self.parents = parents
		self.parentInfo = parentInfo 
		self.names = names
		# self.sectionNames = sectionNames

		self.aimAxis = aimAxis
		self.upAxis = upAxis
		self.ctrlShp = ctrlShp
		self.ctrlColor = ctrlColor
		self.mainCtrlShp = mainCtrlShp
		self.mainCtrlColor = mainCtrlColor

		self.jnts = []
		self.zJnts = []
		self.bendJnts = []
		self.twistJnts = []

		self.mainCtrls = {}  # {0:ctrl, 3:ctrl, index:ctrl}
		self.mainCtrlZroGrps = {}
		self.childLocGrps = {}
		self.curlPmas = {}  # {0:[pmas], 3:[pmas], index:list_of_pma}
		self.bankPmas = {}
		self.twistPmas = {}

	def rig(self):
		# figure out the axis
		self.aimVec = misc.vectorStr(self.aimAxis)
		self.upVec = misc.vectorStr(self.upAxis)
		self.otherAxis = misc.crossAxis(self.aimAxis, self.upAxis)
		self.rotateOrder = '%s%s%s' %(self.aimAxis[-1], self.otherAxis[-1], self.upAxis[-1])

		# anim group
		self.rigCtrlGrp = pm.group(em=True, n='%sRig%s_grp' %(self.elem, self.side))
		pm.parent(self.rigCtrlGrp, self.animGrp)
		
		# do shape parent on all joints
		alp_iter = misc.alphabetIter()
		alps = []
		for i, baseJnt in enumerate(self.tmpJnts):
			# get children in the chain
			children = baseJnt.getChildren(ad=True, type='joint')[::-1]
			jnts = [baseJnt] + children
			numJnt = len(jnts)
			alp = alp_iter.next().upper()
			alps.append(alp)

			# iterate joints the chain
			ctrlJnts, zJnts, bendJnts, twistJnts = [], [], [], []
			for j, jnt in enumerate(jnts):
				
				ctrlJnt = controller.JointController(name='%s%s%s%s_ctrl' %(self.elem, alp, (j+1), self.side),
												st=self.ctrlShp, 
												color=self.ctrlColor, 
												scale=(self.size*0.075),
												draw=True)
				ctrlJnt.lockAttr(v=True)
				ctrlJnt.hideAttr(v=True)
				ctrlJnt.radius.set(self.size*0.5)
				ctrlJnt.rotateOrder.set(self.rotateOrder)
				ctrlZroGrp = misc.zgrp(ctrlJnt, element='Zro', suffix='grp')[0]
				jntParent = ctrlJnts[j-1] if j > 0 else self.rigCtrlGrp
				pm.parent(ctrlZroGrp, jntParent)

				zJnt = misc.addOffsetJnt(ctrlJnt, element='Zro', suffix='jnt')[0]
				bendJnt = misc.addOffsetJnt(ctrlJnt, element='Bend', suffix='jnt')[0]
				twistJnt = misc.addOffsetJnt(ctrlJnt, element='Twst', suffix='jnt')[0]
				misc.snapTransform('parent', jnt, zJnt, False, True)
				
				# do not draw zJnt and sdkJnt
				zJnt.drawStyle.set(2)
				bendJnt.drawStyle.set(2)
				twistJnt.drawStyle.set(2)

				ctrlJnts.append(ctrlJnt)
				zJnts.append(zJnt)
				bendJnts.append(bendJnt)
				twistJnts.append(twistJnt)

			# stores values like - [(jntA1, jntA2, ...), (jntB1, jntB2, ...)]
			self.jnts.append(ctrlJnts)
			self.zJnts.append(zJnts)
			self.bendJnts.append(bendJnts)
			self.twistJnts.append(twistJnts)

		# get all main joint index
		# jntInfo = [{'mainJnts': [0, 3], 'childJnts': [1, 2], 'weights':[(0.667, 0.334), ()]}, ...]
		# print self.jntInfo, '...self.jntInfo'
		# print data['mainJnts'], '...data[mainJnts]..'
		mainJntIndices = list(set([index for data in self.jntInfo for index in data['mainJnts']]))
		partNames = []
		# create main ctrls on all mainJnts
		for i, index in enumerate(mainJntIndices):
			partName = '%s%s' % (self.names[i][0].upper(), self.names[i][1:])
			partNames.append(partName)

			mainCtrl = controller.Controller(name='%s%s%s_ctrl' %(self.elem, partName, self.side),
											st=self.mainCtrlShp, 
											color=self.mainCtrlColor, 
											scale=self.size)
			mainCtrl.lockAttr(v=True)
			mainCtrl.hideAttr(v=True)
			mainCtrl.rotateOrder.set(self.rotateOrder)
			mainCtrlZroGrp = misc.zgrp(mainCtrl, element='Zro', suffix='grp')[0]
			pm.parent(mainCtrlZroGrp, self.rigCtrlGrp)

			# number of joint in the chain
			numJnt = len(self.jnts[index])
			curlAttr = misc.addNumAttr(mainCtrl, 'curl', 'double')
			bankAttr = misc.addNumAttr(mainCtrl, 'bank', 'double')
			twistAttr = misc.addNumAttr(mainCtrl, 'twist', 'double')

			# curl
			sepAttr = misc.addNumAttr(mainCtrl, '__curl__', 'double')
			sepAttr.lock()
			for i in xrange(numJnt - 1):
				misc.addNumAttr(mainCtrl, 'curl%s' %(i+1), 'double')

			# bank
			sepAttr = misc.addNumAttr(mainCtrl, '__bank__', 'double')
			sepAttr.lock()
			for i in xrange(numJnt - 1):
				misc.addNumAttr(mainCtrl, 'bank%s' %(i+1), 'double')

			# twist
			sepAttr = misc.addNumAttr(mainCtrl, '__twist__', 'double')
			sepAttr.lock()
			for i in xrange(numJnt - 1):
				misc.addNumAttr(mainCtrl, 'twist%s' %(i+1), 'double')

			misc.snapTransform('parent', self.jnts[index][0], mainCtrlZroGrp, False, True)
			consNode = misc.snapTransform('parent', mainCtrl, self.zJnts[index][0], False, False)
			consNode.interpType.set(2)
			misc.snapTransform('scale', mainCtrl, self.zJnts[index][0], False, False)

			curlPmas, bankPmas, twistPmas = [], [], []
			for j in xrange(numJnt - 1) :
				bendJnt = self.bendJnts[index][j]
				twistJnt = self.twistJnts[index][j]
				_name = (self.elem, alps[index], (j+1), self.side)

				# curl plus minus average
				curlPma = pm.createNode('plusMinusAverage', n='%s%sCurl%s%s_pma' %_name)
				pm.connectAttr(mainCtrl.curl, curlPma.input1D[0])
				pm.connectAttr(mainCtrl.attr('curl%s' %(j+1)), curlPma.input1D[1])
				pm.connectAttr(curlPma.output1D, bendJnt.attr('r%s' %self.otherAxis[-1]))

				# connect bank
				# bank plus minus average
				bankPma = pm.createNode('plusMinusAverage', n='%s%sBank%s%s_pma' %_name)
				pm.connectAttr(mainCtrl.bank, bankPma.input1D[0])
				pm.connectAttr(mainCtrl.attr('bank%s' %(j+1)), bankPma.input1D[1])
				pm.connectAttr(bankPma.output1D, bendJnt.attr('r%s' %self.upAxis[-1]))
				
				# connect twist
				# twist plus minus average
				twistPma = pm.createNode('plusMinusAverage', n='%s%sTwist%s%s_pma' %_name)
				pm.connectAttr(mainCtrl.twist, twistPma.input1D[0])
				pm.connectAttr(mainCtrl.attr('twist%s' %(j+1)), twistPma.input1D[1])
				pm.connectAttr(twistPma.output1D, twistJnt.attr('r%s' %self.aimAxis[-1]))

				curlPmas.append(curlPma)
				bankPmas.append(bankPma)
				twistPmas.append(twistPma)

			self.mainCtrls[index] = mainCtrl
			self.mainCtrlZroGrps[index] = mainCtrlZroGrp

			self.curlPmas[index] = curlPmas
			self.bankPmas[index] = bankPmas
			self.twistPmas[index] = twistPmas

		# jntInfo = [{'mainJnts': [0, 3], 'childJnts': [1, 2], 'weights':{1:[((w1, w2), (offset)), () ] , 2:[(), ()]}, ...]
		# loop each section of feathers
		numJntInfo = len(self.jntInfo)
		for d, data in enumerate(self.jntInfo):
			mainJntIndices = data['mainJnts']  # [0, 3]
			childJntIndices = data['childJnts']  # [1, 2]
			weights = data['weights']  # {1: ((w1, w2), (offsetX, offsetY, offsetZ)), 2:((), ())}
			has_weights = True if weights else False

			mainCtrls = [self.mainCtrls[m] for m in mainJntIndices]

			# connect visibility
			mainCtrlShp = mainCtrls[0].getShape()
			detailCtrlVisAttr = misc.addNumAttr(mainCtrlShp, 'detailCtrl_vis', 'long', min=0, max=1, dv=0)
			detailCtrlVisAttr.setKeyable(False)
			detailCtrlVisAttr.showInChannelBox(True)

			visMainIndices = mainJntIndices[:-1] if d < numJntInfo - 1 else mainJntIndices
			for pi, pIndex in enumerate(visMainIndices):
				pm.connectAttr(mainCtrlShp.detailCtrl_vis, self.zJnts[pIndex][0].visibility)

			# loop child index
			for ci, cIndex in enumerate(childJntIndices):
				zJnts = self.zJnts[cIndex]
				bendJnts = self.bendJnts[cIndex]
				twistJnts = self.twistJnts[cIndex]

				# connect vis for children
				pm.connectAttr(mainCtrlShp.detailCtrl_vis, zJnts[0].visibility)

				if has_weights:
					# set constraint weights
					consWeights = weights[cIndex][0]
					# normalize the weights
					sumConsWeights = sum([float(w) for w in consWeights])
					normConsWeights = [n/sumConsWeights for n in consWeights]
					# set it back to the data
					self.jntInfo[d]['weights'][cIndex][0] = normConsWeights
					offsets = weights[cIndex][1]

					# point orient the child base joint to 2 of the main chain base joint
					ptNode = misc.snapTransform('point', mainCtrls, zJnts[0], False, False)
					oriNode = misc.snapTransform('orient', mainCtrls, zJnts[0], False, False)
					oriNode.interpType.set(2)
					oriNode.offset.set(offsets)

					# set constraint weights
					for wi, weight in enumerate(normConsWeights):
						ptNode.attr('w%s' %wi).set(weight)
						oriNode.attr('w%s' %wi).set(weight)
				else:
					# point orient the child base joint to 2 of the main chain base joint
					ptNode = misc.snapTransform('point', mainCtrls, zJnts[0], True, False)
					oriNode = misc.snapTransform('orient', mainCtrls, zJnts[0], True, False)
					oriNode.interpType.set(2)

				# loop current child index whole chain
				# connect curl, bank and twist
				for ji in xrange(len(self.jnts[cIndex]) - 1):
					_name = (self.elem, alps[cIndex], (ji+1), self.side)  # wingFeather B 1 LFT

					# create pmas
					sumCurlPma = pm.createNode('plusMinusAverage', n='%s%sCurl%s%s_pma' %_name)
					sumBankPma = pm.createNode('plusMinusAverage', n='%s%sBank%s%s_pma' %_name)
					sumTwistPma = pm.createNode('plusMinusAverage', n='%s%sTwist%s%s_pma' %_name)

					for mi, mIndex in enumerate(mainJntIndices):
						# wingFeather A B Curl 1 LFT
						_pname = (self.elem, alps[mIndex], alps[cIndex], (ji+1), self.side)

						curlPma = self.curlPmas[mIndex][ji]
						curlMdl = pm.createNode('multDoubleLinear', n='%s%s%sCurl%s%s_mdl' %_pname)
						pm.connectAttr(curlPma.output1D, curlMdl.input1)
						pm.connectAttr(curlMdl.output, sumCurlPma.input1D[mi])

						bankPma = self.bankPmas[mIndex][ji]
						bankMdl = pm.createNode('multDoubleLinear', n='%s%s%sBank%s%s_mdl' %_pname)
						pm.connectAttr(bankPma.output1D, bankMdl.input1)
						pm.connectAttr(bankMdl.output, sumBankPma.input1D[mi])

						twistPma = self.twistPmas[mIndex][ji]
						twistMdl = pm.createNode('multDoubleLinear', n='%s%s%sTwist%s%s_mdl' %_pname)
						pm.connectAttr(twistPma.output1D, twistMdl.input1)
						pm.connectAttr(twistMdl.output, sumTwistPma.input1D[mi])

						if has_weights:
							curlMdl.input2.set(weights[cIndex][0][mi])
							bankMdl.input2.set(weights[cIndex][0][mi])
							twistMdl.input2.set(weights[cIndex][0][mi])
						else:
							curlMdl.input2.set(1.0)
							bankMdl.input2.set(1.0)
							twistMdl.input2.set(1.0)

					pm.connectAttr(sumCurlPma.output1D, bendJnts[ji].attr('r%s' %self.otherAxis[-1]))
					pm.connectAttr(sumBankPma.output1D, bendJnts[ji].attr('r%s' %self.upAxis[-1]))
					pm.connectAttr(sumTwistPma.output1D, twistJnts[ji].attr('r%s' %self.aimAxis[-1]))

		# parent main jnt to parents
		# parentInfo = [{'parent':([0], 0)},
		# 				{'parentTranslate': ([0, 2], 3), 'orient':([0, 2], 3)}, ...]
		partLocGrp = pm.group(em=True, n='%sLoc%s_grp' %(self.elem, self.side))
		pm.parent(partLocGrp, self.rigCtrlGrp)
		for zroGrp, parent, name in zip(self.mainCtrlZroGrps.values(), self.parents, partNames):
			childLocGrp = pm.group(em=True, n='%s%sLoc%s_grp' %(self.elem, name, self.side))
			pm.parent(childLocGrp, partLocGrp)

			misc.snapTransform('parent', zroGrp, childLocGrp, False, True)
			misc.snapTransform('parent', parent, childLocGrp, True, False)
			self.childLocGrps[parent] = childLocGrp

		for i, data in enumerate(self.parentInfo):
			for consType, indicesData in data.iteritems():
				parents = [self.parents[pi] for pi in indicesData[0]]
				parentGrps = [self.childLocGrps[parent] for parent in parents]
				child = self.mainCtrlZroGrps[indicesData[1]]

				# do constraint
				consNode = misc.snapTransform(consType, parentGrps, child, True, False)
				consNode.interpType.set(2)


def generateJntInfo(objs=[]):
	from pprint import pprint

	if not objs:
		objs = misc.getSel(num='inf')

	# jntInfo = [{'mainJnts': [0, 3], 'childJnts': [1, 2], 'weights':{1:[((w1, w2), (offset)), ()], 2:[(), ()]}, ...]
	parentIndices, children = [], []
	weightList, offsetList = [], []
	result = []
	for i, obj in enumerate(objs):
		parents = [p for p in misc.getConParents(obj) if p in objs]
		if not parents:  # found a parent
			if not children:
				continue

			# assemble weights dict
			weightDict = {}
			for ci, cIndex in enumerate(children):
				weightDict[cIndex] = [weightList[ci], offsetList[ci]]

			resDict = {	'mainJnts': parentIndices, 
						'childJnts': children,
						'weights': weightDict}
			result.append(resDict)

			children = []
			weightList = []
			offsetList = []
			continue

		# it's child
		children.append(i)

		# get cons weights
		# 'weights':{1: ((w1, w2), (offsetX, offsetY, offsetZ)), 2:((), ())}
		oriCons = obj.rx.inputs(type='orientConstraint')
		if oriCons:
			oriCons = oriCons[0]

		weights = []
		for ne in xrange(oriCons.target.numElements()):
			value = oriCons.attr('w%s' %ne).get()
			offset = list(oriCons.offset.get())
			weights.append(value)
			offsetList.append(offset)

		if weights:
			# normalize the weights
			sumWeights = sum([float(w) for w in weights])
			weights = [n/sumWeights for n in weights]

		weightList.append(weights)
		parentIndices = [objs.index(p) for p  in parents]

	pprint(result)
	return result