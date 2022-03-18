const net = require('net');
const localIp = require('local-ip')('eth0');
const DEBUG = require('debug')('sshd:announce');

const HAPROXY_HOSTS = (process.env.HAPROXY_HOSTS || '')
  .split(',')
  .map((v) => v.split(':'));
const MAP_NAME = process.env.HAPROXY_MAP_NAME || '/usr/local/etc/haproxy/tunnels.map';

async function send(host, port, msg) {
  return new Promise((resolve, reject) => {
    const c = net.createConnection({ port, host }, () => {
      c.write(msg);
    });
    c.on('data', (buffer) => {
      c.end();
      DEBUG('Announce response: %s', buffer);
      resolve(buffer);
    })
    c.on('error', reject);
  });
}

function added(domain) {
  for (const [host, port] of HAPROXY_HOSTS) {
    send(host, port, `set map ${MAP_NAME} ${domain} ${localIp}\n`)
      .then(() => DEBUG('Announced add %s:%i, domain: %s', host, port, domain))
      .catch((e) => {
        DEBUG('Error announcing add %s:%i, domain: %s', host, port, domain)
        DEBUG('%O', e);
      });
  }
}

async function removed(domain) {
  for (const [host, port] of HAPROXY_HOSTS) {
    send(host, port, `del map ${MAP_NAME} ${domain}\n`)
      .then(() => DEBUG('Announced del %s:%i, domain: %s', host, port, domain))
      .catch((e) => {
        DEBUG('Error announcing del %s:%i, domain: %s', host, port, domain)
        DEBUG('%O', e);
      });
  }
}

function createHandler(domains) {
  return (s) => {
    const reply = Object.keys(domains).join('\n');

    s.send(reply, (e) => {
      if (e) {
        DEBUG('Poll error: %O', e);
      }
      s.close();
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
  start
};
