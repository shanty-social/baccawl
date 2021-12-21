const http = require('http');
const { URL } = require('url');
const { WebSocketServer } = require('ws');
const debug = require('debug')('weproxy:server');
const WebSocketBackend = require('./lib/ws/backend');

const server = http.createServer();
const wssBackends = new WebSocketServer({ noServer: true });
const wssFrontends = new WebSocketServer({ noServer: true });

const BACKENDS = {};

wssBackends.on('connection', (ws, req) => {
  // Create a socket backend to handle requests.
  const backend = new WebSocketBackend(ws, req);
  // Register backend, and unregister when it disconnects.
  debug('Registering backend %s', backend.id);
  BACKENDS[backend.id] = backend;
  ws.on('message', backend.handleMessage.bind(backend));
  ws.on('close', () => {
    debug('Deregistering backend %s', backend.id);
    delete BACKENDS[backend.id];
    backend.destroy();
  });
});

wssFrontends.on('connection', (ws) => {
  debug('Frontend connection: %O', ws);

  ws.on('message', (data) => {
    debug('Frontend received: %s', data);
  });
});

server.on('upgrade', (req, sock, head) => {
  debug('Upgrade at url: %O', req.url);

  switch (req.url) {
    case '/backend/':
      wssBackends.handleUpgrade(req, sock, head, (ws) => {
        wssBackends.emit('connection', ws, req);
      });
      break;

    case '/frontend/':
      wssFrontends.handleUpgrade(req, sock, head, (ws) => {
        wssFrontends.emit('connection', ws, req);
      });
      break;

    default:
      sock.destroy();
  }
});

server.on('error', (e) => {
  debug('Error: %O', e);
});

server.on('request', (req, res) => {
  debug('HTTP request received');
  const url = new URL(req.url, `http://${req.headers.host}`);
  const host = url.hostname.split('.')[0];
  debug('Looking up backend: %s', host);
  const backend = BACKENDS[host];

  if (!backend) {
    res.statusCode = 502;
    res.statusMessage = 'Bad Gateway';
    res.end();
    return;
  }

  const beReq = backend.startRequest(url, req, res);
  req.on('data', beReq.handleData.bind(beReq));
  req.on('end', beReq.handleEnd.bind(beReq));
});

server.listen(8080, () => {
  debug('Listening on port %i', server.address().port);
});
