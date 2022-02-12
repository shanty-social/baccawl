const http = require('http');
const { URL } = require('url');
const DEBUG = require('debug')('sshd:proxy');
const jwtEncode = require('jwt-encode');
const localIp = require('local-ip')('eth0');

const JWT_KEY = process.env.JWT_KEY;
const PROXY_URL = new URL(process.env.PROXY_URL || 'http://conduit-balancer:1337');

function add(username, port, domains) {
  // NOTE: Need to validate the domains for the user.
  return new Promise((resolve, reject) => {
    if (username === null || port === null || domains === null) {
      resolve(false);
      return;
    }
    const req = http.request({
      method: 'post',
      host: PROXY_URL.hostname,
      port: PROXY_URL.port,
      path: '/add/',
    }, (res) => {
      if (res.statusCode !== 200) {
        reject(new Error(`Proxy checkin failed, statusCode: ${res.statusCode}`));
        return;
      }
      resolve(port);
    });

    req.on('error', (e) => {
      reject(e);
    });

    // TODO: make it expire in 30s
    const jwt = jwtEncode({
      username,
      domains,
      host: localIp,
      port: port,
      iat: Date.now() / 1000,
      exp: (Date.now() / 1000) + 30000,
    }, JWT_KEY);

    req.write(jwt);
    req.end();
  });
}

function del(username, port, domains) {
  return new Promise((resolve, reject) => {
    const req = http.request({
      method: 'post',
      host: PROXY_URL.hostname,
      port: PROXY_URL.port,
      path: '/del/',
    }, (res) => {
      if (res.statusCode !== 200) {
        DEBUG('Proxy checkout failed');
        reject(new Error('!200 status code'));
        return;
      }
      DEBUG('Proxy checkout successful');
      resolve(port);
    });

    req.on('error', (e) => {
      DEBUG('Proxy checkout error: %O', e);
      reject(e);
    });

    const jwt = jwtEncode({
      username,
      domains,
      host: localIp,
      port: port,
      iat: Date.now() / 1000,
      exp: (Date.now() / 1000) + 30000,
    }, JWT_KEY);

    req.write(jwt);
    req.end();
  });
}

module.exports = {
  add,
  del,
}
