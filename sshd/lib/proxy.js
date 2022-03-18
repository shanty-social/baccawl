const net = require('net');
const { EventEmitter } = require('events');
const DEBUG = require('debug')('sshd:proxy');

function createHandler(domains, emitter) {
  return (c) => {
    // read proxy information, including desired host.
    const host = null;
    const addr = c.address();

    // get host connection info.
    const info = domains[host];
    if (!info) {
      emitter.emit('invalid', host);
      return;
    }

    // establish connection via tunnel.
    const { client, bindAddr, bindPort } = info;
    client.forwardOut(bindAddr, bindPort, addr.address, addr.port, (e, channel) => {
      if (e) {
        DEBUG('Error forwarding: %O', e);
        return;
      }
      // Connect client socket and SSH channel.
      DEBUG('Connecting client<->channel');
      c
        .pipe(channel)
        .pipe(c);

      c.on('end', () => {
        channel.end();
        DEBUG('TCP forwarding closed by client');
      });
      channel.on('end', () => {
        c.end();
        DEBUG('TCP forwarding closed by tunnel');
      });
    });
  };
}

function start(port, addr, domains) {
  const emitter = new EventEmitter();
  const handler = createHandler(domains, emitter);
  const s = net.createServer(handler);

  s.listen(port, addr, 100, () => {
    const addr = s.address();
    DEBUG('Proxy server listening at %s:%i', addr.address, addr.port);
  });

  return emitter;
}

module.exports = {
  start,
};
