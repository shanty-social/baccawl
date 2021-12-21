const http = require('http');
const https = require('https');
const EventEmitter = require('events');
const debug = require('debug')('weproxy:client:response');

class WebSocketResponse extends EventEmitter {
  constructor(ws, json, baseUrl) {
    super();
    this.ws = ws;
    this.id = json.request.id;
    this.json = json;
    this.baseUrl = baseUrl;
    this.req = this.startResponse(json);
  }

  startResponse(json) {
    const client = (this.baseUrl.protocol === 'http:') ? http : https;
    const headers = {
      ...json.request.headers,
      host: this.baseUrl.host,
    };
    const options = {
      protocol: this.baseUrl.protocol,
      port: this.baseUrl.port,
      host: this.baseUrl.host,
      method: json.request.method,
      path: json.request.url.pathname,
      search: json.request.url.search,
      username: json.request.url.username,
      password: json.request.url.password,
      headers: headers,
    };

    debug('Request options: %O', options);
    return client
      .request(options, (res) => {
        const msg = {
          response: {
            id: json.request.id,
            statusCode: res.statusCode,
            statusMessage: res.statusMessage,
            headers: res.headers,
          }
        };
        debug('Sending Response: %O', msg);
        this.ws.send(JSON.stringify(msg));

        res
          .on('data', (chunk) => {
            const msg = {
              response: {
                id: json.request.id,
                body: chunk.toString('base64'),
              }
            };
            debug('Sending Body: %O', msg);
            this.ws.send(JSON.stringify(msg));
          })
          .on('end', () => {
            debug('Sending End');
            this.ws.send(JSON.stringify({
              response: {
                id: json.request.id,
                body: null,
              },
            }));
          });
      })
      .on('error', (e) => {
        debug('Request error: %O', e);
        const msg = {
          response: {
            id: json.request.id,
            statusCode: 500,
            statusMessage: 'Internal Server Error',
            body: e.message,
            headers: {},
          }
        }
        debug('Sending Error: %O', msg);
        this.ws.send(JSON.stringify(msg));
      })
      .on('end', () => this.emit('end'));
  }

  handleBody(json) {
    if (json.request.body) {
      const buffer = Buffer.from(json.request.body, 'base64');
      debug('Sending body: %i bytes', buffer.byteLength);
      this.req.write(buffer);
    } else {
      this.req.end();
    }
  }
}

module.exports = WebSocketResponse;
