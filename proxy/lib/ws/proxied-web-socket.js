const { v4: uuidv4 } = require('uuid');
const debug = require('debug')('baccawl:socket');
const EventEmitter = require('events');

class ProxiedWebSocket extends EventEmitter {
    constructor({id, tunnelWs, clientWs, connected}) {
        super();
        this.id = id || uuidv4().toString();
        this.tunnelWs = tunnelWs;
        this.clientWs = clientWs;
        this.connected = connected;
        this.buffer = [];
        this.clientWs.on('message', this.send.bind(this));
        this.clientWs.on('open', this.open.bind(this));
        // this.tunnelWs.on('close', this.destroy.bind(this));
        this.clientWs.on('close', this.destroy.bind(this));
    }

    send(message) {
        // Encapsulate the message.
        const json = {
            id: this.id,
            socket: {
                message: message.toString('base64'),
            },
        };
        this.tunnelWs.send(JSON.stringify(json));
    }

    open() {
        debug('Websocket connection established');
        // Called when connection is established. Flush pending buffer.
        this.connected = true;
        for (let i = 0; i < this.buffer.length; i++) {
            debug('Flushing buffered message')
            this.clientWs.send(this.buffer[i]);
        }
        this.buffer = [];
    }

    recv(json) {
        debug('Received: %O', json);
        // De-encapsulate the message.
        const message = Buffer.from(json.socket.message, 'base64');
        if (this.connected) {
            debug('Sending message: %O', message);
            this.clientWs.send(message);
        } else {
            debug('Buffering message: %O', message);
            this.buffer.push(message);
        }
    }

    destroy() {
        this.clientWs.close();
        this.emit('close');
    }
}

module.exports = ProxiedWebSocket;
