import maya.utils
import threading

# Thread-object
class MayaThread(threading.Thread):
	def __init__(self, times, *args):
		self.times = times
		self.args = args

		threading.Thread.__init__(self)


	def run(self):
		for i in range(0, self.times):
			result = maya.utils.executeInMainThreadWithResult(*self.args)


# Run as thread
def start(*args, **kwArgs):
	numThread = 4
	times = 1
	for key in kwArgs.keys():
		if key == 'numThread':
			numThread = kwArgs[key]
		if key == 'times':
			times = kwArgs[key]

	for thread in range(1, numThread):
		threadObj = MayaThread(times, *args)

	threadObj.start()
		

