const { timingSafeEqual } = require('crypto');
const { readFileSync } = require('fs');
const { inspect } = require('util');

const { utils: { parseKey }, Server } = require('ssh2');

const allowedPubKey = parseKey(readFileSync('/etc/sshd/keys/id_rsa.pub'));

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

new Server({
  hostKeys: [readFileSync('host.key')]
}, (client) => {
  console.log('Client connected!');

  client.on('authentication', (ctx) => {
    let userName = ctx.username;
    let allowed = false;

    switch (ctx.method) {
      case 'password':
        return ctx.reject();

      case 'publickey':
        if (ctx.key.algo !== allowedPubKey.type
            || !checkValue(ctx.key.data, allowedPubKey.getPublicSSH())
            || (ctx.signature && allowedPubKey.verify(ctx.blob, ctx.signature) !== true)) {
          return ctx.reject();
        } else {
          allowed = true;
        }
        break;

      default:
        return ctx.reject();
    }

    if (allowed)
      ctx.accept();
    else
      ctx.reject();
  }).on('ready', () => {
    console.log('Client authenticated!');

    client.on('session', (accept, reject) => {
      const session = accept();
      session.once('exec', (accept, reject, info) => {
        console.log('Client wants to execute: ' + inspect(info.command));
        const stream = accept();
        stream.stderr.write('Oh no, the dreaded errors!\n');
        stream.write('Just kidding about the errors!\n');
        stream.exit(0);
        stream.end();
      });
    });
  }).on('close', () => {
    console.log('Client disconnected');
  });
}).listen(0, '127.0.0.1', function() {
  console.log('Listening on port ' + this.address().port);
});

function main() {
  console.log('Starting sshd...');
}

if (require.main === module) {
  main();
}
