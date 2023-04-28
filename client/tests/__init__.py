import logging

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.ERROR)
LOGGER.addHandler(logging.StreamHandler())

from tests.test_api import *
from tests.test_tunnel import *
from tests.test_ssh import *
