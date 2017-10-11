#!/usr/bin/env

import socket

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


class Daemon():
    pass

if __name__ == "__main__":
    with open('taskmaster.conf', 'rw') as conf:
        for line in conf:
            if not line.startswith(';'):
                print(line)