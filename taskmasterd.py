
import logging
import signal
import time
import os
from datetime import datetime as dt


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