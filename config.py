import yaml
import signal
import os


def fill_param(x, v, d):
    if isinstance(d, dict) and x not in d.keys():
        d[x] = v
        return d
    else:
        raise ValueError


class Config(object):
    """
    A Config class, shows options for server, client
    or non-interactive taskmaster
    """
    cmd_options_lst = ['cmd', 'umask', 'workingdir', 'priority', 'autostart', 'startsecs', 'autorestart',
                       'exitcodes', 'startretries', 'starttime', 'stopsignal', 'stopwaitsecs', 'user', 'stdout',
                       'stderr', 'env']
    cmd_necessary_opt_lst = ['cmd', 'workingdir', 'startsecs', 'exitcodes', 'starttime', 'startretries',
                             'stopsignal', 'user']

    def __init__(self, conf_name):
        """Return Config object with given dict of options or {}"""
        options = self.read_from_config_file(conf_name)
        self.check_kwarg(options)
        # For each process config fill params and add Process conf to list of confs
        #self.options = self.fullfill_kwarg(options)

    def set_options(self, opt):
        """Set dict of options"""
        self.options = opt

    def get_options(self):
        """Get options from object"""
        return self.options

    def read_from_config_file(self, filename):
        """
        Parse config for taskmaster daemon

        Returns:
            dict with options of config
        """
        with open(filename, 'r') as ymlfile:
            try:
                self.options = yaml.load(ymlfile)
            except yaml.YAMLError as exc:
                raise exc

    def check_kwarg(self, kwarg):
        for opt in kwarg.keys():
            if opt not in self.cmd_options_lst:
                raise ValueError('option "%s" is not found in config' % opt)
        if not set(self.cmd_necessary_opt_lst).issubset(set(kwarg.keys())):
            raise ValueError('not filled all necessary parameters!')
        for k, v in kwarg.items():
            if k == 'cmd' or k == 'umask' or k == 'workingdir' or k == 'exitcodes' or k == 'stopsignal' or k == 'user':
                if not isinstance(k, str):
                    raise ValueError('bad presentation of "%s"' % k)
            if k == 'umask' and not k.isnumeric():
                raise ValueError('bad value for "%s"' % k)
            if k == 'numprocs' or k == 'priority' or k == 'startsecs' or k == 'startretries' or k == 'stopwaitsecs':
                if not isinstance(k, int):
                    raise ValueError('bad presentation of "%s"' % k)
            if k == 'numprocs' or k == 'startsecs' or k == 'startretries' or k == 'stopwaitsecs' and k < 0 or k > 1000:
                raise ValueError('bad value for "%s"' % k)
            if k == 'exitcodes':
                lst = [int(i) for i in v.split(',')]
                if False in list(map(lambda x: False if x not in range(256) else True, lst)):
                    raise ValueError('bad value for "%s"' % k)
            if k == 'stopsignal':
                dict_of_signals = dict((kr, v) for v, kr in reversed(sorted(signal.__dict__.items())) if v.startswith('SIG') and not v.startswith('SIG_'))
                if v not in dict_of_signals.values():
                    raise ValueError('bad value %s for "%s"' % (v, k))

    def fullfill_kwarg(self, kwarg):
        new_kwarg = kwarg.copy()
        try:
            new_kwarg = fill_param('priority', 999, new_kwarg)
            new_kwarg = fill_param('autostart', True, new_kwarg)
            new_kwarg = fill_param('stopwaitsecs', 10, new_kwarg)
            new_kwarg = fill_param('umask', '022', new_kwarg)
            new_kwarg = fill_param('stdout', 1, new_kwarg)
            new_kwarg = fill_param('stderr', 2, new_kwarg)
            new_kwarg = fill_param('env', os.environ, new_kwarg)
            return new_kwarg
        except ValueError as e:
            raise ValueError("Can't initialize process with default values. Exiting")

