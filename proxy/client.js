const { URL } = require('url');
const http = require('http');
const https = require('https');
const EventEmitter = require('events');
const debug = require('debug')('baccawl:client');
const { v4: uuidv4 } = require('uuid');
const { WebSocket } = require('ws');
const ReconnectingWebSocket = require('reconnecting-websocket');
const ProxiedResponse = require('./lib/ws/proxied-response');
const ProxiedWebSocket = require('./lib/ws/proxied-web-socket');

const CLIENT_ID = process.env['CLIENT_ID'] || uuidv4().toString();
const HTTP_HOST = new URL(process.env['HTTP_HOST'] || 'https://www.google.com/');
const SERVER_URL = new URL(process.env['SERVER_URL'], 'http://localhost');
const BACKEND_PATH = process.env.BACKEND_PATH || '/_WGtvxgPJ/';

class ProxyClient extends EventEmitter {
  constructor() {
    super();
    this.id = CLIENT_ID;
    SERVER_URL.hostname = `${this.id}.${SERVER_URL.hostname}`;
    SERVER_URL.pathname = BACKEND_PATH;
    this.baseUrl = HTTP_HOST;
    this.proxyHost = SERVER_URL.toString();
    debug('proxyHost: %s', this.proxyHost);
    this.requests = {};
    this.tunnelWs = null;
  }

  connect() {
    this.tunnelWs = new ReconnectingWebSocket(this.proxyHost, [], {
      WebSocket,
      origin: this.proxyHost,
    });
    this.tunnelWs.addEventListener('open', () => {
      debug('connected');
    });
    this.tunnelWs.addEventListener('close', () => {
      debug('disconnected');
    });
    this.tunnelWs.addEventListener('message', (evt) => {
      const json = JSON.parse(evt.data);
      debug('Received message: %O', json);
      const request = this.requests[json.id];
      if (request) {
        request.recv(json);
        return;
      }
      // Start new request.
      if (json.socket) {
        this.startSocket(json);
      } else {
        this.startRequest(json);
      }
    });
  }

  startSocket(json) {
    // Open websocket.
    const url = new URL(this.baseUrl);
    url.protocol = json.socket.url.protocol;
    url.pathname = json.socket.url.pathname;
    url.search = json.socket.url.search;
    url.username = json.socket.url.username;
    url.password = json.socket.url.password;
    const ws = new WebSocket(url);
    const pSock = new ProxiedWebSocket({
      id: json.id,
      tunnelWs: this.tunnelWs,
      clientWs: ws,
    });
    debug('Adding socket %s to %s', pSock.id, this.id);
    this.requests[pSock.id] = pSock;
    pSock.on('end', () => {
      debug('Removing socket %s from %s', pSock.id, this.id);
      delete this.requests[pSock.id];
    });
  }

  startRequest(json) {
    const client = (this.baseUrl.protocol === 'http:') ? http : https;
    const headers = {
      ...json.request.headers,
      host: this.baseUrl.host,
    };
    const options = {
      protocol: this.baseUrl.protocol,
      port: this.baseUrl.port,
      host: this.baseUrl.hostname,
      method: json.request.method,
      path: json.request.url.pathname,
      search: json.request.url.search,
      username: json.request.url.username,
      password: json.request.url.password,
      headers: headers,
    };

    debug('Request options: %O', options);
    const req = client.request(options)
    const pRes = new ProxiedResponse(this.tunnelWs, json.id, req);
    debug('Adding request %s to %s', pRes.id, this.id);
    this.requests[pRes.id] = pRes;
    pRes.on('end', () => {
      debug('Removing request %s from %s', pRes.id, this.id);
      delete this.requests[pRes.id];
    });
  }
}

const client = new ProxyClient();
client.connect();
