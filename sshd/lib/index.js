const DEBUG = require('debug')('sshd');
const { start: startProxy } = require('./proxy');
const { start: startSSH } = require('./server');
const { added, removed, start: startAnnounce } = require('./announce');

const PROXY_HOST = process.env.PROXY_HOST || '0.0.0.0';
const PROXY_PORT = parseInt(process.env.PROXY_PORT || 80, 10);
const SSHD_HOST = process.env.SSHD_HOST || '0.0.0.0';
const SSHD_PORT = parseInt(process.env.SSHD_PORT || 22, 10);
const ANNOUNCE_HOST = process.env.ANNOUNCE_HOST || '0.0.0.0';
const ANNOUNCE_PORT = parseInt(process.env.ANNOUNCE_PORT || 1337, 10);

function main() {
  DEBUG('Starting up');

  const domains = {};
  const sshd = startSSH(SSHD_PORT, SSHD_HOST);
  const proxy = startProxy(PROXY_PORT, PROXY_HOST, domains);
  startAnnounce(ANNOUNCE_PORT, ANNOUNCE_HOST, domains);

  sshd
    .on('tunnel:open', async (info) => {
      domains[info.domain] = info;
      await added(info.domain);
    })
    .on('tunnel:close', async (info) => {
      delete domains[info.domain];
      await removed(info.domain);
    });

  proxy.on('invalid', async (domain) => {
    await removed(domain);
  });
}

if (require.main === module) {
  main();
}
