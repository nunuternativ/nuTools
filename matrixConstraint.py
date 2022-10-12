from collections import defaultdict

import pymel.core as pm

def loadPlugin(func):
	pluginNames = ['matrixNodes.mll']
	for pn in pluginNames:
		if not pm.pluginInfo(pn, q=True, l=True):
			pm.loadPlugin(pn)
	return func

class MatrixConstraint(object):
	def __init__(self, parents, child, weights=[], wConnections=[], mo=False, **attrs):
		self.parents = parents
		self.child = child
		self.weights = weights
		self.wConnections = wConnections
		self.maintainOffset = mo
		self.attrs = attrs

		self.offsets = []
		self.offsetMultMatrices = []
		self.multMatrix = None
		self.decomposeMatrix = None

		self.childWorldMat = self.child.worldMatrix[0].get()

	def getOffset(self, parent):
		# get the offset matrix
		parentWorldInvMat = parent.worldInverseMatrix[0].get()
		offset = self.childWorldMat * parentWorldInvMat
		return offset

	@loadPlugin
	def doIt(self):
		childName = self.child.nodeName()

		# create the nodes
		self.multMatrix = pm.createNode('multMatrix', n='%s_mm' %childName)
		self.decomposeMatrix = pm.createNode('decomposeMatrix', n='%s_dm' %childName)

		numParents = len(self.parents)

		# try to get child's parent to avoid using 'ParentInverseMatrix'
		childParent = self.child.getParent()

		if numParents > 1:
			if not self.weights:
				self.weights = [1.0 / numParents] * numParents
			else:  # normalize the weights
				sumWeights = sum(self.weights)
				self.weights = [float(w)/sumWeights for w in self.weights]
			if not self.wConnections:
				self.wConnections = [None] * numParents

			self.wtAddMatrix = pm.createNode('wtAddMatrix', n='%s_wam' %childName)
			for i, parent in enumerate(self.parents):
				intoWtAddMatrix = parent.worldMatrix[0]
				# if maintain offset is True
				if self.maintainOffset:
					offsetMM = pm.createNode('multMatrix', n='%s_%sOffset_mm' %(childName, parent.nodeName()))
					self.offsetMultMatrices.append(offsetMM)

					offsetValue = self.getOffset(parent=parent)
					self.offsets.append(offsetValue)

					offsetMM.matrixIn[0].set(offsetValue)
					intoWtAddMatrix = offsetMM.matrixSum
					pm.connectAttr(parent.worldMatrix[0], offsetMM.matrixIn[1])

				pm.connectAttr(intoWtAddMatrix, self.wtAddMatrix.wtMatrix[i].matrixIn)
				self.wtAddMatrix.wtMatrix[i].weightIn.set(self.weights[i])  # set the weights

				if self.wConnections[i]:
					pm.connectAttr(self.wConnections[i], self.wtAddMatrix.wtMatrix[i].weightIn)

			pm.connectAttr(self.wtAddMatrix.matrixSum, self.multMatrix.matrixIn[0])
			# pm.connectAttr(self.child.parentInverseMatrix[0], self.multMatrix.matrixIn[1])
			pm.connectAttr(childParent.worldInverseMatrix[0], self.multMatrix.matrixIn[1])
		else:
			mi = 0
			if self.maintainOffset:

				offsetValue = self.getOffset(parent=self.parents[0])
				self.offsets.append(offsetValue)

				self.multMatrix.matrixIn[0].set(offsetValue)
				mi += 1

			pm.connectAttr(self.parents[0].worldMatrix[0], self.multMatrix.matrixIn[mi])
			if not childParent:
				pm.connectAttr(self.child.parentInverseMatrix[0], self.multMatrix.matrixIn[mi+1])
			else:
				pm.connectAttr(childParent.worldInverseMatrix[0], self.multMatrix.matrixIn[mi+1])

		# finalize
		pm.connectAttr(self.multMatrix.matrixSum, self.decomposeMatrix.inputMatrix)
		pm.connectAttr(self.child.rotateOrder, self.decomposeMatrix.inputRotateOrder)

		dmDict = {'t':'outputTranslate', 'r':'outputRotate', 's':'outputScale'}
		for attr, value in self.attrs.iteritems():
			if value:
				desAttr = self.child.attr(attr)
				if desAttr.isLocked():
					desAttr.setLocked(False)

				# disconnect the children
				desAttrChildren = desAttr.getChildren()
				if desAttrChildren:
					for cAttr in desAttrChildren:
						if cAttr.isLocked():
							cAttr.setLocked(False)

						if cAttr.isConnected():
							cAttr.disconnect()
				# print self.decomposeMatrix.attr(dmDict[attr]), desAttr
				pm.connectAttr(self.decomposeMatrix.attr(dmDict[attr]), desAttr, f=True)



def getConsInfo(child, validConsType = ['parentConstraint', 'scaleConstraint', 'pointConstraint', 'oreintConstraint']):
	results = []  # [('parentConstraint', [p1, p2], [w1, w2], [attr1, attr2], [connection1, connection2])]
	#get constraint connect to obj
	constraints = [node for node in child.parentInverseMatrix[0].outputs(t='constraint') \
					if child in node.outputs() and node.nodeType() in validConsType]
	for cons in constraints:
		#get the targetList
		targetList = cons.getTargetList()
		weightList = []
		connectionList = []  
		for ti in xrange(len(targetList)):
			wAttr = cons.attr('w%s' %ti)

			# get weight value
			weightValue = wAttr.get()
			weightList.append(weightValue)

			# get cons w connnetions
			wInputs = wAttr.inputs(p=True)
			if wInputs:
				connectionList.append(wInputs[0])

		# get constainted attrs
		consAttrs = []
		for attr in [a for a in cons.outputs(p=True) if a.node()==child]:
			attrParent = attr.getParent()
			toAdd = attrParent if attrParent else attr
			nameToAdd = toAdd.shortName()
			if not nameToAdd in consAttrs:
				consAttrs.append(nameToAdd)

		consAttrs = {a:True for a in consAttrs}  # convert to dict
		res = (cons, cons.nodeType(), targetList, weightList, connectionList, consAttrs)
		results.append(res)

	return results

def convertToMatrixConstraint(objs):
	consNodes = []
	i = 0
	TOL = 0.0001
	for obj in [n for n in objs if isinstance(n, pm.nt.Transform) \
				and not isinstance(n, (pm.nt.Constraint))]:

		if isinstance(obj, pm.nt.Joint):
			if list(obj.jointOrient.get()) != [0, 0, 0]:
				continue

		consInfo = getConsInfo(obj)
		if not consInfo:
			continue

		# currently only works on xyz rotateOrder - SHAME!
		if obj.rotateOrder.get() != 0: 
			continue

		targetDict = defaultdict(dict)  # {k:[], k[]}
		for info in consInfo:
			# print info
			consNode = info[0]
			consType = info[1]
			targetList = info[2]
			weightList = info[3]
			connectionList = info[4]
			attrs = info[5]

			consNodes.append(consNode)

			tKey = tuple(sorted(targetList) + sorted(weightList) + sorted(str(connectionList)))
			targetDict[tKey]['targets'] = targetList
			targetDict[tKey]['weights'] = weightList
			targetDict[tKey]['connections'] = connectionList
			if 'attrs' not in targetDict[tKey]:
				targetDict[tKey]['attrs'] = attrs
			else:
				targetDict[tKey]['attrs'].update(attrs)
				
		for targets, data in targetDict.iteritems():
			mcons = MatrixConstraint(parents=data['targets'], child=obj, 
									weights=data['weights'], wConnections=data['connections'],
									mo=True, **data['attrs'])
			mcons.doIt()

		i += 1

	# pm.delete(consNodes)
	print '%s constarint(s) converted.' %i
	return consNodes
