import logging
from .repository import Repository, register_type

logger = logging.getLogger(__name__)

# TODO: refactor this to use GitPython
@register_type('git')
class GitRepository(Repository):

    def init(self, url, ref):
        logger.info("Cloning repository '{}'".format(url))
        res = self.cmd("git clone {} .".format(url))
        res += self.cmd("git checkout {}".format(ref))
        return res

    def __get_current_remote(self):
        return self.cmd("git remote").strip()

    def __get_current_full_branch_name(self):
        remote = self.__get_current_remote()
        branch = self.cmd("git rev-parse --abbrev-ref HEAD").strip()
        return "{}/{}".format(remote, branch)

    def diff(self):
        return self.cmd("git --no-pager diff")

    def pushables(self, remote):
        if remote is None:
            remote = self.__get_current_full_branch_name()
        return self.list_cmd("git --no-pager log --oneline %s..HEAD" % remote)

    def get_commits_from_last_tag(self):
        tag = self.cmd("git describe --abbrev=0 --tags").strip()
        return self.list_cmd("git --no-pager log --oneline {}..HEAD".format(tag))

    def get_new_commits(self):
        return self.list_cmd("git --no-pager log --oneline HEAD..{}".format(self.__get_current_full_branch_name()))

    def update(self):
        logger.info("Pull repository and rebasing...")
        return self.cmd("git pull --rebase")

    def fetch(self):
        return self.cmd("git fetch")

    def status(self):
        return self.cmd("git status")

    def reset(self):
        return self.cmd("git reset --hard ".format(self.__get_current_full_branch_name()))

    def get_own_commits_since(self, since_str):
        user = self.cmd("git config --get user.name").strip()
        return self.cmd("git --no-pager log --oneline --author='{}' --since='{}'".format(user, since_str))

    def get_dirty_files(self):
        files = []
        for file in self.list_cmd("git status --short"):
            if file.find('?') == -1:
                files.append(file)
        return files

    def get_untracked_files(self):
        return self.list_cmd("git ls-files --others --exclude-standard")

    def set_ref(self, ref):
        logger.debug("Set ref {} for repo {}".format(ref, self.name))
        return self.cmd("git checkout {}".format(ref))
