
import logging
import signal
import time
import threading
import sys
import os
import socket
from config import Config, ProcessConfig
from datetime import datetime as dt
from server import ServerThread


class Process():
    def __init__(self, config):
        self.config = config
        """
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
        """

    def run(self):
        pass


class TaskmasterDaemon():
    def __init__(self, config):
        self.config = config
        #process = {'process_name' : 'state'}
        self.processes = []
        self.logging = logging.basicConfig(filename=config.logfile, level=logging.DEBUG)
        #function to call for creating a thread
        #self.func = self.run_server
        #self.shutdown_flag = threading.Event()
        #self.conn = None

    def set_config(self, config):
        self.config = config

    def run(self):
        self.func()

    def choose_command(self, command):
        """
        Get command from server, analyze it and run start/stop/restart/status function
        Returns response to client when end (string with status, etc..)
        Need to implement
        """
        pass

    def change_config(self, new_config):
        reloading, added, changed, removed = config.diff_to_active(new_config)

        """
        for k, v in new_config.items():
            if k != 'taskmasterd':
                new_process_group = []
                self.processes.append(new_process_group)
                # add check numprocs -> try : check Process creation -> except: refill this process info in conf,
                #  go to next process name
                for i in range(v['numprocs']):
                    proc = Process(v)
                    new_process_group.append({ proc.name : proc.status})
        """


class ExitException(Exception):
    """
    Exception class showing we got SIGINT
    """
    pass


def sighup_handler(signum, frame):
    global taskmasterd
    global new_cfg, config
    new_cfg = Config(cfg_name)
    taskmasterd.change_config(new_cfg)
    taskmasterd.set_config(new_cfg)
    config = new_cfg


def sigint_handler(signum, frame):
    raise ExitException('You have pressed Ctrl+C')


def main(path_to_config):
    signal.signal(signal.SIGHUP, sighup_handler)
    signal.signal(signal.SIGINT, sigint_handler)

    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', 1337))
    sock.listen(5)

    while True:
        conn, addr = sock.accept()

        # do server thread like in server.py main func
        # Taskmasterd will be in one thread, instance of server - in other
        # for new client connection, make new thread which can call taskmaster.choose_command(command)
        global config, taskmasterd
        config = Config(path_to_config)
        taskmasterd = TaskmasterDaemon(config)
        taskmasterd.run()


if __name__ == "__main__":
    global cfg_name
    if sys.argv[2]:
        if os.path.exists(sys.argv[2]) and os.path.isfile(sys.argv[2]):
            cfg_name = sys.argv[2]
        else:
            cfg_name = 'taskmaster.yaml'
    else:
        cfg_name = 'taskmaster.yaml'
    main(cfg_name)