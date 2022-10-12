import pymel.core as pm
import maya.OpenMaya as om
import maya.mel as mel
import nuTools.misc as misc

from nuTools.corrective import invertDeformation as idef

reload(misc)
reload(idef)



class ShotSculpt(object):

	def __init__(self):
		self.WINDOW_NAME = 'shotCorrectiveSculptWin'
		self.WINDOW_TITLE = 'Shot Corrective Sculpt v1.2'
		self.shotSculptGrpName = 'shotSculpt_grp'

		self.wfEditColorCode = 20
		self.wfOrigColorCode = 23

		self.shotSculptGrp = None
		self.animMesh = None
		self.editMesh = None
		
	def UI(self):
		if pm.window(self.WINDOW_NAME, ex=True):
			pm.deleteUI(self.WINDOW_NAME, window=True)
		with pm.window(self.WINDOW_NAME, title=self.WINDOW_TITLE, s=False, mb=True, mnb=True, mxb=False) as self.mainWindow:
			pm.menu(l='Tools')
			pm.menuItem(l='remove targets', c=pm.Callback(self.removeTargets))
			pm.menuItem(l='remove selected sculpts', c=pm.Callback(self.removeSelectedSculpts))
			pm.menuItem(l='remove all sculpts', c=pm.Callback(self.removeAllSculpts))
			pm.setParent('..', menu=True)
			with pm.frameLayout(lv=False, bs='etchedIn', mh=5, mw=5, fn='smallObliqueLabelFont', parent=self.mainWindow):
				with pm.rowColumnLayout(nc=3, co=[(1, 'left', 5), (2, 'left', 15), (3, 'left', 15)]):
					self.selCtrl = pm.button(l='Select Ctrl', h=30, w=65, c=pm.Callback(self.selectEditGrp))
					self.sculpt = pm.button(l='Sculpt', h=30, w=100, c=pm.Callback(self.sculpt))
					with pm.columnLayout(rs=3):
						self.applyButton = pm.button(l='Apply', h=30, w=65, c=pm.Callback(self.apply))
						self.revertButton = pm.button(l='Revert', h=30, w=65, c=pm.Callback(self.revert))
						self.autoKeyCheckBox = pm.checkBox('auto key', v=True)
			
		pm.showWindow(self.mainWindow)

	def getShotSculptGrp(self):
		if pm.objExists('|%s' %self.shotSculptGrpName) == False:
			self.shotSculptGrp = pm.group(em=True, n=self.shotSculptGrpName)
			om.MGlobal.displayWarning('New ShotSculpt group created. Please leave this group under wold parent.')
		else:
			self.shotSculptGrp = pm.PyNode('|%s' %self.shotSculptGrpName)
			
	def turnOnCtrls(self, editGrp, valueDict):
		for attr, value in valueDict.iteritems():
			attr.set(value)

	def turnOffCtrls(self, editGrp):
		attrs = editGrp.listAttr(st='f*', se=True, s=True, k=True, sn=True)
		retDict = {}
		for a in attrs:
			retDict[a] = a.get()
			a.set(0)

		return retDict

	def selectEditGrp(self):
		'''Called when 'Select Ctrl' button is pushed'''
		tr, shp = self.getAnimMesh()
		if not tr or not shp:
			om.MGlobal.displayError('No animMesh found in selection.')
			return
		print tr, shp
		animMeshOutputs = shp.message.outputs()
		if not animMeshOutputs:
			om.MGlobal.displayError('Cannot find shotSculpt control for your selection.')
			return

		pm.select(animMeshOutputs[0], r=True)

	def removeTargets(self):
		self.getShotSculptGrp()
		editGrps = self.shotSculptGrp.getChildren()
		for grp in editGrps:
			meshes = [m for m in grp.getChildren(type='transform') if misc.checkIfPly(m)==True]
			pm.delete(meshes)

	def getAnimMesh(self):
		tr, shp = None, None

		# get selection, expecting animated original mesh.
		sel = misc.getSel()
		if not sel:
			return tr, shp

		# in case user select editGrp
		self.getShotSculptGrp()
		if sel in self.shotSculptGrp.getChildren():
			tr = sel.attr('animMesh').inputs()[0]

		elif sel in self.shotSculptGrp.getChildren(ad=True, type='transform'):
			# if user select edit mesh try to get the animMesh
			try:
				editGrp = [i for i in self.shotSculptGrp.getChildren(type='transform') if i == sel.getParent()]
				tr = editGrp[0].animMesh.inputs()[0]
			except:
				return tr, shp
		else:
			tr = sel

		# check if its a polygon
		if not misc.checkIfPly(tr):
			return tr, shp

		# get shape node
		shp = tr.getShape(ni=True)
		if not shp:
			om.MGlobal.displayError('%s  has no shape.' %sel)

		return tr, shp

	def removeSelectedSculpts(self):
		sels = misc.getSel(num='inf')
		for sel in sels:
			pm.select(sel, r=True)
			tr, shp = self.getAnimMesh()
			if not tr or not shp:
				om.MGlobal.displayError('No animMesh found in selection.')
				continue

			self.animMesh = tr
			animMeshShp = self.animMesh.getShape(ni=True)
			animMeshShp.overrideEnabled.set(False)

			# find editGrp for current origMesh, if not one, create.
			editGrps = self.shotSculptGrp.getChildren()
			editGrp = None

			for i in shp.message.outputs():
				if i in editGrps:
					editGrp = i
					break
			# delete bsh
			try:
				bshs = []
				bshNodes = editGrp.bshNode.inputs()
				if bshNodes:
					bshs.append(bshNodes[0])
				parNodes = editGrp.parBshNode.inputs()
				if parNodes:
					bshs.append(parNodes[0]) 

				pm.delete(bshs)
			except:
				pass

			if editGrp:
				pm.delete(editGrp)

	def removeAllSculpts(self):
		self.getShotSculptGrp()
		editGrps = self.shotSculptGrp.getChildren(type='transform')

		# delete blendShapes
		bshs = []
		for grp in editGrps:
			animMesh = grp.animMesh.inputs()
			if animMesh:
				animMeshShp = animMesh[0].getShape(ni=True)
				animMeshShp.overrideEnabled.set(False)

			try:
				bshs = []
				bshNodes = grp.bshNode.inputs()
				if bshNodes:
					bshs.append(bshNodes[0])
				parNodes = grp.parBshNode.inputs()
				if parNodes:
					bshs.append(parNodes[0]) 
				pm.delete(bshs)
			except:
				pass

		pm.delete(self.shotSculptGrp)
		self.animMesh = None
		self.editMesh = None

	def sculpt(self):
		tr, shp = self.getAnimMesh()
		if not tr or not shp:
			om.MGlobal.displayError('No animMesh found in selection.')
			return

		self.animMesh = tr

		# find editGrp for current origMesh, if not one, create.
		editGrps = self.shotSculptGrp.getChildren()
		editGrp = None

		for i in shp.message.outputs():
			if i in editGrps:
				editGrp = i
				break

		if not editGrp:
			nsSplits = self.animMesh.nodeName().split(':')
			nodeNameNoNs = nsSplits[-1]
			grpName = '%s__%s' %('__'.join(nsSplits[:-1]), nodeNameNoNs)
			editGrp = pm.group(em=True, n=grpName)

			misc.addMsgAttr(editGrp, 'animMesh')
			pm.connectAttr(shp.message, editGrp.animMesh, f=True)

			misc.hideAttr(editGrp, hide=True, t=True, r=True, s=True, v=True)
			pm.parent(editGrp, self.shotSculptGrp)

		# get current frame number.
		currentFrame = int(pm.currentTime(q=True))

		# get edit mesh, if not one already created, duplicate origMesh.
		editMeshes = [grp for grp in editGrp.getChildren(type='transform') if misc.checkIfPly(grp)==True]
		editMesh = None
		editGrpName = editGrp.nodeName()

		for m in editMeshes:
			if m.nodeName() == 'f%s_%s' %(currentFrame, editGrpName):
				editMesh = m
				break

		if not editMesh:
			editMesh = pm.duplicate(self.animMesh)[0]
			misc.cleanUnuseOrigShape([editMesh])
			misc.lockAttr(editMesh, lock=False, t=True, r=True, s=True, v=True)
			editMesh.rename('f%s_%s' %(currentFrame, editGrpName))
			pm.parent(editMesh, editGrp)

			# apply lambert1
			try:
				lambert1 = pm.ls('lambert1', type='lambert')[0]
				pm.hyperShade(editMesh, assign=lambert1)
			except:
				pass

			# display smooth preview
			editShp = editMesh.getShape(ni=True)
			pm.displaySmoothness(editShp, po=1)
			editShp.overrideEnabled.set(True)
			editShp.overrideColor.set(self.wfEditColorCode)

			# add frame number as an attribute for the edit mesh
			misc.addNumAttr(editMesh, 'editFrame', 'long', dv=currentFrame, lock=True, hide=True)

		# hide origMesh shape, unhide edit mesh so user can edit the mesh.
		editMesh.visibility.set(True)

		try:
			shp.visibility.set(False)
			shp.overrideEnabled.set(True)
			shp.overrideColor.set(self.wfOrigColorCode)
		except:
			pass

		# select editMesh. toggle on vertex component mode.
		pm.select(editMesh, r=True)
		self.editMesh = editMesh
		om.MGlobal.displayInfo('EDITTING:  f%s  for  %s.' %(currentFrame, self.animMesh)),

	def apply(self):
		if not self.editMesh:
			om.MGlobal.displayError('No editMesh found. Select a mesh and hit Sculpt button first.')
			return

		# Get editGrp from editMesh parent. 
		editGrp = self.editMesh.getParent()

		if not editGrp or not editGrp.hasAttr('animMesh'):
			om.MGlobal.displayError('Cannot find editGrp.')
			return

		# Get animMesh from editGrp
		editGrpConnections = pm.listConnections(editGrp.attr('animMesh'), s=True, d=False)
		if not editGrpConnections:
			om.MGlobal.displayError('Cannot find animMesh from edit mesh.')
			return

		try:
			origShp = editGrpConnections[0].getShape(ni=True)
			origShp.visibility.set(True)
		except:
			om.MGlobal.displayError('Cannot hide animMesh. Attribute is locked or something?')
			return

		self.animMesh = editGrpConnections[0]

		# get current frame
		currFrame = pm.currentTime(q=True)
		# get edit frame from editMesh attribute
		editFrame = self.editMesh.editFrame.get()
		# set current frame to that frame
		pm.currentTime(editFrame, e=True)

		# turn off all ctrl attributes
		oldValues = self.turnOffCtrls(editGrp)
		
		# animMesh name is the same as editGrp name, except for ':' will be replaced with '__'
		animMeshName = editGrp.nodeName()

		# check if animMesh has origShape or not, if yes apply invert mesh
		invertMesh = None
		if misc.getOrigShape(self.animMesh, False):
			# get existing invert mesh under editMesh transform
			try:
				invertMesh = [shp for shp in self.editMesh.getShapes() if shp.isIntermediate()==True and 'inverted' in shp.nodeName()]
				invertMesh = invertMesh[0]
			except: 
				pass
			
			tmpInvTrans = None
			# if found invert mesh built a new transform for it, unintermediate it
			if invertMesh:
				tmpInvTrans = pm.group(em=True, n='tmpInverted_ply')
				misc.snapTransform('parent', self.editMesh, tmpInvTrans, False, True)
				pm.parent(invertMesh, tmpInvTrans, r=True, s=True)
				invertMesh.intermediateObject.set(False)

			# generate inverted mesh
			invertShape = idef.invertDeformation(base=self.animMesh, 
												corrective=self.editMesh, 
												invert=tmpInvTrans)
		else:
			# animMesh has no origShape, meaning it was rigged using constraint only?
			invertShape = pm.duplicate(self.editMesh)[0]
			misc.cleanUnuseOrigShape([invertShape])
			misc.lockAttr(invertShape, lock=False, t=True, r=True, s=True, v=True)
			invertShape.rename('f%s_%s_inverted' %(editFrame, animMeshName))

		# invertShapeName should be the same as bsh node attr name
		invertShapeName = invertShape.nodeName()

		# If editGrp do not have ctrl attribute. Add ctrl attr to edit grp
		attrName = 'f%s' %editFrame 
		ctrlAttr = misc.addNumAttr(editGrp, attrName, 'float', min=0, max=1)

		bshNode = None
		index = 0
		# if this is the first time applying changes. Do blendshape to the original mesh.
		if not editGrp.hasAttr('bshNode') or not editGrp.bshNode.inputs():
			# check if the mesh already has blendshape applied in its rig
			parallel = False
			if [i for i in pm.listHistory(self.animMesh, il=True) if pm.objectType(i) in ['blendShape', 'wrap']]:
				parallel = True

			# create new blendshape
			bshNode = pm.blendShape(invertShape, self.animMesh, n='shotSculpt_%s_bsh' %animMeshName, foc=not(parallel), par=parallel)[0]

			parNode = None
			if parallel == True:
				parNode = [i for i in pm.listConnections(bshNode.outputGeometry[0], d=True, s=False, type='blendShape') if not i.isReferenced()][0]
				parNode.rename('shotSculpt_%s_parallelBsh' %animMeshName)

			#connect bsh node message to edit group for later query
			misc.addMsgAttr(editGrp, 'bshNode')
			pm.connectAttr(bshNode.message, editGrp.bshNode, f=True)

			misc.addMsgAttr(editGrp, 'parBshNode')
			if parNode:
				pm.connectAttr(parNode.message, editGrp.parBshNode, f=True)

		# not the first time, add to existing blendshape node
		else:
			bshNode = editGrp.bshNode.inputs()[0]
			indexList = bshNode.weightIndexList()

			# if editMesh for this frame do not exists
			if not bshNode.hasAttr(invertShapeName):
				index = [i for i in range(0, max(indexList)+2) if i not in indexList][0]
				tg = (self.animMesh, index, invertShape, 1 )
				pm.blendShape(bshNode, e=True, t=tg, w=(index, 1), tc=False)

		# connect ctrl attr
		bshAttr = bshNode.attr('w[%s]' %index)
		if not pm.isConnected(ctrlAttr, bshAttr):
			pm.connectAttr(ctrlAttr, bshAttr, f=True)
		
		# hide editMesh
		self.editMesh.visibility.set(False)
		# parent invert shpe to editMesh transform, set intermediate true to hide it
		invertShapeShp = invertShape.getShape(ni=True)
		pm.parent(invertShapeShp, self.editMesh, r=True, s=True)
		invertShapeShp.intermediateObject.set(True)
		# get rid of empty transform
		pm.delete(invertShape)
		# set the frame back to where the user set ti
		pm.currentTime(currFrame, e=True)
		# turn ctrl attrs back on
		self.turnOnCtrls(editGrp, oldValues)
		# set key frame
		if self.autoKeyCheckBox.getValue() == True:
			pm.setKeyframe(ctrlAttr, v=1.0, t=editFrame)
		# select editGrp (ctrl)
		pm.select(editGrp, r=True)

		self.editMesh = None
		om.MGlobal.displayInfo('APPLIED:  f%s  for  %s.' %(editFrame, self.animMesh))

	def getPoints(self, mesh, space=om.MSpace.kWorld):
		mFnMesh = misc.getMfnMesh(mesh)
		vtxPointArray = om.MPointArray()    
		mFnMesh.getPoints(vtxPointArray, space)
			
		# return a list off all points positions
		return vtxPointArray

	def checkEqualPoint(self, pointA, pointB):
		mPointA = om.MPoint(pointA[0], pointA[1], pointA[2])
		mPointB = om.MPoint(pointB[0], pointB[1], pointB[2])
		if mPointA.distanceTo(mPointB) <= 0.001:
			return True
		else:
			return False

	def revert(self):
		if not self.editMesh:
			om.MGlobal.displayError('No editMesh found. Select a mesh and hit Sculpt button first.')
			return

		editGrp = self.editMesh.getParent()
		if not editGrp or not editGrp.hasAttr('bshNode'):
			om.MGlobal.displayError('Cannot find editGrp.')
			return

		bshNode = editGrp.bshNode.inputs()[0]

		# turn bsh off to see the mesh in its original shape
		bshNode.envelope.set(0)

		# get edit frame
		editFrame = self.editMesh.editFrame.get()

		# get points for animMesh
		origPArray = self.getPoints(self.animMesh.longName())
		currPArray = self.getPoints(self.editMesh.longName())

		# got all the points info we need, turn bsh back on
		bshNode.envelope.set(1)

		# get shape node for editMesh and its long name to pass to mel
		editMeshShp = self.editMesh.getShape(ni=True)
		editMeshShpLn = editMeshShp.longName()

		for i in xrange(0, origPArray.length()):
			if self.checkEqualPoint(currPArray[i], origPArray[i]) == True:
				continue

			vtx = '%s.vtx[%i]' %(editMeshShpLn, i)
			mel.eval('move -ws %f %f %f %s;' %( origPArray[i].x, 
												origPArray[i].y, 
												origPArray[i].z, 
												vtx
											   ))
		# apply the deformation
		self.apply()

		om.MGlobal.displayInfo('REVERTED:  f%s  for  %s.' %(editFrame, self.animMesh))
	
		
