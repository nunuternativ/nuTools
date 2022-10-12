import pymel.core as pm 
import maya.OpenMaya as om

class GeoGrpBsh(object):


	def __init__(self, srcGrp=None, desGrp=None, tol=0.001):
		self.srcGrp = srcGrp
		self.desGrp = desGrp 
		self.bshNodes = []
		self.meshDict = {}
		self.pairDict = {}
		self.tol = tol


	def checkValid(self):
		srcChildren = self.srcGrp.getChildren(ad=True, type='transform')
		desChildren = self.desGrp.getChildren(ad=True, type='transform')

		grpList = [self.srcGrp, self.desGrp]
		childrenLists = [srcChildren, desChildren]
		for grp, children in zip(grpList,childrenLists):
			self.meshDict[grp] = []
			for c in children:
				if isinstance(c, pm.nt.Joint):
					return False
				shp = c.getShape(ni=True)
				if shp:
					if not isinstance(shp, pm.nt.Mesh):
						return False
					else:
						self.meshDict[grp].append(c)

		if len(self.meshDict[self.srcGrp]) != len(self.meshDict[self.desGrp]):
			return False

		return True

	def compareBB(self, BBa, BBb):
		for i in xrange(2):
			ptA = BBa[i]
			ptB = BBb[i]
			if ptA.isEquivalent(ptB, self.tol) == False:
				return False
		return True


	def matchGeo(self):
		res = self.checkValid()
		if res == False:
			return

		self.pairDict = {}
		desBBDict = {}
		for des in self.meshDict[self.desGrp]:
			desBBDict[des] = des.getBoundingBox()

		for src in self.meshDict[self.srcGrp]:
			srcBB = src.getBoundingBox()

			for des, desBB in desBBDict.iteritems():

				if self.compareBB(srcBB, desBB) == True:
					self.pairDict[src] = des
					del desBBDict[des]
					break

		# print self.pairDict

	# def connect(self):
	# 	for src, des in self.pairDict.iteritems():
	# 		nodeName = '%s_bsn' %src.nodeName().split(':')[-1].split('_')[0]
	# 		bshNode = pm.blendShape(src, des, w=(0, 1.0), bf=True, n=nodeName, o='world')
	# 		self.bshNodes.append(bshNode)

	def connect(self):
		for src, des in self.pairDict.iteritems():
			nodeName = '%s_bsn' %src.nodeName().split(':')[-1].split('_')[0]
			bshNode = pm.blendShape(src, des, w=(0, 1.0), bf=True, n=nodeName, o='world')
			self.bshNodes.append(bshNode)


	def disconnect(self):
		pass