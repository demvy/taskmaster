
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

threads = []
taskmasterd = None


def listening_thread():
    global threads
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', 1337))
    sock.listen(5)

    while True:
        try:
            conn, addr = sock.accept()
        except KeyboardInterrupt as e:
            raise ValueError("Can't accept new connection")
        try:
            server_thread = ServerThread(1, conn)
            server_thread.start()
            server_thread.set_caller(taskmasterd)
            threads.append(server_thread)
            print(server_thread.getName())
        except:
            print ("Error: unable to start thread")
            conn.close()


class Process(object):
    def __init__(self, config):
        self.config = config
        self.state = 'starting'
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

    def __repr__(self):
        return self.config.proc_name

    def get_by_name(self, name):
        if self.config.proc_name == name:
            return self
        return None


class TaskmasterDaemon(object):
    def __init__(self, config):
        self.config = config
        #process = {'process_name' : 'state'}
        self.processes = []
        self.logging = logging.basicConfig(filename=config.logfile, level=logging.DEBUG)

    def set_config(self, config):
        self.config = config

    def run(self):
        self.create_processes()
        self.run_processes()
        print("In taskmaster run!")
        while True:
            """
            Need to implement monitoring system:
                Every 1-2 seconds get states from all processes and write in Taskmaster variable
                - get values
                - lock()
                - write_values
                - unlock()
            """
            pass

    def create_processes(self):
        """
        Creates all processes from config
        """
        for proc_conf in self.config.lst_proc_conf:
            process = Process(proc_conf)
            self.processes.append(process)

    def run_processes(self):
        """
        Run each process from config
        """
        for proc in self.processes:
            proc.run()

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
    global threads, config, taskmasterd
    signal.signal(signal.SIGHUP, sighup_handler)
    signal.signal(signal.SIGINT, sigint_handler)

    # do server thread like in server.py main func
    # Taskmasterd will be in one thread, instance of server - in other
    # for new client connection, make new thread which can call taskmaster.choose_command(command)

    try:
        listen_thread = threading.Thread(target=listening_thread)
        config = Config(path_to_config)
        taskmasterd = TaskmasterDaemon(config)
        taskmasterd.run()
    except ExitException:
        print ("Error: unable to start thread")
        for thread in threads:
            thread.shutdown_flag.set()
        for thread in threads:
            thread.join()
        listen_thread.join()


if __name__ == "__main__":
    global cfg_name
    if sys.argv[1]:
        if os.path.exists(sys.argv[1]) and os.path.isfile(sys.argv[1]):
            cfg_name = sys.argv[1]
        else:
            cfg_name = 'taskmaster.yaml'
    else:
        cfg_name = 'taskmaster.yaml'
    main(cfg_name)