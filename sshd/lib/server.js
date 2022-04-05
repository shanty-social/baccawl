const fs = require('fs');
const pathlib = require('path');
const { readFileSync } = require('fs');
const { EventEmitter } = require('events');
const { Server } = require('ssh2');
const DEBUG = require('debug')('sshd:server');
const ps = require('proxied-socket');
const { verifyDomain, checkKey } = require('./client');

const KEY_DIR = process.env.SSHD_HOST_KEY_DIR;

function readServerKeys() {
  const keys = [];
  const paths = fs.readdirSync(KEY_DIR);

  for (const path of paths) {
    if (!path.startsWith('ssh_host') || path.endsWith('.pub')) {
      DEBUG('Skipping non-key file %s', path);
      // eslint-disable-next-line no-continue
      continue;
    }
    DEBUG('Loading key %s', path);
    keys.push(readFileSync(pathlib.join(KEY_DIR, path)));
  }

  return keys;
}

function clientAuthenticationHandler(ctx, clientInfo) {
  DEBUG('Authenticating with %s', ctx.method);

  switch (ctx.method) {
    case 'password':
      DEBUG('Rejecting password');
      ctx.reject(['publickey']);
      break;

    case 'publickey':
      checkKey(ctx)
        .then(() => {
          DEBUG('Accepting key');
          // eslint-disable-next-line no-param-reassign
          clientInfo.username = ctx.username;
          ctx.accept();
        })
        .catch((e) => {
          DEBUG('Rejecting key: %O', e);
          ctx.reject(['publickey']);
        });
      break;

    default:
      ctx.reject(['publickey']);
  }
}

function clientPortRequestHandler(ctx, emitter, clientInfo) {
  DEBUG('Received request: %s, %O', ctx.name, ctx.info);

  const { info } = ctx;
  let { bindPort } = info;

  if (ctx.name === 'tcpip-forward' && bindPort === 0) {
    DEBUG('TCP forwarding request received');

    // Client needs a port between 1 and 65534. We use it only to match up the
    // exec request that we expect to come directly.
    bindPort = Math.round(Math.random() * 65533) + 1;
    clientInfo.tunnels.push({
      bindAddr: info.bindAddr,
      bindPort,
      client: ctx.client,
      domain: null,
    });

    ctx.accept(bindPort);
  } else if (ctx.name === 'cancel-tcpip-forward' && bindPort) {
    DEBUG('TCP forwarding cancellation request received');

    const i = clientInfo.tunnels.findIndex((o) => o.bindPort === bindPort);
    if (i === -1) {
      DEBUG('Request %s rejected, invalid bindPort: %i', bindPort);
      ctx.reject();
      return;
    }
    const tunnelInfo = clientInfo.tunnels.splice(i, 1)[0];
    emitter.emit('tunnel:close', tunnelInfo);
    ctx.accept();
  } else {
    DEBUG('Request %s rejected, bindPort: %i', ctx.name, bindPort);
    ctx.reject();
  }
}

function clientSessionHandler(accept, reject, emitter, clientInfo) {
  DEBUG('Accepting session');
  const session = accept();

  session.on('error', (e) => DEBUG('Error in session: %O', e));
  session.on('exec', (acceptCommand, rejectCommand, info) => {
    const cmdParts = info.command.split(' ');

    if (!cmdParts[0] === 'tunnel') {
      DEBUG('Rejecting command %s', info.command);
      rejectCommand();
      return;
    }

    let bindPort;
    let tunnelInfo;
    try {
      bindPort = parseInt(cmdParts[2], 10);
      DEBUG('Looking up tunnel with bindPort: %i', bindPort);
      tunnelInfo = clientInfo.tunnels.find((o) => o.bindPort === bindPort);
    } catch (e) {
      DEBUG('Command format error: %O', e);
      rejectCommand();
      return;
    }

    if (!tunnelInfo) {
      DEBUG('Invalid port, no tunnel');
      rejectCommand();
      return;
    }

    const domain = cmdParts[1];
    verifyDomain(clientInfo.username, domain)
      .then(() => {
        DEBUG('Accepting command %s', info.command);
        tunnelInfo.domain = domain;
        emitter.emit('tunnel:open', tunnelInfo);
        acceptCommand();
      })
      .catch((e) => {
        DEBUG('Invalid domain: %s, %s', clientInfo.username, domain);
        DEBUG('%O', e);
        rejectCommand();
      });
  });
}

function clientEndHandler(emitter, clientInfo) {
  if (!clientInfo.tunnels || !clientInfo.tunnels.length) {
    return;
  }

  for (const tunnelInfo of clientInfo.tunnels) {
    try {
      emitter.emit('tunnel:close', tunnelInfo);
    } catch (e) {
      DEBUG('Error in tunnel:close handler: %O', e);
    }
  }
}

function createConnectionHandler(emitter) {
  return (client) => {
    DEBUG('Client connected!');

    const clientInfo = {
      username: null,
      tunnels: [],
    };

    client
      .on('authentication', (ctx) => {
        clientAuthenticationHandler(ctx, clientInfo);
      })
      .on('ready', () => DEBUG('Client authenticated!'))
      .on('request', (accept, reject, name, info) => {
        clientPortRequestHandler({
          accept, reject, name, info, client,
        }, emitter, clientInfo);
      })
      .on('session', (accept, reject) => {
        clientSessionHandler(accept, reject, emitter, clientInfo);
      })
      .on('end', () => clientEndHandler(emitter, clientInfo))
      .on('error', (e) => {
        DEBUG('Client error: %O', e);
        client.end();
      })
      .on('close', () => DEBUG('Client disconnected'));
  };
}

function start(port, host) {
  const emitter = new EventEmitter();
  const handler = createConnectionHandler(emitter);

  const server = new Server({
    hostKeys: readServerKeys(),
  });

  server._srv = ps.wrapServer(server._srv, {
    method: 'override',
    format: 'proxy-v2',
  });

  server
    .on('connection', handler)
    .listen(port, host, () => {
      const addr = server.address();
      DEBUG('SSH server listening at %s:%i', addr.address, addr.port);
    });

  return emitter;
}

module.exports = {
  start,
};
