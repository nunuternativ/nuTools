import pymel.core as pm
import maya.mel as mel
import maya.OpenMaya as om
import sys

from nuTools import misc
from nuTools.corrective import conePoseReader as cpr
from nuTools.corrective import invertDeformation as idef
from nuTools.util import symMeshReflector as smr

reload(misc)
reload(cpr)
reload(idef)
reload(smr)


class CorrectiveSculpter(object):

	def __init__(self, mesh=None, bufferMesh=None, name='body'):
		self.mesh = mesh
		self.bufferMesh = bufferMesh
		self.origMesh = None
		self.name = name

		self.mainGrp = None
		self.drivers = {}

		self.smr = smr.SymMeshReflector()
		self.smr.filterBaseGeo = False
		
		self.jnt = None
		self.parent = None

		self.bsh = None

		self.focusDriver = None
		self.focusDriverName = ''

		self.focusTargetMesh = None
		self.focusTargetGrp = None
		self.focusTargetName = ''

		self.targetDict = {}


		self.wfEditColorCode = 20
		self._defaultConeAngleValue = 90.0
		self._defaultTargetAngleValue = 10.0
		self._defaultTargetName = 'TARGET'
		self._defultOutputFloatFieldName = 'CRToutputFloatField'

		self.revertSliderDragging = False
		self.sculpting = False

		self.WINDOW_NAME = 'correctiveSculpterWin'
		self.WINDOW_TITLE = 'Corrective Sculpter v1.0'
	
	def UI(self):
		if pm.window(self.WINDOW_NAME, ex=True):
			pm.deleteUI(self.WINDOW_NAME, window=True)
		with pm.window(self.WINDOW_NAME, title=self.WINDOW_TITLE, s=False, mnb=True, mxb=False) as self.mainWindow:
			with pm.columnLayout(adj=True, rs=5, co=['both', 0]):
				
				# CRT group
				with pm.frameLayout(l='Corrective Group', bs='etchedIn', mh=5, mw=5, cll=True, cl=False, fn='smallObliqueLabelFont'):
					with pm.rowColumnLayout(nc=3, rs=(1, 5), co=[(1, 'left', 7), (2, 'left', 3), (3, 'left', 3)]):
						pm.text(l='mainGrp')
						self.mainGrpTxtFld = pm.textField(w=200, ed=False)
						self.loadMainGrpButt = pm.button(l='<<', c=pm.Callback(self.uiCall, 'loadMainGrp'))
					
					# create tab
					with pm.frameLayout(l='Create Group', bs='etchedIn', mh=5, mw=5, cll=True, cl=False, fn='smallObliqueLabelFont'):
					
						with pm.rowColumnLayout(nc=3, rs=[(1, 5), (2, 5), (3, 5)], co=[(1, 'left', 10), (2, 'left', 3), (3, 'left', 5)]):

							pm.text(l='Mesh')
							self.meshTxtFld = pm.textField(w=200, ed=False)
							self.meshButt = pm.button(l='<<', c=pm.Callback(self.uiCall, 'loadMesh'))

							pm.text(l='Buffer')
							self.bufferMeshTxtFld = pm.textField(w=200, ed=False)
							self.bufferMeshButt = pm.button(l='<<', c=pm.Callback(self.uiCall, 'loadBufferMesh'))

							pm.text(l='Name')
							self.nameTxtFld = pm.textField(w=200, tx='body', ed=True)
							self.createButt = pm.button(l='Create', c=pm.Callback(self.uiCall, 'createMainGrp'))

				with pm.frameLayout(l='Drivers', bs='etchedIn', mh=5, mw=5, cll=True, cl=False, fn='smallObliqueLabelFont'):
					
					with pm.columnLayout(adj=True, rs=5, co=['both', 0]):
						
						self.driverTSL = pm.textScrollList(ams=False, h=150, 
										sc=pm.Callback(self.uiCall, 'setFocusDriver'), 
										dkc=pm.Callback(self.uiCall, 'removeDriver'))
						
					with pm.frameLayout(l='Create Driver', bs='etchedIn', mh=5, mw=5, cll=True, cl=False, fn='smallObliqueLabelFont'):
						with pm.rowColumnLayout(nc=6, co=[(1, 'left', 13), (2, 'left', 3), (3, 'left', 5), 
							(4, 'left', 3), (5, 'left', 10), (6, 'left', 3)]):
							pm.text(l='Elem')
							self.elemTxtFld = pm.textField(tx='limb', w=90, ed=True)

							pm.text(l='Side')
							self.sideTxtFld = pm.textField(tx='', w=45, ed=True)

							pm.text(l='Axis')
							with pm.optionMenu(w=30) as self.axisMenu:
								pm.menuItem(l='+x')
								pm.menuItem(l='+y')
								pm.menuItem(l='+z')
								pm.menuItem(l='-x')
								pm.menuItem(l='-y')
								pm.menuItem(l='-z')
						
						with pm.rowColumnLayout(nc=2, rs=(1, 5), co=[(1, 'left', 0), (2, 'left', 5)]):	
							with pm.rowColumnLayout(nc=3, rs=[(1, 5), (2, 5)], co=[(1, 'left', 3), (2, 'left', 3), (3, 'left', 5)]):
								pm.text(l='joint')
								self.jntTxtFld = pm.textField(w=175, ed=False)
								self.jntButt = pm.button(l='<<', c=pm.Callback(self.uiCall, 'loadJnt'))
								pm.text(l='parent')
								self.parentTxtFld = pm.textField(w=175, ed=False)
								self.parentButt = pm.button(l='<<', c=pm.Callback(self.uiCall, 'loadParent'))

							self.createCPRbutt = pm.button(l='Add', h=25, w=50, c=pm.Callback(self.uiCall, 'createDriver'))

				with pm.frameLayout(l='Targets & Inbetweens', bs='etchedIn', mh=5, mw=5, cll=True, cl=False, fn='smallObliqueLabelFont'):

					with pm.rowColumnLayout(nc=2, rs=(1, 5), co=[(1, 'left', 0), (2, 'left', 3)]):
						with pm.columnLayout(adj=True, rs=3, co=['both', 0]):
							self.targetTSL = pm.textScrollList(ams=False, w=150, h=150, 
										sc=pm.Callback(self.uiCall, 'setFocusTarget'),
										dkc=pm.Callback(self.uiCall, 'removeTarget'))
							
							with pm.rowColumnLayout(nc=2, co=[(1, 'left', 0), (2, 'left', 5)]):
								self.targetNameTxtFld = pm.textField(tx=self._defaultTargetName, w=120, ed=True)
								self.addTargetButt = pm.button(l='Add', w=30, c=pm.Callback(self.uiCall, 'addTarget'))
								
						with pm.columnLayout(adj=True, rs=5, co=['both', 0]):
							self.inbTSL = pm.textScrollList(ams=False, w=150, h=150, 
										sc=pm.Callback(self.uiCall, 'setFocusInb'),
										dkc=pm.Callback(self.uiCall, 'removeInbetween'))

							with pm.rowColumnLayout(nc=2, co=[(1, 'left', 0), (2, 'left', 32)]):

								with pm.columnLayout(adj=True, rs=5, co=['left', 50]) as self.outputFloatFlieldCol:
									self.outputFloatField = pm.floatField(self._defultOutputFloatFieldName, pre=2, w=35, ed=False)
								self.addInbButt = pm.button(l='Add', w=30, c=pm.Callback(self.uiCall, 'addInbetween'))

					with pm.rowColumnLayout(nc=2, co=[(1, 'left', 25), (2, 'left', 45)]):
						self.sculptButt = pm.button(l='Sculpt', h=30, w=110, c=pm.Callback(self.uiCall, 'sculpt'))
						self.applyButt = pm.button(l='Apply', h=30, w=110, c=pm.Callback(self.uiCall, 'apply'))

				with pm.frameLayout(l='Sculpting', bs='etchedIn', mh=5, mw=5, cll=True, cl=False, fn='smallObliqueLabelFont'):

					with pm.rowColumnLayout(nc=4, co=([1, 'left', 5], [2, 'left', 3], [3, 'left', 5], [4, 'left', 5])):
						self.revertFloatFld = pm.floatField(v=100, max=100, min=0, pre=2, w=42, cc=pm.Callback(self.fillRevertMesh))
						self.revertSlider = pm.floatSliderGrp(v=100, max=100, min=0, cw2=[145, 10], f=False, pre=2, el='%',
											dc=pm.Callback(self.dragRevertMesh), cc=pm.Callback(self.endDragRevertMesh))
						pm.button(l='Revert', w=50, h=25, c=pm.Callback(self.revert))
						pm.button(l='Copy', w=40, h=25, c=pm.Callback(self.copy))

					# with pm.rowColumnLayout(nc=2, co=([1, 'left', 25], [2, 'left', 45])):
						# pm.button(l='Flip', w=60, h=25, c=pm.Callback(self.smr.caller, 'flip'))
						



		self.axisMenu.setValue('+y')


				
	def uiCall(self, op):
		# pm.undoInfo(openChunk=True)

		if op == 'loadMainGrp':
			# reninit the main grp
			self.reinit(mainGrp=misc.getSel())

			# reset ui
			self.mainGrpTxtFld.setText('')
			self.driverTSL.removeAll()
			self.targetTSL.removeAll()
			self.inbTSL.removeAll()

			# clear vars
			self.resetFocusDriverVars()
			self.resetFocusTargetVars()
			
			# load the main grp to the field
			self.loadObjToTxtFld(obj=self.mainGrp, txtFld=self.mainGrpTxtFld)

			# update driver
			self.updateDriverUi()

			# re-create output float field
			self.connectOutputFloatField(loc=None)

			# reinit smr
			vtxNum = pm.polyEvaluate(self.mesh.getShape(ni=True), v=True)
			self.smr = smr.SymMeshReflector()
			self.smr.filterBaseGeo = False
			self.smr.baseVtxNum = vtxNum


		elif op == 'loadMesh':
			self.mesh = self.getSelMesh()
			self.meshTxtFld.setText('')

			# load self.mesh to txtFld
			self.loadObjToTxtFld(obj=self.mesh, txtFld=self.meshTxtFld)



		elif op == 'loadJnt':
			self.jnt = misc.getSel(selType='joint')
			self.jntTxtFld.setText('')

			# load self.jnt to txtFld
			self.loadObjToTxtFld(obj=self.jnt, txtFld=self.jntTxtFld)


		elif op == 'loadBufferMesh':
			self.bufferMesh = self.getSelMesh()
			self.bufferMeshTxtFld.setText('')

			# load self.bufferMesh to txtFld
			self.loadObjToTxtFld(obj=self.bufferMesh, txtFld=self.bufferMeshTxtFld)


		elif op == 'loadParent':
			self.parent = misc.getSel()
			self.parentTxtFld.setText('')
			
			# load self.parent to txtFld
			self.loadObjToTxtFld(obj=self.parent, txtFld=self.parentTxtFld)


		elif op == 'createMainGrp':
			if not self.mesh or not self.bufferMesh:
				sys.exit('Please load mesh and buffer mesh to create CRT main grp.')
				return

			# get name from txt field
			self.name = self.nameTxtFld.getText()

			# create the main grp and duplicate orig mesh to be used as reference mesh
			self.createMainGrp()
			self.duplicateOrigMesh()

			pm.select(self.mainGrp)
			self.uiCall('loadMainGrp')


		elif op == 'setFocusDriver':
			tslSel = self.driverTSL.getSelectItem()

			# reset vars
			self.resetFocusDriverVars()
			self.resetFocusTargetVars()

			# if nothing is selected in the driver tsl
			if not tslSel:
				return

			# store selection into vars
			self.focusDriverName = tslSel[0]
			self.focusDriver = self.drivers[self.focusDriverName]

			# reinit to refresh
			result = self.reinitDriver(mainGrp=self.focusDriver.mainGrp)

			if result == True:
				# update targets and inb ui
				self.updateTargetUi()
				self.updateInbUi()
				self.connectOutputFloatField(loc=None)


		elif op == 'createDriver':
			if not self.jnt or not self.parent:
				sys.exit('Please load a joint and its parent to create driver.')
				return
				
			# get elem, side, axis from ui
			elem = self.elemTxtFld.getText()
			side = self.sideTxtFld.getText()
			axis = self.axisMenu.getValue()

			if '%s%s' %(elem, side) in self.drivers.keys():
				sys.exit('Driver with the same name exists. Try something else.')
				return

			# reset vars
			self.resetFocusDriverVars()
			self.resetFocusTargetVars()

			# create driver
			self.createDriver(jnt=self.jnt, parent=self.parent, elem=elem, side=side, axis=axis)

			# reinit to refresh
			self.reinitDriver(mainGrp=self.focusDriver.mainGrp)

			# update ui
			self.updateDriverUi()
			
			# select in TSL
			self.driverTSL.setSelectItem(self.focusDriverName)	

			# refresh ui
			self.uiCall('setFocusDriver')


		elif op == 'removeDriver':
			# if no focus driver (no tsl selection): return
			if not self.focusDriver:
				sys.exit('Please select a driver to remove.')
				return

			# remove all bsh targets in this driver
			for targetName, targetDict in self.targetDict.iteritems():
				invMeshName = 'INV_%s%s_%s_100' %(self.focusDriver.elem, self.focusDriver.side, targetName)
				self.removeBshTarget(invMeshName)

			pm.delete(self.focusDriver.mainGrp)

			# reload main group to reinit and refresh everyting
			pm.select(self.mainGrp, r=True)
			self.uiCall('loadMainGrp')


		elif op == 'setFocusTarget':
			tslSel = self.targetTSL.getSelectItem()

			# reset vars
			self.resetFocusTargetVars()
			
			self.focusTargetName = tslSel[0]

			# connect output attr to ui
			self.updateInbUi()
			self.connectOutputFloatField(loc=self.focusDriver.targetLocs[self.focusTargetName])

			# select target locator
			pm.select(self.focusDriver.targetLocs[self.focusTargetName])


		elif op == 'setFocusInb':
			tslSel = self.inbTSL.getSelectItem()

			if not self.focusTargetName or not tslSel:
				return 
		
			# round the value to 2 decimal places
			value = round(float(tslSel[0]), 2)

			# get the target mesh for this inbetween
			self.focusTargetMesh = self.targetDict[self.focusTargetName][value]

			# set joint rotation
			self.setJntRotation(targetName=self.focusTargetName, inbWeight=value)

			# return the value got from the ui
			return value


		elif op == 'addTarget':
			# return if no focus driver (accidentally press the button)
			if not self.focusDriver:
				return

			# get the name from text field
			targetName = self.targetNameTxtFld.getText()

			# if nothing in the text field or it's the default 'TARGET' : try to add digit to the end
			if not targetName or targetName == self._defaultTargetName:
				i = 1
				targetName = '%s%s' %(self._defaultTargetName, str(i).zfill(2))
				while targetName in self.focusDriver.targetNames:
					i += 1
					targetName = '%s%s' %(self._defaultTargetName, str(i).zfill(2))

			# if user type in the name but the target with the same name already exists
			if targetName in self.focusDriver.targetNames:
				sys.exit('Target with the same name  "%s"  exists. Try something else.' %targetName)
				return

			# reset name var
			self.focusTargetName = ''

			# add cone target
			self.addTarget(driver=self.focusDriver, targetName=targetName, 
				coneAngle=self._defaultConeAngleValue, targetAngle=self._defaultTargetAngleValue)
			
			# turn off all driver evelope
			driverDict, locs = self.turnOffEnvelopes()
			deformerEnvs = self.turnOffDeformerEnvelopes()

			# duplicate self.mesh then apply. (incase its the first time)
			self.duplicateTargetMesh(targetName=self.focusTargetName, inbWeight=1.00)
			self.apply(targetName=self.focusTargetName, inbWeight=1.00)

			# turn envelopes back on
			self.turnOnEnvelopes(driverDict, locs)
			self.turnOnDeformerEnvelopes(deformerEnvs)

			# update ui, select in TSL
			self.updateTargetUi()

			# select target TSL
			self.targetTSL.setSelectItem(self.focusTargetName)
			self.uiCall('setFocusTarget')

			self.inbTSL.setSelectIndexedItem(1)
			self.uiCall('setFocusInb')


		elif op == 'removeTarget':
			if not self.focusDriver or not self.focusTargetName:
				sys.exit('Please select a driver and a target to remove.')
				return

			# delete the whole mesh grp
			self.getTargetMeshGrp(self.focusTargetName)
			pm.delete(self.focusTargetGrp)

			# get the target locator
			loc = self.focusDriver.targetLocs[self.focusTargetName]
			nodes = loc.attr('nodes').outputs()
			
			# disconnect attr first or the nodes will get deleted with the loc
			for i in self.focusDriver.baseDmtx.outputTranslate.outputs(p=True):
				if i.node() in nodes:
					pm.disconnectAttr(self.focusDriver.baseDmtx.outputTranslate, i)

			for i in self.focusDriver.poseVectorPma.output3D.outputs(p=True):
				if i.node() in nodes:
					pm.disconnectAttr(self.focusDriver.poseVectorPma.output3D, i)

			# append the loc grp
			nodes.append(loc.getParent())

			# delete the nodes and the loc grp
			pm.delete(nodes)

			# delete it from the target dict 
			del self.targetDict[self.focusTargetName]

			# reinit the focus driver
			self.reinitDriver(mainGrp=self.focusDriver.mainGrp)	

			# remove bsh target
			self.removeBshTarget('INV_%s%s_%s_100' %(self.focusDriver.elem, self.focusDriver.side, self.focusTargetName))

			# reset all the target vars
			self.resetFocusTargetVars()

			# update ui
			self.updateTargetUi()
			self.inbTSL.removeAll()
			self.connectOutputFloatField(loc=None)


		elif op == 'addInbetween':
			if not self.focusTargetName:
				return

			# get the output value from the loc
			loc = self.focusDriver.targetLocs[self.focusTargetName]
			locOutput = loc.attr('output').get()
			inbWeight = round(locOutput, 2)

			if inbWeight <= 0.00:
				sys.exit('Inbetween weight must be greather than 0.')
				return
			
			if inbWeight in self.targetDict[self.focusTargetName].keys():
				sys.exit('Inbetween for  %s  at  %s  already exists. Try removing it before adding new one.' %(self.focusTargetName, inbWeight))
				return

			# get the attr on the blendshape node
			bshTarget = 'INV_%s%s_%s_100' %(self.focusDriver.elem, self.focusDriver.side, self.focusTargetName)
			bshAttr = self.bsh.attr(bshTarget)

			# discconnect bsh attr, set bsh weight
			rets = self.setBshAttr(bshAttr, locOutput)

			# duplicate the mesh
			self.duplicateTargetMesh(targetName=self.focusTargetName, inbWeight=inbWeight)

			# re connect bsh
			self.resetBshAttr(bshAttr, rets)
			
			# turn the deformer envelopes off
			deformerEnvs = self.turnOffDeformerEnvelopes()
			
			# apply the mesh
			self.apply(targetName=self.focusTargetName, inbWeight=inbWeight)

			# turn deformer envelope back on
			self.turnOnDeformerEnvelopes(deformerEnvs)

			# update ui
			self.updateInbUi()
			self.inbTSL.setSelectItem(inbWeight)
			self.uiCall('setFocusInb')


		elif op == 'removeInbetween':
			inbWeight = self.uiCall('setFocusInb')

			if not self.focusTargetName or not inbWeight:
				sys.exit('Please select target name and target weight.')
				return

			# if user try to remove 1.0 target inb
			if inbWeight == 1.00:
				sys.exit('Cannot remove inbetween at 100%. Use remove target instead.')
				return

			# delete the inb mesh
			try:
				pm.delete(self.focusTargetMesh)
			except: pass
			
			# get the inb values as a list
			inbValues = sorted(self.targetDict[self.focusTargetName].keys())
			fullTargetName = 'INV_%s%s_%s_100' %(self.focusDriver.elem, self.focusDriver.side, self.focusTargetName)

			# remove the inbeween from the bsh tarets
			self.removeBshInb(fullTargetName, inbValues.index(inbWeight))

			# remove from target dict and remove focus target mesh
			del self.targetDict[self.focusTargetName][inbWeight]
			self.focusTargetMesh = None 

			# update the inb ui
			self.updateInbUi()


		elif op == 'sculpt':
			inbWeight = self.uiCall('setFocusInb')

			if not self.focusDriver:
				sys.exit('Please select a driver.')
				return

			if not self.focusTargetName or not inbWeight:
				sys.exit('Please select target name and target weight.')
				return

			driverDict, locs = self.turnOffEnvelopes()

			self.smr.getGeoData(mesh=self.mesh.longName())

			self.turnOnEnvelopes(driverDict, locs)

			# call sculpt
			self.sculpting = True

			# show the target mesh
			self.sculpt(targetName=self.focusTargetName, inbWeight=inbWeight)


		elif op == 'apply':
			inbWeight = self.uiCall('setFocusInb')

			if not self.focusDriver:
				sys.exit('Please select a driver.')
				return

			if not self.focusTargetName or not inbWeight:
				sys.exit('Please select target name and target weight.')
				return

			# turn off envelopes
			driverDict, locs = self.turnOffEnvelopes()
			deformerEnvs = self.turnOffDeformerEnvelopes()

			# apply invert deformation and add to blendshape targets
			self.apply(targetName=self.focusTargetName, inbWeight=inbWeight)

			# turn envelopes back on
			self.turnOnEnvelopes(driverDict, locs)
			self.turnOnDeformerEnvelopes(deformerEnvs)

			# turn off sculpting mode
			self.sculpting = False


		# pm.undoInfo(closeChunk=True)


	def resetFocusDriverVars(self):
		self.focusDriverName = ''
		self.focusDriver = None



	def resetFocusTargetVars(self):
		self.focusTargetGrp = None
		self.focusTargetMesh = None
		self.focusTargetName = ''



	def connectOutputFloatField(self, loc=None):
		if pm.floatField(self._defultOutputFloatFieldName, ex=True):
			pm.deleteUI(self._defultOutputFloatFieldName)
			self.outputFloatField = None

		self.outputFloatField = pm.floatField(self._defultOutputFloatFieldName, pre=2, w=35, ed=False, parent=self.outputFloatFlieldCol)

		if loc:
			pm.connectControl(self.outputFloatField, loc.attr('output'))


	def updateDriverUi(self):
		self.driverTSL.removeAll()
		for i in sorted(self.drivers.keys()):
			self.driverTSL.append(i)



	def updateTargetUi(self):
		self.targetTSL.removeAll()

		for i in sorted(self.focusDriver.targetLocs.keys()):
			self.targetTSL.append(i)



	def updateInbUi(self):
		self.inbTSL.removeAll()

		if not self.focusTargetName in self.targetDict.keys():
			return

		for value in sorted(self.targetDict[self.focusTargetName].keys()):
			self.inbTSL.append(value)



	def getSelMesh(self):
		sel = misc.getSel()
		ret = None
		try:
			shp = sel.getShape(ni=True)
			if isinstance(shp, pm.nt.Mesh):
				ret = sel
		except: pass

		return ret



	def loadObjToTxtFld(self, obj, txtFld):
		if not obj:
			return
		txt = obj.nodeName()
		txtFld.setText(txt)



	def reinit(self, mainGrp=None):
		if not mainGrp:
			mainGrp = misc.getSel()
			if not mainGrp:
				sys.exit('Select a CRT main group to re-initialize.')


		try:
			self.name = mainGrp.attr('name').get()
			self.mainGrp = mainGrp
		except:
			sys.exit('Make sure this is a CRT main group.')

		# get all the meshes
		meshStatus = [False, False, False]
		errMsg = ''
		try:
			self.mesh = self.mainGrp.attr('mesh').inputs()[0]
			meshStatus[0] = True
		except: 
			errMsg += 'No mesh found in CRT main group connection.'

		try:
			self.origMesh = self.mainGrp.attr('origMesh').outputs()[0]
			meshStatus[1] = True
		except: 
			errMsg += 'No orig mesh found in CRT main group connection.'

		try:
			self.bufferMesh = self.mainGrp.attr('bufferMesh').inputs()[0]
			meshStatus[2] = True
		except:
			errMsg += 'No buffer mesh found in CRT main group connection.'

		if meshStatus != [True, True, True]:
			sys.exit(errMsg)

		# get blendshape
		try:
			self.bsh = self.mainGrp.attr('bsh').inputs()[0]
		except:
			pass

		mainGrps = self.mainGrp.drivers.outputs()
		self.drivers = {}

		for mainGrp in mainGrps:
			result = self.reinitDriver(mainGrp=mainGrp)
			if result == False:
				sys.exit('Cannot re-initialize driver : %s. Check connections.' %mainGrp)



	def reinitDriver(self, mainGrp):
		result = False

		# reset target dict
		self.targetDict = {}

		try:
			cprIns = cpr.ConePoseReader()
			cprIns.reinit(mainGrp=mainGrp)

			self.drivers['%s%s' %(cprIns.elem, cprIns.side)] = cprIns
			self.focusDriver = cprIns

			meshGrp = cprIns.meshGrp
			for grp in meshGrp.getChildren(type='transform'):
				targetName = grp.attr('targetName').get()
				self.targetDict[targetName] = {}
				meshes = [m for m in grp.getChildren(type='transform') if isinstance(m.getShape(ni=True), pm.nt.Mesh)]
				meshDict = {}
				for m in meshes:
					inbWeight = m.attr('inbWeight').get()
					meshDict[inbWeight] = m
				self.targetDict[targetName] = meshDict

			result = True

		except: pass

		return result



	def register(self, obj, channel):
		misc.addMsgAttr(self.mainGrp, channel)
		misc.addMsgAttr(obj, 'mainGrp')
		pm.connectAttr(self.mainGrp.attr(channel), obj.attr('mainGrp'), f=True)



	def createMainGrp(self):
		self.mainGrp = pm.group(em=True, n='%sCRT_grp' %self.name)

		misc.addStrAttr(self.mainGrp, 'name', txt=self.name, lock=True)
		misc.addMsgAttr(self.mainGrp, 'mesh')
		misc.addMsgAttr(self.mainGrp, 'bufferMesh')
		misc.addMsgAttr(self.mainGrp, 'origMesh')
		misc.addMsgAttr(self.mainGrp, 'drivers')
		misc.addMsgAttr(self.mainGrp, 'bsh')

		pm.connectAttr(self.mesh.message, self.mainGrp.mesh)
		pm.connectAttr(self.bufferMesh.message, self.mainGrp.bufferMesh)



	def createDriver(self, jnt=None, parent=None, axis='+y', elem='limb', side='', size=1.0):

		cprIns = cpr.ConePoseReader(jnt=jnt, parent=parent, axis=axis, elem=elem, side=side, size=size)
		cprIns.create()

		self.drivers['%s%s' %(elem, side)] = cprIns
		self.register(cprIns.mainGrp, 'drivers')
		pm.parent(cprIns.mainGrp, self.mainGrp)

		# set this cpr to focus
		self.focusDriver = cprIns
		self.focusDriverName = '%s%s' %(elem, side)



	def addTarget(self, driver, targetName, coneAngle, targetAngle):

		# add cone target
		targets = driver.addTarget(name=targetName, coneAngle=coneAngle, targetAngle=targetAngle)

		# get target name from created cone
		targetName = targets['name']

		# store in self var
		self.focusTargetName = targetName
		self.targetDict[targetName] = {1.00:None}

	
	def setBshAttr(self, bshAttr, inbWeight):

		value = bshAttr.get()
		bshLock = bshAttr.isLocked()
		# if bshLock == True:
		bshAttr.setLocked(False)

		bshInputs = bshAttr.inputs(plugs=True)
		if bshInputs:
			bshInputs = bshInputs[0]
			bshAttr.disconnect()

		bshAttr.set(inbWeight)
		retDict = {'value':value, 'input':bshInputs, 'lock':bshLock}
		return retDict


	def resetBshAttr(self, bshAttr, bshAttrDict):
		bshAttr.set(bshAttrDict['value'])
		pm.connectAttr(bshAttrDict['input'], bshAttr)
		bshAttr.setLocked(bshAttrDict['lock'])


	def duplicateTargetMesh(self, targetName, inbWeight):
		elem = self.focusDriver.elem
		side = self.focusDriver.side

		# duplicate current mesh and clean garbage shape
		self.focusTargetMesh = pm.duplicate(self.mesh)[0]
		misc.cleanUnuseOrigShape([self.focusTargetMesh])

		# unlock target mesh translations parent to group
		misc.lockAttr(self.focusTargetMesh, lock=False, t=True, r=True, s=True, v=True)

		# store duplicated mesh into targetDict
		self.targetDict[targetName][inbWeight] = self.focusTargetMesh

		# override wireframe color for target mesh
		targetMeshShp = self.focusTargetMesh.getShape(ni=True)
		targetMeshShp.overrideEnabled.set(True)
		targetMeshShp.overrideColor.set(self.wfEditColorCode)

		# add target name as an attribute for the target mesh
		misc.addNumAttr(self.focusTargetMesh, 'inbWeight', 'double', min=0.0, max=1.0, dv=inbWeight, hide=True, key=False, lock=True)
		rot = list(self.focusDriver.jnt.rotate.get())
		rotCode = '%s_%s_%s' %(rot[0], rot[1], rot[2])
		misc.addStrAttr(self.focusTargetMesh, 'jntRotation', txt=rotCode, lock=True)

		# get target grp
		self.getTargetMeshGrp(targetName=targetName)

		if not self.focusTargetGrp:
			# create target mesh group
			self.focusTargetGrp = pm.group(em=True, n='%s%s_%s_grp' %(elem, side, targetName))
			misc.addStrAttr(self.focusTargetGrp, 'targetName', txt=targetName, lock=True)
			pm.parent(self.focusTargetGrp, self.focusDriver.meshGrp)		
		
		# rename target mesh
		self.focusTargetMesh.rename('%s%s_%s_%s' %(elem, side, targetName, str(int(inbWeight*100))))

		pm.parent(self.focusTargetMesh, self.focusTargetGrp)
		self.focusTargetMesh.visibility.set(False)



	def getFocusTargetMesh(self, targetName, inbWeight):
		self.focusTargetMesh = None
		# loc = self.focusDriver.targetLocs[targetName]
		# currentOutput = loc.attr('output').get()
		try:
			meshDict = self.targetDict[targetName]
			self.focusTargetMesh = meshDict[inbWeight]
		except:
			pass



	def getTargetMeshGrp(self, targetName):
		self.focusTargetGrp = None
		meshGrp = self.focusDriver.meshGrp
		targets = meshGrp.getChildren(type='transform')
		for t in targets:
			try:
				if t.attr('targetName').get() == targetName:
					self.focusTargetGrp = t			
					break
			except: pass

		

	def turnOffEnvelopes(self):
		drivers, locs = {}, {}

		for name, ins in self.drivers.iteritems():
			currentMainEnvValue = ins.mainGrp.outputEnvelope.get()
			if currentMainEnvValue > 0.0:
				ins.mainGrp.outputEnvelope.set(0.0)
				drivers[ins] = currentMainEnvValue

			for loc in ins.targetLocs.values():
				currentInterpValue = loc.attr('interpolation').get()
				if currentInterpValue > 0:
					loc.attr('interpolation').set(0.0)
					locs[loc] = currentInterpValue

		return drivers, locs



	def turnOnEnvelopes(self, drivers, locs):
		for k, v in drivers.iteritems():
			k.mainGrp.outputEnvelope.set(v)

		for loc, value in locs.iteritems():
			loc.attr('interpolation').set(value)



	def sculpt(self, targetName=None, inbWeight=1.00):
		# get sculpting mesh for current target name and inbetween weight
		self.getFocusTargetMesh(targetName, inbWeight)

		# if no shape was duplicated before
		if not self.focusTargetMesh:
			return

		# hide origMesh shape, unhide edit mesh so user can edit the mesh.	
		try: 
			self.focusTargetMesh.visibility.set(True)
			self.mesh.visibility.set(False)
			self.bufferMesh.visibility.set(False)
		except: pass

		# select editMesh. toggle on vertex component mode.
		pm.select(self.focusTargetMesh, r=True)
		# pm.selectMode(component=True)
		# pm.selectType(pv=True)

		# self._sculpting = True
		om.MGlobal.displayInfo('SCULPTING:  %s  at  %s %s.' %(targetName, int(inbWeight*100), '%')),


	def turnOffDeformerEnvelopes(self):
		meshHistories = self.mesh.listHistory(leaf=True, pdo=1, il=2)
		envAttrs = {}

		for deformer in meshHistories:
			if deformer.hasAttr('envelope') and not isinstance(deformer, (pm.nt.SkinCluster, pm.nt.Tweak)):
				defEnv = deformer.attr('envelope')
				value = defEnv.get()
				try: 
					defEnv.set(False)
					envAttrs[defEnv] = value
				except: pass

		return envAttrs


	def turnOnDeformerEnvelopes(self, envAttrs):
		for attr, value in envAttrs.iteritems():
			attr.set(value)



	def apply(self, targetName, inbWeight):
		elem = self.focusDriver.elem
		side = self.focusDriver.side

		# show the mesh
		self.mesh.visibility.set(True)

		# for v in targetKeyValues:
		targetMesh = self.targetDict[targetName][inbWeight]

		# apply invert mesh for origShape
		invertMesh = idef.invert(base=self.mesh.longName(), corrective=targetMesh.longName(), 
					name='INV_%s%s_%s_%s' %(elem, side, targetName, str(int(inbWeight*100))))
		# invertMeshes.append(pm.nt.Transform(invertShape))
		invertMesh = pm.nt.Transform(invertMesh)

		targetMesh.visibility.set(False)
			
		

		# try to get blendshape node
		index = 0
		bshNodes = [b for b in self.mainGrp.attr('bsh').inputs() if isinstance(b, pm.nt.BlendShape) == True]

		# if no registered blendshape node, do blendshape to the original mesh.
		if not bshNodes:

			# check if the mesh already has blendshape applied, if yes, do parallel blendshape
			parallel = False
			if [i for i in pm.listHistory(self.bufferMesh, il=True) if isinstance(i, pm.nt.BlendShape)]:
				parallel = True

			# create new blendshape
			self.bsh = pm.blendShape(invertMesh, self.bufferMesh, n='%sCorrective_bsh' %self.name, foc=not(parallel), par=parallel)[0]

			# connect message to the driver mainGrp
			pm.connectAttr(self.bsh.message, self.mainGrp.attr('bsh'))
		else:
			self.bsh = bshNodes[0]

			# mesh name at 100%
			fullInvShpName = 'INV_%s%s_%s_100' %(elem, side, targetName)
				
			# if the target mesh is NOT already a target in blendshape node
			if not self.bsh.hasAttr(fullInvShpName):

				indexList = self.bsh.weightIndexList()
				if not indexList:
					index = 0
				else:
					# the next avaliable index
					index = [i for i in range(0, max(indexList)+2) if i not in indexList][0]

			# if this target is already a target
			else:
				# get blendshape attribute
				bshAttr = self.bsh.attr(fullInvShpName)

				# index of the attribute in the blendshape node
				index = bshAttr.index()

			mel.eval('blendShape -e -ib -t "%s" %s "%s" %s "%s";' %(self.bufferMesh.longName(), index, invertMesh.longName(), inbWeight, self.bsh.nodeName()))
			if not self.bsh.hasAttr(fullInvShpName): 
				mel.eval('aliasAttr "%s" "%s.w[%s]";' %(fullInvShpName, self.bsh.nodeName(), index))
									
		# delete invert mesh
		pm.delete(invertMesh)

		# connect ctrl attr
		bshAttr = self.bsh.attr('w[%s]' %index)
		targetLoc = self.focusDriver.targetLocs[targetName]
		if not pm.isConnected(targetLoc.attr('output'), bshAttr):
			pm.connectAttr(targetLoc.attr('output'), bshAttr)
		

		pm.selectMode(object=True)
		pm.select(self.mesh, r=True)
		om.MGlobal.displayInfo('APPLIED:  %s  at  %s%s  for  %s.' %(targetName, int(inbWeight*100), '%', self.mesh))		


	def removeBshInb(self, targetName, inbIndex):
		bshAttr = self.bsh.attr(targetName)
		index = bshAttr.index()

		# get array indices (if it has inbetweens)
		inputTargetItemAttr = self.bsh.inputTarget[0].inputTargetGroup[index].inputTargetItem
		arrayIndices = inputTargetItemAttr.getArrayIndices()
	
		# disconnect whatever connected to the blendshape attribute
		bshInput = None
		try:
			bshInput = bshAttr.inputs(p=True)[0]
		except: pass
		bshAttr.disconnect()

		# materialize deleted target (just to fucking delete it...)
		tempShp = pm.polyCube(n='MATERTIALIZE_%s' %targetName, ch=False)[0].getShape(ni=True)
		pm.connectAttr(self.bsh.outputGeometry[0], tempShp.inMesh)
		pm.refresh()
		bshAttr.set(1.0)
		tempShp.inMesh.disconnect()

		# new we got a target mesh to remove from blendshape node
		pm.connectAttr(tempShp.worldMesh[0], inputTargetItemAttr[arrayIndices[inbIndex]].inputGeomTarget, f=True)

		pm.blendShape(self.bsh, e=True, rm=True, t=(self.bufferMesh, index, tempShp, 1.0), tc=False)
		
		# delete temp mesh
		pm.delete(tempShp.getParent())

		if bshInput:
			pm.connectAttr(bshInput, bshAttr)


	def removeBshTarget(self, targetName):
		bshAttr = self.bsh.attr(targetName)
		index = bshAttr.index()

		# get array indices (if it has inbetweens)
		inputTargetItemAttr = self.bsh.inputTarget[0].inputTargetGroup[index].inputTargetItem
		arrayIndices = inputTargetItemAttr.getArrayIndices()

		# disconnect whatever connected to the blendshape attribute
		bshAttr.disconnect()

		# for all target array indices(inbetweens)
		for a in arrayIndices:

			# materialize deleted target (just to fucking delete it...)
			tempShp = pm.polyCube(n='MATERTIALIZE_%s' %targetName, ch=False)[0].getShape(ni=True)
			pm.connectAttr(self.bsh.outputGeometry[0], tempShp.inMesh)
			pm.refresh()
			bshAttr.set(1.0)
			tempShp.inMesh.disconnect()

			# new we got a target mesh to remove from blendshape node
			pm.connectAttr(tempShp.worldMesh[0], inputTargetItemAttr[a].inputGeomTarget, f=True)

			pm.blendShape(self.bsh, e=True, rm=True, t=(self.bufferMesh, index, tempShp, 1.0), tc=False)
			
			# delete temp mesh
			pm.delete(tempShp.getParent())


	def setJntRotation(self, targetName, inbWeight):
		# get sculpting mesh for current target name and inbetween weight
		self.getFocusTargetMesh(targetName, inbWeight)
		# if no shape was duplicated before
		if not self.focusTargetMesh:
			return

		jnt = self.focusDriver.jnt

		rotValuesStr = self.focusTargetMesh.attr('jntRotation').get().split('_')
		rotValues = [float(rotValuesStr[0]), float(rotValuesStr[1]), float(rotValuesStr[2])]

		jnt.rotate.set(rotValues)



	def duplicateOrigMesh(self):
		self.origMesh = pm.duplicate(self.mesh)[0]
		misc.cleanUnuseOrigShape([self.origMesh])
		self.origMesh.rename('ORIG_%s' %self.mesh.nodeName())
		self.register(self.origMesh, 'origMesh')
		pm.parent(self.origMesh, self.mainGrp)

		# self.origMesh.getShape(ni=True).intermediateObject.set(True)
		self.origMesh.getShape(ni=True).visibility.set(False)
		misc.setDisplayType(obj=self.origMesh, disType='reference')

		# pm.select(self.origMesh, r=True)
		self.smr.getGeoData(mesh=self.origMesh.longName())



	def getMeshASelection(self, child=False):
		# get meshA sel
		getMeshAResult = self.smr.getMeshASelection(child=child, check=True)

		check = [True, True, True]
		errMsg = ''
		if getMeshAResult == False:
			errMsg += 'Select a mesh or vertices.'
			check[0] = False

		if self.mesh.getShape(ni=True).longName() in self.smr.focusVtx.keys():
			errMsg += 'Cannot modify the base mesh! Check you selection.'
			check[1] = False

		if not self.focusTargetMesh or self.sculpting == False:
			errMsg += 'Select a inbetween weight and hit  "Sculpt"  button.'
			self.endDragRevertMesh()
			check[2] = False

		if check == [True, True, True]:
			self.smr.getAGeoData(self.smr.meshA)
			self.smr.getMovedVtxMeshA()
		else:
			sys.exit(errMsg)


	def dragRevertMesh(self):
		# if this is the start of draging
		if self.revertSliderDragging == False:
			# get user selection - mesh or vertices			
			self.getMeshASelection(child=False)
			self.revertSliderDragging = True
			pm.undoInfo(openChunk=True)
				
		# get value from float slider %
		percent = self.revertSlider.getValue()

		#set the float field
		pm.floatField(self.revertFloatFld, e=True, value=percent)

		# call the smr set vtx
		self.smr.revertVtxByPercent(percent=percent)



	def fillRevertMesh(self):
		self.getMeshASelection(child=False)

		# get value from float field
		percent = pm.floatField(self.revertFloatFld, q=True, value=True)

		#set the float slider
		self.revertSlider.setValue(percent)

		# revert vtx
		self.smr.revertVtxByPercent(percent=percent)

		# call endDragRevertMesh to reset uis
		self.endDragRevertMesh()



	def endDragRevertMesh(self):
		if self.revertSliderDragging == True:
			pm.undoInfo(closeChunk=True)
			
		#set the float field and float slider back to 100
		self.revertSlider.setValue(100)
		self.revertFloatFld.setValue(100)

		# reset vars
		self.revertSliderDragging = False

		
	def revert(self):
		self.getMeshASelection(child=False)
		self.smr.revertVtxByPercent(percent=0.0)


	def copy(self):
		self.getMeshASelection(child=True)
		self.smr.copyFromMeshA()
		