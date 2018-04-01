
import yaml
import logging
import signal
import time
from datetime import datetime as dt

cmd_options_lst = ['cmd', 'umask', 'workingdir', 'priority', 'autostart', 'startsecs', 'autorestart',
                   'exitcodes', 'startretries', 'starttime', 'stopsignal', 'stopwaitsecs', 'user', 'stdout',
                   'stderr', 'env']
cmd_necessary_opt_lst = ['cmd', 'workingdir', 'autostart', 'exitcodes', 'startretries', 'stopsignal', 'user']

class Process(kwarg=None):
    def __init__(self):
        self.check_kwarg(kwarg)

        # write fullfill_kwarg function
        new_kwarg = self.fullfill_kwarg(kwarg)
        self.cmd = new_kwarg['cmd']
        self.umask = new_kwarg['umask']
        self.workingdir = new_kwarg['workingdir']
        self.autostart = new_kwarg['autostart']
        self.autorestart = new_kwarg['autorestart']
        self.exitcodes = new_kwarg['exitcodes'].split(',')
        self.startretries = new_kwarg['startretries']
        self.starttime = new_kwarg['starttime']
        self.stopsignal = new_kwarg['stopsignal']
        self.stopwaitsecs = new_kwarg['stopwaitsecs']
        self.stdout = new_kwarg['stdout']
        self.stderr = new_kwarg['stderr']
        self.env = new_kwarg['env']

    def check_kwarg(self, kwarg):
        for opt in kwarg.keys():
            if opt not in cmd_options_lst:
                raise ValueError
        if not set(cmd_necessary_opt_lst).issubset(set(kwarg.keys())):
            raise ValueError
        for k, v in kwarg.items():
            #if k == 'cmd':
            # write function to check all params by types and possible values
            print(k)


class TaskmasterDaemon(config=None):
    def __init__(self):
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
    if cfg['taskmasterd']['nodaemon']:
        logging.basicConfig(level=logging.DEBUG)
    else:
        try:
            filename = cfg['taskmasterd']['logfile']
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