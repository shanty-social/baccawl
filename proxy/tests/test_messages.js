const { v4: uuidv4 } = require('uuid');
const assert = require('assert');
const { BackendMessage, PeerMessage, MESSAGE_TYPE } = require('../lib/messages');

const CLIENT_ID = uuidv4();
const REQUEST_ID = uuidv4();

describe('BackendMessage', () => {
  it('can serialize', () => {
    const payload = 'payload';
    const m = new BackendMessage(
      MESSAGE_TYPE.AUTH, CLIENT_ID, REQUEST_ID, payload);
    const b = m.serialize();
    assert.equal(b.byteLength, 40);
  });
});
