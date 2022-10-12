import pymel.core as pm
import maya.OpenMaya as om
import maya.OpenMayaAnim as oma
import maya.mel as mel

from nuTools import misc as misc

reload(misc)

_OBJ_VAR = 'SkinWeightToolObject'

# add hot key when module loads
# Paint Skin Weight influence list walker (alt + z)
nexInfNameCmd = pm.nameCommand('swtNextInfluence', 
		annotation='Skin weight influence pick walk', 
		command='python("%s.nextInf()");' %_OBJ_VAR)
pm.hotkey(k='z', alt=True, name=nexInfNameCmd)

# Toggle paint/select mode (alt + x)
toggleSelModeNameCmd = pm.nameCommand('swtToggleSelModeInfluence', 
		annotation='Skin weight paint/select mode toggle', 
		command='python("%s.togglePaintSelectMode()");' %_OBJ_VAR)
pm.hotkey(k='x', alt=True, name=toggleSelModeNameCmd)


class SkinWeightTool(object):
	def __init__(self):
		self._pinBtn = "pinButton"
		self._infTv = "theSkinClusterInflList"

		self.mesh = None  
		self.skinCluster = None  
		self.joints = []
		self.paintJoints = []

		# get joint influences of the mesh
		res = self.getInfluences()
		if res == False:
			return

		mel.eval('''ArtPaintSkinWeightsTool;''')

	def togglePaintSelectMode(self):
		currCtx = pm.currentCtx()
		if currCtx == 'artAttrSkinContext':
			currentMode = mel.eval('artAttrSkinPaintCtx -q -skinPaintMode %s' %currCtx)
			if currentMode == 1:  # go to select mode
				mel.eval('radioButtonGrp -e -select 2 artAttrSkinPaintModeRadioButton;')
				mel.eval('artAttrSkinPaintModePaintSelect 0 artAttrSkinPaintCtx; selectType -joint false;')
			else:
				selsComp = pm.filterExpand(ex=True, sm=(31, 32, 34))
				if not selsComp:
					pm.select(self.mesh, r=True)
				mel.eval('radioButtonGrp -e -select 1 artAttrSkinPaintModeRadioButton;')
				mel.eval('artAttrSkinPaintModePaintSelect 1 artAttrSkinPaintCtx; selectType -joint true;')

	def nextInf(self):
		currCtx = pm.currentCtx()
		if currCtx == 'artAttrSkinContext' and mel.eval('artAttrSkinPaintCtx -q -skinPaintMode %s' %currCtx) == 1:
			infLists = pm.treeView(self._infTv, q=True, itemVisible=True)
			currItem = pm.treeView(self._infTv, q=True, selectItem=True)[0]
			infNum = len(infLists)
			index = 0

			for i in xrange(0, infNum):
				pm.treeView(self._infTv, e=True, selectItem=(infLists[i], False))
				mel.eval('artSkinInflListChanging %s 0;' %infLists[i])
				if infLists[i] == currItem:
					index = (i+1) % infNum
					break

			pm.treeView(self._infTv, e=True, selectItem=(infLists[index], True))
			cmd = 'artSkinInflListChanging %s 1;' %infLists[index]
			cmd += ' artSkinInflListChanged artAttrSkinPaintCtx;'
			mel.eval(cmd)

	def selectFirstInf(self):
		infLists = pm.treeView(self._infTv, q=True, itemVisible=True)
		infNum = len(infLists)

		for i in xrange(0, infNum):
			pm.treeView(self._infTv, e=True, selectItem=(infLists[i], False))
			mel.eval('artSkinInflListChanging %s 0;' %infLists[i])

		pm.treeView(self._infTv, e=True, selectItem=(infLists[0], True))
		cmd = 'artSkinInflListChanging %s 1;' %infLists[0]
		cmd += ' artSkinInflListChanged artAttrSkinPaintCtx;'
		mel.eval(cmd)

	def getSelMesh(self):
		self.mesh = None
		sels = pm.selected(type='transform')
		if not sels or not misc.checkIfPly(sels[0]):
			om.MGlobal.displayError('Select a transform of a mesh to initialize.')
			return
		self.mesh = sels[0]
		pm.select(self.mesh, r=True)

	def getInfluences(self):
		if not self.mesh:
			self.getSelMesh()

		if not self.mesh:
			return False

		# get MDagPath to self.mesh
		mSel = om.MSelectionList()
		mSel.add(self.mesh.longName())
		dagPath = om.MDagPath()
		mSel.getDagPath(0, dagPath) 
		dagPath.extendToShape()
		currentNode = dagPath.node()

		# get skin cluster node
		fnSkin = None
		self.joints = []

		itDG = om.MItDependencyGraph(currentNode, om.MFn.kSkinClusterFilter, om.MItDependencyGraph.kUpstream)
		while not itDG.isDone():
			oCurrentItem = itDG.currentItem()
			fnSkin = oma.MFnSkinCluster(oCurrentItem)
			self.skinCluster = pm.nt.SkinCluster(fnSkin.name())
			break

		if not fnSkin:
		  om.MGlobal.displayError("Error getting skinCluster node.")
		  return False

		# get joint influence(s)
		jntMDagPathArray = om.MDagPathArray()
		fnSkin.influenceObjects(jntMDagPathArray)
		for i in range(jntMDagPathArray.length()):
			jntPath = jntMDagPathArray[i].fullPathName()
			self.joints.append(pm.PyNode(jntPath))

		if not self.joints:
			om.MGlobal.displayError("Error getting joint influence.")
			return False

		om.MGlobal.displayInfo('\nPainting  :  %s' %self.mesh.nodeName())

	def paint(self, jnts=[]):
		# if arg jnts not passed, get joints selected
		if not jnts:
			selJnt = [i for i in pm.selected(type='transform') if i in self.joints]
		else:
			selJnt = jnts
		self.paintJoints = []
		# if user select joint, do unlock only selected ones
		if selJnt:
			for j in self.joints:
				if j not in selJnt:
					j.liw.set(True)
				else:
					j.liw.set(False)
					self.paintJoints.append(j)

			# deselect joint
			pm.select(selJnt, d=True)

		# get select component
		selsComp = pm.filterExpand(ex=True, sm=(31, 32, 34))
		if not selsComp:
			pm.select(self.mesh, r=True)
		else:
			comps = misc.convertSelToVtx()
			pm.select(comps)
		
		# invoke paint skin weights tool
		mel.eval('ArtPaintSkinWeightsTool;')

		if self.paintJoints:
			for j in self.joints:
				lock = j.liw.get()
				pm.treeView(self._infTv, e=True, si=(j.shortName(), not(lock)))

			pm.iconTextCheckBox(self._pinBtn, e=True, v=True)

			cmd = 'skinClusterInflPinCallback "%s" "%s" 1;' %(self._pinBtn, self._infTv)
			cmd += 'artSkinInflListChanged "artAttrSkinPaintCtx";'
			mel.eval(cmd)

			# select the first inf
			self.selectFirstInf()




			



