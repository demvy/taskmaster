import yaml
import signal
import os

cmd_options_lst = ['cmd', 'umask', 'workingdir', 'priority', 'autostart', 'startsecs', 'autorestart',
                   'exitcodes', 'startretries', 'starttime', 'stopsignal', 'stopwaitsecs', 'user', 'stdout',
                   'stderr', 'env', 'numprocs']
cmd_necessary_opt_lst = ['cmd', 'startsecs', 'exitcodes', 'startretries',
                         'stopsignal', 'numprocs', 'umask', 'autostart', 'autorestart',
                         'stopwaitsecs', 'stdout', 'stderr', 'env', 'workingdir']


class Config(object):
    """
    A Config class, shows options for server, client
    or non-interactive taskmaster
    """

    def __init__(self, conf_name):
        """Return Config object with given dict of options or {}"""
        options = dict(self.read_from_config_file(conf_name))
        user_ps = dict((i, options[i]) for i in options if i!='taskmasterd')
        for d in user_ps.keys():
            self.check_kwarg(user_ps.get(d))
        self.check_daemon_conf(options.get('taskmasterd', {}))
        taskmasterd_opt = options.get('taskmasterd', {})
        self.logfile = taskmasterd_opt.get('logfile', 'taskmasterd.log')
        self.daemon = taskmasterd_opt.get('daemon', False)
        self.jobs_amount = len(user_ps)
        self.lst_proc_conf = []
        self.create_proc_confs(user_ps)

    def create_proc_confs(self, options):
        # For each process config fill params and add Process conf to list of confs
        for k, v in options.items():
            conf = dict()
            for name, value in v.items():
                setattr(conf, name, value)
            setattr(conf, 'priority', conf.get('priority', 999))
            setattr(conf, 'autostart', conf.get('autostart', True))
            setattr(conf, 'stopwaitsecs', conf.get('stopwaitsecs', 10))
            setattr(conf, 'umask', conf.get('umask', '022'))
            setattr(conf, 'stdout', conf.get('stdout', 1))
            setattr(conf, 'stderr', conf.get('stderr', 2))
            setattr(conf, 'env', conf.get('env', os.environ))
            setattr(conf, 'logfile', self.logfile)
            proc_conf = ProcessConfig(conf, k)
            self.lst_proc_conf.append(proc_conf)

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
                options = yaml.load(ymlfile)
                return options
            except yaml.YAMLError as exc:
                raise exc

    def check_daemon_conf(self, kwarg):
        if len(kwarg) > 2:
            raise ValueError('too big config for taskmasterd. 2 params allowed only')
        conf_len = len(kwarg)
        if conf_len == 1 and 'logfile' not in kwarg.keys() or 'daemon' not in kwarg.keys():
            raise ValueError('not known parameter "%s"' % kwarg.keys()[0])
        elif conf_len == 2 and 'logfile' not in kwarg.keys() and 'daemon' not in kwarg.keys():
            raise ValueError('bad options in taskmasterd config')

    def check_kwarg(self, kwarg):
        print(kwarg)
        for opt in kwarg.keys():
            if opt not in cmd_options_lst:
                raise ValueError('option "%s" is not found in config' % opt)
        if not set(cmd_necessary_opt_lst).issubset(set(kwarg.keys())):
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

    def get_proc_conf_by_name(self, name):
        """
        Get ProcessConfig by name from self.lst_proc_conf
        """
        for proc in self.lst_proc_conf:
            if proc.get(name):
                return proc
        return None

    def get_lst_proc_conf(self):
        return self.lst_proc_conf

    def diff_to_active(self, new=None):
        """
        Get lists with added, changed and removed processes to start/restart/kill after SIGHUP
        Says state of Taskmaster conf (changed or not)
        :param new: new config to compare
        :return: tuple with changed Taskmaster conf, added, changed and removed process_confs
        """
        if not new:
            return False, [], [], []

        added, changed, removed = [], [], []
        for proc_conf in new.get_lst_proc_conf():
            proc = self.get_proc_conf_by_name(proc_conf.get_name())
            if proc:
                if not proc.equals(proc_conf):
                    changed.append(proc_conf)
            else:
                added.append(proc_conf)
        for proc_conf in self.lst_proc_conf:
            proc = new.get_proc_conf_by_name(proc_conf.get_name())
            if not proc:
                removed.append(proc_conf)
        if self.logfile == getattr(new, 'logfile') and self.daemon == getattr(new, 'daemon'):
            return False, added, changed, removed
        else:
            return True, added, changed, removed


class ProcessConfig(object):
    def __init__(self, config, proc_name):
        self.proc_name = proc_name
        for name in cmd_options_lst:
            setattr(self, name, config[name])

    def get(self, name):
        if self.proc_name == name:
            return self

    def get_name(self):
        return self.proc_name

    def __repr__(self):
        return self.proc_name
