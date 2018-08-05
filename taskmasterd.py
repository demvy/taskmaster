
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
from utils import _signames, decode_wait_status, get_signame

logger = logging.getLogger("taskmasterd")
logger.setLevel(logging.DEBUG)

taskmasterd = None


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
            #print ("Error: unable to start thread")
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
        self.stdout = config.get_fd(config.stdout)
        self.stderr = config.get_fd(config.stderr)

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
            return ""
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


    def close_fds(self):
        if self.stderr != 2:
            os.close(self.stderr)
        if self.stdout != 1:
            os.close(self.stdout)

    def run(self):
        #print(self.config.proc_name)
        if self.pid:
            msg = 'process \'%s\' already running' % self.config.proc_name
            logger.warning(msg)
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
                os.dup2(self.stdout, 1)
                os.dup2(self.stderr, 2)
                # for i in range(3, 1024):
                #     try:
                #         os.close(i)
                #     except OSError:
                #         pass
                user = getattr(self.config, 'user', None)
                out = self.set_uid(user)
                if out:
                    logger.info("process: %s: %s" % (self.config.proc_name, out))
                env = self.config.get_env()
                cwd = self.config.workingdir
                if cwd is not None:
                    try:
                        os.chdir(cwd)
                    except OSError as why:
                        code = errno.errorcode.get(why.args[0], why.args[0])
                        msg = "process: %s: couldn't chdir to %s: %s\n" % (self.config.proc_name, cwd, code)
                        logger.warning(msg)
                        return
                try:
                    if self.config.umask is not None:
                        os.umask(int(self.config.umask, 8))
                    os.execve(filename, argv, env)
                except OSError as why:
                    code = errno.errorcode.get(why.args[0], why.args[0])
                    msg = "process: %s: couldn't exec %s: %s\n" % (self.config.proc_name, argv[0], code)
                    logger.error(msg)
            else:
                self.pid = pid
                logger.info("child process spawned")
        finally:
            pass

    def __repr__(self):
        return self.config.proc_name

    def get_by_name(self, name):
        if self.config.proc_name == name:
            return self
        return None

    def check_exit(self, code):
        if code in self.config.exitcodes:
            return True
        else:
            return False

    def kill(self, signal):
        if self.state == 'backoff':
            self.state = 'stopped'
            return

        #print("pid = %d" %self.pid)
        if self.pid == 0:
            logger.error("process: %s: tried to kill not running process" % self.config.proc_name)
            return
        self.delay = time.time() + self.config.stopwaitsecs
        self.state = 'stopping'
        self.killing = True
        logger.debug('killing %s (pid %s) with signal %s' % (self.config.proc_name, self.pid, get_signame(signal)))

        try:
            #print("gggggggppppppppdddd")
            #if self.stdout != 1:
                #print(self.stdout, self.stderr)
                #os.close(self.stdout)
            #if self.stderr != 2:
                #os.close(self.stderr)
            #print("pid kill = %d" % self.pid)
            os.kill(self.pid, signal)
            #print("pid after kill = %d" % self.pid)
        except Exception:
            self.pid = 0
            self.state = 'unknown'
            self.delay = 0
            self.killing = False
            #self.stderr = self.config.get_fd(config.stderr)
            #self.stdout = self.config.get_fd(config.stdout)

    def finish(self, status):
        ex_code, message = decode_wait_status(status)

        now = time.time()
        self.laststop = now
        if now > self.laststart:
            too_quick = now - self.laststart < self.config.startsecs
        else:
            too_quick = False
            logger.warn("process \'%s\' laststart time is in the future, don't "
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
            if expected_exit:
                self.startretries = 0
                self.delay = 0
                self.state = 'exited'
        else:
            # normal ending of process from running->stopped state
            self.delay = 0
            if self.state == 'starting':
                self.state = 'running'
            if expected_exit:
                # expected exit code
                self.startretries = 0
                message = "exited: %s (%s)" % (self.config.proc_name, message + "; expected")
            else:
                self.startretries += 1
                message = "exited: %s (%s)" % (self.config.proc_name, message + "; not expected")
            self.state = 'exited'

        logger.info(message)
        self.pid = 0
        if self.config.autorestart == 'never':
            return
        elif self.config.autorestart == 'always':
            self.run()
        elif self.config.autorestart == 'unexpected' and not expected_exit:
            if self.config.startretries > self.startretries:
                self.run()
            else:
                message = "exited: %s: can't run after startretries" % self.config.proc_name
                logger.info(message)

    def check_state(self):
        now = time.time()
        if self.state == 'starting':
            if now - self.laststart > self.config.startsecs:
                self.delay = 0
                #self.startretries = 0
                self.state = 'running'
                msg = ('process: %s: entered RUNNING state, process has stayed up for '
                       '> than %s seconds (startsecs)' % (self.config.proc_name, self.config.startsecs))
                logger.info(msg)

        if self.state == 'backoff':
            if self.startretries >= self.config.startretries:
                self.delay = 0
                self.startretries = 0
                self.state = 'fatal'
                msg = ('process: %s: entered FATAL state, too many start retries too '
                       'quickly' % self.config.proc_name)
                logger.info(msg)

        elif self.state == 'stopping':
            time_left = self.delay - now
            if time_left <= 0:
                # kill processes which are taking too long to stop with a final sigkill.
                # If this doesn't kill it, the process will be stuck in the STOPPING state forever.
                logger.warn(
                    'killing \'%s\' (%s) with %s' % (self.config.proc_name, self.pid, self.config.stopsignal.name))
                self.kill(self.config.stopsignal)

    def restart(self):
        self.stop()
        self.run()

    def stop(self):
        self.kill(self.config.stopsignal)
        #print("after killing, startretries = " + str(self.startretries))
        # try:
        #     pid, sts = os.waitpid(self.pid, os.WNOHANG)
        #     if pid:
        #         self.finish(sts)
        #         print("after fffinish@@@, startretries = " + str(self.startretries))
        # except OSError as exc:
        #     code = exc.args[0]
        #     if code not in (errno.ECHILD, errno.EINTR):
        #         logger.critical('process: %s: waitpid error %r; a process may not be cleaned up properly' % (
        #         self.config.proc_name, code))
        #print("go out!!@!")
        self.check_state()

    def get_state(self):
        return self.state


class TaskmasterDaemon(object):
    def __init__(self, config):
        self.config = config
        self.processes = []
        if self.config.logfile:
            global logger
            fh = logging.FileHandler(config.logfile)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            logger.addHandler(fh)
            self.logging = logger
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

    def show_status(self):
        result = ''
        for proc in self.processes:
            proc.check_state()
            result += "{:20}{:10}\n".format(proc.config.proc_name, proc.state)
        self.wait_children()
        return result

    def run(self):
        self.create_processes(self.config.lst_proc_conf)
        self.run_processes(self.processes)
        #print("In taskmaster run!")
        while True:
            self.show_status()
            #time.sleep(2)
            pass

    def create_processes(self, list_proc_confs):
        """
        Creates all processes from config, returns these Processes objects list
        """
        created_list = []
        for proc_conf in list_proc_confs:
            process = Process(proc_conf)
            self.processes.append(process)
            created_list.append(process)
        return created_list

    def kill_processes(self, signal, process_list):
        for proc in process_list:
            the_same_launched_proc = self.get_proc_by_name(proc.config.proc_name)
            if the_same_launched_proc is not None and isinstance(the_same_launched_proc, Process):
                self.processes.remove(the_same_launched_proc)
                if the_same_launched_proc.stdout != 1:
                    os.close(the_same_launched_proc.stdout)
                if the_same_launched_proc.stderr != 2:
                    os.close(the_same_launched_proc.stderr)
                if the_same_launched_proc.pid:
                    os.kill(the_same_launched_proc.pid, signal.SIGKILL)

    def run_processes(self, process_list):
        """
        Run each process from config
        """
        for proc in process_list:
            if proc.config.autostart:
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

    def get_proc_by_conf(self, conf):
        """
        Get process from list by its config
        """
        for proc in self.processes:
            if proc.config.proc_name == conf.proc_name:
                return proc
        return None

    def choose_command(self, command):
        """
        Get command from server, analyze it and run start/stop/restart/status function
        Returns response to client when end (string with status, etc..)
        Need to implement
        """
        list_args = command.split()
        if (len(list_args) < 1):
            return None
        elif (list_args[0] == "start"):
            proc =  self.get_proc_by_name(list_args[1])
            if proc is None:
                return "no such process '" + list_args[1] + "'"
            if proc.state in ['exited', 'stopped', 'fatal', 'backoff', 'unknown']:
                proc.run()
            return "starting the process '" + list_args[1] + "'..."

        elif (list_args[0] == "stop"):
            if (list_args[1] == "taskmaster"):
                self.kill_processes(signal.SIGKILL, self.processes)
                time.sleep(1)
                exit(0)
                return "closing taskmaster..."
            proc =  self.get_proc_by_name(list_args[1])
            if proc is None:
                return "no such process '" + list_args[1] + "'"
            if proc.state in ['starting', 'running', 'backoff', 'stopping']:
                proc.stop()
            return "the process '" + list_args[1] + "' is stopped"

        elif (list_args[0] == "restart"):
            proc =  self.get_proc_by_name(list_args[1])
            if proc is None:
                return "no such process '" + list_args[1] + "'"
            proc.restart()
            return "restarting the process '" + list_args[1] + "'..."

        elif list_args[0] == "reload":
            sighup_handler(1, frame=None)
            return "config reloaded"

        elif (list_args[0] == "status"):
            return self.show_status()
        return "unexpected command. Try another one"

    def change_config(self, new_config):
        reloading, added, changed, removed = self.config.diff_to_active(new_config)
        #print(reloading, added, changed, removed)

        if not reloading and added or changed or removed:
            lst_proc_to_stop, lst_proc_to_run = [], []
            for proc_conf in changed + removed:
                proc = self.get_proc_by_conf(proc_conf)
                if proc is not None:
                    lst_proc_to_stop.append(proc)
            for proc_conf in added + changed:
                lst_proc_to_run.append(proc_conf)
            self.kill_processes(signal.SIGKILL, lst_proc_to_stop)
            lst_proc_to_run = new_config.filter_proc_conf(['{}'.format(name) for name in lst_proc_to_run])
            lst_proc_to_run = self.create_processes(lst_proc_to_run)
            self.run_processes(lst_proc_to_run)
        self.set_config(new_config)
        self.logging.info("taskmasterd: Config has been reloaded")

class ExitException(Exception):
    """
    Exception class showing we got SIGINT
    """
    pass


def sighup_handler(signum, frame):
    #print("In sighup handler")
    global taskmasterd
    global new_cfg, config
    new_cfg = Config(config.name)
    taskmasterd.change_config(new_cfg)
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
        while True:
            pass
    except ExitException:
        ##print ("Error: unable to start thread")
        taskmasterd.kill_processes(signal.SIGINT, taskmasterd.processes)
        stop_event.set()


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