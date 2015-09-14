
import subprocess
from .repository import Repository

class GitRepository(Repository):
    type = 'git'

    def status(self):
        return self.cmd("git status")

    def get_dirty_files(self):
        content = self.cmd("git status --short")
        return content.split("\n")[:-1]

    def get_untracked_files(self):
        content = self.cmd("git ls-files --others --exclude-standard")
        return content.split("\n")[:-1]