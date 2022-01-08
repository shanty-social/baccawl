const http = require('http');
const EventEmitter = require('events');
const { URL } = require('url');
const { WebSocketServer } = require('ws');
const debug = require('debug')('baccawl:server');
const BackendManager = require('./lib/backend-manager');
const PeerManager = require('./lib/peer-manager');

const PROXY_HOST = process.env.PROXY_HOST || 'localhost';
const PROXY_BCAST = process.env.PROXY_BCAST || '192.168.128.255';
const HTTP_PORT = parseInt(process.env.HTTP_PORT || '8080');
const WHISPER_PORT = parseInt(process.env.WHISPER_PORT || '6200');
const TRANSIT_PORT = parseInt(process.env.TRANSIT_PORT || '6300');
const BACKEND_PORT = parseInt(process.env.BACKEND_PORT || '6400');

class ProxyServer {
  constructor({host, bcast, httpPort, whisperPort, transitPort, backendPort}) {
    this._host = host;
    this._bcast = bcast;
    this._httpPort = httpPort;
    this._peers = new PeerManager(whisperPort, transitPort, this._host, this._bcast);
    this._backends = new BackendManager(backendPort, host, this._peers);
    this._http = http.createServer(this.onRequest.bind(this));
    this._ws = new WebSocketServer({ noServer: true });
    this._http.on('upgrade', this.onUpgrade.bind(this));
  }

  _parseClientId(req) {
    const url = new URL(req.url, `http://${req.headers.host}`);
    debug('Parsing clientID from URL: %s', url.host);
    const parts = url.hostname.split('.');
    return parts[0];
  }

  onUpgrade(req, sock, head) {
    debug('WS request received');
    const clientId = this._parseClientId(req);
    this._ws.handleUpgrade(req, sock, head, async (ws) => {
      let b;

      try {
        b = await this._backends.resolve(clientId);
      }
      catch(e) {
        sock.destroy();
        return;
      }

      b.forwardWebSocket(ws);
    });
  }

  async onRequest(req, res) {
    debug('HTTP request received')
    const clientId = this._parseClientId(req);
    let b;

    try {
      b = await this._backends.resolve(clientId);
    }
    catch (e) {
      res.statusCode = 502;
      res.statusMessage = 'Bad Gateway';
      res.end();
      return;
    }

    b.forwardWebRequest(req, res);
  }

  start() {
    this._backends.start();
    this._peers.start();
    this._http.listen(this._httpPort, this._host);
  }
}

function start(options) {
  const server = new ProxyServer(options);
  server.start();
  return server;
}

if (require.main === module) {
  // Start the server.
  start({
    host: PROXY_HOST,
    bcast: PROXY_BCAST,
    httpPort: HTTP_PORT,
    whisperPort: WHISPER_PORT,
    transitPort: TRANSIT_PORT,
    backendPort: BACKEND_PORT,
  });
}

module.exports = {
  ProxyServer,
  start,
};
