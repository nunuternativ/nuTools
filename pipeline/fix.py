import pymel.core as pm
import maya.cmds as mc
import maya.OpenMaya as om
import maya.mel as mel
from pprint import pprint

import pipeTools
reload(pipeTools)

def deleteDuplicateGraphEditor():
    allGE = [i for i in mc.lsUI(ed=True) if i.startswith('graphEditor')]
    for ge in allGE:
        if ge not in ['graphEditor1GraphEd', 'graphEditor1OutlineEd', 'graphEditor1OutlineEdSlave']:
            mc.deleteUI(ge)
            print 'UI deleted : %s' %ge 

def removeDisconRenPartRefEdits():
    # get current layer
    origRenderLayer = pm.PyNode(pm.editRenderLayerGlobals(q=True, currentRenderLayer=True))
    # set to master layer
    masterLayer = pm.PyNode('defaultRenderLayer')
    masterLayer.setCurrent()

    refs = pm.listReferences()
    for ref in refs:
        edits = ref.getReferenceEdits()

        if not edits:
            continue
        disConPartitionEdits = [e for e in edits if e.startswith('disconnectAttr') and e.endswith('renderPartition.sets"')]
        if not disConPartitionEdits:
            continue

        ref.unload()

        for d in disConPartitionEdits:
            des = d.split(' ')[-1][1:-1]
            try:
                cmd = 'referenceEdit -failedEdits true -successfulEdits true -editCommand "disconnectAttr" -removeEdits "%s:%s";' %(ref.fullNamespace, des)
                print cmd
                mel.eval(cmd)
            except Exception, e:
                print e
            
            ref.load()

    origRenderLayer.setCurrent()

def removeFileTextureRefEdits():
    refs = pipeTools.getFileRefFromObjects(pm.selected())
    if not refs:
        pm.error('Select reference object(s) and try again.')
        return

    masterLayer = pm.PyNode('defaultRenderLayer')
    masterLayer.setCurrent()

    for ref in refs:
        edits = ref.getReferenceEdits()

        if not edits:
            continue
        setAttrEdits = [e for e in edits if e.startswith('setAttr') and '.fileTextureName' in e]
        if not setAttrEdits:
            continue

        ref.unload()

        for s in setAttrEdits:
            # setCmd = s.split(' ')[-1][1:-1]
            setCmd = s.split('setAttr ')[-1]
            setCmd = setCmd.split(' ')[0]
            setCmd = setCmd.replace('"', '')
            try:
                cmd = 'referenceEdit -failedEdits true -successfulEdits true -editCommand "setAttr" -removeEdits "%s";' %(setCmd)
                print cmd
                mel.eval(cmd)
            except Exception, e:
                print e

        ref.load()

def removeConnectAttrRefEdits():
    refs = pipeTools.getFileRefFromObjects(pm.selected())
    if not refs:
        pm.error('Select reference object(s) and try again.')
        return

    masterLayer = pm.PyNode('defaultRenderLayer')
    masterLayer.setCurrent()

    for ref in refs:
        edits = ref.getReferenceEdits()

        if not edits:
            continue

        set_connect_edits = [e for e in edits if e.split(' ')[0] == 'connectAttr']
        if not set_connect_edits:
            continue

        commands = set()
        for s in set_connect_edits:
            splits = s.split(' ')
            commandEdit, src, des, srcNodeName = '', '', '', ''
            srcNode = None
            try:
                commandEdit = splits[0]
                src = splits[1]
                des = splits[2]

                srcNodeName = src.replace('"', '')
                srcNode = pm.PyNode(srcNodeName.split('.')[0])

                if srcNode.type().startswith('animCurve'):
                    continue

            except Exception, e:
                print e
                continue    

            cmd = 'referenceEdit -failedEdits true -successfulEdits true -editCommand "%s" -removeEdits "%s";' %(commandEdit, srcNodeName)
            commands.add(cmd)
                    
        if commands:
            ref.unload()

            for cmd in commands:
                try:    
                    print cmd
                    mel.eval(cmd)
                except Exception, e:
                    print e
            ref.clean(editCommand='disconnectAttr')

            ref.load()

def removeConnectAttrRefEdits_unknownnode(refs):
    # refs = [r for r in pm.listReferences() if r.isLoaded() == False]

    masterLayer = pm.PyNode('defaultRenderLayer')
    masterLayer.setCurrent()

    for ref in refs:
        if isinstance(ref, (str, unicode)):
            ref = pm.FileReference(ref)
        edits = ref.getReferenceEdits()

        if not edits:
            continue

        set_connect_edits = [e for e in edits if e.split(' ')[0] == 'connectAttr']
        if not set_connect_edits:
            continue

        
        commands = set()
        for s in set_connect_edits:
            splits = s.split(' ')
            commandEdit, src, des, srcNodeName = '', '', '', ''
            srcNode = None
            try:
                commandEdit = splits[0]
                src = splits[1]
                des = splits[2]

                srcNodeName = src.replace('"', '')
                srcNode = pm.PyNode(srcNodeName.split('.')[0])

                if srcNode.type().startswith('animCurve'):
                    continue

            except Exception, e:
                print e
                continue    

            if '_UNKNOWN_REF_NODE_' in s:
                cmd = 'referenceEdit -failedEdits true -successfulEdits true -editCommand "%s" -removeEdits "%s";' %(commandEdit, srcNodeName)
                commands.add(cmd)
                    
        if commands:
            ref.unload()

            for cmd in commands:
                try:    
                    print cmd
                    mel.eval(cmd)
                except Exception, e:
                    print e
            # ref.clean(editCommand='disconnectAttr')

            ref.load()

def removeSetAttrRefEdits(searchFor, refPath=None):
    if not refPath:
        refs = pm.listReferences()
        if not refs:
            pm.error('Select reference object(s) and try again.')
            return
    else:
        refs = [pm.FileReference(refPath)]

    for ref in refs:
        edits = ref.getReferenceEdits()

        if not edits:
            continue

        set_attr_edits = [e for e in edits if e.split(' ')[0] == 'setAttr']
        if not set_attr_edits:
            continue

        
        commands = set()
        for s in set_attr_edits:
            splits = s.split(' ')
            commandEdit, src, des, srcNodeName = '', '', '', ''
            try:
                commandEdit = splits[0]
                obj = splits[1]
                nodeName = obj.replace('"', '')
            except Exception, e:
                print e
                continue    

            if searchFor in s:
                cmd = 'referenceEdit -failedEdits true -successfulEdits true -editCommand "%s" -removeEdits "%s";' %(commandEdit, nodeName)
                commands.add(cmd)
        
        print commands
        if commands:
            ref.unload()

            for cmd in commands:
                try:    
                    print cmd
                    mel.eval(cmd)
                except Exception, e:
                    print e

            ref.load()

def fixRefEditDisconnectDeformer():
    refs = pipeTools.getFileRefFromObjects(pm.selected())
    deformer_types = mc.listNodeTypes('deformer')
    for ref in refs:
        edits = ref.getReferenceEdits(ec='disconnectAttr')
        if not edits:
            continue

        for edit in edits:
            splits = edit.split(' ')
            src = splits[-2][1:-1]
            des = splits[-1][1:-1]
            srcNode = src.split('.')[0]
            if len(mc.ls(srcNode)) == 1:
                if pm.nodeType(srcNode) in deformer_types and des.endswith('.inMesh'):
                    if not pm.isConnected(src, des):
                        try:
                            pm.connectAttr(src, des, f=True)
                        except:
                            print 'Cannot reconnect %s %s' %(src, des)

                        # # remove that line of edit
                        # pm.ReferenceEdit(edit, fileReference=ref).remove(force=True)

def cleanUnusedDGs(nodeTypes=['plusMinusAverage', 'addDoubleLinear', 'multDoubleLinear', 'multiplyDivide', 
                'blendColors', 'clamp', 'blendTwoAttr', 'reverse', 'pointOnCurveInfo', 'pointOnSurfaceInfo'], chunkNum=100):
    rigGrp = pm.PyNode('Rig_Grp')
    rigNodes = rigGrp.getChildren(ad=True)
    rigNodes.append(rigGrp)

    dgNodes = [i for i in pm.ls(type=nodeTypes) if not i.isReferenced()]
    node_chunks = []
    
    s = 0
    e = chunkNum
    for n in xrange(len(dgNodes)):
        chunk = dgNodes[s:e]
        node_chunks.append(chunk)
        s = e
        e += chunkNum
    
    unusedNodes = set()
    unusedNodes_add = unusedNodes.add
    unusedNodes_update = unusedNodes.update
    banned = set()
    banned_update = banned.update
    numChunk = len(node_chunks)
    for i, chunk in enumerate(node_chunks):
        percentage = float(i+1)/float(numChunk)*100
        print '%s %% progress of cleaning...' %(round(percentage, 2))
        for node in [c for c in chunk if c not in banned]:
            fHis = node.listHistory(f=True, af=True, bf=True)[::-1]
            for n in fHis:
                if n in rigNodes:
                    banned_update(fHis)
                    break
            else:
                unusedNodes_add(node)
                unusedNodes_update(fHis)
    pprint( unusedNodes )
    return unusedNodes

