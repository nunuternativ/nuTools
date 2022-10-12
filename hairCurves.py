import pymel.core as pm
import maya.OpenMaya as om

from nuTools import misc
reload(misc)


def getInvertedHairCurves(mesh=None, curves=[]):
    '''
    find hair curves with wrong direction pointing inward the mesh  
    '''
    select = False
    if not mesh or not curves:
        sels = misc.getSel(num='inf')
        if len(sels) < 2:
            return
        mesh = sels[0]
        curves = sels[1:]
        select = True
    else:
        mesh = pm.PyNode(mesh)
        curves = [pm.PyNode(c) for c in curves]

    meshShp = mesh.getShape(ni=True)
    inverted_curves = []
    for crv in curves:
        crvShp = crv.getShape(ni=True)
        first_pos = pm.dt.Point(pm.xform(crvShp.cv[0], q=True, ws=True, t=True))
        last_pos = pm.dt.Point(pm.xform(crvShp.cv[crvShp.numCVs() - 1], q=True, ws=True, t=True))

        closest_to_first, first_fid = meshShp.getClosestPoint(first_pos, space='world')
        closest_to_last, last_fid = meshShp.getClosestPoint(last_pos, space='world')

        first_vec = first_pos - closest_to_first
        last_vec = last_pos - closest_to_last

        dist_to_first = first_vec.length()
        dist_to_last = last_vec.length()

        if dist_to_first > dist_to_last:
            inverted_curves.append(crv)
    if select:
        pm.select(inverted_curves, r=True)
    return inverted_curves

def fix_curves_on_border(objs=[], fix=True, tol=0.00001, moveDist=0.001):
    selection_err_msg = 'Please select curves and a mesh.'
    if not objs:
        objs = misc.getSel(num='inf')
        if not objs or len(objs) < 2:
            om.MGlobal.displayError(selection_err_msg)
            return

    crvs = [c for c in objs[:-1] if c.getShape(type='nurbsCurve')]
    mesh = objs[-1].getShape(type='mesh')

    if not mesh or not crvs:
        om.MGlobal.displayError(selection_err_msg)
        return

    infected = []
    for crv in crvs:
    	crvCv = crv.cv[0]
        point = crvCv.getPosition('world')
        # get closest vertex
        closestVert, closestFace = misc.getClosestComponentFromPos(mesh, point)
        connectedEdgeIds = list(closestVert.connectedEdges())
        borderEdges = misc.getUvBorderEdges(mesh=mesh, edges=connectedEdgeIds, select=False)
        for bei in borderEdges:
            edge = mesh.e[bei]
            pt1 = edge.getPoint(0, 'world')
            pt2 = edge.getPoint(1, 'world')
            vec = pt1 - pt2
            vec.normalize()
            pvec = pt1 - point
            pvec.normalize()

            if vec.isEquivalent(pvec, tol=tol):
                infected.append(crv)
                if fix:
                    faceFn = closestFace.__apimfn__()
                    cfc = pm.dt.Point(faceFn.center(om.MSpace.kWorld))
                    cVec = cfc - point
                    cVec *= moveDist
                    newPos = point + cVec
                    pm.xform(crvCv, ws=True, t=newPos)
                break
    if infected:
        pm.select(infected, r=True)

    return infected
