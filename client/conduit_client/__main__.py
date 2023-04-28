import asyncio
import logging
import argparse

from conduit_client import TunnelServer


LOGGER = logging.getLogger()
LOGGER.addHandler(logging.NullHandler())


def main(args):
    server = TunnelServer()
    server.run_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='client',
        description='SSH tunnel client.',
    )

    parser.add_argument('--log-level', type=str, default='DEBUG')

    args = parser.parse_args()

    LOGGER.addHandler(logging.StreamHandler())
    LOGGER.setLevel(logging.getLevelName(args.log_level.upper()))

    main(args)
