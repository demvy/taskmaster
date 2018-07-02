#!/usr/bin/env python

import socket
import threading


class ServerThread(threading.Thread):
    def __init__(self, threadID, conn, caller=None):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.conn = conn
        self.call_back_server = caller

    def run(self):
        print("Starting id %s" % self.threadID)
        self.server_entire()
        print("Exiting %s" % self.threadID)

    def server_entire(self):
        while True:
            try:
                data = self.conn.recv(1024)
            except ConnectionResetError as e:
                data = None
            if not data:
                break
            else:
                print(data)
                #response = self.call_back_server.choose_command(data)
                self.conn.send(data)
        self.conn.close()


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
            new_thread = ServerThread(1, conn)
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