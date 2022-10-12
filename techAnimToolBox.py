import os
import pprint

import maya.cmds as mc
import maya.mel as mel
import pymel.core as pm
import maya.OpenMaya as om

from nuTools.pipeline import pipeTools
reload(pipeTools)

# check if VRay plugin is loaded?
pluginFileName = 'vrayformaya.mll'

if mc.pluginInfo(pluginFileName, q=True, l=True) == False:
	mc.loadPlugin(pluginFileName)

def cleanUnusedRenderLayer():
	rls = pm.ls(type='renderLayer')
	i = 0
	for node in (r for r in rls if not r.isReferenced()):
		if not node.renderInfo.outputs():
			nodeName = node.nodeName()
			if nodeName == 'defaultRenderLayer':
				continue
			try:
				pm.delete(node)
				i += 1
				print 'deleted : %s' %nodeName
				
			except:
				om.MGlobal.displayWarning('Cannot delete : %s' %nodeName)

	print '%s unused renderLayer(s) deleted.' %i

def closeAllFloatingWin():
	cmd = '''
	global string $gMainWindow;

	string $allOpenWindows[] = `lsUI -wnd`;

	for ($items in $allOpenWindows) {
		if ($items != $gMainWindow) {
			window -e -vis 0 $items;
		}
	}
	'''
	mel.eval(cmd)

def setViewPort(mode='wireframe', cam='perspShape'):
	closeAllFloatingWin()
	mel.eval('setNamedPanelLayout("Single Perspective View");')
	modelpanel = mc.getPanel(wl='Persp View')

	pm.modelEditor(modelpanel, e=True, cam=cam, wos=False, displayAppearance=mode, 
			df=False, dim=False, ca=False, hs=False, ha=False, ikh=False, j=False, sds=False,
			lt=False, lc=False, ncl=False, npa=False, nr=False, nc=False, str=False, hu=False,
			dy=False, pv=False, pl=False, fl=False, fo=False, dc=False, tx=False, mt=False,
			m=True, ns=True, pm=True )

def setRenderSettings():
	# set start/end frame
	renderglobal = pm.PyNode('defaultRenderGlobals')
	renderglobal.animation.set(False)
	renderglobal.startFrame.set(pm.playbackOptions(q=True, min=True))
	renderglobal.endFrame.set(pm.playbackOptions(q=True, max=True))

	# set render engine to vray.
	renderglobal.ren.set('vray')
	# vray is depend on the ui
	settingsOpened = False
	if mel.eval('window -q -exists "unifiedRenderGlobalsWindow";'):
		settingsOpened = mel.eval('window -q -vis "unifiedRenderGlobalsWindow";')
	mel.eval('unifiedRenderGlobalsWindow;')
	vrSettings = pm.PyNode('vraySettings')
	vrSettings.aspectLock.set(False)  # set no aspect ratio lock
	vrSettings.width.set(1920)
	vrSettings.height.set(800)
	vrSettings.aspectRatio.set(2.4)
	mel.eval('updateDefaultResolution;')
	if not settingsOpened:
		mel.eval('window -e -vis 0 unifiedRenderGlobalsWindow;')

def cleanUnusedAnimCurve():
	animCrvs = (c for c in pm.ls(type='animCurve') if not c.isReferenced() and not c.isLocked())

	i = 0
	deletes = []
	for animCrv in animCrvs:
		outputs = animCrv.outputs(p=True)
		if outputs:		
			if outputs[0].node().type() != 'reference':
				continue

		for output in outputs:
			output.disconnect()

		print 'deleted : %s' %animCrv.nodeName()
		pm.delete(animCrv)
		i += 1

	print '%s unused animCurve(s) deleted.' %i

