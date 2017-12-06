#!/usr/bin/env python

import socket
import os
import subprocess


if __name__ == "__main__":
    """
    prompt = Daemon()
    config = reading_conf_f()
    prompt.logfile = config['logfile']
    prompt.prompt = 'wtf?> '
    prompt.cmdloop()
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
                # conn.send(data)
        conn.close()