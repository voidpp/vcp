
class Storage(dict):

    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value

    def __hasattr__(self, key):
        return key in self

class CLIArgumentsTreeParser(object):

    def __init__(self, config, root_name, parser):
        self.parser = parser
        self.config = config
        self.root_name = root_name

    def __build(self, parser, node, node_name):
        subparsers = parser.add_subparsers(dest = node_name)

        for item in node:
            subparser = subparsers.add_parser(item['name'], **item['desc'])

            if 'arguments' in item:
                for arg in item['arguments']:
                    name = arg['arg_name']
                    del arg['arg_name']
                    if isinstance(name, list):
                        subparser.add_argument(*name, **arg)
                    else:
                        subparser.add_argument(name, **arg)

            if 'subcommands' in item:
                self.__build(subparser, item['subcommands'], item['name'])

    def build(self):
        self.__build(self.parser, self.config, self.root_name)

    def parse(self):
        self.raw_data = vars(self.parser.parse_args())

        self.data = Storage()

        self.structuring(self.root_name, self.data)

        return self.data

    def structuring(self, name, result, nodes = []):
        if name in self.raw_data:
            nodes.append(name)
            result.name = name
            if len(self.raw_data) > len(nodes):
                result.sub = Storage()
                self.structuring(self.raw_data[name], result.sub, nodes)
            else:
                result.sub = Storage(name = self.raw_data[name])
        else:
            result.name = name
            result.args = Storage()
            for dname in self.raw_data:
                if dname not in nodes:
                    result.args[dname] = self.raw_data[dname]
