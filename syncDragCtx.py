import pymel.core as pm
import maya.OpenMaya as om


class SyncDragCtx(object):

    def __init__(self, info, ctxName='syncDragCtx', cursor='track', tol=0.1, hotkey=True):
        self.tol = tol
        self.ctxName = ctxName
        self.cursor = cursor
        self.info = info
        self.prevTool = 'selectSuperContext'

        self.objs = {}
        self.dragCtx = None

        self._STATE = False

    def createCtx(self):
        try:
            pm.deleteUI(self.ctxName)
        except: pass

        self.dragCtx = pm.draggerContext(   n=self.ctxName,
                                            um='step', 
                                            sp='screen', 
                                            pr='viewPlane', 
                                            cur=self.cursor,
                                            inz=pm.Callback(self.printActivated),
                                            fnz=pm.Callback(self.printDeactivated),
                                            pc=pm.Callback(self.click),
                                            dc=pm.Callback(self.drag))

        self.activate()

    def activate(self):
        self.prevTool = pm.currentCtx()
        pm.setToolTo(self.dragCtx)
        self._STATE = True

    def deactivate(self):
        pm.setToolTo(self.prevTool)
        self._STATE = False

    def printDeactivated(self):
        om.MGlobal.displayInfo('OFF : Sync Dragger mode.')

    def printActivated(self):
        om.MGlobal.displayInfo('ON : Sync Dragger mode!')


    def click(self):
        selected = pm.ls(sl=True, type='transform')
        if not selected:
            om.MGlobal.displayWarning('No selection!')
            return

        self.objs = {'x':[], 'y':[]}

        ancPos = pm.draggerContext(self.dragCtx, q=True, anchorPoint=True)
        button = pm.draggerContext(self.dragCtx, q=True, button=True)
        mod = pm.draggerContext(self.dragCtx, q=True, modifier=True)

        buttonDict = self.info[button]

        if mod in buttonDict.keys():
            for obj in selected:  
                for a in ['x', 'y']:
                    for attr in buttonDict[mod][a]:
                        try: 
                            attribute = obj.attr(attr[0])
                            value = attribute.get()
                            self.objs[a].append([attribute, value, attr[1]])
                        except:
                            pass



    def drag(self):
        currPos = pm.draggerContext(self.dragCtx, q=True, dragPoint=True)
        ancPos = pm.draggerContext(self.dragCtx, q=True, anchorPoint=True)

        x = (currPos[0] - ancPos[0]) * self.tol
        y = (currPos[1] - ancPos[1]) * self.tol
        currValue = {'x':x, 'y':y}
            
        for a, values in self.objs.iteritems():
            for v in values:
                attribute = v[0]
                origValue = v[1]
                mult = v[2]
                value = origValue + (currValue[a] * mult)
                try:
                    pm.setAttr(attribute, value)
                except: pass

        pm.refresh(cv=True)



    


    