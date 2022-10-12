def mapLocalEnv(localRoot, version=None):
	import sys
	import maya.mel as mel

	try:
		# append python local path
		sys.path.append('%s/python' %localRoot)

		# get mel local path
		mayaScriptPath = mel.eval('getenv "MAYA_SCRIPT_PATH";')
		mayaPluginPath = mel.eval('getenv "MAYA_PLUG_IN_PATH";')
		mayaXbmLanguagePath = mel.eval('getenv "XBMLANGPATH";')

		# append path
		mayaScriptPath += ';%s/mel' %localRoot
		mayaPluginPath += ';%s/plugin/any' %localRoot
		if version:
			mayaPluginPath += ';%s/plugin/%s' %(localRoot, version)
		mayaXbmLanguagePath += ';%s/icons' %localRoot

		# add paths
		mel.eval('putenv "MAYA_SCRIPT_PATH" "%s";' %mayaScriptPath)
		mel.eval('putenv "MAYA_PLUG_IN_PATH" "%s";' %mayaPluginPath)
		mel.eval('putenv "XBMLANGPATH" "%s";' %mayaXbmLanguagePath)	

		# refresh 
		mel.eval('rehash;')			

	except:
		mel.eval('Error: cannot add local env paths...')