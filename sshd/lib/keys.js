const http = require('http');
const { utils: { parseKey } } = require('ssh2');
const { URL } = require('url');

const SHANTY_URL = new URL(process.env.SHANTY_URL || 'http://www.shanty.social');

function checkKey(ctx) {
    return new Promise((resolve, reject) => {
      const postData = JSON.stringify({
        key: ctx.key.data.toString('base64'),
        type: ctx.key.algo,
      });
      // TODO: The same key is passed to us twice. Once to verify the key,
      // then again to verify the signature. We could cache the result of
      // this API call in order to eliminate one call.
      const req = http.request({
        method: 'post',
        host: SHANTY_URL.hostname,
        port: SHANTY_URL.port,
        path: `/api/sshkeys/${ctx.username}/verify/`,
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': postData.length,
        },
      }, (res) => {
        if (res.statusCode !== 200) {
          reject(new Error(`Key verification failed, statusCode: ${res.statusCode}`));
          return;
        }

        if (ctx.signature) {
          const key = parseKey(ctx.key.data);
          if (key.verify(ctx.blob, ctx.signature) !== true) {
            reject(new Error('Signature verification failed'));
            return;
          }
        }

        resolve();
      });
  
      req.on('error', (e) => {
        reject(e);
      });
  
      req.write(postData);
      req.end();
    });
}

module.exports = {
    checkKey,
}
