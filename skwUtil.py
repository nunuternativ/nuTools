import os
import json, cPickle

import pymel.core as pm
import maya.cmds as mc
import maya.mel as mel

from nuTools import misc

def loadData(fn):
    dirname = os.path.dirname(fn)

    print 'Loading: %s' %fn
    data = None
    with open(fn, 'r') as f:
        data = json.load(f)
    return data

def readSkinWeights(geos=[], fn='skinWeights.json', 
                    geoSearchFor='', geoReplaceWith='', geoPrefix='', geoSuffix='', 
                    infSearchFor='', infReplaceWith='', infPrefix='', infSuffix=''):
    if not geos:
        sels = misc.getSel(num='inf')
        if not sels: return
        geos = [g.name() for g in sels if misc.checkIfPly(g)]
    if not geos:
        return

    dirname = os.path.dirname(fn)
    if not dirname:
        dirname = os.path.dirname(pm.sceneName())
        fn = '%s/%s' %(dirname, fn)
    if not os.path.exists(dirname):
        print 'Directory does not exits: %s' %dirname
        return
    if not os.path.exists(fn):
        print 'Path does not exists: %s' %fn
        return

    data = loadData(fn)
    for geo in geos:
        geo = geo.replace(geoSearchFor, geoReplaceWith)
        geo = '%s%s%s' %(geoPrefix, geo, geoSuffix)
        if geo in data:
            wDct = data[geo]
            infs = wDct['influences']

            currInfs = []
            for inf in infs:
                currInf = inf
                if infSearchFor:
                    currInf = currInf.replace(infSearchFor, infReplaceWith)
                currInf = '%s%s%s' %(infPrefix, currInf, infSuffix)
                currInfs.append(currInf)
            
            for currInf in currInfs:
                if not mc.objExists(currInf):
                    print 'Scene has no %s ' %currInf

            oSkn = mel.eval('findRelatedSkinCluster "%s"' %geo)
            if oSkn:
                mc.skinCluster(oSkn, e=True, ub=True)
            tmpSkn = mc.skinCluster(currInfs, geo, tsb=True)[0]
            
            skn = mc.rename(tmpSkn, wDct['name'])
            mc.setAttr('%s.skinningMethod' %skn, wDct['skinningMethod'])
            sknSet = mc.listConnections('%s.message' %skn, d=True, s=False)[0]
            mc.rename(sknSet, wDct['set'])
            
            for currInf in currInfs:
                mc.setAttr('%s.liw'% currInf, False)
            
            mc.setAttr('%s.normalizeWeights' %skn, False)
            mc.skinPercent(skn, geo, nrm=False, prw=100)
            mc.setAttr('%s.normalizeWeights' %skn, True)

            weights = cPickle.loads(str(wDct['weights']))
            for ix in xrange(mc.polyEvaluate(geo, v=True)):      
                for iy in xrange(len(currInfs)):
                    wVal = weights[ix][iy]
                    if wVal:
                        wlAttr = '%s.weightList[%s].weights[%s]' %(skn, ix, iy)
                        mc.setAttr(wlAttr, wVal)
            
            print '%s: readSkinWeights done.' %geo


def getSkinWeightData(geos) :
    ret = {}
    for geo in geos:
        if not pm.objExists(geo):
            print 'Object does not exist: %s' %geo

        skn = mel.eval('findRelatedSkinCluster "%s"' %geo)
        if skn :
            sknMeth = mc.getAttr('%s.skinningMethod' %skn)
            useCompo = mc.getAttr('%s.useComponents' %skn)
            infs = mc.skinCluster(skn, q=True, inf=True)
            sknSet = mc.listConnections('%s.message' %skn, d=True, s=False)[0]

            wDct = {}
            wDct['influences'] = infs
            wDct['name'] = skn
            wDct['set'] = sknSet
            wDct['skinningMethod'] = sknMeth
            wDct['useComponents'] = useCompo
            
            weights = []
            for ix in xrange(mc.polyEvaluate(geo , v=True)):
                currVtx = '%s.vtx[%d]' %(geo, ix)
                skinVal = mc.skinPercent(skn, currVtx, q=True, v=True)
                weights.append(skinVal)
                # wDct[ix] = cPickle.dumps(skinVal)
            wDct['weights'] = cPickle.dumps(weights)
            ret[geo] = wDct
        else :
            print '%s has no related skinCluster node.' %geo

    return ret

def writeSkinWeights(geos=[], fn='skinWeights.json'):
    if not geos:
        sels = misc.getSel(num='inf')
        if not sels: return
        geos = [g.name() for g in sels if misc.checkIfPly(g)]
    if not geos:
        return
    dirname = os.path.dirname(fn)
    if not dirname:
        dirname = os.path.dirname(pm.sceneName())
        fn = '%s/%s' %(dirname, fn)
    if not os.path.exists(dirname):
        print 'Directory does not exits: %s' %dirname
        return
    
    data = getSkinWeightData(geos)
    with open(fn, 'w') as f:
        json.dump(data, f, sort_keys=True, indent=4, separators=(',', ':'))

    # for g in geos:
    print 'writeSkinWeights done.'