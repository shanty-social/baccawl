const { v4: uuidv4 } = require('uuid');
const EventEmitter = require('events');
const debug = require('debug')('weproxy:server:request');

class WebSocketRequest extends EventEmitter {
  constructor(backend, url, req, res) {
    super();
    this.backend = backend;
    this.url = url;
    this.req = req;
    this.res = res;
    this.id = uuidv4().toString();
    this.json = {
      request: {
        id: this.id,
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
    };
    this._timeout = setTimeout(this.handleTimeout.bind(this), 30000);  
  }

  handleTimeout() {
    debug('Handling timeout');
    this.res.statusCode = 504;
    this.res.statusMessage = 'Gateway Timeout';
    this.destroy();
  }

  clearTimeout() {
    if (!this._timeout) return;
    clearTimeout(this._timeout);
    this._timeout = null;
  }

  handleResponse(json) {
    if (typeof json.response.body === 'undefined') {
      debug('Response: starting');
      const headers = {
        ...json.response.headers,
      };
      this.res.writeHead(json.response.statusCode, json.response.statusMessage, headers);
      this.clearTimeout();
    } else if (json.response.body) {
      const buffer = Buffer.from(json.response.body, 'base64');
      debug('Response: sending body: %i bytes', buffer.byteLength);
      this.res.write(buffer);
    } else {
      debug('Response: sending end');
      this.destroy();
    }
  }

  handleData(chunk) {
    debug('Request: sending body: %i bytes', chunk.byteLength);
    this.backend.ws.send(JSON.stringify({
      request: {
        id: this.id,
        body: chunk.toString('base64'),
      },
    }))
  }

  handleEnd() {
    debug('Request: sending End');
    this.backend.ws.send(JSON.stringify({
      request: {
        id: this.id,
        body: null,
      },
    }));
  }

  destroy() {
    this.clearTimeout();
    this.res.end();
    this.emit('end');
  }
}

module.exports = WebSocketRequest;
