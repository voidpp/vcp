
from .git_repository import GitRepository
from .repository_command_result_box import RepositoryCommandResultBox
from .exceptions import ProjectException

class Project(object):
    def __init__(self, name, description = '', repositories = []):
        self.name = name
        self.description = description
        self.repositories = repositories
        self.db = None

    def news(self, fromcache):
        for name in self.repositories:
            repo = self.db.repositories[name]
            if not fromcache:
                repo.fetch()
            commits = repo.get_new_commits()
            if len(commits):
                yield RepositoryCommandResultBox(repo, "\n".join(commits))

    def diff(self):
        for name in self.repositories:
            repo = self.db.repositories[name]
            diff = repo.diff()
            if len(diff):
                yield RepositoryCommandResultBox(repo, diff)

    def pushables(self, remote):
        for name in self.repositories:
            repo = self.db.repositories[name]
            commits = repo.pushables(remote)
            if len(commits):
                yield RepositoryCommandResultBox(repo, "\n".join(commits))

    def untracked(self):
        for name in self.repositories:
            repo = self.db.repositories[name]
            files = repo.get_untracked_files()
            if len(files):
                yield RepositoryCommandResultBox(repo, "\n".join(files))

    def dirty(self):
        for name in self.repositories:
            repo = self.db.repositories[name]
            files = repo.get_dirty_files()
            if len(files):
                yield RepositoryCommandResultBox(repo, "\n".join(files))

    def fetch(self):
        for name in self.repositories:
            repo = self.db.repositories[name]
            res = repo.fetch()
            if len(res):
                yield RepositoryCommandResultBox(repo, res)

    def status(self):
        for name in self.repositories:
            repo = self.db.repositories[name]
            yield RepositoryCommandResultBox(repo, repo.status())

    def cmd(self, command):
        for repo_name in self.repositories:
            repo = self.db.repositories[repo_name]
            res = repo.cmd(command)
            if len(res):
                yield RepositoryCommandResultBox(repo, res)

    def __repr__(self):
        return "<Project: %s>" % self.__dict__()

    def __dict__(self):
        return dict(
            name = self.name,
            repositories = sorted(self.repositories),
            description = self.description,
        )
