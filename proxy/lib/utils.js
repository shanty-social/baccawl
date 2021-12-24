const debug = require('debug')('baccawl:utils');

function serializeRequest(r) {
    debug('Serializing HTTP request: %O', r);
}

function deserializeRequest(m) {
    debug('Deserializing HTTP request: %O', m);
}

function serializeSocket(s) {
    debug('Serializing Websocket: %O', s);

}

function deserializeSocket(m) {
    debug('Deserializing Websocket: %O', m);
}

module.exports = {
    serializeRequest,
    deserializeRequest,
    serializeSocket,
    deserializeSocket,
};
