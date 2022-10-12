import pymel.core as pm
import maya.cmds as mc
from nuTools import controller as ctrl
from nuTools import misc as misc
import maya.OpenMaya as OpenMaya

def isTemplateRoot(obj):
	if not obj:
		return
	try:
		if obj._SUBTYPE.get() == 'TEMP_Controller' and obj._TEMPLATE.get():
			return True
		else: return False
	except: return False

def bake(objs=[]):
	allTmpJntsDic = {}

	for obj in objs:
		objTmpJnts = obj.tmpJnts
		#pos = obj.pos
		if isinstance(obj.tmpJnts, dict):
			objTmpJnts = objTmpJnts.values()
			if any(isinstance(tj, list) for tj in objTmpJnts):
				objTmpJnts = [item for sublist in objTmpJnts for item in sublist]

		for objTmpJnt in objTmpJnts:
			name = objTmpJnt.nodeName().replace('TEMP_', '')
			jnt = pm.createNode('joint', n='%s' %(name))
			jnt.radius.set(obj.scale)
			misc.snapTransform('parent', objTmpJnt, jnt, False, True)
			pm.makeIdentity(jnt, apply=True, t=True, r=True, s=True, n=True)
			allTmpJntsDic[objTmpJnt] = jnt

	for tmp, jnt in allTmpJntsDic.iteritems():
		parent = []
		try:
			parentCons = tmp._PARENT.inputs()
			if parentCons:
				parentJnt = allTmpJntsDic[parentCons[0]]
				pm.parent(jnt, parentJnt)
		except:
			pass

	#delete tempJnt rootCtrl
	rootCtrls = []
	for obj in objs:
		if pm.objExists(obj.rootCtrl) == True:
			rootCtrls.append(obj.rootCtrl)

	pm.delete(rootCtrls)


def connectTempJnts(child, parent):
	try:
		if parent._TYPE.get() != 'tmpJnt':
			return
		if child._TYPE.get() != 'tmpJnt':
			return
	except: return

	pParts = misc.nameSplit(parent.nodeName().replace('TEMP_', ''))

	#figure out name for arrow
	cParts = misc.nameSplit(child.nodeName().replace('TEMP_', ''))
	pointerName = 'TEMP_%s%s__%s%s' %(pParts['elem'], pParts['pos'], cParts['elem'], cParts['pos'])

	#unparent form old parent first
	disconnectTempJnts(child)

	misc.annPointer(pointFrom=parent, pointTo=child, ref=True, constraint=False, nameParts=pointerName)
	pm.connectAttr(parent.attr('_CHILD'), child.attr('_PARENT'), f=True)

	pm.select(parent, r=True)

def disconnectTempJnts(obj):
	try:
		oldParents = obj._PARENT.inputs()
	except: return

	if oldParents:
		obj._PARENT.disconnect()
		for tr in pm.listRelatives(obj, children=True, type='transform'):
			shp = tr.getShape()
			if not shp:
				continue
			if shp.type() != 'annotationShape':
				continue
			conParent = misc.getConParents(tr)
			if oldParents[0] in conParent:		
				try:
					loc = shp.dagObjectMatrix[0].inputs()[0]
					pm.delete(loc, tr)
				except: continue


def getMirrored(obj):
	mirrors = []
	if obj.hasAttr('_MIRRORED'):
		mirrors = obj._MIRRORED.outputs()
	return mirrors

def mirrorTemp(obj, pos='', connect=True):
	#security checks
	if obj.pos == pos:
		OpenMaya.MGlobal.displayError('Same template with pos  "%s"  already exists! Try something else.' %pos)
		return

	mPositions = []
	positions = obj.positions

	for position in positions:
		mX = position[0] * -1
		mPositions.append([mX, position[1], position[2]])

	#mNames = obj.names

	#get aim
	#mMult = obj.mult * -1

	mObj = obj.__class__(elem=obj.elem, pos=pos)

	#mObj.pos = pos
	mObj.positions = mPositions
	#mObj.names = obj.names
	mObj.mult = obj.mult * -1
	mObj.elem = obj.elem
	mObj.scale = obj.scale
	mObj.num = obj.num
	mObj.ctrlAxis = obj.ctrlAxis
	mObj.aimVec = obj.aimVec
	mObj.upVec = obj.upVec

	#create it
	mObj.create()

	#move to match
	connectObj = MirrorTempConnection(obj, mObj)

	connectObj.connect()

	if connect == False:
		connectObj.disconnect()
	else:
		obj.mirrorConObj = connectObj

	pm.select(obj.rootCtrl, r=True)

	return mObj

def createMdl(a, b, c):
	nodeName = '%sMIRROR%s%s' %(a, b, c)
	node = pm.createNode('multDoubleLinear', n=misc.nameObj(elem='TEMP_%s' %(nodeName), typ='mdl'))
	node.input2.set(-1)
	return node






########################################################################################################################################
########################################################################################################################################
########################################################################################################################################
######################################################### BASE CLASSES #################################################################
########################################################################################################################################
########################################################################################################################################
########################################################################################################################################







class MirrorTempConnection(object):
	def __init__(self, objA, objB):
		self.objA = objA
		self.objB = objB
		self.nodes = []
		self.connected = []

	def connect(self):
		if not type(self.objA) is type(self.objB):
			return

		#connect tmpJnts
		source = sorted(self.objA.tmpJnts)
		des = sorted(self.objB.tmpJnts)

		for s, d in zip(source, des):
			try:
				if s.tx.isLocked() == False:	
					sParts = misc.nameSplit(s.nodeName().replace('TEMP_', ''))
					dParts = misc.nameSplit(d.nodeName().replace('TEMP_', ''))
					node = createMdl(sParts['elem'], dParts['elem'], 'TX')
					self.nodes.append(node)
					pm.connectAttr(s.tx, node.input1)
					pm.connectAttr(node.output, d.tx, f=True)
				if s.ty.isLocked() == False:	
					pm.connectAttr(s.ty, d.ty, f=True)
				if s.tz.isLocked() == False:	
					pm.connectAttr(s.tz, d.tz, f=True)
				pm.connectAttr(s.radius, d.radius, f=True)
				self.connected.append(d)
				pm.connectAttr(s._MIRRORED, d._MIRRORED, f=True)
			except: pass

		#connect sub object
		aRoots, bRoots = [self.objA.rootCtrl], [self.objB.rootCtrl]
		if hasattr(self.objA, 'subCtrls') and hasattr(self.objB, 'subCtrls'):
			for subA, subB in zip(self.objA.subCtrls.values(), self.objB.subCtrls.values()):
				aRoots.append(subA)
				bRoots.append(subB)

		for aRoot, bRoot in zip(aRoots, bRoots):
			#connect rootCtrl
			for attr in ['ty', 'tz', 'rx', 'sx', 'sy', 'sz']:
				if bRoot.attr(attr).isLocked() == False: 
					pm.connectAttr(aRoot.attr(attr), bRoot.attr(attr), f=True)

			sParts = misc.nameSplit(aRoot.nodeName().replace('TEMP_', ''))
			dParts = misc.nameSplit(bRoot.nodeName().replace('TEMP_', ''))

			for attr in ['tx', 'ry', 'rz']:
				if aRoot.attr(attr).isLocked() == True:
					continue 
				node = createMdl(sParts['elem'], dParts['elem'], attr.upper())
				self.nodes.append(node)
				pm.connectAttr(aRoot.attr(attr), node.input1)
				pm.connectAttr(node.output, bRoot.attr(attr), f=True)

			self.connected.append(bRoot)



	def disconnect(self):
		#disconnect  tmpJnts
		constraints = ['aimConstraint', 'orientConstraint', 'pointConstraint', 'parentConstraint']
		for conObj in self.connected:
			for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']:
				connections = conObj.attr(attr).inputs()
				if not connections:
					continue
				connectedTo = connections[0]
				if connectedTo.type() not in constraints and conObj.attr(attr).isLocked() == False:
					conObj.attr(attr).disconnect()
		pm.delete(self.nodes)
				

class TempJoint(object):
	''' 
	Template Joint base class 
	'''
	def __init__(self, name='', pos='', radius=0.1, color=11, position=(0.0, 0.0, 0.0), jnt=None):
		self.name = name
		self.pos = pos
		self.radius = radius
		self.color = color
		self.tmpJnt = jnt
		self.position = position
		self.axis = []
		#self.templateGrp, self.templateMainCtrl = None, None
		#self.createtmpJnt()

	def create(self):
		tmpJntName = misc.nameObj(elem='TEMP_%s' %self.name, pos=self.pos, typ='tmpJnt')
		self.tmpJnt =  pm.sphere(name=tmpJntName, r=self.radius, ch=False)[0]

		#attrs
		misc.addStrAttr(self.tmpJnt, '_TYPE', txt='tmpJnt', lock=True)
		misc.addStrAttr(self.tmpJnt, '_LABEL', txt=self.name, lock=True)
		misc.addMsgAttr(self.tmpJnt, '_PARENT')
		misc.addMsgAttr(self.tmpJnt, '_CHILD')
		misc.addMsgAttr(self.tmpJnt, '_MIRRORED')

		#connect radius
		self.connectScale()

		#change color
		tmpJntShp = self.tmpJnt.getShape()
		instObjGrpAttr = tmpJntShp.instObjGroups[0]
		instObjGrpAttr.disconnect()
		tmpJntShp.overrideEnabled.set(True)
		tmpJntShp.overrideColor.set(self.color)
		tmpJntShp.overrideShading.set(False)

		#create axis
		self.axisTemp()
		self.connectAxisVis()

		#create pivot loc
		self.pivotLoc()

		#put to position
		pm.xform(self.tmpJnt, ws=True, t=self.position)
	
	def connectAxisVis(self):
		axisVisAttr = misc.addNumAttr(self.tmpJnt, 'showAxis', 'float', dv=1.0, min=0.0)
		for a in self.axis:
			pm.connectAttr(axisVisAttr, a.visibility)

	def pivotLoc(self):
		locName = misc.nameObj(elem='TEMP_%s' %self.name, pos=self.pos, typ='pivLoc')
		self.pivLoc = pm.spaceLocator()
		self.pivLoc.rename(locName)
		self.pivLoc.localScale.set([0,0,0])
		misc.setDisplayType(self.pivLoc, disType='ref', shp=True)
		pm.parent(self.pivLoc, self.tmpJnt)

	def axisTemp(self):
		xCy = pm.cylinder(name='X', radius=self.radius*0.075, heightRatio=self.radius*370, ch=False)[0]
		yCy = pm.cylinder(name='Y', radius=self.radius*0.075, heightRatio=self.radius*370, ch=False)[0]
		zCy = pm.cylinder(name='Z', radius=self.radius*0.075, heightRatio=self.radius*370, ch=False)[0]
		xCvs = xCy.cv
		yCvs = yCy.cv
		zCvs = zCy.cv

		pm.xform(yCvs, r=True, os=True, ro=[0,0,90])
		pm.xform(zCvs, r=True, os=True, ro=[0,90,0])

		pm.xform(xCvs, r=True, os=True, wd=True, t=[self.radius*1.3125, 0, 0])
		pm.xform(yCvs, r=True, os=True, wd=True, t=[0, self.radius*1.3125, 0])
		pm.xform(zCvs, r=True, os=True, wd=True, t=[0, 0, self.radius*1.3125])
		
		axisShps = []
		#change color
		for axis, color in zip([xCy, yCy, zCy], [13, 14, 6]):
			axisShp = axis.getShape()
			instObjGrpAttr = axisShp.instObjGroups[0]
			instObjGrpAttr.disconnect()
			axisShp.overrideEnabled.set(True)
			axisShp.overrideColor.set(color)
			axisShps.append(axisShp)

		self.axis = axisShps
		pm.parent(axisShps, self.tmpJnt, r=True, s=True)
		pm.delete([xCy, yCy, zCy])

	def connectScale(self):
		radAttr = misc.addNumAttr(self.tmpJnt, 'radius', 'float', dv=1.0, min=0.0)
		pm.connectAttr(radAttr, self.tmpJnt.sx)
		pm.connectAttr(radAttr, self.tmpJnt.sy)
		pm.connectAttr(radAttr, self.tmpJnt.sz)

		self.tmpJnt.scaleX.setLocked(True)
		self.tmpJnt.scaleY.setLocked(True)
		self.tmpJnt.scaleZ.setLocked(True)
		self.tmpJnt.visibility.setLocked(True)

		self.tmpJnt.scaleX.setKeyable(False)
		self.tmpJnt.scaleY.setKeyable(False)
		self.tmpJnt.scaleZ.setKeyable(False)
		self.tmpJnt.visibility.setKeyable(False)

		self.tmpJnt.scaleX.showInChannelBox(False)
		self.tmpJnt.scaleY.showInChannelBox(False)
		self.tmpJnt.scaleZ.showInChannelBox(False)
		self.tmpJnt.visibility.showInChannelBox(False)

	def setTempScale(self, mult=1):
		if not self.rootCtrl:
			return
		self.rootCtrl.sx.set(self.scale*mult)
		self.rootCtrl.sy.set(self.scale*mult)
		self.rootCtrl.sz.set(self.scale*mult)

class TempJoints(TempJoint):
	''' 
	Template Joint chain class.
	'''
	def __init__(self, names=[], positions=[], ctrlShape='crossCircle', ctrlAxis = '+y', scale=1, mult=1, num=1, gap=0.1):
		TempJoint.__init__(self)

		self.names = names
		self.positions = positions	
		self.ctrlShape = ctrlShape
		self.scale = scale
		self.ctrlAxis = ctrlAxis
		self.mult = mult
		self.mirrorConObj = None
		self.createPosition = [0,0,0]
		self.num = num
		self.gap = gap
		self.tmpJnts = []
		self.tmpJntDict = {}
		self.nameDict = {}
		self.aimVec = []
		self.upVec = []
		
	def create(self, positions, parentChain=True):
		self.createRoot()
		
		i = 0
		for name, position in zip(self.names, positions):
			#singleJnt = TempJoint(elem=name, pos=self.pos, position=position, radius=self.radius, color=self.color)

			#create tmpJnt
			self.name = name
			TempJoint.create(self)

			#put to position
			pm.xform(self.tmpJnt, ws=True, t=position)

			self.tmpJnts.append(self.tmpJnt)

			if i > 0 and parentChain == True:
				parent = self.tmpJnts[i - 1]
				self.arrow(pointTo=self.tmpJnts[i], pointFrom=parent, elem='TEMP_%s__%s%s' %(self.names[i-1], name, self.pos))
				self.parent(child=self.tmpJnts[i], parent=parent)

			i += 1
		pm.xform(self.rootCtrl, ws=True, t=positions[0])


	def arrow(self, pointTo, pointFrom, elem):
		for obj in [pointTo, pointFrom]:
			try:
				if obj._TYPE.get() not in ['tmpJnt', 'tmpHelper']:
					return
			except:
				return
				
		#annotation
		misc.annPointer(pointFrom=pointFrom, pointTo=pointTo, ref=True, constraint=False, nameParts=elem)

	def aimToChild(self, aimAxis=[0,1,0], upAxis=[0,0,1], objUpAxis=[0,0,1], upObj=None):
		if not upObj:
			upObj = self.rootCtrl
			if not upObj:
				return

		for tmpJnt in self.tmpJnts:
			childs = tmpJnt._CHILD.outputs()
			if childs:
				misc.lockAttr(tmpJnt, t=False, r=True, lock=False)
				pm.aimConstraint(childs[0], tmpJnt, aimVector=aimAxis, upVector=upAxis, worldUpType='objectrotation', 
								worldUpVector=objUpAxis, worldUpObject=upObj)

	def parent(self, child, parent):
		pm.connectAttr(parent._CHILD, child._PARENT, f=True)

	# def multPosition(self, positions):
	# 	newPositions = []
	# 	for pos in positions:
	# 		pos = map(lambda x: x*self.scale, pos)
	# 		newPositions.append(pos)
	# 	return newPositions

	def createRoot(self):
		self.getCreatePosition()
		self.rootCtrl = ctrl.Controller(name=misc.nameObj(elem='TEMP_%s' %self.elem,pos=self.pos, typ='ctrl'), st=self.ctrlShape, 
						scale=0.5, axis=self.ctrlAxis)
		self.rootCtrl.setColor('yellow')
		self.rootCtrl.lockAttr(v=True)
		self.rootCtrl.hideAttr(v=True)

		misc.addStrAttr(self.rootCtrl, '_SUBTYPE', 'TEMP_Controller', lock=True)
		misc.addStrAttr(self.rootCtrl, '_TEMPLATE', self.__name__, lock=True)
		misc.addStrAttr(self.rootCtrl, 'elem', self.elem, lock=True)
		misc.addStrAttr(self.rootCtrl, 'pos', self.pos, lock=True)
		misc.addStrAttr(self.rootCtrl, 'tempScale', self.scale, lock=True)
		misc.addStrAttr(self.rootCtrl, 'tempJntNum' , self.num, lock=True)
		misc.addStrAttr(self.rootCtrl, 'ctrlAxis' , self.ctrlAxis, lock=True)

		misc.addMsgAttr(self.rootCtrl, 'subCtrls')
		misc.addMsgAttr(self.rootCtrl, '_MIRRORED')

	def getTmpJntWorldOrient(self, aimVec, upVec):

		aimVec = pm.dt.Vector(aimVec)
		upVec = pm.dt.Vector(upVec)
		cross = aimVec.cross(upVec)

		matrixV =	[cross.x , cross.y , cross.z , 0 , 
					aimVec.x*self.mult ,aimVec.y*self.mult , aimVec.z*self.mult, 0 ,
					upVec.x , upVec.y , upVec.z, 0,
					0,0,0,1]

		matrixM = OpenMaya.MMatrix()
		OpenMaya.MScriptUtil.createMatrixFromList(matrixV , matrixM)
		matrixFn = OpenMaya.MTransformationMatrix(matrixM)
		rot = matrixFn.eulerRotation()
		rotValues = [pm.dt.degrees(rot.x), pm.dt.degrees(rot.y), pm.dt.degrees(rot.z)]
		return rotValues

	def multPositions(self):
		newPos = []
		for pos in self.positions:
			pos = [pos[0]*self.mult, pos[1], pos[2]]
			newPos.append(pos)
		self.positions = newPos

	def getCreatePosition(self):
		sel = misc.getSel(num='inf')
		if not sel:
			self.createPosition = [0,0,0]
			return 

		pm.setToolTo('moveSuperContext') 
		pos = pm.manipMoveContext('Move', q=True, p=True)
		#pos = pm.xform(sel, q=True, ws=True, t=True)
		self.createPosition = pos


	def generateName(self):
		if not self.elem:
			self.elem = 'Limb'
		names = []
		for i in range(0, self.num):
			name = '%s%s' %(self.elem, str(i+1).zfill(2))
			names.append(name)
		return names

	def generatePositions(self):
		pos = []
		for i in range(0, self.num):
			tr = list(self.aimVec * self.gap*(i+1))
			pos.append(tr)

		return pos
			

	def report(self, objs, attr):
		for obj in objs:
			source = misc.addMsgAttr(self.rootCtrl, attr)
			destination = misc.addMsgAttr(obj, 'tmpRoot')
			if pm.isConnected(source, destination) == False:
				pm.connectAttr(source, destination, f=True)





########################################################################################################################################
########################################################################################################################################
########################################################################################################################################
####################################################### TEMPLATE CLASSES ###############################################################
########################################################################################################################################
########################################################################################################################################
########################################################################################################################################

_CUSTOMIZEABLE_JNT_NUM_CLS = ['YChain_BipedSpline', 'ZChain_Tail', 'ZChain_QuardrupedSpline', 'XChain_Finger']


class Single_WorldPivot(TempJoints):

	def __init__(self, positions=[[0,0,0]], elem='root', pos='', scale=1):
		TempJoints.__init__(self)

		self.__name__ = 'Single_WorldPivot'
		self.names = [elem]
		self.pos = pos
		self.positions = positions
		self.elem = elem
		self.scale = scale
		self.ctrlShape = 'crossSphere'

	def create(self):
		#create tmpJnt_rootCtrl
		TempJoints.create(self, self.positions)
		misc.lockAttr(self.tmpJnts[0], t=False, r=True)
		misc.hideAttr(self.tmpJnts[0], t=False, r=True)
		pm.parent(self.tmpJnts, self.rootCtrl)

		pm.xform(self.rootCtrl, ws=True, t=self.createPosition)
		pm.select(self.rootCtrl, r=True)
		self.report(self.tmpJnts, 'tmpJnts')
		self.setTempScale()

class Single_XAimedPivot(TempJoints):

	def __init__(self, positions=[[0,0,0]], elem='clav', pos='', scale=1):
		TempJoints.__init__(self)
		self.__name__ = 'Single_XAimedPivot'
		self.names = [elem]
		self.pos = pos
		self.positions = positions
		self.elem = elem
		self.scale = scale
		self.ctrlShape = 'square'
		self.tmpJnts = []
		self.ctrlAxis = '+x'
		self.subCtrls = {}

		self.drawVec = pm.dt.Vector([1, 0, 0])
		self.aimVec = pm.dt.Vector([0, 1, 0])
		self.upVec = pm.dt.Vector([0, 0, 1])
		self.objUpVec = pm.dt.Vector([0, 1, 0])

	def create(self):
		self.drawVec = self.drawVec * self.mult
		self.aimVec = self.aimVec * self.mult
		self.upVec = self.upVec * self.mult
		#self.objUpVec = self.objUpVec * self.mult

		#create tmpJnt
		TempJoints.create(self, self.positions)
		#create aim loc
		self.aimLoc = pm.spaceLocator(n='%s%s_aimLoc' %(self.names[0], self.pos))
		misc.addStrAttr(self.aimLoc, 'elem', 'aimLoc', True)
		self.aimLoc.getShape().localScale.set(self.scale*0.3, self.scale*0.3, self.scale*0.3)
		
		locPos = (self.drawVec * self.scale) + self.positions[0]
		pm.xform(self.aimLoc, ws=True, t=locPos)
		misc.lockAttr(self.aimLoc, t=False, r=True, s=True, v=True)
		misc.hideAttr(self.aimLoc, t=False, r=True, s=True, v=True)
		misc.addStrAttr(self.aimLoc, '_TYPE', txt='tmpHelper', lock=True)

		#aim to helper
		#mult = float((self.positions[0] - self.drawVec).dot(pm.dt.Vector(-1,-1,-1)))

		pm.aimConstraint(self.aimLoc, self.tmpJnts[0], aimVector=self.aimVec, 
						upVector=self.upVec, worldUpType='objectrotation', worldUpVector=self.objUpVec, 
						worldUpObject=self.rootCtrl)

		#create annotation
		self.arrow(pointTo=self.aimLoc, pointFrom=self.tmpJnts[0], elem='%s%s' %(self.elem, self.pos))

		#clean up
		#misc.lockAttr(self.tmpJnts[0], r=True) <<<fuck! this crash maya everytime I hit undo and create again
		misc.hideAttr(self.tmpJnts[0], t=False, r=True)

		pm.parent(self.tmpJnts, self.rootCtrl)
		pm.parent(self.aimLoc, self.rootCtrl)
		pm.xform(self.rootCtrl, ws=True, t=self.createPosition)
		pm.select(self.rootCtrl, r=True)

		#append aimLoc to helper
		self.subCtrls['aimLoc'] = self.aimLoc

		self.report(self.tmpJnts, 'tmpJnts')
		self.report([self.aimLoc], 'subCtrls')
		self.setTempScale()


class Single_mYAimedPivot(Single_XAimedPivot):

	def __init__(self, positions=[[0,0,0]], elem='clav', pos='', scale=1):
		Single_XAimedPivot.__init__(self, positions=positions, elem=elem, pos=pos, scale=scale)
		self.__name__ = 'Single_mYAimedPivot'

		self.ctrlAxis = '-y'

		self.drawVec = pm.dt.Vector([0, -1, 0])
		self.aimVec = pm.dt.Vector([0, 1, 0])
		self.upVec = pm.dt.Vector([0, 0, 1])
		self.objUpVec = pm.dt.Vector([0, 0, 1])

class Single_YAimedPivot(Single_XAimedPivot):

	def __init__(self, positions=[[0,0,0]], elem='clav', pos='', scale=1):
		Single_XAimedPivot.__init__(self, positions=positions, elem=elem, pos=pos, scale=scale)
		self.__name__ = 'Single_YAimedPivot'

		self.ctrlAxis = '+y'

		self.drawVec = pm.dt.Vector([0, 1, 0])
		self.aimVec = pm.dt.Vector([0, 1, 0])
		self.upVec = pm.dt.Vector([0, 0, 1])
		self.objUpVec = pm.dt.Vector([0, 0, 1])

class Single_ZAimedPivot(Single_XAimedPivot):

	def __init__(self, positions=[[0,0,0]], elem='clav', pos='', scale=1):
		Single_XAimedPivot.__init__(self, positions=positions, elem=elem, pos=pos, scale=scale)
		self.__name__ = 'Single_ZAimedPivot'

		self.ctrlAxis = '+z'

		self.drawVec = pm.dt.Vector([0, 0, 1])
		self.aimVec = pm.dt.Vector([0, 0, 1])
		self.upVec = pm.dt.Vector([0, 1, 0])
		self.objUpVec = pm.dt.Vector([0, 1, 0])

class YChain_BipedSpline(TempJoints):

	def __init__(self, names=[], positions=(), elem='spline', gap=1.7, num=4, pos='', scale=1):	
		TempJoints.__init__(self, names, positions)

		self.__name__ = 'YChain_BipedSpline'
		self.elem = elem
		self.pos = pos
		self.num = num
		self.scale = scale
		self.gap = gap * self.scale
		self.rootCtrl = None
		self.ctrlShape = 'crossCircle'
		self.tmpJnts = []

		#self.drawAxis = pm.dt.Vector([0, 1, 0])
		self.ctrlAxis = '+y'
		self.aimVec = pm.dt.Vector([0, 1, 0])
		self.upVec = pm.dt.Vector([0, 0, 1])


	def create(self):
		#generate names and positions
		self.names = self.generateName()
		self.positions = self.generatePositions()

		rotValues = self.getTmpJntWorldOrient(aimVec=list(self.aimVec), upVec=list(self.upVec))

		#create tmpJnt_rootCtrl
		TempJoints.create(self, positions=self.positions, parentChain=True)
		for jnt in self.tmpJnts:
			#misc.snapTransform('orient', self.rootCtrl, jnt, True, False)
			#pm.orientConstraint(self.rootCtrl, jnt, mo=True)
			pm.xform(jnt, ws=True, ro=rotValues)
			misc.lockAttr(jnt, t=False, r=True)
			misc.hideAttr(jnt, t=False, r=True)	
		pm.parent(self.tmpJnts, self.rootCtrl)

		pm.xform(self.rootCtrl, ws=True, t=self.createPosition)
		pm.select(self.rootCtrl, r=True)

		self.report(self.tmpJnts, 'tmpJnts')
		self.setTempScale()

class ZChain_Tail(YChain_BipedSpline):

	def __init__(self, names=[], positions=(), elem='tail', gap=1.7, num=4, pos='', scale=1):
		YChain_BipedSpline.__init__(self, names, positions, elem=elem, gap=gap, num=num, pos=pos, scale=scale)
		
		self.__name__ = 'ZChain_Tail'
		self.elem = elem
		# self.drawAxis = pm.dt.Vector([0, 0, -1])
		self.ctrlAxis = '-z'
		self.aimVec = pm.dt.Vector([0, 0, -1])
		self.upVec = pm.dt.Vector([0, 1, 0])


class ZChain_QuardrupedSpline(YChain_BipedSpline):

	def __init__(self, names=[], positions=(), elem='spline', gap=1.7, num=2, pos='', scale=1):
		YChain_BipedSpline.__init__(self, names, positions, elem=elem, gap=gap, num=num, pos=pos, scale=scale)
		
		self.__name__ = 'ZChain_QuardrupedSpline'
		self.elem = elem
		# self.drawAxis = pm.dt.Vector([0, 0, -1])
		self.ctrlAxis = '+z'
		self.aimVec = pm.dt.Vector([0, 0, 1])
		self.upVec = pm.dt.Vector([0, 1, 0])

class Arm_PV(TempJoints):

	def __init__(self, names=['upArm', 'foreArm', 'wrist', 'elbowIk'], 
				positions=([0,0,0], [4, 0, -0.4], [8, 0, 0], [4, 0, -4]), 
				elem='arm', pos='', ctrlAxis='+x'):
		TempJoints.__init__(self, names, positions)

		self.__name__ = 'Arm_PV'
		self.names = names
		self.pos = pos
		self.positions = positions
		self.elem = elem
		self.scale = 1
		self.rootCtrl = None
		self.ctrlShape = 'crossCircle'
		self.ctrlAxis = ctrlAxis
		self.tmpJntDict = {}

	def create(self):
		#figure out rotations...
		rotValues = self.getTmpJntWorldOrient(aimVec=[1*self.mult,0,0], upVec=[0,0,1])

		#create tmpJnts
		TempJoints.create(self, self.positions, parentChain=False)

		#crate tmpJntDict
		dictKeys = ['base', 'mid', 'tip','pv']
		for key, name, jnt in zip(dictKeys, self.names, self.tmpJnts):
			self.tmpJntDict[name] = jnt
			self.nameDict[key] = name
			pm.xform(jnt, ws=True, ro=rotValues)
			jnt.translateY.setLocked(True)
			misc.lockAttr(jnt, t=False, r=True)
			misc.hideAttr(jnt, t=False, r=True)

		#parent	
		self.parent(child=self.tmpJnts[1], parent=self.tmpJnts[0])
		self.parent(child=self.tmpJnts[2], parent=self.tmpJnts[1])
		self.parent(child=self.tmpJnts[3], parent=self.tmpJnts[1])

		self.arrow(pointTo=self.tmpJnts[1], pointFrom=self.tmpJnts[0], elem='%s%s' %(self.nameDict['mid'], self.pos))
		self.arrow(pointTo=self.tmpJnts[2], pointFrom=self.tmpJnts[1], elem='%s%s' %(self.nameDict['tip'], self.pos))
		self.arrow(pointTo=self.tmpJnts[3], pointFrom=self.tmpJnts[1], elem='%s%s' %(self.nameDict['pv'], self.pos))

		#connect PV
		pm.connectAttr(self.tmpJnts[1].translateX, self.tmpJnts[3].translateX)

		pm.parent(self.tmpJnts, self.rootCtrl)
		pm.xform(self.rootCtrl, ws=True, t=self.createPosition)
		pm.select(self.rootCtrl, r=True)

		self.report(self.tmpJnts, 'tmpJnts')
		self.setTempScale()

class Leg_BipedPV(TempJoints):

	def __init__(self, names=['upLeg', 'knee', 'ankle', 'kneeIk', 'heel',
				'footIn', 'footOut', 'ball', 'toe'], 
				positions=([0,0,0], [0,-4,0.4], [0,-8,0], [0,-4,4], [0,-9,-1],
				[-1,-9,0], [1,-9,0], [0,-9,2], [0,-9,3]), 
				elem='leg', pos='', scale=1):
		TempJoints.__init__(self, names, positions)

		self.__name__ = 'Leg_BipedPV'
		self.names = names
		self.pos = pos
		self.positions = positions
		self.elem = elem
		self.scale = scale
		self.rootCtrl = None
		self.ctrlShape = 'crossCircle'
		self.ctrlAxis = '+x'
		
	def create(self):	
		#figure out rotations...
		rotValues = self.getTmpJntWorldOrient(aimVec=[0,-1,0], upVec=[0,0,1])
		toeRotValues = self.getTmpJntWorldOrient(aimVec=[0, 0, 1], upVec=[0, 1, 0])

		#create tmpJnts
		TempJoints.create(self, self.positions, parentChain=False)

		#crate tmpJntDict
		dictKeys = ['base', 'mid', 'tip','pv', 'heel', 'footIn', 'footOut', 'ball', 'toe']
		self.tmpJntDict = {}
		self.nameDict = {}
		for key, name, jnt in zip(dictKeys, self.names, self.tmpJnts):
			self.tmpJntDict[key] = jnt
			self.nameDict[key] = name
			if key in ['ball', 'toe']:
				rot = toeRotValues
			else:
				rot = rotValues
			pm.xform(jnt, ws=True, ro=rot)
			if key in ['footIn', 'footOut']:
				continue
			jnt.translateX.setLocked(True)
			misc.lockAttr(jnt, t=False, r=True)
			misc.hideAttr(jnt, t=False, r=True)

		#parent
		self.parent(child=self.tmpJntDict['mid'], parent=self.tmpJntDict['base'])
		self.arrow(pointTo=self.tmpJntDict['mid'], pointFrom=self.tmpJntDict['base'], elem='%s%s' %(self.nameDict['mid'], self.pos))

		self.parent(child=self.tmpJntDict['tip'], parent=self.tmpJntDict['mid'])
		self.arrow(pointTo=self.tmpJntDict['tip'], pointFrom=self.tmpJntDict['mid'], elem='%s%s' %(self.nameDict['tip'], self.pos))


		self.parent(child=self.tmpJntDict['pv'], parent=self.tmpJntDict['mid'])
		self.arrow(pointTo=self.tmpJntDict['pv'], pointFrom=self.tmpJntDict['mid'], elem='%s%s' %(self.nameDict['pv'], self.pos))


		self.parent(child=self.tmpJntDict['ball'], parent=self.tmpJntDict['tip'])
		self.arrow(pointTo=self.tmpJntDict['ball'], pointFrom=self.tmpJntDict['tip'], elem='%s%s' %(self.nameDict['ball'], self.pos))
		

		self.parent(child=self.tmpJntDict['heel'], parent=self.tmpJntDict['tip'])
		self.arrow(pointTo=self.tmpJntDict['heel'], pointFrom=self.tmpJntDict['tip'], elem='%s%s' %(self.nameDict['heel'], self.pos))


		self.parent(child=self.tmpJntDict['toe'], parent=self.tmpJntDict['ball'])
		self.arrow(pointTo=self.tmpJntDict['toe'], pointFrom=self.tmpJntDict['ball'], elem='%s%s' %(self.nameDict['toe'], self.pos))


		self.parent(child=self.tmpJntDict['footIn'], parent=self.tmpJntDict['tip'])
		self.arrow(pointTo=self.tmpJntDict['footIn'], pointFrom=self.tmpJntDict['tip'], elem='%s%s' %(self.nameDict['footIn'], self.pos))

		self.parent(child=self.tmpJntDict['footOut'], parent=self.tmpJntDict['tip'])
		self.arrow(pointTo=self.tmpJntDict['footOut'], pointFrom=self.tmpJntDict['tip'], elem='%s%s' %(self.nameDict['footOut'], self.pos))

		#connect PV
		pm.connectAttr(self.tmpJntDict['mid'].translateY, self.tmpJntDict['pv'].translateY, f=True)
		self.tmpJntDict['pv'].translateY.setKeyable(False)
		self.tmpJntDict['pv'].translateY.showInChannelBox(False)

		pm.parent(self.tmpJnts, self.rootCtrl)
		pm.xform(self.rootCtrl, ws=True, t=self.createPosition)
		pm.select(self.rootCtrl, r=True)

		self.report(self.tmpJnts, 'tmpJnts')
		self.setTempScale()

class XChain_Finger(TempJoints):

	def __init__(self, positions=([0,0,0], [0.5,0,0], [0.9,0,0], [1.3,0,0], [1.7,0,0]), 
				elem='finger', pos='', ctrlAxis='+x', scale=0.5, mult=1, num=5, gap=0.4):
		TempJoints.__init__(self, positions)

		self.__name__ = 'XChain_Finger'
		self.num = num
		self.gap = gap	
		self.pos = pos
		self.positions = positions
		self.elem = elem
		self.names = self.generateName()
		self.scale = scale
		self.rootCtrl = None
		self.ctrlShape = 'circle'
		self.ctrlAxis = ctrlAxis
		self.mult = mult

	def create(self):
		TempJoints.create(self, self.positions)

		rotValues = self.getTmpJntWorldOrient(aimVec=[1*self.mult,0,0], upVec=[0,1,0])
		for jnt in self.tmpJnts:
			pm.xform(jnt, ws=True, ro=rotValues)
			misc.lockAttr(jnt, t=False, r=True)
			misc.hideAttr(jnt, t=False, r=True)

		pm.parent(self.tmpJnts, self.rootCtrl)
		pm.xform(self.rootCtrl, ws=True, t=self.createPosition)
		pm.select(self.rootCtrl, r=True)

		self.report(self.tmpJnts, 'tmpJnts')
		self.setTempScale()

class Hand_5Finger(TempJoints):
	def __init__(self, names=['hand', 'thumb', 'index', 'middle', 'ring', 'pinky'] , 
				positions=[[0.3,0,0], [0.0,-0.35,0.7], [0.8,0,0.7], [0.8,0,0.25], [0.8,0,-0.25], [0.8,0,-0.7]], 
				elem='Hand', pos='', ctrlAxis='+x', scale=0.5):
		TempJoints.__init__(self, names, positions)

		self.__name__ = 'Hand_5Finger'
		self.names = names
		self.pos = pos
		self.positions = positions
		self.elem = elem
		self.scale = scale
		self.rootCtrl = None
		self.ctrlShape = 'cube'
		self.ctrlAxis = ctrlAxis
		self.subCtrls = {}

	def create(self):
		#create root hand jnt
		TempJoints.create(self, [self.positions[0]])
		self.tmpJntDict['hand'] = [self.tmpJnts[0]]

		rotValues = self.getTmpJntWorldOrient(aimVec=[1*self.mult,0,0], upVec=[0,0,1])
		pm.xform(self.tmpJntDict['hand'][0], ws=True, ro=rotValues)
		pm.parent(self.tmpJntDict['hand'], self.rootCtrl)
		
		#create all the fingers
		fingerNames = ['thumb', 'index', 'middle', 'ring', 'pinky']
		fingerPositions = self.positions[1:]
		fingerSection = 5
		for name,position in zip(fingerNames, fingerPositions):
			if name == 'thumb': fingerSection = 4
			else: fingerSection = 5
			fingerObj = XChain_Finger(elem=name, pos=self.pos, mult=self.mult, num=fingerSection, scale=self.scale*1.25)
			fingerObj.multPositions()
			fingerObj.create()
			self.tmpJnts.extend(fingerObj.tmpJnts)
			pm.xform(fingerObj.rootCtrl, ws=True, t=position)
			pm.parent(fingerObj.rootCtrl, self.rootCtrl)
			connectTempJnts(fingerObj.tmpJnts[0], self.tmpJntDict['hand'][0])
			self.subCtrls[name] = fingerObj.rootCtrl

		pm.xform(self.rootCtrl, ws=True, t=self.createPosition)
		pm.select(self.rootCtrl, r=True)

		self.report(self.tmpJnts, 'tmpJnts')
		self.report(self.subCtrls.values(), 'subCtrls')
		self.setTempScale()

class Head_JawEyes(TempJoints):

	def __init__(self, names=['head01', 'head02', 'eyeLFT', 'eyeRHT', 'eyeTrgtLFT', 'eyeTrgtRHT', 'eyeTrgt', 'jaw01LO', 'jaw02LO', 
				'jaw03LO', 'jaw01UP', 'jaw02UP'], 
				positions=([0,0,0], [0,2,0], [0.5,0.7,1.5], [-0.5,0.7,1.5], [0.5,0.7,10], [-0.5,0.7,10], [0,0.7,10], [0,0,0.4], [0,-1,0.4],
				[0,-1,2], [0,-0.7,0.4],[0,-0.7,2]), elem='Head', pos='', scale=1):

		self.__name__ = 'Head_JawEyes'
		TempJoints.__init__(self, names, positions)

		self.names = names
		self.positions = positions
		self.elem = elem
		self.pos = pos
		self.scale = scale
		self.rootCtrl = None
		self.ctrlShape = 'cube'
		self.nodes = []
		self.tmpJntDict = {}
		self.nameDict = {}

	def create(self):

		#create tmpJnt_rootCtrl
		TempJoints.create(self, positions=self.positions, parentChain=False)

		jntDic ={}
		jntDicKeys = ['head01', 'head02', 'eyeLFT', 'eyeRHT', 'eyeTrgtLFT', 'eyeTrgtRHT', 'eyeTrgt',
				 	'jaw01LO', 'jaw02LO', 'jaw03LO', 'jaw01UP', 'jaw02UP']
		for key, jnt in zip(jntDicKeys, self.tmpJnts):
			#misc.snapTransform('orient', self.rootCtrl, jnt, True, False)
			#pm.orientConstraint(self.rootCtrl, jnt, mo=True)
			#misc.lockAttr(jnt, r=True)
			misc.hideAttr(jnt, t=False, r=True)
			self.tmpJntDict[key] = jnt

		pm.parent(self.tmpJnts, self.rootCtrl)

		#parent head
		self.arrow(pointTo=self.tmpJntDict['head02'], pointFrom=self.tmpJntDict['head01'], elem='TEMP_%s__%s%s' %(self.tmpJntDict['head01'], self.tmpJntDict['head02'], self.pos))
		self.parent(child=self.tmpJntDict['head02'], parent=self.tmpJntDict['head01'])

		#parent eyeLFT eyeRHT
		self.arrow(pointTo=self.tmpJntDict['eyeLFT'], pointFrom=self.tmpJntDict['head01'], elem='TEMP_%s__%s%s' %(self.tmpJntDict['head01'], self.tmpJntDict['eyeLFT'], self.pos))
		self.parent(child=self.tmpJntDict['eyeLFT'], parent=self.tmpJntDict['head01'])

		self.arrow(pointTo=self.tmpJntDict['eyeRHT'], pointFrom=self.tmpJntDict['head01'], elem='TEMP_%s__%s%s' %(self.tmpJntDict['head01'], self.tmpJntDict['eyeRHT'], self.pos))
		self.parent(child=self.tmpJntDict['eyeRHT'], parent=self.tmpJntDict['head01'])

		#parent eyeTrgt
		self.arrow(pointTo=self.tmpJntDict['eyeTrgtLFT'], pointFrom=self.tmpJntDict['eyeTrgt'], elem='TEMP_%s__%s%s' %(self.tmpJntDict['eyeTrgt'], self.tmpJntDict['eyeTrgtLFT'], self.pos))
		self.parent(child=self.tmpJntDict['eyeTrgtLFT'], parent=self.tmpJntDict['eyeTrgt'])

		self.arrow(pointTo=self.tmpJntDict['eyeTrgtRHT'], pointFrom=self.tmpJntDict['eyeTrgt'], elem='TEMP_%s__%s%s' %(self.tmpJntDict['eyeTrgt'], self.tmpJntDict['eyeTrgtRHT'], self.pos))
		self.parent(child=self.tmpJntDict['eyeTrgtRHT'], parent=self.tmpJntDict['eyeTrgt'])

		self.arrow(pointTo=self.tmpJntDict['eyeTrgt'], pointFrom=self.tmpJntDict['head01'], elem='TEMP_%s__%s%s' %(self.tmpJntDict['head01'], self.tmpJntDict['eyeTrgt'], self.pos))
		self.parent(child=self.tmpJntDict['eyeTrgt'], parent=self.tmpJntDict['head01'])

		#parent jaw
		self.arrow(pointTo=self.tmpJntDict['jaw03LO'], pointFrom=self.tmpJntDict['jaw02LO'], elem='TEMP_%s__%s%s' %(self.tmpJntDict['jaw02LO'], self.tmpJntDict['jaw03LO'], self.pos))
		self.parent(child=self.tmpJntDict['jaw03LO'], parent=self.tmpJntDict['jaw02LO'])

		self.arrow(pointTo=self.tmpJntDict['jaw02LO'], pointFrom=self.tmpJntDict['jaw01LO'], elem='TEMP_%s__%s%s' %(self.tmpJntDict['jaw01LO'], self.tmpJntDict['jaw02LO'], self.pos))
		self.parent(child=self.tmpJntDict['jaw02LO'], parent=self.tmpJntDict['jaw01LO'])

		self.arrow(pointTo=self.tmpJntDict['jaw01LO'], pointFrom=self.tmpJntDict['head01'], elem='TEMP_%s__%s%s' %(self.tmpJntDict['head01'], self.tmpJntDict['jaw01LO'], self.pos))
		self.parent(child=self.tmpJntDict['jaw01LO'], parent=self.tmpJntDict['head01'])

		self.arrow(pointTo=self.tmpJntDict['jaw02UP'], pointFrom=self.tmpJntDict['jaw01UP'], elem='TEMP_%s__%s%s' %(self.tmpJntDict['jaw01UP'], self.tmpJntDict['jaw02UP'], self.pos))
		self.parent(child=self.tmpJntDict['jaw02UP'], parent=self.tmpJntDict['jaw01UP'])

		self.arrow(pointTo=self.tmpJntDict['jaw01UP'], pointFrom=self.tmpJntDict['head01'], elem='TEMP_%s__%s%s' %(self.tmpJntDict['head01'], self.tmpJntDict['jaw01UP'], self.pos))
		self.parent(child=self.tmpJntDict['jaw01UP'], parent=self.tmpJntDict['head01'])

		#up jaw are special need to flip axis
		upPos = pm.xform(self.tmpJntDict['jaw01UP'], q=True, ws=True, t=True)
		loPos = pm.xform(self.tmpJntDict['jaw01LO'], q=True, ws=True, t=True)
		rotValues = self.getTmpJntWorldOrient(aimVec=[0,-1,0], upVec=[0,0,1])

		#set rotate values
		pm.xform([self.tmpJntDict['jaw01UP'], self.tmpJntDict['jaw02UP']], ws=True, ro=rotValues)

		#connect and actual parent for easy placing
		self.node = createMdl('eyeLFT', 'eyeRHT', 'TX')
		pm.connectAttr(self.tmpJntDict['eyeLFT'].tx, self.node.input1)
		pm.connectAttr(self.node.output, self.tmpJntDict['eyeRHT'].tx)
		pm.connectAttr(self.tmpJntDict['eyeLFT'].ty, self.tmpJntDict['eyeRHT'].ty)
		pm.connectAttr(self.tmpJntDict['eyeLFT'].tz, self.tmpJntDict['eyeRHT'].tz)

		pm.connectAttr(self.tmpJntDict['eyeLFT'].tx, self.tmpJntDict['eyeTrgtLFT'].tx)
		pm.connectAttr(self.tmpJntDict['eyeLFT'].ty, self.tmpJntDict['eyeTrgtLFT'].ty)

		pm.connectAttr(self.tmpJntDict['eyeRHT'].tx, self.tmpJntDict['eyeTrgtRHT'].tx)
		pm.connectAttr(self.tmpJntDict['eyeRHT'].ty, self.tmpJntDict['eyeTrgtRHT'].ty)

		pm.connectAttr(self.tmpJntDict['eyeLFT'].ty, self.tmpJntDict['eyeTrgt'].ty)
		pm.connectAttr(self.tmpJntDict['eyeTrgt'].tz, self.tmpJntDict['eyeTrgtLFT'].tz)
		pm.connectAttr(self.tmpJntDict['eyeTrgt'].tz, self.tmpJntDict['eyeTrgtRHT'].tz)

		self.tmpJntDict['eyeTrgt'].tx.setLocked(True)
		self.tmpJntDict['eyeTrgt'].ty.setLocked(True)
		self.tmpJntDict['eyeTrgtLFT'].translate.setLocked(True)
		self.tmpJntDict['eyeTrgtRHT'].translate.setLocked(True)


		pm.xform(self.rootCtrl, ws=True, t=self.createPosition)
		pm.select(self.rootCtrl, r=True)

		self.report(self.tmpJnts, 'tmpJnts')
		self.report([self.nodes], 'nodes')
		self.setTempScale()



class Leg_QuardrupedPV(TempJoints):

	def __init__(self, names=['upLeg', 'knee', 'lowLeg', 'ankle', 'kneeIk', 'heel',
				'footIn', 'footOut', 'ball', 'toe'], 
				positions=([0,0,0], [0,-2,0.5], [0,-4,-0.4], [0,-8,0], [0,-4,4], [0,-9,-1],
				[-1,-9,0], [1,-9,0], [0,-9,2], [0,-9,3]), 
				elem='leg', pos='', scale=1):
		TempJoints.__init__(self, names, positions)

		self.__name__ = 'Leg_QuardrupedPV'
		self.names = names
		self.pos = pos
		self.positions = positions
		self.elem = elem
		self.scale = scale
		self.rootCtrl = None
		self.ctrlShape = 'crossCircle'
		self.ctrlAxis = '+x'
		
	def create(self):	
		#figure out rotations...
		rotValues = self.getTmpJntWorldOrient(aimVec=[0,-1,0], upVec=[0,0,1])
		toeRotValues = self.getTmpJntWorldOrient(aimVec=[0, 0, 1], upVec=[0, 1, 0])

		#create tmpJnts
		TempJoints.create(self, self.positions, parentChain=False)

		#crate tmpJntDict
		dictKeys = ['base', 'mid', 'low', 'tip','pv', 'heel', 'footIn', 'footOut', 'ball', 'toe']
		self.tmpJntDict = {}
		self.nameDict = {}
		for key, name, jnt in zip(dictKeys, self.names, self.tmpJnts):
			self.tmpJntDict[key] = jnt
			self.nameDict[key] = name
			if key in ['ball', 'toe']:
				rot = toeRotValues
			else:
				rot = rotValues
			pm.xform(jnt, ws=True, ro=rot)
			if key in ['footIn', 'footOut']:
				continue
			jnt.translateX.setLocked(True)
			misc.lockAttr(jnt, t=False, r=True)
			misc.hideAttr(jnt, t=False, r=True)

		#parent
		self.parent(child=self.tmpJntDict['mid'], parent=self.tmpJntDict['base'])
		self.arrow(pointTo=self.tmpJntDict['mid'], pointFrom=self.tmpJntDict['base'], elem='%s%s' %(self.nameDict['mid'], self.pos))

		self.parent(child=self.tmpJntDict['low'], parent=self.tmpJntDict['mid'])
		self.arrow(pointTo=self.tmpJntDict['low'], pointFrom=self.tmpJntDict['mid'], elem='%s%s' %(self.nameDict['low'], self.pos))


		self.parent(child=self.tmpJntDict['tip'], parent=self.tmpJntDict['low'])
		self.arrow(pointTo=self.tmpJntDict['tip'], pointFrom=self.tmpJntDict['low'], elem='%s%s' %(self.nameDict['tip'], self.pos))


		self.parent(child=self.tmpJntDict['pv'], parent=self.tmpJntDict['mid'])
		self.arrow(pointTo=self.tmpJntDict['pv'], pointFrom=self.tmpJntDict['mid'], elem='%s%s' %(self.nameDict['pv'], self.pos))


		self.parent(child=self.tmpJntDict['ball'], parent=self.tmpJntDict['tip'])
		self.arrow(pointTo=self.tmpJntDict['ball'], pointFrom=self.tmpJntDict['tip'], elem='%s%s' %(self.nameDict['ball'], self.pos))
		

		self.parent(child=self.tmpJntDict['heel'], parent=self.tmpJntDict['tip'])
		self.arrow(pointTo=self.tmpJntDict['heel'], pointFrom=self.tmpJntDict['tip'], elem='%s%s' %(self.nameDict['heel'], self.pos))


		self.parent(child=self.tmpJntDict['toe'], parent=self.tmpJntDict['ball'])
		self.arrow(pointTo=self.tmpJntDict['toe'], pointFrom=self.tmpJntDict['ball'], elem='%s%s' %(self.nameDict['toe'], self.pos))


		self.parent(child=self.tmpJntDict['footIn'], parent=self.tmpJntDict['tip'])
		self.arrow(pointTo=self.tmpJntDict['footIn'], pointFrom=self.tmpJntDict['tip'], elem='%s%s' %(self.nameDict['footIn'], self.pos))

		self.parent(child=self.tmpJntDict['footOut'], parent=self.tmpJntDict['tip'])
		self.arrow(pointTo=self.tmpJntDict['footOut'], pointFrom=self.tmpJntDict['tip'], elem='%s%s' %(self.nameDict['footOut'], self.pos))

		#connect PV
		pm.connectAttr(self.tmpJntDict['mid'].translateY, self.tmpJntDict['pv'].translateY, f=True)
		self.tmpJntDict['pv'].translateY.setKeyable(False)
		self.tmpJntDict['pv'].translateY.showInChannelBox(False)

		pm.parent(self.tmpJnts, self.rootCtrl)
		pm.xform(self.rootCtrl, ws=True, t=self.createPosition)
		pm.select(self.rootCtrl, r=True)

		self.report(self.tmpJnts, 'tmpJnts')
		self.setTempScale()