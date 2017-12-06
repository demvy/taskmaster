#!/usr/bin/env python

import sys
from ConfigClass import Config

options = {'--timeout': ' n \vafter n seconds, terminate the executable',
           '--delayrandom': ' \vdelay the execution of executable by '
                            'random seconds up to n',
           '--debug': ' \venable debugging output, all logs to stderr and'
                      ' not syslog.',
           '--help': 'this text',
           '--': 'use the -- to separate supervisor options from arguments'
                 ' to the executable which will appear as options.'}


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
    for (key, val) in zip(args[::2], args[1::2]):
        if val != '--':
            conf.add_option(key, val)
        else:
            conf.add_option(key, True)


if __name__ == "__main__":
    conf = Config()
    cmd_index = sys.argv.index('--') + 1
    if good_cmd_args(sys.argv[1:cmd_index]):
        add_args_to_conf(sys.argv[1:cmd_index], conf)
    print(conf.get_options())