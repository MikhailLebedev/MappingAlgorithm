#class for VPA logging
class VPALogger:
	def __init__(self, filename_1, filename_2):
		self.logfile = open(filename_1+".log","w")
		self.stat = open(filename_2+".log","w")

	def writelog(self, s):
		self.logfile.write(s)

	def writestat(self, s):
		self.stat.write(s)	
