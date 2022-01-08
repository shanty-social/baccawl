const fs = require('fs');
const pathlib = require('path');
const { timingSafeEqual } = require('crypto');
const { readFileSync } = require('fs');
const { inspect } = require('util');
const DEBUG = require('debug')('sshd');

const { utils: { parseKey }, Server } = require('ssh2');

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
    DEBUG('Client connected!');

    client.on('authentication', (ctx) => {
      let userName = ctx.username;
  
      switch (ctx.method) {
        case 'password':
          return ctx.reject();
  
        case 'publickey':
          // TODO: make http call to auth server with username and key info.
          if (ctx.key.algo !== allowedPubKey.type
              || !checkValue(ctx.key.data, allowedPubKey.getPublicSSH())
              || (ctx.signature && allowedPubKey.verify(ctx.blob, ctx.signature) !== true)) {
            return ctx.reject();
          } else {
            ctx.accept();
          }
          break;
  
        default:
          return ctx.reject();
      }
    });

    client.on('ready', () => {
      DEBUG('Client authenticated!');
    })

    client.on('session', (accept, reject) => {
      const session = accept();
      session.once('exec', (accept, reject, info) => {
        DEBUG('Client wants to execute: ' + inspect(info.command));
        const stream = accept();
        stream.stderr.write('Oh no, the dreaded errors!\n');
        stream.write('Just kidding about the errors!\n');
        stream.exit(0);
        stream.end();
      });
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
