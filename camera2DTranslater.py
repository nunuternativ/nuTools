import pymel.core as pm
import maya.OpenMaya as om


class Camera2DTranslater(object):

	def __init__(self, cam=None, ctxName='cam2DTranslater', cursor='track', tol=0.001, hotkey=True):
		if not cam:
			try:
				sel = pm.selected(type='transform')[0]
				shp = sel.getShape(ni=True)
				if shp.type() == 'camera':
					cam = sel
			except:
				pass
		print cam
		if not cam:
			om.MGlobal.displayError('Select a camera from a view port and try agian.')
			return

		self.tol = tol
		self.ctxName = ctxName
		self.cursor = cursor
		self.prevTool = 'selectSuperContext'
		self.cam = cam
		self.objs = {}
		self.dragCtx = None

		self.oldOverScan = 1.0
		self.oldHorizontalFilmOffset = 0.0
		self.oldVerticalFilmOffset = 0.0

		self._STATE = False

		self.createCtx()

	def createCtx(self):
		try:
			pm.deleteUI(self.ctxName)
		except: pass

		self.dragCtx = pm.draggerContext(   n=self.ctxName,
											um='step', 
											sp='screen', 
											pr='viewPlane', 
											cur=self.cursor,
											inz=pm.Callback(self.printActivated),
											fnz=pm.Callback(self.printDeactivated),
											# pc=pm.Callback(self.click),
											dc=pm.Callback(self.drag))

		self.activate()

	def activate(self):
		self.prevTool = pm.currentCtx()
		pm.setToolTo(self.dragCtx)
		self._STATE = True

	def deactivate(self):
		pm.setToolTo(self.prevTool)
		self._STATE = False

	def printDeactivated(self):
		om.MGlobal.displayInfo('OFF : Camera 2D translate mode!')
		self.cam.horizontalFilmOffset.set(self.oldHorizontalFilmOffset)
		self.cam.verticalFilmOffset.set(self.oldVerticalFilmOffset)
		self.cam.overscan.set(self.oldOverScan)
		
	def printActivated(self):
		om.MGlobal.displayInfo('ON : Camera 2D translate mode!')

	def drag(self):
		currPos = pm.draggerContext(self.dragCtx, q=True, dragPoint=True)
		ancPos = pm.draggerContext(self.dragCtx, q=True, anchorPoint=True)

		x = (currPos[0] - ancPos[0]) * self.tol
		y = (currPos[1] - ancPos[1]) * self.tol
		mod = pm.draggerContext(self.dragCtx, q=True, modifier=True)

		currOverScan = self.cam.overscan.get()
		if mod == 'ctrl':
			overScan = currOverScan + y
			if overScan >= 0.01:
				self.cam.overscan.set(overScan)
		else:
			currX = self.cam.horizontalFilmOffset.get()
			currY = self.cam.verticalFilmOffset.get()
			invOverScan = 1/currOverScan
			self.cam.horizontalFilmOffset.set(currX + (x * invOverScan))
			self.cam.verticalFilmOffset.set(currY + (y * invOverScan))

		pm.refresh(cv=True)



	


