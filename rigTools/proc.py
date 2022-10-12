import pymel.core as pm
import maya.OpenMaya as om
from nuTools import misc 
from nuTools import controller
from nuTools import naming
reload(misc)
reload(controller)
reload(naming)

import math, random

def invSkinJntRig(step=1, surf=None, mesh=None, rootJnt=None, scaleParent=None, elem='lips', side='', scale=1.0):
	'''
		Create invert skin joint rig that attaches to the mesh base on point on NURBS surface.
		@param
			step(int) = Increment step for parameterV attribute on pointOnSurfaceInfo node.
			surf(pm.nt.NurbsSurface) = The NURBS surface's transform. This surface will be wrapped on the deforming mesh.
			mesh(pm.nt.Mesh) = The mesh that joints will be deforming.
			rootJnt(pm.nt.Joint) = The joint to be binded on 'mesh' that will be the place holder for weights.
			scaleParent(pm.nt.Transform) = The transform the joints will be scaled with. (anim_grp)
			elem(str) = Naming string.
			side(str) = Naming string.
			scale(float) = Scale for joint radius and controllers. 
	'''

	if not surf or not mesh or not  rootJnt or not scaleParent:
		sels = pm.selected()
		surf = sels[0]
		mesh = sels[1]
		scaleParent = sels[2]
		rootJnt = sels[2]
		if not surf or not mesh or not rootJnt or not scaleParent:
			return

	surfShp = surf.getShape(ni=True)
	num = surfShp.spansUV.get()[1]
	# print num
	jnts, invZgrps, posis = [], [], []

	for i in xrange(0, num, step):
		# create joint
		jnt = pm.createNode('joint', n=naming.NAME((elem, (i+1)), side, naming.JNT))
		jnt.radius.set(scale*0.2)
		# create ctrl, invZro grp and zro grp
		ctrl = controller.Controller(n=naming.NAME((elem, (i+1)), side, naming.CTRL), 
				shapeType='sphere', scale=scale, axis='+y')
		gctrl = ctrl.addGimbal()

		misc.lockAttr(ctrl, lock=True, t=False, r=False, s=False, v=True)
		ctrl.setColor('lightBlue')

		invZgrp = misc.zgrp(ctrl, suffix='grp', element='InvZro', preserveHeirachy=True)[0]
		zgrp = misc.zgrp(invZgrp, suffix='grp', element='Zro', preserveHeirachy=True)[0]
		posi = pm.createNode('pointOnSurfaceInfo', n=naming.NAME((elem, (i+1)), side, naming.POSI))
		
		aimNode = pm.createNode('aimConstraint', n=naming.NAME((elem, (i+1)), side, naming.AIMCON))
		aimNode.aimVectorZ.set(1.0)
		aimNode.aimVectorX.set(0.0)
		aimNode.aimVectorY.set(0.0)
		aimNode.aimVectorZ.set(1.0)
		aimNode.upVectorX.set(0.0)
		aimNode.upVectorY.set(1.0)
		aimNode.upVectorZ.set(0.0)
		aimNode.worldUpType.set(3)

		pm.parent(aimNode, zgrp)
		pm.parent(jnt, gctrl)
		pm.scaleConstraint(scaleParent, zgrp, mo=True)

		# connect
		pm.connectAttr(posi.tangentU, aimNode.worldUpVector)
		pm.connectAttr(posi.normal, aimNode.target[0].targetTranslate)
		pm.connectAttr(aimNode.constraintRotateX, zgrp.rotateX)
		pm.connectAttr(aimNode.constraintRotateY, zgrp.rotateY)
		pm.connectAttr(aimNode.constraintRotateZ, zgrp.rotateZ)
		pm.connectAttr(surfShp.worldSpace[0], posi.inputSurface)
		pm.connectAttr(posi.position, zgrp.translate)

		jnts.append(jnt)
		invZgrps.append(invZgrp)
		posis.append(posi)

		uattr = misc.addNumAttr(surf, 'pos_u%s' %(i+1), 'float', dv=0.15)
		vattr = misc.addNumAttr(surfShp, 'pos_v%s' %(i+1), 'float', dv=float(i))
		pm.connectAttr(uattr, posi.parameterU)
		pm.connectAttr(vattr, posi.parameterV)
	

	jnts.append(rootJnt)

	# get root joint group
	rootJntZgrp = rootJnt.getParent()
	if not rootJntZgrp:
		rootJntZgrp = misc.zgrp(rootJnt)[0]
	invZgrps.append(rootJntZgrp)

	# bind the mesh, find skinCluster node
	pm.skinCluster(jnts, mesh, tsb=True)
	skc = misc.findRelatedSkinCluster(mesh)

	# connect worldInverseMatrix of the group above the joint to the skinCluster's bindPreMatrix attribute
	# on the coresponding index
	for jnt, grp in zip(jnts, invZgrps):
		cons = jnt.worldMatrix[0].outputs(type='skinCluster', p=True)
		indx = None
		for c in cons:
			if c.node() == skc:
				indx = c.logicalIndex()
				break
		pm.connectAttr(grp.worldInverseMatrix[0], skc.bindPreMatrix[indx])

def rbbnMuscle(startJnt=None, endJnt=None, createCtrl=False, elem='', side='', axis='y'):
	if not startJnt or not endJnt:
		sels = misc.getSel(selType='joint', num=2)
		startJnt = sels[0]
		endJnt = sels[1]
		if not startJnt or not endJnt:
			return

	# if no elem provided, try splitting start joint name for elem
	if not elem:
		import re
		elem = misc.nameSplit(startJnt)['elem']
		mname = re.search(r"(\d+)", elem)
		try:
			endDigit = mname.group()
			elem = elem.replace(endDigit, '')
		except:
			pass

	# get distance from start to end
	dist = misc.getDistanceFromPosition(startJnt.getTranslation('world'), endJnt.getTranslation('world'))

	# create groups
	startGrp = pm.group(em=True, n=misc.nameObj('%sRbbnMuscleStart' %elem, side, naming.GRP))
	endGrp = pm.group(em=True, n=misc.nameObj('%sRbbnMuscleEnd' %elem, side, naming.GRP))
	startAimGrp = pm.group(em=True, n=misc.nameObj('%sRbbnMuscleStartAim' %elem, side, naming.GRP))
	endAimGrp = pm.group(em=True, n=misc.nameObj('%sRbbnMuscleEndAim' %elem, side, naming.GRP))
	startUpGrp = pm.group(em=True, n=misc.nameObj('%sRbbnMuscleStartUp' %elem, side, naming.GRP))
	endUpGrp = pm.group(em=True, n=misc.nameObj('%sRbbnMuscleEndUp' %elem, side, naming.GRP))
	mConsGrp = pm.group(em=True, n=misc.nameObj('%sRbbnMuscleCons' %elem, side, naming.GRP))
	mZroGrp = pm.group(em=True, n=misc.nameObj('%sRbbnMuscleZro' %elem, side, naming.GRP))

	# create reverse node for constraint weights
	weightRev = pm.createNode('reverse', n=misc.nameObj('%sRbbnMuscleConsWeight' %elem, side, naming.REV))

	# store radius
	rad = startJnt.radius.get() 

	# duplicate joints
	startBaseJnt = pm.duplicate(startJnt, po=True, n=misc.nameObj('%sRbbnMuscleStartBase' %elem, side, naming.JNT))[0]
	startTipJnt = pm.duplicate(startJnt, po=True, n=misc.nameObj('%sRbbnMuscleStartTip' %elem, side, naming.JNT))[0]
	mJnt = pm.duplicate(startJnt, po=True, n=misc.nameObj('%sRbbnMuscle' %elem, side, 'jnt'))[0]
	endBaseJnt = pm.duplicate(endJnt, po=True, n=misc.nameObj('%sRbbnMuscleEndBase' %elem, side, naming.JNT))[0]
	endTipJnt = pm.duplicate(endJnt, po=True, n=misc.nameObj('%sRbbnMuscleEndTip' %elem, side, naming.JNT))[0]

	pm.parent(mZroGrp, mConsGrp)
	pm.parent(startTipJnt, startBaseJnt)
	pm.parent(endTipJnt, endBaseJnt)
	pm.parent([startAimGrp, startUpGrp], startGrp)
	pm.parent([endAimGrp, endUpGrp], endGrp)

	misc.snapTransform('parent', startJnt, startGrp, False, True)
	misc.snapTransform('parent', endJnt, endGrp, False, True)
	misc.snapTransform('parent', startJnt, mConsGrp, False, True)

	pm.parent(mJnt, mZroGrp)
	pm.parent(startBaseJnt, startAimGrp)
	pm.parent(endBaseJnt, endAimGrp)
	pm.parent(startGrp, startJnt)
	pm.parent(endGrp, endJnt)

	vecDict = {'x':([1, 0, 0], [0, 1, 0]), 'y':([0, 1, 0], [1, 0, 0]), 'z':([0, 0, 1], [1, 0, 0])}
	aimVec = pm.dt.Vector(vecDict[axis][0])
	upVec = pm.dt.Vector(vecDict[axis][1])
	if side == 'RGT':
		aimVec = aimVec * -1
	invAimVec = aimVec * -1

	pm.move(startUpGrp, upVec*0.1, r=True, os=True)
	pm.move(endUpGrp, upVec*0.1, r=True, os=True)
	pm.move(startTipJnt, (aimVec*(dist*0.1)), r=True, os=True)
	pm.move(endTipJnt, (aimVec*(dist*-0.1)), r=True, os=True)

	# create aim constraint
	startAimNode = pm.aimConstraint(endJnt, startAimGrp, aimVector=aimVec, upVector=upVec, worldUpType='object', worldUpObject=startUpGrp)
	endAimNode = pm.aimConstraint(startJnt, endAimGrp, aimVector=invAimVec, upVector=upVec, worldUpType='object', worldUpObject=endUpGrp)

	# point constraint mJnt to be exactly inbetween startJnt and endJnt
	pointCons = pm.pointConstraint([startBaseJnt, endBaseJnt], mConsGrp)

	wAttr = misc.addNumAttr(mJnt, 'weight', 'float', min=0.0, max=1.0, dv=0.5)
	pm.connectAttr(wAttr, weightRev.inputX)
	pm.connectAttr(weightRev.outputX, pointCons.attr('%sW0' %startBaseJnt.nodeName()))
	pm.connectAttr(wAttr, pointCons.attr('%sW1' %endBaseJnt.nodeName()))

	pm.parent(mConsGrp, startBaseJnt)

	# set radius
	jnts = [startBaseJnt, startTipJnt, mJnt, endBaseJnt, endTipJnt]
	for j in jnts:
		j.radius.set(rad*1.1)
	startJnt.radius.set(rad*0.1)
	endJnt.radius.set(rad*0.1)

	# create ctrl
	if createCtrl == True:
		ctrl = controller.Controller(name=misc.nameObj(elem, side, naming.CTRL), shapeType='sphere', scale=rad*1.2, axis='+y')
		ctrl.setColor('pink')
		misc.lockAttr(mJnt, t=False, r=False, s=False, v=True, radius=True)
		misc.hideAttr(mJnt, t=False, r=False, s=False, v=True, radius=True)
		shp = ctrl.getShape(ni=True)
		pm.parent(shp, mJnt, r=True, s=True)
		pm.delete(ctrl)

	pm.select(mJnt, r=True)

# #------------------------------------------------------------------------------------------------------------
# #------------------------------------------btwJnt------------------------------------------------------------------
#     print "# Generate >> BtwJnt"
#     ## btwJnt >> Head
#     proc.btwJnt(jnts=['Neck5RbnDtl_Jnt', 'Head_Jnt', 'HeadEnd_Jnt'],axis='y', pointConstraint=True)
#     proc.btwJnt(jnts=['Spine5_Jnt', 'Neck_Jnt', 'Neck1RbnDtl_Jnt'],axis='y', pointConstraint=True)
#     proc.btwJnt(jnts=['Spine5_Jnt', 'Clav_L_Jnt', 'UpArm_L_Jnt'],axis='y', pointConstraint=True)
#     proc.btwJnt(jnts=['Spine5_Jnt', 'Clav_R_Jnt', 'UpArm_R_Jnt'],axis='y', pointConstraint=True)
#     proc.btwJnt(jnts=['UpArm5RbnDtl_L_Jnt', 'Forearm_L_Jnt', 'Forearm1RbnDtl_L_Jnt'],axis='y', pointConstraint=False)
#     proc.btwJnt(jnts=['UpArm5RbnDtl_R_Jnt', 'Forearm_R_Jnt', 'Forearm1RbnDtl_R_Jnt'],axis='y', pointConstraint=False)
#     proc.btwJnt(jnts=['Forearm5RbnDtl_L_Jnt', 'Wrist_L_Jnt', 'Hand_L_Jnt'],axis='y', pointConstraint=True)
#     proc.btwJnt(jnts=['Forearm5RbnDtl_R_Jnt', 'Wrist_R_Jnt', 'Hand_R_Jnt'],axis='y', pointConstraint=True)
#     proc.btwJnt(jnts=['Pelvis_Jnt', 'UpLeg_L_Jnt', 'UpLeg1RbnDtl_L_Jnt'],axis='y', pointConstraint=True)
#     proc.btwJnt(jnts=['Pelvis_Jnt', 'UpLeg_R_Jnt', 'UpLeg1RbnDtl_R_Jnt'],axis='y', pointConstraint=True)
#     proc.btwJnt(jnts=['UpLeg5RbnDtl_L_Jnt', 'LowLeg_L_Jnt', 'LowLeg1RbnDtl_L_Jnt'],axis='y', pointConstraint=False)
#     proc.btwJnt(jnts=['UpLeg5RbnDtl_R_Jnt', 'LowLeg_R_Jnt', 'LowLeg1RbnDtl_R_Jnt'],axis='y', pointConstraint=False)
#     proc.btwJnt(jnts=['Spine4Sca_Jnt', 'Spine5_Jnt', 'Neck_Jnt'],axis='y', pointConstraint=True)


def btwJnt(jnts=[], axis='y', pointConstraint=True, elem='', side='',):
	if not jnts or len(jnts) != 3:
		jnts = misc.getSel(num=3, selType='joint')
		if not jnts:
			return
	parentJnt = jnts[0]
	startJnt = jnts[1]
	endJnt = jnts[2]

	if isinstance(parentJnt, (str, unicode)):
		parentJnt = pm.PyNode(parentJnt)
	if isinstance(startJnt, (str, unicode)):
		startJnt = pm.PyNode(startJnt)
	if isinstance(endJnt, (str, unicode)):
		endJnt = pm.PyNode(endJnt)

	nameElems = misc.nameSplit(startJnt.nodeName())
	if not elem:
		elem = nameElems['elem']
	if not side:
		side = nameElems['pos']

	rad = startJnt.radius.get()

	# print side, 'side'
	allBtwJntGrp = pm.group(em=True, n=naming.NAME((elem, 'BtwAll'), side, naming.GRP))
	allBtwJntMove = pm.group(em=True, n=naming.NAME((elem, 'BtwAllMove'), side, naming.GRP))
	allBtwJntHide = pm.group(em=True, n=naming.NAME((elem, 'BtwHide'), side, naming.GRP))
	upGrp = pm.group(em=True, n=naming.NAME((elem, 'BtwUp'), side, naming.GRP))
	# pole = pm.spaceLocator()
	# pole.rename('%sBtwPole%s_loc' %(elem, side))

	mutiScalePositive = pm.createNode("multiplyDivide", n=naming.NAME((elem, 'MulScalePos'), side, naming.MDV))
	mutiScaleNegative = pm.createNode("multiplyDivide", n=naming.NAME((elem, 'MulScaleNeg'), side, naming.MDV))
	condScalePosOnOff = pm.createNode("condition", n=naming.NAME((elem, 'MulScalePosOnOff'), side, naming.COND))
	condScaleNegOnOff = pm.createNode("condition", n=naming.NAME((elem, 'MulScaleNegOnOff'), side, naming.COND))
	clampScalePositive = pm.createNode("clamp", n=naming.NAME((elem, 'ClampScalePos'), side, naming.CMP))
	clampScaleNegative = pm.createNode("clamp", n=naming.NAME((elem, 'ClampScaleNeg'), side, naming.CMP))
	plusPosiNegaScale = pm.createNode("plusMinusAverage", n=naming.NAME((elem, 'PlusPosNegScale'), side, naming.PMA))
	mutiScaleMutiPlus = pm.createNode("multiplyDivide", n=naming.NAME((elem, 'MulScaleMutiPlus'), side, naming.MDV))
	addDoubleScaleOne = pm.createNode("addDoubleLinear", n=naming.NAME((elem, 'DoubleScaleA'), side, naming.ADL))
	addDoubleScaleTwo = pm.createNode("addDoubleLinear", n=naming.NAME((elem, 'DoubleScaleB'), side, naming.ADL))
	reveseDriverVoid = pm.createNode("reverse", n=naming.NAME((elem, 'DriveVoid'), side, naming.REV))
	clampScaleLimit = pm.createNode("clamp", n=naming.NAME((elem, 'ClampScaleLimit'), side, naming.CMP))

	jntBtw = pm.duplicate(startJnt, po=True, n=naming.NAME((elem, 'Btw'), side, naming.JNT))[0]
	jntBtwEnd = pm.duplicate(startJnt, po=True, n=naming.NAME((elem, 'BtwEnd'), side, naming.JNT))[0]
	jntBtwIK = pm.duplicate(startJnt, po=True, n=naming.NAME((elem, 'BtwIk'), side, naming.JNT))[0]
	jntBtwIKEnd = pm.duplicate(startJnt, po=True, n=naming.NAME((elem, 'BtwEndIk'), side, naming.JNT))[0]

	jntAim = pm.duplicate(startJnt, po=True, n=naming.NAME((elem, 'BtwAim'), side, naming.JNT))[0]
	jntAimEnd = pm.duplicate(startJnt, po=True, n=naming.NAME((elem, 'BtwAimEnd'), side, naming.JNT))[0]
	jntVoid = pm.duplicate(startJnt, po=True, n=naming.NAME((elem, 'BtwVoid'), side, naming.JNT))[0]
	jntVoidEnd = pm.duplicate(startJnt, po=True, n=naming.NAME((elem, 'BtwVoidEnd'), side, naming.JNT))[0]

	allJntDup = [jntBtw, jntAim, jntVoid, jntBtwIK]
	allJntEndDup = [jntBtwEnd, jntAimEnd, jntVoidEnd, jntBtwIKEnd]

	misc.unlockChannelbox(allJntDup)
	misc.unlockChannelbox(allJntEndDup)
	for s, e in zip(allJntDup, allJntEndDup):
		s.radius.unlock()
		s.radius.set(rad*1.5)
		e.radius.unlock()
		e.radius.set(rad*0.5)

	distAimAndVoid = misc.getDistanceFromPosition(aPos=startJnt.getTranslation('world'), bPos=endJnt.getTranslation('world'))

	mutiScalePositive.input2X.set(-0.01)
	mutiScalePositive.input2Y.set(-0.01)
	mutiScalePositive.input2Z.set(-0.01)
	
	mutiScaleNegative.input2X.set(0.01)
	mutiScaleNegative.input2Y.set(0.01)
	mutiScaleNegative.input2Z.set(0.01)

	condScalePosOnOff.st.set(1)
	condScalePosOnOff.ctr.set(-0.001)
	condScalePosOnOff.cfr.set(0)

	condScaleNegOnOff.st.set(1)
	condScaleNegOnOff.ctr.set(0.001)
	condScaleNegOnOff.cfr.set(0)
	
	clampScalePositive.maxR.set(180)
	clampScalePositive.maxG.set(180)
	clampScalePositive.maxB.set(180)

	clampScaleNegative.maxR.set(180)
	clampScaleNegative.maxG.set(180)
	clampScaleNegative.maxB.set(180)
	
	addDoubleScaleOne.input1.set(1)
	addDoubleScaleTwo.input1.set(1)

	pm.parent(jntBtwEnd, jntBtw)
	pm.parent(jntAimEnd, jntAim)
	pm.parent(jntVoidEnd, jntVoid)
	pm.parent(jntBtwIKEnd, jntBtwIK)

	# pm.parent([upGrp, pole], allBtwJntHide)
	pm.parent(upGrp, allBtwJntHide)
	pm.parent(allBtwJntHide, allBtwJntMove)
	pm.parent(allBtwJntMove, allBtwJntGrp)

	pm.delete(pm.parentConstraint(startJnt, allBtwJntGrp))
	pm.parent(jntBtw, allBtwJntMove)
	# pm.parent([jntBtwIK, jntAim, jntVoid, jntVoidAim], allBtwJntHide)
	pm.parent([jntBtwIK, jntAim, jntVoid], allBtwJntHide)

	moveSide = 2
	mult = 1
	tmpEndJnt = endJnt.duplicate(po=True)[0]
	misc.unlockChannelbox(tmpEndJnt)
	pm.parent(tmpEndJnt, startJnt)

	objSpaceTr = tmpEndJnt.getTranslation('object')
	pm.delete(tmpEndJnt)

	exec('aimTr = objSpaceTr.%s' %axis[-1])

	if aimTr <= 0.0:
		mult = -1

	axisUpDict = {'x':'y', 'y':'x', 'z':'x'}

	pm.parent(allBtwJntGrp, parentJnt)

	tMove = 't%s' %axis
	aimV = misc.vectorStr(axis) * mult
	upV = misc.vectorStr(axisUpDict[axis])

	#pm.parent(allBtwJntMove, startJnt)
	allBtwJntMove.attr(tMove).set((distAimAndVoid*-0.334*mult))

	if pointConstraint == True:
		# print startJnt,allBtwJntGrp
		pm.pointConstraint(startJnt, allBtwJntGrp)
	distanceBtwEnd = misc.getDistanceFromPosition(aPos=jntBtw.getTranslation('world'), bPos=startJnt.getTranslation('world'))

	for jnt in (jntBtwEnd, jntAimEnd, jntVoidEnd, jntBtwIKEnd):
		jnt.attr(tMove).set((distanceBtwEnd*moveSide*mult))

	misc.addNumAttr(jntBtw, 'aimBtw', 'float', min=0, max=1, dv=0.5)
	misc.addNumAttr(jntBtw, 'scaleBtw', 'float', dv=2)
	misc.addNumAttr(jntBtw, 'scaleLimit', 'float', dv=2)
	misc.addNumAttr(jntBtw, 'posOnOff', 'bool', min=0, max=1, dv=1)
	misc.addNumAttr(jntBtw, 'negOnOff', 'bool', min=0, max=1, dv=1)

	pm.connectAttr(jntBtw.aimBtw, reveseDriverVoid.inputX)

	for a in 'XYZ':
		pm.connectAttr(jntBtw.scaleBtw, mutiScaleMutiPlus.attr('input2%s' %a))

	for s, e in zip(allJntDup, allJntEndDup):
		if not e.inverseScale.isConnected():
			pm.connectAttr(s.scale, e.inverseScale, f=True)

	ik, eff = pm.ikHandle(sol='ikRPsolver', s='sticky', sj=jntBtwIK, ee=jntBtwIKEnd)
	ik.rename(naming.NAME((elem, 'Btw'), side, naming.IKHNDL))
	eff.rename(naming.NAME((elem, 'BtwEnd'), side, naming.EFF))

	# pm.poleVectorConstraint(pole, ik)
	ik.poleVector.set([0, 0, 0])
	ik.poleVector.lock()
	ikPoint = pm.pointConstraint([jntAimEnd, jntVoidEnd], ik)

	allBtwJntHide.visibility.set(False)
	pm.parent(ik, allBtwJntHide)

	aimAim = pm.aimConstraint(endJnt, jntAim, aimVector=aimV, upVector=upV, worldUpType='object', worldUpObject=upGrp)
	# aimVoid = pm.aimConstraint(jntVoidAim, jntVoid, aimVector=aimV, upVector=upV, worldUpType='object', worldUpObject=upGrp)

	pm.connectAttr(jntBtw.aimBtw, ikPoint.attr('%sW0' %jntAimEnd.nodeName()))
	pm.connectAttr(reveseDriverVoid.outputX, ikPoint.attr('%sW1' %jntVoidEnd.nodeName()))

	pm.connectAttr(jntBtw.posOnOff, condScalePosOnOff.ft)
	pm.connectAttr(jntBtw.negOnOff, condScaleNegOnOff.ft)
	
	for a in 'xyz':
		upperA = a.upper()
		pm.connectAttr(jntBtwIK.attr('r%s' %a), mutiScalePositive.attr('input1%s' %upperA))
		pm.connectAttr(jntBtwIK.attr('r%s' %a), mutiScaleNegative.attr('input1%s' %upperA))

		pm.connectAttr(condScalePosOnOff.ocr, mutiScalePositive.attr('input2%s' %upperA))
		pm.connectAttr(condScaleNegOnOff.ocr, mutiScaleNegative.attr('input2%s' %upperA))

	pm.connectAttr(mutiScalePositive.output, clampScalePositive.input)
	pm.connectAttr(mutiScaleNegative.output, clampScaleNegative.input)
	pm.connectAttr(clampScalePositive.output, plusPosiNegaScale.input3D[0])
	pm.connectAttr(clampScaleNegative.output, plusPosiNegaScale.input3D[1])
	pm.connectAttr(plusPosiNegaScale.output3D, mutiScaleMutiPlus.input1)

	remAxis = 'xyz'.replace(axis, '')

	pm.connectAttr(mutiScaleMutiPlus.attr('output%s' %remAxis[0].upper()), addDoubleScaleTwo.input2)
	pm.connectAttr(mutiScaleMutiPlus.attr('output%s' %remAxis[1].upper()), addDoubleScaleOne.input2)

	pm.connectAttr(jntBtw.scaleLimit, clampScaleLimit.maxR)
	pm.connectAttr(jntBtw.scaleLimit, clampScaleLimit.maxG)
	pm.connectAttr(addDoubleScaleOne.output, clampScaleLimit.inputR)
	pm.connectAttr(addDoubleScaleTwo.output, clampScaleLimit.inputG)
	pm.connectAttr(clampScaleLimit.outputR,	jntBtw.attr('s%s' %remAxis[0]))
	pm.connectAttr(clampScaleLimit.outputG,	jntBtw.attr('s%s' %remAxis[1]))

	pm.makeIdentity(jntBtwIK, apply=True, t=True, r=True, s=False)
	pm.delete(pm.parentConstraint(jntBtwIK, jntBtw))
	pm.makeIdentity(jntBtw, apply=True, t=True, r=True, s=False)
	pm.parentConstraint(jntBtwIK, jntBtw)
	
	##-- Generate btwAutoShape
	##-- auto Shape Pos
	btwShapeCmp = pm.createNode("clamp", n=naming.NAME((elem, 'MulScaleAutoPos'), side, naming.CMP))
	btwShapeMdv = pm.createNode("multiplyDivide", n=naming.NAME((elem, 'MulScaleAutoPos'), side, naming.MDV))
	btwShapePma = pm.createNode("plusMinusAverage", n=naming.NAME((elem, 'PlusPosNegAutoScale'), side, naming.PMA))

	## -- 
	btwShapeCmp.minG.set(-70)
	btwShapeCmp.maxR.set(70)
	btwShapeCmp.maxB.set(70)
	btwShapeMdv.input2X.set(0.007)
	btwShapeMdv.input2Y.set(-0.01)
	btwShapeMdv.input2Z.set(0.015)

	## connect 1 line
	pm.connectAttr(parentJnt.rx, btwShapeCmp.inputR)
	pm.connectAttr(parentJnt.rx, btwShapeCmp.inputG)
	pm.connectAttr(parentJnt.rz, btwShapeCmp.inputB)

	pm.connectAttr(btwShapeCmp.outputR, btwShapeMdv.input1X)
	pm.connectAttr(btwShapeCmp.outputG, btwShapeMdv.input1Y)
	pm.connectAttr(btwShapeCmp.outputB, btwShapeMdv.input1Z)

	pm.connectAttr(btwShapeMdv.outputX, btwShapePma.input2D[0].input2Dx)
	pm.connectAttr(btwShapeMdv.outputY, btwShapePma.input2D[1].input2Dx)
	pm.connectAttr(btwShapeMdv.outputZ, btwShapePma.input2D[2].input2Dx)

	pm.parent(allBtwJntGrp, parentJnt)
	# lock hide unused attrs
	jntBtw.translate.lock()
	jntBtw.rotate.lock()
	jntBtw.scale.lock()
	jntBtw.visibility.lock()

def btwJntPelvis(jnts=[], axis='y', pointConstraint=True, elem='', side=''):

	# print jnts
	if not jnts or len(jnts) != 3:
		jnts = misc.getSel(num=3, selType='joint')
		if not jnts:
			return
	parentJnt = jnts[0]
	startJnt = jnts[1]
	endJnt = jnts[2]
	if isinstance(parentJnt, (str, unicode)):
		parentJnt = pm.PyNode(parentJnt)
	if isinstance(startJnt, (str, unicode)):
		startJnt = pm.PyNode(startJnt)
	if isinstance(endJnt, (str, unicode)):
		endJnt = pm.PyNode(endJnt)
	nameElems = misc.nameSplit(startJnt.nodeName())
	if not elem:
		elem = nameElems['elem']
	if not side:
		side = nameElems['pos']

	rad = startJnt.radius.get()

	# print side, 'side'
	allBtwJntGrp = pm.group(em=True, n=naming.NAME((elem, 'BtwAll'), side, naming.GRP))
	allBtwJntMove = pm.group(em=True, n=naming.NAME((elem, 'BtwAllMove'), side, naming.GRP))
	allBtwJntHide = pm.group(em=True, n=naming.NAME((elem, 'BtwHide'), side, naming.GRP))
	upGrp = pm.group(em=True, n=naming.NAME((elem, 'BtwUp'), side, naming.GRP))
	# pole = pm.spaceLocator()
	# pole.rename('%sBtwPole%s_loc' %(elem, side))

	mutiScalePositive = pm.createNode("multiplyDivide", n=naming.NAME((elem, 'MulScalePos'), side, naming.MDV))
	mutiScaleNegative = pm.createNode("multiplyDivide", n=naming.NAME((elem, 'MulScaleNeg'), side, naming.MDV))
	condScalePosOnOff = pm.createNode("condition", n=naming.NAME((elem, 'MulScalePosOnOff'), side, naming.COND))
	condScaleNegOnOff = pm.createNode("condition", n=naming.NAME((elem, 'MulScaleNegOnOff'), side, naming.COND))
	clampScalePositive = pm.createNode("clamp", n=naming.NAME((elem, 'ClampScalePos'), side, naming.CMP))
	clampScaleNegative = pm.createNode("clamp", n=naming.NAME((elem, 'ClampScaleNeg'), side, naming.CMP))
	plusPosiNegaScale = pm.createNode("plusMinusAverage", n=naming.NAME((elem, 'PlusPosNegScale'), side, naming.PMA))
	mutiScaleMutiPlus = pm.createNode("multiplyDivide", n=naming.NAME((elem, 'MulScaleMutiPlus'), side, naming.MDV))
	addDoubleScaleOne = pm.createNode("addDoubleLinear", n=naming.NAME((elem, 'DoubleScaleA'), side, naming.ADL))
	addDoubleScaleTwo = pm.createNode("addDoubleLinear", n=naming.NAME((elem, 'DoubleScaleB'), side, naming.ADL))
	reveseDriverVoid = pm.createNode("reverse", n=naming.NAME((elem, 'DriveVoid'), side, naming.REV))
	clampScaleLimit = pm.createNode("clamp", n=naming.NAME((elem, 'ClampScaleLimit'), side, naming.CMP))

	jntBtw = pm.duplicate(startJnt, po=True, n=naming.NAME((elem, 'Btw'), side, naming.JNT))[0]
	jntBtwEnd = pm.duplicate(startJnt, po=True, n=naming.NAME((elem, 'BtwEnd'), side, naming.JNT))[0]
	jntBtwIK = pm.duplicate(startJnt, po=True, n=naming.NAME((elem, 'BtwIk'), side, naming.JNT))[0]
	jntBtwIKEnd = pm.duplicate(startJnt, po=True, n=naming.NAME((elem, 'BtwEndIk'), side, naming.JNT))[0]

	jntAim = pm.duplicate(startJnt, po=True, n=naming.NAME((elem, 'BtwAim'), side, naming.JNT))[0]
	jntAimEnd = pm.duplicate(startJnt, po=True, n=naming.NAME((elem, 'BtwAimEnd'), side, naming.JNT))[0]
	jntVoid = pm.duplicate(startJnt, po=True, n=naming.NAME((elem, 'BtwVoid'), side, naming.JNT))[0]
	jntVoidEnd = pm.duplicate(startJnt, po=True, n=naming.NAME((elem, 'BtwVoidEnd'), side, naming.JNT))[0]

	allJntDup = [jntBtw, jntAim, jntVoid, jntBtwIK]
	allJntEndDup = [jntBtwEnd, jntAimEnd, jntVoidEnd, jntBtwIKEnd]

	misc.unlockChannelbox(allJntDup)
	misc.unlockChannelbox(allJntEndDup)
	for s, e in zip(allJntDup, allJntEndDup):
		s.radius.unlock()
		s.radius.set(rad*1.5)
		e.radius.unlock()
		e.radius.set(rad*0.5)

	distAimAndVoid = misc.getDistanceFromPosition(aPos=startJnt.getTranslation('world'), bPos=endJnt.getTranslation('world'))

	mutiScalePositive.input2X.set(-0.01)
	mutiScalePositive.input2Y.set(-0.01)
	mutiScalePositive.input2Z.set(-0.01)
	
	mutiScaleNegative.input2X.set(0.01)
	mutiScaleNegative.input2Y.set(0.01)
	mutiScaleNegative.input2Z.set(0.01)

	condScalePosOnOff.st.set(1)
	condScalePosOnOff.ctr.set(-0.001)
	condScalePosOnOff.cfr.set(0)

	condScaleNegOnOff.st.set(1)
	condScaleNegOnOff.ctr.set(0.001)
	condScaleNegOnOff.cfr.set(0)
	
	clampScalePositive.maxR.set(180)
	clampScalePositive.maxG.set(180)
	clampScalePositive.maxB.set(180)

	clampScaleNegative.maxR.set(180)
	clampScaleNegative.maxG.set(180)
	clampScaleNegative.maxB.set(180)
	
	addDoubleScaleOne.input1.set(1)
	addDoubleScaleTwo.input1.set(1)

	pm.parent(jntBtwEnd, jntBtw)
	pm.parent(jntAimEnd, jntAim)
	pm.parent(jntVoidEnd, jntVoid)
	pm.parent(jntBtwIKEnd, jntBtwIK)

	# pm.parent([upGrp, pole], allBtwJntHide)
	pm.parent(upGrp, allBtwJntHide)
	pm.parent(allBtwJntHide, allBtwJntMove)
	pm.parent(allBtwJntMove, allBtwJntGrp)

	pm.delete(pm.parentConstraint(startJnt, allBtwJntGrp))
	pm.parent(jntBtw, allBtwJntMove)
	# pm.parent([jntBtwIK, jntAim, jntVoid, jntVoidAim], allBtwJntHide)
	pm.parent([jntBtwIK, jntAim, jntVoid], allBtwJntHide)

	moveSide = 2
	mult = 1
	tmpEndJnt = endJnt.duplicate(po=True)[0]
	misc.unlockChannelbox(tmpEndJnt)
	pm.parent(tmpEndJnt, startJnt)

	objSpaceTr = tmpEndJnt.getTranslation('object')
	pm.delete(tmpEndJnt)

	exec('aimTr = objSpaceTr.%s' %axis[-1])

	if aimTr <= 0.0:
		mult = -1

	axisUpDict = {'x':'y', 'y':'x', 'z':'x'}

	pm.parent(allBtwJntGrp, parentJnt)

	tMove = 't%s' %axis
	aimV = misc.vectorStr(axis) * mult
	upV = misc.vectorStr(axisUpDict[axis])

	# pm.parent(allBtwJntMove, startJnt)
	allBtwJntMove.attr(tMove).set((distAimAndVoid*-0.334*mult))

	if pointConstraint == True:
		pm.pointConstraint(startJnt, allBtwJntGrp)
	distanceBtwEnd = misc.getDistanceFromPosition(aPos=jntBtw.getTranslation('world'), bPos=startJnt.getTranslation('world'))

	for jnt in (jntBtwEnd, jntAimEnd, jntVoidEnd, jntBtwIKEnd):
		jnt.attr(tMove).set((distanceBtwEnd*moveSide*mult))


	misc.addNumAttr(jntBtw, 'btwAutoShape', 'long', min=0, max=1, dv=1)
	misc.addNumAttr(jntBtw, 'aimBtw', 'float', min=0, max=1, dv=0.5)

	misc.addNumAttr(jntBtw, 'aimBtwDriven', 'float', min=0, max=1, dv=0.5)
	misc.addNumAttr(jntBtw, 'scaleBtw', 'float', dv=2)
	misc.addNumAttr(jntBtw, 'scaleLimit', 'float', dv=2)
	misc.addNumAttr(jntBtw, 'posOnOff', 'bool', min=0, max=1, dv=1)
	misc.addNumAttr(jntBtw, 'negOnOff', 'bool', min=0, max=1, dv=1)
	misc.addNumAttr(jntBtw, 'rotX_Amp', 'float', min=-1000, max=1000, dv=0)
	misc.addNumAttr(jntBtw, 'rotY_Amp', 'float', min=-1000, max=1000, dv=0)
	misc.addNumAttr(jntBtw, 'rotZ_Amp', 'float', min=-1000, max=1000, dv=0)

	pm.connectAttr(jntBtw.aimBtwDriven, reveseDriverVoid.inputX)

	for a in 'XYZ':
		pm.connectAttr(jntBtw.scaleBtw, mutiScaleMutiPlus.attr('input2%s' %a))

	for s, e in zip(allJntDup, allJntEndDup):
		if not e.inverseScale.isConnected():
			pm.connectAttr(s.scale, e.inverseScale, f=True)

	ik, eff = pm.ikHandle(sol='ikRPsolver', s='sticky', sj=jntBtwIK, ee=jntBtwIKEnd)
	ik.rename(naming.NAME((elem, 'Btw'), side, naming.IKHNDL))
	eff.rename(naming.NAME((elem, 'BtwEnd'), side, naming.EFF))

	# pm.poleVectorConstraint(pole, ik)
	ik.poleVector.set([0, 0, 0])
	ik.poleVector.lock()
	ikPoint = pm.pointConstraint([jntAimEnd, jntVoidEnd], ik)

	allBtwJntHide.visibility.set(False)
	pm.parent(ik, allBtwJntHide)

	aimAim = pm.aimConstraint(endJnt, jntAim, aimVector=aimV, upVector=upV, worldUpType='object', worldUpObject=upGrp)
	# aimVoid = pm.aimConstraint(jntVoidAim, jntVoid, aimVector=aimV, upVector=upV, worldUpType='object', worldUpObject=upGrp)

	pm.connectAttr(jntBtw.aimBtwDriven, ikPoint.attr('%sW0' %jntAimEnd.nodeName()))
	pm.connectAttr(reveseDriverVoid.outputX, ikPoint.attr('%sW1' %jntVoidEnd.nodeName()))

	pm.connectAttr(jntBtw.posOnOff, condScalePosOnOff.ft)
	pm.connectAttr(jntBtw.negOnOff, condScaleNegOnOff.ft)
	
	for a in 'xyz':
		upperA = a.upper()
		pm.connectAttr(jntBtwIK.attr('r%s' %a), mutiScalePositive.attr('input1%s' %upperA))
		pm.connectAttr(jntBtwIK.attr('r%s' %a), mutiScaleNegative.attr('input1%s' %upperA))

		pm.connectAttr(condScalePosOnOff.ocr, mutiScalePositive.attr('input2%s' %upperA))
		pm.connectAttr(condScaleNegOnOff.ocr, mutiScaleNegative.attr('input2%s' %upperA))

	pm.connectAttr(mutiScalePositive.output, clampScalePositive.input)
	pm.connectAttr(mutiScaleNegative.output, clampScaleNegative.input)
	pm.connectAttr(clampScalePositive.output, plusPosiNegaScale.input3D[0])
	pm.connectAttr(clampScaleNegative.output, plusPosiNegaScale.input3D[1])
	pm.connectAttr(plusPosiNegaScale.output3D, mutiScaleMutiPlus.input1)

	remAxis = 'xyz'.replace(axis, '')

	pm.connectAttr(mutiScaleMutiPlus.attr('output%s' %remAxis[0].upper()), addDoubleScaleTwo.input2)
	pm.connectAttr(mutiScaleMutiPlus.attr('output%s' %remAxis[1].upper()), addDoubleScaleOne.input2)

	pm.connectAttr(jntBtw.scaleLimit, clampScaleLimit.maxR)
	pm.connectAttr(jntBtw.scaleLimit, clampScaleLimit.maxG)
	pm.connectAttr(addDoubleScaleOne.output, clampScaleLimit.inputR)
	pm.connectAttr(addDoubleScaleTwo.output, clampScaleLimit.inputG)
	pm.connectAttr(clampScaleLimit.outputR,	jntBtw.attr('s%s' %remAxis[0]))
	pm.connectAttr(clampScaleLimit.outputG,	jntBtw.attr('s%s' %remAxis[1]))

	pm.makeIdentity(jntBtwIK, apply=True, t=True, r=True, s=False)
	pm.delete(pm.parentConstraint(jntBtwIK, jntBtw))
	pm.makeIdentity(jntBtw, apply=True, t=True, r=True, s=False)
	pm.parentConstraint(jntBtwIK, jntBtw)
	
	##-- Generate btwAutoShape
	##-- auto Shape Pos
	btwShapeCmp = pm.createNode("clamp", n=naming.NAME((elem, 'MulScaleAutoPos'), side, naming.CMP))
	btwShapeMdv = pm.createNode("multiplyDivide", n=naming.NAME((elem, 'MulScaleAutoPos'), side, naming.MDV))
	btwShapeRevMdv = pm.createNode("multiplyDivide", n=naming.NAME((elem, 'MulScaleRevAutoPos'), side, naming.MDV))
	btwShapePma = pm.createNode("plusMinusAverage", n=naming.NAME((elem, 'PlusPosNegAutoScale'), side, naming.PMA))
	btwShapeRvs = pm.createNode("reverse", n=naming.NAME((elem, 'DriveVoidAutoPos'), side, naming.REV))
	btwShapeBcol = pm.createNode("blendColors", n=naming.NAME((elem, 'DriveVoidAutoPos'), side, naming.BCOL))
	btwShapeDefBcol = pm.createNode("blendColors", n=naming.NAME((elem, 'DefAutoPos'), side, naming.BCOL))

	## -- Set Attribute Default
	btwShapeCmp.minG.set(-80)
	btwShapeCmp.maxR.set(80)
	btwShapeCmp.maxB.set(80)
	btwShapeMdv.input2X.set(0.01)
	btwShapeMdv.input2Y.set(0.01)
	btwShapeMdv.input2Z.set(0.01)
	btwShapeDefBcol.color1R.set(0.5)
	btwShapeDefBcol.color2R.set(0.5)
	btwShapeDefBcol.color2B.set(0)
	jntBtw.rotX_Amp.set(0.1)
	jntBtw.rotY_Amp.set(-0.3)
	jntBtw.rotZ_Amp.set(0.7)

	pm.connectAttr(startJnt.rx, btwShapeCmp.inputR)
	pm.connectAttr(startJnt.rx, btwShapeCmp.inputG)
	pm.connectAttr(startJnt.rz, btwShapeCmp.inputB)
	pm.connectAttr(btwShapeCmp.outputR, btwShapeMdv.input1X)
	pm.connectAttr(btwShapeCmp.outputG, btwShapeMdv.input1Y)
	pm.connectAttr(btwShapeCmp.outputB, btwShapeMdv.input1Z)
	pm.connectAttr(jntBtw.rotX_Amp, btwShapeRevMdv.input2X)
	pm.connectAttr(jntBtw.rotY_Amp, btwShapeRevMdv.input2Y)
	pm.connectAttr(jntBtw.rotZ_Amp, btwShapeRevMdv.input2Z)
	pm.connectAttr(btwShapeMdv.outputX, btwShapeRevMdv.input1X)
	pm.connectAttr(btwShapeMdv.outputY, btwShapeRevMdv.input1Y)
	pm.connectAttr(btwShapeMdv.outputZ, btwShapeRevMdv.input1Z)



	pm.connectAttr(btwShapeRevMdv.outputX, btwShapePma.input2D[0].input2Dx)
	pm.connectAttr(btwShapeRevMdv.outputY, btwShapePma.input2D[1].input2Dx)
	pm.connectAttr(btwShapeRevMdv.outputZ, btwShapePma.input2D[2].input2Dx)
	pm.connectAttr(btwShapeDefBcol.outputR, btwShapePma.input2D[3].input2Dx)
	pm.connectAttr(btwShapePma.output2Dx, btwShapeBcol.color2R)

	## connect 2 line
	pm.connectAttr(jntBtw.btwAutoShape, btwShapeRvs.inputX)
	pm.connectAttr(btwShapeRvs.outputX, btwShapeBcol.blender)
	pm.connectAttr(jntBtw.aimBtw, btwShapeBcol.color1R)
	pm.connectAttr(btwShapeBcol.outputR, jntBtw.aimBtwDriven)
	pm.connectAttr(jntBtw.btwAutoShape, btwShapeDefBcol.blender)

	## lockAttribute
	pm.parent(allBtwJntGrp, parentJnt)
	# lock hide unused attrs
	jntBtw.aimBtwDriven.lock()
	jntBtw.translate.lock()
	jntBtw.rotate.lock()
	jntBtw.scale.lock()
	jntBtw.visibility.lock()

def ribbonNonRollRig(rbnCtrl=None, elem='', side='', skinGrp='Skin_Grp', animGrp='Anim_Grp',
	rbnAttr='detailControl', 
	visAttrName='secDetailControl', 
	autoTwstAttrName='secAutoTwist',
	ctrlColor='pink'):
	if not rbnCtrl:
		rbnCtrl = misc.getSel(selType='transform', num=1)
		if not rbnCtrl:
			return
	if isinstance(rbnCtrl, (str, unicode)):
		rbnCtrl = pm.PyNode(rbnCtrl)

	dtlCtrlGrps = rbnCtrl.attr(rbnAttr).outputs()
	dtlCtrls = []
	dtlCons = []
	dtlJnts = []
	for grp in dtlCtrlGrps:
		dtlTwGrp = grp.getChildren(type='transform')[0]
		dtlCtrl = dtlTwGrp.getChildren(type='transform')[0]
		dtlCon = grp.getChildren(type='parentConstraint')[0]

		jntPar = dtlCtrl.outputs(type='parentConstraint')[0]
		dtlJntZro = jntPar.outputs(type='transform')[0]
		dtlJnt = dtlJntZro.getChildren(type='joint')[0]

		dtlCtrls.append(dtlCtrl)
		dtlCons.append(dtlCon)
		dtlJnts.append(dtlJnt)

	posGrps = [c.getTargetList()[0] for c in dtlCons]
	
	# sort list by names
	dtlCtrls = sorted(dtlCtrls, key=lambda x: x.nodeName())
	dtlCons = sorted(dtlCons, key=lambda x: x.nodeName())
	posGrps = sorted(posGrps, key=lambda x: x.nodeName())
	dtlJnts = sorted(dtlJnts, key=lambda x: x.nodeName())

	rigGrp = pm.group(em=True, n=naming.NAME(elem, 'Rig', side, naming.GRP))
	jntGrp = pm.group(em=True, n=naming.NAME(elem, 'Skin', side, naming.GRP))
	ctrlGrp = pm.group(em=True, n=naming.NAME(elem, 'Anim', side, naming.GRP))
	pm.parent(ctrlGrp, rigGrp)
	try:
		pm.parent(jntGrp, pm.PyNode(skinGrp))
	except:
		pass

	try:
		pm.parent(rigGrp, pm.PyNode(animGrp))
	except:
		pass

	visAttr = misc.addNumAttr(rbnCtrl.getShape(), visAttrName, 'long', min=0, max=1, dv=0, hide=False, lock=False, key=True)
	pm.connectAttr(visAttr, ctrlGrp.visibility)

	autoTwstAttr = misc.addNumAttr(rbnCtrl, autoTwstAttrName, 'double', min=0, max=1, dv=1, hide=False, lock=False, key=True)
	baseTwstGrp = dtlCtrls[0].getParent()
	
	nrJnts, nrCtrls = [], []
	i = 0
	for j, c in zip(dtlJnts, dtlCtrls):
		nrJnt = j.duplicate(po=True, n=naming.NAME((elem, (i+1)), side, naming.JNT))[0]

		nrJnt.radius.set(j.radius.get()*1.1)
		misc.lockAttr(obj=nrJnt, lock=False, t=True, r=True, s=True, v=False)
		misc.hideAttr(obj=nrJnt, hide=False, t=True, r=True, s=True, v=False)

		pm.parent(nrJnt, jntGrp)
		pm.makeIdentity(nrJnt, apply=True)
		nrJnts.append(nrJnt)

		nrCtrl = c.duplicate(n=naming.NAME((elem, (i+1)), side, naming.CTRL))[0]
		misc.scaleCtrlVtx(inc=True, percent=10, obj=nrCtrl)
		
		ctrlZgrp = misc.zgrp(nrCtrl, element='Zro', suffix='Grp')[0]
		pm.parent(ctrlZgrp, ctrlGrp)

		nrCtrls.append(nrCtrl)

		misc.lockAttr(obj=nrCtrl, lock=False, t=True, r=True, s=True, v=False)
		misc.hideAttr(obj=nrCtrl, hide=False, t=True, r=True, s=True, v=False)
		unused_attrs = nrCtrl.listAttr( r=True, s=True, k=True, ud=True)
		for a in unused_attrs:
			a.lock()
			a.setKeyable(False)
			a.showInChannelBox(False)

		pm.parentConstraint(posGrps[i], ctrlZgrp)
		pm.parentConstraint(nrCtrl, nrJnt)
		# pm.scaleConstraint(nrCtrl, nrJnt, mo=True)

		
		twstGrp = None
		ro_input_attr = None
		ro_source_attr = None
		# if connectTwst == True:
		twstGrp = dtlCtrls[i].getParent()
		# else:
			# twstGrp = baseTwstGrp

		for rax in ['rx', 'ry', 'rz']:
			ro_attr = twstGrp.attr(rax)
			if ro_attr.isConnected():

				ro_input_attr = rax
				ro_source_attr = ro_attr.inputs(p=True, scn=True)[0]
				break

		if ro_input_attr and ro_source_attr:
			bTwoAttr = pm.createNode('blendTwoAttr', n=naming.NAME((elem, (i+1), 'AutoTwst'), side, naming.BTA))
			bTwoAttr.input[0].set(0.0)

			ctrlTwstGrp = pm.group(nrCtrl, n=naming.NAME((elem, (i+1), 'Twst'), side, naming.GRP))

			pm.connectAttr(autoTwstAttr, bTwoAttr.attributesBlender)
			pm.connectAttr(ro_source_attr, bTwoAttr.input[1])
			pm.connectAttr(bTwoAttr.output, ctrlTwstGrp.attr(ro_input_attr))

		# scale
		scalePma = pm.createNode('plusMinusAverage', n=naming.NAME((elem, (i+1), 'Sqsh'), side, naming.PMA))
		for ax in 'xyz':
			pm.connectAttr(nrCtrl.attr('s%s' %ax), scalePma.input3D[0].attr('input3D%s' %ax))
			pm.connectAttr(j.attr('s%s' %ax), scalePma.input3D[1].attr('input3D%s' %ax))
		pm.connectAttr(scalePma.output3D, nrJnt.scale)

		i += 1

	misc.setWireFrameColor(color=ctrlColor, objs=nrCtrls)

def wheelAutoRotate(parent=None, wheels=[], name='wheel', 
	elems=['Front', 'Front', 'Back', 'Back'], sides=['LFT', 'RGT', 'LFT', 'RGT'], 
	direction='z', axis='x'):

	if not parent or not wheels:
		sels = misc.getSel(num='inf')
		parent = sels[0]
		wheels = sels[1:]

	locGrp = pm.group(em=True, n='%sLoc_grp' %(name))
	locGrp.visibility.set(False)

	originLoc = pm.spaceLocator(n='%sOrigin_loc' %(name))
	moveLoc = pm.spaceLocator(n='%sMove_loc' %(name))
	pm.parent([originLoc, moveLoc], locGrp)
	
	misc.snapTransform('parent', parent, originLoc, True, True)
	misc.snapTransform('parent', parent, moveLoc, True, False)

	dist = pm.createNode('distanceBetween', n='%sAutoSpin_dist' %(name))
	pm.connectAttr(moveLoc.translate, dist.point2)
	pm.connectAttr(originLoc.translate, dist.point1)

	pma = pm.createNode('plusMinusAverage', n='%sAutoSpinVec_pma' %(name))
	pma.operation.set(2)  # set to subtract
	pm.connectAttr(moveLoc.translate, pma.input3D[0])
	pm.connectAttr(originLoc.translate, pma.input3D[1])

	cond = pm.createNode('condition', n='%sAutoSpinDirection_cond' %(name))
	cond.secondTerm.set(0.0)
	cond.operation.set(2)
	cond.colorIfTrueR.set(360.0)
	cond.colorIfFalseR.set(-360.0)

	pm.connectAttr(pma.attr('output3D%s' %direction), cond.firstTerm)
	
	for i, wheel in enumerate(wheels):
		_name = (name, elems[i], sides[i])

		# add control Attribute
		timeSpinAttr = misc.addNumAttr(wheel, 'timeSpin', 'double', dv=0.0)
		autoSpinAttr = misc.addNumAttr(wheel, 'autoSpin', 'double', dv=1.0)

		# sum node for all modes
		sumPma = pm.createNode('plusMinusAverage', n='%s%sSum%s_pma' %(_name))

		# --- time spin
		timeNode = pm.PyNode('time1')
		timeSpinMult = pm.createNode('multDoubleLinear', n='%sTimeSpinMult%s%s_mdl' %_name)
		pm.connectAttr(timeNode.outTime, timeSpinMult.input1)
		pm.connectAttr(timeSpinAttr, timeSpinMult.input2)
		pm.connectAttr(timeSpinMult.output, sumPma.input1D[0])
		

		# --- auto spin
		bb = wheel.boundingBox()
		diameter = abs(bb[0][1] - bb[1][1])

		diaAttr = misc.addNumAttr(moveLoc, '%s%s%s_diameter' %_name, 'double')
		diaAttr.set(diameter)
		diaMdl = pm.createNode('multDoubleLinear', n='%s%sDiameter%s_mdl' %_name)
		pm.connectAttr(diaAttr, diaMdl.input1)
		diaMdl.input2.set(math.pi)

		divMdv = pm.createNode('multiplyDivide', n='%s%sDiv%s_mdv' %_name)
		divMdv.operation.set(2)
		pm.connectAttr(dist.distance, divMdv.input1X)
		pm.connectAttr(diaMdl.output, divMdv.input2X)

		degMdl = pm.createNode('multDoubleLinear', n='%s%sDeg%s_mdl' %_name)
		pm.connectAttr(divMdv.outputX, degMdl.input1)
		pm.connectAttr(cond.outColorR, degMdl.input2)

		autoSpinMult = pm.createNode('multDoubleLinear', n='%s%sAutoSpinMult%s_mdl' %_name)
		pm.connectAttr(degMdl.output, autoSpinMult.input1)
		pm.connectAttr(autoSpinAttr, autoSpinMult.input2)

		pm.connectAttr(autoSpinMult.output, sumPma.input1D[1])

		# connect to rotate grp
		pm.connectAttr(sumPma.output1D, wheel.attr('r%s' %axis))

def wheelAutoRotateExp(wheels=[], elem='wheel', side='',
	direction='z', axis='x'):

	if not wheels:
		wheels = misc.getSel(num='inf')
		numWheels = len(wheels)
		if not wheels or numWheels < 2 or numWheels % 2 != 0:
			om.MGlobal.displayError('Invalid selection!')
			return

	axisVec = misc.vectorStr(axis)

	locGrp = pm.group(em=True, n=naming.NAME((elem, 'Loc'), side, naming.GRP))
	locGrp.visibility.set(False)

	i = 0
	for parent, wheel in zip(wheels[::2], wheels[1::2]):
		nsp = misc.nameSplit(wheel.nodeName())
		elem = nsp['elem']
		side = nsp['pos']

		# add control Attribute
		timeSpinAttr = misc.addNumAttr(parent, 'timeSpin', 'double', dv=0.0)
		autoSpinAttr = misc.addNumAttr(parent, 'autoSpin', 'long', dv=1.0, min=0, max=1)

		# sum node for all modes
		sumPma = pm.createNode('plusMinusAverage', n=naming.NAME((elem, 'Sum'), side, naming.PMA))

		# --- time spin
		timeNode = pm.PyNode('time1')
		timeSpinMult = pm.createNode('multDoubleLinear', n=naming.NAME((elem, 'TimeSpinMult'), side, naming.MDL))
		pm.connectAttr(timeNode.outTime, timeSpinMult.input1)
		pm.connectAttr(timeSpinAttr, timeSpinMult.input2)
		pm.connectAttr(timeSpinMult.output, sumPma.input1D[0])
		
		# --- auto spin
		moveLoc = pm.spaceLocator(n=naming.NAME((elem, 'AutoSpinTr'), side, naming.LOC))
		spinLoc = pm.spaceLocator(n=naming.NAME((elem, 'AutoSpinRot'), side, naming.Loc))
		pm.parent([moveLoc, spinLoc], locGrp)
		
		misc.snapTransform('point', parent, moveLoc, False, True)
		moveLoc.ty.set(0.0)
		misc.snapTransform('point', parent, moveLoc, True, False)
		pm.aimConstraint(parent, moveLoc, 
			aimVector=[0, 1, 0], upVector=axisVec, worldUpVector=axisVec,
			worldUpType='objectrotation', worldUpObject=parent)

		misc.snapTransform('parent', parent, spinLoc, False, True)

		bb = wheel.boundingBox()
		diameter = abs(bb[0][1] - bb[1][1])
		if diameter == 0.0:
			diameter = 1.0

		diaAttr = misc.addNumAttr(parent, 'autoSpin_diameter', 'double')
		diaAttr.set(diameter)
		diaAttr.setKeyable(False)
		diaAttr.showInChannelBox(False)
		
		expNode = makeAutoRotate(autoSpinAttr.name(), transform=moveLoc, wheel=spinLoc,
			elem=elem, side=side, diameter=diaAttr.name(),
			direction=direction, axis=axis)
		
		# # when autoSpine is 0, the expression node state is "hasNoEffect"
		# autoSpinRev = pm.createNode('reverse', n='%sAutoSpin%s_rev' %_name)
		# pm.connectAttr(autoSpinAttr, autoSpinRev.inputX)
		# pm.connectAttr(autoSpinRev.outputX, expNode.nodeState)

		# multiplier for auto spin
		autoSpinMult = pm.createNode('multDoubleLinear', n=naming.NAME((elem, 'AutoSpinMult'), side, naming.MDL))
		pm.connectAttr(spinLoc.attr('r%s' %axis), autoSpinMult.input1)
		pm.connectAttr(autoSpinAttr, autoSpinMult.input2)

		pm.connectAttr(autoSpinMult.output, sumPma.input1D[1])

		# connect to rotate grp
		pm.connectAttr(sumPma.output1D, wheel.attr('r%s' %axis))

		i += 1

def makeAutoRotate(switchAttr, transform=None, wheel=None, 
	elem='', side='', diameter=1.0,
	direction='z', axis='x'):

	if not transform or not wheel:
		sels = misc.getSel(num=2)
		if len(sels) != 2:
			om.MGlobal.displayError('Invalid selection!')
			return
		transform = sels[0]
		wheel = sels[1]

	if not elem:
		nsp = misc.nameSplit(wheel.nodeName())
		elem = nsp['elem']
		side = nsp['pos']
	
	trName = transform.nodeName()
	whName = wheel.nodeName()
	diVec = misc.vectorStr(direction)
	axisVec = misc.vectorStr(axis)
	crossVec = diVec.cross(axisVec)
	matIndxDict = {'x':[0, 1, 2], 'y':[4, 5, 6], 'z':[8, 9, 10]}
	rotAxis = 'xyz'.index(axis[-1])
	otherAxis = [a for a in 'xyz' if a != direction[-1] and a != axis[-1]]
	otherAxis = otherAxis[0]
	mult = crossVec['xyz'.index(otherAxis)]
	mult *= 360.0

	exp = """
	$doIt = %s;
	if($doIt == 1) { 
		float $diameter = %s;
		float $by = `playbackOptions -q -by`;
		float $lastFrame = (frame - $by);

		float $lastTr[] = `getAttr -time $lastFrame %s.translate`;
		float $currTr[] = `getAttr %s.translate`;

		vector $currTrV = <<$currTr[0], $currTr[1], $currTr[2]>>;
		vector $lastTrV = <<$lastTr[0], $lastTr[1], $lastTr[2]>>;

		vector $travelV = $currTrV - $lastTrV;
		float $distance = mag($travelV);

		if ($distance > 0.0) {
			float $lastRot[] = `getAttr -time $lastFrame %s.rotate`;
			float $trMatrix[] = `xform -q -ws -matrix %s`;
			vector $directionVec = unit(<<$trMatrix[%s], $trMatrix[%s], $trMatrix[%s]>>);
			vector $travelVNorm = unit($travelV);
			float $d = dot($travelVNorm, $directionVec);

			float $result = (((($distance/($diameter * %s))* %s * $d) + $lastRot[%s]));
			%s.r%s = $result;
		} 
	}

	""" %(switchAttr, diameter,
		trName, trName, whName, trName, 
		matIndxDict[direction][0], 
		matIndxDict[direction][1], 
		matIndxDict[direction][2],
		math.pi, mult, rotAxis, whName, axis)
	expNode = pm.expression(s=exp, n=naming.NAME(elem, side, naming.EXP))
	pm.lockNode(expNode, l=True)

	return expNode

def convertAnimKeyToSdk(driverAttr, sdks=[], attrPrefix='sdk_'):
	'''
	driverAttr = driver attribute name (str)
	skds = driver and driven objects [PyNode, PyNode] *user selection
	'''

	if not sdks:
		sdks = misc.getSel(selType='any', num=3)

	driver = sdks[0]
	keyedObj = sdks[1]
	target = sdks[2]

	driverAttrObj = None
	try:
		driverAttrObj = driver.attr(driverAttr)
	except Exception:
		return

	for kattr in keyedObj.listAttr(k=True, s=True, se=True, u=True):
		acs = kattr.inputs(type='animCurve')

		targetAttr = None
		try:
			targetAttr = target.attr('%s%s' %(attrPrefix, kattr.longName()))
		except Exception:
			continue

		if acs:
			animCrv = acs[0]
			pm.connectAttr(driverAttrObj, animCrv.input)
			pm.connectAttr(animCrv.output, targetAttr)
			pm.disconnectAttr(animCrv.output, kattr)
