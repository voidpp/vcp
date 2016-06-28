import os
from abc import ABCMeta, abstractmethod
import getpass
import json
from collections import OrderedDict
import logging
import shutil
from tools import confirm_prompt

logger = logging.getLogger(__name__)

class PackageFactory(object):

    types = {}

    def create(self, name):
        return self.types[name]()

def register(name):
    def decor(cls):
        PackageFactory.types[name] = cls
        return cls
    return decor

class PackageBase(object):

    __metaclass__ = ABCMeta

    @abstractmethod
    def init(self):
        pass


@register('python')
class PythonPackage(PackageBase):

    config_filename = 'setup.json'

    def init(self, path = os.getcwd()):
        config_file_path = os.path.join(path, self.config_filename)

        if os.path.exists(config_file_path):
            logger.error("In this folder there is a python package already!")
            return

        dirname = path.split('/')[-1:][0]
        descriptors = [
            dict(name = 'name', label = 'Name', default = dirname),
            dict(name = 'version', label = 'Version', default = '0.0.1'),
            dict(name = 'description', label = 'Description', default = None),
            dict(name = 'author', label = 'Author', default = getpass.getuser()),
            dict(name = 'author_email', label = 'Author email', default = None),
            dict(name = 'url', label = 'URL', default = None),
            dict(name = 'license', label = 'Licence', default = 'MIT'),
            dict(name = 'install_requires', label = None, default = []),
            dict(name = 'packages', label = None, default = [dirname]),
            dict(name = 'include_package_data', label = None, default = True),
            dict(name = 'scripts', label = None, default = []),
        ]

        data = OrderedDict()

        logger.info("This utility will walk you through creating files for a python package.\n"
                    "It only covers the most common items, and tries to guess sensible defaults.\n\n"
                    "Press ^C at any time to quit.\n")
        try:
            for desc in descriptors:
                if desc['label'] is None:
                    value = desc['default']
                else:
                    msg = "{}: ".format(desc['label'])
                    if desc['default'] is not None:
                        msg += "({}) ".format(desc['default'])
                    value = raw_input(msg)
                    if len(value) == 0 and desc['default'] is not None:
                        value = desc['default']

                data[desc['name']] = value
        except KeyboardInterrupt:
            print("\n")
            logger.warning("Python package initialization cancelled.")
            return

        logger.info("\nAbout to write setup.json:\n%s", json.dumps(data, indent = 2))

        if not confirm_prompt("Is this ok? "):
            return

        with open(config_file_path, 'w') as f:
            json.dump(data, f, indent = 2)
            f.write("\n")

        shutil.copy(os.path.join(os.path.dirname(__file__), 'setup_py_template.py'), os.path.join(path, 'setup.py'))

        with open(os.path.join(path, 'MANIFEST.in'), 'w') as f:
            f.write("include setup.json\n")

        logger.info("Files created")
