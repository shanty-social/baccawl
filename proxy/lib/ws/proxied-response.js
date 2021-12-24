const EventEmitter = require('events');
const debug = require('debug')('baccawl:client:response');

class ProxiedResponse extends EventEmitter {
  constructor(tunnelWs, id, req) {
    super();
    this.id = id;
    this.tunnelWs = tunnelWs;
    this.req = req;
    this.req.on('response', this.response.bind(this));
    this.req.on('error', this.error.bind(this));
  }

  response(res) {
    const msg = {
      id: this.id,
      response: {
        statusCode: res.statusCode,
        statusMessage: res.statusMessage,
        headers: res.headers,
      }
    };
    debug('Sending Response: %O', msg);
    this.tunnelWs.send(JSON.stringify(msg));
    this.res = res;
    this.res.on('data', this.send.bind(this));
    this.res.on('end', this.end.bind(this));
  }

  error(e) {
    debug('Request error: %O', e);
    const msg = {
      id: this.id,
      response: {
        statusCode: 500,
        statusMessage: 'Internal Server Error',
        body: e.message,
        headers: {},
      }
    }
    debug('Sending Error: %O', msg);
    this.tunnelWs.send(JSON.stringify(msg));
  }

  send(chunk) {
    const msg = {
      id: this.id,
      response: {
        body: chunk.toString('base64'),
      }
    };
    debug('Sending Body: %O', msg);
    this.tunnelWs.send(JSON.stringify(msg));
  }

  recv(json) {
    if (json.request.body) {
      const buffer = Buffer.from(json.request.body, 'base64');
      debug('Sending body: %i bytes', buffer.byteLength);
      this.req.write(buffer);
    } else {
      this.req.end();
    }
  }

  end() {
    debug('Sending End');
    this.tunnelWs.send(JSON.stringify({
      id: this.id,
      response: {
        body: null,
      },
    }));
    this.emit('end');
  }
}

module.exports = ProxiedResponse;
