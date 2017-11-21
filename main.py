#!/usr/bin/env

import socket
import cmd
import os
import subprocess

#look for subprocess module not os

"""
while True:
    sock = socket.socket()
    sock.bind(('', 1337))
    sock.listen(5)
    conn, addr = sock.accept()

    print('connected:', addr)

    while True:
        data = conn.recv(1024)
        if not data:
            break
        #conn.send(data)
    conn.close()
"""


class Daemon(cmd.Cmd):

    def do_greet(self, line):
        print('hello,', line)

    def do_EOF(self, line):
        "Exit"
        return True


class Illustrate(cmd.Cmd):
    "Illustrate the base class method use."

    def cmdloop(self, intro=None):
        print ('cmdloop(%s)' % intro)
        return cmd.Cmd.cmdloop(self, intro)

    def preloop(self):
        print ('preloop()')

    def postloop(self):
        print ('postloop()')

    def parseline(self, line):
        print ('parseline(%s) =>' % line)
        ret = cmd.Cmd.parseline(self, line)
        print (ret)
        return ret

    def onecmd(self, s):
        print ('onecmd(%s)' % s)
        return cmd.Cmd.onecmd(self, s)

    def emptyline(self):
        print ('emptyline()')
        return cmd.Cmd.emptyline(self)

    def default(self, line):
        print ('default(%s)' % line)
        return cmd.Cmd.default(self, line)

    def precmd(self, line):
        print ('precmd(%s)' % line)
        return cmd.Cmd.precmd(self, line)

    def postcmd(self, stop, line):
        print ('postcmd(%s, %s)' % (stop, line))
        return cmd.Cmd.postcmd(self, stop, line)

    def do_greet(self, line):
        print ('hello,', line)

    def do_EOF(self, line):
        "Exit"
        return True


def reading_conf_f():
    with open('taskmaster.conf', 'r+') as conf:
        for line in conf:
            if line == 'config:':
                print(line)
    return {}


if __name__ == "__main__":
    """
    prompt = Daemon()
    config = reading_conf_f()
    prompt.logfile = config['logfile']
    prompt.prompt = 'wtf?> '
    prompt.cmdloop()
    """
    while True:
        try:
            command = input('wtf?> ')
            subprocess.run(command, stdout)
            #print(command)
        except EOFError:
            exit()