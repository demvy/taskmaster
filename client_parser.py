import cmd
import socket

class client_parser(cmd.Cmd):

    def __init__(self):
        super().__init__()
        self.prompt = "wtf?> "
        self.socket = socket.socket()
        self.init_socket()

    def init_socket(self):
        created = False
        while not created:
            try:
                self.socket.connect(('localhost', 1337))
                created = True
            except socket.error as e:
                self.socket.close()
                exit()

    def usage(self):
        print("Usage:\tstart\t'process name'\n\tstop\t'process name'\n\trestart\t'process name'\n\tstop\ttaskmaster\n\tstatus")  

    def do_stop(self, line):
        if line:
            list_args = line.split()
            if (len(list_args) != 1):
                self.usage()
                pass
            try:
                self.socket.send(("stop " + line).encode())
            except Exception as e:
                pass
        else:
            self.usage()

    def do_start(self, line):
        if line:
            list_args = line.split()
            if (len(list_args) != 1):
                self.usage()
                pass
            try:
                self.socket.send(("start " + line).encode())
            except Exception as e:
                pass
        else:
            self.usage()

    def do_restart(self, line):
        if line:
            list_args = line.split()
            if (len(list_args) != 1):
                self.usage()
                pass
            try:
                self.socket.send(("restart " + line).encode())
                data = self.socket.recv(1024).decode()
            except Exception as e:
                pass
            if (data):
                print(data)
        else:
            self.usage()

    def do_status(self, line):
        if (line != None):
            try:
                self.socket.send(("status").encode())
                data = self.socket.recv(1024).decode()
            except Exception as e:
                pass
            if (data):
                print(data)
        else:
            self.usage()
    
    def emptyline(self):
        return None

    def default(self, line):
        self.usage()
        pass

    def do_EOF(self, line):
        return True

if __name__ == '__main__':
    client = client_parser().cmdloop()
