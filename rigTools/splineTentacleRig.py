import pymel.core as pm
import maya.mel as mel
import maya.OpenMaya as om
from nuTools import misc, config, controller
import nuTools.rigTools.baseRig as baseRig

reload(misc)
reload(config)
reload(controller)
reload(baseRig)

import random


def splineTentacleGenerator():
	from nuTools.rigTools import crm_ui as ui
	reload(ui)
	mainWinName = 'Spline_Tentacle_Generator'
	mainWinTitle = 'Spline Tentacle Generator v1.0'

	try:
		pm.deleteUI(mainWinName)
	except: pass


	mainWin = pm.window(mainWinName, t=mainWinTitle, s=False, mnb=False, mxb=False, w=270, h=160)
	# mainCol = pm.columnLayout(adj=True, parent=mainWin, rs=5)
	baseUi = ui.BaseUi(mainWin)
	baseUi.create()

	# hide unused UIs
	baseUi.elemSideRowCol.setManage(False)
	baseUi.parentRowCol.setManage(False)
	baseUi.rigGrpFrameLayout.setManage(False)

	mainCol = pm.columnLayout(adj=True, co=['both', 5], rs=3, parent=baseUi.mainCol)
	stgUi = ui.splineTentacleRig(baseUi, mainCol)
	button = pm.button(l='Rig', h=30, c=pm.Callback(stgUi.call), parent=mainCol)

	mainWin.show()



class SplineTentacleRig(baseRig.BaseRig):

	def __init__(self, parent=None, crv=None, span=10, length=0.334, sharpness=0.8, jointOrient='yzx', secAxis='yup',
		size=1.00, elem='tentacle', side='', rebuildSpan=False, crvSpan=8, crossSection='flatDiamond', tipStart=0.8, createPolygon=True,
		animGrp=None, utilGrp=None, skinGrp=None, stillGrp=None):
		super(SplineTentacleRig, self).__init__(parent=parent, animGrp=animGrp, utilGrp=utilGrp, skinGrp=skinGrp, stillGrp=stillGrp)
		
		self.crv = crv
		self.span = span
		self.jointOrient = jointOrient
		self.length = length
		self.sharpness = sharpness
		self.size = size
		self.elem = elem
		self.side = side
		self.rebuildSpan = rebuildSpan
		self.crvSpan = crvSpan

		self.secAxis = secAxis
		self.crossSecShape = crossSection
		self.tipStart = tipStart
		self.jnts = []
		self.circles = []
		self.rigGrp = None
		self.rootCtrl = None
		self.surface = None
		self.circleNodes = []
		self.ikHndl = None
		self.crvJnts = []
		self.ctrls = []
		self.jntConsGrp = None
		self.scaleAttrs = []
		self.createPolygon = createPolygon

		self.ctrlColors = ['red', 'green', 'blue', 'lightBlue', 'yellow', 'orange', 'lightBrown', 'pink',
			'navyBlue', 'darkBlue', 'darkRed', 'brown', 'darkGreen']



	def rig(self):
		if not self.crv:
			return

		# origCrv = self.crv
		# self.crv = pm.duplicate(origCrv)[0]
		# try:
		# 	origCrv.attr('visibility').set(False)
		# except:
		# 	pass

		self.crv.rename('%s%s_crv' %(self.elem, self.side))
		misc.lockAttr(self.crv, lock=True, t=True, r=True, s=True, v=False)
		
		if self.rebuildSpan == True and self.crvSpan < 4:
			self.crvSpan = 4

		# create rig group. 
		self.createRigGrp()
		# pm.parent(self.crv, self.geoGrp)

		# rebuild crv, create jnts, apply spline ik
		self.createJnts()
		pm.parent(self.ikHndl, self.stillGrp)
		pm.parent(self.jntConsGrp, self.utilGrp)

		self.createCtrl()
		pm.parent(self.crvJnts[0], self.jntConsGrp)
		pm.parent(self.ctrlGrp, self.rootCtrl)


		self.createGeo()
		pm.parent(self.surface, self.geoGrp)


		misc.setDisplayType(self.crv, shp=True, disType='reference')
		pm.select(self.rootCtrl, r=True)



	def createRigGrp(self):
		self.rigGrp = pm.group(em=True, n='%sRig%s_grp' %(self.elem, self.side))
		misc.addStrAttr(self.rigGrp, 'crv')
		misc.addStrAttr(self.rigGrp, 'jnts')
		misc.addStrAttr(self.rigGrp, 'ikHndl')
		misc.addStrAttr(self.rigGrp, 'rootCtrl')

		self.animGrp = pm.group(em=True, n='%sAnim%s_grp' %(self.elem, self.side))
		self.stillGrp = pm.group(em=True, n='%sStill%s_grp' %(self.elem, self.side))
		self.utilGrp = pm.group(em=True, n='%sJnt%s_grp' %(self.elem, self.side))
		self.geoGrp = pm.group(em=True, n='%sGeo%s_grp' %(self.elem, self.side))


		self.stillGrp.attr('visibility').set(False)
		self.utilGrp.attr('visibility').set(False)

		self.stillGrp.inheritsTransform.set(False)
		self.utilGrp.inheritsTransform.set(False)
		self.geoGrp.inheritsTransform.set(False)

		pm.parent([self.animGrp, self.geoGrp, self.utilGrp, self.stillGrp], self.rigGrp)

		for grp in [self.rigGrp, self.animGrp, self.geoGrp, self.utilGrp, self.stillGrp]:
			misc.lockAttr(grp, lock=True, t=True, r=True, s=True)



	def createRootCtrl(self):
		self.rootCtrl = controller.Controller(name='%sRoot%s_ctrl'%(self.elem, self.side), 
			st='stick', scale=self.size * 5, axis='-%s'%self.jointOrient[0])
		self.rootCtrl.setColor('white')
		self.rootCtrl.lockAttr(v=True)
		self.rootCtrl.hideAttr(v=True)

		misc.addNumAttr(self.rootCtrl, '__ikCtrls__', 'float', lock=True)
		misc.addNumAttr(self.rootCtrl, 'slide', 'float', min=0)
		misc.addNumAttr(self.rootCtrl, 'stretch', 'float', dv=0, min=-1.0)
		misc.addNumAttr(self.rootCtrl, 'squash', 'float', dv=0, min=-1.0)
		misc.addNumAttr(self.rootCtrl, 'flat', 'float', dv=0, min=-1.0)
		misc.addNumAttr(self.rootCtrl, 'twist', 'float', dv=0)
		misc.addNumAttr(self.rootCtrl, 'roll', 'float', dv=0)

		self.ctrlGrp = pm.group(em=True, n='%sCtrl%s_grp' %(self.elem, self.side))

		rootCtrlShp = self.rootCtrl.getShape()
		ctrlVisAttr = misc.addNumAttr(rootCtrlShp, 'ctrlVis', 'long', max=1, min=0, dv=0, key=False, lock=False, hide=False)
		pm.connectAttr(ctrlVisAttr, self.ctrlGrp.attr('visibility'), f=True)

		misc.addNumAttr(rootCtrlShp, '__spanScale__', 'float', lock=True)

		rootCtrlZgrp = misc.zgrp(self.rootCtrl)
		misc.snapTransform('parent', self.jnts[0], rootCtrlZgrp, False, True)
		pm.parent(rootCtrlZgrp, self.animGrp)



	def createCtrl(self):
		self.createRootCtrl()

		pm.connectAttr(self.rootCtrl.attr('slide'), self.ikHndl.attr('offset'), f=True)
		pm.connectAttr(self.rootCtrl.attr('twist'), self.ikHndl.attr('twist'), f=True)
		pm.connectAttr(self.rootCtrl.attr('roll'), self.ikHndl.attr('roll'), f=True)
		misc.snapTransform('parent', self.rootCtrl, self.jntConsGrp, True, False)
		misc.snapTransform('scale', self.rootCtrl, self.jntConsGrp, True, False)
		

		slopeIndex = int(self.span * self.tipStart)
		slopeBase = self.span - slopeIndex
		s = 6

		for i in range(len(self.jnts)):

			sqstPma = pm.createNode('plusMinusAverage', n='%s%sSquashStretch%s_pma' %(self.elem, str(i+1).zfill(2), self.side))
			sqstPma.operation.set(1)
			sqstPma.input3D[0].input3Dx.set(1.0)
			sqstPma.input3D[0].input3Dy.set(1.0)
			sqstPma.input3D[0].input3Dz.set(1.0)

			

			pm.connectAttr(self.rootCtrl.attr('squash'), sqstPma.input3D[1].input3Dx)
			pm.connectAttr(self.rootCtrl.attr('flat'), sqstPma.input3D[2].input3Dx)
			pm.connectAttr(sqstPma.output3Dx, self.jnts[i].attr('s%s' %self.jointOrient[1]))

			pm.connectAttr(self.rootCtrl.attr('squash'), sqstPma.input3D[1].input3Dz)
			pm.connectAttr(sqstPma.output3Dz, self.jnts[i].attr('s%s' %self.jointOrient[2]))

			if i >= slopeIndex:
				radius = (1.1 - ((float(i) / float(self.span-1))  ** (8*(1.0-self.sharpness)))) * self.size
				s += 1
			else:
				radius = (1.1 - (float(i) / float(self.span-1)) * self.sharpness) * self.size

			if i < int(self.span * 0.8):
				pm.connectAttr(self.rootCtrl.attr('stretch'), sqstPma.input3D[1].input3Dy)
				pm.connectAttr(sqstPma.output3Dy, self.jnts[i].attr('s%s' %self.jointOrient[0]))

			spanScaleAttr = misc.addNumAttr(self.rootCtrl.getShape(), 'span%s' %(str(i+1).zfill(2)), 'float', dv=radius)
			self.scaleAttrs.append(spanScaleAttr)


		crvShp = self.crv.getShape()
		numCVs = crvShp.numCVs()

		for i in range(numCVs):
			position = list(crvShp.cv[i].getPosition(space='world'))
			crvJnt = pm.joint(position=position, rad=self.size, 
				n='%s%s%s_jnt' %(self.elem, str(i+1).zfill(2), self.side))
			self.crvJnts.append(crvJnt)

		
		prevCtrl = None
		randColorIndx = random.randint(0, 7)

		
		pm.makeIdentity(self.crvJnts[0], apply=True, t=True, r=True, s=True, n=False)
		pm.joint(self.crvJnts, e=True, zso=True, oj=self.jointOrient, sao=self.secAxis)
		self.crvJnts[-1].jointOrient.set([0,0,0])

		for i in range(numCVs):
			ctrl = controller.Controller(name='%s%s%s_ctrl' %(self.elem, str(i+1).zfill(2), self.side), 
				st='crossSphere', scale=self.size, axis='+y')

			
			ctrl.setColor(self.ctrlColors[randColorIndx])
			ctrl.lockAttr(v=True, s=True)
			ctrl.hideAttr(s=True, v=True)

			localWorldAttr = misc.addNumAttr(ctrl, 'localWorld', 'float', min=0.0, max=1.0, dv=1.0)

			ctrlZgrp = misc.zgrp(ctrl)

			misc.snapTransform('parent', self.crvJnts[i], ctrlZgrp, False, True)
			misc.snapTransform('parent', ctrl, self.crvJnts[i], False, False)

			if prevCtrl:
				parCons = pm.parentConstraint([self.rootCtrl, prevCtrl], ctrlZgrp, mo=True)
				misc.connectSwitchAttr(
					ctrlAttr=localWorldAttr, 
					posAttr=parCons.attr('%sW0' %self.rootCtrl.nodeName()), 
					negAttr=parCons.attr('%sW1' %prevCtrl.nodeName()), 
					elem='%s%s%s' %(self.elem, str(i+1).zfill(2), self.side))
			prevCtrl = ctrl
			self.ctrls.append(ctrl)
			pm.parent(ctrlZgrp, self.ctrlGrp)

		# bind skin
		pm.skinCluster(self.crvJnts, self.crv, tsb=True, ih=True, dr=0.1)



	def createJnts(self):
		if not self.crv:
			return
		crvShp = self.crv.getShape(ni=True)
		degree = crvShp.degree()
		# if self.rebuildSpan == False:
		# 	pm.rebuildCurve(self.crv, ch=False, rpo=True, rt=4, end=True, kr=False,
		# 	kcp=False, kep=True, kt=False, d=degree, tol=0.075)
		if self.rebuildSpan == True:
			print 'dada'
			pm.rebuildCurve(self.crv, ch=False, rpo=True, rt=0, end=True, kr=False,
			kcp=False, kep=True, kt=False, s=self.crvSpan-2, d=degree, tol=0.075)


		pocif = pm.createNode('pointOnCurveInfo', n='%s%s_pocif' %(self.elem, self.side))
		pm.connectAttr(crvShp.worldSpace[0], pocif.inputCurve, f=True)
		pocif.turnOnPercentage.set(True)

		self.jnts = []

		for i in range(0, self.span):
			value = self.length * (float(i)/float(self.span))
			pocif.parameter.set(value)

			trans = pocif.position.get()
			jnt = pm.joint(position=trans, rad=self.size*self.length, n='%sIk%s%s_jnt' %(self.elem, str(i+1).zfill(2), self.side))

		 	self.jnts.append(jnt)

		pm.delete(pocif)

		# re-orient joints
		
		pm.makeIdentity(self.jnts[0], apply=True, t=True, r=True, s=True, n=False)
		pm.joint(self.jnts[0], e=True, zso=True, oj=self.jointOrient, sao=self.secAxis, ch=True)
		self.jnts[-1].jointOrient.set([0,0,0])

		# pm.makeIdentity(self.jnts[0], apply=True, t=True, r=True, s=True, n=False)

		self.ikHndl = pm.ikHandle(sj=self.jnts[0], ee=self.jnts[-1], c=self.crv, ccv=False,
			scv=False, roc=True, shf=True, tws='linear', cra=True, rtm=False, ce=True, pcv=False,
			sol='ikSplineSolver')[0]
		# self.ikHndl = ikHndls[0]
		self.ikHndl.rename('%s%s_ikHndl' %(self.elem, self.side))
		self.ikHndl.attr('visibility').set(False)

		self.jntConsGrp = pm.group(em=True, n='%sJntCons%s_grp' %(self.elem, self.side))
		misc.snapTransform('parent', self.jnts[0], self.jntConsGrp, False, True)
		pm.parent(self.jnts[0], self.jntConsGrp)



	def createGeo(self):
		if not self.jnts:
			return

		for i in range(self.span):
			# circle = pm.circle(c=[0, 0, 0], nr=[0, 1, 0], sw=360, r=1.0, 
			# 	d=3, ut=0, tol=0.01, s=8, ch=False, n='%sLoft%s%s_crv' %(self.elem, str(i+1).zfill(2), self.side))[0]
			crossSecStr = controller.Controller(name='%sLoft%s%s_crv' %(self.elem, str(i+1).zfill(2), self.side), st=self.crossSecShape, 
											scale=1, axis='+%s'%self.jointOrient[0])
			crossSec = pm.PyNode(crossSecStr)

			crossSec.getShape(ni=True).rename('%sLoft%s%s_crvShape' %(self.elem, str(i+1).zfill(2), self.side))

			pm.connectAttr(self.scaleAttrs[i], crossSec.attr('scaleX'))
			pm.connectAttr(self.scaleAttrs[i], crossSec.attr('scaleY'))
			pm.connectAttr(self.scaleAttrs[i], crossSec.attr('scaleZ'))
			misc.snapTransform('parent', self.jnts[i], crossSec, False, True)
			pm.parent(crossSec, self.jnts[i])
			crossSec.attr('visibility').set(False)
			self.circles.append(crossSec)

		pm.nurbsToPolygonsPref(f=2, pt=0, un=self.span, vn=4)
		lofts = pm.loft(self.circles, n='%s%sLoft_nrbs' %(self.elem, self.side), po=self.createPolygon)
		self.surface = lofts[0]
		loftNode = lofts[1]
		loftNode.rename('%s%s_loft' %(self.elem, self.side))

		misc.lockAttr(self.surface, lock=True, t=True, r=True, s=True, v=True)

		


