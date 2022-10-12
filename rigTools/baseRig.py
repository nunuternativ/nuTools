from pymel.core import *
import maya.OpenMaya as om

from nuTools.naming import *
from nuTools import misc
reload(misc)
from nuTools.controller import CurveController, JointController
nodetypes.JointController = JointController
nodetypes.CurveController = CurveController

DEFAULT_ELEMENT = 'limb'
DEFAULT_SIDE = ''
DEFAULT_SIZE = 1.00
DEFAULT_ROTATEORDER = 'zxy'

class BaseRig(object):
    """
    The base class for all the rig classes.

    """
    def __init__(self, 
                parent=None,
                animGrp=None, 
                skinGrp=None, 
                utilGrp=None, 
                stillGrp=None, 
                elem=DEFAULT_ELEMENT, 
                side=DEFAULT_SIDE, 
                size=DEFAULT_SIZE,
                rotateOrder=DEFAULT_ROTATEORDER,
                **kwargs):
        self.elem = elem
        self.side = side
        self.size = size
        self.rotateOrder = rotateOrder
        self.network = None

        if 'rigGrp' in kwargs:
            rigGrp = kwargs['rigGrp']

            self.animGrp = rigGrp.animGrp
            self.skinGrp = rigGrp.skinGrp
            self.utilGrp = rigGrp.utilGrp
            self.stillGrp = rigGrp.stillGrp
        else:
            if isinstance(animGrp, (str, unicode)) == True:
                try:
                    animGrp = PyNode(animGrp)
                except Exception, e:
                    print e
                    om.MGlobal.displayError('Cannot cast %s to PyNode!' %(animGrp))
            self.animGrp = animGrp

            if isinstance(skinGrp, (str, unicode)) == True:
                try:
                    skinGrp = PyNode(skinGrp)
                except Exception, e:
                    print e
                    om.MGlobal.displayError('Cannot cast %s to PyNode!' %(skinGrp))
            self.skinGrp = skinGrp

            if isinstance(utilGrp, (str, unicode)) == True:
                try:
                    utilGrp = PyNode(utilGrp)
                except Exception, e:
                    print e
                    om.MGlobal.displayError('Cannot cast %s to PyNode!' %(utilGrp))
            self.utilGrp = utilGrp

            if isinstance(stillGrp, (str, unicode)) == True:
                try:
                    stillGrp = PyNode(stillGrp)
                except Exception, e:
                    print e
                    om.MGlobal.displayError('Cannot cast %s to PyNode!' %(stillGrp))
            self.stillGrp = stillGrp

        if isinstance(parent, (str, unicode)) == True:
            try:
                parent = PyNode(parent)
            except Exception, e:
                print e
                om.MGlobal.displayError('Cannot cast %s to PyNode!' %(parent))
        self.parent = parent

    @classmethod
    def init_from_data(cls, network):
        if isinstance(network, (str, unicode)):
            try:
                network = PyNode(network)
            except MayaNodeError:
                om.MGlobal.displayError('Failed to find network: %s' %network)
                return
        dataStr = ''
        if network.hasAttr('__init_data__'):
            dataStr = network.__init_data__.get()
        else:
            om.MGlobal.displayError('Found no data in: %s' %network)
            return
        ns = network.namespace()
        if ns:
            new_data = []
            for d in dataStr.split(', '):
                if '(u\'' in d:
                    d = d.replace('(u\'', '(u\'%s' %(ns))
                new_data.append(d)
            dataStr = ', '.join(new_data)

        exec('init_data = %s' %dataStr)
        # print init_data
        new_obj = cls()
        for key, value in init_data.iteritems():
            setattr(new_obj, key, value)

        return new_obj

    def createNetwork(self):
        self.network = createNode('network', name=NAME(self.elem, self.side, NETWORK))
        modStr = self.__class__.__module__
        misc.addStrAttr(obj=self.network, attr='__module__', 
            txt=modStr, lock=True)

        clsName = self.__class__.__name__
        misc.addStrAttr(obj=self.network, attr='__class__', 
            txt=clsName, lock=True)

    def register_str(self, name, text):
        misc.addStrAttr(obj=self.network, attr=name, 
            txt=text, lock=True)

    # def register_nodes(self, name, nodes):
    #     if not self.network.hasAttr(name):
    #         misc.addMsgAttr(self.network, name)
    #     for node in nodes:
    #         connectAttr(self.network.name, node.message, f=True)

    def register(self):
        variables = vars(self)
        if not self.network and not objExists(NAME(self.elem, self.side, NETWORK)):
            self.createNetwork()

        var_data = {}
        for k, v in variables.iteritems():
            if not k.startswith('_'):
                var_data[k] = v
        data = str(var_data)
        self.register_str(name='__init_data__', text=data)

    def lockInf(self, jnts, value):
        for j in jnts:
            j.lockInfluenceWeights.set(value)

    def jntsArgs(self, jnts):
        if not jnts:
            return

        single = False
        if not isinstance(jnts, (list, tuple, set)):
            jnts = [jnts]
            single = True

        joints = []
        for j in jnts:
            if not isinstance(j, PyNode):
                try:
                    j = PyNode(j)
                except Exception, e:
                    print e
                    pass
            joints.append(j)

        if joints:
            if single == True:
                return joints[0]
            else:
                return joints

