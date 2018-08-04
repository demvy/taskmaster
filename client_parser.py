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

    def send_receive(self, line):
        try:
            self.socket.send(line.encode())
            if (line == "stop taskmaster"):
                exit()
            data = self.socket.recv(1024).decode()
        except Exception as e:
            return
        if (data):
            print(data)
        # if (line == "stop taskmaster" and data == "closing taskmaster..."):
        #     exit()

    def do_stop(self, line):
        if line:
            list_args = line.split()
            if (len(list_args) != 1):
                self.usage()
                return
            self.send_receive("stop " + list_args[0])
        else:
            self.usage()

    def do_start(self, line):
        if line:
            list_args = line.split()
            if (len(list_args) != 1):
                self.usage()
                return
            self.send_receive("start " + list_args[0])
        else:
            self.usage()

    def do_restart(self, line):
        if line:
            list_args = line.split()
            if (len(list_args) != 1):
                self.usage()
                return
            self.send_receive("restart " + list_args[0])
        else:
            self.usage()

    def do_status(self, line):
        if (line != None):
            self.send_receive("status")
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
