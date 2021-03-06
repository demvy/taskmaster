import yaml
import signal
import os
import shlex
import stat
import logging
import copy

from utils import get_signum

cmd_options_lst = ['cmd', 'umask', 'workingdir', 'priority', 'autostart', 'startsecs', 'autorestart',
                   'exitcodes', 'startretries', 'stopsignal', 'stopwaitsecs', 'user', 'stdout',
                   'stderr', 'env', 'numprocs']
cmd_necessary_opt_lst = ['cmd', 'startsecs', 'exitcodes', 'startretries',
                         'stopsignal', 'numprocs', 'umask', 'autostart', 'autorestart',
                         'stopwaitsecs', 'stdout', 'stderr', 'env', 'workingdir']
logger = logging.getLogger("taskmasterd")


class Config(object):
    """
    A Config class, shows options for server, client
    or non-interactive taskmaster
    """

    def __init__(self, conf_name):
        """Return Config object with given dict of options or {}"""
        self.name = conf_name
        options = dict(self.read_from_config_file(conf_name))
        user_ps = dict((i, options[i]) for i in options if i != 'taskmasterd')
        for d in user_ps.keys():
            self.check_kwarg(user_ps.get(d))
        self.check_daemon_conf(options.get('taskmasterd', {}))
        taskmasterd_opt = options.get('taskmasterd', {})
        self.logfile = taskmasterd_opt.get('logfile', 'taskmasterd.log')
        self.daemon = taskmasterd_opt.get('daemon', False)
        self.lst_proc_conf = []
        self.create_proc_confs(user_ps)

    def create_proc_confs(self, options):
        """
        For each process config fill params and add Process conf to list of confs
        """
        for k, v in options.items():
            conf = dict()
            for name, value in v.items():
                conf[name] = value
            conf['priority'] = conf.get('priority', 999)
            conf['autostart'] = conf.get('autostart', True)
            conf['stopwaitsecs'] = conf.get('stopwaitsecs', 10)
            conf['umask'] = conf.get('umask', '022')
            conf['stdout'] = conf.get('stdout', 1)
            conf['stderr'] = conf.get('stderr', 2)
            conf['env'] = conf.get('env', os.environ)
            conf['exitcodes'] = list(map(int, conf.get('exitcodes').split(',')))
            num = conf.get('numprocs')
            conf['stopsignal'] = get_signum(conf.get('stopsignal'))
            for i in range(1, num + 1):
                config = copy.copy(conf)
                proc_conf = ProcessConfig(config, "{}_{}".format(k, i))
                self.lst_proc_conf.append(proc_conf)

    def filter_proc_conf(self, proc_conf_list):
        """
        Filter self.proc_conf with names from proc_conf_list
        """
        l = [conf.proc_name for conf in self.lst_proc_conf]
        result_list = []
        for needed in proc_conf_list:
            if needed in l:
                result_list.append(self.get_proc_conf_by_name(needed))
        return result_list

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
        if conf_len == 1 and 'logfile' not in kwarg.keys():
            raise ValueError('not known parameter "%s"' % kwarg.keys()[0])
        elif conf_len == 2 and 'logfile' not in kwarg.keys() and 'daemon' not in kwarg.keys():
            raise ValueError('bad options in taskmasterd config')

    def check_kwarg(self, kwarg):
        for opt in kwarg.keys():
            if opt not in cmd_options_lst:
                raise ValueError('option "%s" is not found in config' % opt)
        if not set(cmd_necessary_opt_lst).issubset(set(kwarg.keys())):
            raise ValueError('not filled all necessary parameters!')
        for k, v in kwarg.items():
            if k == 'cmd' or k == 'umask' or k == 'workingdir' or k == 'exitcodes' or k == 'stopsignal' or k == 'user' or k == 'autorestart':
                if not isinstance(v, str):
                    raise ValueError('bad presentation of "%s"' % k)
                if k == 'autorestart':
                    if v not in ['unexpected', 'never', 'always']:
                        raise ValueError('bad presentation of "%s", need to be %s' % (k, 'unexpected' + ' or never or ' + 'always'))
            if k == 'umask' and not v.isnumeric():
                raise ValueError('bad value for "%s"' % k)
            if k == 'autostart' and not isinstance(v, bool):
                raise ValueError('bad value for "%s"' % k)
            if k == 'numprocs' or k == 'priority' or k == 'startsecs' or k == 'startretries' or k == 'stopwaitsecs':
                if not isinstance(v, int):
                    raise ValueError('bad presentation of "%s"' % k)
            if k == 'numprocs' or k == 'startsecs' or k == 'startretries' or k == 'stopwaitsecs':
                if v < 0 or v > 1000:
                    raise ValueError('bad value for "%s"' % k)
            if k == 'exitcodes':
                try:
                    lst = [int(i) for i in v.split(',')]
                except Exception as e:
                    raise ValueError('bad value for "%s"' % k)              
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
        for proc_conf in new.lst_proc_conf:
            proc = self.get_proc_conf_by_name(proc_conf.get_name())
            if proc is not None:
                if not proc.equal(proc_conf):
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
        for name, value in config.items():
            setattr(self, name, value)

    def get(self, name):
        if self.proc_name == name:
            return True
        return False

    def get_name(self):
        return self.proc_name

    def __repr__(self):
        return self.proc_name

    def equal(self, other):
        return self.__dict__ == other.__dict__

    def get_fd(self, option):
        if isinstance(option, int):
            return option
        else:
            if isinstance(option, str):
                try:
                    file = os.open(option, os.O_CREAT | os.O_WRONLY | os.O_APPEND)
                    return file
                except Exception:
                    logger.error("Can't open file for pipe %s" % option)
            else:
                try:
                    fd = int(option)
                    return fd
                except Exception:
                    logger.error("Bad type for fd %s" % option)

    def stat(self, filename):
        return os.stat(filename)

    def get_path(self):
        """Return a list corresponding to $PATH, or a default."""
        path = ["/bin", "/usr/bin", "/usr/local/bin"]
        if "PATH" in os.environ:
            p = os.environ["PATH"]
            if p:
                path = p.split(os.pathsep)
        return path

    def check_execv_args(self, filename, argv, st):
        """
        Check command arguments to pass to execve
        """
        if st is None:
            raise ValueError("can't find command %r" % filename)

        elif stat.S_ISDIR(st[stat.ST_MODE]):
            raise ValueError("command at %r is a directory" % filename)

        elif not (stat.S_IMODE(st[stat.ST_MODE]) & 0o111):
            raise ValueError("command at %r is not executable" % filename)

        elif not os.access(filename, os.X_OK):
            raise ValueError("no permission to run command %r" % filename)

    def check_cmd(self):
        """
        Check command and arguments, return splitted ones for exec
        """
        try:
            commandargs = shlex.split(self.cmd)
        except ValueError as e:
            raise ValueError("can't parse command %r: %s" % (self.cmd, str(e)))

        if commandargs:
            program = commandargs[0]
        else:
            raise ValueError("command is empty")

        if "/" in program:
            filename = program
            try:
                st = self.stat(filename)
            except OSError:
                st = None

        else:
            path = self.get_path()
            found = None
            st = None
            for dir in path:
                found = os.path.join(dir, program)
                try:
                    st = self.stat(found)
                except OSError:
                    pass
                else:
                    break
            if st is None:
                filename = program
            else:
                filename = found

        self.check_execv_args(filename, commandargs, st)
        return filename, commandargs

    def get_env(self):
        new_env = os.environ.copy()
        self.env = {str(k): str(v) for k, v in self.env.items()}
        new_env.update(self.env)
        return new_env
