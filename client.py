#!/usr/bin/env

import socket
import sys

sock = socket.socket()
sock.connect(('localhost', 1337))
sock.send(' '.join(sys.argv[1:]))
data = sock.recv(1024)
sock.close()