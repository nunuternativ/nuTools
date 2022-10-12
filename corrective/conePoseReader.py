import pymel.core as pm
import maya.mel as mel
import maya.OpenMaya as om

from nuTools import misc

reload(misc)

mayaVersion = mel.eval('getApplicationVersionAsFloat;')
if mayaVersion <= 2012:
	if not pm.pluginInfo('decomposeMatrix.mll', query=True, loaded=True):
		pm.loadPlugin('decomposeMatrix.mll')
if mayaVersion > 2012:
	if not pm.pluginInfo('matrixNodes.mll', query=True, loaded=True):
		pm.loadPlugin('matrixNodes.mll')


class ConePoseReader(object):

	def __init__(self, jnt=None, parent=None, axis='+y', elem='limb', side='', size=1.0):
		# parents attrs
		self.jnt = jnt
		self.parent = parent

		# str attrs
		self.elem = elem
		self.side = side
		self.size = size
		self.axis = axis

		# get from msg attrs
		self.baseLoc = None
		self.poseLoc = None
		self.targetLocs = {}
		self.targetNames = []


		self.poseVectorPma = None
		self.baseDmtx = None		

		# grps
		self.mainGrp = None
		self.baseGrp = None
		self.targetGrp = None
		self.meshGrp = None
		# self.bsh = None
	

	def clearVars(self):
		# parents attrs
		self.jnt = None
		self.parent = None

		# str attrs
		self.elem = ''
		self.side = ''
		self.size = ''
		self.axis = ''

		# get from msg attrs
		self.baseLoc = None
		self.poseLoc = None
		self.targetLocs = {}
		self.targetNames = []

		self.poseVectorPma = None
		self.baseDmtx = None		

		# grps
		self.baseGrp = None
		self.targetGrp = None
		self.meshGrp = None
		# self.bsh = None


	def reinit(self, mainGrp=None):
		result = False

		if not mainGrp:
			mainGrp = misc.getSel()
			if not mainGrp:
				om.MGlobal.displayError('Select a ConePoseReader mainGrp to re-initialize.')
				return result

		self.mainGrp = mainGrp

		# clear vars
		self.clearVars()

		try:
			# parent attrs
			self.jnt = mainGrp.attr('jnt').inputs()[0]
			if self.jnt.rotate.inputs():
				om.MGlobal.displayWarning('%s  rotate has incoming connections make sure you can rotate it.' %self.jnt.nodeName())

			self.parent = mainGrp.attr('parent').inputs()[0]

			# str attrs
			self.elem = self.getElem()
			self.side = self.getSide()
			self.size = self.getSize()
			self.axis = self.getAxis()

			# get from msg attrs
			self.baseLoc = mainGrp.attr('baseLoc').outputs()[0]
			self.poseLoc = mainGrp.attr('poseLoc').outputs()[0]
			# get locs to dictionary
			targetLocs = mainGrp.attr('targetLocs').outputs()
			if targetLocs:
				for loc in targetLocs:
					targetName = loc.attr('targetName').get()
					self.targetNames.append(targetName)
					self.targetLocs[targetName] = loc

			self.poseVectorPma = mainGrp.attr('poseVectorPma').outputs()[0]
			self.baseDmtx = mainGrp.attr('baseDmtx').outputs()[0]		

			# grps	
			self.baseGrp = mainGrp.attr('baseGrp').outputs()[0]
			self.targetGrp = mainGrp.attr('targetGrp').outputs()[0]
			self.meshGrp = mainGrp.attr('meshGrp').outputs()[0]

			result = True

		except: pass

		return result



	def register(self, obj, channel):
		misc.addMsgAttr(self.mainGrp, channel)
		misc.addMsgAttr(obj, 'mainGrp')
		pm.connectAttr(self.mainGrp.attr(channel), obj.attr('mainGrp'), f=True)


	def getElem(self):
		elem = self.mainGrp.attr('elem').get()
		if not elem:
			elem = ''
		return elem

	def getSide(self):
		side = self.mainGrp.attr('side').get()
		if not side:
			side = ''
		return side

	def getSize(self):
		size = float(self.mainGrp.attr('size').get())
		if not size:
			size = 1.0
		return size

	def getAxis(self):
		axis = self.mainGrp.attr('axis').get()
		if not axis:
			axis = ''
		return axis


	def create(self):
		# create main grp
		self.mainGrp = pm.group(em=True, n='CPR%s%s_grp' %(self.elem, self.side))
		misc.addNumAttr(self.mainGrp, 'outputEnvelope', 'double', min=0.0, max=1.0, dv=1.0)

		misc.addStrAttr(self.mainGrp, 'elem', txt=self.elem, lock=True)
		misc.addStrAttr(self.mainGrp, 'side', txt=self.side, lock=True)
		misc.addStrAttr(self.mainGrp, 'size', txt=str(self.size), lock=True)
		misc.addStrAttr(self.mainGrp, 'axis', txt=self.axis, lock=True)

		misc.addMsgAttr(self.mainGrp, 'jnt')
		misc.addMsgAttr(self.mainGrp, 'parent')
		misc.addMsgAttr(self.mainGrp, 'targetLocs')
		# misc.addMsgAttr(self.mainGrp, 'bsh')

		# connect from joint and parent
		pm.connectAttr(self.jnt.attr('message'), self.mainGrp.attr('jnt'), f=True)
		pm.connectAttr(self.parent.attr('message'), self.mainGrp.attr('parent'), f=True)

		self.baseGrp = pm.group(em=True, n='%sBase%s_grp' %(self.elem, self.side))
		self.register(self.baseGrp, 'baseGrp')

		self.targetGrp = pm.group(em=True, n='%sTarget%s_grp' %(self.elem, self.side))
		self.register(self.targetGrp, 'targetGrp')
		self.targetGrp.rotateOrder.set(self.parent.rotateOrder.get())

		self.meshGrp = pm.group(em=True, n='%sMesh%s_grp' %(self.elem, self.side))
		self.meshGrp.inheritsTransform.set(False)
		self.register(self.meshGrp, 'meshGrp')

		pm.parent([self.baseGrp, self.targetGrp, self.meshGrp], self.mainGrp)

		# set rotate order
		jntRotOrder = self.jnt.rotateOrder.get()
		self.baseGrp.rotateOrder.set(jntRotOrder)

		# constraint
		misc.snapTransform('parent', self.jnt, self.mainGrp, False, True)

		misc.snapTransform('parent', self.jnt, self.targetGrp, False, True)
		misc.snapTransform('parent', self.parent, self.targetGrp, True, False)
		
		misc.snapTransform('parent', self.jnt, self.baseGrp, True, False)

		# create locators
		locSize = (self.size*0.1, self.size*0.1, self.size*0.1)

		# base loc
		self.baseLoc = pm.spaceLocator()
		self.baseLoc.rename('%sBase%s_loc' %(self.elem, self.side))
		baseLocShp = self.baseLoc.getShape()
		baseLocShp.attr('localScale').set(locSize)
		self.baseLoc.getShape().visibility.set(False)

		self.register(self.baseLoc, 'baseLoc')
	
		misc.setWireFrameColor('darkBlue', self.baseLoc)

		# pose loc
		self.poseLoc = pm.spaceLocator()
		self.poseLoc.rename('%sPose%s_loc' %(self.elem, self.side))
		poseLocShp = self.poseLoc.getShape()
		poseLocShp.attr('localScale').set(locSize)
		
		self.register(self.poseLoc, 'poseLoc')

		misc.setWireFrameColor('red', self.poseLoc)


		misc.snapTransform('parent', self.jnt, self.baseLoc, False, True)
		misc.snapTransform('parent', self.jnt, self.poseLoc, False, True)
		
		# parent to main grp
		pm.parent([self.baseLoc, self.poseLoc], self.baseGrp)

		posePos = list(misc.vectorStr(self.axis, mult=self.size))
		self.poseLoc.translate.set(posePos)


		# node connections
		self.baseDmtx = pm.createNode('decomposeMatrix', n='%sBaseCpr%s_dMtx' %(self.elem, self.side))
		poseDmtx = pm.createNode('decomposeMatrix', n='%sPoseCpr%s_dMtx' %(self.elem, self.side))
		self.register(self.baseDmtx, 'baseDmtx')


		self.poseVectorPma = pm.createNode('plusMinusAverage', n='%sposeVector%s_pma' %(self.elem, self.side))
		self.poseVectorPma.operation.set(2)
		self.register(self.poseVectorPma, 'poseVectorPma')


		pm.connectAttr(self.baseLoc.worldMatrix[0], self.baseDmtx.inputMatrix)
		pm.connectAttr(self.poseLoc.worldMatrix[0], poseDmtx.inputMatrix)
		pm.connectAttr(poseDmtx.outputTranslate, self.poseVectorPma.input3D[0])
		pm.connectAttr(self.baseDmtx.outputTranslate, self.poseVectorPma.input3D[1])

		# lock attrs
		misc.lockAttr(self.baseLoc, lock=True)
		misc.lockAttr(self.poseLoc, lock=True)

		misc.lockAttr(self.mainGrp, lock=True)
		misc.lockAttr(self.baseGrp, lock=True)
		misc.lockAttr(self.targetGrp, lock=True)
		misc.lockAttr(self.meshGrp, lock=True)


	def addTarget(self, name='', coneAngle=75.0, targetAngle=5.0):
		if not name:
			name = 'Target01'

		locSize = (self.size*0.1, self.size*0.1, self.size*0.1)

		targetLoc = pm.spaceLocator()
		targetLoc.rename('%s%s%s_loc' %(self.elem, name, self.side))
		targetLocShp = targetLoc.getShape()
		targetLocShp.attr('localScale').set(locSize)
		# targetLoc.getShape().visibility.set(False)

		targetLocGrp = pm.group(em=True, n='%s%sLoc%s_grp' %(self.elem, name, self.side))
		targetLocGrp.rotateOrder.set(self.jnt.rotateOrder.get())
		misc.snapTransform('parent', self.jnt, targetLocGrp, False, True)
		pm.parent(targetLoc, targetLocGrp)

		# currPosePos = pm.xform(self.poseLoc, q=True, ws=True, t=True)
		# currPoseRot = pm.xform(self.poseLoc, q=True, ws=True, ro=True)
		# pm.xform(targetLoc, ws=True, t=currPosePos, ro=currPoseRot)
		misc.snapTransform('parent', self.poseLoc, targetLoc, False, True)

		# add attrs	
		# envAttr = misc.addNumAttr(targetLoc, 'envelope', 'double', hide=False, min=0.0, max=1.0, dv=1.0)

		interpAttr = misc.addNumAttr(targetLoc, "interpolation", "enum", hide=False, k=True, dv=1, enum="None:Linear:Smooth:Spline:")

		coneAngleAttr = misc.addNumAttr(targetLoc, 'coneAngle', 'double', hide=False, min=0, max=180, dv=coneAngle)
		targetAngleAttr = misc.addNumAttr(targetLoc, 'targetAngle', 'double', hide=False, min=0, max=180, dv=targetAngle)
		
		outputAttr = misc.addNumAttr(targetLoc, 'output', 'double', hide=False)

		# rot = pm.xform(self.jnt, q=True, os=True, ro=True)
		# rots = [str(rot[0]), str(rot[1]), str(rot[2])]
		# rotCode = 'r'.join(rots)
		# rotAttr = misc.addStrAttr(targetLoc, 'targetRotate', txt=rotCode, lock=True)

		misc.addStrAttr(targetLoc, 'targetName', txt=name, lock=True)
		self.register(targetLoc, 'targetLocs')

		nodesAttr = misc.addMsgAttr(targetLoc, 'nodes')

		misc.setWireFrameColor('lightBlue', targetLoc)

		# create cone
		# coneShp = pm.createNode('renderCone')
		# cone = coneShp.getParent()
		# cone.rename('%s%sCone%s_renderCone' %(self.elem, name, self.side))

		# misc.snapTransform('point', self.jnt, cone, False, True)
		# pm.delete(pm.aimConstraint(targetLoc, cone, aim=(0,0,-1)))
		# pm.parent(cone, targetLoc)

		# cone.scale.set((0.5*self.size, 0.5*self.size, 0.5*self.size))
		# coneShp.coneCap.set(0.5*self.size)

		# pm.connectAttr(coneAngleAttr, coneShp.attr('coneAngle'))

		
		# node connections
		targetDmtx = pm.createNode('decomposeMatrix', n='%s%s%s_dMtx' %(self.elem, name, self.side))

		targetVectorPma = pm.createNode('plusMinusAverage', n='%s%sVector%s_pma' %(self.elem, name, self.side))
		targetVectorPma.operation.set(2)

		pm.connectAttr(targetLoc.worldMatrix[0], targetDmtx.inputMatrix)
		pm.connectAttr(targetDmtx.outputTranslate, targetVectorPma.input3D[0])
		pm.connectAttr(self.baseDmtx.outputTranslate, targetVectorPma.input3D[1])

		anBtw = pm.createNode('angleBetween', n='%s%s%s_anBtw' %(self.elem, name, self.side))
		pm.connectAttr(targetVectorPma.output3D, anBtw.vector1)
		pm.connectAttr(self.poseVectorPma.output3D, anBtw.vector2)

		divMdl = pm.createNode('multDoubleLinear', n='%s%sDiv%s_mdl' %(self.elem, name, self.side))
		divMdl.input2.set(0.50)
		pm.connectAttr(targetLoc.attr('coneAngle'), divMdl.input1)
		
		targetConePma = pm.createNode('plusMinusAverage', n='%s%sTargetCone%s_pma' %(self.elem, name, self.side))
		targetConePma.operation.set(2)
		pm.connectAttr(anBtw.angle, targetConePma.input3D[0].input3Dx)
		pm.connectAttr(divMdl.output, targetConePma.input3D[0].input3Dy)
		pm.connectAttr(targetAngleAttr, targetConePma.input3D[1].input3Dx)
		pm.connectAttr(targetAngleAttr, targetConePma.input3D[1].input3Dy)

		targetConeCond = pm.createNode('condition', n='%s%sTargetCone%s_cond' %(self.elem, name, self.side))
		targetConeCond.operation.set(3)
		targetConeCond.colorIfFalseR.set(0.0)
		pm.connectAttr(anBtw.angle, targetConeCond.firstTerm)
		pm.connectAttr(targetLoc.attr('targetAngle'), targetConeCond.secondTerm)
		pm.connectAttr(targetConePma.output3Dx, targetConeCond.colorIfTrueR)

		ratioMdv = pm.createNode('multiplyDivide', n='%s%sRatio%s_mdv' %(self.elem, name, self.side))
		ratioMdv.operation.set(2)
		pm.connectAttr(targetConeCond.outColorR, ratioMdv.input1X)
		pm.connectAttr(targetConePma.output3Dy, ratioMdv.input2X)

		rev = pm.createNode('reverse', n='%s%sOutput%s_rev' %(self.elem, name, self.side))
		pm.connectAttr(ratioMdv.outputX, rev.inputX)

		# clamp = pm.createNode('clamp', n='%s%sOutput%s_cmp' %(self.elem, name, self.side))
		# clamp.minR.set(0.0)
		# clamp.maxR.set(1.0)
		# pm.connectAttr(envAttr, clamp.maxR)

		outputRmv = pm.createNode('remapValue', n='%s%sOutput%s_rmv' %(self.elem, name, self.side))
		pm.connectAttr(rev.outputX, outputRmv.inputValue)
		pm.connectAttr(interpAttr, outputRmv.value[0].value_Interp)

		mainEnvMdl = pm.createNode('multDoubleLinear', n='%s%sEnv%s_mdl' %(self.elem, name, self.side))
		pm.connectAttr(outputRmv.outValue, mainEnvMdl.input1)
		pm.connectAttr(self.mainGrp.outputEnvelope, mainEnvMdl.input2)
		pm.connectAttr(mainEnvMdl.output, outputAttr)

		# connect all nodes to target loc
		nodes = [targetDmtx, targetVectorPma, anBtw, ratioMdv, targetConeCond, targetConePma, divMdl, outputRmv, rev, mainEnvMdl]
		for node in nodes:
			targetLocAttr = misc.addMsgAttr(node, 'targetLoc')
			pm.connectAttr(nodesAttr, targetLocAttr)

		# parent to main grp
		pm.parent(targetLocGrp, self.targetGrp)
		self.targetLocs[name] = targetLoc
		self.targetNames.append(name)
		misc.snapTransform('point', self.baseLoc, targetLocGrp, True, False)

		# lock attrs
		misc.lockAttr(targetLoc, lock=True)
		misc.lockAttr(targetLocGrp, lock=True, t=True, r=False, s=True, v=True)
		# misc.lockAttr(cone, lock=True)

		# misc.setDisplayType(cone, shp=True, disType='reference')

		return {'loc':targetLoc, 'name':name}

