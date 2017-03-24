import os
import logging
from abc import ABCMeta, abstractmethod, abstractproperty
from subprocess import check_output, CalledProcessError, list2cmdline, check_call
from virtualenvapi.manage import VirtualEnvironment

logger = logging.getLogger(__name__)

class EnvironmentBase(object):

    __metaclass__ = ABCMeta

    @abstractmethod
    def get_status(self, force = False):
        pass

    @abstractproperty
    def last_status(self):
        pass

class PythonEnvironment(VirtualEnvironment, EnvironmentBase):

    def get_status(self, force = False):
        return True

    @property
    def last_status(self):
        return True

class JavascriptEnvironment(dict, EnvironmentBase):

    def __init__(self, path, config = {}, npm_usage_config = {}):
        self.path = path
        self.vars = vars
        self.__env = os.environ.copy()
        self.__env.update({"npm_config_{}".format(name): val for name, val in config.items()})
        self.__bin = npm_usage_config.get('command_override', 'npm')
        self.__last_status = False
        self.__do_status_check = npm_usage_config.get('check_status', True)

    @property
    def last_status(self):
        return self.__last_status

    def cmd(self, command):
        try:
            logger.debug("Call command: {} in {}".format(list2cmdline(command), self.path))
            return check_output(command, env = self.__env, cwd = self.path)
        except CalledProcessError as e:
            logger.exception("Error in call")
            return None

    def npm(self, command):
        return self.cmd([self.__bin] + command)

    def link(self, name = None):
        cmd = ['link']
        if name:
            cmd.append(name)
        return self.npm(cmd)

    def get_status(self):
        if not self.__do_status_check:
            return True

        try:
            # npm ls will return 1 when there is an error with the packages (missing, extranous, etc...)
            check_call([self.__bin, 'ls'], env = self.__env, cwd = self.path)
            self.__last_status = True
        except CalledProcessError as e:
            self.__last_status = False

        return self.__last_status

    def install(self, name = None, save = False, save_dev = False, save_opt = False, save_exact = False):
        cmd = ['install']

        if name:
            cmd.append(name)
        else:
            return self.npm(cmd)

        if save:
            cmd.append('--save')
        if save_dev:
            cmd.append('--save-dev')
        if save_dev:
            cmd.append('--save-optional')
        if save_dev:
            cmd.append('--save-exact')

        return self.npm(cmd)

    def unlink(self, name = None):
        return ''
        cmd = ['unlink']
        if name:
            cmd.append(name)
        return self.npm(cmd)
