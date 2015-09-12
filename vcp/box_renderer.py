
from colors import Colors

class BoxRenderer(object):
    def __init__(self, width = 100, decor = "-"):
        self.width = width
        self.decor = decor

    def render(self, box):
        padding = 10

        res  = Colors.yellow + self.decor * padding
        res += Colors.green + " %s " % box.caption
        res += Colors.yellow + self.decor * (self.width - len(box.caption) - 2 - padding)
        res += Colors.default + "\n" + box.content

        return res
