const fs = require('fs')
const http = require('http');
const { URL } = require('url');
const { utils: { parseKey } } = require('ssh2');
const DEBUG = require('debug')('sshd:proxy');
const jwtEncode = require('jwt-encode');
const localIp = require('local-ip')('eth0');

const JWT_KEY_FILE = process.env.JWT_KEY_FILE || '/run/secrets/shanty_jwt_key';
const PROXY_URL = new URL(process.env.PROXY_URL || 'http://conduit-balancer:1337');
const SHANTY_URL = new URL(process.env.SHANTY_URL || 'http://www.shanty.social');

let JWT_KEY = null;
try {
  JWT_KEY = fs.readFileSync(JWT_KEY_FILE);
} catch (e) {
  console.error('Error reading JWT key from: ', JWT_KEY_FILE);
  console.error(e);
  process.exit(1);
}


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

async function requestJson(options) {
  return new Promise((resolve, reject) => {
    request(options)
      .then((res) => {
        try {
          res.body = JSON.parse(res.body);
        } catch (e) {
          DEBUG('Failure parsing response: %O', res.body);
          reject(e);
          return;
        }
        resolve(res.body);
      })
      .catch((e) => {
        if (e.body) {
          try {
            e.body = JSON.parse(e.body);
          } catch (jsonError) {
            DEBUG('Failure parsing error response: %O', e.body);
          }
        }
        reject(e);
      });
  });
}

function checkKey(ctx) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({
      key: ctx.key.data.toString('base64'),
      type: ctx.key.algo,
    });

    requestJson({
      method: 'post',
      host: SHANTY_URL.hostname,
      port: SHANTY_URL.port,
      path: `/api/sshkeys/${ctx.username}/verify/`,
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

async function verifyDomains(oauthToken, domains) {
  return new Promise((resolve, reject) => {
    requestJson({
      method: 'get',
      host: SHANTY_URL.hostname,
      port: SHANTY_URL.port,
      path: '/api/hosts/',
      headers: {
        Authorization: `Bearer ${oauthToken}`,
      },
    })
      .then((json) => {
        for (const domain of domains) {
          if (!json.find((o) => o.name === domain)) {
            DEBUG('Invalid domain: %s', domain);
            resolve(false);
            return;
          }
        }
        resolve(true);
      })
      .catch(reject);
  });
}

function add({
  username, port, domains, oauthToken,
}) {
  return new Promise((resolve, reject) => {
    if (username === null || port === null || domains === null) {
      resolve(false);
      return;
    }

    verifyDomains(oauthToken, domains)
      .then((r) => {
        if (!r) {
          reject(new Error('Invalid domains'));
          return;
        }

        const body = jwtEncode({
          username,
          domains,
          host: localIp,
          port,
          iat: Date.now() / 1000,
          exp: (Date.now() / 1000) + 30000,
        }, JWT_KEY);

        request({
          method: 'post',
          host: PROXY_URL.hostname,
          port: PROXY_URL.port,
          path: '/add/',
          body,
        })
          .then(() => resolve(true))
          .catch(reject);
      })
      .catch(reject);
  });
}

function del({ username, port, domains }) {
  return new Promise((resolve, reject) => {
    const body = jwtEncode({
      username,
      domains,
      host: localIp,
      port,
      iat: Date.now() / 1000,
      exp: (Date.now() / 1000) + 30000,
    }, JWT_KEY);

    request({
      method: 'post',
      host: PROXY_URL.hostname,
      port: PROXY_URL.port,
      path: '/del/',
      body,
    })
      .then(() => resolve(true))
      .catch(reject);
  });
}

module.exports = {
  add,
  del,
  checkKey,
};
