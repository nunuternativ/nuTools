# import pymel.core as pm
import maya.cmds as mc
import maya.OpenMaya as om


def getAllGeoInRef(ref):
	nodes = mc.referenceQuery(ref, nodes=True, dp=True)
	geo = []
	for n in nodes:
		try:
			shp = mc.listRelatives(n, shapes=True, ni=True)[0]
			if shp and mc.objectType(shp)=='mesh' and mc.getAttr('%s.v' %n) == True:
				geo.append(n)
		except: pass

	return geo


def getRefFromObjects(objs=[]):
	refPaths = set()
	for obj in objs:
		refPath = mc.referenceQuery(obj, f=True)
		refPaths.add(refPath)

	return refPaths 


def convertSelectionToAllGeoInRef():
	sels = mc.ls(sl=True, l=True, type='transform')
	refs = getRefFromObjects(sels)

	geos = []
	for ref in refs:
		geo = getAllGeoInRef(ref)
		if geo:
			geos.extend(geo)
	if geos:
		mc.select(geos, r=True)