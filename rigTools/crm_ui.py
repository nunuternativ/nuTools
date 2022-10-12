import pymel.core as pm
import maya.OpenMaya as om
import maya.mel as mel
import sys

from nuTools import misc
reload(misc)

from nuTools.rigTools import baseRig
from nuTools.rigTools import skirtPosRig as skpr
from nuTools.rigTools import skirtPosNonRollRig as skpnrr
from nuTools.rigTools import follicleJntRig as fjr
from nuTools.rigTools import dtlRig as dtlr
from nuTools.rigTools import dtlRig2 as dtlr2
from nuTools.rigTools import consCrtJntRig as ccjr
from nuTools.rigTools import splineTentacleRig as sptr
from nuTools.rigTools import backSplineIkRig as bsir

reload(baseRig)
reload(skpr)
reload(skpnrr)
reload(fjr)
reload(dtlr)
reload(dtlr2)
reload(ccjr)
reload(sptr)
reload(bsir)

class BaseUi(object):
	"""
	The base class for rigging classes within nuTools.rigTools. 

	""" 

	def __init__(self, parent):
		self.uiparent = parent
		self.rigCol = None
		self._REQUIRE = {}

		#rig objs
		self.rigObj = None
		self.rigParent = None 
		self.animGrp = None
		self.utilGrp = None
		self.ikhGrp = None
		self.skinGrp = None
		self.stillGrp = None

		self.defultElem = 'elem'

	
	def create(self):
		with pm.columnLayout(adj=True, parent=self.uiparent, rs=2) as self.masterCol:
			with pm.rowColumnLayout(nc=2, co=[(1, 'left', 77), (2, 'left', 5)]) as self.rigScaleRowCol:
				pm.text(l='Rig Scale: ')
				self.rigSizeFloatSliderGrp = pm.floatSliderGrp(f=True, v=1, max=5, min=0.01, fs=0.01, cw=([1,36], [2,110]), pre=3)
			with pm.rowColumnLayout(nc=4, co=[(1, 'left', 105), (2, 'left', 5), (3, 'left', 12), (4, 'left', 5)]) as self.elemSideRowCol:
				pm.text(l='elem')
				self.elemTxtFld = pm.textField(w=65, ed=True)
				pm.text(l='side')
				self.sideTxtFld = pm.textField(w=40, ed=True)

			with pm.rowColumnLayout(nc=3, co=[(1, 'left', 95), (2, 'left', 5), (3, 'left', 5)]) as self.parentRowCol:
				pm.text(l='parent')
				self.rigParentTxtFld = pm.textField(w=142, ed=False, en=True)
				self.loadParentButt = pm.button(l='<<', c=pm.Callback(self.loadRigParent), en=True)

			with pm.columnLayout(adj=True) as self.mainCol:
				#waiting for extensions from different rig modules
				pass

			with pm.frameLayout(label='Rig Groups', borderStyle='out', mh=5, mw=5, cll=True, cl=True, w=375) as self.rigGrpFrameLayout:
				with pm.rowColumnLayout(nc=3, co=[(1, 'left', 80), (2, 'left', 5), (3, 'left', 5)]):
					pm.text(l='animGrp')
					self.animGrpTxtFld = pm.textField(ed=False)
					self.loadAnimGrpButt = pm.button(l='<<', c=pm.Callback(self.loadAnimGrp))
					pm.text(l='utilGrp')
					self.jntGrpTxtFld = pm.textField(ed=False)
					self.loadJntGrpButt = pm.button(l='<<', c=pm.Callback(self.loadJntGrp))
					pm.text(l='ikhGrp')
					self.ikhGrpTxtFld = pm.textField(ed=False)
					self.loadIkhGrpButt = pm.button(l='<<', c=pm.Callback(self.loadIkhGrp))
					pm.text(l='skinGrp')
					self.skinGrpTxtFld = pm.textField(ed=False)
					self.loadSkinGrpButt = pm.button(l='<<', c=pm.Callback(self.loadSkinGrp))
					pm.text(l='stillGrp')
					self.stillGrpTxtFld = pm.textField(ed=False)
					self.loadStillGrpButt = pm.button(l='<<', c=pm.Callback(self.loadStillGrp))


	def checkRequires(self):
		missingObjs = []

		for varName, obj in self._REQUIRE.iteritems():
			if not obj:
				missingObjs.append(varName)

		if missingObjs:
			om.MGlobal.displayError('%s  are missing!' %missingObjs),
			return False
		return True
		

	def clearUi(self):
		pm.deleteUI(self.mainCol)

	def getSide(self):
		txt = self.sideTxtFld.getText()
		if not txt: txt = ''
		return txt

	def getElem(self):
		txt = self.elemTxtFld.getText()
		if not txt: txt = self.defultElem
		return txt

	def getSize(self):
		return self.rigSizeFloatSliderGrp.getValue()

	def loadRigParent(self, sel=None):
		if not sel:
			sel = misc.getSel()
		if not sel:
			self.rigParent = None
			self.rigParentTxtFld.setText('')
			return
		self.rigParent = sel
		self.rigParentTxtFld.setText(sel.nodeName())

	def loadAnimGrp(self, sel=None):
		if not sel:
			sel = misc.getSel()
		if not sel:
			self.animGrp = None
			self.animGrpTxtFld.setText('')
			return
		self.animGrp = sel
		self.animGrpTxtFld.setText(self.animGrp.nodeName())
	
	def loadJntGrp(self, sel=None):
		if not sel:
			sel = misc.getSel()
		if not sel:
			self.utilGrp = None
			self.jntGrpTxtFld.setText('')
			return
		self.utilGrp = sel
		self.jntGrpTxtFld.setText(sel.nodeName())

	def loadIkhGrp(self, sel=None):
		if not sel:
			sel = misc.getSel()
		if not sel:
			self.ikhGrp = None
			self.ikhGrpTxtFld.setText('')
			return
		self.ikhGrp = sel
		self.ikhGrpTxtFld.setText(sel.nodeName())

	def loadSkinGrp(self, sel=None):
		if not sel:
			sel = misc.getSel()
		if not sel:
			self.skinGrp = None
			self.skinGrpTxtFld.setText('')
			return
		self.skinGrp = sel
		self.skinGrpTxtFld.setText(sel.nodeName())

	def loadStillGrp(self, sel=None):
		if not sel:
			sel = misc.getSel()
		if not sel:
			self.stillGrp = None
			self.stillGrpTxtFld.setText('')
			return
		self.stillGrp = sel
		self.stillGrpTxtFld.setText(sel.nodeName())

	def loadObjsToTxtFld(self, objs, txtFld):
		objNames = []
		if not objs:
			txtFld.setText('')
			return
		for obj in objs:
			objNames.append(obj.nodeName())
		txtFld.setText(str(objNames))

	def loadObjToTxtFld(self, obj, txtFld):
		txtFld.setText(obj.nodeName())

	def clearElemSideTxtFld(self):
		self.elemTxtFld.setText('')
		self.sideTxtFld.setText('')



class skirtPosRig(BaseUi):


	_DESCRIPTION = """SKIRT POINT ON SURFACE RIG
	Skirt Rig. Ideal for cylindrical mesh that wraps over 2 seperate limbs. 

	METHOD: FK, Point On Surface
	PARENT: hip(hip_jnt)
	REQUIRES: Temp_root(skirtPosRigTemp_root)
	"""

	def __init__(self, baseUi, parent):
		BaseUi.__init__(self, parent)
		self.uiparent = parent
		self.baseUi = baseUi
		self.rigTempRoot = None
		self.baseUi.defultElem = 'skirt'

		#ui
		try:
			pm.deleteUI(self.rigCol)
		except: pass

		with pm.columnLayout(adj=True, rs=5, parent=self.uiparent) as self.rigCol:

			pm.separator()
			with pm.rowColumnLayout(nc=3, co=[(1, 'left', 5), (2, 'left', 5), (3, 'left', 5)]):
				pm.text(l='Rig Template Root')
				self.rigTempTxtFld = pm.textField(w=230, ed=False)
				self.loadRigTempRootButt = pm.button(l='<<', c=pm.Callback(self.loadRigTempRoot))

			with pm.columnLayout(adj=True, rs=3, co=['both', 20]):
				self.uCountIntSliderGrp = pm.intSliderGrp(label="uCount", min=1, max=20, v=3, field=True, cw3=[40, 20, 10])
				self.vCountIntSliderGrp = pm.intSliderGrp(label="vCount", min=2, max=20, v=8, field=True, cw3=[40, 20, 20],
										  cc=pm.Callback(self.filterEvenValue))							  
				self.offsetFloatSliderGrp = pm.floatSliderGrp(label="offset", min=0, max=0.5, v=0, field=True, cw3=[40, 35, 10], pre=2)

		self.baseUi.clearElemSideTxtFld()



	def filterEvenValue(self):
		currVal = self.vCountIntSliderGrp.getValue()
		if currVal %2 != 0:
			self.vCountIntSliderGrp.setValue(currVal+1)



	def loadRigTempRoot(self):
		sels = misc.getSel()
		if not sels:
			self.rigTempRoot = None
			self.rigTempTxtFld.setText('')
			return

		warn = False
		try: 
			if sels._TYPE.get() != 'rigTempRoot':
				warn = True
		except: warn = True

		if warn == True:
			om.MGlobal.displayWarning('Make sure it is a rig template root ctrl.')

		self.rigTempRoot = sels
		self.loadObjToTxtFld(self.rigTempRoot, self.rigTempTxtFld)


	def getBaseVars(self):
		if not self.rigObj:
			return

		self.rigObj.elem = self.baseUi.getElem()
		self.rigObj.side = self.baseUi.getSide()
		self.rigObj.size = self.baseUi.getSize()



	def call(self):
		self._REQUIRE = {'Rig Temp Root':self.rigTempRoot}
		if not self.checkRequires():
			return

		self.rigObj = skpr.SkirtPosRig(	tempRoot=self.rigTempRoot,
										parent=self.baseUi.rigParent, 
										animGrp=self.baseUi.animGrp, 
										utilGrp=self.baseUi.utilGrp, 
										skinGrp= self.baseUi.skinGrp, 
										stillGrp=self.baseUi.stillGrp, 
										uCount=self.uCountIntSliderGrp.getValue(), 
										vCount=self.vCountIntSliderGrp.getValue(),
										offset=self.offsetFloatSliderGrp.getValue())

		# get elem, side, size
		self.getBaseVars()

		# rig
		self.rigObj.rig()



class skirtPosNonRollRig(BaseUi):


	_DESCRIPTION = """SKIRT POINT ON SURFACE NON-ROLL RIG
	Skirt Rig. Ideal for cylindrical mesh that wraps over 2 seperate limbs. 
	With extra non-roll ik, the skirt will not twist with the leg.
	
	METHOD: FK, Point On Surface, Ik(non-roll)
	PARENT: hip(hip_jnt)
	REQUIRES: Temp_root(skirtPosRigTemp_root)
	"""

	def __init__(self, baseUi, parent):
		BaseUi.__init__(self, parent)
		self.uiparent = parent
		self.baseUi = baseUi
		self.rigTempRoot = None
		self.baseUi.defultElem = 'skirt'

		#ui
		try:
			pm.deleteUI(self.rigCol)
		except: pass

		with pm.columnLayout(adj=True, rs=5, parent=self.uiparent) as self.rigCol:

			pm.separator()
			with pm.rowColumnLayout(nc=3, co=[(1, 'left', 5), (2, 'left', 5), (3, 'left', 5)]):
				pm.text(l='Rig Template Root')
				self.rigTempTxtFld = pm.textField(w=230, ed=False)
				self.loadRigTempRootButt = pm.button(l='<<', c=pm.Callback(self.loadRigTempRoot))

			with pm.columnLayout(adj=True, rs=3, co=['both', 20]):
				self.uCountIntSliderGrp = pm.intSliderGrp(label="uCount", min=1, max=20, v=3, field=True, cw3=[40, 20, 10])
				self.vCountIntSliderGrp = pm.intSliderGrp(label="vCount", min=2, max=20, v=8, field=True, cw3=[40, 20, 20],
										  cc=pm.Callback(self.filterEvenValue))							  
				self.offsetFloatSliderGrp = pm.floatSliderGrp(label="offset", min=0, max=0.5, v=0, field=True, cw3=[40, 35, 10], pre=2)

		self.baseUi.clearElemSideTxtFld()



	def filterEvenValue(self):
		currVal = self.vCountIntSliderGrp.getValue()
		if currVal %2 != 0:
			self.vCountIntSliderGrp.setValue(currVal+1)



	def loadRigTempRoot(self):
		sels = misc.getSel()
		if not sels:
			self.rigTempRoot = None
			self.rigTempTxtFld.setText('')
			return

		warn = False
		try: 
			if sels._TYPE.get() != 'rigTempRoot':
				warn = True
		except: warn = True

		if warn == True:
			om.MGlobal.displayWarning('Make sure it is a rig template root ctrl.')

		self.rigTempRoot = sels
		self.loadObjToTxtFld(self.rigTempRoot, self.rigTempTxtFld)


	def getBaseVars(self):
		if not self.rigObj:
			return

		self.rigObj.elem = self.baseUi.getElem()
		self.rigObj.side = self.baseUi.getSide()
		self.rigObj.size = self.baseUi.getSize()



	def call(self):
		self._REQUIRE = {'Rig Temp Root':self.rigTempRoot}
		if not self.checkRequires():
			return

		self.rigObj = skpnrr.SkirtPosNonRollRig(	tempRoot=self.rigTempRoot,
										parent=self.baseUi.rigParent, 
										animGrp=self.baseUi.animGrp, 
										utilGrp=self.baseUi.utilGrp, 
										skinGrp= self.baseUi.skinGrp, 
										stillGrp=self.baseUi.stillGrp, 
										uCount=self.uCountIntSliderGrp.getValue(), 
										vCount=self.vCountIntSliderGrp.getValue(),
										offset=self.offsetFloatSliderGrp.getValue())

		# get elem, side, size
		self.getBaseVars()

		# rig
		self.rigObj.rig()


class follicleJntRig(BaseUi):


	_DESCRIPTION = """FOLLICLE JOINT RIG
	Attatch joints on the created NURBS surface lofted from input curves.  

	METHOD: Constraint, Point On Surface
	PARENT: None
	REQUIRES: 2 or more NURBS curves. 
	"""

	def __init__(self, baseUi, parent):
		BaseUi.__init__(self, parent)
		self.uiparent = parent
		self.baseUi = baseUi

		self.loftCrvs = []
		self.baseUi.defultElem = 'posMesh'

		#ui
		try:
			pm.deleteUI(self.rigCol)
		except: pass

		with pm.columnLayout(adj=True, rs=5, parent=self.uiparent) as self.rigCol:

			pm.separator()
			with pm.rowColumnLayout(nc=3, co=[(1, 'left', 20), (2, 'left', 5), (3, 'left', 5)]):
				pm.text(l='Loft Curves')
				self.loftCrvsTxtFld = pm.textField(w=230, ed=False)
				self.loadLoftCrvsButt = pm.button(l='<<', c=pm.Callback(self.loadLoftCrvs))

			with pm.columnLayout(adj=True, rs=3, co=['both', 20]):
				self.uCountIntSliderGrp = pm.intSliderGrp(label="uCount", min=1, max=50, v=1, field=True, cw3=[40, 20, 10])
				self.vCountIntSliderGrp = pm.intSliderGrp(label="vCount", min=1, max=50, v=8, field=True, cw3=[40, 20, 20])							  
				self.offsetFloatSliderGrp = pm.floatSliderGrp(label="offset", min=0, max=0.5, v=0, field=True, cw3=[40, 35, 10], pre=2)

			with pm.rowColumnLayout(nc=2, co=[(1, 'left', 100), (2, 'left', 40)]):
				self.createCtrlChkBox = pm.checkBox(l='create ctrl', v=False)
				self.keepLoftHistoryChkBox = pm.checkBox(l='keep loft history', v=True)

		self.baseUi.clearElemSideTxtFld()
		self.baseUi.rigParentTxtFld.setEnable(False)
		self.baseUi.loadParentButt.setEnable(False)


	def loadLoftCrvs(self):
		sels = misc.getSel(num='inf')
		if not sels:
			self.loftCrvs = []
			self.loftCrvsTxtFld.setText('')
			return

		warn = False

		try:
			for sel in sels:
				if isinstance(sel.getShape(), pm.nt.NurbsCurve) == False:
					warn = True
		except:
			warn = True

		if warn == True:
			om.MGlobal.displayWarning('Please load least 2 NURBS curves.')

		self.loftCrvs = sels
		self.loadObjsToTxtFld(self.loftCrvs, self.loftCrvsTxtFld)



	def getBaseVars(self):
		if not self.rigObj:
			return

		self.rigObj.elem = self.baseUi.getElem()
		self.rigObj.side = self.baseUi.getSide()
		self.rigObj.size = self.baseUi.getSize()



	def call(self):
		self._REQUIRE = {'Loft Curves':self.loftCrvs}
		if not self.checkRequires():
			return

		self.rigObj = fjr.FollicleJntRig(	loftCurves=self.loftCrvs, 
											createCtrl=self.createCtrlChkBox.getValue(),
											keepHistory=self.keepLoftHistoryChkBox.getValue(),
											uCount=self.uCountIntSliderGrp.getValue(), 
											vCount=self.vCountIntSliderGrp.getValue(),
											offset=self.offsetFloatSliderGrp.getValue(), 
											animGrp=self.baseUi.animGrp, 
											utilGrp=self.baseUi.utilGrp, 
											skinGrp= self.baseUi.skinGrp, 
											stillGrp=self.baseUi.stillGrp)

		# get elem, side, size
		self.getBaseVars()

		# rig
		self.rigObj.rig()



class dtlRig(BaseUi):

	_DESCRIPTION = """DETAIL RIG
	Create a sticky control which follows the mesh and also control the mesh. 

	METHOD: Constraint, Point on curve. 
	PARENT: joint(head_jnt)
	REQUIRES:
	Rivet Mesh : Mesh deforms the same as main mesh.\nSkin Mesh : Mesh that will be skinned to Dtl joints.\nTemp Locator(s) 
	"""

	def __init__(self, baseUi, parent):
		BaseUi.__init__(self, parent)
		self.uiparent = parent
		self.baseUi = baseUi

		self.tempLocs = []
		self.baseUi.defultElem = 'face'
		self.counter = 1


		#ui
		try:
			pm.deleteUI(self.rigCol)
		except: pass

		with pm.columnLayout(adj=True, rs=5, parent=self.uiparent) as self.rigCol:
			pm.separator()
			with pm.columnLayout(adj=True, rs=5, co=['both', 5]):
				with pm.rowColumnLayout(nc=3, rs=(1, 5), co=[(1, 'left', 25), (2, 'left', 3), (3, 'left', 3)]):
					self.skinMeshTxt = pm.text(l='Skin Mesh: ')
					self.skinMeshTxtFld = pm.textField(w=220, ed=False)
					self.skinMeshButt = pm.button(l='<<', c=pm.Callback(self.loadSkinMesh))

					self.rivetMeshTxt = pm.text(l='Rivet Mesh: ')
					self.rivetMeshTxtFld = pm.textField(w=220, ed=False)
					self.rivetMeshButt = pm.button(l='<<', c=pm.Callback(self.loadRivetMesh))

					self.tempLocTxt = pm.text(l='Temp Locs: ')
					self.tempLocTxtFld = pm.textField(w=220, ed=False)
					self.loadTempLocButt = pm.button(l='<<', c=pm.Callback(self.loadTempLoc))
			with pm.columnLayout(adj=True, rs=5, co=['both', 25]):
				self.createLocButt = pm.button(l='Create Temp Loc', h=25, c=pm.Callback(self.createLoc))

			with pm.rowColumnLayout(nc=2, rs=[(1,3), (2,3)], co=[(1, 'left', 110), (2, 'left', 5)]):
				pm.text(l='ctrl color')
				with pm.optionMenu(w=30) as self.ctrlColorMenu:
					pm.menuItem(l='red')
					pm.menuItem(l='yellow')
					pm.menuItem(l='darkBlue')
					pm.menuItem(l='blue')
					pm.menuItem(l='lightBlue')
					pm.menuItem(l='green')
					pm.menuItem(l='darkGreen')
					pm.menuItem(l='navyBlue')
					pm.menuItem(l='darkRed')
					pm.menuItem(l='lightBrown')
					pm.menuItem(l='brown')
					pm.menuItem(l='pink')

				pm.text(l='ctrl shape')
				with pm.optionMenu(w=60) as self.ctrlShapeMenu:
					pm.menuItem(l='cube')
					pm.menuItem(l='locator')

		self.baseUi.clearElemSideTxtFld()



	def getBaseVars(self):
		if not self.rigObj:
			return

		self.rigObj.elem = self.baseUi.getElem()
		self.rigObj.side = self.baseUi.getSide()
		self.rigObj.size = self.baseUi.getSize()

	def getSelMesh(self):
		sel = misc.getSel()
		if not sel:
			return None

		warn = False		
		try:
			shp = sel.getShape()
		except:
			shp = None

		if not shp or isinstance(shp, pm.nt.Mesh) == False:
			warn = True

		if warn == True:
			om.MGlobal.displayWarning('Select a polygon to load.')

		return shp

	def loadRivetMesh(self):
		self.rivetMesh = self.getSelMesh()
		if not self.rivetMesh:
			self.rivetMeshTxtFld.setText('')
			return

		self.rivetMeshTxtFld.setText(self.rivetMesh.nodeName())

		# let user select vertex to create temp locs
		self.hiliteRivetMesh()
		self.counter = 1

	def loadSkinMesh(self):
		self.skinMesh = self.getSelMesh()
		if not self.skinMesh:
			self.skinMeshTxtFld.setText('')
			return
		self.skinMeshTxtFld.setText(self.skinMesh.nodeName())


	def hiliteRivetMesh(self):
		if not self.rivetMesh:
			return
		pm.selectMode(component=True)
		pm.hilite(self.rivetMesh, r=True)

	def createLoc(self, multiple=True):
		sel = misc.getSel(selType='any', num=1)
		if not sel or isinstance(sel, pm.MeshVertex) == False:
			om.MGlobal.displayWarning('Select a vertex where you want to place temp locator on the rivetMesh.')
			self.hiliteRivetMesh()
			return

		# basic vars
		elem = self.baseUi.getElem()
		side = self.baseUi.getSide()
		size = self.baseUi.getSize()

		# create and name locs
		tempLocPos = sel.getPosition('world')
		strCounter = str(self.counter).zfill(2)
		tempLoc = pm.spaceLocator(n='TEMP_%sDtl%s%s_loc' %(elem, strCounter, side))
		tempLocShp = tempLoc.getShape()
		
		tempLocShp.localScale.set([size, size, size])
		pm.xform(tempLoc, ws=True, t=tempLocPos)

		self.tempLocs.append(tempLoc)
		self.loadObjsToTxtFld(self.tempLocs, self.tempLocTxtFld)

		self.counter += 1
		self.hiliteRivetMesh()

	def loadTempLoc(self):
		sels = misc.getSel(num='inf')
		if not sels:
			self.tempLocTxtFld.setText('')
			self.tempLocs = []
			return

		self.tempLocs = sels 
		self.loadObjsToTxtFld(self.tempLocs, self.tempLocTxtFld)


	def call(self):
		reload(dtlr)
		self._REQUIRE = {'Temp Locs' : self.tempLocs,
						 'Rivet Mesh': self.rivetMesh,
						 'Skin Mesh' : self.skinMesh }
		if not self.checkRequires():
			return

		self.rigObj = dtlr.DtlRig (	parent=self.baseUi.rigParent,
									rivetMesh=self.rivetMesh,
									skinMesh=self.skinMesh,
									tempLocs=self.tempLocs,
									ctrlColor=self.ctrlColorMenu.getValue(),
									ctrlShape=self.ctrlShapeMenu.getValue(),
									animGrp=self.baseUi.animGrp, 
									utilGrp=self.baseUi.utilGrp, 
									skinGrp= self.baseUi.skinGrp, 
									stillGrp=self.baseUi.stillGrp)

		# get elem, side, size
		self.getBaseVars()

		# rig
		self.rigObj.rig()

		#reset counter
		self.counter = 1

class dtlRig2(BaseUi):

	_DESCRIPTION = """DETAIL RIG 2
	Create a sticky control which follows the mesh and also control the mesh. 

	METHOD: Constraint, Point on curve. 
	PARENT: joint(head_jnt)
	REQUIRES:
	Surface : A Nurbs surface lofted from polygon edge loops.
	Skin Mesh : Mesh to be skinned to detail joints.
	Wrap Mesh : Mesh that already be skinned.
	"""

	def __init__(self, baseUi, parent):
		BaseUi.__init__(self, parent)
		self.uiparent = parent
		self.baseUi = baseUi

		self.baseUi.defultElem = 'lip'
		self.surf = None


		#ui
		try:
			pm.deleteUI(self.rigCol)
		except: pass

		with pm.columnLayout(adj=True, rs=5, parent=self.uiparent) as self.rigCol:
			pm.separator()
			with pm.columnLayout(adj=True, rs=5, co=['both', 5]):
				with pm.rowColumnLayout(nc=3, rs=(1, 5), co=[(1, 'left', 25), (2, 'left', 3), (3, 'left', 3)]):
					self.surfaceTxt = pm.text(l='Surface: ')
					self.surfaceTxtFld = pm.textField(w=220, ed=False)
					self.surfaceButt = pm.button(l='<<', c=pm.Callback(self.loadSurface))

					self.skinMeshTxt = pm.text(l='Skin Mesh: ')
					self.skinMeshTxtFld = pm.textField(w=220, ed=False)
					self.skinMeshButt = pm.button(l='<<', c=pm.Callback(self.loadSkinMesh))

					self.wrapMeshTxt = pm.text(l='Wrap Mesh: ')
					self.wrapMeshTxtFld = pm.textField(w=220, ed=False)
					self.wrapMeshButt = pm.button(l='<<', c=pm.Callback(self.loadWrapMesh))

				with pm.columnLayout(adj=False, rs=3, co=['left', 30]):
					self.numJntIntSliderGrp = pm.intSliderGrp(label="numJnt", min=1, max=50, v=18, field=True, cw3=[50, 20, 230])

				with pm.columnLayout(adj=False, rs=3, co=['left', 30]):
					self.paramVOffsetFloatSliderGrp = pm.floatSliderGrp(label="paramVOffset", min=0.001, pre=5, max=100, v=2.0, field=True, cw3=[50, 50, 200])

				with pm.columnLayout(adj=False, rs=3, co=['left', 30]):
					self.paramUIntSliderGrp = pm.floatSliderGrp(label="paramU", min=0.01, pre=2, max=10, v=0.15, field=True, cw3=[50, 30, 220])

			with pm.rowColumnLayout(nc=2, rs=[(1,3), (2,3)], co=[(1, 'left', 110), (2, 'left', 5)]):
				pm.text(l='ctrl color')
				with pm.optionMenu(w=30) as self.ctrlColorMenu:
					pm.menuItem(l='lightBlue')
					pm.menuItem(l='lightBrown')
					pm.menuItem(l='red')
					pm.menuItem(l='yellow')
					pm.menuItem(l='darkBlue')
					pm.menuItem(l='blue')
					pm.menuItem(l='green')
					pm.menuItem(l='darkGreen')
					pm.menuItem(l='navyBlue')
					pm.menuItem(l='darkRed')
					pm.menuItem(l='brown')
					pm.menuItem(l='pink')

				pm.text(l='ctrl shape')
				with pm.optionMenu(w=60) as self.ctrlShapeMenu:
					pm.menuItem(l='sphere')
					pm.menuItem(l='cube')
					pm.menuItem(l='locator')

		self.baseUi.clearElemSideTxtFld()


	def getBaseVars(self):
		if not self.rigObj:
			return

		self.rigObj.elem = self.baseUi.getElem()
		self.rigObj.side = self.baseUi.getSide()
		self.rigObj.size = self.baseUi.getSize()


	def getSelNurbs(self):
		sel = misc.getSel()
		if not sel:
			return None

		warn = False		
		try:
			shp = sel.getShape()
		except:
			shp = None

		if not shp or isinstance(shp, pm.nt.NurbsSurface) == False:
			warn = True

		if warn == True:
			om.MGlobal.displayWarning('Select a nurbs surface to load.')

		return sel

	def getSelMesh(self):
		sel = misc.getSel()
		if not sel:
			return None

		warn = False		
		try:
			shp = sel.getShape()
		except:
			shp = None

		if not shp or isinstance(shp, pm.nt.Mesh) == False:
			warn = True

		if warn == True:
			om.MGlobal.displayWarning('Select a polygon to load.')

		return sel

	def loadSurface(self):
		self.surf = self.getSelNurbs()
		if not self.surf:
			self.surfaceTxtFld.setText('')
			return
		self.surfaceTxtFld.setText(self.surf.nodeName())

	def loadSkinMesh(self):
		self.skinMesh = self.getSelMesh()
		if not self.skinMesh:
			self.skinMeshTxtFld.setText('')
			return
		self.skinMeshTxtFld.setText(self.skinMesh.nodeName())

	def loadWrapMesh(self):
		self.wrapMesh = self.getSelMesh()
		if not self.wrapMesh:
			self.wrapMeshTxtFld.setText('')
			return
		self.wrapMeshTxtFld.setText(self.wrapMesh.nodeName())

	def call(self):
		reload(dtlr2)
		self._REQUIRE = {'Parent' : self.baseUi.rigParent,
						'Wrap Mesh' : self.wrapMesh, 
						'Skin Mesh' : self.skinMesh,
						'Surface' : self.surf}
		if not self.checkRequires():
			return

		self.rigObj = dtlr2.DtlRig2 (parent=self.baseUi.rigParent,
									surf=self.surf,
									wrapMesh=self.wrapMesh,
									skinMesh=self.skinMesh,
									num=self.numJntIntSliderGrp.getValue(),
									paramVOffset=self.paramVOffsetFloatSliderGrp.getValue(),
									paramU=self.paramUIntSliderGrp.getValue(),
									ctrlColor=self.ctrlColorMenu.getValue(),
									ctrlShape=self.ctrlShapeMenu.getValue(),
									animGrp=self.baseUi.animGrp, 
									utilGrp=self.baseUi.utilGrp, 
									skinGrp= self.baseUi.skinGrp, 
									stillGrp=self.baseUi.stillGrp)

		# get elem, side, size
		self.getBaseVars()

		# rig
		self.rigObj.rig()


class consCrtJntRig(BaseUi):

	_DESCRIPTION = """CONSTRAINT CORRECTIVE JOINT RIG
	Create an extra joint that helps preserve volumn for bending area.
	Ideal for knee/elbow or any single direction bending limb.

	METHOD: Constraint, Node connections 
	PARENT: joint(The joint above the bending joint)
	REQUIRES:
	2 joints(Parent Joint, Bend joint)
	"""

	def __init__(self, baseUi, parent):
		BaseUi.__init__(self, parent)
		self.uiparent = parent
		self.baseUi = baseUi

		self.baseUi.defultElem = 'limb'
		self.bendJnt = None


		#ui
		try:
			pm.deleteUI(self.rigCol)
		except: pass

		with pm.columnLayout(adj=True, rs=5, parent=self.uiparent) as self.rigCol:
			pm.separator()
			with pm.columnLayout(adj=True, rs=5, co=['both', 5]):
				with pm.rowColumnLayout(nc=3, rs=(1, 5), co=[(1, 'left', 25), (2, 'left', 3), (3, 'left', 3)]):
					self.bendJntTxt = pm.text(l='Bend Jnt: ')
					self.bendJntTxtFld = pm.textField(w=220, ed=False)
					self.bendJntButt = pm.button(l='<<', c=pm.Callback(self.loadBendJnt))

			with pm.rowColumnLayout(nc=2, rs=[(1,3), (2,3)], co=[(1, 'left', 150), (2, 'left', 5)]):
				pm.text(l='offset')
				self.offsetFloatField = pm.floatField(pre=2, v=0.1)

				pm.text(l='aim axis')
				with pm.optionMenu(w=40) as self.aimAxisMenu:
					pm.menuItem(l='+x')
					pm.menuItem(l='+y')
					pm.menuItem(l='+z')
					pm.menuItem(l='-x')
					pm.menuItem(l='-y')
					pm.menuItem(l='-z')
					
				pm.text(l='up axis')
				with pm.optionMenu(w=40) as self.upAxisMenu:
					pm.menuItem(l='+x')
					pm.menuItem(l='+y')
					pm.menuItem(l='+z')
					pm.menuItem(l='-x')
					pm.menuItem(l='-y')
					pm.menuItem(l='-z')
		
		self.baseUi.clearElemSideTxtFld()
		self.aimAxisMenu.setValue('+y')
		self.upAxisMenu.setValue('+z')

	def getBaseVars(self):
		if not self.rigObj:
			return

		self.rigObj.elem = self.baseUi.getElem()
		self.rigObj.side = self.baseUi.getSide()
		self.rigObj.size = self.baseUi.getSize()


	def getSelJnt(self):
		sel = misc.getSel()
		if not sel:
			return None

		warn = False		

		if isinstance(sel, pm.nt.Joint) == False:
			om.MGlobal.displayWarning('Select a joint to load.')
			return None

		return sel

	def loadBendJnt(self):
		self.bendJnt = self.getSelJnt()
		if not self.bendJnt:
			self.bendJntTxtFld.setText('')
			return
		self.bendJntTxtFld.setText(self.bendJnt.nodeName())


	def call(self):
		self._REQUIRE = {'Parent' : self.baseUi.rigParent,
						 'Bend Jnt': self.bendJnt}
		if not self.checkRequires():
			return

		self.rigObj = ccjr.VolCrtJntRig(parent=self.baseUi.rigParent,
										jnt=self.bendJnt,
										aimAxis=self.aimAxisMenu.getValue(),
										upAxis=self.upAxisMenu.getValue(),
										offset=self.offsetFloatField.getValue(),
										animGrp=self.baseUi.animGrp, 
										utilGrp=self.baseUi.utilGrp, 
										skinGrp= self.baseUi.skinGrp, 
										stillGrp=self.baseUi.stillGrp)

		# get elem, side, size
		self.getBaseVars()
		# rig
		self.rigObj.rig()



class splineTentacleRig(BaseUi):
	_DESCRIPTION = """SPLINE TENTACLE RIG
	Generate a tentacle like spline ik rig and geometry.

	METHOD: Spline Ik, Node connections, Loft 
	PARENT: None
	REQUIRES:
	1 or more NURBS curve
	"""

	def __init__(self, baseUi, parent):
		BaseUi.__init__(self, parent)
		self.uiparent = parent
		self.baseUi = baseUi

		self.baseUi.defultElem = 'tentacle'
		self.crvs = []
		self.rigObjs = []


		#ui
		try:
			pm.deleteUI(self.rigCol)
		except: pass

		with pm.columnLayout(adj=True, rs=5, parent=self.uiparent) as self.rigCol:
			pm.separator()

			with pm.columnLayout(adj=True, rs=5, co=['both', 20]):
				with pm.rowColumnLayout(nc=3, rs=(1, 5), co=[(1, 'left', 5), (2, 'left', 3), (3, 'left', 3)]):
					self.crvTxt = pm.text(l='Curves: ')
					self.crvTxtFld = pm.textField(w=230, ed=False)
					self.crvButt = pm.button(l='<<', c=pm.Callback(self.loadCrvs))
				with pm.rowColumnLayout(nc=2, rs=(1, 5), co=[(1, 'left', 97), (2, 'left', 13)]):
					pm.text(l='crossSection')
					with pm.optionMenu(w=60) as self.crossSecShapeMenu:
							pm.menuItem(l='flatDiamond')
							pm.menuItem(l='diamond')
							pm.menuItem(l='halfCircle')
							pm.menuItem(l='circle')
							pm.menuItem(l='square')
							pm.menuItem(l='roundSquare')

				# with pm.rowColumnLayout(nc=3, rs=(1, 5), co=[(1, 'left', 0), (2, 'left', 10), (3, 'left', 3)]):
				with pm.rowColumnLayout(nc=2, rs=(1, 5), co=[(1, 'left', 0), (2, 'left', 7)]):
					with pm.columnLayout(adj=True, rs=9):
						self.rebuildSpanChkBoxGrp = pm.checkBoxGrp(label='rebuild span', v1=True, cc=pm.Callback(self.checkLockSlider))
						self.createPolygonChkBoxGrp = pm.checkBoxGrp(label='create polygon', v1=True)
					with pm.rowColumnLayout(nc=2, rs=(1, 2), co=[(1, 'left', 0), (2, 'left', 5)]):
						pm.text(l='jnt orient')
						with pm.optionMenu(w=45) as self.jointOrientMenu:
							pm.menuItem(l='xyz')
							pm.menuItem(l='yzx')
							pm.menuItem(l='zxy')
							pm.menuItem(l='xzy')
							pm.menuItem(l='yxz')
							pm.menuItem(l='zyx')
						pm.text(l='sec axis')
						with pm.optionMenu(w=60) as self.secAxisMenu:
							pm.menuItem(l='xup')
							pm.menuItem(l='yup')
							pm.menuItem(l='zup')
							pm.menuItem(l='xdown')
							pm.menuItem(l='ydown')
							pm.menuItem(l='zdown')

				with pm.columnLayout(adj=True, rs=3):
					self.crvSpanIntSliderGrp = pm.intSliderGrp(label="crvSpan", min=4, max=80, v=8, field=True, cw3=[50, 20, 90])
					self.geoSpanIntSliderGrp = pm.intSliderGrp(label="geoSpan", min=3, max=256, v=12, field=True, cw3=[50, 20, 10])
					self.lengthFloatSliderGrp = pm.floatSliderGrp(label="length", pre=3, min=0.01, max=1.0, v=0.334, field=True, cw3=[50, 30, 10])
					self.sharpnessFloatSliderGrp = pm.floatSliderGrp(label="sharpness", pre=3, min=0.00, max=1.0, v=0.5, field=True, cw3=[50, 30, 10])	
					self.tipStartFloatSliderGrp = pm.floatSliderGrp(label="tipStart", pre=3, min=0.00, max=1.0, v=0.8, field=True, cw3=[50, 30, 10])
					
				
				

		
		self.baseUi.clearElemSideTxtFld()
		self.jointOrientMenu.setValue('yzx')
		self.secAxisMenu.setValue('yup')



	def checkLockSlider(self):
		checked = self.rebuildSpanChkBoxGrp.getValue1()
		self.crvSpanIntSliderGrp.setEnable(checked)



	def getBaseVars(self):
		if not self.rigObj:
			return

		self.rigObj.elem = self.baseUi.getElem()
		self.rigObj.side = self.baseUi.getSide()
		self.rigObj.size = self.baseUi.getSize()


	def getSelCrv(self):
		sels = misc.getSel(num='inf')
		crvs = []
		if not sels:
			return crvs
		
		for sel in sels:
			try:
				crvShp = sel.getShape(ni=True)
				if isinstance(crvShp, pm.nt.NurbsCurve) == False:
					om.MGlobal.displayWarning('%s is not a NURBS curve.' %sel)
					pass
				crvs.append(sel)
			except:
				pass

		return crvs


	def loadCrvs(self):
		self.crvs = self.getSelCrv()
		if not self.crvs:
			om.MGlobal.displayError('Select 1 or more NURBS curve.')
			self.crvTxtFld.setText('')
			return

		self.loadObjsToTxtFld(self.crvs, self.crvTxtFld)

	def autoGenElemIndx(self):
		i = 1
		exit = False

		while(exit == False):
			iStr = str(i).zfill(2)
			if pm.objExists('%s%sRig%s_grp' %(self.rigObj.elem, iStr, self.rigObj.side)) == True:
				i += 1
			else:
				self.rigObj.elem = '%s%s' %(self.rigObj.elem, iStr)
				exit = True

	def call(self):
		self._REQUIRE = {'Curves': self.crvs}
		if not self.checkRequires():
			return

		reload(sptr)
		
		for crv in self.crvs:
			self.rigObj = sptr.SplineTentacleRig(crv=crv, 
											span=self.geoSpanIntSliderGrp.getValue(), 
											length=self.lengthFloatSliderGrp.getValue(), 
											sharpness=self.sharpnessFloatSliderGrp.getValue(),
											jointOrient=self.jointOrientMenu.getValue(),
											secAxis=self.secAxisMenu.getValue(),
											rebuildSpan=self.rebuildSpanChkBoxGrp.getValue1(), 
											crvSpan=self.crvSpanIntSliderGrp.getValue(),
											crossSection=self.crossSecShapeMenu.getValue(),
											tipStart=self.tipStartFloatSliderGrp.getValue(),
											createPolygon=self.createPolygonChkBoxGrp.getValue1())
			# get elem, side, size, auto generate name
			self.getBaseVars()
			self.autoGenElemIndx()

			# rig
			self.rigObj.rig()



class backSplineIkRig(BaseUi):
	_DESCRIPTION = """BACK SPLINE IK RIG
	Classic Lego City style for a character's spine rig.
	User has 2 options to pin the base(fk-like) or both ends(ribbon-like).

	METHOD: Spline Ik, Node connections
	PARENT: optional
	REQUIRES:
	3 or more joints
	"""

	def __init__(self, baseUi, parent):
		super(backSplineIkRig, self).__init__(parent)
		self.uiparent = parent
		self.baseUi = baseUi

		self.baseUi.defultElem = 'back'
		self.jnts = []


		#ui
		try:
			pm.deleteUI(self.rigCol)
		except: pass

		with pm.columnLayout(adj=True, rs=5, parent=self.uiparent) as self.rigCol:
			pm.separator()

			with pm.columnLayout(adj=True, rs=5, co=['both', 20]):
				with pm.rowColumnLayout(nc=3, rs=(1, 5), co=[(1, 'left', 5), (2, 'left', 3), (3, 'left', 3)]):
					pm.text(l='Jnts: ')
					self.jntsTxtFld = pm.textField(w=230, ed=False)
					self.jntsButt = pm.button(l='<<', c=pm.Callback(self.loadJnts))

				# with pm.columnLayout(adj=True, rs=3):
				self.numJntIntSliderGrp = pm.intSliderGrp(label="numJnt", min=3, max=120, v=6, field=True, cw3=[50, 20, 90])

				with pm.rowColumnLayout(nc=2, rs=(1, 5), co=[(1, 'left', 97), (2, 'left', 13)]):
					pm.text(l='pin')
					with pm.optionMenu(w=60) as self.pinMenu:
						pm.menuItem(l='base')
						pm.menuItem(l='both')

					pm.text(l='ctrlShape')
					with pm.optionMenu(w=60) as self.ctrlShapeMenu:
							pm.menuItem(l='roundSquare')
							pm.menuItem(l='circle')
							pm.menuItem(l='crossCircle')
							pm.menuItem(l='square')
							pm.menuItem(l='crossSquare')

				

	def getBaseVars(self):
		if not self.rigObj:
			return

		self.rigObj.elem = self.baseUi.getElem()
		self.rigObj.side = self.baseUi.getSide()
		self.rigObj.size = self.baseUi.getSize()


	def getSelJnt(self):
		sels = misc.getSel(num='inf', selType='joint')
		if not sels:
			return None

		return sels


	def loadJnts(self):
		self.jnts = self.getSelJnt()
		if not self.jnts:
			self.jntsTxtFld.setText('')
			return
		self.loadObjsToTxtFld(self.jnts, self.jntsTxtFld)



	def call(self):
		self._REQUIRE = {'Joints': self.jnts}
		if not self.checkRequires():
			return

		self.rigObj = bsir.BackSplineIkRig(jnts=self.jnts, 
										parent=self.baseUi.rigParent, 
										numJnt=self.numJntIntSliderGrp.getValue(),
										pin=self.pinMenu.getValue(),
										ctrlShp=self.ctrlShapeMenu.getValue(),
										animGrp=self.baseUi.animGrp, 
										skinGrp= self.baseUi.skinGrp, 
										stillGrp=self.baseUi.stillGrp)
		# get elem, side, size
		self.getBaseVars()

		# rig
		self.rigObj.rig()