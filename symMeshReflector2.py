# import time
# from functools import partial
import os, sys
from collections import defaultdict
import collections
import cPickle

import maya.OpenMaya as om
import maya.cmds as mc
import maya.mel as mel

from nuTools import misc
reload(misc)

DEFAULT_TOL = 0.00001
DEFAULT_EMPTY_TEXT = '-'
WS_CONTROL_NAME = 'symMeshReflector_ws'

# PANE_LAYOUT_NAME = 'symMeshReflector_paneLayout'
WINDOW_TITLE = 'Sym Mesh Reflector v.3.0'
WINDOW_NAME = 'smrWin'
MODULE_DIR = os.path.dirname(sys.modules[__name__].__file__).replace('\\', '/')

# load plugin
package_root = '/'.join(MODULE_DIR.split('/')[:-1])
plugins_dir = '%s/plugins' %(package_root)
pluginName = 'setMeshVertexCmd.py'
pluginPath = '%s/%s' %(plugins_dir, pluginName)
try:
    if not mc.pluginInfo(pluginPath, q=True, l=True):
        mc.loadPlugin(pluginPath, qt=True)
except Exception, e:
    print e
    om.MGlobal.displayError('Failed to load plugin: %s' %(pluginPath))
    raise RuntimeError

def pointListToStrArg(points):
    argLists = []
    for p in points:
        ptStr = '%s %s %s' %(p[0], p[1], p[2])
        argLists.append(ptStr)
    arg = ','.join(argLists)
    return arg

class SymMeshReflectors(object):

    def __init__(self, slotNum=20):
        #UI vars
        self.slotNum = slotNum

        self.objs = [None] * slotNum
        self.statuses = [False] * slotNum
        self.focusIndx = 0

        self.revertFloatFld = 'smr_revertFloatFld'
        self.revertSlider = 'smr_revertSlider'
        self.copyFloatFld = 'smr_copyFloatFld'
        self.copySlider = 'smr_copySlider'
        self.subsetTsl = 'smr_subsetTsl'
        self.statusTxt = 'smr_statusTxt'
        self.slotTsl = 'smr_slotTsl'
        self.tolFloatField = 'smr_tolFloatFld'

    def UI(self, dock=True):
        if dock:
            cbName = mel.eval('getUIComponentDockControl("Channel Box / Layer Editor", false);')
            winCall = 'from %s import smrObj;smrObj.buildUI()' %__name__
            closeCall = 'from %s import smrObj;smrObj.closeUI()' %__name__
            self.closeUI()
            if not mc.workspaceControl(WS_CONTROL_NAME, q=True, exists=True):
                mc.workspaceControl(WS_CONTROL_NAME, 
                    uiScript=winCall, 
                    closeCommand=closeCall,
                    label=WINDOW_TITLE, 
                    initialWidth=300, 
                    initialHeight=500, 
                    minimumWidth=False,
                    widthProperty='fixed',
                    loadImmediately=False,
                    retain=False)
            
            mc.workspaceControl(WS_CONTROL_NAME, e=True, vis=True)
            mc.workspaceControl(WS_CONTROL_NAME, e=True, r=True, rs=True)  # raise it
        else:
            if mc.window(WINDOW_NAME, ex=True):
                mc.deleteUI(WINDOW_NAME, window=True)

            self.mainWin = mc.window(WINDOW_NAME, title=WINDOW_TITLE, s=True, mnb=False, mxb=False)
            self.buildUI()
            mc.showWindow(self.mainWin)

    def closeUI(self):
        if mc.workspaceControl(WS_CONTROL_NAME, q=True, exists=True):
            mc.workspaceControl(WS_CONTROL_NAME, e=True, close=True)
            # mc.deleteUI(WS_CONTROL_NAME, control=True)

    def buildUI(self):
        """
        The maya.cmds UI function. 

        """
        self.mainCol = mc.columnLayout(adj=True, rs=0, co=['both', 0])
        mc.frameLayout(label='by Nuternativ : nuttynew@hotmail.com', fn='smallObliqueLabelFont', mh=5, mw=5)

        mc.columnLayout(adj=True, rs=0, co=['both', 5])
        mc.rowColumnLayout(nc=4, co=([1, 'left', 0], [2, 'left', 0], [3, 'left', 100], [4, 'left', 10]))
        mc.text(l='tolerance')
        mc.floatField(self.tolFloatField, w=58, v=DEFAULT_TOL, pre=6, min=0.0, cc=lambda *args: self.changeTol())
        mc.button(l='Save', w=33, c=lambda *args: self.saveSettings())
        mc.button(l='Load', w=33, c=lambda *args: self.loadSettings())
        mc.setParent('..')
        mc.setParent('..')

        mc.columnLayout(adj=True, rs=5, co=['both', 0])
        mc.text(self.statusTxt, l='No Base Mesh Data.', bgc=[0.4, 0, 0], h=25)
        mc.rowColumnLayout(nc=2, co=([1, 'left', 0], [2, 'left', 3]))
        mc.textScrollList(self.slotTsl, w=175, h=100, nr=self.slotNum, allowMultiSelection=False, 
                    sc=lambda *args: self.changeSlot())
        mc.columnLayout(adj=True, rs=5, co=['both', 0])
        mc.rowColumnLayout(nc=3, co=([1, 'left', 0], [2, 'left', 5], [3, 'left', 5]), rs=(3,3))
        mc.button(l='+', h=15, w=30, c=lambda  *args: self.addSubset())
        mc.text(l='Sub Set')
        mc.button(l='-', h=15, w=30,  c=lambda  *args: self.removeSubset())
        mc.setParent('..')
        mc.textScrollList(self.subsetTsl, w=50, h=100, nr=100, allowMultiSelection=True)
        mc.button(l='Select', c=lambda  *args: self.selectSubset('replace'))
        mc.rowColumnLayout(nc=3, co=([1, 'left', 0], [2, 'left', 7], [3, 'left', 7]), rs=(3,3))
        mc.button(l='+', w=33, c=lambda  *args: self.selectSubset('add'))
        mc.button(l='-', w=33,  c=lambda  *args: self.selectSubset('deselect'))
        mc.button(l='tgl', w=33,  c=lambda  *args: self.selectSubset('toggle'))
        
        mc.setParent('..')
        mc.setParent('..')
        mc.setParent('..')

        mc.columnLayout(adj=True, rs=5, co=['both', 0])
        mc.button(l='Get Base Mesh Data', c=lambda *args: self.assignSlot(), h=35)
        mc.setParent('..')

        mc.rowColumnLayout(nc=3, co=([1, 'left', 23], [2, 'left', 10], [3, 'left', 10]))
        mc.button(l='Check Sym', h=20, w=100, c=lambda *args: self.checkSymmetry())
        mc.button(l='Sel Moved', h=20, w=70, c=lambda *args: self.getMovedVtx())
        mc.button(l='Clear Slot', c=lambda *args: self.clearSlot())
        mc.setParent('..')

        mc.frameLayout( label='Operations', mh=5, mw=5, cll=False, cl=False)

        mc.rowColumnLayout(nc=3, co=([1, 'left', 0], [2, 'left', 3], [3, 'left', 3]))
        mc.floatField(self.revertFloatFld, v=100, max=100, min=0, pre=2, w=42, cc=lambda *args: self.fillRevertMesh())
        mc.floatSliderGrp(self.revertSlider, v=100, max=100, min=0, cw2=[170, 10], f=False, pre=2, el='%',
                        dc=lambda *args: self.dragRevertMesh(), cc=lambda *args: self.endDragRevertMesh())
        mc.button(l='Revert', c=lambda *args: self.revertToBase())
        mc.setParent('..')


        mc.rowColumnLayout(nc=3, rs=([1, 5]), co=([1, 'left', 0], [2, 'left', 20], [3, 'left', 20]))
        mc.button(l='M >>', w=80, h=30, c=lambda *args: self.mirror_neg())
        mc.button(l='Flip', w=80, h=30, c=lambda *args: self.flip())
        mc.button(l='<< M', w=80, h=30, c=lambda *args: self.mirror_pos())
        mc.button(l='Subtract', w=80, h=25, c=lambda *args: self.subtractFromMeshA())
        mc.button(l='Copy n Flip', w=80, h=25, c=lambda *args: self.copyAndFlip())
        mc.button(l='Add', w=80, h=25, c=lambda *args: self.addFromMeshA())
        mc.setParent('..')

        mc.rowColumnLayout(nc=3, co=([1, 'left', 0], [2, 'left', 3], [3, 'left', 11]))
        mc.floatField(self.copyFloatFld, v=0, max=100, min=0, pre=2, w=42, cc=lambda *args: self.fillCopyMesh())
        mc.floatSliderGrp(self.copySlider, v=0, max=100, min=0, cw2=[170, 10], f=False, pre=2, el='%',
                        dc=lambda *args: self.dragCopyMesh(), cc=lambda *args: self.endDragCopyMesh())
        mc.button(l='Copy', c=lambda *args: self.copyFromMeshA())
        mc.setParent('..')
        
        self.initSlot()

    def saveSettings(self):
        mydoc_path = os.path.expanduser('~')
        path = mc.fileDialog2(ds=1, cap='Save settigns', dir=mydoc_path, fm=0, ff='*.pkl')

        if not path:
            return

        # write out settings
        with open(path[0], 'wb') as handle:
            cPickle.dump(self.objs, handle, cPickle.HIGHEST_PROTOCOL)

    def loadSettings(self):
        mydoc_path = os.path.expanduser('~')
        path = mc.fileDialog2(ds=1, cap='Load settigns', dir=mydoc_path, fm=1, ff='*.pkl')
        if not path:
            return

        data = None
        with open(path[0], 'rb') as handle:
            data = cPickle.load(handle)
        if any(data):
            self.objs = data
        else:
            return

        self.initSlot()
        for i, smrObj in enumerate(self.objs):
            if not smrObj:
                continue

            # smrObj.caller('analyzeBaseGeo')
            if not smrObj.baseMesh:
                continue

            self.focusIndx = i
            meshLn = smrObj.baseMesh
            meshSn = meshLn.split('|')[-1]

            tslIndx = (self.focusIndx+1)
            mc.textScrollList(self.slotTsl, e=True, rii=tslIndx)
            mc.textScrollList(self.slotTsl, e=True, ap=(tslIndx, meshSn))
            mc.textScrollList(self.slotTsl, e=True, selectIndexedItem=tslIndx)

            if smrObj.baseMeshData:
                self.statuses[self.focusIndx] = True
                self.setStatusTxt(True)
            else:
                self.statuses[self.focusIndx] = False
                self.setStatusTxt(False)
        self.refreshSubsetTsl() 



    def selectSubset(self, mode):
        smrObj = self.getFocusObj()
        if smrObj:
            focusSubsetIndxs = mc.textScrollList(self.subsetTsl, q=True, selectIndexedItem=True)
            if focusSubsetIndxs:
                allItems = mc.textScrollList(self.subsetTsl, q=True, allItems=True)
                numItems = range(mc.textScrollList(self.subsetTsl, q=True, numberOfItems=True))

                subsetNames = []
                for index, txt in zip(numItems, allItems):
                    if (index+1) in focusSubsetIndxs:
                        subsetNames.append(txt)

                smrObj.selectSubset(subsetNames, mode)

    def addSubset(self):
        smrObj = self.getFocusObj()
        if smrObj and smrObj.getUserSelection():
            res = mc.promptDialog(title='Subset Name', 
                                message='Enter Name: ',
                                button=('OK','Cancel'),
                                defaultButton='OK', cancelButton='Cancel',
                                dismissString='Cancel')
            if res and res != 'Cancel':
                txt = mc.promptDialog(q=True, text=True)
                if txt:
                    addRes = smrObj.addSubset(txt)
                    if addRes:
                        self.refreshSubsetTsl()

    def removeSubset(self):
        smrObj = self.getFocusObj()
        if smrObj:
            focusSubsetIndxs = mc.textScrollList(self.subsetTsl, q=True, selectIndexedItem=True)
            if focusSubsetIndxs:
                allItems = mc.textScrollList(self.subsetTsl, q=True, allItems=True)
                numItems = range(mc.textScrollList(self.subsetTsl, q=True, numberOfItems=True))
                for index, txt in zip(numItems, allItems):
                    if (index+1) in focusSubsetIndxs:
                        smrObj.removeSubset(txt)
                self.refreshSubsetTsl()

    def refreshSubsetTsl(self):
        smrObj = self.getFocusObj()
        if smrObj:
            mc.textScrollList(self.subsetTsl, e=True, ra=True)
            for subsetName in smrObj.subset.keys():
                mc.textScrollList(self.subsetTsl, e=True, append=subsetName)


    def initSlot(self):
        mc.textScrollList(self.slotTsl, e=True, ra=True)
        for i in xrange(self.slotNum):
            mc.textScrollList(self.slotTsl, e=True, append=DEFAULT_EMPTY_TEXT)

        mc.textScrollList(self.slotTsl, e=True, selectIndexedItem=1)

    def copyAndFlip(self):
        smrObj = self.getFocusObj()
        if smrObj:
            sels = mc.ls(sl=True, l=True)
            # smrObj.caller('copyFromMeshA')
            # for mesh in smrObj.focusVtx:
            #   mc.select(mesh, r=True)
            #   smrObj.caller('flip')
            pairs = zip(sels[::2], sels[1::2])
            for s, d in pairs:
                mc.select([s, d], r=True)
                smrObj.caller('copyFromMeshA')
                mc.select(d, r=True)
                smrObj.caller('flip')

            mc.select(sels, r=True)

    def changeTol(self):
        value = mc.floatField(self.tolFloatField, q=True, v=True)
        smrObj = self.objs[self.focusIndx]
        if smrObj:
            smrObj.changeTol(value=value)

    def getFocusIndx(self):
         # get ui slot selection
        self.focusIndx = mc.textScrollList(self.slotTsl, q=True, selectIndexedItem=True)[0] - 1

    def assignSlot(self):
        self.getFocusIndx()
        value = mc.floatField(self.tolFloatField, q=True, v=True)
        smrObj = SymMeshReflector(tol=value)
        self.objs[self.focusIndx] = smrObj


        smrObj.caller('analyzeBaseGeo')
        if not smrObj.baseMesh:
            return

        meshLn = smrObj.baseMesh
        meshSn = meshLn.split('|')[-1]

        tslIndx = (self.focusIndx+1)
        mc.textScrollList(self.slotTsl, e=True, rii=tslIndx)
        mc.textScrollList(self.slotTsl, e=True, ap=(tslIndx, meshSn))
        mc.textScrollList(self.slotTsl, e=True, selectIndexedItem=tslIndx)

        if smrObj.baseMesh and smrObj.baseMeshData:
            self.statuses[self.focusIndx] = True
            self.setStatusTxt(True)
        else:
            self.statuses[self.focusIndx] = False
            self.setStatusTxt(False)

    def clearSlot(self):
        self.getFocusIndx()
        self.objs[self.focusIndx] = None

        tslIndx = (self.focusIndx+1)
        mc.textScrollList(self.slotTsl, e=True, rii=tslIndx)
        mc.textScrollList(self.slotTsl, e=True, ap=(tslIndx, DEFAULT_EMPTY_TEXT))
        mc.textScrollList(self.slotTsl, e=True, selectIndexedItem=tslIndx)

        self.statuses[self.focusIndx] = False
        self.setStatusTxt(False)

    def getFocusObj(self):
        smrObj = self.objs[self.focusIndx]
        return smrObj

    def setStatusTxt(self, status):
        if status == True:
            mc.text(self.statusTxt, e=True, bgc=([0, 0.4, 0]), l='Loaded.')
        else:
            mc.text(self.statusTxt, e=True, bgc=([0.4, 0, 0]), l='No Base Mesh Data.')

    def changeSlot(self):
        self.getFocusIndx()
        smrObj = self.getFocusObj()

        self.setStatusTxt(self.statuses[self.focusIndx])
        if smrObj:
            mc.floatField(self.tolFloatField, e=True, v=smrObj.tol)
            self.refreshSubsetTsl()

    def getMovedVtx(self):
        smrObj = self.getFocusObj()
        if smrObj:
            smrObj.caller('getMovedVtx')

    def checkSymmetry(self):
        smrObj = self.getFocusObj()
        if smrObj:
            smrObj.caller('checkSymmetry')

    def revertToBase(self):
        smrObj = self.getFocusObj()
        if smrObj:
            smrObj.caller('revertToBase')

    def mirror_neg(self):
        smrObj = self.getFocusObj()
        if smrObj:
            smrObj.caller('mirror_neg')

    def flip(self):
        smrObj = self.getFocusObj()
        if smrObj:
            smrObj.caller('flip')

    def mirror_pos(self):
        smrObj = self.getFocusObj()
        if smrObj:
            smrObj.caller('mirror_pos')

    def subtractFromMeshA(self):
        smrObj = self.getFocusObj()
        if smrObj:
            smrObj.caller('subtractFromMeshA')

    def copyFromMeshA(self):
        smrObj = self.getFocusObj()
        if smrObj:
            smrObj.caller('copyFromMeshA')

    def addFromMeshA(self):
        smrObj = self.getFocusObj()
        if smrObj:
            smrObj.caller('addFromMeshA')

    def fillRevertMesh(self):
        smrObj = self.getFocusObj()
        if smrObj:
            percent = mc.floatField(self.revertFloatFld, q=True, value=True)
            smrObj.fillRevertMesh(percent=percent)
        mc.floatField(self.revertFloatFld, e=True, value=100)

    def dragRevertMesh(self):
        smrObj = self.getFocusObj()
        if smrObj:
            percent = mc.floatSliderGrp(self.revertSlider, q=True, value=True)
            smrObj.dragRevertMesh(percent=percent)
             #set the float field
            mc.floatField(self.revertFloatFld, e=True, value=percent)

    def endDragRevertMesh(self, *args):
        smrObj = self.getFocusObj()
        if smrObj:
            smrObj.endDragRevertMesh()
        #set the float field and float slider back to 100
        mc.floatSliderGrp(self.revertSlider, e=True, value=100)   
        mc.floatField(self.revertFloatFld, e=True, value=100)
        
    def dragCopyMesh(self):
        smrObj = self.getFocusObj()
        if smrObj:
            percent = mc.floatSliderGrp(self.copySlider, q=True, value=True)

            smrObj.dragCopyMesh(percent=percent)
             #set the float field
            mc.floatField(self.copyFloatFld, e=True, value=percent)

    def fillCopyMesh(self):
        smrObj = self.getFocusObj()
        if smrObj:
            percent = mc.floatField(self.copyFloatFld, q=True, value=True)
            smrObj.fillCopyMesh(percent=percent)
        mc.floatField(self.copyFloatFld, e=True, value=0)

    def endDragCopyMesh(self, *args):
        smrObj = self.getFocusObj()
        if smrObj:
            smrObj.endDragCopyMesh()

        #set the float field and float slider back to 0
        mc.floatSliderGrp(self.copySlider, e=True, value=0)   
        mc.floatField(self.copyFloatFld, e=True, value=0)

class SymMeshReflector(object):
    """
    Tool for mirroring mesh modification on one side to the other.
    By given a symmetry mesh once, the script can manipulate another geometry with the same 
    topology. 

    """

    def __init__(self, tol=0.001):

        # global vars
        self.tol = tol
        self.baseVtxNum = 0
        self.revertSliderDragging = False
        self.copySliderDragging = False

        # base mesh vars
        self.baseMesh = None
        self.baseMeshData = []
        self.meshCenter = []
        
        self.noneIndx = []
        self.filterIndx = {'pos':[], 'neg':[]}

        self.midDict = {}
        self.pairDict = {}

        # multiple action vars
        self.focusVtx = collections.defaultdict(list)  #{mesh:[vtx1, vtx2, ...]}
        self.focusIndx = collections.defaultdict(list)  #{mesh:[indx1, indx2, ...]}
        self.currTrans = collections.defaultdict(list)
        self.relTrans = collections.defaultdict(list)

        # meshA vars
        self.meshA = None
        self.meshAData = []
        self.meshACenter = []

        self.filterAIndx = {'pos':[], 'neg':[]}
        self.noneAIndx = []
        self.midAPosIndx = []
        self.midANegIndx = []

        self.midADict = {}
        self.pairADict = {}

        # meshA action vars
        self.movedAVtxs = []
        self.movedAIndxs = []
        self.meshAFocusVtxs = []
        self.meshAFocusIndxs = []

        self.subset = defaultdict(list)  # {setName:[0, 1, ...]}

        # ui
        self.statusTxt = None

    def addSubset(self, subsetName='subset'):
        self.subset[subsetName] = []
        for mesh, indxs in self.focusIndx.iteritems():
            self.subset[subsetName].extend(indxs)

        return True

    def selectSubset(self, subsetNames, mode):
        if self.getUserSelection():
            indxs = []
            for name in subsetNames:
                indxs.extend(self.subset[name])

            indxs = list(set(indxs))
            if indxs:
                toSels = []
                meshes = set()
                for mesh in self.focusVtx:
                    toSels.extend(self.getVtxFromIndx(mesh, indxs))
                    meshes.add(mesh)

                meshes = list(meshes)
                mc.hilite(meshes)

                selArg = {mode:True}
                mc.select(toSels, **selArg)

    def removeSubset(self, subsetName):
        if not subsetName in self.subset.keys():
            return

        del self.subset[subsetName]

    def addFromMeshA(self):
        """
        Add self.meshA modifications to each items in self.focusVtx.

        """
        # mc.undoInfo(ock=True)

        for mesh in self.focusVtx:
            #get all vtx current position
            points = self.getCurrOsTrans(mesh)

            for v, i in zip(self.focusVtx[mesh], self.focusIndx[mesh]):
                if self.checkEqualPoint(self.meshAData[i], self.baseMeshData[i]) == True:
                    continue

                relTrans = self.getRelativeTrans(self.meshAData[i], self.baseMeshData[i])
                points[i] = (points[i][0]+relTrans[0], points[i][1]+relTrans[1], points[i][2]+relTrans[2])
                # mc.move(currTrans[i][0]+relTrans[0], currTrans[i][1]+relTrans[1], currTrans[i][2]+relTrans[2], v, ls=True)
            arg = pointListToStrArg(points)
            mc.setMeshVertex(mesh, p=arg)
        # mc.undoInfo(cck=True)

    def getGeoData(self, mesh=None):
        """
        Get all vertices position for self.mesh (no mirroring or pairing data)

        """
        if not mesh:
            try: 
                mesh = mc.ls(sl=True, l=True)[0]
            except:
                return

        self.baseMeshData = []

        #iterate thru each mesh 
        mfnMesh = self.getMFnMesh(obj=mesh)
        pArray = om.MPointArray()   
        mfnMesh.getPoints(pArray, om.MSpace.kObject)

        for i in xrange(0, pArray.length()):
            self.baseMeshData.append([pArray[i].x, pArray[i].y, pArray[i].z])

    def analyzeBaseGeo(self, mesh=None):
        """
        Analyze a mesh to be used as base geometry. Collect all data, pair vtxs, mids, etc.. 

        """
        #reset base mesh data
        self.baseMesh = None
        self.baseMeshData = []
        posIndx, negIndx, self.noneIndx = [], [], []
        self.filterIndx = {'pos':[], 'neg':[]}
        self.meshCenter = []
        self.pairDict = {}
        self.midDict = {}

        if not mesh:
            try: 
                mesh = mc.ls(sl=True, l=True)[0]
            except:
                om.MGlobal.displayWarning('Please select base mesh.')
                return 

        self.baseMesh = mesh

        #iterate thru each mesh 
        try:
            mfnMesh = self.getMFnMesh(obj=self.baseMesh)
        except:
            return
        
        if not mfnMesh:
            return

        pWArray = om.MPointArray()   
        mfnMesh.getPoints(pWArray, om.MSpace.kWorld)
        pLArray = om.MPointArray()   
        mfnMesh.getPoints(pLArray, om.MSpace.kObject)
        pos, neg = [], []

        #finding the mesh center
        self.meshCenter = mc.objectCenter(self.baseMesh, l=False)
        # self.meshCenter = mc.xform(self.baseMesh, q=True, rotatePivot=True)

        #for each vertex, store all in orig and get those in the middle
        self.baseVtxNum = pWArray.length()
        for i in xrange(0, self.baseVtxNum):
            self.baseMeshData.append([pLArray[i].x, pLArray[i].y, pLArray[i].z])
            self.midDict[i] = False

            #found that it is in the mid
            if abs(pWArray[i].x - self.meshCenter[0]) <= self.tol:
                self.filterIndx['pos'].append(i)
                self.filterIndx['neg'].append(i)
                self.midDict[i] = True
                continue

            if pWArray[i].x > self.meshCenter[0]:
                pos.append(i)
            else:
                neg.append(i)

        #matching left and right vertex
        for p in pos:
            mirrorPos = om.MPoint((pLArray[p].x*-1), pLArray[p].y, pLArray[p].z)
            for n in neg:
                if pLArray[n].distanceTo(mirrorPos) <= self.tol:
                    self.filterIndx['neg'].append(n)
                    self.filterIndx['pos'].append(p)
                    self.pairDict[p] = n
                    self.pairDict[n] = p
                    neg.pop(neg.index(n))
                    break
            else:
                self.noneIndx.append(p)

        #add negative verts that'was left unmatched to none    
        self.noneIndx.extend(neg)

        if self.noneIndx:
            nonSymVtxs = self.getVtxFromIndx(self.baseMesh, self.noneIndx)
            mc.select(nonSymVtxs, r=True)
            om.MGlobal.displayWarning('Mesh is NOT symmetrical. Not all vertex can be mirrored.')
        else:
            mc.select(self.baseMesh, r=True)
            om.MGlobal.displayInfo('Mesh is symmetrical.')

    def analyzeAGeo(self, mesh=None):
        """
        Analyze a mesh to be used as self.meshA. Collect all data, pair vtxs, mids, etc.. 
        Warn user if the mesh is not all symmetry. Called by 'check symmetry' action.

        """
        if not mesh:
            try: 
                mesh = mc.sl(sl=True, l=True)[0]
            except:
                return 

        #reset data
        self.meshAData = []
        posAIndx, negAIndx, midAIndx = [], [], []
        self.noneAIndx = []
        self.filterAIndx = {'pos':[], 'neg':[]}
        self.meshACenter = []
        self.pairADict = {}
        self.midADict = {}

        #iterate thru each mesh 
        try:
            mfnMesh = self.getMFnMesh(obj=mesh)
        except:
            return

        if not mfnMesh:
            return

        pWArray = om.MPointArray()   
        mfnMesh.getPoints(pWArray, om.MSpace.kWorld)
        pLArray = om.MPointArray()   
        mfnMesh.getPoints(pLArray, om.MSpace.kObject)
        pos, neg = [], []

        #finding the mesh center
        meshAData = mc.listRelatives(mesh, p=True, f=True)[0]
        self.meshACenter = mc.objectCenter(mesh, l=False)

        #for each vertex, store all in orig and get those in the middle
        vtxNum = pWArray.length()

        for i in xrange(0, vtxNum):
            self.meshAData.append([pLArray[i].x, pLArray[i].y, pLArray[i].z])
            self.midADict[i] = False

            #found that it is in the mid
            if abs(pWArray[i].x - self.meshACenter[0]) <= self.tol:
                self.filterAIndx['pos'].append(i)
                self.filterAIndx['neg'].append(i)
                self.midADict[i] = True
                continue

            if pWArray[i].x > self.meshACenter[0]:
                pos.append(i)
            else:
                neg.append(i)

        #matching left and right vertex
        for p in pos:
            find = om.MPoint((pWArray[p].x*-1)+(2*self.meshACenter[0]), pWArray[p].y, pWArray[p].z)
            for n in neg:
                if pWArray[n].distanceTo(find) <= self.tol:
                    self.filterAIndx['neg'].append(n)
                    self.filterAIndx['pos'].append(p)
                    self.pairADict[p] = n
                    self.pairADict[n] = p
                    neg.pop(neg.index(n))
                    break
            else:
                self.noneAIndx.append(p)


        #add negative verts that'was left unmatched to none    
        self.noneAIndx.extend(neg)
        if self.noneAIndx:
            nonSymVtxs = self.getVtxFromIndx(mesh, self.noneAIndx)
            mc.select(nonSymVtxs, r=True)
            om.MGlobal.displayWarning('Mesh is NOT symmetrical. Not all vertex can be mirrored.')
        else:
            mc.select(mesh, r=True)
            om.MGlobal.displayInfo('Mesh is symmetrical.')

    def caller(self, op, sels=[]):
        """
        Caller function for all the actions.

        """
        mc.waitCursor(state=True)

        if op in ['mirror_pos', 'mirror_neg']:
            if self.getUserSelection(sels) == True:
                self.mirrorVtx(filterIndxList=self.filterIndx[op.split('_')[-1]])
            else:
                om.MGlobal.displayError('Mirror : Select a mesh to mirror.')

        elif op == 'revertToBase':
            if self.getUserSelection(sels) == True:
                self.revertVtxToBase()

        elif op == 'flip':
            if self.getUserSelection(sels) == True:
                self.flipVtx(filterIndxList=self.filterIndx['pos'])

        elif op == 'flipApi':
            if self.getUserSelection(sels) == True:
                self.flipVtxApi()

        elif op == 'copyFromMeshA':
            if self.getMeshASelection(child=True) == True:
                self.getAGeoData(mesh=self.meshA)
                self.copyFromMeshA()
            else:
                om.MGlobal.displayError('Copy : Select the source mesh, then destination meshes with the same vertex count.')

        elif op == 'addFromMeshA':
            if self.getMeshASelection(child=True) == True:
                self.getAGeoData(mesh=self.meshA)
                self.addFromMeshA()
            else:
                om.MGlobal.displayError('Add : Select the source mesh, then destination meshes with the same vertex count.')

        elif op == 'subtractFromMeshA':
            if self.getMeshASelection(child=True) == True:
                self.getAGeoData(mesh=self.meshA)
                self.subtractFromMeshA()
            else:
                om.MGlobal.displayError('Subtract : Select the source mesh, then destination meshes with the same vertex count.')

        elif op == 'checkSymmetry':
            self.getMeshASelection(child=False)
            self.analyzeAGeo(mesh=self.meshA)

        elif op == 'getMovedVtx':
            if self.getUserSelection(sels) == True:
                self.getMovedVtx(sel=True)

        elif op == 'analyzeBaseGeo':
            self.analyzeBaseGeo()
        
        mc.waitCursor(state=False)

    def copyFromMeshA(self):
        """
        Copy self.meshA modifications to each items in self.focusVtx.

        """
        # mc.undoInfo(ock=True)
        for mesh, vertices in self.focusVtx.iteritems():
            # get all vtx current position
            points = self.getCurrOsTrans(mesh)
            for v, i in zip(vertices, self.focusIndx[mesh]):
                if self.checkEqualPoint(points[i], self.meshAData[i]) == True:
                    continue
                # mc.move(self.meshAData[i][0], self.meshAData[i][1], self.meshAData[i][2], v, ls=True)
                points[i] = (self.meshAData[i][0], self.meshAData[i][1], self.meshAData[i][2])
            arg = pointListToStrArg(points)
            mc.setMeshVertex(mesh, p=arg)
        # mc.undoInfo(cck=True)

    def checkSymPoint(self, pointA, pointB):
        """
        Accept 2 point positions(A and B). Calculate if pointB is the mirror of point A under the tolerance.
        Return: boolean

        """
        mPointA = om.MPoint(pointA[0], pointA[1], pointA[2])
        mPointB = om.MPoint(pointB[0], pointB[1], pointB[2])
        mirMPoint = om.MPoint((pointA[0]*-1) + (2*self.meshCenter[0]), pointA[1], pointA[2])
        return mPointB.distanceTo(mirMPoint) <= self.tol

    def checkEqualPoint(self, pointA, pointB):
        """
        Accept 2 points position, see if pointA is equal to point B under the tolerance.
        Return: boolean

        """
        mPointA = om.MPoint(pointA[0], pointA[1], pointA[2])
        mPointB = om.MPoint(pointB[0], pointB[1], pointB[2])
        return mPointA.distanceTo(mPointB) <= self.tol

    def changeTol(self, value):
        print value
        self.tol = value

    def fillRevertMesh(self, percent):
        if self.getUserSelection() == True:
            self.getAGeoData(self.meshA)
            self.getRelTransToBase()

            self.revertVtxByPercent(src=self.baseMeshData, percent=percent * 0.01)
            self.endDragRevertMesh()

    def endDragRevertMesh(self, *args):
        if self.revertSliderDragging == True:        
            mc.undoInfo(cck=True)

        self.revertSliderDragging = False

    def getRelTransToBase(self):
        self.relTrans = {}

        for mesh, vertices in self.focusVtx.iteritems():
            currTrans = self.getCurrOsTrans(mesh)
            self.currTrans[mesh] = currTrans
            rels = {}
            for v, i in zip(vertices, self.focusIndx[mesh]):
                r = self.getRelativeTrans(currTrans[i], self.baseMeshData[i])
                if self.checkEqualPoint(r, [0.0, 0.0, 0.0]) == True:
                    continue
                else:
                    rels[i] = r
            self.relTrans[mesh] = rels

    def dragRevertMesh(self, percent):
        if self.revertSliderDragging == False:
            if self.getUserSelection() == True:
                self.getAGeoData(self.meshA)
                self.getRelTransToBase()
                mc.undoInfo(ock=True)

                self.revertSliderDragging = True

        if self.revertSliderDragging == True:
            self.revertVtxByPercent(src=self.baseMeshData, percent=percent*0.01)
    
    def revertVtxByPercent(self, src, percent):
        """
        Revert self.meshA(one object) to base mesh by the percent given.

        """ 
        for mesh, rels in self.relTrans.iteritems():
            points = self.currTrans[mesh]
            for i, r in rels.iteritems():
                # v = '%s.vtx[%s]' %(mesh, i)
                # mc.move(src[i][0]+r[0]*percent, 
                #     src[i][1]+r[1]*percent, 
                #     src[i][2]+r[2]*percent, 
                #     v, ls=True)
                points[i] = (src[i][0]+r[0]*percent, src[i][1]+r[1]*percent, src[i][2]+r[2]*percent)
            arg = pointListToStrArg(points)
            mc.setMeshVertex(mesh, p=arg)

    def copyVtxByPercent(self, orig, percent):
        """
        Copy self.meshA(one object) to select mesh by the percent given.

        """
        for mesh, rels in self.relTrans.iteritems():
            points = list(orig[mesh])
            for i, r in rels.iteritems():
                # v = '%s.vtx[%s]' %(mesh, i)
                # mc.move(orig[mesh][i][0]+r[0]*percent, 
                #     orig[mesh][i][1]+r[1]*percent, 
                #     orig[mesh][i][2]+r[2]*percent, 
                #     v, ls=True)
                points[i] = (orig[mesh][i][0]+r[0]*percent, orig[mesh][i][1]+r[1]*percent, orig[mesh][i][2]+r[2]*percent)
            arg = pointListToStrArg(points)
            mc.setMeshVertex(mesh, p=arg)

    def getRelTransToMeshA(self):
        self.relTrans = {}
        for mesh, vertices in self.focusVtx.iteritems():
            self.currTrans[mesh] = self.getCurrOsTrans(mesh)
            rels = {}
            for v, i in zip(vertices, self.focusIndx[mesh]):
                r = self.getRelativeTrans(self.meshAData[i], self.currTrans[mesh][i])
                if self.checkEqualPoint(r, [0.0, 0.0, 0.0]) == True:
                    continue
                else:
                    rels[i] = r
            self.relTrans[mesh] = rels

    def dragCopyMesh(self, percent):
        if self.copySliderDragging == False:
            
            if self.getMeshASelection(child=True) == True:
                self.getAGeoData(self.meshA)
                self.getRelTransToMeshA()
                mc.undoInfo(ock=True)

                self.copySliderDragging = True

        if self.copySliderDragging == True:
            self.copyVtxByPercent(orig=self.currTrans, percent=percent*0.01)

    def fillCopyMesh(self, percent):
        if self.getMeshASelection(child=True) == True:
            self.getAGeoData(self.meshA)
            self.getRelTransToMeshA()

            self.copyVtxByPercent(orig=self.currTrans, percent=percent*0.01)
            self.endDragCopyMesh()

    def endDragCopyMesh(self, *args):
        if self.copySliderDragging == True:        
            mc.undoInfo(cck=True)

        self.copySliderDragging = False

    def filterSelection(self):
        """
        Filter all focus var to be only those that has the same vertex count as self.baseMesh.

        """
        res = True
        toDel = []
        for mesh in self.focusVtx:
            meshVtxNum = mc.polyEvaluate(mesh, v=True)
            if meshVtxNum != self.baseVtxNum:
                toDel.append(mesh)

        for mesh in toDel:
            del(self.focusVtx[mesh])
            del(self.focusIndx[mesh])


        if not self.focusIndx:
            res = False

        return res

    def flipVtx(self, filterIndxList):
        """
        Flip each focus mesh.
        Args: filterIndexList : List of vertex that will be use as filter for user selection to prevent
                                user from selecting vertex from both sides. 

        """
        # startTime = time.time()
        for mesh in self.focusVtx:
            #get all vtx current position
            points = self.getCurrOsTrans(mesh)
            new_points = list(points)

            #filter out vtx
            filterIndxs = list(set(self.focusIndx[mesh]).intersection(filterIndxList))
            filterVtxs = self.getVtxFromIndx(mesh, filterIndxs)

            for v, i in zip(filterVtxs, filterIndxs):

                #if it's in the middle of the mesh
                if self.midDict[i] == True:
                    # mc.move(currTrans[i][0]*-1, currTrans[i][1], currTrans[i][2], v, ls=True)
                    new_points[i] = (points[i][0]*-1, points[i][1], points[i][2])

                #it's on the left or right side
                else:
                    c = self.pairDict[i]
                    # if both verts are already sym, skip to increse speed of moving stady point
                    if self.checkSymPoint(points[i], points[c]) == True:
                        continue

                    # cVtx = '%s.vtx[%i]' %(mesh, c)
                    new_points[c] = (points[i][0]*-1, points[i][1], points[i][2])
                    new_points[i] = (points[c][0]*-1, points[c][1], points[c][2])
                    # mc.move(currTrans[i][0]*-1, currTrans[i][1], currTrans[i][2], cVtx, ls=True)
                    # mc.move(currTrans[c][0]*-1, currTrans[c][1], currTrans[c][2], v, ls=True)
            arg = pointListToStrArg(new_points)
            mc.setMeshVertex(mesh, p=arg)

    def flipVtxApi(self):
        """
        Flip each focus mesh.
        Args: filterIndexList : List of vertex that will be use as filter for user selection to prevent
                                user from selecting vertex from both sides. 

        """
        for mesh in self.focusVtx:
            # get MFnMesh 
            mFnMesh = self.getMFnMesh(mesh)
            dagPath = self.getDagPath(mesh)

            # get all points
            vtxPointArray = om.MPointArray()
            mFnMesh.getPoints(vtxPointArray, om.MSpace.kObject)      

            resultPointArray = om.MPointArray()
            geoIterator = om.MItGeometry(dagPath)

            cPos = {}
            while( not geoIterator.isDone()):
                pointPosition = geoIterator.position()
                
                vIndx = geoIterator.index()

                if self.midDict[vIndx] == True:
                    pointPosition.x = pointPosition.x*-1
                    
                else:
                    c = self.pairDict[vIndx]
                    
                    if vIndx in cPos.keys():
                        pointPosition.x = cPos[vIndx].x*-1
                        pointPosition.y = cPos[vIndx].y 
                        pointPosition.z = cPos[vIndx].z
                    else:
                        cPos[c] = vtxPointArray[vIndx]     
                        pointPosition.x = vtxPointArray[c].x*-1
                        pointPosition.y = vtxPointArray[c].y 
                        pointPosition.z = vtxPointArray[c].z 

                resultPointArray.append(pointPosition)    
                geoIterator.next()

            geoIterator.setAllPositions(resultPointArray)

    def getAGeoData(self, mesh=None):
        """
        Get all vertices position for self.meshA

        """
        if not mesh:
            try: 
                mesh = mc.ls(sl=True, l=True)[0]
            except:
                return

        self.meshAData = []
        mfnMesh = self.getMFnMesh(obj=mesh)
        if not mfnMesh:
            return

        pArray = om.MPointArray()   
        mfnMesh.getPoints(pArray, om.MSpace.kObject)

        for i in xrange(0, pArray.length()):
            self.meshAData.append([pArray[i].x, pArray[i].y, pArray[i].z])

    def getUserSelection(self, sels=[]):
        """
        Get user selection for multiple mesh operations (mirror, flip).
        Stores data to : 
        self.focusVtx       : mesh:[vtx1, vtx2, vtx3, ...]
        self.focusIndx      : mesh:[0, 1, 2, ...]
        self.focusVtxList   : [vtx1, vtx2, vtx3, ...] 
        self.focusIndxList  : [0, 1, 2, ...]

        """
        self.resetFocusData()
        if not sels:
            sels = mc.filterExpand(fp=True, ex=True, sm=(12, 31, 32, 34))
            if not sels:
                return False

        for sel in sels:
            typ = mc.objectType(sel)
            if typ == 'transform':
                shps = mc.listRelatives(sel, f=True, ni=True, shapes=True, type='mesh')
                if shps:
                    shp = shps[0]
                    numVtx = mc.polyEvaluate(shp, v=True)
                    numVtxRange = xrange(0, numVtx)
                    vtxs = self.getVtxFromIndx(shp, numVtxRange)
                    self.focusVtx[shp].extend(vtxs)
                    self.focusIndx[shp].extend(numVtxRange)

            else:
                if '.vtx' in sel:
                    splits = sel.split('.vtx')
                    mesh = splits[0]
                    indx = int(splits[-1][1:-1])
                    self.focusVtx[mesh].append(sel)
                    self.focusIndx[mesh].append(indx)
                elif '.f' in sel or '.e' in sel:
                    verts = mc.polyListComponentConversion(sel, tv=True)
                    verts = mc.ls(verts, flatten=True)
                    for v in verts:
                        splits = v.split('.vtx')
                        mesh = splits[0]
                        indx = int(splits[-1][1:-1])
                        self.focusVtx[mesh].append(v)
                        self.focusIndx[mesh].append(indx)
                else:
                    numVtx = mc.polyEvaluate(sel, v=True)
                    numVtxRange = xrange(0, numVtx)
                    vtxs = self.getVtxFromIndx(sel, numVtxRange)
                    self.focusVtx[sel].extend(vtxs)
                    self.focusIndx[sel].extend(numVtxRange)

        res = self.filterSelection()

        return res

    def getMovedVtxMeshA(self):
        """
        Check if self.meshA vertices have moved from the base mesh and store those in self.moveAVtxs and self.moveAIndxs.

        """
        # Clear the vars
        self.movedAVtxs = []
        self.movedAIndxs = []

        for v, i in zip(self.meshAFocusVtxs, self.meshAFocusIndxs):
            if self.checkEqualPoint(self.meshAData[i], self.baseMeshData[i]) == False:
                self.movedAVtxs.append(v)
                self.movedAIndxs.append(i)

    def getMovedVtx(self, sel=True):
        """
        From focus data retrieved from function 'getUserSelection()'. Compare any of the vertices has moved from the original.
        Called by 'Select moved vertices' action.

        """
        toSel = []
        for mesh in self.focusVtx:
            #get all vtx current position
            currTrans = self.getCurrOsTrans(mesh)

            for v, i in zip(self.focusVtx[mesh], self.focusIndx[mesh]):
                if self.checkEqualPoint(currTrans[i], self.baseMeshData[i]) == False:
                    toSel.append(v)

        if sel == True:
            if toSel:
                mc.select(toSel, r=True)
            else:
                mc.select(cl=True)
                om.MGlobal.displayInfo('No vertex was modified.')

    def getVtxFromIndx(self, mesh, indxs):
        """
        Accept mesh(str) and index(int) combine string to retrieve vertices name.
        Return: List

        """
        return ['%s.vtx[%i]' %(mesh, i) for i in indxs]

    def getRelativeTrans(self, pointA, pointB):
        """
        Accept 2 point positions(A and B). Subtract B from A to get relative transform.
        Return: list(position)

        """
        return [pointA[0] - pointB[0], pointA[1] - pointB[1], pointA[2] - pointB[2]]

    def getCurrOsTrans(self, mesh):
        """
        Given mesh name as string, will iterate through each vertex and get its position.
        Return: list([vtx1.x, vtx1.y, vtx1.z], [...], ...)

        """
        mFnMesh = self.getMFnMesh(mesh)
        vtxPointArray = om.MPointArray()    
        mFnMesh.getPoints(vtxPointArray, om.MSpace.kObject)
            
        # return a list off all points positions
        return [[vtxPointArray[i][0], vtxPointArray[i][1], vtxPointArray[i][2]] for i in xrange(0, vtxPointArray.length())]

    def getMFnMesh(self, obj):
        """
        Given mesh name as string, return mfnMesh.

        """
        try:
            msl = om.MSelectionList()
            msl.add(obj)
            nodeDagPath = om.MDagPath()
            msl.getDagPath(0, nodeDagPath)
            return om.MFnMesh(nodeDagPath)
        except:
            return None

    def getDagPath(self, obj):
        """
        Given mesh name as string, return mfnMesh.

        """
        try:
            msl = om.MSelectionList()
            msl.add(obj)
            nodeDagPath = om.MDagPath()
            msl.getDagPath(0, nodeDagPath)
        except:
            return

        return nodeDagPath

    def getMeshASelection(self, sels=[], child=False):
        """
        Get user selection for operation that has other mesh involve in operation (subtract, add, copy).
        Stores data to : 
        self.meshA               : mesh 
        self.meshAFocusVtx       : mesh:[vtx1, vtx2, vtx3, ...]
        self.meshAFocusIndx      : mesh:[0, 1, 2, ...]

        """
        self.resetMeshAFocusData()

        if not sels:
            sels = mc.ls(sl=True, l=True, fl=True)

            if not sels:
                om.MGlobal.displayError('Select something!')
                return False

            if len(sels) <= child:
                return False

            if child == True:
                res = self.getUserSelection(sels=sels[1:])
                if res == False:
                    self.resetFocusData()
                    return res

        meshA = sels[0]

        if '.vtx' in meshA:
            splits = meshA.split('.vtx')
            self.meshA = splits[0]
            vtxNum = mc.polyEvaluate(self.meshA, v=True)
            for s in sels:
                splits = s.split('.vtx')
                if splits[0] == self.meshA:
                    self.meshAFocusVtxs.append(s)
                    self.meshAFocusIndxs.append(int(splits[-1][1:-1]))
        else:
            typ = mc.objectType(meshA)
            if typ == 'transform':
                shps = mc.listRelatives(meshA, ni=True, f=True, shapes=True, type='mesh')
                if shps:
                    self.meshA = shps[0]
                    vtxNum = mc.polyEvaluate(self.meshA, v=True)
                    indxRange = xrange(0, vtxNum)
                    self.meshAFocusVtxs = self.getVtxFromIndx(self.meshA, indxRange)
                    self.meshAFocusIndxs = indxRange

            elif typ == 'mesh':
                self.meshA = meshA
                vtxNum = mc.polyEvaluate(self.meshA, v=True)
                indxRange = xrange(0, vtxNum)
                self.meshAFocusVtxs = self.getVtxFromIndx(self.meshA, indxRange)
                self.meshAFocusIndxs = indxRange

        if vtxNum != len(self.baseMeshData):
            return False

        return True

    def mirrorVtx(self, filterIndxList):
        """
        Mirror each focus mesh to the other side.
        Args: filterIndexList : List of vertex that will be use as filter for user selection to prevent
                                user from selecting vertex from both sides. 

        """
        for mesh in self.focusVtx:
            #get all vtx current position
            points = self.getCurrOsTrans(mesh)
            new_points = list(points)
            #filter out vtx
            filterIndxs = list(set(self.focusIndx[mesh]).intersection(filterIndxList))
            filterVtxs = self.getVtxFromIndx(mesh, filterIndxs)

            for v, i in zip(filterVtxs, filterIndxs):

                #if it's in the middle of the mesh
                if self.midDict[i] == True:
                    # mc.move(self.baseMeshData[i][0], currTrans[i][1], currTrans[i][2], v, ls=True)
                    new_points[i] = (self.baseMeshData[i][0], points[i][1], points[i][2])

                #it's on the left or right side
                else:
                    c = self.pairDict[i]

                    # if both verts are already sym, skip to increse speed of moving stady point
                    if self.checkSymPoint(points[i], points[c]) == True:
                        continue

                    # cVtx = '%s.vtx[%i]' %(mesh, c)
                    # mc.move(currTrans[i][0]*-1, currTrans[i][1], currTrans[i][2], cVtx, ls=True)
                    new_points[c] = (points[i][0]*-1, points[i][1], points[i][2])
            arg = pointListToStrArg(new_points)
            mc.setMeshVertex(mesh, p=arg)

    def revertVtxToBase(self):
        """
        Revert self.focusVtx(multiple objects) to base mesh.

        """
        for mesh in self.focusVtx:
            #get all vtx current position
            points = self.getCurrOsTrans(mesh)

            for v, i in zip(self.focusVtx[mesh], self.focusIndx[mesh]):
                if self.checkEqualPoint(points[i], self.baseMeshData[i]) == True:
                    continue
                # mc.move(self.baseMeshData[i][0], self.baseMeshData[i][1], self.baseMeshData[i][2], v, ls=True)
                points[i] = (self.baseMeshData[i][0], self.baseMeshData[i][1], self.baseMeshData[i][2])
            arg = pointListToStrArg(points)
            mc.setMeshVertex(mesh, p=arg)

    def resetFocusData(self):
        """
        Reset all focus variables for multiple operations(mirror, flip).

        """
        self.focusVtx = collections.defaultdict(list) 
        self.focusIndx = collections.defaultdict(list)
        # self.relTrans = collections.defaultdict(list)
        # self.currTrans = collections.defaultdict(list)

    def resetMeshAFocusData(self):
        """
        Reset all focus variables for meshA operations(subtract, copy, add).

        """
        self.movedAVtxs = []
        self.movedAIndxs = []
        self.meshAFocusVtxs = []
        self.meshAFocusIndxs = []
        self.meshA = None

    def subtractFromMeshA(self):
        """
        Subtract self.meshA modifications from each items in self.focusVtx.

        """
        # mc.undoInfo(ock=True)
        for mesh in self.focusVtx.keys():
            #get all vtx current position
            points = self.getCurrOsTrans(mesh)

            for v, i in zip(self.focusVtx[mesh], self.focusIndx[mesh]):
                if self.checkEqualPoint(self.meshAData[i], self.baseMeshData[i]) == True:
                    continue
                relTrans = self.getRelativeTrans(self.meshAData[i], self.baseMeshData[i])
                # mc.move(currTrans[i][0]-relTrans[0], currTrans[i][1]-relTrans[1], currTrans[i][2]-relTrans[2], v, ls=True)
                points[i] = (points[i][0]-relTrans[0], points[i][1]-relTrans[1], points[i][2]-relTrans[2])
            arg = pointListToStrArg(points)
            mc.setMeshVertex(mesh, p=arg)
       #  mc.undoInfo(cck=True)

    def setStatusTxt(self, status):
        if status == True:
            mc.text(self.statusTxt, e=True, bgc=([0, 0.4, 0]), l='Loaded.')
        else:
            mc.text(self.statusTxt, e=True, bgc=([0.4, 0, 0]), l='No Base Mesh Data.')

smrObj = SymMeshReflectors()














