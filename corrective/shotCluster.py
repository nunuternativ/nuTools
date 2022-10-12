import pymel.core as pm
import maya.OpenMaya as om
import maya.mel as mel

class ShotCluster(object):
	def __init__(self, name='', vtxs=[], parents=[]):
		if not vtxs or not parents:
			ret = self.getSelections()
			if not ret:
				return
		else:
			self.vtxs = vtxs
			self.parents = parents

		if not name:
			i = 1
			exit = False
			while not exit:
				if pm.objExists('cluster%sShotCluster_grp' %i):
					i += 1
					continue
				else:
					name = 'cluster%s' %i
					exit = True

		self.name = name
		self.cluster = None
		self.clusterHndl = None
		self.mainGrp = None
		self.clusterGrp = None
		self.consLoc = None

		self.doIt()
		
	def doIt(self):
		pm.select(self.vtxs, r=True)
		clusters = pm.cluster()
		self.cluster = clusters[0]
		self.clusterHndl = clusters[1]

		# set relative
		self.cluster.relative.set(True)

		# grouping
		self.mainGrp = pm.group(em=True, n='%sShotCluster_grp' %self.name)
		self.clusterGrp = pm.group(em=True, n='%sZro_grp' %self.name)
		pm.parent(self.clusterHndl, self.clusterGrp)
		pm.parent(self.clusterGrp, self.mainGrp)

		# rename clusters
		self.cluster.rename('%s_clusterDeformer' %self.name)
		self.clusterHndl.rename('%s_clusterHandl' %self.name)

		# create locator
		self.consLoc = pm.spaceLocator(n='%sCons_loc' %self.name)
		# snap loc
		pm.delete(pm.pointConstraint(self.clusterHndl, self.consLoc))
		# do constraints
		pm.parentConstraint(self.parents, self.consLoc, mo=True)
		# hide, parent locator to the main grp
		self.consLoc.visibility.set(False)
		pm.parent(self.consLoc, self.mainGrp)

		# point constraint the cluster grp to the loc
		pm.pointConstraint(self.consLoc, self.clusterGrp, mo=True)

		pm.select(self.clusterHndl)

	def getSelections(self):
		sels = pm.selected()
		vtxs = [v for v in sels if isinstance(v, pm.MeshVertex)]
		parents = [p for p in sels if isinstance(p, pm.nt.Transform)]

		if not vtxs or not parents:
			om.MGlobal.displayError('Invalid selection. Please select some vertices and one or more transform.')
			return False

		self.vtxs = vtxs
		self.parents = parents
		return True

def floodSelectedClusterWeight():
	sels = pm.selected(type='transform')

	for sel in sels:
		shp = sel.getShape(ni=True)
		if not shp:
			continue
		if shp.type() != 'clusterHandle':
			continue

		clusterDefNode, memberSet = None, None
		try:
			clusterDefNode = shp.clusterTransforms[0].outputs(type='cluster')[0]
			memberSet = clusterDefNode.message.outputs(type='objectSet')[0]
		except:
			continue

		pm.select(memberSet, r=True)
		verts = [v for v in pm.selected(fl=True) if isinstance(v, pm.MeshVertex)]
		pm.percent(clusterDefNode, verts, v=1.0)

	pm.select(sels, r=True)

def smoothSelectedClusterWeight(dropoffMult=3):
	sels = pm.selected(type='transform')

	for sel in sels:
		shp = sel.getShape(ni=True)
		if not shp:
			continue
		if shp.type() != 'clusterHandle':
			continue

		clusterDefNode, memberSet = None, None
		try:
			clusterDefNode = shp.clusterTransforms[0].outputs(type='cluster')[0]
			memberSet = clusterDefNode.message.outputs(type='objectSet')[0]
		except:
			continue

		pm.select(memberSet, r=True)
		verts = [v for v in pm.selected(fl=True) if isinstance(v, pm.MeshVertex)]
		pos = [pm.pointPosition(v) for v in verts]
		x = [p.x for p in pos]
		y = [p.y for p in pos]
		z = [p.z for p in pos]
		minx = min(x)
		maxx = max(x)
		miny = min(y)
		maxy = max(y)
		minz = min(z)
		maxz = max(z)

		dropoffDistance = abs(((maxx-minx)+(maxy-miny)+(maxz-minz))/3)
		
		tmpLoc = pm.spaceLocator(n='smoothClusterTmp_loc')
		pm.delete(pm.pointConstraint(sel, tmpLoc))
		dropoffPt = tmpLoc.getTranslation(ws=True)
		pm.delete(tmpLoc)

		pm.percent(clusterDefNode, verts, 
				dp=dropoffPt, 
				dds=dropoffDistance*dropoffMult, 
				mp=True, 
				v=1.0)

	pm.select(sels, r=True)


def getClusterSetAndVertSelection():
	memberSet, vtxs = None, None
	sels = pm.selected()
	if not sels:
		om.MGlobal.displayError('No selection.')
		return memberSet, vtxs

	vtxs = [v for v in sels if isinstance(v, pm.MeshVertex)]
	transforms = [t for t in sels if isinstance(t, pm.nt.Transform)]
	for tr in transforms:
		shp = tr.getShape(ni=True)
		if shp.type() == 'clusterHandle':
			try:
				clusterDefNode = shp.clusterTransforms[0].outputs(type='cluster')[0]
				memberSet = clusterDefNode.message.outputs(type='objectSet')[0]
				break
			except:
				continue

	if not vtxs or not memberSet:
		om.MGlobal.displayError('Invalid selection : Select a cluster and some vertices.')
		return memberSet, vtxs

	return memberSet, vtxs

def addClusterMember():
	memberSet, vtxs = getClusterSetAndVertSelection()
	if memberSet and vtxs:
		for vtx in vtxs:
			memberSet.add(vtx)

def removeClusterMember():
	memberSet, vtxs = getClusterSetAndVertSelection()
	if memberSet and vtxs:
		for vtx in vtxs:
			memberSet.remove(vtx)


	
