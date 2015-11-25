
from .box import Box

class RepositoryCommandResultBox(Box):
    def __init__(self, repository, content):
        self.repository = repository
        caption = '%(name)s: %(path)s' % repository.__dict__()
        super(RepositoryCommandResultBox, self).__init__(caption, content)
