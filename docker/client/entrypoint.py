#!/usr/local/bin/jurigged -v

import os
import sys
import time
import logging

import paramiko

from client import ssh


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
    manager = ssh.create_manager()
    for tunnel in tunnels:
        manager.add_tunnel(*tunnel)

    while True:
        manager.poll()
        time.sleep(10)


main(_parse_args(sys.argv[1:]))
