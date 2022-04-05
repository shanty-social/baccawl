import sys
import logging

from conduit_client.server import SSHManagerServer


LOGGER = logging.getLogger()


def main(sock_name):
    server = SSHManagerServer(sock_name)
    server.run_forever()


if __name__ == '__main__':
    LOGGER.addHandler(logging.StreamHandler())
    LOGGER.setLevel(logging.DEBUG)
    main(sys.argv[1])
