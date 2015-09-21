
from .git_repository import GitRepository
from .box import Box
from .exceptions import ProjectException

class Project(object):
    def __init__(self, name, description = '', repositories = []):
        self.name = name
        self.description = description
        self.repositories = repositories
        self.db = None

    def pushables(self, remote):
        for name in self.repositories:
            repo = self.db.repositories[name]
            commits = repo.pushables(remote)
            if len(commits):
                yield Box(repo.name, "\n".join(commits))

    def untracked(self):
        for name in self.repositories:
            repo = self.db.repositories[name]
            files = repo.get_untracked_files()
            if len(files):
                yield Box(repo.name, "\n".join(files))

    def dirty(self):
        for name in self.repositories:
            repo = self.db.repositories[name]
            files = repo.get_dirty_files()
            if len(files):
                yield Box(repo.name, "\n".join(files))

    def fetch(self):
        for name in self.repositories:
            repo = self.db.repositories[name]
            res = repo.fetch()
            if len(res):
                yield Box(repo.name, res)

    def status(self):
        for name in self.repositories:
            repo = self.db.repositories[name]
            yield Box(repo.name, repo.status())

    def cmd(self, command):
        for repo_name in self.repositories:
            repo = self.db.repositories[repo_name]
            res = repo.cmd(command)
            if len(res):
                yield Box(repo.name, res)

    def __repr__(self):
        return "<Project: %s>" % self.__dict__()

    def __dict__(self):
        return dict(
            name = self.name,
            repositories = sorted(self.repositories),
            description = self.description,
        )
