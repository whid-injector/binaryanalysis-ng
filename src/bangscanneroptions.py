import os
import sys
import multiprocessing
import argparse
import stat
import configparser

class objectdict(dict):
    def __setattr__(self,name,value):
        self[name] = value
    def __getattr__(self,name):
        return self[name]

class BangScannerOptions:
    def __init__(self):
        self._setDefaultOptions()
        self._parseArguments()
        self._readConfigurationFile()
        self._setOptionsFromConfigurationFile()
        self._setOptionsFromArguments()
        self._validateOptions()

    def _setDefaultOptions(self):
        self.defaults = {
                'cfg' : os.path.join(os.path.dirname(sys.argv[0]),'bang.config'),
                'baseunpackdirectory' : '',
                'temporarydirectory' : None,
                'removescandirectory' : False,
                'createbytecounter' : False,
                'tlshmaximum' : sys.maxsize,
                'postgresql_host' : None,
                'postgresql_port' : None,
                'postgresql_user' : None,
                'postgresql_password' : None,
                'postgresql_db' : None,
                'usedatabase' : True,
                'dbconnectionerrorfatal' : False,
                'writereport' : True,
                'uselogging' : True,
                'bangthreads' : multiprocessing.cpu_count(),
                'checkdirectory' : None,
                'checkfile' : None,
                'usedatabase' : False,
        }
        self.options = objectdict(dict(self.defaults))

    def getOptions(self):
        return self.options

    def _error(self,msg):
        print(msg, file=sys.stderr)
        sys.exit(1)
    def _parseArguments(self):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument("-f", "--file", action="store", dest="checkfile",
                            help="path to file to check", metavar="FILE")
        self.parser.add_argument("-d", "--directory", action="store", dest="checkdirectory",
                            help="path to directory with files to check", metavar="DIR")
        self.parser.add_argument("-c", "--config", action="store", dest="cfg",
                            help="path to configuration file", metavar="FILE",default=self.defaults['cfg'])
        self.args = self.parser.parse_args()
        self._checkConfigurationFile()
    def _checkConfigurationFile(self):
        if self.args.cfg is None:
            self.parser.error("No configuration file provided, exiting")
        # the configuration file should exist ...
        if not os.path.exists(self.args.cfg):
            self.parser.error("File %s does not exist, exiting." % self.args.cfg)
        # ... and should be a real file
        if not stat.S_ISREG(os.stat(self.args.cfg).st_mode):
            self.parser.error("%s is not a regular file, exiting." % self.args.cfg)

    def _readConfigurationFile(self):
        # read the configuration file. This is in Windows INI format.
        self.config = configparser.ConfigParser()
        try:
            configfile = open(self.args.cfg, 'r')
            self.config.read_file(configfile)
        except:
            self._error("Cannot open configuration file, exiting")

    def _setStringOptionFromConfig(self,option_name, section=None,option=None):
        if option == None: option = option_name
        try:
            v = self.config.get(section,option)
        except configparser.NoOptionError:
            return
        except KeyError:
            return
        self.options[option_name] = v
        # self.options.__setattr__(option_name,v)

    def _setIntegerOptionFromConfig(self,option_name, section=None,option=None):
        if option == None: option = option_name
        try:
            v = int(self.config.get(section,option))
        except configparser.NoOptionError:
            return
        except KeyError:
            return
        except ValueError:
            return
        self.options[option_name] = v
        # self.options.__setattr__(option_name,v)

    def _setBooleanOptionFromConfig(self,option_name, section=None,option=None):
        if option == None: option = option_name
        try:
            v = self.config.get(section,option) == 'yes'
        except configparser.NoOptionError:
            return
        except KeyError:
            return
        except ValueError:
            return
        self.options[option_name] = v
        # self.options.__setattr__(option_name,v)

    def _setOptionsFromConfigurationFile(self):
        self._setStringOptionFromConfig('baseunpackdirectory', section='configuration')
        self._setStringOptionFromConfig('temporarydirectory', section='configuration')
        self._setIntegerOptionFromConfig('bangthreads', section='configuration',option='threads')
        self._setBooleanOptionFromConfig('removescandirectory', section='configuration')
        self._setBooleanOptionFromConfig('createbytecounter', section='configuration',option='bytecounter')
        self._setIntegerOptionFromConfig('tlshmaximum', section='configuration')
        self._setBooleanOptionFromConfig('writereport', section='configuration',option='report')
        self._setBooleanOptionFromConfig('uselogging', section='configuration',option='logging')
        self._setBooleanOptionFromConfig('dbconnectionerrorfatal', section='database')
        self._setStringOptionFromConfig('postgresql_user', section='database')
        self._setStringOptionFromConfig('postgresql_password', section='database')
        self._setStringOptionFromConfig('postgresql_db', section='database')
        self._setStringOptionFromConfig('postgresql_host', section='database')
        self._setIntegerOptionFromConfig('postgresql_port', section='database')

    def _setOptionsFromArguments(self):
        self.options.checkdirectory = self.args.checkdirectory
        self.options.checkfile = self.args.checkfile

    def _validateOptions(self):
        # bangthreads >= 1
        if self.options.bangthreads < 1:
            self.options.bangthreads = self.defaults['bangthreads']
        # option usedatabase true if db parameters set
        self.options.usedatabase = self.options.postgresql_db and \
                self.options.postgresql_user and \
                self.options.postgresql_password
        # if dbconnectionerrorfatal, db parameters must be set
        if self.options.dbconnectionerrorfatal and self.options.usedatabase == False:
            self._error('Missing or invalid database information')
        # baseunpackdirectory must be declared
        if not self.options.baseunpackdirectory:
            self._error('Missing base unpack directory')
        # baseunpackdirectory must exist
        if not os.path.exists(self.options.baseunpackdirectory):
            self._error("Base unpack directory %s does not exist, exiting" % self.options.baseunpackdirectory)
        # .. be a directory
        if not os.path.isdir(self.options.baseunpackdirectory):
            self._error("Base unpack directory %s is not a directory, exiting" % self.options.baseunpackdirectory)
        # and writable
        if self.checkIfDirectoryIsWritable(self.options.baseunpackdirectory):
            self._error("Base unpack directory %s cannot be written to, exiting" % self.options.baseunpackdirectory)
        # if temporarydirectory is defined
        if self.options.temporarydirectory != None:
            # it must exist,
            if not os.path.exists(self.options.baseunpackdirectory):
                self._error("Temporary directory %s does not exist, exiting" % self.options.temporarydirectory)
            # .. be a directory
            if not os.path.isdir(self.options.baseunpackdirectory):
                self._error("Temporary directory %s is not a directory, exiting" % self.options.temporarydirectory)
            # .. and writable
            if self.checkIfDirectoryIsWritable(self.options.baseunpackdirectory):
                self._error("Temporary directory %s cannot be written to, exiting" % self.options.temporarydirectory)

        # either a check directory or a check file must be specified
        if self.options.checkdirectory == None and self.options.checkfile == None:
            self._error("No file(s) provided to scan, exiting")
        if self.options.checkdirectory != None and self.options.checkfile != None:
            self._error("Cannot scan a directory and a single file, exiting")
        if self.options.checkdirectory != None:
            if not stat.S_ISDIR(os.stat(self.options.checkdirectory).st_mode):
                self._error("%s is not a directory, exiting." % self.options.checkdirectory)
        if self.options.checkfile != None:
            # the file to scan should exist ...
            if not os.path.exists(self.options.checkfile):
                self._error("File %s does not exist, exiting." % self.options.checkfile)
            # ... and should be a real file
            if not stat.S_ISREG(os.stat(self.options.checkfile).st_mode):
                self._error("%s is not a regular file, exiting." % self.options.checkfile)
            # ... and not empty
            if os.stat(self.options.checkfile).st_size == 0:
                self._error("%s is an empty file, exiting" % self.options.checkfile)

    def checkIfDirectoryIsWritable(self,dirname):
        try:
            testfile = tempfile.mkstemp(dir=dirname)
            os.unlink(testfile[1])
            return True
        except:
            return False

