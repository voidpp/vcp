
import os
import pkg_resources
from prettytable import PrettyTable
from functools import partial
from logging import getLogger
from voidpp_tools.json_config import JSONConfigLoader

from .project import Project
from .box_renderer import BoxRenderer
from .git_repository import GitRepository
from .exceptions import RepositoryException, ProjectException

logger = getLogger(__name__)

class RepositoryFactory(object):
    def __init__(self):
        self.types = {}
        self.types[GitRepository.type] = GitRepository

    def create(self, path, type, name):
        return self.types[type](path, name)

class ProjectModifyRepositoryCommand(object):
    def __init__(self, project, vcp):
        self.project = project
        self.vcp = vcp

    def add(self, names):
        self.project.repositories += list(set(names))
        logger.info("Repo added to project '%s'" % self.project.name)
        self.vcp.save_config()

    def clear(self):
        self.project.repositories = []
        logger.info("Repositories cleared from project '%s'" % self.project.name)
        self.vcp.save_config()

    def remove(self, names):
        self.project.repositories = list(set(self.project.repositories) - set(names))
        logger.info("Repo removed from project '%s'" % self.project.name)
        self.vcp.save_config()

class ProjectModifyCommand(object):
    def __init__(self, project, vcp):
        self.project = project
        self.vcp = vcp

    def repository(self):
        return ProjectModifyRepositoryCommand(self.project, self.vcp)

    def description(self, data):
        self.project.description = data
        logger.info("Description modified")
        self.vcp.save_config()

class DyanmicProjectModifyCommand(object):
    def __init__(self, vcp):
        self.vcp = vcp

    def __hasattr__(self, name):
        return name in self.vcp.projects

    def __getattr__(self, name):
        return partial(ProjectModifyCommand, self.vcp.projects[name], self.vcp)

class ProjectCommand(object):
    def __init__(self, vcp):
        self.vcp = vcp

    def create(self, name, description, repositories, default = False):
        if name in self.vcp.projects:
            raise ProjectException("Project '%s' is already exists" % name)
        self.vcp.projects[name] = Project(name, description, repositories)

        if default:
            self.vcp.default_project = name

        logger.info("Project '%s' created" % name)
        self.vcp.save_config()

    def default(self, name):
        self.vcp.default_project = name
        logger.info("Project '%s' set for default project" % name)
        self.vcp.save_config()

    def remove(self, name):
        del self.vcp.projects[name]
        logger.info("Project '%s' removed" % name)
        self.vcp.save_config()

    def modify(self):
        return DyanmicProjectModifyCommand(self.vcp)

    def show(self, name):
        project = self.vcp.projects[name]

        logger.info("Repositories of '%s'(%s) project:" % (project.name, project.description))

        table = PrettyTable(["Type", "Name", "Path"])
        table.align = 'l'
        for repo_name in project.repositories:
            repo = self.vcp.repositories[repo_name]
            table.add_row([repo.type, repo.name, repo.path])
        logger.info(table)

    def list(self):
        logger.info("Known projects:")
        table = PrettyTable(["Name", "Description", "Repo cnt"])
        table.align = 'l'
        table.align["Repo cnt"] = "r"
        for project in self.vcp.projects.values():
            table.add_row([project.name, project.description, len(project.repositories)])

        logger.info(table)

class RepositoryCommand(object):
    def __init__(self, vcp):
        self.vcp = vcp

    def cmd(self, name, command):
        logger.info(self.vcp.repositories[name].cmd(command))

    def list(self):
        logger.info("Known repositories")

        table = PrettyTable(["Type", "Name", "Path"])
        table.align = 'l'
        for repo_name in self.vcp.repositories:
            repo = self.vcp.repositories[repo_name]
            table.add_row([repo.type, repo.name, repo.path])
        logger.info(str(table))

    def remove(self, name):
        del self.vcp.repositories[name]
        for prj_name in self.vcp.projects:
            project = self.vcp.projects[prj_name]
            if name in project.repositories:
                project.repositories.remove(name)
                logger.info("Repository '%s' removed from project '%s'" % (name, prj_name))
        logger.info("Repository '%s' removed" % name)
        self.vcp.save_config()

    def create(self, path, type, name, add_to = None):
        path = os.path.abspath(path)
        if not os.path.isdir(path):
            raise RepositoryException("Path '%s' is not exists" % path)
        if name is None:
            name = path.split(os.path.sep)[-1:][0]

        if name in self.vcp.repositories:
            raise ProjectException("Repository '%s' is already exists" % name)

        self.vcp.repositories[name] = self.vcp.repo_factory.create(path, type, name)

        msg = "Repository '%s' created" % name

        if add_to is not None:
            add_to = set(add_to)
            for prj_name in add_to:
                self.vcp.projects[prj_name].repositories.append(name)
            msg += " and added to project: " + ', '.join(add_to)

        logger.info(msg)
        self.vcp.save_config()

class VCP(object):

    def __init__(self, config_file_name = '.vcp'):
        self.config_loader = JSONConfigLoader(__file__)
        self.config = self.config_loader.load(config_file_name)
        self.default_project = None
        self.projects = {}
        self.repositories = {}
        self.box_renderer = BoxRenderer()
        self.repo_factory = RepositoryFactory()
        self.command_names = []

        if 'projects' in self.config:
            for name in self.config['projects']:
                project = Project(**self.config['projects'][name])
                project.db = self
                self.projects[name] = project

        if 'repositories' in self.config:
            for name in self.config['repositories']:
                self.repositories[name] = self.repo_factory.create(**self.config['repositories'][name])

        if 'default_project' in self.config:
            self.default_project = self.config['default_project']

    def action_commands_lookup(self, project_related_commands):
        self.command_names = [command['name'] for command in project_related_commands]

    # common handler for all project related action commands
    def __getattr__(self, attr_name):
        if attr_name not in self.command_names:
            raise KeyError(attr_name)

        def action(name, **kwargs):
            list = kwargs['list']
            del kwargs['list']
            project = self.projects[name]
            if list:
                logger.info(','.join([box.repository.name for box in getattr(project, attr_name)(**kwargs)]))
            else:
                for box in getattr(project, attr_name)(**kwargs):
                    logger.info(self.box_renderer.render(box))

        return action

    def version(self):
        logger.info(pkg_resources.get_distribution("vcp").version)

    def repository(self):
        return RepositoryCommand(self)

    def project(self):
        return ProjectCommand(self)

    def get_data(self):
        return dict(
            projects = self.projects,
            repositories = self.repositories,
            default_project = self.default_project,
        )

    def save_config(self):
        self.config_loader.save(self.get_data())
        logger.info("Config saved")
