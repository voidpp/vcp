import os
import re
import logging
from subprocess import check_call, check_output, CalledProcessError, PIPE
from abc import ABCMeta, abstractmethod, abstractproperty

from .exceptions import SystemPackageManagerHandlerException

logger = logging.getLogger(__name__)

def register(name, distros):
    def wrapper(cls):
        cls.name = name
        for distro in distros:
            SystemPackageManagerHandlerFactory.types[distro] = cls
        return cls
    return wrapper

class SystemPackageManagerHandlerFactory(object):
    types = {}

    def get_current(self):
        release_info_file = '/etc/os-release'
        if not os.path.isfile(release_info_file):
            logger.error("Could not find %s to determine linux distro", release_info_file)
            return None
        with open(release_info_file) as f:
            data = f.read()
        matches = re.search('^ID=(.+)', data, re.MULTILINE)
        if not matches:
            logger.error("Could not find ID field in release info: %s", data)
            return None
        return matches.group(1)

    def create(self):
        name = self.get_current()
        if name is None:
            raise SystemPackageManagerHandlerException("Cannot determine the current system distro name.")
        if name not in self.types:
            raise SystemPackageManagerHandlerException("Unknown distro type {}. Known types: {}".format(name, self.types.keys()))
        return self.types[name]()

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

@register('dpkg', ['debian', 'ubuntu'])
class DPKGHandler(SystemPackageManagerHandlerHandlerBase):

    __metaclass__ = ABCMeta

    def is_package_installed(self, name):
        try:
            check_call(['dpkg', '-s', name], stdout = PIPE, stderr = PIPE)
            return True
        except CalledProcessError as e:
            if e.returncode == 1:
                return False
            else:
                raise

@register('pacman', ['arch'])
class PacManHandler(SystemPackageManagerHandlerHandlerBase):

    __metaclass__ = ABCMeta

    def is_package_installed(self, name):
        try:
            check_call(['pacman', '-Qi', name], stdout = PIPE, stderr = PIPE)
            return True
        except CalledProcessError as e:
            if e.returncode == 1:
                return False
            else:
                raise
