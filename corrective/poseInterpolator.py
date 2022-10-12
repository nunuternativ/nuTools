import pymel.core as pm
import maya.cmds as mc
import maya.mel as mel
import maya.OpenMaya as om

from nuTools import misc
reload(misc)

pluginName = 'poseInterpolator.mll'
try:
    if not pluginInfo(pluginName, q=True, l=True):
        loadPlugin(pluginName, qt=True)
except:
    pass

def addPose(node, poseName):
    if isinstance(node, (str, unicode)):
        node = pm.PyNode(node)
    nodeShp = node.getShape(type='poseInterpolator')
    pidx = mel.eval('poseInterpolatorAddShapePose %s %s "swing" {} 0;' %(nodeShp.nodeName(), poseName))
    nodeAttr = misc.addNumAttr(node, poseName, 'double')
    pm.connectAttr(nodeShp.output[pidx], nodeAttr, f=True)

    
