import os
import pymel.core as pm
import maya.OpenMaya as om

from nuTools import misc
reload(misc)
from nuTools.pipeline import pipeTools
reload(pipeTools)


def deleteEmptyGrpInHeirarchy(sel=None):
	if not sel:
		sel = misc.getSel()
		if not sel:
			return

	children = [c for c in sel.getChildren(type='transform', ad=True) if not c.getShapes() and not c.getChildren()]
	pm.delete(children)

def flattenPolygonHierarchy(sel=None):
	if not sel:
		sel = misc.getSel()
		if not sel:
			return

	children = [c for c in sel.getChildren(type='transform', ad=True)]
	for child in children:
		if misc.checkIfPly(child)==True:
			plyGChildren = [c for c in child.getChildren(type='transform', ad=True) if misc.checkIfPly(c)==True]
			if plyGChildren:
				parent = child.getParent()
				if parent:
					pm.parent(plyGChildren, parent)

	deleteEmptyGrpInHeirarchy(sel)

def mergeAll(tol=0.001, chunkNum=30):
	allPly = [p for p in pm.ls(type='transform') if misc.checkIfPly(p)==True]
	ply_chunks = []
	s = 0
	e = chunkNum
	for n in xrange(len(allPly)):
		chunk = allPly[s:e]
		ply_chunks.append(chunk)
		s = e
		e += chunkNum

	pm.refresh(suspend=True)
	for i, chunk in enumerate(ply_chunks):
		for ply in chunk:
			# pm.delete(ply, ch=True)
			pm.polyMergeVertex(ply, d=tol, am=False, ch=False) 
		print '%s/%s' %((i+1), len(ply_chunks))

	pm.refresh(suspend=False)
	pm.refresh(force=True)

def mergeAllBelow(tol=0.001, chunkNum=30):
	allPly = [p for p in pm.selected()[0].getChildren(ad=True) if misc.checkIfPly(p)==True]
	ply_chunks = []
	s = 0
	e = chunkNum
	for n in xrange(len(allPly)):
		chunk = allPly[s:e]
		ply_chunks.append(chunk)
		s = e
		e += chunkNum

	pm.refresh(suspend=True)
	allChunkLen = len(ply_chunks)
	for i, chunk in enumerate(ply_chunks):
		lenChunk = len(chunk)
		c = 0
		for ply in chunk:
			# pm.delete(ply, ch=True)
			pm.polyMergeVertex(ply, d=tol, am=False, ch=False) 
			c += 1
			print '%s/%s , %s/%s' %(c, lenChunk, i, len(ply_chunks))

	pm.refresh(suspend=False)
	pm.refresh(force=True)


def autoProjectAll(exceptions=[], chunkNum=30):
	allPly = [p for p in pm.ls(type='transform') if misc.checkIfPly(p)==True]
	ply_chunks = []
	s = 0
	e = chunkNum
	for n in xrange(len(allPly)):
		chunk = allPly[s:e]
		ply_chunks.append(chunk)
		s = e
		e += chunkNum

	pm.refresh(suspend=True)
	for chunk in ply_chunks:
		for ply in chunk:
			if ply not in exceptions:
				pm.polyAutoProjection(ply, lm=0, pb=0, ibd=1, cm=0, l=2, sc=1, o=1, p=6, ps=0.2, ws=0, ch=False)

	pm.refresh(suspend=False)
	pm.refresh(force=True)

def getAllCrvs():
	allCrvShps = pm.ls(type='nurbsCurve')
	allCrvs = []
	if allCrvShps:
		allCrvs = [i.getParent() for i in allCrvShps]

	return allCrvs

def deleteAllCrvs():
	allCrvs = getAllCrvs()
	pm.delete(allCrvs)

def getAllHidden():
	hiddenTrans = [t for t in pm.ls(type='transform') if misc.checkIfPly(t)==True and t.v.get()==False]
	return hiddenTrans

def deleteAllHidden():
	hiddens = getAllHidden()
	pm.delete(hiddens)

def getAllStickers(createSet=False):
	allCrvs = getAllCrvs()
	stickers = []
	for c in allCrvs:
		parent = c.getParent()
		parentOfParent = parent.getParent()
		suspect = None
		if parent.v.get() == False:
			suspect = parentOfParent
		else:
			suspect = parent

		if '_mm_' in suspect.nodeName():
			stickers.append(suspect)

	stickers = list(set(stickers))
	if createSet == True:
		newSet = pm.sets(em=True, n='sticker_set1')
		pm.sets(newSet, add=stickers)
		return newSet
	else:
		return stickers

def cleanAll():
	sel = misc.getSel()
	if not sel or sel not in pm.ls(assemblies=True):
		om.MGlobal.displayError('Please select top geo group.')
		return

	result = pm.confirmDialog(title='LOD Optimization', message='Start cleanup?\nThis may take a while.', 
		button=('OK', 'Cancle'))
	if result == 'Cancle':
		return

	chunkSize = 30
	result = pm.promptDialog(title='Merge option', message='Chunk size:', text='100', 
		button=('OK', 'Cancle'))
	if result == 'Cancle':
		return
	else:
		chunkSize = int(pm.promptDialog(q=True, text=True))

	tol = 0.001
	result = pm.promptDialog(title='Merge option', message='tolerance:', text='0.001', 
		button=('OK', 'Cancle'))
	if result == 'Cancle':
		return
	else:
		tol = float(pm.promptDialog(q=True, text=True))

	doUvResult = pm.confirmDialog(title='UV option', message='Do auto project UV?', 
		button=('Yes', 'No'))
	doAutoProjectUv = True
	if doUvResult == 'No':
		doAutoProjectUv = False

	doCleanupResult = pm.confirmDialog(title='Cleanup option', message='Do scene cleanup?', 
		button=('Yes', 'No'))
	doCleanup = True
	if doCleanupResult == 'No':
		doCleanup = False

	print '\nUnlocking all translations under top group...',
	misc.unlockChannelbox()

	print '\nDeleting histories...'
	pm.delete(sel, ch=True)

	print '\nFinding stickers...',
	stickers = getAllStickers()

	print '\n%s sticker(s) found, Deleting all curves...' %(len(stickers)),
	deleteAllCrvs()

	print '\nDeleting all hidden polygons...',
	deleteAllHidden()

	print '\nFlatten all polygon hierarchies...',
	flattenPolygonHierarchy()

	print '\nmerging close vertices...',
	if chunkSize > 0:
		mergeAll(tol=tol, chunkNum=chunkSize)

	if doAutoProjectUv == True:
		print '\nAuto projecting UVs...',
		autoProjectAll(exceptions=stickers)

	if doCleanup == True:
		print '\nFinal cleanup in progress...',
		pipeTools.deleteAllTurtleNodes()
		pipeTools.deleteExtraDefaultRenderLayer()
		misc.deleteAllTypeInScene('displayLayer')
		pipeTools.deleteAllUnknownNodes()
		pipeTools.deleteUnusedNodes()
		pipeTools.optimizeSceneSize()

	pm.confirmDialog(title='LOD Optimization', message='Optimization complete', button='OK')

def transferShadeAssign_object(parent=None, child=None):
	"""
	Assingn the shade assigned to the parent to the child.
		args:
			parent = The source object to get shader assigned. (PyNode)
			child = The child object to assign shader to. (PyNode)

		return: None
	"""

	if not parent or not child:
		sels = getSel(num='inf')
		parent = sels[0]
		child = sels[1:]
		if not parent or not child:
			return
	if not isinstance(child, (list, tuple)):
		child = [child]

	parentShp = parent.getShape()
	childShp = []
	for c in child:
		cs = c.getShapes(ni=True)
		if not cs:
			continue
		childShp.append(cs)

	if not parentShp or not childShp:
		return

	#kill all duplicate(s)
	parentSgs = list(set(pm.listConnections(parentShp, d=True, type='shadingEngine')))
	if not parentSgs:
		return
	if len(parentSgs)>1:
		pm.warning('The object has more than one shadingEngine assigned to it, will use first one.')

	sg = parentSgs[0]
	#shd = parentSgs[0].surfaceShader.inputs()
	if sg.isReferenced() == True:
		misc.addMsgAttr(sg, '_refDuplicate')
		if sg._refDuplicate.inputs():
			sg = sg._refDuplicate.inputs()[0]
		else:
			newSg = pm.duplicate(sg, upstreamNodes=True)[0]
			pm.connectAttr(newSg.message, sg._refDuplicate, f=True)
			sg = newSg

	result = True
	for c in childShp:
		try:
			pm.sets(sg, e=True, nw=True, fe=c)		
		except:
			result = False

	return result

def swapImportObj():
	from tempfile import mkstemp
	pluginFileName = 'objExport.mll'
	if not pm.pluginInfo(pluginFileName, q=True, l=True):
		pm.loadPlugin(pluginFileName)

	sels = pm.selected(type='transform')
	if not sels:
		om.MGlobal.displayError('Select something!')
		return

	models = (i for i in sels if misc.checkIfPly(i)==True)
	pm.refresh(suspend=True)
	
	i = 0
	for tr in models:
		trParent = tr.getParent()
		trName = tr.nodeName()

		wFileH, wFilePath = mkstemp('.obj')
		pm.select(tr, r=True)
		pm.exportSelected(wFilePath, type='OBJexport', 
			options="groups=0;ptgroups=0;materials=0;smoothing=0;normals=1", 
			force=True)
		newNodes = pm.importFile(wFilePath, type='OBJ', 
			returnNewNodes=True, options='mo=0')

		newTr = None
		for n in newNodes:
			if n.type() == 'transform' and misc.checkIfPly(n) == True:
				newTr = n
				break
		else:
			i += 1
			continue

		transferShadeAssign_object(parent=tr, child=newTr)
		if trParent:
			currentIndx = trParent.getChildren(type='transform').index(tr)
			pm.delete(tr)
			pm.parent(newTr, trParent)
			newTr.rename(trName)
			pm.reorder(newTr, r=currentIndx+1)
		else:
			pm.delete(tr)
		
		os.close(wFileH)
		i += 1

	pm.refresh(suspend=False)
	pm.refresh(force=True)

	pm.confirmDialog(title='Swap Import OBJ', message='Swapped %s object(s)' %i, button='OK')