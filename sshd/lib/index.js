const fs = require('fs');
const pathlib = require('path');
const net = require('net');
const { readFileSync } = require('fs');
const { Server } = require('ssh2');
const DEBUG = require('debug')('sshd');
const api = require('./client');

const KEY_DIR = process.env.SSHD_HOST_KEY_DIR;
const HOST = process.env.SSHD_HOST || '127.0.0.1';
const PORT = parseInt(process.env.SSHD_PORT || 22, 10);

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

function start(host, port) {
  const server = new Server({
    hostKeys: readServerKeys(),
  });

  server.on('connection', (client) => {
    const auth = {
      username: null,
      oauthToken: null,
      domains: null,
      port: null,
      checkedIn: false,
    };

    DEBUG('Client connected!');
    client.on('authentication', (ctx) => {
      DEBUG('Authenticating with %s', ctx.method);

      switch (ctx.method) {
        case 'password':
          DEBUG('Rejecting password');
          ctx.reject(['publickey']);
          break;

        case 'publickey':
          api
            .checkKey(ctx)
            .then(() => {
              DEBUG('Accepting key');
              auth.username = ctx.username;
              ctx.accept();
            })
            .catch((e) => {
              DEBUG('Rejecting key: %O', e);
              ctx.reject();
            });
          break;

        default:
          ctx.reject(['publickey']);
      }
    });

    client.on('ready', () => {
      DEBUG('Client authenticated!');
    });

    client.on('request', (accept, reject, name, info) => {
      if (auth.checkedIn) {
        reject();
        return;
      }
      const { bindAddr, bindPort } = info;

      DEBUG('Received request: %s, %O', name, info);

      if (name !== 'tcpip-forward' || bindPort !== 0) {
        DEBUG('Request rejected');
        reject();
        client.end();
        return;
      }

      DEBUG('TCP forwarding request received');

      const proxy = net.createServer((c) => {
        DEBUG('TCP connection received, forwarding');
        const addr = c.address();
        client.forwardOut(bindAddr, bindPort, addr.address, addr.port, (e, channel) => {
          if (e) {
            DEBUG('Error forwarding: %O', e);
            return;
          }
          // Connect client socket and SSH channel.
          DEBUG('Connecting socket<->channel');
          c.pipe(channel);
          channel.pipe(c);

          channel.on('end', () => {
            DEBUG('TCP forwarding complete');
          });
        });
      }).listen(bindPort, bindAddr, () => {
        auth.port = proxy.address().port;
        DEBUG('Listening at: %s:%i', bindAddr, auth.port);
        api
          .add(auth)
          .then((r) => {
            auth.checkedIn = r;
            accept(auth.port);
          })
          .catch((e) => {
            DEBUG('Error checking in: %O', e);
            reject();
            client.end();
          });
      });
    });

    client.on('session', (accept, reject) => {
      if (auth.checkedIn) {
        DEBUG('Rejecting session');
        reject();
        return;
      }

      DEBUG('Accepting session');
      const session = accept();
      session.on('exec', (_, __, info) => {
        const cmdParts = info.command.split(' ');
        if (!cmdParts[0] === 'proxy') {
          DEBUG('Rejecting command %s', info.command);
          return;
        }

        DEBUG('Accepting command %s', info.command);
        // eslint-disable-next-line prefer-destructuring
        auth.oauthToken = cmdParts[1];
        auth.domains = cmdParts.slice(2);
        api
          .add(auth)
          .then((r) => {
            auth.checkedIn = r;
          })
          .catch((e) => {
            DEBUG('Error registering with proxy: %O', e);
            client.end();
          });
      });
    });

    client.on('end', () => {
      if (auth.checkedIn) {
        api
          .del(auth)
          .then(() => DEBUG('Deregistered from proxy'))
          .catch((e) => {
            DEBUG('Error deregistering with proxy: %O', e);
          });
      }
    });

    client.on('error', (e) => {
      DEBUG('Client error: %O', e);
      client.end();
    });

    client.on('close', () => {
      DEBUG('Client disconnected');
    });
  });

  server.listen(port, host, () => {
    const addr = server.address();
    console.log(`Listening at ${addr.address}:${addr.port}`);
  });

  console.log('Starting sshd...');
  return server;
}

if (require.main === module) {
  start(HOST, PORT);
}

module.exports = {
  start,
};
