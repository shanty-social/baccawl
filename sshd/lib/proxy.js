/* eslint-disable no-bitwise, no-param-reassign, no-plusplus */
const net = require('net');
const { EventEmitter } = require('events');
const DEBUG = require('debug')('sshd:proxy');
const ps = require('proxied-socket');

function createHandler(domains, emitter) {
  return (client) => {
    client.on('error', (e) => DEBUG('Error handling user http request: %O', e));
    client.pause();

    let host;
    try {
      host = client.proxyHeader.tlv.find((o) => o.type === 'UNIQUE_ID').value;
    } catch (e) {
      DEBUG('Error reading unique id: %O', e);
    }

    // get host connection info.
    const info = domains[host];
    if (!info) {
      emitter.emit('invalid', host);
      return;
    }

    // establish connection via tunnel.
    info.client.forwardOut(
      info.bindAddr,
      info.bindPort,
      client.remoteAddress,
      client.remotePort,
      (e, channel) => {
        if (e) {
          DEBUG('Error forwarding: %O', e);
          return;
        }
        // Connect client socket and SSH channel.
        DEBUG('Connecting client<->channel');

        client
          .pipe(channel)
          .pipe(client);

        client.on('end', () => {
          channel.end();
          DEBUG('TCP forwarding closed by client');
        });

        channel.on('end', () => {
          client.end();
          DEBUG('TCP forwarding closed by tunnel');
        });
      }
    );
  };
}

function start(port, host, domains) {
  const emitter = new EventEmitter();
  const handler = createHandler(domains, emitter);
  const s = ps.wrapServer(net.Server(handler), { method: 'override', format: 'proxy-v2' });

  s.listen(port, host, 100, () => {
    const addr = s.address();
    DEBUG('Proxy server listening at %s:%i', addr.address, addr.port);
  });

  return emitter;
}

module.exports = {
  start,
};
