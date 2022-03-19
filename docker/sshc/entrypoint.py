#!/usr/local/bin/jurigged -v

import sys
sys.path.append('/app')

import os
import time
import logging

import paramiko

import sshc

LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG').upper()

LOGGER = logging.getLogger()
LOGGER.addHandler(logging.StreamHandler())
LOGGER.setLevel(getattr(logging, LOG_LEVEL, 'DEBUG'))


def _parse_args(args):
    tunnels = []
    for arg in args:
        try:
            hostname, addr, port = arg.split(':')
            tunnels.append((hostname, addr, int(port)))

        except ValueError as e:
            print('Invalid tunnel specification: %s, %s' % (arg, e.args[0]))
            sys.exit(1)
    return tunnels


def main(tunnels):
    for tunnel in tunnels:
        sshc.add_tunnel(*tunnel)

    while True:
        sshc.poll()
        time.sleep(30)


main(_parse_args(sys.argv[1:]))
