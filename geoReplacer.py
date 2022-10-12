import pymel.core as pm
import maya.OpenMaya as om
import re, os
from pprint import pprint
from nuTools import misc, config


reload(misc)
reload(config)

global gGeoReplacerRefs
gGeoReplacerRefs = []

TOLERANCE = 0.1

class GeoReplacer(object):
	"""
	Geometry Replacer Class helps you match geometries with the same name/position to identify them in as a pair.
	After each object is identified, you can choose a method for replacing old geometry with the new one.

	Instance Command :
		from nuTools import util as ut
		reload(ut)
		geoReplacer = ut.GeoReplacer()
		geoReplacer.UI()

	Methods are:
		1. copyUv : Will copy the UV from the new object to the old one. If the old object has deformer(s) applied,
					this method will not leave any history on the mesh.
		2. replace : Replace the old object with the new one by deleting the old one and parent the new one to the 
					same heirachy.
		3. copySkinWeight : Apply smooth skin and copy skin weight from the old one to the new one.
	"""		
	def __init__(self):
		self.WINDOW_NAME = 'geoReplacerMainWin'
		self.WINDOW_TITLE = 'Geometry Replacer v3.2'
		self.matchDict = {}
		self.partMatchDict = {}
		self.noMatch = []
		self.sels = []
		self.unSels = []
		self.nonTopoMatchObjs = []
		self.centers = {}

	def UI(self):
		pm.windowPref(ra=True)
		if pm.window(self.WINDOW_NAME, ex=True):
			pm.deleteUI(self.WINDOW_NAME, window=True)
		with pm.window(self.WINDOW_NAME, title=self.WINDOW_TITLE, s=False, mnb=True, mxb=False) as self.mainWindow:
			with pm.frameLayout(l='Source File', mh=5, mw=5, fn='smallObliqueLabelFont'):      
				with pm.columnLayout(adj=True, rs=5, co=['both', 5]):
					with pm.rowColumnLayout(nc=2, co=[(1, 'left', 55), (2, 'left', 20)]):
						pm.button(l='Create Ref', c=pm.Callback(self.createRef), w=75, h=30, bgc=(0,0.4,0.2))
						pm.button(l='Remove Ref', c=pm.Callback(self.removeRef), w=75, h=30, bgc=(0.4,0.0,0.0))


			with pm.frameLayout(l='Matching', mh=5, mw=5, fn='smallObliqueLabelFont'):     		
				with pm.columnLayout(adj=True, rs=0, co=['both', 5]):
					self.feedBackTxt = pm.text(l='Select original objects and press "Match Selected".', h=20, bgc=[0.3,0,0])
					self.feedBackNoMatchTxt = pm.text(l='N/A', h=20, bgc=[0.3,0,0])
				with pm.columnLayout(adj=True, rs=5, co=['both', 5]):
					with pm.rowColumnLayout(nc=2, co=[(1, 'left', 5), (2, 'left', 5)]):
						prefixTxt = pm.text(l='Namespace')
						self.prefixTxtFld = pm.textField(w=150)

				with pm.columnLayout(adj=True, rs=5, co=['both', 65]):
					# with pm.rowColumnLayout(nc=2, co=[(1, 'left', 5), (2, 'left', 5)]):
						# checkTopoTxt = pm.text(l='check topology')

					pm.button(l='Match by Name', w=100, h=25, bgc=(0,0.3,0.3), c=pm.Callback(self.matchObjCall, 'name'))
					with pm.rowColumnLayout(nc=2, co=[(1, 'left', 5), (2, 'left', 5)]):
						tolTxt = pm.text(l='tolerance')
						self.toleranceFloatFld = pm.floatField(value=TOLERANCE, w=50)
					pm.button(l='Match by Center and Volume', w=100, h=25, bgc=(0.4,0.0,0.0), c=pm.Callback(self.matchObjCall, 'centerAndVolume'))
					
					with pm.rowColumnLayout(nc=2, co=[(1, 'left', 0), (2, 'left', 5)]):
						pm.button(l='Select\nMatched', w=75, h=35, c=pm.Callback(self.selMatched))
						pm.button(l='Select\nNon Matched', w=75, h=35, c=pm.Callback(self.selNoMatched))

			with pm.frameLayout(l='Checking', mh=5, mw=5, fn='smallObliqueLabelFont'):
				with pm.columnLayout(adj=True, rs=5, co=['both', 50]):   		
					pm.button(l='Check Topology', w=100, h=25, bgc=(0.5,0.5,0.0), c=pm.Callback(self.checkTopologyCall))
					pm.button(l='Select\nNon Matched', w=75, h=35, c=pm.Callback(self.selNoTopoMatched))

			with pm.frameLayout(l='Replaceing', mh=5, mw=5, fn='smallObliqueLabelFont'):     		
				with pm.rowColumnLayout(nc=2, rs=(1, 5), co=[(1, 'left', 52), (2, 'left', 5)]):
					pm.text(l='Replace Methods')
					with pm.optionMenu() as self.metOptionMenu:
							pm.menuItem(l='copyUv')
							pm.menuItem(l='setUv')
							pm.menuItem(l='replace')
							pm.menuItem(l='replace(relative)')
							pm.menuItem(l='copySkinWeight')
							pm.menuItem(l='do nothing')
					pm.text(l='Shader Options')
					with pm.optionMenu() as self.shdOptionMenu:
							pm.menuItem(l='use original')
							pm.menuItem(l='use imported')
							pm.menuItem(l='do nothing')

				with pm.columnLayout(adj=True, rs=5, co=['both', 50]):
					pm.button(l='Replace Selected', w=100, h=30, bgc=(0,0.3,0.3), c=pm.Callback(self.replaceObj, 'selected'))
					pm.button(l='Replace All', w=100, h=40, bgc=(0,0.4,0.2), c=pm.Callback(self.replaceObj, 'all'))


	def createRef(self):
		currPath = pm.sceneName()
		try:
			assetPath = '/'.join(currPath.split('/')[0:6])
			refDirPath = assetPath.replace('/work/', '/publ/')
			# refDirPath = '%s/publish' %(assetPath)
		except:
			om.MGlobal.displayWarning('Failed splitting path.')
			refDirPath = os.path.dirname(currPath)
		
		# if not os.path.exists(refDirPath):
		# 	om.MGlobal.displayError('Path do not exists: %s' %refDirPath)
			

		refFilePath = pm.fileDialog2(ff="Maya Files (*.ma *.mb)", ds=2, fm=1, 
				dir=refDirPath, cap='Create Reference', okc='Reference')
		if not refFilePath:
			return
		basename = os.path.basename(refFilePath[0])
		fileName = os.path.splitext(basename)[0]
		ref = pm.createReference(refFilePath, ns=fileName)

		global gGeoReplacerRefs
		ns = ref.namespace
		gGeoReplacerRefs.append(ref) 

		#reset prefix text field
		self.prefixTxtFld.setText('%s:' %ns)
	

	def matchObjCall(self, method, prefix=''):
		if not prefix:
			prefix = self.prefixTxtFld.getText()
		
		#reset the status txt
		try:
			self.feedBackTxt.setBackgroundColor([0.3,0,0])
			self.feedBackNoMatchTxt.setBackgroundColor([0.3,0,0])
			self.feedBackTxt.setLabel('Select original objects and press "Match Selected".')
			self.feedBackNoMatchTxt.setLabel('N/A')
		except:
			pass

		self.getSelMesh()

		self.matchDict, self.noMatch = self.matchObj(prefix=prefix, method=method)

		
		try:
			matchNum = len(self.matchDict)
			noMatchNum = len(self.noMatch)
			self.feedBackTxt.setLabel('%s  object(s) matched.' %matchNum)
			self.feedBackNoMatchTxt.setLabel('%s object(s) unable to find match.' %noMatchNum)

			if matchNum > 0:
				self.feedBackTxt.setBackgroundColor([0,0.5,0])
			if noMatchNum == 0:
				self.feedBackNoMatchTxt.setBackgroundColor([0,0.5,0])
		except:
			pass

		return self.matchDict

	def checkTopologyCall(self):
		if not self.matchDict:
			om.MGlobal.displayError('Please do matching first.')
			return
		if not all([pm.objExists(o) for o in self.matchDict.keys()]) or not all([pm.objExists(n) for n in self.matchDict.values()]):
			om.MGlobal.displayError('Some of the object(s) in data do not exists, please do matching first.')
			return

		self.nonTopoMatchObjs = []
		for old, new in self.matchDict.iteritems():
			if not self.checkTopology(old, new):
				self.nonTopoMatchObjs.append(old)
		if self.nonTopoMatchObjs:
			print '----- Objects with different topology -----'
			print '\n'.join([str(o.nodeName()) for o in self.nonTopoMatchObjs])
		else:
			print 'All matched object(s) has the same topology.',
		return self.nonTopoMatchObjs

	def selNoTopoMatched(self):
		if not self.nonTopoMatchObjs:
			return
		pm.select(self.nonTopoMatchObjs, r=True)

	def selMatched(self):
		sels = misc.getSel(num='inf')
		if not sels:
			return
		orig, new = [], []
		for s in sels:
			if s in self.matchDict.keys():
				orig.append(s)
				new.append(self.matchDict[s])
		if orig and new:
			pm.select([orig, new], r=True)

	def selNoMatched(self):
		if not self.noMatch:
			return
		pm.select(self.noMatch, r=True)

	def replaceObj(self, scope):
		if not self.matchDict:
			return

		method = self.metOptionMenu.getValue()
		
		match = {}
		self.partMatchDict = {}
		if scope == 'selected':
			sels = misc.getSel(num='inf')
			for s in sels:
				if s in self.matchDict.keys():
					newObj = self.matchDict[s]
					self.partMatchDict[s] = newObj
			match = self.partMatchDict

		elif scope == 'all':
			match = self.matchDict

		self.batchOpOnPairObjs(objDict=match, op=method)

	def removeRef(self):
		global gGeoReplacerRefs
		refs = gGeoReplacerRefs
		for ref in refs:
			try:
				ref.remove()
			except:
				pass

		gGeoReplacerRefs = []

	def importRef(self):
		if not self.ref:
			return
		self.ref.importContents(removeNamespace=True)

	def getSelMesh(self):
		self.sels = []
		sels = misc.getSel(num='inf')
		if not sels:
			pm.error('No selection! Select polygon(s) to find another with matching name.')

		filteredSel = []
		for s in sels:
			tran = None
			tran = self.checkIfPolygons(s)
			if tran:
				self.sels.append(tran)

	def checkIfPolygons(self, obj):
		shp = obj.getShape()
		if shp:
			meshShp = filter(lambda x: isinstance(x, (pm.nt.Mesh)), [shp])
			if meshShp:
				trans = meshShp[0].getParent()
				return trans

	def getUnselected(self):
		if not self.sels:
			return
		prefix = self.prefixTxtFld.getText()
		self.unSels = []
		allTrans = pm.ls('%s*' %prefix, type='transform')
		for i in allTrans:
			isPly = self.checkIfPolygons(i)
			if i not in self.sels and isPly:
				self.unSels.append(i)


	def matchObj(self, prefix='', method='name'):
		if not self.sels:
			return

		retDict, noMatch = {}, []
		objNum = len(self.sels)

		pm.progressWindow(isInterruptable=True, 
						maxValue=objNum,
						title='Progress', 
						status='Matching Geometries by %s...' %method)

		for sel in self.sels:
			#if user hit cancel
			if pm.progressWindow(q=True, isCancelled=True):
				pm.progressWindow(endProgress=True)
				print 'Cancelled by user.'
				break

			newObj = ''
			matchFound = False
			if method == 'name':
				splitNs = sel.nodeName().split(':')[-1]

				sameNames = pm.ls('%s%s' %(prefix, splitNs), r=True)

				for s in sameNames:
					if s == sel or s.isVisible() == False:
						sameNames.remove(s)	
				#we got more than one matching name. 
				if len(sameNames) > 1:
					#Will compare each object center and get the closest one.
					newObj, matchFound = self.compareCenter(sel, sameNames)
				else:
					if sameNames != []:
						newObj = sameNames[0]
						matchFound = True

			elif method == 'centerAndVolume':
				self.getUnselected()
				self.getUnSelCenters()

				newObj, matchFound = self.compareCenterAndVolume(sel, self.unSels)
				
			if matchFound == True and newObj not in retDict.values():
				newObj = pm.PyNode(newObj)
				retDict[sel] = newObj
			else:
				pm.warning('Cannot find match for  %s' %sel),
				noMatch.append(sel)

			#increment progress bar
			pm.progressWindow(e=True, step=1)

		pm.progressWindow(endProgress=True)

		pprint(retDict)

		return retDict, noMatch

	def checkTopology(self, obj1, obj2):
		mSel = om.MSelectionList()
		mSel.add(obj1.longName())
		mSel.add(obj2.longName())

		dMesh1 = om.MDagPath()
		mSel.getDagPath(0, dMesh1) 
		dMesh1.extendToShape()
		mfnA = om.MFnMesh(dMesh1)

		dMesh2 = om.MDagPath()
		mSel.getDagPath(1, dMesh2) 
		dMesh2.extendToShape()
		mfnB = om.MFnMesh(dMesh2)

		aa1 = om.MIntArray()
		aa2 = om.MIntArray()

		ba1 = om.MIntArray()
		ba2 = om.MIntArray()

		mfnA.getVertices(aa1, aa2)
		mfnB.getVertices(ba1, ba2)  

		if len(aa1) != len(ba1):
			return False

		fi = 0
		for ai, bi in zip(aa1, ba1):
			if ai != bi:
				return False
			sliceAA2 = aa2[fi:fi+ai]
			sliceBA2 = ba2[fi:fi+ai]

			for v in sliceAA2:
				if v not in sliceBA2:
					return False
			fi += ai

		return True

	def getUnSelCenters(self):
		for i in [s for s in self.unSels if s not in self.centers]:
			center = pm.objectCenter(i.getShape(ni=True), gl=True)
			self.centers[i] = center

	def compareCenter(self, oldObj, newObjs):
		matchFound = False
		closeObjs = []
		closestObject = ''
		oldCenter = pm.objectCenter(oldObj, gl=True)
		for s in newObjs:
			center = pm.objectCenter(s.getShape(ni=True), gl=True)
			if center == oldCenter:
				closeObjs.append(s)
		
		closeObjNum = len(closeObjs)
		if closeObjNum == 1:
			matchFound = True
			closestObject = closeObjs[0]

		return closestObject, matchFound

	def compareCenterAndVolume(self, oldObj, newObjs):
		tol = self.toleranceFloatFld.getValue()
		matchFound = False
		closestDist = 1000000
		closestObject = None
		closestObjects = []
		oldCenter = pm.objectCenter(oldObj, gl=True)

		for s in newObjs:
			dist = misc.getDistanceFromPosition(oldCenter, self.centers[s])
			if dist <= tol:
				closestObjects.append(s)
		
		closestObjNum = len(closestObjects)
		if closestObjNum > 1:
			# 'more than one'
			closestObject, matchFound = self.compareVolume(oldObj, closestObjects)
		elif closestObjNum == 1:
			# 'found one'
			closestObject = closestObjects[0]
			matchFound = True
		else:
			# 'not found'
			matchFound = False

		return closestObject, matchFound

	def compareVolume(self, oldObj, closestObjects):
		tol = self.toleranceFloatFld.getValue()
		matchFound = False
		vols = []
		closestObject = ''

		# pm.select(oldObj, r=True)
		oldVol = misc.computePolysetVolume(objs=[oldObj])
		
		for s in closestObjects:
			# pm.select(s, r=True)
			if s.nodeName() == 'tvc_batSignal_70917_Old:m6183_arch_1x6x2_1':
				print 
			newVol = misc.computePolysetVolume(objs=[s])
			vols.append(newVol)
		
		diff = [abs(i-oldVol) for i in vols]
		closestDiff = min(diff)

		if diff.count(closestDiff) == 1 and closestDiff <= tol:
			idx = diff.index(closestDiff)
			closestObject = closestObjects[idx]
			matchFound = True

		return closestObject, matchFound

	def batchOpOnPairObjs(self, objDict, op):
		if not objDict:
			pm.error('/nThis function need dictionary of {oldObject:newObject} as input.'),
		result = []
		objNum = len(objDict.keys())

		#Progress bar
		pm.progressWindow(isInterruptable=True, 
						maxValue=objNum,
						title='Progress', 
						status='%s...' %op)

		shadeMethod = self.shdOptionMenu.getValue()

		for k in sorted(objDict.keys(), key=lambda k:len(objDict[k].split('|')), reverse=True):
			v = objDict[k]
			#if user hit cancel
			if pm.progressWindow(q=True, isCancelled=True):
				pm.progressWindow(endProgress=True)
				print 'Cancelled by user.'
				break

			if op == 'do nothing':
				self.doApplyShade(old=k, new=v, shadeMethod=shadeMethod)
				result.append('nothing\t%s\t\t%s' %(v, k))

			elif op == 'copyUv':
				if not k.isReferenced():
					ret = misc.copyUv(parent=v, child=[k], rename=False, printRes=False)
					self.doApplyShade(old=k, new=v, shadeMethod=shadeMethod)
					if ret['uv'] == False:
						result.append({ret['uv']:'%s  --->  %s' %(v, k)})
				else:
					pm.warning('%s is a referenced object.' %k.nodeName())

			elif op == 'setUv':
				ret = misc.setUv(source=v, destination=k)
				self.doApplyShade(old=k, new=v, shadeMethod=shadeMethod)
				result.append('%s : %s\t\t%s' %(ret, v, k))

			elif op == 'replace' or op == 'replace(relative)':
				relativeArg = {'relative':True}
				nonRelativeArg = {}
				argDict = {'replace':nonRelativeArg, 'replace(relative)':relativeArg}

				# duplicate the source, delete all children
				dup = v.duplicate()[0]
				dupchildren = dup.getChildren(type='transform')
				if dupchildren:
					pm.delete(dupchildren)

				# unlock the souce (prevent popping)
				misc.unlockChannelbox(obj=[dup], heirachy=False, t=True, r=True, s=True)

				# get destination children, unlock them
				kchildren = k.getChildren(type='transform')
				misc.unlockChannelbox(obj=kchildren, heirachy=False, t=True, r=True, s=True)

				# the destination parent
				oldParent = k.getParent()

				# get the current child order of the destination
				currentIndx = oldParent.getChildren(type='transform').index(k)

				# do apply shader
				self.doApplyShade(old=v, new=dup, shadeMethod=shadeMethod)
				
				# store old name
				oldName = k.nodeName()
				
				# parent the destination children to the new parent first
				pm.parent(kchildren, dup)
				
				# delete destination
				pm.delete(k)

				# parent duplicate of source to the old parent
				pm.parent(dup, oldParent, **argDict[op])

				# reorder it, and rename it to be the same as before
				pm.reorder(dup, r=(currentIndx+1))
				dup.rename(oldName)

				result.append(dup)

			elif op == 'copySkinWeight':
				try:
					scs = misc.copySkinWeight(parent=k, child=v)
				except:
					scs = None
					pass

				self.doApplyShade(old=k, new=v, shadeMethod=shadeMethod)
				result = scs

			#increment progress bar
			pm.progressWindow(e=True, step=1)

		pm.progressWindow(endProgress=True)
		pprint(result)

	def doApplyShade(self, old, new, shadeMethod):
		if shadeMethod == 'use imported':
			misc.transferShadeAssign(parent=new, child=old)
		elif shadeMethod == 'use original':
			misc.transferShadeAssign(parent=old, child=new)

	def parentToGroup(self):
		sels = misc.getSel(num=2)
		newGrp = sels[0]
		oldGrp = sels[1]

		oldChilds = pm.listRelatives(oldGrp, children=True, type='transform')
		newChilds = pm.listRelatives(newGrp, children=True, type='transform')

		pm.delete(oldChilds)
		pm.parent(newChilds, oldGrp, r=True)
