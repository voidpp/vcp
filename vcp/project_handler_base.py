import logging
import os
import re
import yaml
from abc import ABCMeta, abstractmethod

PROJECT_CONFIG_EXTENSION = "yaml"

logger = logging.getLogger(__name__)

class ProjectHandlerFactory(object):

    handlers = {}

    def __init__(self):
        self.schema_pattern = re.compile("^({}):\/\/(.+)".format('|'.join(self.handlers.keys())))

    def create(self, uri, local_path):
        """Create a project handler

        Args:
            uri (str): schema://something formatted uri
            local_path (str): the project configs directory

        Return:
            ProjectHandler derived class instance
        """
        matches = self.schema_pattern.search(uri)

        if not matches:
            logger.error("Unknown uri schema: '%s'. Added schemas: %s", uri, self.handlers.keys())
            return None

        schema = matches.group(1)
        url = matches.group(2)

        return self.handlers[schema](url, local_path)


def register_schema(schema):
    def decorator(cls):
        ProjectHandlerFactory.handlers[schema] = cls
        return cls
    return decorator

class ProjectHandlerBase(object):

    __metaclass__ = ABCMeta

    def __init__(self, url, path):
        self.url = url
        self.path = self.get_path(path)

    def get_project_config_path(self, name):
        base_path = os.path.expanduser(self.path)
        return os.path.join(base_path, "{}.{}".format(name, PROJECT_CONFIG_EXTENSION))

    def load(self):
        """Load the projects config data from local path

        Returns:
            Dict: project_name -> project_data
        """
        projects = {}

        path = os.path.expanduser(self.path)

        if not os.path.isdir(path):
            return projects

        logger.debug("Load project configs from %s", path)

        for filename in os.listdir(path):
            filename_parts = os.path.splitext(filename)

            if filename_parts[1][1:] != PROJECT_CONFIG_EXTENSION:
                continue
            name = filename_parts[0]

            try:
                project_file_path = os.path.join(path, filename)
                with open(project_file_path) as f:
                    data = yaml.load(f)
                projects[name] = data
            except ValueError:
                continue

            logger.debug("Project '{}' config readed from {}".format(name, project_file_path))

        return projects

    def save(self, projects):
        """Save the projects configs to local path

        Args:
            projects (dict): project_name -> project_data
        """

        base_path = os.path.expanduser(self.path)

        if not os.path.isdir(base_path):
            return

        logger.debug("Save projects config to %s", base_path)

        for name, data in projects.items():
            project_file_path = self.get_project_config_path(name)
            with open(project_file_path, "w") as f:
                yaml.dump(data, stream = f, default_flow_style = False)
                logger.debug("Project '%s' config has been writed to '%s'", name, project_file_path)

    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def get_path(self, path):
        pass

    @abstractmethod
    def config_init(self):
        pass

    @abstractmethod
    def post_process_cli_config(self, config):
        pass

    @abstractmethod
    def edit(self, name, summary, command_result):
        pass

    @abstractmethod
    def create(self, name, default, command_result):
        pass

    @abstractmethod
    def remove(self, name, command_result):
        pass
