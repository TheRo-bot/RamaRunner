
import os, json, shutil, sys

class Project:

	def __init__(self, config):
		self.dependencies = []
		self.locations = {
			"jar": "./dependencies",
			"code": "./code",
			"bin": "./bin"
		}

		#											    .json v     v '<>/ramaRunner/'
		self.location = os.path.abspath(os.path.join(config, '..', '..'))
		if( os.path.isfile(config) ):
			son = open(config, "r").read()
			try:
				self.config = json.loads(son)
			except json.decoder.JSONDecodeError as e:
				print('failed to parse JSON at "' + config + '"')


		# if ('dependencies' in self.config ):
		# 	print(self.name() + ":", self.dependencies, self.config['dependencies'])
		# 	for dependency in self.config['dependencies']:
		# 		print(dependency)
		# 		self.withDependency(RamaRunner.at(dependency['location']))


	def withDependency(self, dependency):
		if( isinstance(dependency, Project) ):
			self.dependencies.append(dependency)

		return self

	def hasDependencies(self):
		return 'dependencies' in self.config

	def hasDependency(self, name):
		dependencies = os.path.join(self.location, 'dependencies')
		if( os.path.isdir(dependencies) ):
			files = os.listdir(dependencies)
			for file in files:
				if( name in file ):
					return True

		return False

	def versionOf(self, dependency):
		for file in os.listdir(os.path.join(self.location, 'dependencies')):
			if( dependency in file ):
				return file.replace(dependency, '').replace('.jar', '')

		return None

	def compile(self):
		os.chdir(os.path.join(self.location, 'code'))
		print('compiling', self.name())
		d = '../bin'
		cp = ''

		if( "dependencies" in self.config ):
			cp = '.;'
			for dependency in self.config["dependencies"]:
				location = dependency['location'].replace('~', os.path.abspath(os.path.join(__file__, '..')))
				print(dependency['name'], 'at', location)
				runner = RamaRunner.at(location)
				if( runner != None ):
					if( not self.hasDependency(runner.name()) ):
						if( not runner.hasJar() or runner.version() != self.versionOf(runner.name()) ):
							runner.jar(compileIfNeeded = True)

						if( runner.hasJar() ):
							runner.copyJarTo(os.path.join(self.location, 'dependencies'))
						else:
							print(runner.name() + " dependency not met!")

					if( self.hasDependency(runner.name()) ):
						print(runner.name() + " dependency met!")
						cp += '../dependencies/' + runner.jarName()


		for compileTarget in self.config['toCompile']:
			compileFile = './' + compileTarget.replace('.', '/') + '.java'
			cmd = 'javac '
			if( d != '' ):
				cmd += '-d ' + d + ' '

			if( cp != '' ):
				cmd += '-cp "' + cp + '" '

			cmd += compileFile

			print(cmd)
			os.system(cmd)



	def establishDependencies(self):
		failed = []
		for dependency in self.dependencies:

			if( dependency != None ):
				if( not dependency.hasJar() ):
					dependency.jar(compileIfNeeded = True)

				if( dependency.hasJar() ):
					dependency.copyJarTo('../dependencies/')
				else:
					print("couldn't get " + dependency.name() + "! fix that shit!")
					failed.append(dependency)

		return failed

	def hasCompiled(self):
		binDir = os.path.join(self.location, 'bin')
		failedDependencies = []

		if( os.path.isfile(binDir) ):
			for cd in self.config['toCompile']:
				file = os.path.join(cd.replace('.', '/') + '.class')
				if( os.path.isfile(os.path.join(binDir, file)) ):
					failedDependencies.append(cd)

		return failedDependencies 


	### manifest stuff

	def manifestLocation(self):
		return os.path.join(self.location, 'bin', self.jarName().replace('.jar', '') + '.manifest')

	def createManifest(self):
		out = ""

		if( 'author' in self.config ):
			if( 'version' in self.config ):
				out += 'Created-By: %s (%s)' % (self.config['version'], self.config['author'])
			else:
				out += 'Created-By: %s' % self.config['author']

		if( 'mainClass' in self.config ):
			'Main-Class: %s' % self.config['mainClass']

		out += '\n'
		open(self.manifestLocation(), 'w').write(out)

	def hasManifest(self):
		return os.path.isfile(self.manifestLocation())


	### jarring stuff

	def spitDependencyContentsTo(self, dir):
		print('START -- spitDependencyContentsTo')
		depDir = os.path.join(self.location, 'dependencies')
		for file in os.listdir(depDir):
			print(file)
			os.chdir(os.path.join(self.location, 'bin'))
			filePath = os.path.relpath(os.path.join(depDir, file), os.getcwd())
			cmd = 'jar xf "' + filePath + '"'
			print(cmd)
			os.system(cmd)
		print('END -- spitDependencyContentsTo')


	def jar(self, compileIfNeeded = False):
		binDir = os.path.join(self.location, 'bin')

		compiled = False
		print('!! jarring ' + self.name())
		if( compileIfNeeded ):
			self.compile()

		print('[' + self.name() + '] hasCompiled?', len(self.hasCompiled()) == 0)
		# could be any compiled code really
		if( len(self.hasCompiled()) == 0 ):
			c = '--create '
			f = '--file ' + self.jarName() + ' '
			m = ''

			self.createManifest()
			if( self.hasManifest() ):
				m = '--manifest "' + os.path.relpath(self.manifestLocation(), binDir) + '" '
				print('including manifest!')

			# move all dependency jars into the bin folder before we jar everything
			if( self.hasDependencies() ):
				self.spitDependencyContentsTo(binDir)

			cmd = 'jar ' + c + f + m + "./"
			os.chdir(binDir)

			print(cmd)
			os.system(cmd)

		return compiled


	def version(self):
		if( 'version' in self.config ):
			return self.config['version']

		return "EXPERIMENTAL"

	def name(self):
		return os.path.basename(self.location)

	def jarName(self):
		return self.name() + "_" + self.version() + ".jar"

	def jarLocation(self):
		return os.path.join(self.location, 'bin', self.jarName())

	def hasJar(self):
		return os.path.isfile(self.jarLocation())

	def copyJarTo(self, location):
		if( self.hasJar() ):
			if( not os.path.isdir(location) ):
				os.mkdir(location)
	

			shutil.copy(self.jarLocation(), os.path.join(location, self.jarName()))


	def run(self, cma = ''):
		if( 'mainClass' in self.config ):
			os.chdir(os.path.join(self.location, 'bin'))
			cmd = 'java ' + self.config['mainClass'] + ' ' + cma
			print(cmd)
			os.system(cmd)

class RamaRunner:
	def __init__(self):
		pass

	def at(location):
		if( '~' in location ):
			location = location.replace('~', os.path.abspath(os.path.join(__file__, '..')))

		config = os.path.abspath(os.path.join(location, 'ramaRunner', 'config.json'))
		print('config?', config)
		if( os.path.isfile(config) ):
			return Project(config)

		return None
	





if( __name__ == '__main__' ):

	runner = None
	if( len(sys.argv) > 1 ):
		runner = RamaRunner.at(sys.argv[1])

	validCommands = ['compile', 'jar', 'run', 'clean']
	if( runner != None ):
		commands = []
		for x in sys.argv[1:]:
			if( x in validCommands ):
				commands.append(x)

		for command in commands:
			if( command == 'compile' ):
				runner.compile()

			elif( command == 'jar' ):
				runner.jar()

			elif( command == 'run' ):
				runner.run()

			elif( command == 'clean' ):
				runner.clean()


# rutils = RamaRunner.at('../../RUtils')

# rutils.compile()

# engineR = RamaRunner.at('~/EngineR/')
# engineR.compile()

# engineR.run()
# engineR.jar()
# engineR.withDependency(rutils)


# engineR.establishDependencies()


# if( not rutils.hasJar() ):
# 	rutils.jar(True)

# if( rutils.hasJar() ):
# 	rutils.copyJarTo('../dependencies/')

# proj.withDependency()



