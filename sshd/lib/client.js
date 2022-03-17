const fs = require('fs');
const http = require('http');
const { URL } = require('url');
const { utils: { parseKey } } = require('ssh2');
const { createClient } = require('redis');
const DEBUG = require('debug')('sshd:proxy');
const localIp = require('local-ip')('eth0');

const REDIS_KEY = process.env.REDIS_KEY || 'sshd:endpoints';
const REDIS_HOST = process.env.REDIS_HOST || 'redis';
const REDIS_PORT = parseInt(process.env.REDIS_PORT || 6379, 10);
const SHANTY_URL = new URL(process.env.SHANTY_URL || 'http://www.shanty.social');

const REDIS = createClient({url: `redis://${REDIS_HOST}:${REDIS_PORT}`});
REDIS.connect();

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

    request({
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

async function verifyDomains(username, domain) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({
      uuid: username,
      domain,
    });
    request({
      method: 'post',
      host: SHANTY_URL.hostname,
      port: SHANTY_URL.port,
      path: '/api/hosts/verify/',
      body,
      headers: {
        'Content-Type': 'application/json',
      },
    })
      .then(() => resolve(true))
      .catch(reject);
  });
}

function add({ username, domain, port }) {
  return new Promise((resolve, reject) => {
    if (username === null || domain === null || port === null) {
      resolve(false);
      return;
    }

    verifyDomains(username, domain)
      .then((r) => {
        if (!r) {
          reject(new Error('Invalid domain'));
          return;
        }

        const endpoint = `${localIp}:${port}`;
        REDIS
          .hSet(REDIS_KEY, domain, endpoint)
          .then(() => resolve(true))
          .catch(reject)
      })
      .catch(reject);
  });
}

function del(domain) {
  return new Promise((resolve, reject) => {
    REDIS
      .hDel(REDIS_KEY, domain)
      .then(() => resolve(true))
      .catch(reject)
  });
}

module.exports = {
  add,
  del,
  checkKey,
};
