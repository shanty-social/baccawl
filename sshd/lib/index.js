const fs = require('fs');
const pathlib = require('path');
const net = require('net');
const { readFileSync } = require('fs');
const { Server } = require('ssh2');
const DEBUG = require('debug')('sshd');
const proxy = require('./proxy');
const keys = require('./keys');

const KEY_DIR = process.env.SSHD_HOST_KEY_DIR;
const HOST = process.env.SSHD_HOST || '127.0.0.1';
const PORT = parseInt(process.env.SSHD_PORT | 22);

function readServerKeys() {
  const keys = [];
  const paths = fs.readdirSync(KEY_DIR);

  for (const path of paths) {
    if (!path.startsWith('ssh_host') || path.endsWith('.pub')) {
      DEBUG('Skipping non-key file %s', path);
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
    let username = null;

    DEBUG('Client connected!');
    client.on('authentication', (ctx) => {
      DEBUG('Authenticating with %s', ctx.method);

      switch (ctx.method) {
        case 'password':
          DEBUG('Rejecting password');
          return ctx.reject(['publickey']);
  
        case 'publickey':
          keys
            .checkKey(ctx)
            .then(() => {
              DEBUG('Accepting key');
              username = ctx.username;
              ctx.accept();
            })
            .catch((e) => {
              DEBUG('Rejecting key: %O', e)
              return ctx.reject();
            });
          break;
  
        default:
          return ctx.reject(['publickey']);
      }
    });

    client.on('ready', () => {
      DEBUG('Client authenticated!');
    })

    client.on('request', (accept, reject, name, info) => {
      let { bindAddr, bindPort } = info;

      DEBUG('Received request: %s, %O', name, info);

      if (name !== 'tcpip-forward' || bindPort !== 0) {
        DEBUG('Request rejected');
        reject();
        client.end();
        return;
      }

      DEBUG('TCP forwarding request received');

      const server = net.createServer((c) => {
        DEBUG('TCP connection received, forwarding');
        const addr = c.address();
        client.forwardOut(bindAddr, bindPort, addr.address, addr.port, (e, channel) => {
          if (e) {
            DEBUG('Error forwarding: %O', e);
            //client.end();
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
        const port = server.address().port;
        DEBUG('Listening at: %s:%i', bindAddr, port);

        DEBUG('Registering with proxy');
        proxy
          .add(username, port)
          .then(() => {
            client.on('end', () => {
              proxy
                .del(username, port)
                .then(() => DEBUG('Deregistered from proxy'));
            });
            accept(port);
          })
          .catch((e) => {
            DEBUG('Error registering with proxy: %O', e);
            reject();
            client.end();
          });
      });
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
