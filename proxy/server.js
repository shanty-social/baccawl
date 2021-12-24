const http = require('http');
const EventEmitter = require('events');
const { URL } = require('url');
const { WebSocketServer } = require('ws');
const debug = require('debug')('baccawl:server');
const ProxyClientBackend = require('./lib/ws/proxy-client-backend');

const SERVER_HOST = process.env.SERVER_HOST || 'localhost';
const SERVER_PORT = parseInt(process.env.SERVER_PORT || '8080');
const SERVER_URL = new URL(process.env['SERVER_URL'], 'ws://localhost');
const BACKEND_PATH = process.env.BACKEND_PATH || '/_WGtvxgPJ/';

class ProxyServer extends EventEmitter {
  /*
  Represents a proxy "server". This server handles three types of connections:

  1. ws:// connections from "backend" clients.
  2. ws:// connections from browsers (which are forwarded to an appropriate backend).
  3. http:// connections from browsers (which are forwarded to an appropriate backend).
  */
  constructor() {
    // This will contain all the available backends. If an http or ws request arrives,
    // this list of backends will be searched for the host name portion of the Host header.
    // That is the identifier for the backend.
    super();
    this.backends = {};
    this._http = http.createServer();
    this._ws = new WebSocketServer({
      noServer: true,
    });
    this._http
      .on('error', (e) => {
        debug('Error: %O', e);
      })
      .on('upgrade', this.onUpgrade.bind(this))
      .on('request', this.onRequest.bind(this));
  }

  listen(port, host) {
    this._http.listen(port, host, () => {
      const addr = this._http.address();
      debug('Listening at, http://%s:%i/', addr.address, addr.port);
    });
  }

  getBackend(req) {
    const url = new URL(req.url, `http://${req.headers.host}`);
    debug('URL: %s', url.toString());
    const parts = url.hostname.split('.');
    const domain = parts.slice(1).join('.');
    if (domain !== SERVER_URL.hostname) {
      debug('Received connection to unknown domain: %s', domain);
      return [null, null];
    }
    const host = parts[0];
    debug('Looking up backend: %s', host);
    const backend = this.backends[host];
    if (!backend) {
      debug('No backend for: %s', host);
    }
    return [url, backend];
  }

  onUpgrade(req, sock, head) {
    debug('Upgrade request received.');
    // Could be connection type 1 or two. Type 1 connections use a specific path.
    if (req.url === BACKEND_PATH) {
      // TODO: authentication is required.
      this._ws.handleUpgrade(req, sock, head, (ws) => {
        const backend = new ProxyClientBackend(req, ws);
        debug('Adding backend: %s', backend.id);
        if (this.backends[backend.id]) {
          debug('Removing duplicate backend: %s', backend.id);
          this.backends[backend.id].destroy();
          delete this.backends[backend.id];
        }
        this.backends[backend.id] = backend;
      });
    } else {
      const [url, backend] = this.getBackend(req);
      if (!backend) {
        debug('Unavailable backend: %s', url);
        sock.destroy();
        return;
      }
      this._ws.handleUpgrade(req, sock, head, (ws) => {
        backend.startSocket(url, ws, head);
      });
    }
  }

  onRequest(req, res) {
    const [url, backend] = this.getBackend(req);
    if (!backend) {
      res.statusCode = 502;
      res.statusMessage = 'Bad Gateway';
      res.end();
      return;
    }
    debug('Starting new request.');
    backend.startRequest(url, req, res);
  }
}

const server = new ProxyServer();
server.listen(SERVER_PORT, SERVER_HOST);
