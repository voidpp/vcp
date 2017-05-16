import os
import json
import logging
import shutil
from subprocess import check_call, check_output, CalledProcessError, STDOUT
from abc import ABCMeta, abstractmethod, abstractproperty

from .language_environments import PythonEnvironment, JavascriptEnvironment

logger = logging.getLogger(__name__)


def register(lang_name):
    def wrapper(cls):
        LanguageFactory.types[lang_name] = cls
        return cls
    return wrapper

class LanguageFactory(object):
    types = {}

    def create(self, project, types):
        return [self.types[t](project, t) for t in types]

class LanguageBase(object):

    __metaclass__ = ABCMeta

    def __init__(self, project, name):
        self.name = name
        self.project = project
        self._env = None

    @abstractmethod
    def init(self):
        """Initialize the language specific part of the project, eg pip install or npm install.

        Returns:
            True if the initialization is succeeded, else False
        """
        pass

    @abstractmethod
    def install_to(self, project, env):
        """Install current (self.project) project to the argument one.

        Args:
            project (Project): the target project
            env (EnvironmentBase): the target environment

        Returns:
            True if the install is succeeded, else False
        """
        pass

    @abstractproperty
    def env(self):
        pass

    def __str__(self):
        return self.name

@register('python')
class Python(LanguageBase):

    @property
    def _env_path(self):
        return os.path.join(self.project.vcp.python_venv['path'], self.project.name)

    @property
    def _interpreter(self):
        return self.project.vcp.python_venv['interpreter']

    @property
    def env(self):
        if self._env is None:
            self._env = PythonEnvironment(self._env_path, python = self._interpreter)
            if not self._env._pip_exists():
                logger.info("Create virtual environment for project '{}'".format(self.project.name))
            self._env.open_or_create()
        return self._env

    def install_dev(self, path, env):
        env.install('-e {}'.format(path))
        return True

    def install_to(self, project, env):
        self.install_dev(self.project.path, env)

    def init(self):
        for name, project in self.project.get_dependent_projects().items():
            project.install_to(self.project, self.env)

        logger.info("Install '{}' as editable package".format(self.project.name))
        return self.install_dev(self.project.path, self.env)

    def purge(self):
        if os.path.isdir(self._env_path):
            logger.debug("Remove python virtual environment from '{}'".format(self._env_path))
            shutil.rmtree(self._env_path)


@register('python2')
class Python2(LanguageBase):

    @property
    def _interpreter(self):
        return 'python2'

@register('python3')
class Python3(LanguageBase):

    @property
    def _interpreter(self):
        return 'python3'

@register('javascript')
class Javascript(LanguageBase):

    @property
    def env(self):
        if self._env is None:
            self._env = JavascriptEnvironment(self.project.path, self.project.vcp.npm_config, self.project.vcp.npm_usage_config)
        return self._env

    def get_package_name(self):
        with open(os.path.join(self.project.path, 'package.json')) as f:
            data = json.load(f)
            return data['name']

    def install_to(self, project, env):
        if self.project.path is None:
            logger.error("Why self.project({}).path is None?".format(self.project.name))
            raise Exception("madafaka")
        name = self.get_package_name()
        logger.info("Make link in {} to {}".format(project.name, self.project.name))
        env.link(name)

    def init(self):
        try:
            # for create an order, needs all dep recursively, but after this the not direct dep must be not linked, so need to remove
            all_deps = self.project.get_sorted_dependencies(remove_indirect_deps = True)
            direct_dep_names = self.project.dependencies.keys()
            deps = [p for p in all_deps if p.name in direct_dep_names]

            for project in reversed(deps):
                project.install_to(self.project, self.env)

            logger.info("Install all the npm dependencies.")

            install_res = self.env.install()
            self.env.link()

            logger.debug("Install output:\n{}".format(install_res))

            if install_res is None:
                return False

        except CalledProcessError as e:
            logger.error("Error in init\n{}".format(e), exc_info = True)
            return False

        return True

    def purge(self):
        self.env.unlink()
