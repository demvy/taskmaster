
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
from server import ServerThread
from utils import _signames, decode_wait_status

logger = logging.getLogger("taskmasterd")
logger.setLevel(logging.DEBUG)

taskmasterd = None
state_choice = {'S': 'running', 'R': 'running', 'T': 'stopped', 't': 'stopped',
                'Z': 'zombie', 'X': 'killed', 'x': 'killed'}


def listening_thread(stop_event):
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', 1337))
    sock.listen(5)

    while not stop_event.is_set():
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
    delay = 0 # If nonzero, delay starting or killing until this time
    startretries = 0
    killing = False

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
        self.killing = False
        try:
            filename, argv = self.config.check_cmd()
        except ValueError as what:
            self.state = 'backoff'
            self.startretries += 1
            return

        try:
            pid = os.fork()
            if pid == 0:
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
                    self.logger.info("process: %s: " % self.config.proc_name + out)
                env = self.config.get_env()
                cwd = self.config.workingdir
                if cwd is not None:
                    try:
                        os.chdir(cwd)
                    except OSError as why:
                        code = errno.errorcode.get(why.args[0], why.args[0])
                        msg = "process: %s: couldn't chdir to %s: %s\n" % (self.config.proc_name, cwd, code)
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
                    msg = "process: %s: couldn't exec %s: %s\n" % (self.config.proc_name, argv[0], code)
                    self.logger.error(msg)
            else:
                self.pid = pid
                self.logger.info("child process spawned")
        finally:
            #self.logger.error("child process was not spawned")
            print("333333333333333")
            #os._exit(127)  # exit process with code for spawn failure

    def __repr__(self):
        return self.config.proc_name

    def get_by_name(self, name):
        if self.config.proc_name == name:
            return self
        return None

    def check_exit(self, code):
        print(self.config.exitcodes)
        if code in self.config.exitcodes:
            return True
        else:
            return False

    def kill(self, signal):
        if self.state == 'backoff':
            self.state = 'stopped'
            return

        if self.pid == 0:
            self.logger.error("process: %s: tried to kill not running process" % self.config.proc_name)
        self.delay = time.time() + self.config.stopwaitsecs
        self.state = 'stopping'
        self.killing = True

        try:
            os.close(self.config.stdout)
            os.close(self.config.stderr)
            os.kill(self.pid, signal)
        except Exception:
            self.pid = 0
            self.state = 'unknown'
            self.delay = 0
            self.killing = False

    def finish(self, status):
        ex_code, message = decode_wait_status(status)

        now = time.time()
        self.laststop = now
        if now > self.laststart:
            too_quick = now - self.laststart < self.config.startsecs
        else:
            too_quick = False
            self.logger.warn("process \'%s\' laststart time is in the future, don't "
                             "know how long process was running so assuming it did "
                             "not exit too quickly" % self.config.proc_name)

        expected_exit = self.check_exit(ex_code)
        if self.killing:
            self.killing = False
            self.delay = 0
            message = "process: %s: (%s)" % (self.config.proc_name, message)
            if self.state == 'stopping':
                self.state = 'stopped'
        if too_quick:
            # exited faster than needed to be is status launched
            message = "exited: %s (%s)" % (self.config.proc_name, message + "; not expected")
            self.startretries += 1
            if self.state == 'starting':
                self.state = 'backoff'
            if self.config.startretries > self.startretries:
                self.run()
            else:
                message = "exited: %s (%s); can't run after startretries" % (self.config.proc_name, message)
                self.state = "exited"
        else:
            # normal ending of process from running->stopped state
            self.delay = 0
            self.backoff = 0
            if self.state == 'starting':
                self.state = 'running'
            if expected_exit:
                # expected exit code
                message = "exited: %s (%s)" % (self.config.proc_name, message + "; expected")
            else:
                # unexpected exit code
                message = "exited: %s (%s)" % (self.config.proc_name, message + "; not expected")
            self.state = 'exited'

        self.logger.info(message)
        self.pid = 0

    def get_state(self):
        #if self.state in ['backoff', 'exited', 'stopped']:
        return self.state
        #try:
        #    stat = open("/proc/{}/stat".format(self.pid), 'r')
        #    mode = stat.readline().split()[2]
        #    self.state = state_choice[mode]
        #    return self.state
        #except Exception:
        #    return 'killed'


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

    def wait_children(self):
        try:
            pid, sts = os.waitpid(-1, os.WNOHANG)
            if pid:
                process = self.get_proc_by_pid(pid)
                if process is None:
                    self.logging.info('reaped unknown pid %s' % pid)
                else:
                    process.finish(sts)
        except OSError as exc:
            code = exc.args[0]
            if code not in (errno.ECHILD, errno.EINTR):
                self.logging.critical('waitpid error %r; a process may not be cleaned up properly' % code)
            pid, sts = None, None
        return pid, sts

    def run(self):
        self.create_processes()
        self.run_processes()
        print("In taskmaster run!")
        while True:
            print("%-20s|%-5s|%-10s" % ("Process", "PID", "State"))
            for struct in self.proc_states:
                print("{:20}|{:5}|{:10}".format(struct[0], self.get_proc_by_name(struct[0]).pid, struct[1]))

            for el in self.proc_states:
                proc = self.get_proc_by_name(el[0])
                if proc:
                    el[1] = proc.get_state()

            self.wait_children()


            time.sleep(2)

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
        self.wait_children()

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

    def get_proc_by_pid(self, pid):
        """
        Get process from list by its pid
        """
        for proc in self.processes:
            if proc.pid == pid:
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
    global config, taskmasterd
    signal.signal(signal.SIGHUP, sighup_handler)
    signal.signal(signal.SIGINT, sigint_handler)

    # do server thread like in server.py main func
    # Taskmasterd will be in one thread, instance of server - in other
    # for new client connection, the same thread, can call taskmaster.choose_command(command)

    try:
        global listen_thread#, job_thread
        stop_event = threading.Event()
        listen_thread = threading.Thread(name='listener', target=listening_thread, args=(stop_event,))
        listen_thread.setDaemon(True)
        listen_thread.start()
        config = Config(path_to_config)
        taskmasterd = TaskmasterDaemon(config)
        taskmasterd.run()
    except ExitException:
        #print ("Error: unable to start thread")
        taskmasterd.kill_processes(signal.SIGINT)
        stop_event.set()
        #listen_thread.join()


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