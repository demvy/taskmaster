#!/usr/bin/env python

import socket
import os
import subprocess
import _thread
import threading

def client_entire(conn):
    while True:
        try:
            data = conn.recv(1024)
        except ConnectionResetError as e:
            data = None
        if not data:
            break
        else:
            print(data)
            conn.send(data)
    conn.close()

class myThread (threading.Thread):
   def __init__(self, threadID, conn):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.conn = conn
   def run(self):
      print("Starting id %s" % self.threadID)
      client_entire(self.conn)
      print("Exiting %s" % self.threadID)


if __name__ == "__main__":
    """
    prompt = Daemon()
    config = reading_conf_f()
    prompt.logfile = config['logfile']
    prompt.prompt = 'wtf?> '
    prompt.cmdloop()
    """
    #while True:
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', 1337))
    sock.listen(5)


    


    while True:
        try:
            conn, addr = sock.accept()
        except KeyboardInterrupt as e:
            exit()

        print('connected:', addr)

        try:
            new_thread = myThread(1, conn)
            new_thread.start()
            print(new_thread.getName())
            #new_thread.join()
        except:
            print ("Error: unable to start thread")
            conn.close()

        print(threading.enumerate())
"""
        try:
            _thread.start_new_thread(client_entire, (conn, ))
        except:
            print ("Error: unable to start thread")
            conn.close()
"""