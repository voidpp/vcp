import os
import imp
import json
import shutil
import logging
import getpass
from abc import ABCMeta, abstractmethod
from collections import OrderedDict
from setuptools import find_packages
import pip

from .tools import confirm_prompt

logger = logging.getLogger(__name__)

class PackageFactory(object):

    types = {}

    def create(self, name):
        return self.types[name]()

    def create_all(self):
        for cls in self.types.values():
            yield cls()

def register(name):
    def decor(cls):
        PackageFactory.types[name] = cls
        return cls
    return decor

class PackageBase(object):

    __metaclass__ = ABCMeta

    @abstractmethod
    def init(self, path):
        pass

    @abstractmethod
    def install_requirements(self):
        pass


@register('python')
class PythonPackage(PackageBase):

    config_filename = 'setup.json'

    def __get_old_style_config_py_data(self, path):
        config_py_file_path = os.path.join(path, 'config.py')
        if not os.path.isfile(config_py_file_path):
            return {}
        return imp.load_source('config', config_py_file_path).config

    def config_file_path(self, path):
        return os.path.join(path, self.config_filename)

    def init(self, path = os.getcwd()):
        config_file_path = self.config_file_path(path)
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
            dict(name = 'packages', label = None, default = find_packages()),
            dict(name = 'include_package_data', label = None, default = True),
            dict(name = 'scripts', label = None, default = []),
        ]

        defaults = self.__get_old_style_config_py_data(path)

        for desc in descriptors:
            desc['default'] = defaults.get(desc['name'], desc['default'])

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


    def install_requirements(self):
        config_file_path = self.config_file_path(os.getcwd())

        if not os.path.isfile(config_file_path):
            raise Exception("This is not a python package ('{}' not found)".format(self.config_filename))

        with open(config_file_path) as f:
            config_data = json.load(f)

        packages = config_data.get('install_requires', []) + config_data.get('dev_requirements', [])

        if not len(packages):
            logger.info("There is no packages to install!")
            return

        pip.main(['install'] + packages + ['--upgrade'])
