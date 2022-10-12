import maya.cmds as mc

from nuTools.pipeline import pipeTools
# reload(pipeTools)

ROTATE_ORDERS = ['xyz', 'yzx','zxy','xzy','yxz','zyx']


def restore(objs=[], oldRo='yzx', newRo='xzy'):
    if not objs:
        objs = mc.ls(sl=True, shortNames=True, type='transform')
        if not objs:
            om.MGlobal.displayError('Please make a selection.')
            return
    for obj in objs:
        mc.xform(obj, preserve=False, rotateOrder=oldRo)

    convert_current(objs, newRo)

def convert_current(sel, roo):
    time = mc.currentTime(query=True)

    #check that all rot channels have keys, or no keys
    keytimes = dict()
    prevRoo = dict()
    allKeytimes = list()
    keyedObjs = list()
    unkeyedObjs = list()

    for obj in sel:
        rotKeys = mc.keyframe(obj, attribute='rotate', query=True, timeChange=True)
        if rotKeys:
            keytimes[obj] = list(set(rotKeys))
            prevRoo[obj] = ROTATE_ORDERS[mc.getAttr(obj+'.rotateOrder')]
            allKeytimes.extend(rotKeys)
            keyedObjs.append(obj)
        else:
            unkeyedObjs.append(obj)

    mc.undoInfo(openChunk=True)
    #change rotation order for keyed objects
    if keyedObjs:

        allKeytimes = list(set(allKeytimes))
        allKeytimes.sort()

        # mc.ogs(pause=True)
        # mc.refresh(suspend=True)
        with pipeTools.FreezeViewport():
            #set keyframes first, so that frames that aren't keyed on all channels are
            for frame in allKeytimes:
                mc.currentTime(frame, edit=True)
                for obj in keyedObjs:
                    if frame in keytimes[obj]:
                        #set keyframe to make sure every channel has a key
                        mc.setKeyframe(obj, attribute='rotate')

            for frame in allKeytimes:
                mc.currentTime(frame, edit=True)
                for obj in keyedObjs:
                    if frame in keytimes[obj]:
                        #change the rotation order to the new value
                        mc.xform(obj, preserve=True, rotateOrder=roo)
                        #set a keyframe with the new rotation order
                        mc.setKeyframe(obj, attribute='rotate')
                        #change rotation order back without preserving, so that the next value is correct
                        mc.xform(obj, preserve=False, rotateOrder=prevRoo[obj])

            #reset current time while still isolated, for speed.
            mc.currentTime(time, edit=True)

            #set the final rotate order for keyed objects
            for each in keyedObjs:
                mc.xform(each, preserve=False, rotateOrder=roo)
                mc.filterCurve(each)

        # mc.refresh(suspend=False)
        # mc.refresh(f=True)
        # mc.ogs(pause=True)
    #for unkeyed objects, rotation order just needs to be changed with xform
    if unkeyedObjs:
        for obj in unkeyedObjs:
            mc.xform(obj, preserve=True, rotateOrder=roo)

    mc.undoInfo(closeChunk=True)
