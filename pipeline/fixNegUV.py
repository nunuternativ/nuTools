import os, shutil
import pymel.core as pm
import maya.mel as mel
# INPUT : P:/Lego_FRD/asset/3D/type/subtype/assetname
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
for each in logger.handlers[::-1] :
	if type(each).__name__ == 'StreamHandler':
		logger.removeHandler(each)

	if type(each).__name__== 'FileHandler': 
		logger.removeHandler(each)
		each.flush()
		each.close()

from nuTools.util import meshDataUtil as mdu
reload(mdu)
from tool.mergeUv import core as muvc
reload(muvc)
from tool.shade.shadeTool import shadeRS_app as shadeRS
reload(shadeRS)
from tool.utils import entityInfo, fileUtils


class FixNegUVTool(object):
	def __init__(self):
		self.hasShd = False

	def prepare(self, assetPath):
		# --- logger
		ch = logging.StreamHandler()
		ch.setLevel(logging.ERROR)
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		ch.setFormatter(formatter)
		logger.addHandler(ch)

		# --------------------------------------------------------------------
		GEO_GRP = 'Geo_Grp'
		UV_DATA = 'uv_coords.pkl'
		TOPOLOGY_DATA = 'uv_topology.pkl'
		NORMALS_DATA = 'uv_normals.pkl'
		PROJ_PATH = 'P:/Lego_FRD'
		# --------------------------------------------------------------------
		# get animMd, shadeRsMd on the sever
		splits = assetPath.split('/')
		typ = splits[4]
		styp = splits[5]
		assetName = splits[6]
		animMdPath = '%s/ref/%s_AnimMd.ma' %(assetPath, assetName)
		shadeRsMdPath = '%s/ref/%s_ShadeRsMd.ma' %(assetPath, assetName)

		if not os.path.exists(animMdPath):
			logger.error('AnimMd does not exists: %s' %(animMdPath))
			return 
		logger.info('AnimMd path: %s' %(animMdPath))
		
		if not os.path.exists(shadeRsMdPath):
			logger.error('ShadeRsMd does not exists: %s' %(shadeRsMdPath))
			self.hasShd = False
		self.hasShd = True
		logger.info('ShadeRsMd path: %s' %(shadeRsMdPath))

		logPath = '%s/asset/mapping/UV_LOGS/%s_RenderRsMd.ma' %(PROJ_PATH, assetName)
		logger.info('Log path: %s' %logPath)
		if not os.path.exists(logPath):
			logger.error('Cannot find affected polygon log file: %s' %(logPath))
			return 
		# --------------------------------------------------------------------
		# copy animMd and shadeRsMd to LOCAL
		myDocPath = os.path.expanduser('~')
		locProjDir = '%s/Lego_FRD_fixNegUV' %myDocPath
		if not os.path.exists(locProjDir):
			logger.info('Creating folder: %s' %(locProjDir))
			os.mkdir(locProjDir)
			logger.info('Folder created: %s' %(locProjDir))
		
		locAssetPath = '%s/%s_%s_%s' %(locProjDir, typ, styp, assetName)
		logger.info('Local asset folder: %s' %locAssetPath)
		if not os.path.exists(locAssetPath):
			os.mkdir(locAssetPath)
			logger.info('Folder created: %s' %(locAssetPath))

		locTexPath = '%s/textures/md' %locAssetPath
		logger.info('Local textures folder: %s' %locTexPath)
		if not os.path.exists(locTexPath):
			os.makedirs(locTexPath)
			logger.info('Folder created: %s' %(locTexPath))

		locMeshDataPath = '%s/meshData' %locAssetPath
		logger.info('Local textures folder: %s' %locMeshDataPath)
		if not os.path.exists(locMeshDataPath):
			os.mkdir(locMeshDataPath)
			logger.info('Folder created: %s' %(locMeshDataPath))

		localAnimMdPath = '%s/%s_AnimMd.ma' %(locAssetPath, assetName)
		shutil.copy(animMdPath, localAnimMdPath)
		logger.info('Copied from: %s to %s' %(animMdPath, localAnimMdPath))

		if self.hasShd:
			localShadeRsMdPath = '%s/%s_ShadeRsMd.ma' %(locAssetPath, assetName)
			shutil.copy(shadeRsMdPath, localShadeRsMdPath)
			logger.info('Copied from: %s to %s' %(shadeRsMdPath, localShadeRsMdPath))
		
		# --------------------------------------------------------------------
		# open LOCAL animMD
		logger.info('Opening: %s' %localAnimMdPath)
		pm.openFile(localAnimMdPath, f=True)
		logger.info('Opened: %s' %localAnimMdPath)

		# --------------------------------------------------------------------
		# export Geo_Grp as LOCAL WORK FILE
		if not pm.objExists(GEO_GRP) or len(pm.ls(GEO_GRP)) != 1:
			logger.error('Cannot find Geo_Grp')
			return 

		pm.select(GEO_GRP)
		logger.info('Selected: %s' %GEO_GRP)
		localWorkPath = '%s/%s_fixNegUV_v001.ma' %(locAssetPath, assetName)
		logger.info('local work path: %s' %localWorkPath)
		# pm.exportSelected(localWorkPath, f=True, ch=False, shader=False, preserveReferences=False, type='mayaAscii')
		mel.eval('file -force -options "v=0;" -typ "mayaAscii" -es "%s";' %localWorkPath)
		logger.info('Exported %s to %s' %(GEO_GRP, localWorkPath))

		# --------------------------------------------------------------------
		# open LOCAL WORK FILE
		logger.info('Opening local work file: %s' %localWorkPath)
		pm.openFile(localWorkPath, f=True)
		logger.info('Opened local work file: %s' %localWorkPath)

		logger.info('Getting geos in  local UV work file...')
		allGeos = muvc.getGeoInGrp(GEO_GRP)
		logger.info('\n'.join([n.longName() for n in allGeos]))
		if not allGeos:
			logger.error('No geometry found in local work')
			return

		# --------------------------------------------------------------------
		# import & assign shaders from temp shadeRsMd (script needed)
		# if do not have shade
		info = entityInfo.info(assetPath)
		uvDir, latestFile = info.latestFile('uv', 'uv_md')

		hook = shadeRS.maya_hook
		hook.deleteUI(shadeRS.UI_NAME)
		rsToolApp = shadeRS.lookDev_RS(hook.getMayaWindow(), 
						asset='%s/%s' %(uvDir, latestFile),
						uiMode=False)
		rsToolApp.doConnectShade()

		# --------------------------------------------------------------------
		# create affected polygon set
		aMeshes = []
		logger.info('Reading affected polygon log file...')
		with open(logPath, 'r') as logfile:
			aMeshes = logfile.readlines()
		aMeshes = [m.replace('\n', '') for m in aMeshes]
		aMeshes = ['|'.join(m.split('|')[:-1]) for m in aMeshes]
		logger.info('\n'.join(aMeshes))

		afNodes = []
		for meshName in aMeshes:
			if pm.objExists(meshName):
				tr = pm.PyNode(meshName)
				afNodes.append(tr)
			else:
				logger.error('Cannot find: %s' %meshName)
		pm.sets(afNodes, n='negativeUV_set')

		### FIX THE UVs, tweak 2dPlacement nodes...
		### If need to tweak texture files:
			### copy those files to temp project directory
			### change path in the file node to the temp texture file

	def submit(self):
		pass
		# ------------
		# -- BUTTON 2
		# save overwrite LOCAL WORK FILE

		# get temp proj directory path, prepare directory
		
		# export UV data to local directory

		# --- if has shadeRsMd
			# edit file node texture path to relative path on temp proj on server
			# export shadeRsMd, shadeYml to LOCAL
			# with empty scene, reference LOCAL AnimMD, import & assign temp shadeRsMd, save in LOCAL as ShadeWork


		# open LOCAL AnimMd, apply LOCAL UV data, save overwrite LOCAL animMd
		
		
		# --- if has shadeRsMd
			# copy LOCAL shadeRsMd, shadeYml to temp proj directory on server
			# copy LOCAL ShadeWork to temp proj directory on server

		# copy LOCAL UV data to temp proj directory on server
		# copy LOCAL AnimMd to temp proj directory on server
		# copy LOCAL textures folder to temp proj directory on server