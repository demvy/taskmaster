
import logging
import signal
import time
import threading
import sys
import os
import socket
import pwd
import grp
import errno
from config import Config
from datetime import datetime as dt
from server import ServerThread

logger = logging.getLogger("taskmasterd")
logger.setLevel(logging.DEBUG)

threads = []
taskmasterd = None
state_choice = {'S': 'running', 'R': 'running', 'T': 'stopped', 't': 'stopped',
                'Z': 'zombie', 'X': 'killed', 'x': 'killed'}


def listening_thread():
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
            server_thread.set_caller(taskmasterd)
            server_thread.run()
        except:
            print ("Error: unable to start thread")
            conn.close()


class Process(object):
    config = None
    state = ''
    pid = 0
    laststart = 0
    laststop = 0
    delay = 0
    startretries = 0

    def __init__(self, config):
        self.config = config
        self.state = 'stopped'
        self.logger = logger

    def drop_priviledges(self, user):
        if user is None:
            return "No user specified to setuid to!"

        try:
            uid = int(user)
        except ValueError:
            try:
                pwrec = pwd.getpwnam(user)
            except KeyError:
                return "Can't find username %r" % user
            uid = pwrec[2]
        else:
            try:
                pwrec = pwd.getpwuid(uid)
            except KeyError:
                return "Can't find uid %r" % uid

        current_uid = os.getuid()
        if current_uid == uid:
            return
        if current_uid != 0:
            return "Can't drop privilege as nonroot user"

        gid = pwrec[3]
        if hasattr(os, 'setgroups'):
            user = pwrec[0]
            groups = [grprec[2] for grprec in grp.getgrall() if user in
                      grprec[3]]
            groups.insert(0, gid)
            try:
                os.setgroups(groups)
            except OSError:
                return 'Could not set groups of effective user'
        try:
            os.setgid(gid)
        except OSError:
            return 'Could not set group id of effective user'
        os.setuid(uid)
        return "User set for the process"

    def set_uid(self, user):
        return self.drop_priviledges(user)

    def run(self):
        print(self.config.proc_name)
        if self.pid:
            msg = 'process \'%s\' already running' % self.config.proc_name
            self.logger.warning(msg)
            return

        self.laststart = time.time()
        self.state = 'starting'
        try:
            filename, argv = self.config.check_cmd()
        except ValueError as what:
            self.state = 'backoff'
            self.startretries += 1
            return

        try:
            pid = os.fork()
            if pid == 0:
                print("ggggggggw")
                os.setpgrp()
                os.dup2(self.config.stdout, 1)
                os.dup2(self.config.stderr, 2)
                for i in range(3, 1024):
                    try:
                        os.close(i)
                    except OSError:
                        pass
                user = getattr(self.config, 'user', None)
                out = self.set_uid(user)
                if out:
                    self.logger.info("process: %s: " % self.pid + out)
                env = self.config.get_env()
                cwd = self.config.workingdir
                if cwd is not None:
                    try:
                        os.chdir(cwd)
                    except OSError as why:
                        code = errno.errorcode.get(why.args[0], why.args[0])
                        msg = "process: %s: couldn't chdir to %s: %s\n" % (self.pid, cwd, code)
                        self.logger.warning(msg)
                        return
                try:
                    print("44444444444444")
                    if self.config.umask is not None:
                        os.umask(int(self.config.umask))
                    print(filename, argv, env)
                    os.execve(filename, argv, env)
                    print("555555555555555555")
                except OSError as why:
                    code = errno.errorcode.get(why.args[0], why.args[0])
                    msg = "process: %s: couldn't exec %s: %s\n" % (self.pid, argv[0], code)
                    self.logger.error(msg)
            else:
                self.pid = pid
        finally:
            self.logger.error("child process was not spawned")
            #print("333333333333333")
            #os._exit(127)  # exit process with code for spawn failure

    def __repr__(self):
        return self.config.proc_name

    def get_by_name(self, name):
        if self.config.proc_name == name:
            return self
        return None

    def kill(self, signal):
        if self.state == 'backoff':
            self.state = 'stopped'
            return
        if not self.pid:
            self.logger.error("tried to kill not running process")
        self.delay = time.time() + self.config.stopwaitsecs
        self.state = 'stopping'
        try:
            os.close(self.config.stdout)
            os.close(self.config.stderr)
            os.kill(self.pid, signal)
        except Exception:
            self.pid = 0
            self.state = 'unknown'
            self.delay = 0

    def get_state(self):
        try:
            stat = open("/proc/{}/stat".format(self.pid), 'r')
            mode = stat.readline().split()[2]
            self.state = state_choice[mode]
            return self.state
        except Exception:
            return 'killed'


class TaskmasterDaemon(object):
    def __init__(self, config):
        self.config = config
        #process = ['process_name', 'state'] # this is structure in proc_states
        self.proc_states = []
        self.processes = []
        if self.config.logfile:
            global logger
            self.logging = logger
            fh = logging.FileHandler(config.logfile)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            self.logging.addHandler(fh)
            logger = self.logging
        else:
            self.logging = logging

    def set_config(self, config):
        self.config = config

    def run(self):
        self.create_processes()
        self.run_processes()
        print("In taskmaster run!")
        while True:
            for el in self.proc_states:
                proc = self.get_proc_by_name(el[0])
                if proc:
                    el[1] = proc.get_state()

            print("%-20s|%-5s|%-10s" % ("Process", "PID", "State"))
            for struct in self.proc_states:
                print("{:20}|{:5}|{:10}".format(struct[0], self.get_proc_by_name(struct[0]).pid, struct[1]))
            time.sleep(1)
            """
            Need to implement monitoring system:
                Every 1-2 seconds get states from all processes and write in Taskmaster variable
                - get values
                - lock()
                - write_values
                - unlock()
            """

    def create_processes(self):
        """
        Creates all processes from config
        """
        for proc_conf in self.config.lst_proc_conf:
            process = Process(proc_conf)
            self.processes.append(process)
            self.proc_states.append([process.config.proc_name, 'stopped'])

    def kill_processes(self, signal):
        for proc in self.processes:
            proc.kill(signal)

    def run_processes(self):
        """
        Run each process from config
        """
        for proc in self.processes:
            proc.run()

    def get_proc_by_name(self, name):
        """
        Get process from list by its name
        """
        for proc in self.processes:
            if proc.get_by_name(name):
                return proc
        return None

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
        self.logging.info("Config has been reloaded")

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
    # for new client connection, the same thread, can call taskmaster.choose_command(command)

    try:
        global listen_thread#, job_thread
        listen_thread = threading.Thread(name='listener', target=listening_thread)
        listen_thread.setDaemon(True)
        listen_thread.start()
        config = Config(path_to_config)
        taskmasterd = TaskmasterDaemon(config)
        taskmasterd.run()
    except ExitException:
        print ("Error: unable to start thread")
        taskmasterd.kill_processes(signal.SIGINT)
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