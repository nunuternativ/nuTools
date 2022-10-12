import maya.cmds as mc
import maya.OpenMaya as om
import maya.OpenMayaAnim as oma 
import pymel.core as pm

from nuTools import misc, controller
reload(misc)
reload(controller)
import nuTools.rigTools.baseRig as baseRig
reload(baseRig)
from nuTools.util import selection
reload(selection)

pluginName = 'MayaMuscle.mll'
if not pm.pluginInfo(pluginName, q=True, l=True):
	pm.loadPlugin(pluginName, qt=True)

class BpmRig(baseRig.BaseRig):
	def __init__(self, 
				jnts=[],
				parent=None,
				rootJnt=None,
				inputGeometry=None,
				skinCluster=None,
				**kwargs):
		super(BpmRig, self).__init__(**kwargs)

		self.surfAttachs = []
		self.skcRootIndex = 0
		self.skcIndices = []
		self.skcConnections = {}

		# temp joints
		self.tmpJnts = self.jntsArgs(jnts)
		self.parent = self.jntsArgs(parent)

		if rootJnt:
			self.rootJnt = pm.PyNode(rootJnt)
			rootJntParent = self.rootJnt.getParent()
			if not rootJntParent:
				rootJntParent = misc.zgrp(self.rootJnt, element='Zro', suffix='grp')[0]
			self.rootJntParent = rootJntParent

		if inputGeometry:
			self.inputGeometry = pm.PyNode(inputGeometry)
			self.inputGeometryShape = self.inputGeometry.getShape(ni=True)
			
		if skinCluster:
			self.skinCluster = pm.PyNode(skinCluster)

	def getSurfAttachNodes(self):
		self.surfAttachs = [n.getShape() for n in self.inputGeometryShape.outMesh.outputs(type='cMuscleSurfAttach')]

	def rig(self):
		# anim group
		self.rigCtrlGrp = pm.group(em=True, n='%sBpmRig%s_grp' %(self.elem, self.side))
		pm.parent(self.rigCtrlGrp, self.animGrp)
		self.rigCtrlGrp.inheritsTransform.set(False)

		# still grp
		self.rigStillGrp = pm.group(em=True, n='%sBpmStill%s_grp' %(self.elem, self.side))
		pm.parent(self.rigStillGrp, self.stillGrp)

		# find and connect root joint index
		rootOuts = [a for a in self.rootJnt.worldMatrix.outputs(type='skinCluster', p=True) if a.node()==self.skinCluster]
		self.skcRootIndex = rootOuts[0].index()
		skcRootBpmAttr = self.skinCluster.bindPreMatrix[self.skcRootIndex]
		if not skcRootBpmAttr.isConnected():
			pm.connectAttr(self.rootJntParent.worldInverseMatrix[0], skcRootBpmAttr)

		# loop over each temp joint to create cMuscleSurfAttach
		for i, jnt in enumerate(self.tmpJnts):
			iname = (self.elem, (i+1), self.side)
			position = jnt.getTranslation('world')

			# create surface attach
			sa = pm.createNode('cMuscleSurfAttach', n='%s%s%s_saShape' %iname)
			sa.visibility.set(False)	
			saTr = sa.getParent()
			saTr.rename('%s%s%s_sa' %iname)	
			self.surfAttachs.append(sa)

			# connect sa transform rotate order to the shape
			pm.connectAttr(saTr.rotateOrder, sa.inRotOrder)

			# connect the inputGeom
			pm.connectAttr(self.inputGeometryShape.outMesh, sa.surfIn)

			# find parallel edges
			closestVert, closestFace = misc.getClosestComponentFromPos(mesh=self.inputGeometry, 
										pos=position)
			e1, e2 = misc.getParallelEdgesFromClosestPointOnMesh(closestVert, closestFace)

			# set edge indices
			sa.edgeIdx1.set(e1.indices()[0])
			sa.edgeIdx2.set(e2.indices()[0])

			# set uLoc, vLoc so the node sits on top of the closest vert
			sa.uLoc.set(0)
			e1ConVerts = e1.connectedVertices()
			vValue = 0 if e1ConVerts[0] == closestVert else 1
			sa.vLoc.set(vValue)

			pm.connectAttr(sa.attr('outTranslate'), saTr.attr('translate'))
			pm.connectAttr(sa.attr('outRotate'), saTr.attr('rotate'))

			# get bpm index 

			jntSkcOuts = [a for a in jnt.worldMatrix.outputs(type='skinCluster', p=True) if a.node()==self.skinCluster]
			print jnt, jntSkcOuts
			index = jntSkcOuts[0].index()

			self.skcIndices.append(index)

	def lockAndHideJnts(self):
		for jnt in self.tmpJnts:
			jnt.drawStyle.set('None')
			misc.lockAttr(jnt, t=True, r=True, s=True, v=True)
			misc.hideAttr(jnt, t=True, r=True, s=True, v=True)

	def getSkinClusterBpmConnections(self):
		self.skcConnections = {}
		for bi in xrange(self.skinCluster.bindPreMatrix.numElements()):
			bpmAttr = self.skinCluster.bindPreMatrix[bi]
			inputs = bpmAttr.inputs(c=True, p=True)
			for d, s in inputs:
				self.skcConnections[s] = bi

	def changeSkinCluster(self, newSkinCluster):
		newSkc = pm.PyNode(newSkinCluster)
		self.getSkinClusterBpmConnections()
		
		for s, di in self.skcConnections.iteritems():
			self.skinCluster.bindPreMatrix[di].disconnect()
			pm.connectAttr(s, newSkc.bindPreMatrix[di])

		self.skinCluster = newSkc

	def changeInputGeom(self, newInputGeom, orig=False):
		newGeom = pm.PyNode(newInputGeom)
		self.getSurfAttachNodes()
		
		if not orig:
			newGeomShp = newGeom.getShape(ni=True)
		else:
			newGeomShp = misc.getOrigShape(newGeom)[0]
		for sa in self.surfAttachs:
			sa.surfIn.disconnect()
			pm.connectAttr(newGeomShp.outMesh, sa.surfIn, f=True)

	def addSkinCluster(self, newSkinCluster):
		newSkc = pm.PyNode(newSkinCluster)
		self.getSkinClusterBpmConnections()
		newSkcJnts = newSkc.matrix.inputs(type='joint')

		for jnt, indx in self.skcConnections.iteritems():
			if jnt in newSkcJnts:
				ni = newSkcJnts.index(jnt)
				pm.connectAttr(jnt, newSkc.bindPreMatrix[ni])

class BpmIkRig(BpmRig):
	def __init__(self, 
				jnts=[],
				parent=None,
				rootJnt=None,
				inputGeometry=None,
				skinCluster=None,
				ctrlShp='cube',
				ctrlColor='lightBlue',
				**kwargs):
		super(BpmIkRig, self).__init__(jnts=jnts, 
				parent=parent,
				rootJnt=rootJnt,
				inputGeometry=inputGeometry,
				skinCluster=skinCluster,
				**kwargs)

		self.ctrlShp = ctrlShp
		self.ctrlColor = ctrlColor
		self.ctrls = []

	def rig(self):
		# call the base class rig method
		super(BpmIkRig, self).rig()

		# loop over each joint
		for i, jnt in enumerate(self.tmpJnts):
			iName = (self.elem, (i+1), self.side)

			sa = self.surfAttachs[i]
			saTr = sa.getParent()
			pm.parent(saTr, self.rigCtrlGrp)

			if self.parent:
				misc.snapTransform('scale', self.parent, saTr, True, False)

			# bpm group
			ctrlBpmGrp = pm.group(em=True, n='%s%sBpm%s_grp' %iName)
			pm.parent(ctrlBpmGrp, saTr)
			misc.snapTransform('parent', jnt, ctrlBpmGrp, False, True)

			# create controller
			ctrl = controller.JointController(name='%s%s%s_Ctrl' %iName,
												st=self.ctrlShp, 
												color=self.ctrlColor, 
												scale=self.size,
												draw=False)
			ctrl.lockAttr(v=True)
			ctrl.hideAttr(v=True)
			ctrl.rotateOrder.set(self.rotateOrder)
			ctrlZroGrp = misc.zgrp(ctrl, element='Zro', suffix='grp')[0]
			misc.snapTransform('parent', jnt, ctrlZroGrp, False, True)
			self.ctrls.append(ctrl)

			pm.parent(jnt, ctrl)
			pm.parent(ctrlZroGrp, ctrlBpmGrp)

			# disconnect jnt's inverse scale
			jnt.inverseScale.disconnect()

			# connect bpm
			pm.connectAttr(ctrlBpmGrp.worldInverseMatrix[0], self.skinCluster.bindPreMatrix[self.skcIndices[i]])

		# lock & hide joints
		self.lockAndHideJnts()

class BpmFkRig(BpmRig):
	def __init__(self, 
				jnts=[],
				parent=None,
				rootJnt=None,
				inputGeometry=None,
				skinCluster=None,
				ctrlShp='crossCircle',
				ctrlColor='red',
				**kwargs):
		super(BpmFkRig, self).__init__(jnts=jnts, 
				parent=parent,
				rootJnt=rootJnt,
				inputGeometry=inputGeometry,
				skinCluster=skinCluster,
				**kwargs)

		self.ctrlShp = ctrlShp
		self.ctrlColor = ctrlColor

		self.locators = []
		self.ctrls = []

	def rig(self):
		# call the base class rig method
		super(BpmFkRig, self).rig()

		# loop over each joint
		for i, jnt in enumerate(self.tmpJnts):
			iName = (self.elem, (i+1), self.side)

			sa = self.surfAttachs[i]
			saTr = sa.getParent()
			pm.parent(saTr, self.rigStillGrp)

			# locator
			loc = pm.spaceLocator(n='%s%sBpm%s_loc' %iName)
			loc.localScale.set([self.size*0.1, self.size*0.1, self.size*0.2])
			misc.snapTransform('parent', jnt, loc, False, True)
			misc.snapTransform('parent', saTr, loc, True, False)
			if self.parent:
				misc.snapTransform('scale', self.parent, loc, True, False)
			self.locators.append(loc)

			# bpm group
			ctrlBpmGrp = pm.group(em=True, n='%s%sBpm%s_grp' %iName)
			pm.parent(ctrlBpmGrp, saTr)
			misc.snapTransform('parent', jnt, ctrlBpmGrp, False, True)

			# create controller
			ctrl = controller.JointController(name='%s%s%s_Ctrl' %iName,
												st=self.ctrlShp, 
												color=self.ctrlColor, 
												scale=self.size,
												draw=False)
			ctrl.lockAttr(v=True)
			ctrl.hideAttr(v=True)
			ctrl.rotateOrder.set(self.rotateOrder)
			ctrlZroGrp = misc.zgrp(ctrl, element='Zro', suffix='grp')[0]
			misc.snapTransform('parent', loc, ctrlZroGrp, False, True)
			self.ctrls.append(ctrl)

			pm.parent(jnt, ctrl)
			pm.parent(ctrlZroGrp, ctrlBpmGrp)

			# parent
			if i == 0:
				pm.parent(loc, self.rigStillGrp)
				pm.parent(ctrlBpmGrp, self.rigCtrlGrp)
			else:
				pm.parent(loc, self.locators[i-1])
				pm.parent(ctrlBpmGrp, self.ctrls[i-1])

			# connect bpm
			misc.directConnectTransform(objs=[loc, ctrlBpmGrp], t=True, r=True, s=True, force=True)
			pm.connectAttr(loc.worldInverseMatrix[0], self.skinCluster.bindPreMatrix[self.skcIndices[i]])

		# lock & hide joints
		self.lockAndHideJnts()

# ---------------------------------------------------------------
# ---------------------------------------------------------------

STICKYATTR = 'stickyDeformer'
DEFAULT_STICKYCLUSTER_NAME = 'stickyCluster'
global bpmClusterRig_prev_name
bpmClusterRig_prev_name = 'stickyCluster'
class BpmClusterRig(object):
	'''
	from nuTools.rigTools import bpmRig
	reload(bpmRig)

	stickyCluster = bpmRig.BpmClusterRig()
	stickyCluster.rig()
	'''
	def __init__(self, 
				components=[],
				name='',
				ctrlShp='diamond3d',
				ctrlColor='green',
				**kwargs):

		# get the components if there's none provided
		if not components:
			components = self.getInputGeometry()
		elif isinstance(components, (str, unicode)):
			components = pm.PyNode(components)
		elif isinstance(components, (list, tuple)):
			components = []
			for i in components:
				components.append(pm.PyNode(i))

		canceled = False
		try:
			if not name:
				global bpmClusterRig_prev_name
				if not bpmClusterRig_prev_name:
					prevName = DEFAULT_STICKYCLUSTER_NAME
				else:
					prevName = bpmClusterRig_prev_name
				result = pm.promptDialog(title='Sticky Cluster', message='Name:', text=prevName, 
					button=('OK', 'Cancel'))
				if result in ['Cancel', 'dismiss']:
					canceled = True
				else:
					name = str(pm.promptDialog(q=True, text=True))
				bpmClusterRig_prev_name = name
		except:
			name = DEFAULT_STICKYCLUSTER_NAME

		if canceled:
			raise Exception, 'Canceled.'

		self.components = components
		self.deformer = None
		self.name = name
		self.ctrlShp = ctrlShp
		self.ctrlColor = ctrlColor
		self.isDeformed = False

		self.__version = 1.0

	def getInputGeometry(self):
		node = None
		# get component selection
		selComps = [c for c in mc.ls(sl=True, l=True, fl=True) if '.vtx[' in c or '.f[' in c or '.e[' in c]
		# get mesh selection
		selMeshes = [s.getShape(ni=True) for s in misc.getSel(num='inf') if misc.checkIfPly(s)]
		comps = []
		# if user select mesh, convert to all vertices
		if not selComps and selMeshes:
			mesh = selMeshes[0]
			meshName = mesh.longName()
			comps = ['%s.vtx[%s]' %(meshName, i) for i in xrange(mesh.numVertices())]
		elif not selComps and not selMeshes:
			return
		elif selComps:
			# convert any selection to list of vertices
			comps = mc.polyListComponentConversion(selComps, tv=True)
			comps = mc.ls(comps, l=True, fl=True)
		# check if all vertices are from the same mesh
		for c in comps:
			current_node = ''.join(c.split('.')[:-1])
			if node and current_node != node:
				pm.error('Components must come from the same polygon shape.')
			else:
				node = current_node
		return comps

	def getIncrementalName(self):
		exit = False
		i = 1
		while not exit:
			incName = '%s%s' %(self.name, i)
			if pm.objExists(incName):
				i += 1
			else:
				self.name = incName
				exit = True

	def findDeformer(self):
		dgHis = self.shape.listHistory(pruneDagObjects=True)
		default_sc = None
		for node in dgHis:
			if node.hasAttr(STICKYATTR):
				default_sc = node
				continue
			elif node.hasAttr('outputGeometry[0]') and 'geometryFilter' in pm.nodeType(node, inherited=True) and pm.nodeType(node) != 'tweak':
				self.isDeformed = True
				return node

		if not default_sc:
			# else create 1 defualt cluster
			default_sc , clusterHndl = pm.cluster(self.shape.vtx[0], n='%s_scDef' %self.shape.nodeName().split(':')[-1])
			misc.addStrAttr(default_sc, STICKYATTR, txt=self.__version, lock=True)
			clusterHndl.visibility.set(False)
			misc.lockAttr(obj=clusterHndl, lock=True, t=True, r=True, s=True, v=True)

			# needs to get the new shape and components in case "shapeDeformed" was created
			tr = default_sc.outputGeometry[0].outputs()[0]
			self.shape = tr.getShape(ni=True)
			shapeName = self.shape.longName()
			new_components = []
			for c in self.components:
				# index = c.index()
				# new_components.append(self.shape.vtx[index])\
				splits = c.split('.')
				new_components.append('%s.%s' %(shapeName, splits[-1]))
			self.components = new_components

		return default_sc

	def getWeights(self):
		# if soft selection is on get weights for the deformer from it
		numVtx = self.shape.numVertices()
		weights = om.MFloatArray(numVtx, 0.0)  # initialize the array size to num vertices and the value 0.0
		if pm.softSelect(q=True, sse=True):
			result = selection.getSoftSelection()  # {fullPathName: {i1:w1, i2:w2, ...}}
			softValues = result[self.shape.longName()] 
			for vi, value in softValues.iteritems():
				weights[vi] = value
		else:
			for vtx in self.components:
				index = int(''.join(vtx.split('.vtx[')[-1][:-1]))
				weights[index] = 1.0

		return weights

	def setWeights(self, weights):
		mSel = om.MSelectionList()
		mSel.add(self.clusterNode.nodeName())
		oCluster = om.MObject()
		mSel.getDependNode(0, oCluster)
		fnDeformer = oma.MFnWeightGeometryFilter(oCluster)

		# Get components effected by deformer
		fnSet = om.MFnSet(fnDeformer.deformerSet())
		members = om.MSelectionList()
		fnSet.getMembers(members, False)
		dagPath = om.MDagPath()
		components = om.MObject()
		members.getDagPath(0, dagPath, components)

		# set the weights
		fnDeformer.setWeight(dagPath, components, weights)

	def rig(self):
		if not self.components:
			pm.error('Please select polygon components(vertices, edges or faces).')

		self.getIncrementalName()
		# self.shape = self.components[0].node()
		self.shape = pm.PyNode(self.components[0]).node()

		# get the weights before creating the cluster
		weights = self.getWeights()

		self.deformer = self.findDeformer()

		self.clusterNode, self.clusterHndl = pm.cluster(self.shape, n=self.name)

		# move vertices to selected component center
		vtxCenter = misc.getCenterOfVertices(self.components)
		pm.xform(self.clusterHndl, piv=vtxCenter)
		self.clusterHndl.getShape().origin.set(vtxCenter)

		# take care of the cluster weights
		self.setWeights(weights)

		misc.addStrAttr(self.clusterNode, STICKYATTR, txt=self.__version, lock=True)
		self.clusterNode.relative.set(not self.isDeformed)

		self.clusterHndl.overrideEnabled.set(True)
		colorCode = misc.getColorCode(self.ctrlColor)
		self.clusterHndl.overrideColor.set(colorCode)

		roPiv, scaPiv = self.clusterHndl.getPivots()

		# group the cluster twice
		self.offsetGrp = misc.zgrp(self.clusterHndl, element='Offset', suffix='grp', snap=False)[0]
		self.zgrp = misc.zgrp(self.offsetGrp, element='Zro', suffix='grp', snap=False)[0]

		# create surface attach
		self.sa = pm.createNode('cMuscleSurfAttach', n='%s_saShape' %self.name)
		self.sa.visibility.set(False)	
		self.saTr = self.sa.getParent()
		self.saTr.rename('%s_sa' %self.name)	

		# connect sa transform rotate order to the shape
		pm.connectAttr(self.saTr.rotateOrder, self.sa.inRotOrder)

		# connect the inputGeom
		pm.connectAttr(self.deformer.outputGeometry[0], self.sa.surfIn)

		# find parallel edges
		closestVert, closestFace = misc.getClosestComponentFromPos(mesh=self.shape, pos=roPiv)
		e1, e2 = misc.getParallelEdgesFromClosestPointOnMesh(closestVert, closestFace)

		# set edge indices
		self.sa.edgeIdx1.set(e1.indices()[0])
		self.sa.edgeIdx2.set(e2.indices()[0])

		# set uLoc, vLoc so the node sits on top of the closest vert
		self.sa.uLoc.set(0)
		e1ConVerts = e1.connectedVertices()
		vValue = 0 if e1ConVerts[0] == closestVert else 1
		self.sa.vLoc.set(vValue)

		pm.connectAttr(self.sa.attr('outTranslate'), self.saTr.attr('translate'))
		pm.connectAttr(self.sa.attr('outRotate'), self.saTr.attr('rotate'))

		pm.parent(self.zgrp, self.saTr)
		pm.connectAttr(self.offsetGrp.parentInverseMatrix[0], self.clusterNode.bindPreMatrix, f=True)

		# create curve shape
		ctrlTr = controller.Controller(st=self.ctrlShp, color=self.ctrlColor, scale=0.2)
		ctrlShp = ctrlTr.getShape()
		# print ctrlShp
		ctrlShp.rename('%sCtrlShape' %(self.name))
		pm.select([ctrlShp, self.clusterHndl])
		# pm.parent([ctrlShp, self.clusterHndl], r=True, s=True)
		pm.parent(r=True, s=True)
		pm.delete(ctrlTr)
		clsPos = pm.xform(self.clusterHndl, q=True, ws=True, rp=True)
		pm.move(ctrlShp.cv, clsPos, ws=True, r=True)

		# add envelope
		# add neccessary attribute to handle
		sepAttr = misc.addNumAttr(self.clusterHndl, '__Cluster__', 'double', dv=0.0)
		sepAttr.lock()
		envAttr = misc.addNumAttr(self.clusterHndl, 'envelope', 'float', min=0.0, max=1.0, dv=1.0)
		pm.connectAttr(envAttr, self.clusterNode.envelope)

		# lock unused attrs
		misc.lockAttr(obj=self.offsetGrp, lock=True, t=True, r=True, s=True, v=True)
		misc.lockAttr(obj=self.zgrp, lock=True, t=True, r=True, s=True, v=True)
		misc.lockAttr(obj=self.saTr, lock=True, t=True, r=True, s=True, v=True)
		misc.lockAttr(obj=self.clusterHndl, lock=True, t=False, r=False, s=False, v=True)
		misc.hideAttr(obj=self.clusterHndl, hide=True, t=False, r=False, s=False, v=True)

		self.sa.vLoc.lock()
		self.sa.uLoc.lock()
		self.sa.fixPolyFlip.lock()
		self.sa.size.lock()

		# select the cluster
		pm.select(self.clusterHndl, r=True)

# ---------------------------------------------------------------
# ---------------------------------------------------------------

DEFAULT_STICKYSOFTMOD_NAME = 'stickySoftMod'
global bpmSoftModRig_prev_name
bpmSoftModRig_prev_name = 'stickySoftMod'
class BpmSoftModRig(object):
	'''
	from nuTools.rigTools import bpmRig
	reload(bpmRig)

	stickyCluster = bpmRig.BpmClusterRig()
	stickyCluster.rig()
	'''
	def __init__(self, 
				mesh=None,
				center=[],
				name='',
				ctrlColor='yellow',
				ctrlShp='crossSphere',
				**kwargs):

		self.selComps = [c for c in mc.ls(sl=True, l=True, fl=True) if '.vtx[' in c or '.f[' in c or '.e[' in c]
		if not center:
			self.center = misc.getCenterOfVertices(mc.ls(sl=True, l=True, fl=True))
		else:
			self.center = center

		# get the components if there's none provided
		if not mesh:
			mesh = self.getInputGeometry()
		elif isinstance(mesh, (str, unicode)):
			mesh = pm.PyNode(mesh)
		if not mesh:
			pm.error('Please select polygon components(vertices, edges or faces).')

		# pop up name UI
		canceled = False
		try:
			if not name:
				global bpmSoftModRig_prev_name
				if not bpmSoftModRig_prev_name:
					prevName = DEFAULT_STICKYSOFTMOD_NAME
				else:
					prevName = bpmSoftModRig_prev_name
				result = pm.promptDialog(title='Sticky SoftMod', message='Name:', text=prevName, 
					button=('OK', 'Cancel'))
				print '...'+result
				if result in ['Cancel', 'dismiss']:
					canceled = True
				else:
					name = str(pm.promptDialog(q=True, text=True))
				bpmSoftModRig_prev_name = name
		except:
			name = DEFAULT_STICKYSOFTMOD_NAME

		if canceled:
			raise Exception, 'Canceled.'
		
		self.mesh = mesh
		self.deformer = None
		self.name = name
		self.ctrlShp = ctrlShp
		self.ctrlColor = ctrlColor
		self.isDeformed = False

		self.__version = 1.0

	def getInputGeometry(self):
		node = None
		# get component selection
		# selComps = [c for c in mc.ls(sl=True, l=True, fl=True) if '.vtx[' in c or '.f[' in c or '.e[' in c]
		# get mesh selection
		selMeshes = [s.getShape(ni=True) for s in misc.getSel(num='inf') if misc.checkIfPly(s)]
		comps = []
		# if user select mesh, convert to all vertices
		if not self.selComps and selMeshes:
			mesh = selMeshes[0]
			meshName = mesh.longName()
			comps = ['%s.vtx[%s]' %(meshName, i) for i in xrange(mesh.numVertices())]
		elif not self.selComps and not selMeshes:
			return
		elif self.selComps:
			# convert any selection to list of vertices
			comps = mc.polyListComponentConversion(self.selComps, tv=True)
			comps = mc.ls(comps, l=True, fl=True)

		# check if all vertices are from the same mesh
		for c in comps:
			current_node = ''.join(c.split('.')[:-1])
			if node and current_node != node:
				pm.error('Components must come from the same polygon shape.')
			else:
				node = current_node

		return pm.PyNode(node)

	def getIncrementalName(self):
		exit = False
		i = 1
		while not exit:
			incName = '%s%s' %(self.name, i)
			if pm.objExists(incName):
				i += 1
			else:
				self.name = incName
				exit = True

	def findDeformer(self):
		dgHis = self.mesh.listHistory(pruneDagObjects=True)
		default_ss = None
		for node in dgHis:
			if node.hasAttr(STICKYATTR):
				default_ss = node
				continue
			elif node.hasAttr('outputGeometry[0]') and 'geometryFilter' in pm.nodeType(node, inherited=True) and pm.nodeType(node) != 'tweak':
				self.isDeformed = True
				return node

		if not default_ss:
			# else create 1 defualt cluster
			default_ss, clusterHndl = pm.cluster(self.mesh.vtx[0], n='%s_smDef' %self.mesh.nodeName().split(':')[-1])
			misc.addStrAttr(default_ss, STICKYATTR, txt=self.__version, lock=True)
			clusterHndl.visibility.set(False)
			misc.lockAttr(obj=clusterHndl, lock=True, t=True, r=True, s=True, v=True)

			# needs to get the new shape and components in case "shapeDeformed" was created
			tr = default_ss.outputGeometry[0].outputs()[0]
			self.mesh = tr.getShape(ni=True)

		return default_ss

	def rig(self):
		if not self.mesh:
			pm.error('Please select polygon components(vertices, edges or faces).')

		self.getIncrementalName()
		self.deformer = self.findDeformer()

		self.softModNode, self.softModHndl = pm.softMod(self.mesh, n=self.name)
		misc.addStrAttr(self.softModNode, STICKYATTR, txt=self.__version, lock=True)
		self.softModNode.relative.set(not self.isDeformed)
		# move softMod to center to self.center
		self.softModShape = self.softModHndl.getShape()
		self.softModShape.origin.set(self.center)

		pm.xform(self.softModHndl, ws=True, piv=self.center)
		
		# set softMod color
		self.softModHndl.overrideEnabled.set(True)
		colorCode = misc.getColorCode(self.ctrlColor)
		self.softModHndl.overrideColor.set(colorCode)
		roPiv, scaPiv = self.softModHndl.getPivots()

		# group the softMod twice
		self.offsetGrp = misc.zgrp(self.softModHndl, element='Offset', suffix='grp', snap=False)[0]
		
		# create surface attach
		self.sa = pm.createNode('cMuscleSurfAttach', n='%s_saShape' %self.name)
		self.sa.visibility.set(False)	
		self.saTr = self.sa.getParent()
		self.saTr.rename('%s_sa' %self.name)	

		# connect sa transform rotate order to the shape
		pm.connectAttr(self.saTr.rotateOrder, self.sa.inRotOrder)

		# connect the inputGeom
		pm.connectAttr(self.deformer.outputGeometry[0], self.sa.surfIn)

		# find parallel edges
		closestVert, closestFace = misc.getClosestComponentFromPos(mesh=self.mesh, pos=roPiv)
		e1, e2 = misc.getParallelEdgesFromClosestPointOnMesh(closestVert, closestFace)

		# set edge indices
		self.sa.edgeIdx1.set(e1.indices()[0])
		self.sa.edgeIdx2.set(e2.indices()[0])

		# set uLoc, vLoc so the node sits on top of the closest vert
		self.sa.uLoc.set(0)
		e1ConVerts = e1.connectedVertices()
		vValue = 0 if e1ConVerts[0] == closestVert else 1
		self.sa.vLoc.set(vValue)

		pm.connectAttr(self.sa.attr('outTranslate'), self.saTr.attr('translate'))
		pm.connectAttr(self.sa.attr('outRotate'), self.saTr.attr('rotate'))
		pm.connectAttr(self.offsetGrp.worldInverseMatrix[0], self.softModNode.bindPreMatrix, f=True)

		if not self.isDeformed:
			self.softModNode.falloffCenter.set(self.center)
			pm.parent(self.offsetGrp, self.saTr)
		else:
			self.locator = pm.spaceLocator(n='%sZro_loc' %self.name)
			self.locatorShp = self.locator.getShape()
			self.locatorShp.visibility.set(False)

			pm.connectAttr(self.locatorShp.worldPosition, self.softModNode.falloffCenter)
			pm.xform(self.locator, ws=True, t=self.center)
			pm.parent(self.offsetGrp, self.locator)
			pm.parent(self.locator, self.saTr)
			misc.lockAttr(obj=self.locator, lock=True, t=True, r=True, s=True, v=True)

		# create curve shape
		ctrlTr = controller.Controller(st=self.ctrlShp, color=self.ctrlColor, scale=0.2)
		ctrlShp = ctrlTr.getShape()
		ctrlShp.rename('%sCtrlShape' %(self.name))
		pm.select([ctrlShp, self.softModHndl])
		pm.parent(r=True, s=True)
		pm.delete(ctrlTr)
		clsPos = pm.xform(self.softModHndl, q=True, ws=True, rp=True)
		pm.move(ctrlShp.cv, clsPos, ws=True, r=True)


		# add neccessary attribute to handle
		sepAttr = misc.addNumAttr(self.softModHndl, '__softMod__', 'double', dv=0.0)
		sepAttr.lock()
		# add envelope
		envAttr = misc.addNumAttr(self.softModHndl, 'envelope', 'float', min=0.0, max=1.0, dv=1.0)
		pm.connectAttr(envAttr, self.softModNode.envelope)

		# get default radius value from soft select
		default_radius = 1.0
		if mc.softSelect(q=True, sse=True):
			
			compRadius = 0.0
			if self.selComps:
				dists = []
				for c in self.selComps:
					pos = mc.xform(c, q=True, ws=True, t=True)
					distance = misc.getDistanceFromPosition(pos, self.center)
					dists.append(distance)
				compRadius = (max(dists) + min(dists)) * 0.5
			default_radius = mc.softSelect(q=True, ssd=True) + compRadius
		misc.addNumAttr(self.softModHndl, 'radius', 'double', dv=default_radius, min=0.0)
		misc.addNumAttr(self.softModHndl, 'mode', 'enum', enum=('Volume', 'Surface'), dv=0, min=0, max=1)
		pm.connectAttr(self.softModHndl.radius, self.softModNode.falloffRadius)
		pm.connectAttr(self.softModHndl.mode, self.softModNode.falloffMode)

		# lock unused attrs
		misc.lockAttr(obj=self.offsetGrp, lock=True, t=True, r=True, s=True, v=True)
		misc.lockAttr(obj=self.saTr, lock=True, t=True, r=True, s=True, v=True)
		misc.lockAttr(obj=self.softModHndl, lock=True, t=False, r=False, s=False, v=True)
		misc.hideAttr(obj=self.softModHndl, hide=True, t=False, r=False, s=False, v=True)

		self.sa.vLoc.lock()
		self.sa.uLoc.lock()
		self.sa.fixPolyFlip.lock()
		self.sa.size.lock()
		self.softModNode.falloffRadius.lock()
		self.softModNode.falloffCenter.lock()
		self.softModNode.falloffInX.lock()
		self.softModNode.falloffInY.lock()
		self.softModNode.falloffInZ.lock()
		self.softModNode.falloffAroundSelection.lock()
		self.softModNode.falloffMasking.lock()

		# select the cluster
		pm.select(self.softModHndl, r=True)