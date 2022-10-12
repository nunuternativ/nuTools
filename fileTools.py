import shutil, os, re
import json
# import maya.OpenMaya as om
from tempfile import mkstemp
import subprocess


FFMPEG_PATH = r'C:\sysTool\python\ffmpeg\bin\ffmpeg.exe'
DJV_CONVERT_PATH = r'O:\studioTools\lib\djv\bin\djv_convert.exe'

def replace(filePath, search, replace):
	#Create temp file
	wFileH, wFilePath = mkstemp()
	wFile = open(wFilePath,'w')
	rFile = open(filePath)
	for line in rFile:
		wFile.write(line.replace(search, replace))

	#close temp file
	wFile.close()
	os.close(wFileH)
	rFile.close()
	# Remove original file
	os.remove(filePath)
	# Move new file
	shutil.move(wFilePath, filePath)

def getFileNameFromPath(path):
	baseName = os.path.basename(path)
	return os.path.splitext(baseName)[0]

def getRefInfoFromMaFile(filePath, printResult=False):
	refCmd = 'file -r '
	res = []
	with open(filePath, 'r') as readFile:
		foundRef = False
		for line in readFile:
			if line.startswith(refCmd):
				foundRef = True
				splits = line.split()

				try:
					node = splits[splits.index('-rfn') + 1].split('"')[1::2][0]
					ns = splits[splits.index('-ns') + 1].split('"')[1::2][0]
					path = splits[-1].split('"')[1::2][0]
					res.append([path, node, ns])
				except:
					continue
				
			elif foundRef == True:
				break

	if res and printResult:
		for oldElem in sorted(res):
			print '%s\n%s\n%s\n' %(oldElem[0], oldElem[1], oldElem[2])

	return res

def replaceRefFromMaFile(filePath, pairPathDict):
	'''
		Replace references from a .ma file. This includes refNode name and namespaces
		input:
			pairPathDict = {oldPath: newPath, ...}
	'''

	# get existing ref first: 
	# oldRefs = [[oldPath, oldNode, oldNs], ...]
	oldRefs = getRefInfoFromMaFile(filePath, printResult=False)
	if not oldRefs:
		return

	# turn oldRefs into {newPath: [oldPath, oldNode, oldNs]}
	rRefDict = {}
	for oldElems in oldRefs:
		if oldElems[0] in pairPathDict.keys():
			newPath = pairPathDict[oldElems[0]]
			rRefDict[newPath] = oldElems

	wFileH, wFilePath = mkstemp()
	wFile = open(wFilePath,'w')
	rFile = open(filePath)

	i = 0
	retDict = {}
	for line in rFile:
		for new, old in rRefDict.iteritems():
			filename = getFileNameFromPath(new)
			refNo = old[1].split('RN')[-1]
			if old[0] in line:
				line = line.replace(old[0], new)

			if old[1] in line:
				newRefNodeName = '%sRN%s' %(filename, refNo)
				line = line.replace(old[1], newRefNodeName)

			if old[2] in line:
				newNs = '%s%s' %(filename, refNo)
				line = line.replace(old[2], newNs)


		wFile.write(line)

	# close files
	wFile.close()
	os.close(wFileH)
	rFile.close()

	# remove old file
	os.remove(filePath)

	# move brand new written file to the filePath
	shutil.move(wFilePath, filePath)

def getFileSeqInDir(path, exts=[]):
	isfile = os.path.isfile
	path_join = os.path.join
	os_path_splitext = os.path.splitext

	files = sorted([f for f in os.listdir(path) if isfile(path_join(path, f)) == True])
	nums = []
	ext = ''
	if files:
		if exts:
			files = (f for f in files if os_path_splitext(f)[-1] in exts)

		nums, files, ext = getFileSeq(files=files)

	return nums, files, ext

def getFileSeq(files):
	rfiles, nums, exts = [], [], []
	name_part, ext = '', ''

	os_path_splitext = os.path.splitext
	re_findall = re.findall
	nums_append = nums.append
	rfiles_append = rfiles.append
	exts_append = exts.append

	for f in files:
		name, ext = os_path_splitext(f)
		match = re_findall('\d+$', name)

		if name_part and name_part not in name:
			ext = exts[-1]
			break

		if match:
			num = match[-1] 
			name_part = name.rsplit(num, 1)[0]
			if not nums or int(num) - int(nums[-1]) == 1:
				nums_append(num)
				rfiles_append(f)
				exts_append(ext)

	return nums, rfiles, ext

def batchRenameFile(path, search, replace, filterExt='.png'):
	for i in [f for f in os.listdir(path) if os.path.splitext(f)[-1]==filterExt]:
		name, ext = os.path.splitext(i)
		newname = name.replace(search, replace)
		# print newname
		old_fp = r'%s\%s%s' %(path, name, ext)
		new_fp = r'%s\%s%s' %(path, newname, ext)
		# print new_fp
		os.rename(old_fp, new_fp)


def convertImageFiles(sourceDir, destinationDir, sourceExt='.exr', destinationExt='.png'):
	'''
	from nuTools import fileTools
	reload(fileTools)

	sourceDir = r'C:\Users\Nunu\Desktop\Nuternativ\_playground\texture-col-high-exr_body_1005'
	destinationDir = r'C:\Users\Nunu\Desktop\Nuternativ\_playground\texture_test'
	fileTools.convertExrInFolderToPng(sourceDir, destinationDir)
	'''
	if not os.path.exists(sourceDir) or not os.path.exists(destinationDir):
		print 'Source dir or destination dir do not exist!'
		return 

	# find source files
	src_files = [f for f in os.listdir(sourceDir) if os.path.splitext(f)[-1] == sourceExt]
	if not src_files:
		print 'Cannot find %s image in %s' %(sourceExt, sourceDir)
		return

	# ffmpeg str
	for f in src_files:
		src_fp = '%s\\%s' %(sourceDir, f)
		fileName, oldExt = os.path.splitext(f)
		desFile = '%s%s' %(fileName, destinationExt)
		des_fp = '%s\\%s' %(destinationDir, desFile)
		cmd = '%s %s %s ' %(DJV_CONVERT_PATH, src_fp, des_fp)
		retcode = 0
		try:
			ffmpeg_process = subprocess.Popen(cmd, shell=True)
			while ffmpeg_process.poll() == None:
				continue
				
		except Exception, e:
			print e


def removeJsonKey(filePath, keys_to_remove, endswith=True, overwrite=False):
	filePath = os.path.normpath(filePath)
	if not os.path.exists(filePath):
		return

	data = None
	with open(filePath, 'r') as f:
		data = json.load(f)

	if not data or not 'objects' in data:
		return

	objData = data['objects']

	removes = []
	if endswith:
		for k, v in objData.iteritems():
			for kr in keys_to_remove:
				if k.endswith(kr):
					removes.append(k)
					break
	else:
		removes = keys_to_remove

	result = False
	if removes:
		for rem in removes:
			del objData[rem]

		data['objects'] = objData
		# print data
		if overwrite:
			with open(filePath, 'w') as f:
				json.dump(data, f)
		result = True

	return result, data