import os
import sys
import logging
import uuid

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
    key = sshc.gen_key()
    client = sshc.SSHC(str(uuid.uuid4()), key)
    for tunnel in tunnels:
        client.add_tunnel(*tunnel)
    client.join()


main(_parse_args(sys.argv[1:]))
