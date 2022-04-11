const net = require('net');
const localIp = require('local-ip')('eth0');
const DEBUG = require('debug')('sshd:announce');

const HAPROXY_HOSTS = (
  process.env.HAPROXY_HOSTS || process.env.HAPROXY_HOST || ''
).split(',');
const HAPROXY_PORT = parseInt(process.env.HAPROXY_PORT || 9999, 10);
const MAP_NAME = process.env.HAPROXY_MAP_NAME || '/usr/local/etc/haproxy/tunnels.map';

async function send(host, port, msg) {
  DEBUG('Sending: %s to %s:%i', msg, host, port);

  return new Promise((resolve, reject) => {
    const c = net.createConnection({ port, host }, () => {
      c.write(msg);
    });
    c.on('error', (e) => DEBUG('Error providing domain list: %O', e));
    c.on('data', (buffer) => {
      // eslint-disable-next-line no-param-reassign
      buffer = buffer.toString().trim();
      DEBUG('Response: %s', buffer);
      c.end();
      if (buffer.includes('not found')) {
        reject(new Error(buffer));
      } else {
        resolve(buffer);
      }
    });
    c.on('error', reject);
  });
}

async function added(domain) {
  for (const host of HAPROXY_HOSTS) {
    // NOTE: haproxy has set and add. Without knowing if a given key exists,
    // we first try to set, then add.
    for (const cmd of ['set', 'add']) {
      try {
        // eslint-disable-next-line no-await-in-loop
        await send(host, HAPROXY_PORT, `${cmd} map ${MAP_NAME} ${domain} ${localIp}\n`);
        DEBUG('Announced domain: %s', domain);
        break;
      } catch (e) {
        DEBUG('Error announcing: %s with %s', domain, cmd);
      }
    }
  }
}

async function removed(domain) {
  for (const host of HAPROXY_HOSTS) {
    try {
      // eslint-disable-next-line no-await-in-loop
      await send(host, HAPROXY_PORT, `del map ${MAP_NAME} ${domain}\n`);
    } catch (e) {
      DEBUG('Error announcing del domain: %s, %O', domain, e);
    }
  }
}

function createHandler(domains) {
  return (s) => {
    const domainList = Object.keys(domains);
    const reply = domainList.join('\n');

    s.on('error', (e) => DEBUG('Poll error: %O', e));

    DEBUG('Sending list of %i domains', domainList.length);
    s.write(reply, (e) => {
      if (e) {
        DEBUG('Poll error: %O', e);
      }
      s.end();
    });
  };
}

function start(port, host, domains) {
  const handler = createHandler(domains);
  const s = net.createServer(handler);

  s.listen(port, host, 100, () => {
    const addr = s.address();
    DEBUG('Announce server listening at %s:%i', addr.address, addr.port);
  });
}

module.exports = {
  added,
  removed,
  start,
};
