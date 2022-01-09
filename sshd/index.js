const fs = require('fs');
const pathlib = require('path');
const net = require('net');
const http = require('http');
const jwtEncode = require('jwt-encode');
const { timingSafeEqual } = require('crypto');
const { readFileSync } = require('fs');
const DEBUG = require('debug')('sshd');
const localIp = require('local-ip')('eth0');

const { utils: { parseKey }, Server } = require('ssh2');

const KEY_DIR = process.env.SSHD_HOST_KEY_DIR;
const HOST = process.env.SSHD_HOST || '127.0.0.1';
const PORT = parseInt(process.env.SSHD_PORT | 22);
const SSH_KEY = process.env.SSH_KEY;
const SECRET_KEY = process.env.SECRET_KEY;

const ALLOWED_PUB_KEY = parseKey(readFileSync(SSH_KEY));

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

function checkValue(input, allowed) {
  const autoReject = (input.length !== allowed.length);
  if (autoReject) {
    // Prevent leaking length information by always making a comparison with the
    // same input when lengths don't match what we expect ...
    allowed = input;
  }
  const isMatch = timingSafeEqual(input, allowed);
  return (!autoReject && isMatch);
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
          // TODO: make http call to auth server with username and key info.
          if (ctx.key.algo !== ALLOWED_PUB_KEY.type
              || !checkValue(ctx.key.data, ALLOWED_PUB_KEY.getPublicSSH())
              || (ctx.signature && ALLOWED_PUB_KEY.verify(ctx.blob, ctx.signature) !== true)) {
            DEBUG('Rejecting key')
            return ctx.reject();
          } else {
            DEBUG('Accepting key');
            username = ctx.username;
            ctx.accept();
          }
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
            client.end();
            return;
          }
          // Connect client socket and SSH channel.
          DEBUG('Connecting socket<->channel');
          c.pipe(channel);
          channel.pipe(c);
        });
      }).listen(bindPort, bindAddr, () => {
        bindPort = server.address().port;
        DEBUG('Listening at: %s:%i', bindAddr, bindPort);

        // Advertise to proxy.
        const req = http.request({
          method: 'post',
          host: 'proxy',
          path: '/local/add/',
        }, (res) => {
          if (res.statusCode !== 200) {
            DEBUG('Proxy checkin failed');
            reject();
            client.end();
          } else {
            DEBUG('Proxy checkin successful');
            accept(bindPort);  
          }
        });

        req.on('error', (e) => {
          DEBUG('Proxy checkin error: %O', e);
          reject();
          client.end();
        });

        // TODO: make it expire in 30s
        const jwt = jwtEncode({
          username,
          host: localIp,
          port: bindPort,
          iat: Date.now(),
        }, SECRET_KEY);

        req.write(jwt);
        req.end();  
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
