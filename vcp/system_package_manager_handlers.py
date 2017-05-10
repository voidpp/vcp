import os
import re
import logging
from subprocess import check_call, check_output, CalledProcessError, PIPE
from abc import ABCMeta, abstractmethod, abstractproperty
import platform

from .exceptions import SystemPackageManagerHandlerException

logger = logging.getLogger(__name__)

def register(name, determiner):
    def wrapper(cls):
        cls.name = name
        cls.determiner = determiner
        SystemPackageManagerHandlerFactory.types[name] = cls
        return cls
    return wrapper

class SystemPackageManagerHandlerFactory(object):
    types = {}

    def create(self):
        for name, cls in self.types.items():
            if cls.determiner.test():
                return self.types[name]()

        raise SystemPackageManagerHandlerException("Cannot determine the current system distro name.")

class SystemPackageManagerHandlerHandlerBase(object):

    __metaclass__ = ABCMeta

    def get_system_dependencies(self, project):
        if self.name not in project.system_dependencies:
            return []
        return project.system_dependencies[self.name]

    def get_not_installed_packages(self, project):
        names = self.get_system_dependencies(project)
        return [name for name in names if not self.is_package_installed(name)]

    @abstractmethod
    def is_package_installed(self, name):
        pass

class DeterminerBase(object):

    __metaclass__ = ABCMeta

    @abstractmethod
    def test(self):
        pass

class LinuxDeterminer(DeterminerBase):

    def __init__(self, *distro_names):
        self._names = distro_names

    def test(self):
        distro_name = platform.linux_distribution()[0].lower()
        return distro_name in self._names

class MaxOSDeterminer(DeterminerBase):

    def __init__(self, pkg_mgr):
        self._pkg_mgr = pkg_mgr

    def test(self):
        mac_ver = platform.mac_ver()
        # not mac
        if len(mac_ver[0]) < 2:
            return False

        try:
            check_call(['which', self._pkg_mgr], stdout = PIPE, stderr = PIPE)
            return True
        except CalledProcessError:
            return False

@register('brew', MaxOSDeterminer('brew'))
class BrewHandler(SystemPackageManagerHandlerHandlerBase):

    def is_package_installed(self, name):
        try:
            check_call(['brew', 'ls', '--versions', name], stdout = PIPE, stderr = PIPE)
            return True
        except CalledProcessError as e:
            if e.returncode == 1:
                return False
            else:
                raise

@register('dpkg', LinuxDeterminer('debian', 'ubuntu', 'linuxmint'))
class DPKGHandler(SystemPackageManagerHandlerHandlerBase):

    def is_package_installed(self, name):
        try:
            check_call(['dpkg', '-s', name], stdout = PIPE, stderr = PIPE)
            return True
        except CalledProcessError as e:
            if e.returncode == 1:
                return False
            else:
                raise

@register('pacman', LinuxDeterminer('arch'))
class PacManHandler(SystemPackageManagerHandlerHandlerBase):

    def is_package_installed(self, name):
        try:
            check_call(['pacman', '-Qi', name], stdout = PIPE, stderr = PIPE)
            return True
        except CalledProcessError as e:
            if e.returncode == 1:
                return False
            else:
                raise
