#!/usr/bin/env python

import sys
import os
import signal
import tempfile
import argparse
import time
from subprocess import TimeoutExpired, Popen


def run_command(args):
    """
    Runs command, print stdout to stdout of parent shell, uses 42sh)

    Args:
        args (ArgumentParser obj): arguments of command line
    """
    time.sleep(args.delayrandom)
    with tempfile.TemporaryFile() as tempf:
        proc = Popen(["42sh", args.command], preexec_fn=os.setsid)
        try:
            if args.timeout:
                code = proc.wait(timeout=args.timeout)
        except TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            tempf.seek(0)
            print(tempf.read().decode('utf-8'))


def parse_args():
    """
    Parsing cmdline arguments
    """
    parser = argparse.ArgumentParser(description="Taskmaster non-interactive mode")
    parser.add_argument('-t', '--timeout', action='store', type=int, required=False,
                        help='Terminate the executable after n seconds')
    parser.add_argument('-d', '--delayrandom', action='store', required=False,
                        help='Delay the execution of executable by n seconds')
    parser.add_argument('-c', '--command', action="store", required=True,
                        help="Command to execute")
    parser.set_defaults(func=run_command)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        args.func(args)
    except Exception as e:
        print(e)