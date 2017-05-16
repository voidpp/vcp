
import logging
import tempfile
import yaml
import os
import shutil
from functools import wraps
from subprocess import check_call, CalledProcessError
from prettytable import PrettyTable


from .project import Project
from .exceptions import RepositoryException, ProjectException
from .tools import confirm, confirm_prompt

logger = logging.getLogger(__name__)


def post_process(func):
    """Calls the project handler same named function

    Note: the project handler may add some extra arguments to the command,
          so when use this decorator, add **kwargs to the end of the arguments

    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        project_command = args[0]
        project_handler = project_command.vcp.project_handler
        if not project_handler:
            return res
        kwargs['command_result'] = res
        getattr(project_handler, func.func_name)(**kwargs)
        return res

    return wrapper

class ProjectConfigCommand(object):
    def __init__(self, vcp):
        self.vcp = vcp

    def uri(self, value):
        matches = self.vcp.project_handler_factory.schema_pattern.search(value)

        if not matches:
            logger.error("Unknown uri schema: '{}'".format(value))
            return

        self.vcp.projects_reference['uri'] = value

        try:
            project_handler = self.vcp.project_handler_factory.create(value, self.vcp.projects_reference['path'])
            project_handler.config_init()
        except Exception as e:
            logger.error("Unknown error: {}".format(e), exc_info = e)
            return

        self.vcp.save_config()
        logger.info("Project config storage uri has been set!")

    def path(self, value):
        self.vcp.projects_reference['path'] = value
        self.vcp.save_config()

    def update(self):
        self.vcp.project_handler.update()

class ProjectCommand(object):
    def __init__(self, vcp):
        self.vcp = vcp

    def __init(self, project, path, force, init_languages):
        status = {}
        """
        REFACTOR status to project init result ENUM
        jelenleg ha a project init False, akkor torlunk minden adatot a projectrol
        de van egy atmenet, mikor csak a lang init nem sikerult
        erre valo jelenleg a status. ez rossz
        """

        project.init(path, status, force, init_languages = init_languages)

        failed = []
        for name, val in status.items():
            if val is False and name not in failed:
                failed.append(name)

        return failed

    def __search_sub_path_in_repos(self, path):
        search = os.path.realpath(path) + os.sep
        for name, repo in self.vcp.repositories.items():
            repo_path = os.path.realpath(repo.path) + os.sep
            if search.startswith(repo_path):
                print repo_path, search
                return repo
        return None

    def __confirm_init_path(self, path):
        repo = self.__search_sub_path_in_repos(path)
        if repo:
            if not confirm_prompt("The given path is under the '{}' repo. Do you really want to initialize the new project(s) to it?".format(repo.name)):
                return False
        return True

    def __default(self, name):
        self.vcp.default_project = name
        logger.info("Project '%s' set for default project" % name)

    def __edit(self, project):
        with tempfile.NamedTemporaryFile(suffix = '.yaml', mode = "rw+") as fd:

            # write project data to the tmp file
            yaml.dump(project.data, stream = fd, default_flow_style = False)
            fd.flush()

            # open editor with tmp file
            editor = os.getenv('EDITOR', default = 'vim')
            try:
                check_call([editor, fd.name])
            except CalledProcessError as e:
                logger.error("Error occured when calling editor: {}".format(e.output))
                return False

            # read back the tmp file content
            fd.seek(0, 0)
            data = yaml.load(fd)

            # save data if changed
            if data == project.data:
                return False

            unknown_deps = []
            for name, ref in data['dependencies'].items():
                if name not in self.vcp.projects:
                    unknown_deps.append(name)

            if len(unknown_deps):
                logger.error("Unknown dependencies: {}".format(unknown_deps))
                return False

            project.data = data

        self.vcp.save_config()

        return True

    def init(self, name, path, force = False, init_languages = True):
        if not self.__confirm_init_path(path):
            return

        project = self.vcp.projects[name]
        tries = 5

        for i in range(tries):

            failed = self.__init(project, path, force, init_languages)

            if not len(failed):
                break

            logger.error("In {} projects the init was not successfull ({}). Try again! ({}/{})".format(len(failed), ', '.join(failed), i+1,tries))

            if i+1 == tries:
                logger.error("No more attempt...")

            force = True

        self.vcp.save_config()

    def update(self, name, path):
        self.vcp.project_handler.update()
        self.init(name, path, force = True, init_languages = True)

    def config(self):
        return ProjectConfigCommand(self.vcp)

    def workon(self, name):
        self.__default(name)
        prj = self.vcp.projects[name]
        prj.set_dependencies_state()
        self.vcp.save_config()

    def show(self, name):
        prj = self.vcp.projects[name]
        logger.info(yaml.dump(prj.data, default_flow_style = False))

    @post_process
    def remove(self, name, **kwargs):
        # TODO: check other projects dependencies
        del self.vcp.projects[name]
        os.remove(self.vcp.project_handler.get_project_config_path(name))
        logger.info("Project removed")
        self.vcp.save_project_config()

    @post_process
    def edit(self, name, summary, **kwargs):
        res = self.__edit(self.vcp.projects[name])
        if res:
            logger.info("Project modified")
            self.vcp.save_project_config()
        return res

    @post_process
    def create(self, name, default = False, **kwargs):
        if name in self.vcp.projects:
            raise ProjectException("Project '%s' is already exists" % name)

        if default:
            self.vcp.default_project = name

        prj = Project(name, self.vcp)

        self.vcp.projects[name] = prj

        res = self.__edit(prj)
        if res:
            logger.info("Project created")
            self.vcp.save_project_config()
        return res

    def list(self):
        table = PrettyTable(["Name", "Description", "Deps", "Languages", "Initialized"])
        table.align = 'l'
        table.align["Deps"] = "r"
        projects = self.vcp.projects.values()
        for project in sorted(projects, key = lambda p: p.name):
            table.add_row([
                project.name,
                project.description,
                len(project.get_dependent_projects()),
                ', '.join(project.data['languages']),
                project.initialized,
            ])

        logger.info("Known projects ({}):\n{}".format(len(projects), table))

    def default(self, name):
        self.__default(name)
        self.vcp.save_config()

    @confirm()
    def purge(self, name, iamsure):
        project = self.vcp.projects[name]
        project.purge()

        self.vcp.save_config()

    @confirm()
    @confirm('Really?')
    def purge_all(self, iamsure):
        for name, project in self.vcp.projects.items():
            project.purge()

        self.vcp.save_config()


class PythonVenvCommand(object):
    def __init__(self, vcp):
        self.vcp = vcp

    def path(self, value):
        self.vcp.python_venv['path'] = value
        self.vcp.save_config()
        logger.info("Python virtual environment storage path has been saved")

    def interpreter(self, value):
        self.vcp.python_venv['interpreter'] = value
        self.vcp.save_config()
        logger.info("Python virtual environment interpreter has been saved")

class NPMConfigCommand(object):
    def __init__(self, vcp):
        self.vcp = vcp

    def set(self, name, value):
        self.vcp.npm_config[name] = value
        self.vcp.save_config()
        logger.info("Npm config saved")

    def unset(self, name):
        del self.vcp.npm_config[name]
        self.vcp.save_config()
        logger.info("Npm config saved")

    def list(self):
        if not len(self.vcp.npm_config):
            logger.info("Empty")

        table = PrettyTable(["Name", "Value"])
        for name in sorted(self.vcp.npm_config.keys()):
            table.add_row([name, self.vcp.npm_config[name]])
        logger.info("NPM config:\n{}".format(table))

class RepositoryCommand(object):
    def __init__(self, vcp):
        self.vcp = vcp

    def cmd(self, name, command):
        logger.info(self.vcp.repositories[name].cmd(command))

    def show_path(self, name):
        print(self.vcp.repositories[name].path)

    def list(self, format):
        # TODO: refactor this output format to sg generic, which appliable to the whole vcp
        if format == 'table':
            table = PrettyTable(["Type", "Name", "Path"])
            table.align = 'l'
            for repo_name in sorted(self.vcp.repositories):
                repo = self.vcp.repositories[repo_name]
                table.add_row([repo.type, repo.name, repo.path])
            logger.info("Known repositories:\n{}".format(table))
        else:
            # logger prints color codes, but this format use for bash tab completion
            print('\n'.join(sorted(self.vcp.repositories.keys())))

    def remove(self, name):
        del self.vcp.repositories[name]
        logger.info("Repository '{}' removed".format(name))
        self.vcp.save_config()

    @confirm()
    def clear(self, iamsure):
        self.vcp.repositories = {}
        self.vcp.save_config()
        logger.info("Repositories has been removed.")

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

class PackageCommand(object):

    def __init__(self, vcp):
        self.vcp = vcp

    def init(self, language):
        package_handler = self.vcp.package_factory.create(language)
        package_handler.init()

    def install_requirements(self, language):
        if language is None:
            for handler in self.vcp.package_factory.create_all():
                handler.install_requirements()
        else:
            package_handler = self.vcp.package_factory.create(language)
            package_handler.install_requirements()
