
import unittest

from vcp import VCP

class FakeConfigLoader(object):

    def __init__(self, config):
        self.config = config

    def load(self, filename):
        self.filename = filename
        return self.config

    def save(self, filename):
        pass

class TestCore(unittest.TestCase):

    def test_build_from_empty(self):
        vcp = VCP(FakeConfigLoader({}))
        self.assertEquals(len(vcp.projects), 0)
        self.assertEquals(len(vcp.repositories), 0)
        self.assertEquals(vcp.default_project, None)
