

class Config(object):
    """
    A Config class, shows options for server, client
    or non-interactive taskmaster
    """
    def __init__(self):
        """Return Config object with empty dict of options"""
        self.options = dict()

    def set_options(self, opt):
        """Set dict of options"""
        self.options = opt

    def get_options(self):
        """Get options from object"""
        return self.options

    def add_option(self, option, value):
        """Adding new option with value to Config object"""
        self.options[str(option)] = value

    def remove_option(self, option):
        """Removing option from Config object"""
        self.options.pop(str(option), None)
