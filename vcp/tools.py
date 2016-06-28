
from datetime import datetime
import logging
from functools import wraps
from subprocess import Popen, CalledProcessError, PIPE
import yaml

from .colors import Colors

class ColoredFormatter(logging.Formatter):

    # TODO: debug_mode to ctor?

    def __init__(self, debug):
        super(ColoredFormatter, self).__init__()
        self.debug = debug

    def format(self, record):
        colors = {
            logging.ERROR: Colors.red,
            logging.WARNING: Colors.yellow,
            logging.INFO: Colors.default,
            logging.DEBUG: Colors.cyan
        }

        if self.debug:
            msg = '%s - %s:%s: ' % (datetime.now(), record.name, record.lineno)
            msg += Colors.default + record.getMessage()
        else:
            msg = record.getMessage()

        msg = colors.get(record.levelno, Colors.default) + msg + Colors.default

        if record.exc_info:
            msg += '\n' + self.formatException(record.exc_info)

        return msg

def confirm_prompt(msg = "Are you sure?", help = "(ok: enter, cancel: ctrl+c)"):
    try:
        raw_input("{} {} ".format(msg, help))
        return True
    except KeyboardInterrupt:
        # for new line
        print('')
        return False

def get_func_defaults(func):
    diff = len(func.func_code.co_varnames) - len(func.func_defaults)
    return {func.func_code.co_varnames[diff+idx]: val for idx, val in enumerate(func.func_defaults)}

def confirm(msg = get_func_defaults(confirm_prompt)['msg'], help = get_func_defaults(confirm_prompt)['help']):

    def decor(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            if not kwargs.get('iamsure', False) and not confirm_prompt(msg, help):
                return
            func(*args, **kwargs)

        return wrapper

    return decor

def yaml_add_object_hook_pairs(type_):
    _mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG

    def dict_representer(dumper, data):
        return dumper.represent_dict(data.iteritems())

    def dict_constructor(loader, node):
        return type_(loader.construct_pairs(node))

    yaml.add_representer(type_, dict_representer)
    yaml.add_constructor(_mapping_tag, dict_constructor)

def check_call(command, **kwargs):
    p = Popen(command, stderr = PIPE, stdout = PIPE, **kwargs)
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        raise CalledProcessError(p.returncode, command, stderr)

def define_singleton(carrier, name, cls, cls_args = {}):
    """Creates a property with the given name, but the cls will created only with the first call

    Args:
        carrier: an instance of the class where want to reach the cls instance
        name (str): the variable name of the cls instance
        cls (type): the singleton object type
        cls_args (dict): optional dict for createing cls

    """
    instance_name = "__{}".format(name)
    setattr(carrier, instance_name, None)

    def getter(self):
        instance = getattr(carrier, instance_name)

        if instance is None:
            instance = cls(**cls_args)
            setattr(carrier, instance_name, instance)

        return instance

    setattr(type(carrier), name, property(getter))
