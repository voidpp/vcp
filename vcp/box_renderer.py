
from colors import Colors

from voidpp_tools.terminal import get_size

class BoxRenderer(object):
    def __init__(self, config):
        self.width = config['width']
        self.decor = config['decorator']
        if self.width == -1:
            self.width = get_size()['cols']

    def render(self, box):
        padding = 10

        res  = Colors.yellow + self.decor * padding
        res += Colors.green + " %s " % box.caption
        res += Colors.yellow + self.decor * (self.width - len(box.caption) - 2 - padding)
        res += Colors.default + "\n" + box.content

        return res
