
import os
import pty
from subprocess import Popen, PIPE
from abc import ABCMeta, abstractmethod
import logging

from .exceptions import RepositoryCommandException

logger = logging.getLogger(__name__)

def register_type(type_name):
    def wrapper(cls):
        RepositoryFactory.types[type_name] = cls
        return cls
    return wrapper

class RepositoryFactory(object):
    types = {}

    def create(self, path, type, name):
        repo = self.types[type](path, name)
        repo.type = type
        return repo

def num_bytes_readable(fd):
    import array
    import fcntl
    import termios
    buf = array.array('i', [0])
    if fcntl.ioctl(fd, termios.FIONREAD, buf, 1) == -1:
        raise Exception("We really should have had data")
    return buf[0]

class Repository(object):
    __metaclass__ = ABCMeta

    def __init__(self, path, name):
        self.path = path
        self.name = name
        self.type = None

    def list_cmd(self, command):
        return self.cmd(command).split("\n")[:-1]

    # somewhat this way to get colored output stucks the execution on osx
    # def cmd(self, command, raise_on_error = False):
    #     # pty for colored output
    #     master, slave = pty.openpty()
    #     p = Popen(command, cwd = self.path, shell = True, stdout = slave, stderr = slave)
    #     logger.debug("Execute command: '%s' in '%s'" % (command, self.path))
    #     p.communicate()
    #     if p.returncode != 0 and raise_on_error:
    #         raise RepositoryCommandException(p.returncode, command, os.read(master, num_bytes_readable(master)))
    #     return os.read(master, num_bytes_readable(master))

    def cmd(self, command, raise_on_error = False):
        from subprocess import STDOUT
        logger.debug("Execute command: '%s' in '%s'", command, self.path)
        p = Popen(command, shell = True, cwd = self.path, stdout = PIPE, stderr = STDOUT)
        stdout, _ = p.communicate()
        if p.returncode != 0 and raise_on_error:
            raise RepositoryCommandException(p.returncode, command, stdout)
        return stdout

    @abstractmethod
    def set_ref(self, ref):
        pass

    @abstractmethod
    def init(self, url):
        pass

    @abstractmethod
    def diff(self):
        pass

    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def fetch(self):
        pass

    @abstractmethod
    def pushables(self, remote):
        pass

    @abstractmethod
    def status(self):
        pass

    @abstractmethod
    def get_untracked_files(self):
        pass

    @abstractmethod
    def get_dirty_files(self):
        pass

    @abstractmethod
    def get_own_commits_since(self, since_str):
        pass

    def __repr__(self):
        return "<Repository: %s>" % self.__dict__()

    def __dict__(self):
        return dict(
            path = self.path,
            name = self.name,
            type = self.type,
        )
