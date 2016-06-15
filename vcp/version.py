
import pkg_resources

def get_installed_version():
    return pkg_resources.get_distribution("vcp").version

def get_signo():
    return "vcp (v{})".format(get_installed_version())
