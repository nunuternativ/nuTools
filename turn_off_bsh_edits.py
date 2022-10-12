import maya.cmds as mc
import pymel.core as pm
import maya.OpenMaya as om

def run(blendShapeNodes=[]):
    bshs = []
    if not blendShapeNodes:
        bshs = pm.ls(type='blendShape')
    else:
        for node in blendShapeNodes:
            if pm.objExists(node) and pm.nodeType(node) == 'blendShape':
                pyNode = pm.PyNode(node)
                bshs.append(pyNode)
            else:
                om.MGlobal.displayWarning('Skipping: {}'.format(node))
    if not bshs:
        return

    for bsh in bshs:
        editting = bsh.inputTarget[0].sculptTargetIndex.get()
        if editting != -1:
            pm.sculptTarget(bsh, e=True, target=editting)
            bsh.inputTarget[editting].sculptTargetIndex.set(-1)