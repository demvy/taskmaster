#!/usr/bin/env python

import socket
import sys
import time

commands = {
	'start': 0,
	'stop': 1
}

def parse_input(string):
	if not string:
		return 0

	arg_list = string.split(" ")

	try:
		key = commands[arg_list[0]]
	except:
		return 0

	print(key)

	return 1

def main():
	sock = socket.socket()

	try:
		sock.connect(('localhost', 1337))
	except ConnectionRefusedError as e:
		sock.close()
		exit()

	while True:
		try:
			string = input('> ')
		except KeyboardInterrupt as e:
			break

		if not string:
			continue

		if not parse_input(string):
			continue

		try:
			sock.send(''.join([string, ]).encode())
			data = sock.recv(1024).decode()
		except BrokenPipeError as e:
			break
	
		print(data)
		if data == 'exit':
			break

	print('my exit')
	sock.close()

#start stop status help

main()