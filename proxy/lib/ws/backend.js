const debug = require('debug')('weproxy:server:backend');
const WebSocketRequest = require('./request');

class WebSocketBackend {
  constructor(ws, req) {
    this.id = req.headers.host.split('.')[0];
    this.ws = ws;
    this.requests = {};
  }

  handleMessage(json) {
    json = JSON.parse(json);
    const req = this.requests[json.response.id];
    if (!req) {
      debug('Invalid request %s for backend %s', json.response.id, this.id);
      return;
    }
    req.handleResponse(json);
  }

  startRequest(url, req, res) {
    const beReq = new WebSocketRequest(this, url, req, res);
    debug('Registering request %s in backend %s', beReq.id, this.id);
    this.requests[beReq.id] = beReq;
    beReq.on('end', () => {
      debug('Deregistering request %s in backend %s', beReq.id, this.id);
      delete this.requests[beReq.id];
    });
    this.ws.send(JSON.stringify(beReq.json));
    return beReq;
  }

  endRequest(req) {
    req.destroy();
  }

  destroy() {
    for (const id in this.requests) {
      this.requests[id].destroy();
    }
  }
}

module.exports = WebSocketBackend;
