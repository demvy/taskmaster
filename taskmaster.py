#!/usr/bin/env python

import sys, os, signal
#import subprocess
import tempfile
from random import randint
from time import sleep
from ConfigClass import Config
from subprocess import TimeoutExpired, run, Popen

options = {'--timeout': 'n\v\bafter n seconds, terminate the executable',
           '--delayrandom': 'n\v\bdelay the execution of executable by '
                            'random seconds up to n',
           '--help': 'this text',
           '--': 'separate taskmaster options from command'}


def good_cmd_args(args):
    """
    Checks options, prints errors in stderr
    :param args: list of arguments from shell, up to --
    :return: True if all options are right, False otherwise
    """
    for ar in args:
        if ar[:1] == '--' or ar.startswith('-') and ar not in options.keys():
            print('ERROR:taskmaster:option {} not recognized'.format(ar),
                  end='\n', file=sys.stderr)
            return False
    return True


def add_args_to_conf(args, conf):
    """
    Makes Config object filled with args
    :param args: list of arguments from shell, up to --
    :param conf: Config object
    :return:
    """
    for (key, val) in zip(args[::], args[1::]):
        if not val.startswith('--') and key.startswith('--'):
            conf.add_option(key, val)
        elif key.startswith('--'):
            conf.add_option(key, True)


def check_delim(args):
    """
    Checks option -- as delimeter in command line arguments
    :param args: list from arguments from shell
    :return: True if -- in args, False otherwise
    """
    try:
        cmd_index = sys.argv.index('--') + 1
        return True
    except ValueError:
        # print('ERROR:taskmaster usage: python3 taskmaster.py [options]'
        #       ' -- command. For more detailed manual use flag --help',
        #       end='\n', file=sys.stderr)
        return False


def check_command(index, args):
    """
    Checks if only one command in args after index of --
    :param index: index of -- option
    :param args: list of command line arguments
    :return: True if all is ok, False otherwise
    """
    return len(args[index:]) == 1 and not args[index:][0] == '-'


def check_args(args, config):
    """
    Checks ccommand line arguments are right
    :param args: command line arguments after name of program
    :return: True if all is ok, False otherwise
    """
    if check_delim(args):
        cmd_index = args.index('--') + 1
        if good_cmd_args(args[:cmd_index]):
            if check_command(cmd_index, args):
                return True
    config.set_options({'--help': True})
    run_help(config)
    return False


def delay_run_command(n):
    """
    Delay program from 1 to n seconds chosen randomly
    :return:
    """
    b = randint(1, n)
    print('choosen delay = {}'.format(b))
    sleep(b)


def run_command(conf):
    """
    Runs command, print stdout to stdout of parent shell, uses 42sh)
    :param command: command to run (string) can be a format of 42sh
    :return:
    """
    if '--delayrandom' in conf.options:
        delay_run_command(conf.options['--delayrandom'])
    with tempfile.TemporaryFile() as tempf:
        proc = Popen(["42sh", conf.options['--']], preexec_fn=os.setsid)
        try:
            tempf, errs = proc.communicate(timeout=conf.options['--timeout'])
        except TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            tempf.seek(0)
            print(tempf.read().decode('utf-8'))


def run_help(config):
    """
    Shows help for module usage
    :param config: Config object of program
    :return:
    """
    print('You are reading a help for taskmaster!\nUsage: python3 '
          'taskmaster.py [options] -- command.', end='\n', file=sys.stdout)
    print('OPTIONS:', end='\n', file=sys.stdout)
    if len(config.options) > 1:
        for key in config.options:
            print('{}\t{}'.format(key.rjust(15, ' '),
                                  options[key].ljust(60, ' ')),
                  end='\n', file=sys.stdout)
    else:
        for key in options:
            print('{}\t{}'.format(key.rjust(15, ' '),
                                  options[key].ljust(60, ' ')),
                  end='\n', file=sys.stdout)


def validate_conf_vars(conf):
    try:
        if '--timeout' in conf.options:
            conf.add_option('--timeout', int(conf.options['--timeout']))
        if '--delayrandom' in conf.options:
            conf.add_option('--delayrandom', int(conf.options['--delayrandom']))
        return True
    except ValueError:
        print('Variables n have to be an integers!Read --help',
              file=sys.stderr)
        return False


if __name__ == "__main__":
    conf = Config()
    if check_args(sys.argv[1:], conf):
        cmd_index = sys.argv.index('--') + 1
        add_args_to_conf(sys.argv[1:cmd_index + 1], conf)
        if validate_conf_vars(conf):
            print(conf.get_options())
            if '--help' in conf.options.keys():
                run_help(conf)
                exit(0)
            command = conf.options['--']
            run_command(conf)
