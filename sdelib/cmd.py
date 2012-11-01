import commons

class BaseCommand(object):
    cmd_name = None
    conf_syntax = ''
    conf_help = ''

    def __init__(self, config, args):
        self.config = config
        self.args = args

    def configure(self):
        pass

    def parse_args(self):
        return self.config.parse_args(self)

    def process_args(self):
        return True

    def handle(self):
        raise commons.UsageError('You can not use base class directly.')
