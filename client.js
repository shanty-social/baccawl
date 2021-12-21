const { URL } = require('url');
const { v4: uuidv4 } = require('uuid');
const { WebSocket } = require('ws');
const ReconnectingWebSocket = require('reconnecting-websocket');
const debug = require('debug')('weproxy:client');
const WebSocketResponse = require('./lib/ws/response');

const CLIENT_ID = process.env['CLIENT_ID'] || uuidv4().toString();
const BASE_URL = new URL(process.env['BASE_URL'] || 'https://www.google.com/');
const SERVER_URL = new URL(process.env['SERVER_URL'], 'http://localhost:8080/');
const PROXY_HOST = `${CLIENT_ID}.${SERVER_URL.hostname}:${SERVER_URL.port}`;
const RESPONSES = [];

debug('PROXY_HOST: %s', PROXY_HOST);
const ws = new ReconnectingWebSocket(`ws://${PROXY_HOST}/backend/`, [], {
  WebSocket,
  origin: `http://${PROXY_HOST}/backend/`,
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
    response = new WebSocketResponse(ws, json, BASE_URL);
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
