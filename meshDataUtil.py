import cPickle, gzip
from maya.api import OpenMaya as om
import pymel.core as pm
import maya.cmds as mc
import maya.mel as mm

# -------------------------------------------------
# --------------- utility functions ---------------
def getMfnMesh(meshName):
	mSel = om.MSelectionList()
	mSel.add(meshName)

	mDag = mSel.getDagPath(0)
	mfnMesh = om.MFnMesh(mDag)
	return mfnMesh

def getUv(meshFn):
	uvCounts, uvIds = meshFn.getAssignedUVs()
	us, vs = meshFn.getUVs()
	return uvCounts, uvIds, us, vs

def getTopology(meshFn):
	vtxCounts, vtxLists = meshFn.getVertices()
	return vtxCounts, vtxLists

def getNormals(meshFn):
	normals = meshFn.getVertexNormals(True)
	return normals

def setUvFromData(meshFn, uvData):
	uvCounts = uvData['uvCounts']
	uvIds = uvData['uvIds']
	us = uvData['us']
	vs = uvData['vs']

	meshFn.clearUVs()
	meshFn.setUVs(us, vs)
	meshFn.assignUVs(uvCounts, uvIds)

# -------------------------------------------------
# ---------------- write functions ----------------
def writeUvData(objs, path):
	data = dict()
	for obj in objs:
		objShape = obj.getShape()
		meshFn = getMfnMesh(objShape.longName())

		uvCounts, uvIds, us, vs = getUv(meshFn)

		uvData = {'uvCounts': tuple(uvCounts), 
				'uvIds': tuple(uvIds), 
				'us': tuple(us), 
				'vs': tuple(vs)}

		objName = obj.nodeName().split(':')[-1]
		data[objName] = uvData

	with open(path, 'wb') as f:
		cPickle.dump(data, f, cPickle.HIGHEST_PROTOCOL)

def writeTopologyData(objs, path):
	data = dict()
	for obj in objs:
		objShape = obj.getShape()
		meshFn = getMfnMesh(objShape.longName())

		vtxCounts, vtxLists = getTopology(meshFn)

		topoData = {'vtxCounts': tuple(vtxCounts), 
				'vtxLists': tuple(vtxLists)}
		objName = obj.nodeName().split(':')[-1]
		data[objName] = topoData

	with open(path, 'wb') as f:
		cPickle.dump(data, f, cPickle.HIGHEST_PROTOCOL)

def writeNormalsData(objs, path):
	data = dict()
	for obj in objs:
		objShape = obj.getShape()
		meshFn = getMfnMesh(objShape.longName())

		normals = getNormals(meshFn)
		normalsData = tuple((tuple(n) for n in normals))

		objName = obj.nodeName().split(':')[-1]
		data[objName] = normalsData

	with open(path, 'wb') as f:
		cPickle.dump(data, f, cPickle.HIGHEST_PROTOCOL)


# -------------------------------------------------
# ---------------- read functions ----------------
def readData(path):
	data = {}
	with open(path, 'rb') as f:
		data = cPickle.load(f)
	
	return data
	
