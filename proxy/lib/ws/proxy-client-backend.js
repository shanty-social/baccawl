const EventEmitter = require('events');
const { URL } = require('url');
const debug = require('debug')('baccawl:server:backend');
const ProxiedRequest = require('./proxied-request');
const ProxiedWebSocket = require('./proxied-web-socket');

class ProxyClientBackend extends EventEmitter {
  constructor(req, ws) {
    super();
    const url = new URL(req.url, `http://${req.headers.host}`);
    const parts = url.hostname.split('.');
    this.id = parts[0];
    this.tunnelWs = ws;
    this.requests = {}
    this.tunnelWs
      .on('message', this.onMessage.bind(this))
      .on('close', this.destroy.bind(this));
  }

  onMessage(json) {
    // Could be a reply for a proxied http request or websocket. Both are represented
    // by a class with the same interface, each one has a unique ID, so located the
    // object and pass it the message.
    json = JSON.parse(json);
    const request = this.requests[json.id];
    if (!request) {
      debug('Unknown request id: %s', json.id);
      return;
    }
    request.recv(json);
  }

  startSocket(url, ws, head) {
    const pSock = new ProxiedWebSocket({
      tunnelWs: this.tunnelWs,
      clientWs: ws,
      connected: true,
    });
    const json = {
      id: pSock.id,
      socket: {
          url: {
            pathname: url.pathname,
            search: url.search,
            host: url.host,
            port: url.port,
            protocol: 'ws:',  // url.protocol,
            username: url.username,
            password: url.password,
          },
          headers: head,
      },
    };
    debug('Initiating socket: %O', json);
    this.tunnelWs.send(JSON.stringify(json));
    this.requests[pSock.id] = pSock;
    pSock.on('close', () => {
      delete this.requests[pSock.id];
    })
  }

  startRequest(url, req, res) {
    const pReq = new ProxiedRequest(this.tunnelWs, url, req, res);
    this.tunnelWs.send(JSON.stringify({
      id: pReq.id,
      request: {
          url: {
              pathname: url.pathname,
              search: url.search,
              host: url.host,
              port: url.port,
              protocol: url.protocol,
              username: url.username,
              password: url.password,
          },
          method: req.method,
          headers: req.headers,
        },
    }));
    this.requests[pReq.id] = pReq;
    pReq.on('close', () => {
      delete this.requests[pReq.id];
    });
  }

  destroy() {
    for (const id in this.requests) {
      this.requests[id].destroy();
      delete this.requests[id];
    }
  }
}

module.exports = ProxyClientBackend;
