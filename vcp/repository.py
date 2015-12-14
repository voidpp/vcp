
import os
import pty
from subprocess import Popen, PIPE
from abc import ABCMeta, abstractmethod

import logging
logger = logging.getLogger(__name__)

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
    type = 'notimplemented'

    def __init__(self, path, name):
        self.path = path
        self.name = name

    def list_cmd(self, command):
        return self.cmd(command).split("\n")[:-1]

    def cmd(self, command):
        # pty for colored output
        master, slave = pty.openpty()
        p = Popen(command, cwd = self.path, shell = True, stdout = slave, stderr = slave)
        logger.debug("Execute command: '%s' in '%s'" % (command, self.path))
        p.communicate()
        return os.read(master, num_bytes_readable(master))

    @abstractmethod
    def diff(self):
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

    def __repr__(self):
        return "<Repository: %s>" % self.__dict__()

    def __dict__(self):
        return dict(
            path = self.path,
            name = self.name,
            type = self.type,
        )
