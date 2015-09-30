
import subprocess
from .repository import Repository

class GitRepository(Repository):
    type = 'git'

    def pushables(self, remote):
        return self.list_cmd("git --no-pager log --oneline %s..HEAD" % remote)

    def get_new_commits(self):
        return self.list_cmd("git --no-pager log --oneline HEAD..origin/master")

    def fetch(self):
        return self.cmd("git fetch")

    def status(self):
        return self.cmd("git status")

    def get_dirty_files(self):
        return self.list_cmd("git status --short")

    def get_untracked_files(self):
        return self.list_cmd("git ls-files --others --exclude-standard")
