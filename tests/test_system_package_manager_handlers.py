
import unittest

from vcp.system_package_manager_handlers import SystemPackageManagerHandlerFactory

from voidpp_tools.mocks.file_system import mockfs

OS_RELEASE = dict(
    ubuntu = u"""
NAME="Ubuntu"
VERSION="14.04.1 LTS, Trusty Tahr"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 14.04.1 LTS"
VERSION_ID="14.04"
HOME_URL="http://www.ubuntu.com/"
SUPPORT_URL="http://help.ubuntu.com/"
BUG_REPORT_URL="http://bugs.launchpad.net/ubuntu/"
""",
    debian = u"""
PRETTY_NAME="Debian GNU/Linux 8 (jessie)"
NAME="Debian GNU/Linux"
VERSION_ID="8"
VERSION="8 (jessie)"
ID=debian
HOME_URL="http://www.debian.org/"
SUPPORT_URL="http://www.debian.org/support"
BUG_REPORT_URL="https://bugs.debian.org/"
"""
)

class TestSystemPackageManagerHandler(unittest.TestCase):

    @mockfs(dict(etc = {'os-release': OS_RELEASE['debian']}))
    def test_get_current_debian(self):
        # Arrange
        factory = SystemPackageManagerHandlerFactory()

        # Act
        os_type = factory.get_current()

        # Assert
        self.assertEqual(os_type, 'debian')

    @mockfs(dict(etc = {'os-release': OS_RELEASE['ubuntu']}))
    def test_get_current_ubuntu(self):
        # Arrange
        factory = SystemPackageManagerHandlerFactory()

        # Act
        os_type = factory.get_current()

        # Assert
        self.assertEqual(os_type, 'ubuntu')

    @mockfs()
    def test_get_current_missing_file(self):
        # Arrange
        factory = SystemPackageManagerHandlerFactory()

        # Act
        os_type = factory.get_current()

        # Assert
        self.assertIsNone(os_type)
