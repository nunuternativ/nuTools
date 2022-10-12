import pymel.core as pm
import maya.OpenMaya as om
import colorsys

from nuTools import misc

reload(misc)



class TempShdPalette(object):

	def __init__(self, dim=(10, 6)):
		self.WINDOW_NAME = 'TempShdPaletteWin'
		self.WINDOW_TITLE = 'Temp Shade Palette v1.0'

		# self.EDIT_WINDOW_NAME = 'TempShdPaletteEditWin'
		# self.EDIT_WINDOW_TITLE = 'Edit Color'

		self.HSV_saturation = 1
		self.HSV_value = 1
		self.numColor = dim[0] * dim[1] 
		self.dim = dim
		self.HSV_tuples = []

		self.beforeEditHsv = []
		self.beforeEditTrans = 0.0

		self.selColor = []
		self.tempShades = []
		self.existingSdp = []
		self.colorDict = {}
		

	def UI(self):
		if pm.window(self.WINDOW_NAME, ex=True):
			pm.deleteUI(self.WINDOW_NAME, window=True)
		with pm.window(self.WINDOW_NAME, title=self.WINDOW_TITLE, s=False, mnb=True, mxb=False) as self.mainWindow:
			with pm.columnLayout(adj=True, rs=5, co=['both', 5]):
				with pm.frameLayout(labelVisible=0, mh=5, mw=5):

					self.palette = pm.palettePort(dim=self.dim, h=145, w=220, ced=False, cc=pm.Callback(self.updateSelCanvas))
					
				with pm.frameLayout(labelVisible=0, mh=5, mw=5, borderStyle='out'):
					with pm.rowColumnLayout(nc=2, co=([1, 'left', 5], [2, 'left', 5])):
						self.selColorCanvas = pm.canvas(hsv=(0, 0, 0), width=50, height=50, pc=pm.Callback(self.createNewShd))

						with pm.rowColumnLayout(nc=3, rs=([1, 10]), co=([1, 'left', 5], [2, 'left', 5], [3, 'left', 5])):
							pm.text(l='Dull')
							self.saturationIntSliderGrp = pm.intSliderGrp(v=10, min=0, max=10, cc=pm.Callback(self.getSaturation))
							pm.text(l='Vivid')

							pm.text(l='Dark')
							self.valueIntSliderGrp = pm.intSliderGrp(v=10, min=0, max=10, cc=pm.Callback(self.getValue))
							pm.text(l='Bright')

					with pm.frameLayout(l='Existing Colors', mh=5, mw=5, h=300, borderStyle='in', cll=True, cl=False):
						with pm.scrollLayout():
							with pm.gridLayout(nc=4, autoGrow=True, cellWidthHeight=(64, 64)) as self.existingGridLayout:
								pass
					
					pm.button(l='Update', c=pm.Callback(self.updateInfo))
					# with pm.rowColumnLayout(nc=2, rs=([1, 10]), co=([1, 'left', 40], [2, 'left', 20])):
					# 	pm.button(l='Assign', h=30, w=100)
					# 	pm.button(l='Copy', h=30, w=100)



		pm.palettePort(self.palette, edit=True, scc=0 )
		self.updatePalette()
		self.updateSelCanvas()

		self.getAllShader()
		self.updateExistShade()



	def updateInfo(self):
		self.getAllShader()
		self.updateExistShade()



	def getColorName(self):
		paletteIndex = pm.palettePort(self.palette, q=True, scc=True )
		if paletteIndex in range(0, 5):
			return 'red'
		elif paletteIndex in range(5, 10):
			return 'orange'

		elif paletteIndex in range(10, 15):
			return 'yellow'
		elif paletteIndex in range(15, 20):
			return 'chartreuseGreen'

		elif paletteIndex in range(20, 25):
			return 'green'
		elif paletteIndex in range(25, 30):
			return 'springGreen'

		elif paletteIndex in range(30, 35):
			return 'cyan'
		elif paletteIndex in range(35, 40):
			return 'azure'

		elif paletteIndex in range(40, 45):
			return 'blue'
		elif paletteIndex in range(45, 50):
			return 'violet'

		elif paletteIndex in range(50, 55):
			return 'magenta'
		elif paletteIndex in range(55, 60):
			return 'rose'



	def getShaderName(self):
		#paletteIndexStr = str(pm.palettePort(self.palette, q=True, scc=True ))
		colorName = self.getColorName()
		# satStr = str(self.selColor[1]).replace('.', '')
		# valStr = str(self.selColor[2]).replace('.', '')

		shaderName = '%s_tmpShd01' %(colorName)
		return shaderName



	def createNewShd(self):
		newShd = None
		selected = pm.ls(sl=True, dag=True)
		pm.select(cl=True)

		for shd, color in self.colorDict.iteritems():
			if self.selColor == color:
				newShd = shd
				om.MGlobal.displayWarning('Shader with this color already exists! Will use  %s.' %shd)
				break

		if not newShd:
			newShd = pm.shadingNode('lambert', asShader=True, n=self.getShaderName())
			rgb = colorsys.hsv_to_rgb(self.selColor[0], self.selColor[1], self.selColor[2])

			newShd.colorR.set(rgb[0])
			newShd.colorG.set(rgb[1])
			newShd.colorB.set(rgb[2])



		if selected:
			pm.select(selected, r=True)
			self.assignColor(newShd)

		self.updateInfo()



	def getAllShader(self):
		self.tempShades = []
		self.colorDict = {}

		shds = pm.ls(type='lambert')
		lamberts = [s for s in shds if isinstance(s, pm.nt.Lambert) and s.nodeName() != 'lambert1']

		for lambert in lamberts:
			connections = pm.listConnections(lambert, s=True, d=False)
			if not connections:
				self.tempShades.append(lambert)

	def removeAllExistingSdp(self):
		for sdp in self.existingSdp:
			pm.deleteUI(sdp)

		self.existingSdp = []



	def updateExistShade(self):
		if not self.tempShades:
			return

		self.removeAllExistingSdp()
		for s in self.tempShades:
			hsv = self.getHSVFromShader(s)
			if not hsv in self.colorDict.values():
				self.colorDict[s] = hsv
				sdp = self.createSdp(hsv, s)
				self.existingSdp.append(sdp)



	def createSdp(self, hsv, shade):
		sdp = pm.swatchDisplayPort(rs=64, wh=(64, 64), bw=1, sn=shade, parent=self.existingGridLayout, ann=shade.nodeName(), 
								  pc=pm.Callback(self.assignColor, shade))
		pm.popupMenu( parent=sdp )
		pm.menuItem(l='Edit', c=pm.Callback(self.editShader, shade))
		pm.menuItem(l='Delete', c=pm.Callback(self.deleteShade, shade))
		return sdp



	def editShader(self, shade):
		self.beforeEditHsv = self.getHSVFromShader(shade)

		shaderTrans = shade.transparency.get()
		trans = colorsys.rgb_to_hsv(shaderTrans[0], shaderTrans[1], shaderTrans[2])
		self.beforeEditTrans = trans[2]

		pm.layoutDialog(ui=pm.Callback(self.editUI, self.beforeEditHsv, self.beforeEditTrans, shade))
		#self.updateInfo()



	def editUI(self, hsv, trans, shade):
   		with pm.formLayout(pm.setParent(q=True)) as self.editForm:
			with pm.frameLayout(labelVisible=0, mh=5, mw=5, borderStyle='out'):
				with pm.rowColumnLayout(nc=2, co=([1, 'left', 5], [2, 'left', 5])):
					self.editColorSdp = pm.swatchDisplayPort(rs=64, wh=(64, 64), sn=shade, ann=shade.nodeName())

					with pm.rowColumnLayout(nc=2, rs=([1, 5]), co=([1, 'left', 5], [2, 'left', 5])):
						pm.text(l='Hue')
						self.editHueIntSliderGrp = pm.intSliderGrp(v=hsv[0]*100, min=0, max=100, dc=pm.Callback(self.editShadeValue, shade))

						pm.text(l='Saturation')
						self.editSaturationIntSliderGrp = pm.intSliderGrp(v=hsv[1]*10, min=0, max=10, dc=pm.Callback(self.editShadeValue, shade))

						pm.text(l='Value')
						self.editValueIntSliderGrp = pm.intSliderGrp(v=hsv[2]*10, min=0, max=10, dc=pm.Callback(self.editShadeValue, shade))


						pm.text(l='Transparency')
						self.editTransIntSliderGrp = pm.intSliderGrp(v=trans*10, min=0, max=10, dc=pm.Callback(self.editShadeValue, shade))


				with pm.rowColumnLayout(nc=2, rs=([1, 10]), co=([1, 'left', 40], [2, 'left', 30])):
					pm.button(l='OK', h=25, w=70, c='pm.layoutDialog(dis="OK")')
					pm.button(l='Cancel', h=25, w=70, c=pm.Callback(self.editCancel, shade))



	def editCancel(self, shade):
		rgb = colorsys.hsv_to_rgb(self.beforeEditHsv[0], self.beforeEditHsv[1], self.beforeEditHsv[2])
		shade.colorR.set(rgb[0])
		shade.colorG.set(rgb[1])
		shade.colorB.set(rgb[2])

		shade.transparencyR.set(self.beforeEditTrans)
		shade.transparencyG.set(self.beforeEditTrans)
		shade.transparencyB.set(self.beforeEditTrans)

		pm.layoutDialog(dis="Canceled")



	def editShadeValue(self, shade):
		hue = self.editHueIntSliderGrp.getValue() * 0.01
		sat = self.editSaturationIntSliderGrp.getValue() * 0.1
		val = self.editValueIntSliderGrp.getValue() * 0.1
		trans = self.editTransIntSliderGrp.getValue() * 0.1

		rgb = colorsys.hsv_to_rgb(hue, sat, val)

		shade.colorR.set(rgb[0])
		shade.colorG.set(rgb[1])
		shade.colorB.set(rgb[2])

		shade.transparencyR.set(trans)
		shade.transparencyG.set(trans)
		shade.transparencyB.set(trans)



	def deleteShade(self, shade):
		pm.delete(shade)
		self.updateInfo()



	def assignColor(self, shd):
		if not pm.ls(sl=True, dag=True):
			pm.hyperShade(objects=shd)
			return
		pm.hyperShade(assign=shd)



	def getHSVFromShader(self, shader):
		return colorsys.rgb_to_hsv(shader.colorR.get(), shader.colorG.get(), shader.colorB.get())



	def updateSelCanvas(self):
		self.getSelectedColor()
		if self.selColor:
			pm.canvas(self.selColorCanvas, e=True, hsv=[self.selColor[0]*360, self.selColor[1], self.selColor[2]])



	def getSelectedColor(self):
		rgb = pm.palettePort(self.palette, q=True, rgb=True )
		if not rgb:
			self.selColor = []
		self.selColor = colorsys.rgb_to_hsv(rgb[0], rgb[1], rgb[2])
		


	def getHSV(self):
		self.HSV_tuples = [(x*360.0/self.numColor, self.HSV_saturation, self.HSV_value) for x in range(self.numColor)]



	def updatePalette(self):
		self.getHSV()
		index = 0
		for i in self.HSV_tuples:
		    pm.palettePort(self.palette, e=True, hsv=(index, i[0], i[1], i[2], 0))
		    index += 1

		pm.palettePort(self.palette, e=True, redraw=True)



	def getValue(self):
		self.HSV_value = self.valueIntSliderGrp.getValue() * 0.1
		self.updatePalette()
		self.updateSelCanvas()

	def getSaturation(self):
		self.HSV_saturation = self.saturationIntSliderGrp.getValue() * 0.1
		self.updatePalette()
		self.updateSelCanvas()
