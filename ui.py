import pymel.core as pm
import os
from pprint import pprint
from nuTools import misc, config

class SmallPBarWindow(object):

	def __init__(self, times, txt='',title='Progress', width=200):
		if times < 1:
			times = 1
		self.title = title
		self.txt = txt
		self.times = times
		self.width = width

		self.create()
	def create(self):
		with pm.window(title=self.title, mnb=False, mxb=False, s=False) as self.pBarWin:
			pm.columnLayout(adj=True, co=['both', 5])
			pm.text(l=self.txt)
			self.pBar = pm.progressBar(w=self.width, beginProgress=True, isInterruptable=True, maxValue=self.times, imp=False)
		self.pBarWin.show()

	def increment(self):
		self.pBar.step()

	def end(self, do=True):
		if do == True:
			self.pBar.endProgress(True)
			self.pBarWin.delete()

	def getCancelled(self):
		return self.pBar.getIsCancelled()

	def getProgress(self):
		return self.pBar.getProgress()


class PromptTxtFld(object):

	def __init__(self, title='Fill in Text', message='Text:', ok='OK', cancel='Cancel', dismissString=''):
		self.title = title
		self.message = message
		self.button = [ok, cancel]
		self.dismissString = dismissString

		self.result = pm.promptDialog(title=self.title, message=self.message, button=self.button, defaultButton=self.button[0], 
				dismissString=self.dismissString)

		if self.result == self.button[0]:
			self.txt =  pm.promptDialog(query=True, text=True)
		else: 
			self.txt = None


class ConfirmDialog(object):

	def __init__(self, title='Confirm', message='Are you sure?', ok='OK', cancel='Cancel', dismissString=''):
		self.title = title
		self.message = message
		self.button = [ok, cancel]
		self.dismissString = dismissString

		self.create()

	def create(self):
		result = pm.confirmDialog( title=self.title, message=self.message,
				button=self.button, defaultButton=self.button[0], dismissString=self.dismissString )
		if result == self.button[0]:
			self.ret = True
		else:
			self.ret = False