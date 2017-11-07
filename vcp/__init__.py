import os
import pkg_resources
from functools import partial
from logging import getLogger
import collections

from .project import Project
from .box_renderer import BoxRenderer
from .repository import RepositoryFactory
from .repositories import GitRepository
from .project_handler_base import ProjectHandlerFactory
from .commands import RepositoryCommand, ProjectCommand, NPMConfigCommand, PackageCommand, PythonVenvCommand
from .project_languages import LanguageFactory
from .system_package_manager_handlers import SystemPackageManagerHandlerFactory
from .tools import yaml_add_object_hook_pairs, define_singleton
from .exceptions import SystemPackageManagerHandlerException
from .packages import PackageFactory

logger = getLogger(__name__)

CONFIG_FILE_NAME = '.vcp'

class _VCPConfigParser(object):
    def parse(self, config_data, vcp, defaults):
        for name, default in defaults.items():

            # TODO: recursive update in case of dict data
            node_value = config_data.get(name, default)

            func = 'process_%s' % name
            if not hasattr(self, func):
                if vcp.warnings['unknown_config_node']:
                    logger.warning("Unknown config node: '%s'" % name)
                continue

            attr = getattr(self, func)

            logger.debug("Process config node: '%s'" % name)
            attr(node_value, vcp)


    def process_repositories(self, config, vcp):
        vcp.repositories = {}
        for name in config:
            vcp.repositories[name] = vcp.repo_factory.create(**config[name])

    def process_default_project(self, config, vcp):
        vcp.default_project = config

    def process_output_format(self, config, vcp):
        vcp.output_format = config

    def process_warnings(self, config, vcp):
        vcp.warnings = config

    def process_projects_reference(self, config, vcp):
        vcp.projects_reference = config

        prj_ref_path = os.path.expanduser(config['path'])
        config['path'] = prj_ref_path
        if not os.path.isdir(prj_ref_path):
            os.mkdir(prj_ref_path)

        vcp.project_handler_factory = ProjectHandlerFactory()
        vcp.project_handler = vcp.project_handler_factory.create(config['uri'], prj_ref_path)

        if vcp.project_handler is None:
            return

        vcp.project_handler.config_init()

        projects = vcp.project_handler.load()
        vcp.projects = {name: Project(name, vcp, data) for name, data in projects.items()}

    def process_python_venv_dir(self, config, vcp):
        vcp.python_venv['path'] = config

    def process_python_venv(self, config, vcp):
        vcp.python_venv.update(config)
        path = os.path.normpath(os.path.expanduser(vcp.python_venv['path']))
        if not os.path.isdir(path):
            logger.warning("Python virtual env path does not exists! ({})".format(vcp.python_venv['path']))

    # backward compatibility parser for preserve old-style projects
    def process_projects(self, config, vcp):
        vcp.repo_groups = config

    def process_repo_groups(self, config, vcp):
        vcp.repo_groups = config

    def process_npm_config(self, config, vcp):
        vcp.npm_config = config

    def process_npm_usage_config(self, config, vcp):
        vcp.npm_usage_config = config

class VCP(object):
    """Config and cli handler class"""

    def __init__(self, config_loader, config_file_name = CONFIG_FILE_NAME):

        define_singleton(self, 'repo_factory', RepositoryFactory)
        define_singleton(self, 'language_factory', LanguageFactory)
        define_singleton(self, 'package_factory', PackageFactory)

        self.command_names = []
        self.projects = {}
        self.project_handler_factory = None
        self.project_handler = None
        self.python_venv = {}

        yaml_add_object_hook_pairs(collections.OrderedDict)

        self.warning_descriptors = dict(
            unknown_default_project = dict(
                default = True,
                name = "Unknown default project",
            ),
            unknown_config_node = dict(
                default = True,
                name = "Unknown config node"
            ),
        )

        config_defaults = dict(
            default_project = None,
            repositories = {},
            output_format = dict(
                header = dict(
                    show_repo_path = False,
                    width = 100,
                    decorator = '-',
                ),
            ),
            projects_reference = dict(
                uri = 'local://default',
                path = '~/.vcp_project_configs/',
            ),
            warnings = {name: d['default'] for name, d in self.warning_descriptors.items()},
            python_venv = dict(
                path = '~/.virtualenvs',
                interpreter = 'python2',
            ),
            repo_groups = {},
            # backward compatibility node for preserve old-style projects
            projects = {},
            npm_config = {},
            npm_usage_config = {},
        )

        self.load_configs(config_defaults, config_loader, config_file_name)

    @property
    def system_package_manager_handler(self):
        if not hasattr(self, '__system_package_manager_handler'):
            try:
                self.__system_package_manager_handler = SystemPackageManagerHandlerFactory().create()
            except SystemPackageManagerHandlerException as e:
                logger.error(e)
                self.__system_package_manager_handler = None
        return self.__system_package_manager_handler

    def load_configs(self, defaults, config_loader, config_file_name):
        self.config_loader = config_loader
        self.config = self.config_loader.load(config_file_name)
        logger.debug("Config loaded successfully from '%s'" % self.config_loader.filename)

        parser = _VCPConfigParser()
        parser.parse(self.config, self, defaults)

        self.box_renderer = BoxRenderer(self.output_format['header'])

        logger.debug("Config parsed. Projects: %d, repositories %d." % (len(self.projects), len(self.repositories)))

    def action_commands_lookup(self, project_related_commands):
        self.command_names = [command['name'] for command in project_related_commands]

    # common handler for all project related action commands
    def __getattr__(self, attr_name):
        if attr_name not in self.command_names:
            raise KeyError("Unknown project related command: '{}'".format(attr_name))

        def action(name, **kwargs):
            list = kwargs['list']
            del kwargs['list']
            project = self.projects[name]
            if list:
                logger.info(','.join([box.repository.name for box in getattr(project, attr_name)(**kwargs)]))
            else:
                for box in getattr(project, attr_name)(**kwargs):
                    box.reconfig(self.output_format['header'])
                    logger.info(self.box_renderer.render(box))

        return action

    def npmconfig(self):
        return NPMConfigCommand(self)

    def pyvenv(self):
        return PythonVenvCommand(self)

    def version(self):
        logger.info(pkg_resources.get_distribution("vcp").version)

    def warning(self, action, message):
        self.warnings[message] = True if action == 'enable' else False
        self.save_config()
        logger.info("Warning message {}d".format(action))

    def repository(self):
        return RepositoryCommand(self)

    def project(self):
        return ProjectCommand(self)

    def get_data(self):
        return dict(
            projects_reference = self.projects_reference,
            repositories = self.repositories,
            default_project = self.default_project,
            output_format = self.output_format,
            warnings = self.warnings,
            python_venv = self.python_venv,
            repo_groups = self.repo_groups,
            npm_config = self.npm_config,
            npm_usage_config = self.npm_usage_config,
        )

    def save_config(self):
        self.config_loader.save(self.get_data())
        logger.debug("VCP config saved to '%s'" % self.config_loader.filename)

    def save_project_config(self):
        if self.project_handler is not None:
            self.project_handler.save({name: project.data for name, project in self.projects.items()})

    def package(self):
        return PackageCommand(self)

    def get_cli_config(self, default_project):

        # initialize cli tree
        project_names = self.projects.keys()
        repository_names = self.repositories.keys()
        package_lang_names = self.package_factory.types.keys()

        # NOTE: project name parameter added later!
        project_action_commands = [
            dict(
                name = 'status',
                desc = dict(help = 'Project status'),
            ),
            dict(
                name = 'cmd',
                desc = dict(help = 'Execute a command on a project (all repos)'),
                arguments = [
                    dict(arg_name = 'command', help = 'command and params'),
                ]
            ),
            dict(
                name = 'untracked',
                desc = dict(help = 'Untracked files'),
            ),
            dict(
                name = 'dirty',
                desc = dict(help = 'Dirty files (list of untracked or modified files)'),
            ),
            dict(
                name = 'pushables',
                desc = dict(help = 'Show all unpushed local commits'),
                arguments = [
                    dict(arg_name = '--remote', help = 'remote name', default = None)
                ]
            ),
            dict(
                name = 'fetch',
                desc = dict(help = 'Fetch repositories'),
            ),
            dict(
                name = 'news',
                desc = dict(help = 'Project news'),
                arguments = [
                    dict(arg_name = ['--fromcache', '-c'], help = 'does not do fetch before the check', action = 'store_true'),
                ]
            ),
            dict(
                name = 'diff',
                desc = dict(help = 'Show diff in all repositories'),
            ),
            dict(
                name = 'reset',
                desc = dict(help = 'Delete all local commits. Warning: BIOHAZARD! Cannot be reverted if reflog is off!'),
            ),
            dict(
                name = 'unreleased',
                desc = dict(help = 'Show all unreleased commits'),
            ),
            dict(
                name = 'standup',
                desc = dict(help = 'List your commits from the last 24 hour'),
                arguments = [
                    dict(
                        arg_name = ['--length', '-l'],
                        help = 'duration length (examples: 24h, 1d, 26h, 1d1h) (m: mins, h: hours, d: days, w: weeks)',
                        type = str,
                        default = '24h',
                    ),
                ]
            ),
        ]

        manager_commands = [
            dict(
                name = 'project',
                desc = dict(help = 'Project manager commands'),
                subcommands = [
                    dict(
                        name = 'init',
                        desc = dict(help = "Initialize project. This command will clone all locally unknown repositories"),
                        arguments = [
                            dict(arg_name = 'name', help = 'project name', choices = project_names),
                            dict(arg_name = '--path', help = 'the base path of the repos (default: current)', default = os.getcwd()),
                            dict(arg_name = '--force', help = 'git pull --rebase and reinit lang pkg', action = 'store_true', default = False),
                        ]
                    ),
                    dict(
                        name = 'update',
                        desc = dict(help = "Update project. This command will clone all locally unknown repositories"),
                        arguments = [
                            dict(arg_name = 'name', help = 'project name', choices = project_names),
                            dict(arg_name = '--path', help = 'the base path of the repos (default: current)', default = os.getcwd()),
                        ]
                    ),
                    dict(
                        name = 'create',
                        desc = dict(help = 'Create project'),
                        arguments = [
                            dict(arg_name = 'name', help = 'project name'),
                            dict(arg_name = '--default', help = 'make this project default', action = 'store_true'),
                        ]
                    ),
                    dict(
                        name = 'edit',
                        desc = dict(help = 'Edit project file'),
                        arguments = [
                            dict(arg_name = 'name', help = 'project name', choices = project_names),
                            dict(arg_name = 'summary', help = 'the summary of the changes', nargs = '?', default = ''),
                        ]
                    ),
                    dict(
                        name = 'remove',
                        desc = dict(help = 'Remove project config'),
                        arguments = [
                            dict(arg_name = 'name', help = 'project name', choices = project_names),
                        ]
                    ),
                    dict(
                        name = 'show',
                        desc = dict(help = 'Show project'),
                        arguments = [
                            dict(arg_name = 'name', help = 'project name', choices = project_names),
                        ]
                    ),
                    dict(
                        name = 'list',
                        desc = dict(help = 'List of projects'),
                    ),
                    dict(
                        name = 'default',
                        desc = dict(help = 'Set project for default. If default project is specified, the \'project\' parameter in the generic commands is optional'),
                        arguments = [
                            dict(arg_name = 'name', help = 'project name', choices = project_names),
                        ]
                    ),
                    dict(
                        name = 'workon',
                        desc = dict(help = "Set project for default and set all the dependant project's ref according to this project config."),
                        arguments = [
                            dict(arg_name = 'name', help = 'project name', choices = project_names),
                        ]
                    ),
                    dict(
                        name = 'config',
                        desc = dict(help = "Project config commands"),
                        subcommands = [
                            dict(
                                name = 'uri',
                                desc = dict(help = "Set the projects config storage uri"),
                                arguments = [
                                    dict(arg_name = 'value', type = str),
                                ]
                            ),
                            dict(
                                name = 'path',
                                desc = dict(help = "Set the projects config storage path"),
                                arguments = [
                                    dict(arg_name = 'value', type = str),
                                ]
                            ),
                            dict(
                                name = 'update',
                                desc = dict(help = "Update the project config storage"),
                                arguments = []
                            ),
                        ]
                    ),
                    dict(
                        name = 'purge',
                        desc = dict(help = 'Remove all data about the project except the project config'),
                        arguments = [
                            dict(arg_name = 'name', help = 'project name', choices = project_names),
                            dict(arg_name = '--iamsure', help = 'confirmation', action = 'store_true'),
                        ],
                    ),
                    dict(
                        name = 'purge-all',
                        desc = dict(help = 'Remove all data about all the projects except the project configs'),
                        arguments = [
                            dict(arg_name = '--iamsure', help = 'confirmation', action = 'store_true'),
                        ],
                    ),
                ]
            ),
            dict(
                name = 'repository',
                desc = dict(help = 'Repository manager commands'),
                subcommands = [
                    dict(
                        name = 'create',
                        desc = dict(help = 'Create repository'),
                        arguments = [
                            dict(arg_name = 'path', help = 'Repository path'),
                            dict(arg_name = '--name', help = 'Repository name. Default: repo dir name', default = None),
                            dict(arg_name = '--type', help = 'Repository type', choices = ['git'], default = 'git'),
                            dict(arg_name = '--add-to', help = 'add to projects', choices = project_names, nargs = '*'),
                        ]
                    ),
                    dict(
                        name = 'cmd',
                        desc = dict(help = 'Execute a command on a repository'),
                        arguments = [
                            dict(arg_name = 'name', help = 'repository name', choices = repository_names),
                            dict(arg_name = 'command', help = 'command and params'),
                        ]
                    ),
                    dict(
                        name = 'remove',
                        desc = dict(help = 'Remove repository'),
                        arguments = [
                            dict(arg_name = 'name', help = 'repository name', choices = repository_names),
                        ]
                    ),
                    dict(
                        name = 'list',
                        desc = dict(help = 'List of repositories'),
                        arguments = [
                            dict(arg_name = '--format', help = 'Output format', choices = ['table', 'lines'], default = 'table'),
                        ]
                    ),
                    dict(
                        name = 'show_path',
                        desc = dict(help = 'Show path repository'),
                        arguments = [
                            dict(arg_name = 'name', help = 'repository name', choices = repository_names),
                        ],
                    ),
                    dict(
                        name = 'clear',
                        desc = dict(help = 'Remove all repository'),
                        arguments = [
                            dict(arg_name = '--iamsure', help = 'confirmation', action = 'store_true'),
                        ],
                    ),
                ]
            ),
            dict(
                name = 'version',
                desc = dict(help = 'Show VCP version'),
            ),
            dict(
                name = 'warning',
                desc = dict(help = 'Enable/disable VCP warning message'),
                arguments = [
                    dict(arg_name = 'action', help = 'action', choices = ['enable', 'disable']),
                    dict(arg_name = 'message', help = 'message', choices = self.warning_descriptors.keys()),
                ],
            ),
            dict(
                name = 'pyvenv',
                desc = dict(help = 'Set the python virtualenv stuffs'),
                subcommands = [
                    dict(
                        name = 'path',
                        desc = dict(help = "Set storage path"),
                        arguments = [
                            dict(arg_name = 'value', type = str),
                        ]
                    ),
                    dict(
                        name = 'interpreter',
                        desc = dict(help = "set interpreter"),
                        arguments = [
                            dict(arg_name = 'value', type = str),
                        ]
                    ),
                ]
            ),
            dict(
                name = 'npmconfig',
                desc = dict(help = 'Manage npm config (for npm related commands)'),
                subcommands = [
                    dict(
                        name = 'set',
                        desc = dict(help = 'Set config value'),
                        arguments = [
                            dict(arg_name = 'name', help = 'Repository path'),
                            dict(arg_name = 'value', help = 'Repository path'),
                        ]
                    ),
                    dict(
                        name = 'unset',
                        desc = dict(help = 'Delete config value'),
                        arguments = [
                            dict(arg_name = 'name', help = 'config name', choices = self.npm_config.keys()),
                        ]
                    ),
                    dict(
                        name = 'list',
                        desc = dict(help = 'Show all configured value'),
                    ),
                ]
            ),
            dict(
                name = 'package',
                desc = dict(help = 'Package managing'),
                subcommands = [
                    dict(
                        name = 'init',
                        desc = dict(help = 'Initialize package data'),
                        arguments = [
                            dict(arg_name = 'language', help = 'language', choices = package_lang_names),
                        ],
                    ),
                    dict(
                        name = 'install-requirements',
                        desc = dict(help = 'Install all the packages requirements'),
                        arguments = [
                            dict(arg_name = 'language', help = 'language', choices = package_lang_names, nargs = '?', default = None),
                        ],
                    ),
                ],
            )
        ]
        # add project name parameter for project_action_commands
        for command in project_action_commands:
            project_param = dict(arg_name = 'name', help = 'project name', choices = project_names)
            if default_project:
                project_param.update(nargs = '?', default = default_project)
            if 'arguments' not in command:
                command['arguments'] = []
            command['arguments'].insert(0, project_param)
            command['arguments'].append(dict(arg_name = '--list', help = 'Print only repo names', action = 'store_true'))

        self.action_commands_lookup(project_action_commands)

        return project_action_commands + manager_commands
