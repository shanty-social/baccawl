const { URL } = require('url');
const net = require('net');
const http = require('http');
const https = require('https');
const { EventEmitter } = require('events');
const debug = require('debug')('baccawl:client');
const { v4: uuidv4 } = require('uuid');
const { WebSocket } = require('ws');
const { BackendMessage } = require('./lib/messages');
const { ForwardedWebRequest, ForwardedWebSocket } = require('./lib/forwarded');

const CLIENT_ID = process.env['CLIENT_ID'] || uuidv4().toString();
const HTTP_HOST = new URL(process.env['HTTP_HOST'] || 'https://www.google.com/');
const SERVER = process.env['SERVER'] || 'localhost';
const PORT = parseInt(process.env.PORT || '6400');

class ProxyClient {
  constructor({clientId, httpHost, server, port}) {
    this._clientId = clientId;
    this._httpHost = httpHost;
    this._server = server;
    this._port = port;
    this._requests = {};
    this._sock = new net.Socket();
    this._sock.on('data', this.onData.bind(this));
    this._sock.on('end', this.onEnd.bind(this));
  }

  onData(chunk) {
    const m = BackendMessage.deserialize(chunk);
  }

  onEnd() {
    this.connect();
  }

  makeWebRequest(message) {
    const ep = new EventEmitter();
    const fwr = new ForwardedWebRequest(ep, req, res);
    this._requests(message.requestId) = { request: fwr, eventProxy: ep };
  }

  makeWebSocket(message) {
    const ep = new EventEmitter();
    const fwr = new ForwardedWebSocket(ep, ws);
    this._requests(message.requestId) = { request: fwr, eventProxy: ep };
  }

  connect() {
    this._sock.connect(this._port, this._server, () => {
      const m = new BackendMessage(BackendMessage.TYPES.AUTH, this._clientId);
      this._sock.write(m.serialize());
    });
  }

  start() {
    this.connect();
  }
}

function start(options) {
  const client = new ProxyClient(options);
  client.start();
  return client;
}

if (require.main === module) {
  start({
    clientId: CLIENT_ID,
    httpHost: HTTP_HOST,
    server: SERVER,
    port: PORT,
  });
}

module.exports = {
  ProxyClient,
  start,
};
