import os
import shutil
import logging
from voidpp_tools.terminal import get_size
from collections import OrderedDict
import re
from datetime import timedelta, datetime

from .repository_command_result_box import RepositoryCommandResultBox
from .exceptions import ProjectException, RepositoryCommandException
from .project_languages import LanguageFactory

logger = logging.getLogger(__name__)

class TopologicalSorter(object):
    """
    Implements Tarjan's algorithm.
    """
    def __init__(self, nodes):
        self.nodes = nodes
        self.marks = {n: None for n in self.nodes}
        self.result = []

    def get_mark(self, node):
        return self.marks[node.name]

    def has_temp_mark(self, node):
        return self.get_mark(node) == 'temp'

    def has_permanent_mark(self, node):
        return self.get_mark(node) == 'permanent'

    def sort(self):
        while True:
            has_unmarked = False
            for name, node in self.nodes.items():
                if not self.has_permanent_mark(node):
                    has_unmarked = True
                    self.__visit(node)

            if not has_unmarked:
                return self.result

    def __visit(self, node):
        if self.has_temp_mark(node):
            return

        if not self.has_permanent_mark(node):
            self.marks[node.name] = 'temp'
            for dep in node.get_dependent_projects().values():
                self.__visit(dep)
            self.marks[node.name] = 'permanent'
            self.result.insert(0, node)

class Project(object):

    def __init__(self, name, vcp, data = None):
        self.name = name
        self.description = None
        self.languages = []
        self.repo = dict(
            url = None,
            type = None,
        )
        self.dependencies = {}
        self.system_dependencies = {}
        self.vcp = vcp

        if data:
            self.data = data

    @property
    def last_status(self):
        for lang in self.languages:
            if not lang.env.last_status:
                return False
        return True

    @property
    def repositories(self):
        projects = self.get_dependent_projects().values() + [self]
        return [p.name for p in projects]

    @property
    def path(self):
        try:
            return self.vcp.repositories[self.name].path
        except KeyError:
            return None

    @property
    def initialized(self):
        return self.name in self.vcp.repositories

    @property
    def data(self):
        return OrderedDict([
            ('description', self.description),
            ('dependencies', self.dependencies),
            ('repo', self.repo),
            ('languages', [l.name for l in self.languages]),
            ('system_dependencies', self.system_dependencies),
        ])

    @data.setter
    def data(self, value):
        self.description = value['description']
        self.repo = value['repo']
        self.dependencies = value['dependencies']
        self.system_dependencies = value['system_dependencies']
        self.languages = self.vcp.language_factory.create(self, value['languages'])

    def set_dependencies_state(self):
        for name in self.get_dependent_projects(recursive = False):
            ref = self.dependencies[name]
            try:
                self.vcp.repositories[name].set_ref(ref)
                logger.info("Set ref '%s' for '%s'", ref, name)
            except RepositoryCommandException as e:
                logger.error(e.output)

    def search_for_ref_in_deps(self, project_name, projects):
        ref = None
        refprj = None
        for prj in projects:
            depref = prj.dependencies.get(project_name)
            if depref is None:
                continue
            if ref is not None and ref != depref:
                raise Exception("Found multiple refs for dep '{}', {}:{} and {}:{} ".format(project_name, prj.name, depref, refprj, ref))
            ref = depref
            refprj = prj.name

        if ref is None:
            raise Exception("Cannot find ref for '{}' but it's impossible!".format(project_name))

        return ref

    def init(self, base_path, status, force = False, install_deps = True, init_languages = True, ref = 'master'):

        repo_exists = self.name in self.vcp.repositories

        logger.debug("Start project init: '%s', force = %s, install_deps = %s, init_languages = %s", self.name, force, install_deps, init_languages)

        if repo_exists and not force:
            logger.debug("Project '%s' has been initialized already, skipping...", self.name)
            return True

        repo_dir = os.path.join(base_path, self.name)

        if install_deps:
            projects = self.get_sorted_dependencies()

            logger.info("Dependencies of %s: %s", self.name, [p.name for p in projects])

            for project in reversed(projects):
                try:
                    ref = self.dependencies[project.name]
                except KeyError as e:
                    ref = self.search_for_ref_in_deps(project.name, projects)
                if not project.init(base_path, status, force, install_deps = False, init_languages = init_languages, ref = ref):
                    return False

        if not repo_exists or init_languages:
            tw = get_size()['cols']
            label = "< Initializie {} >".format(self.name)
            pre_len = 10
            logger.info('\n' + '-' * pre_len + label + '-' * (tw - pre_len - len(label)))
            logger.info("URL: '{}', path: '{}'".format(self.repo['url'], repo_dir))

        status[self.name] = True

        try:
            if self.vcp.system_package_manager_handler:
                packages = self.vcp.system_package_manager_handler.get_not_installed_packages(self)
                if len(packages):
                    logger.error("Need to install these system packages: %s", ', '.join(packages))
                    return False

            # create repo config
            repo = self.vcp.repo_factory.create(repo_dir, self.repo['type'], self.name)

            if repo_exists:
                repo.update()
            else:
                # create folder
                os.mkdir(repo_dir)

                repo.init(self.repo['url'], ref)
                self.vcp.repositories[self.name] = repo

            # initialize language specific stuffs
            if not repo_exists or init_languages:
                for lang in self.languages:
                    lang.init()
                    if not lang.env.get_status():
                        status[self.name] = False

            return True
        except (Exception, KeyboardInterrupt) as e:
            logger.exception("Error during initialize '{}'. Reverting all the work. Traceback:".format(self.name))
            self.purge()
            return False

    def purge(self):
        path = self.path

        logger.info("Purge project '{}'".format(self.name))

        for lang in self.languages:
            lang.purge()

        if self.name in self.vcp.repositories:
            del self.vcp.repositories[self.name]
            logger.debug("Delete repository config")

        if path and os.path.isdir(path):
            shutil.rmtree(path)
            logger.debug("Delete repository directory '%s'", path)

    def install_to(self, project, env):
        for lang in self.languages:
            if type(env) == type(lang.env):
                lang.install_to(project, env)

    def get_sorted_dependencies(self, remove_indirect_deps = False):
        topo = TopologicalSorter(self.get_dependent_projects())

        all_dep = topo.sort()

        if remove_indirect_deps:
            for prj in all_dep:
                if prj.name not in self.dependencies:
                    all_dep.remove(prj)

        return all_dep

    def get_dependent_projects(self, recursive = True):
        """Get the dependencies of the Project

        Args:
            recursive (bool): add the dependant project's dependencies too

        Returns:
            dict of project name and project instances
        """
        projects = {}
        for name, ref in self.dependencies.items():
            try:
                prj = self.vcp.projects[name]
            except KeyError:
                logger.error("Unknown project '%s' in project '%s' dependencies!", name, self.name)
                continue
            projects[name] = prj
            if recursive:
                projects.update(prj.get_dependent_projects())
        return projects

    def news(self, fromcache):
        for name in self.repositories:
            repo = self.vcp.repositories[name]
            if not fromcache:
                repo.fetch()
            commits = repo.get_new_commits()
            if len(commits):
                yield RepositoryCommandResultBox(repo, "\n".join(commits))

    def unreleased(self):
        for name in self.repositories:
            repo = self.vcp.repositories[name]
            commits = repo.get_commits_from_last_tag()
            if len(commits):
                yield RepositoryCommandResultBox(repo, "\n".join(commits))

    def diff(self):
        for name in self.repositories:
            repo = self.vcp.repositories[name]
            diff = repo.diff()
            if len(diff):
                yield RepositoryCommandResultBox(repo, diff)

    def pushables(self, remote):
        for name in self.repositories:
            repo = self.vcp.repositories[name]
            commits = repo.pushables(remote)
            if len(commits):
                yield RepositoryCommandResultBox(repo, "\n".join(commits))

    def untracked(self):
        for name in self.repositories:
            repo = self.vcp.repositories[name]
            files = repo.get_untracked_files()
            if len(files):
                yield RepositoryCommandResultBox(repo, "\n".join(files))

    def dirty(self):
        for name in self.repositories:
            repo = self.vcp.repositories[name]
            files = repo.get_dirty_files()
            if len(files):
                yield RepositoryCommandResultBox(repo, "\n".join(files))

    def fetch(self):
        for name in self.repositories:
            repo = self.vcp.repositories[name]
            res = repo.fetch()
            if len(res):
                yield RepositoryCommandResultBox(repo, res)

    def standup(self, length):
        lengths = OrderedDict([
            ('w', 60 * 24 * 7),
            ('d', 60 * 24),
            ('h', 60),
            ('m', 1),
        ])

        decode_pattern = re.compile(''.join(['([\d]+{})?'.format(k) for k in lengths]))
        res = decode_pattern.match(length)
        if not res:
            raise Exception('go back')

        length_items = list(lengths)

        value = 0
        for idx, grp in enumerate(res.groups()):
            if grp is None:
                continue
            abbr = length_items[idx]
            val = int(grp[:-1])
            value += val * lengths[abbr]

        time_len = timedelta(minutes = value)

        since = datetime.now() - time_len

        for name in self.repositories:
            repo = self.vcp.repositories[name]
            res = repo.get_own_commits_since(since.isoformat())
            if len(res):
                yield RepositoryCommandResultBox(repo, res)

    def status(self):
        for name in self.repositories:
            repo = self.vcp.repositories[name]
            yield RepositoryCommandResultBox(repo, repo.status())

    def reset(self):
        for name in self.repositories:
            repo = self.vcp.repositories[name]
            yield RepositoryCommandResultBox(repo, repo.reset())

    def cmd(self, command):
        for repo_name in self.repositories:
            repo = self.vcp.repositories[repo_name]
            res = repo.cmd(command)
            if len(res):
                yield RepositoryCommandResultBox(repo, res)

    def __repr__(self):
        return "<Project: %s>" % self.__dict__
