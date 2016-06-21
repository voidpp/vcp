
class ProjectException(Exception):
    pass

class RepositoryException(Exception):
    pass

class RepositoryCommandException(RepositoryException):
    def __init__(self, returncode, command, output):
        msg = "Error when executing '{}'. Return code: {}, output: {}".format(command, returncode, output)
        super(RepositoryException, self).__init__(msg)
        self.returncode = returncode
        self.command = command
        self.output = output

class SystemPackageManagerHandlerException(Exception):
    pass
