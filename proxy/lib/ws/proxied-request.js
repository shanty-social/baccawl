
const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');
const debug = require('debug')('baccawl:server:request');

class ProxiedRequest extends EventEmitter {
    constructor(tunnelWs, url, req, res) {
        super();
        this.tunnelWs = tunnelWs;
        this.url = url;
        this.req = req;
        this.res = res;
        this.id = uuidv4().toString();
        this.req.on('data', this.send.bind(this));
        this.req.on('end', this.end.bind(this));
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
    
    send(chunk) {
        this.tunnelWs.send(JSON.stringify({
            id: this.id,
            request: {
              body: chunk.toString('base64'),
            },
        }));      
    }

    recv(json) {
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

    end() {
        debug('Request: sending End');
        this.tunnelWs.send(JSON.stringify({
            id: this.id,
            request: {
                body: null,
            },
        }));
        this.emit('end');
    }
    
    destroy() {
        this.clearTimeout();
        this.res.end();
    }    
}

module.exports = ProxiedRequest;