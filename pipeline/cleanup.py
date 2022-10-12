import pymel.core as pm
import maya.cmds as mc
import maya.OpenMaya as om
import maya.mel as mel

from nuTools import misc
reload(misc)

from nuTools.pipeline import pipeTools
reload(pipeTools)

TOP_GRP = 'Rig_Grp'
EXCEPTIONS = ['Geo_Grp']
CONSTRAINT_TYPES = ['parentConstraint', 'orientConstraint', 'pointConstraint', 'scaleConstraint', 'pairBlend']

class AnimatedController(object):
	def __init__(self, ctrl):
		self._ctrl = ctrl
		self._parent = ctrl.getParent()
		self._ctrlShape = None
		if ctrl.hasAttr('getShape'):
			self._ctrlShape = ctrl.getShape(ni=True)

		self.ctrlShortName = self._ctrl.nodeName()
		self.ctrlLongName = getRefFullPath(self._ctrl)

		self.ctrlShapeShortName = ''
		self.ctrlShapeLongName = ''
		if self._ctrlShape:
			self.ctrlShapeShortName = self._ctrlShape.nodeName()
			self.ctrlShapeLongName = '%s|%s' %(self.ctrlLongName, self.ctrlShapeShortName)

		if self._parent:
			self.parentShortName = self._parent.nodeName()
			self.parentLongName = getRefFullPath(self._parent)
		
		self.ctrlAttrs = {}  # {attrName:value, ...}
		self.ctrlShapeAttrs = {}
		self.ctrlParentAttrs = {}

		self.inConnections = []  # [(ctrlAttrLn, srcAttr), ...] 
		self.outConnections = []  # [(ctrlAttrLn, desAttr), ...] 
		self.constraints = {}  # {consNode:{'index':indx, 'tr':(), 'ro':()}}

	def getPipelineStringInfo(self):
		pipelineAttrs = [a for a in self._ctrl.listAttr(ud=True, u=True, se=True, cfo=True) if a.type()=='string']
		for attr in pipelineAttrs:
			attrLn = '%s.%s' %(self.ctrlLongName, attr.longName(fullPath=True))
			self.ctrlAttrs[attrLn] = attr.get()

	def getInfo(self):
		# --- get set attributes
		ctrlAttrs = self._ctrl.listAttr(k=True, u=True, se=True)
		for attr in ctrlAttrs:
			if not pm.objExists(attr):
				continue
			if not attr.inputs():  # only get non-connected attribute
				ctrlAttrLn = '%s.%s' %(self.ctrlLongName, attr.longName(fullPath=True))
				self.ctrlAttrs[ctrlAttrLn] = attr.get()

		if self._ctrlShape:
			ctrlShapeAttrs = self._ctrlShape.listAttr(v=True, se=True, ud=True, u=True, cb=True)
			for attr in ctrlShapeAttrs:
				if not pm.objExists(attr):
					continue
				if not attr.inputs():  # only get non-connected attribute
					ctrlShpAttrLn = '%s|%s.%s' %(self.ctrlLongName, self.ctrlShapeShortName, attr.longName(fullPath=True))
					self.ctrlShapeAttrs[ctrlShpAttrLn] = attr.get()

		#----- get input and output constraints
		# input constraints
		ctrlConsIns = self._ctrl.parentInverseMatrix.outputs(type=CONSTRAINT_TYPES)
		for consNode in [n for n in ctrlConsIns if not n.isReferenced()]:
			# only check for constraint which has outputs to the control, skipping those false ones
			# if self._ctrl in consNode.listHistory(f=True, allFuture=True):
			self.constraints[consNode] = {'parent': self.ctrlLongName}
			# else:
			# 	try:
			# 		om.MGlobal.displayWarning('Deleting unused constarint on: %s %s' %(self.ctrlShortName, consNode.nodeName()))
			# 		pm.delete(consNode)
			# 	except RuntimeError, e:
			# 		print e
		if self._parent:
			ctrlConsIns = self._parent.parentInverseMatrix.outputs(type=CONSTRAINT_TYPES)
			for consNode in [n for n in ctrlConsIns if not n.isReferenced()]:
				# only check for constraint which has outputs to the control, skipping those false ones
				# if self._parent in consNode.listHistory(f=True, allFuture=True):
				self.constraints[consNode] = {'parent': self.parentLongName}
				# else:
				# 	try:
				# 		om.MGlobal.displayWarning('Deleting unused constarint on: %s %s' %(self.parentShortName, consNode.nodeName()))
				# 		pm.delete(consNode)
				# 	except RuntimeError, e:
				# 		print e

		# output constraints
		ctrlConsOuts = self._ctrl.parentMatrix.outputs(type=CONSTRAINT_TYPES, c=True, p=True)
		if self._parent:
			ctrlConsOuts += self._parent.parentMatrix.outputs(type=CONSTRAINT_TYPES, c=True, p=True)
		for ctrlAttr, consAttr in ctrlConsOuts:
			consNode = consAttr.node()

			if consNode.isReferenced():
				continue

			# for cout in ('ct', 'cr', 'cs'):
			# 	if consNode.hasAttr(cout) and consNode.attr(cout).numConnectedChildren():
			# 		break
			# else:
			# 	try:
			# 		om.MGlobal.displayWarning('Deleting unused constarint from: %s %s' %(ctrlAttr.node().nodeName(), consNode.nodeName()))
			# 		pm.delete(consNode)
			# 	except RuntimeError, e:
			# 		print e
			# 	continue

			consInfo = {}
			consType = pm.nodeType(consNode)
			targetAttr = consAttr.getParent()
			targetIndx = targetAttr.index()
			consInfo['indx'] = targetIndx

			# need to lock the constarint weight attr so it won't get deleted
			consNode.attr('w%s' %targetIndx).lock()

			if consType == 'parentConstraint':
				ofstTr = targetAttr.targetOffsetTranslate.get()
				ofstRo = targetAttr.targetOffsetRotate.get()

				consInfo['tr'] = ofstTr
				consInfo['ro'] = ofstRo

			consNodeParent = consNode.getParent()
			if consNodeParent:
				consInfo['parent'] = getRefFullPath(consNodeParent)

			self.constraints[consNode] = consInfo

		#----- input connections
		allInputs = self._ctrl.inputs(c=True, p=True)
		for des, src in allInputs:
			srcNode = src.node()
			desNode = des.node()
			if srcNode.isReferenced() or srcNode==desNode:
				continue

			desStr = '%s.%s' %(self.ctrlLongName, des.longName(fullPath=True))
			self.inConnections.append((desStr, src))

		if self._parent:
			allInputs = self._parent.inputs(c=True, p=True, type=CONSTRAINT_TYPES)
			for des, src in allInputs:
				srcNode = src.node()
				desNode = des.node()
				if srcNode.isReferenced() or srcNode==desNode:
					continue

				desStr = '%s.%s' %(self.parentLongName, des.longName(fullPath=True))
				self.inConnections.append((desStr, src))

		# shape inputs
		if self._ctrlShape:
			allShapeInputs = self._ctrlShape.inputs(c=True, p=True)
			for des, src in allShapeInputs:
				srcNode = src.node()
				desNode = des.node()
				if srcNode.isReferenced() or srcNode==desNode:
					continue

				desStr = '%s.%s' %(self.ctrlShapeLongName, des.longName(fullPath=True))
				self.inConnections.append((desStr, src))

		#----- output connections
		allOutputs = self._ctrl.outputs(type=CONSTRAINT_TYPES, c=True, p=True)
		for src, des in allOutputs:
			srcNode = src.node()
			desNode = des.node()
			if desNode.isReferenced() or srcNode==desNode:
				continue

			srcStr = '%s.%s' %(self.ctrlLongName, src.longName(fullPath=True))
			self.outConnections.append((srcStr, des))

		if self._parent:
			allOutputs = self._parent.outputs(type=CONSTRAINT_TYPES, c=True, p=True)
			for src, des in allOutputs:
				srcNode = src.node()
				desNode = des.node()
				if desNode.isReferenced() or srcNode==desNode:
					continue

				srcStr = '%s.%s' %(self.parentLongName, src.longName(fullPath=True))
				self.outConnections.append((srcStr, des))


def getRefFullPath(obj):
		allParents = obj.getAllParents()[::-1]
		fullPaths = []
		for parent in allParents:
			if not parent.isReferenced():
				continue
			else:
				fullPaths.append(parent.nodeName())
		fullPaths.append(obj.nodeName())
		return '|'.join(fullPaths)

def cleanAnimReference(refPaths=[]):
	# initialize Pymel FileReference object from path or selection
	selection_mode = False
	if not refPaths:
		refs = pipeTools.getFileRefFromObjects(pm.selected())
		if not refs:
			om.MGlobal.displayError('Select reference object(s) and try again.')
			return

		selection_mode = True
		# confrim dialog
		refNodes = [r.refNode.nodeName() for r in refs]
		refMsg = 'Selected reference(s) are:'
		refMsg += '\n - %s' %'\n - '.join(refNodes)
		refMsg += '\n\nStart cleanup?\n - The action is NOT undoable.\n - This will remove unwanted changes made\n    to the reference.'
		
		result = pm.confirmDialog(title='Anim Reference Cleanup', message=refMsg, 
								button=('OK', 'Cancle'))
		if result == 'Cancle':
			return
	else:
		refs = set()
		for path in refPaths:
			try:
				refObj = pm.FileReference(path)
				refs.add(refObj)
			except RuntimeError:
				om.MGlobal.displayWarning('Cannot initialize path: %s' %path)

		if not refs:
			return
		refs = list(refs)

	# filtered_ctrls = list(ctrls)
	for ref in refs:
		refPath = ref.withCopyNumber()
		print '---------- Cleaning: %s' %refPath

		# ----------
		# get all controllers, value set on attributes and constrainted attributes
		print '---------- Getting controller objects...'
		ctrlObjs = []
		refNodes = ref.nodes()

		ctrls = [n for n in refNodes if isinstance(n, pm.nt.DagNode)]
		for c in ctrls:
			nodeName = c.nodeName()
			if nodeName.endswith('_ctrl') or nodeName.endswith('_Ctrl'):
				ctrlObj = AnimatedController(c)
				ctrlObj.getInfo()
				ctrlObjs.append(ctrlObj)

			elif nodeName.split(':')[-1] in EXCEPTIONS:
				pipelineObj = AnimatedController(c)
				pipelineObj.getPipelineStringInfo()
				ctrlObjs.append(pipelineObj)
					
		print '- %s ctrl(s) found' %len(ctrlObjs)
		# return ctrlObjs
		# ----------
		# unload the ref
		ref.unload()
		# ----------
		# get Rig_Grp and constraint parnet command
		print '---------- Getting parent command...'
		parentRefEdits = ref.getReferenceEdits(editCommand='parent')
		parentCmd = ''

		for edit in parentRefEdits:
			splits = edit.split(' ')
			if splits[-2].endswith('%s"' %TOP_GRP):
				parentCmd += '%s;\n' %edit
				continue


		if parentCmd:
			print '- parent commands are: %s' %parentCmd
		else:
			om.MGlobal.displayWarning('No parent command found')

		# ----------
		# clean ref
		print '---------- Removing refEdits...'

		# only keep addAttr edits
		ref.clean(editCommand='parent')
		ref.clean(editCommand='deleteAttr')
		ref.clean(editCommand='disconnectAttr')
		ref.clean(editCommand='connectAttr')
		ref.clean(editCommand='setAttr')

		# ref.removeReferenceEdits(editCommand='parent', successfulEdits=True, failedEdits=True)
		# ref.removeReferenceEdits(editCommand='deleteAttr', successfulEdits=True, failedEdits=True)
		# ref.removeReferenceEdits(editCommand='disconnectAttr', successfulEdits=True, failedEdits=True)
		# ref.removeReferenceEdits(editCommand='connectAttr', successfulEdits=True, failedEdits=True)
		# ref.removeReferenceEdits(editCommand='setAttr', successfulEdits=True, failedEdits=True)

		# ----------
		# reload ref
		print '---------- Reloading reference...' 
		try:
			ref.load(pmt=False)
		except:
			pass

		# ----------
		# execute parent commmand
		if parentCmd:
			print '---------- Executing parent command...'
			try:
				mel.eval(parentCmd)
			except RuntimeError, e:
				print e

		# ----------
		# set attrs
		print '---------- Reconnecting controllers...'
		for ctrlObj in ctrlObjs:
			print '----- %s' %ctrlObj.ctrlShortName

			# setAttrs
			numAttr = len(ctrlObj.ctrlAttrs)
			if numAttr:
				print '--- %s attr(s) on %s' %(numAttr, ctrlObj.ctrlShortName)

			for attr, value in ctrlObj.ctrlAttrs.iteritems():
				attrObj = pm.PyNode(attr)
				# print attr, value
				attrObj.set(value)

			if ctrlObj.ctrlShapeLongName:
				numAttr = len(ctrlObj.ctrlShapeAttrs)
				if numAttr:
					print '--- %s attr(s) on %s' %(numAttr, ctrlObj.ctrlShapeShortName)

				for attr, value in ctrlObj.ctrlShapeAttrs.iteritems():
					attrObj = pm.PyNode(attr)
					attrObj.set(value)

			# connections
			if ctrlObj.inConnections:
				print '--- %s input connections on: %s' %(len(ctrlObj.inConnections), ctrlObj.ctrlShortName)
				for desStr, src in ctrlObj.inConnections:
					des = pm.PyNode(desStr)
					try:
						pm.connectAttr(src, des, f=True)
						print '- connected %s ---> %s' %(src.name(), des.name())
					except:
						print 'ERROR: failed to connect %s ---> %s' %(src.name(), des.name())

			if ctrlObj.outConnections:
				print '--- %s input connections on: %s' %(len(ctrlObj.outConnections), ctrlObj.ctrlShortName)
				for srcStr, des in ctrlObj.outConnections:
					src = pm.PyNode(srcStr)
					try:
						pm.connectAttr(src, des, f=True)
						print '- connected %s ---> %s' %(src.name(), des.name())
					except:
						print 'ERROR: failed to connect %s ---> %s' %(src.name(), des.name())


			# constrints
			for node, consInfo in ctrlObj.constraints.iteritems():
				nodeName = node.nodeName()
				if 'parent' in consInfo:
					parent = pm.PyNode(consInfo['parent'])
					try:
						pm.parent(node, parent)
						print '- constraint parented: %s ---> %s' %(nodeName, parent.nodeName())
					except:
						print 'ERROR: failed to connect %s ---> %s' %(nodeName, parent.nodeName())


				# it's a parentConstraint that need its offset set
				if 'indx' in consInfo:
					indx = 0
					ofstTr = [0, 0, 0]
					ofstRo = [0, 0, 0]
					if 'indx' in consInfo:
						indx = consInfo['indx']
					if 'tr' in consInfo:
						ofstTr = consInfo['tr']
					if 'ro' in consInfo:
						ofstRo = consInfo['ro']
					targetAttrName = node.target[indx].longName(fullPath=True)

					node.target[indx].targetOffsetTranslate.set(ofstTr)
					print '- targetOffsetTranslate: %s.%s = %s' %(nodeName, targetAttrName, ofstTr)
					node.target[indx].targetOffsetRotate.set(ofstRo)
					print '- targetOffsetRotate: %s.%s = %s' %(nodeName, targetAttrName, ofstRo)


		print '---------- Finish cleaning: %s' %refPath

	if selection_mode:
		result = pm.confirmDialog(title='Anim Reference Cleanup', message='Cleanup complete!', 
								button=('OK'))
					
def restoreShader(objs=[]):
	'''
	In case shapeDeformed is created on referenced geo and shader on the shapeDeformed is differ from the shapeOrig
	from the source reference, this will reapply shader on shapeOrig to shapeDeform.
	'''
	if not objs:
		objs = pm.selected(type='transform')
	rets = []
	for tr in [i for i in objs if isinstance(i, pm.nt.Transform)]:
		print '\n---------- %s' %tr
	
		meshHiss = tr.listHistory(type='mesh')
		if len(meshHiss) < 2:
			om.MGlobal.displayWarning('Skipping, less then 2 meshes in history.')
			continue

		print '----- Shapes found...'
		print '- %s' %'\n'.join([m.nodeName() for m in meshHiss])

		if meshHiss[0].isReferenced():
			om.MGlobal.displayWarning('Skipping, no shapeDeformed.')
			continue
		
		deformedShp = meshHiss[0]
		refShp = meshHiss[1]

		# get assinged on refShp
		res = misc.getShaderAssigned(shp=refShp)  # (sg, shader): shape  or (sg, shader): ['f[i]', f...]
		if res:
			print '----- Referenced mesh is assigned to shaders...'
			print '-%s' %res
		else:
			om.MGlobal.displayWarning('Skipping, refShape has no SG assinged.' )
			continue

		defInstIndices = deformedShp.instObjGroups.getArrayIndices()
		print '----- Disconnecting outputs from shapeDeformed...'
		for i in defInstIndices:
			iAttr = deformedShp.instObjGroups[i]
			print '-%s' %iAttr
			iAttr.disconnect()
			for o in deformedShp.instObjGroups[i].objectGroups.getArrayIndices():
				oAttr = deformedShp.instObjGroups[i].objectGroups[o]
				print '-%s' %oAttr
				oAttr.disconnect()

		print '----- Reassigning shaders to shapeDeformed...'
		deformedShpLn = deformedShp.longName()

		for sgs, assingedObj in res.iteritems():
			sg = sgs[0]
			if isinstance(assingedObj, pm.nt.Mesh):
				pm.sets(sg, e=True, fe=deformedShp)
				print '- %s ---> %s' %(deformedShp, sg)
			elif isinstance(assingedObj, list):
				for a in assingedObj:
					fStr = '%s.%s' %(deformedShpLn, a)
					fNode = pm.PyNode(fStr)
					pm.sets(sg, e=True, fe=fNode)
					print '- %s ---> %s' %(fStr, sg)
					rets.append(fNode)

	return rets