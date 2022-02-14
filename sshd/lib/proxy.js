const http = require('http');
const { URL } = require('url');
const DEBUG = require('debug')('sshd:proxy');
const jwtEncode = require('jwt-encode');
const localIp = require('local-ip')('eth0');
const keys = require('./keys');

const JWT_KEY = process.env.JWT_KEY;
const PROXY_URL = new URL(process.env.PROXY_URL || 'http://conduit-balancer:1337');

async function verifyDomains(oauthToken, domains) {
  return new Promise((resolve) => {
    keys.getDomains(oauthToken)
    .then((hosts) => {
      DEBUG('Domains: %O', domains);
      for (const domain of domains) {
        if (!hosts.find(o => o.name == domain)) {
          DEBUG('Invalid domain: %s', domain);
          resolve(false);
          return;
        }
      }
      resolve(true);
    })
    .catch((e) => {
      DEBUG('Error fetching domains: %O', e);
      resolve(false);
    })
  });
}

function add({username, port, domains, oauthToken}) {
  return new Promise(async (resolve, reject) => {
    if (username === null || port === null || domains === null) {
      resolve(false);
      return;
    }

    const validDomains = await verifyDomains(oauthToken, domains);
    if (!validDomains) {
      reject(new Error('Invalid domains'));
      return;
    }

    const req = http.request({
      method: 'post',
      host: PROXY_URL.hostname,
      port: PROXY_URL.port,
      path: '/add/',
      headers: {
        'Authorization': `Bearer ${oauthToken}`,
      }
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

function del({username, port, domains}) {
  return new Promise((resolve, reject) => {
    const req = http.request({
      method: 'post',
      host: PROXY_URL.hostname,
      port: PROXY_URL.port,
      path: '/del/',
    }, (res) => {
      if (res.statusCode !== 200) {
        DEBUG('Proxy checkout failed');
        resolve();
        return;
      }
      DEBUG('Proxy checkout successful');
      resolve();
    });

    req.on('error', (e) => {
      DEBUG('Proxy checkout error: %O', e);
      resolve();
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
