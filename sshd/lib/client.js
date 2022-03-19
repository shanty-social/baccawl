const http = require('http');
const { URL } = require('url');
const { utils: { parseKey } } = require('ssh2');
const DEBUG = require('debug')('sshd:client');

const SHANTY_URL = new URL(process.env.SHANTY_URL || 'http://www.shanty.social');

async function request(options) {
  return new Promise((resolve, reject) => {
    // eslint-disable-next-line no-param-reassign
    options.method = options.method || 'get';

    DEBUG('request options: %O', options);

    const req = http.request({
      method: options.method,
      host: options.host,
      port: options.port,
      path: options.path,
      headers: options.headers,
    }, (res) => {
      let buffer = '';

      res.on('data', (chunk) => {
        DEBUG('Received chunk: %s', chunk.toString());
        buffer += chunk.toString();
      });

      res.on('end', () => {
        if (res.statusCode < 200 || res.statusCode > 299) {
          const e = new Error('Request failed');
          e.statusCode = res.statusCode;
          e.body = buffer;
          e.res = res;
          reject(e);
          return;
        }
        res.body = buffer;
        resolve(res);
      });
    });

    req.on('error', (e) => {
      reject(e);
    });

    if (['post', 'put'].includes(options.method) && options.body) {
      DEBUG('Writing body for %s request', options.method);
      req.write(options.body);
    }

    req.end();
  });
}

function checkKey(ctx) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({
      key: ctx.key.data.toString('base64'),
      type: ctx.key.algo,
    });

    request({
      method: 'post',
      host: SHANTY_URL.hostname,
      port: SHANTY_URL.port,
      path: `/api/consoles/${ctx.username}/verify_key/`,
      body,
      headers: {
        'Content-Type': 'application/json',
      },
    })
      .then(() => {
        if (ctx.signature) {
          const key = parseKey(ctx.key.data);
          if (key.verify(ctx.blob, ctx.signature) !== true) {
            reject(new Error('Signature verification failed'));
            return;
          }
        }
        resolve();
      })
      .catch(reject);
  });
}

async function verifyDomain(username, domain) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({
      domain,
    });
    request({
      method: 'post',
      host: SHANTY_URL.hostname,
      port: SHANTY_URL.port,
      path: `/api/consoles/${username}/verify_host/`,
      body,
      headers: {
        'Content-Type': 'application/json',
      },
    })
      .then(() => resolve(true))
      .catch(reject);
  });
}

module.exports = {
  checkKey,
  verifyDomain,
};
