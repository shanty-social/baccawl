/* eslint-disable no-bitwise, no-param-reassign, no-plusplus */
const net = require('net');
const { EventEmitter } = require('events');
const DEBUG = require('debug')('sshd:proxy');
const ps = require('proxied-socket');

function createHandler(domains, emitter) {
  return (client) => {
    client.pause();

    let host;
    try {
      host = client.proxyHeader.tlv.find((o) => o.type === 'UNIQUE_ID').value;
    } catch (e) {
      DEBUG('Error reading unique id: %O', e);
      return;
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
        let sent = 0;
        // Connect client socket and SSH channel.
        DEBUG('Connecting client<->channel');

        client
          .pipe(channel)
          .pipe(client);

        client.once('data', (buffer) => {
          DEBUG('Received from client: %s', buffer);
        });

        channel.on('data', (buffer) => {
          sent += buffer.length;
        });

        client.on('end', () => {
          DEBUG('client closed');
        });

        channel.on('end', () => {
          DEBUG('tunnel closed, sent %i bytes', sent);
        });
      }
    );
  };
}

function start(port, host, domains) {
  const emitter = new EventEmitter();
  const handler = createHandler(domains, emitter);
  const server = ps.wrapServer(net.Server(handler), {
    method: 'override',
    format: 'proxy-v2',
  });

  server.listen(port, host, 100, () => {
    const addr = server.address();
    DEBUG('Proxy server listening at %s:%i', addr.address, addr.port);
  });

  return emitter;
}

module.exports = {
  start,
};
