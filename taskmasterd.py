
import yaml
import logging
import signal
import time
import os
from datetime import datetime as dt

cmd_options_lst = ['cmd', 'umask', 'workingdir', 'priority', 'autostart', 'startsecs', 'autorestart',
                   'exitcodes', 'startretries', 'starttime', 'stopsignal', 'stopwaitsecs', 'user', 'stdout',
                   'stderr', 'env']
cmd_necessary_opt_lst = ['cmd', 'workingdir', 'startsecs', 'exitcodes', 'starttime', 'startretries',
                         'stopsignal', 'user']


def fill_param(x, v, d):
    if isinstance(d, dict) and x not in d.keys():
        d[x] = v
        return d
    else:
        raise ValueError


class Process():
    def __init__(self, kwarg):
        try:
            self.check_kwarg(kwarg)
            new_kwarg = self.fullfill_kwarg(kwarg)
            self.cmd = new_kwarg['cmd']
            self.umask = new_kwarg['umask']
            self.workingdir = new_kwarg['workingdir']
            self.priority = new_kwarg['priority']
            self.autostart = new_kwarg['autostart']
            self.autorestart = new_kwarg['autorestart']
            self.exitcodes = [int(i) for i in new_kwarg['exitcodes'].split(',')]
            self.startretries = new_kwarg['startretries']
            self.startsecs = new_kwarg['starttime']
            self.stopsignal = new_kwarg['stopsignal']
            self.stopwaitsecs = new_kwarg['stopwaitsecs']
            self.stdout = new_kwarg['stdout']
            self.stderr = new_kwarg['stderr']
            self.env = new_kwarg['env']
        except ValueError:
            raise ValueError("Can't create process with such config!")

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

    def check_kwarg(self, kwarg):
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

    def run(self):
        pass

class TaskmasterDaemon():
    def __init__(self, config):
        self.config = None
        #process = {'process_name' : 'state'}
        self.processes = []
        self.nodaemon = False
        self.logfile = None
        self.set_config(config)

    def set_config(self, config):
        self.config = config
        self.nodaemon = config['taskmasterd']['nodaemon']
        self.logfile = config['taskmasterd']['logfile']
        self.reparse_config(config)

    def reparse_config(self, config):
        for k, v in config.items():
            if k != 'taskmasterd':
                new_process_group = []
                self.processes.append(new_process_group)
                # add check numprocs -> try : check Process creation -> except: refill this process info in conf,
                #  go to next process name
                for i in range(v['numprocs']):
                    proc = Process(v)
                    new_process_group.append({ proc.name : proc.status})


def parse_config():
    """
    Parse config for taskmaster daemon

    Returns:
        dict with options of config
    """
    with open("taskmaster.yaml", 'r') as ymlfile:
        try:
            cfg = yaml.load(ymlfile)
            return cfg
        except yaml.YAMLError as exc:
            raise exc

new_cfg = {}

def signal_handler(signum, frame):
    global new_cfg
    new_cfg = parse_config()
    # implement
    #  !!!!! reload_config()

try:
    new_cfg = parse_config()
    if new_cfg['taskmasterd']['nodaemon']:
        logging.basicConfig(level=logging.DEBUG)
    else:
        try:
            filename = new_cfg['taskmasterd']['logfile']
            logging.basicConfig(filename=filename, level=logging.DEBUG)
        except KeyError as e:
            logging.basicConfig(filename=dt.strftime(dt.now(), '%Y.%m.%d-%H:%M:%S'), level=logging.DEBUG)
except Exception as e:
    print(e)
    logging.error(e)


if __name__ == "__main__":
    signal.signal(signal.SIGHUP, signal_handler)
    while True:
        time.sleep(3)
        print(new_cfg)
    #logging.debug("In main test logging")