#!/usr/local/bin/python3

import os
import logging
import json
import time
from pprint import pformat
from http import client
from urllib.parse import urlparse

from pddns import providers
from pddns.pddns import get_ip


CONSOLE_AUTH_TOKEN = os.getenv('CONSOLE_AUTH_TOKEN')
CONSOLE_URL = os.getenv('CONSOLE_URL')
INTERVAL = int(os.getenv('INTERVAL', '300'))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.StreamHandler())
LOGGER.setLevel(getattr(logging, LOG_LEVEL))

PROVIDERS = {
    'afraid': ('Afraid', providers.Afraid),
    'cloudflare': ('Cloudflare', providers.Cloudflare),
    'hurricane': ('Hurricane Electric', providers.HurricaneElectric),
    'strato': ('Strato', providers.Strato),
}


def request(path, headers=None):
    urlp = urlparse(CONSOLE_URL)
    headers = headers.copy() if headers else {}
    headers.update({
        'Authorization': f'Bearer {CONSOLE_AUTH_TOKEN}',
    })
    c = client.HTTPConnection(urlp.hostname, urlp.port)
    c.request('GET', path, headers=headers)
    r = c.getresponse()
    assert r.status == 200, f'Invalid HTTP status {r.status}'
    return json.loads(r.read().decode())['objects']


def get_clients():
    clients, domains = [], request('/api/domains/')
    for domain in domains:
        try:
            config = {}
            config_name, klass = PROVIDERS[domain['provider']]
            options = config[config_name] = domain['options']
            options['Name'] = domain['name']
#            if 'nameservers' in domain:
#                options['Nameservers'] = domain['Nameservers']
            clients.append((domain['name'], klass(config, "v2.1.0")))

        except Exception:
            LOGGER.exception('Error initializing client: %s', pformat(domain))

    return clients


def main():
    LOGGER.info('Starting dyndns client.')
    while True:
        try:
            for domain, client in get_clients():
                LOGGER.info(
                    'Updating: %s, provider=%s', domain,
                    client.__class__.__name__)
                client.main(get_ip(), None)

        except Exception:
            LOGGER.exception('Error updating dns records.')
            pass

        LOGGER.info('Slumbering for %i seconds...', INTERVAL)
        time.sleep(INTERVAL)


if __name__ == '__main__':
    main()
