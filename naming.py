# constants
SEPARATOR = '_'
GIMBAL = 'Gimbal'

# type suffixes
GRP = 'Grp'
JNT = 'Jnt'
CTRL = 'Ctrl'
GEO = 'Geo'
PLY = 'Ply'
NRBS = 'Nrbs'
CRV = 'Crv'
LOC = 'Loc'

# node names
ADL = 'Adl'
AIMCON = 'AimCon'

BCOL = 'Bcol'
BTA = 'Bta'

CMSA = 'Cmsa'
COND = 'Cond'
CMP = 'Cmp'
CFME = 'Cfme'

DIST = 'Dist'
DMTX = 'Dm'
DLYR = 'DLyr'

EXP = 'Exp'
EFF = 'Eff'

FOL = 'Fol'

HSYS = 'HSys'

IKHNDL = 'IkHndl'

LOFT = 'Loft'

MDL = 'Mdl'
MMTX = 'Mm'
MDV = 'Mdv'
MP = 'Mp'

NPOC = 'Npoc'
NETWORK = 'Network'
NCLS = 'Ncls'

ORICON = 'OriCon'

PMA = 'Pma'
POSI = 'Posi'
POCI = 'Poci'
PARCON = 'ParCon'
PNTCON = 'PntCon'

QTE = 'Qte'

REV = 'Rev'
RLYR = 'RLyr'


def NAME(element, side, objType):
	if isinstance(element, (tuple, list)):
		element = [str(i) for i in element]
		element = ''.join(element)

	if side:
		side = '{0}{1}'.format(SEPARATOR, side)
	return '{0}{2}{1}{3}'.format(element, SEPARATOR, side, objType)