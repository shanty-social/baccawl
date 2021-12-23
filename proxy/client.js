const { URL } = require('url');
const { v4: uuidv4 } = require('uuid');
const { WebSocket } = require('ws');
const ReconnectingWebSocket = require('reconnecting-websocket');
const debug = require('debug')('baccawl:client');
const WebSocketResponse = require('./lib/ws/response');

const CLIENT_ID = process.env['CLIENT_ID'] || uuidv4().toString();
const HTTP_HOST = new URL(process.env['HTTP_HOST'] || 'https://www.google.com/');
const SERVER_URL = new URL(process.env['SERVER_URL'], 'http://localhost');
SERVER_URL.hostname = `${CLIENT_ID}.${SERVER_URL.hostname}`;
SERVER_URL.pathname = '_WGtvxgPJ/';
const PROXY_HOST = SERVER_URL.toString();
const RESPONSES = [];

debug('PROXY_HOST: %s', PROXY_HOST);
const ws = new ReconnectingWebSocket(PROXY_HOST, [], {
  WebSocket,
  origin: PROXY_HOST,
});

ws.addEventListener('open', () => {
  debug('connected');
});

ws.addEventListener('close', () => {
  debug('disconnnected');
});

ws.addEventListener('message', (e) => {
  const json = JSON.parse(e.data);
  debug('Received: %O', json);

  let response = RESPONSES[json.request.id];
  if (!response) {
    // Start a new response to handle this request.
    response = new WebSocketResponse(ws, json, HTTP_HOST);
    // Register response, and deregister once completed.
    debug('Registering response for: %s', response.id);
    RESPONSES[response.id] = response;
    response.on('end', () => {
      debug('Unregistering response for: %s', response.id);
      RESPONSES[response.id]
    });
  } else {
    // Pass additional body data to existing response.
    response.handleBody(json);
  }
});
