import pymel.core as pm
import maya.OpenMaya as om
from nuTools import misc as misc
from nuTools import controller as ctr
import nuTools.rigTools.baseRig as baseRig
# import nuTools.rigTools.baseRig as baseRig

reload(misc)
reload(baseRig)

class DtlRig(baseRig.BaseRig):

	def __init__(self, parent=None, rivetMesh=None, skinMesh=None, tempLocs=[], ctrlColor='red', ctrlShape='cube',
				 animGrp=None, utilGrp=None, skinGrp=None, stillGrp=None, **kwargs):
		super(DtlRig, self).__init__(parent, animGrp=animGrp, utilGrp=utilGrp, skinGrp=skinGrp, stillGrp=stillGrp, **kwargs)

		self.rivetMesh = self.jntsArgs(rivetMesh)
		self.skinMesh = self.jntsArgs(skinMesh)
		self.tempLocs = self.jntsArgs(tempLocs)
		self.parent = parent

		self.ctrlColor = ctrlColor
		self.ctrlShape = ctrlShape

	def rig(self):
		size = [self.size, self.size, self.size]

		# rivet grp
		ctrlGrpName = '%sDtlCtrl%s_grp'%(self.elem, self.side)
		ctrlGrp = pm.group(n=ctrlGrpName, em=True)

		if self.parent: # orient to parent
			misc.snapTransform('orient', self.parent, ctrlGrp, mo=True, delete=False)
		if self.animGrp:
			pm.parent(ctrlGrp, self.animGrp)

		# jnt grp
		dtlJntGrpName = misc.nameObj('%sDtlJnt'%self.elem, self.side, 'grp')
		dtlJntGrp = pm.group(n=dtlJntGrpName, em=True)
		if self.utilGrp:
			pm.parent(dtlJntGrp, self.utilGrp)

		# still grp
		dtlRvtGrpName = misc.nameObj('%sDtlRvt'%self.elem, self.side, 'grp')
		dtlRvtGrp = pm.group(n=dtlRvtGrpName, em=True)
		if self.stillGrp:
			pm.parent(dtlRvtGrp, self.stillGrp)

		counter = 1
		# main loop
		for tempLoc in self.tempLocs:
			# counterStr = str(counter).zfill(1)
			tempLocName = tempLoc.nodeName()
			nameDict = misc.nameSplit(tempLocName)
			elem = nameDict['elem']
			side = nameDict['pos']

			#get cloest vtx on rivetMesh from locator position
			tempLocShp = tempLoc.getShape()
			locPos = pm.getAttr(tempLocShp.attr('worldPosition[0]'))
			closestVtx, closestFace = misc.getClosestComponentFromPos(self.rivetMesh, locPos)

			# closestVtxIndex = closestVtx.indices()[0]

			# vtxPos = closestVtx.getPosition('world')
			# cEdges = closestFace.connectedEdges()
			# print cEdges
			edgeIndexes = closestFace.getEdges()

			paramValue = 0.0
			edgeIndex = 0
			tmpCrvs = []
			cdist = 999999999.0
			for eIndx in edgeIndexes:
				edge = self.rivetMesh.e[eIndx]
				aPnt = edge.getPoint(0, 'world')
				bPnt = edge.getPoint(1, 'world')
				tmpCrv = pm.curve(d=1, p=[aPnt, bPnt])
				tmpCrvs.append(tmpCrv)

				mSel = om.MSelectionList()
				mSel.add(tmpCrv.longName())
				dag = om.MDagPath()
				mSel.getDagPath(0, dag)
				dag.extendToShape()

				fnCrv = om.MFnNurbsCurve(dag)
				pt = om.MPoint(locPos[0], locPos[1], locPos[2])
				# fnCrvs.append(fnCrv)

				# dist = fnCrv.distanceToPoint(pt, om.MSpace.kWorld)
				mutil = om.MScriptUtil()
				mutil.createFromDouble(0.0)
				paramPtr = mutil.asDoublePtr()
				fnCrv.closestPoint(pt, paramPtr, 1.0e-4, om.MSpace.kWorld)
				p = mutil.getDouble(paramPtr)
				ptOnCrv = om.MPoint()
				fnCrv.getPointAtParam(p, ptOnCrv, om.MSpace.kWorld)

				dist = pt.distanceTo(ptOnCrv)
				if dist < cdist:
					cdist = dist
					paramValue = p
					edgeIndex = eIndx
				# dists.append(dist)

			# ne = dists.index(min(dists))
			# edgeIndex = edgeIndexes[ne]
			# mutil = om.MScriptUtil()
			# mutil.createFromDouble(0.0)
			# paramPtr = mutil.asDoublePtr()
			# fnCrvs[ne].closestPoint(pt, paramPtr, 1.0e-4, om.MSpace.kWorld)
			# paramValue = mutil.getDouble(paramPtr)

			pm.delete(tmpCrvs)
			# for i in [0, 1]:
			# 	pos = cEdges.getPoint(1)
			# 	if pos == vtxPos:
			# 		paramValue = i
			
			#create and self.elem nodes, grps
			ctrlName = '%sDtl%s_ctrl'%(elem, side)
			ctrl = ctr.Controller(n=ctrlName, st=self.ctrlShape, scale=self.size)
			ctrl.setColor(self.ctrlColor)
			ctrl.lockAttr(v=True)
			ctrl.hideAttr(v=True)
			
			# dtGrpName = '%sDtlFixDt%s_grp'%(elem, side)
			# dtGrp = pm.group(n=dtGrpName, em=True)

			# rivetGrpName = '%sDtlCtrl%s_grp'%(elem, side)
			# rivetGrp = pm.group(n=rivetGrpName, em=True)

			dtGrp = misc.zgrp(ctrl, element='Inv', suffix='grp')[0]

			rivetGrp = misc.zgrp(dtGrp, element='Zro', suffix='grp')[0]

			# pm.parent(ctrl, dtGrp)
			# pm.parent(dtGrp, rivetGrp)
			pm.parent(rivetGrp, ctrlGrp)

			mdvNodeName = '%sDtlFixDt%s_mdv'%(elem, side)
			dtFixMdv = pm.createNode('multiplyDivide', n=mdvNodeName)
			dtFixMdv.input2X.set(-1)
			dtFixMdv.input2Y.set(-1)
			dtFixMdv.input2Z.set(-1)

			cfmeName = '%sDtl%s_cfme'%(elem, side)
			pociName = '%sDtl%s_poci'%(elem, side)
			rivetLocName = '%sDtl%s_loc'%(elem, side)

			cfmeNode = pm.createNode('curveFromMeshEdge', n=cfmeName)
			pociNode = pm.createNode('pointOnCurveInfo', n=pociName)
			rivetLoc = pm.spaceLocator(n=rivetLocName)

			cfmeNode.edgeIndex[0].set(edgeIndex)
			pociNode.parameter.set(paramValue)
			pociNode.turnOnPercentage.set(True)
			rivetLoc.localScale.set(size)
			pm.parent(rivetLoc, dtlRvtGrp)

			jntName = '%sDtl%s_jnt'%(elem, side)
			jnt = pm.createNode('joint', n=jntName)
			jnt.radius.set(self.size)

			jntZGrp = misc.zgrp(jnt, element='Zro', suffix='grp')
			pm.parent(jntZGrp, dtlJntGrp)

			#connect
			pm.connectAttr(ctrl.translate, dtFixMdv.input1)
			pm.connectAttr(dtFixMdv.output, dtGrp.translate)

			pm.connectAttr(self.rivetMesh.worldMesh[0], cfmeNode.inputMesh)
			pm.connectAttr(cfmeNode.outputCurve, pociNode.inputCurve)
			pm.connectAttr(pociNode.position, rivetLoc.translate)

			pm.connectAttr(ctrl.translate, jnt.translate)
			pm.connectAttr(ctrl.rotate, jnt.rotate)
			pm.connectAttr(ctrl.scale, jnt.scale)

			#point constraint
			misc.snapTransform('point', rivetLoc, rivetGrp, mo=False, delete=False)
			misc.snapTransform('orient', tempLoc, rivetGrp, mo=False, delete=True)


			# skinMeshVert = self.skinMesh.vtx[closestVtxIndex]
			# skinMeshPos = skinMeshVert.getPosition('world')
			# pm.xform(jntZGrp, ws=True, t=skinMeshPos)
			misc.snapTransform('point', rivetLoc, jntZGrp, mo=False, delete=True)
			misc.snapTransform('orient', tempLoc, jntZGrp, mo=False, delete=True)

			
			#delete tmpLoc
			try:
				pm.delete(tempLoc)
			except Exception:
				pass

			#inc counter
			counter += 1







			

