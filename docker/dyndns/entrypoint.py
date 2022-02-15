#!/usr/local/bin/python3

import os
import logging
import json
import time
import signal
from pprint import pformat
from http import client
from urllib.parse import urlparse

from pddns import providers
from pddns.pddns import get_ip


CACHE_PATH = os.getenv('CACHE_PATH', '/var/lib/dyndns.cache')
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
# NOTE: lifted from source code.
# TODO: refactor this library so version can be imported.
PDDNS_VERSION = "v2.1.0"


def _load_cache():
    if os.path.getsize(CACHE_PATH) == 0:
        return {}

    LOGGER.info('Loading cache')
    try:
        with open(CACHE_PATH, 'r') as f:
            cache = json.load(f)
        LOGGER.debug('Loaded %i items from cache', len(cache))
        return cache

    except Exception:
        LOGGER.exception('Error loading cache')
        return {}


def _save_cache(*args):
    LOGGER.info('Saving cache')
    try:
        with open(CACHE_PATH, 'w') as f:
            json.dump(IP_CACHE, f)

    except Exception:
        LOGGER.exception('Error saving cache')

    finally:
        exit(0)


IP_CACHE = _load_cache()


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


def update_dns(ip):
    try:
        domains = request('/api/domains/')

    except Exception:
        LOGGER.exception('Error getting domain list')
        return

    for domain in domains:
        config = {}
        try:
            provider = domain['provider']
            config_name, klass = PROVIDERS[provider]
            options = config[config_name] = domain['options']
            domain_name = options['Name'] = domain['name']
#            if 'nameservers' in domain:
#                options['Nameservers'] = domain['Nameservers']

        except Exception:
            LOGGER.exception('Error initializing client: %s', pformat(domain))
            continue

        if ip == IP_CACHE.get(domain_name):
            # If the ip has not changed since last run, don't update it.
            LOGGER.debug(
                'Skipping: %s, provider=%s, no ip change',
                domain_name, provider)
            continue

        LOGGER.info(
            'Updating: %s, provider=%s', domain_name, provider)
        try:
            # NOTE: if ip address is defined, it is a static record, use that
            # ip rather than the detected one.
            client_ip = options.get('ip address') or ip
            klass(config, PDDNS_VERSION).main(client_ip, None)
            IP_CACHE[domain_name] = ip

        except Exception:
            LOGGER.exception('Error updating ip.')
            continue


def main():
    signal.signal(signal.SIGTERM, _save_cache)
    LOGGER.info('Starting dyndns client.')
    while True:
        update_dns(get_ip())

        LOGGER.info('Slumbering for %i seconds...', INTERVAL)
        time.sleep(INTERVAL)


if __name__ == '__main__':
    main()
