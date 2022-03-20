/* eslint-disable no-bitwise, no-param-reassign, no-plusplus */
const net = require('net');
const { EventEmitter } = require('events');
const DEBUG = require('debug')('sshd:proxy');

const MAGIC = '\r\n\r\n\x00\r\nQUIT\n';

function decodeV4Address(buf, offset) {
  let i;
  const address = new Array(4);
  for (i = 0; i < 4; i++) {
    address[i] = Number(buf[offset + i]).toString();
  }

  return address.join('.');
}

// eslint-disable-next-line no-unused-vars
function decodeV6Address(buf, offset) {
  let i;
  const address = new Array(8);
  for (i = 0; i < 8; i++) {
    address[i] = Number(buf.readUInt16BE(offset + i * 2, true)).toString(16);
  }

  return address.join(':').replace(/:(?:0:)+/, '::');
}

function parseTLV(buffer, offset) {
  console.log(buffer.subarray(offset).toString('hex'));
  const type = buffer.readUInt8(offset++);
  const length = buffer.readUInt16BE(offset);
  offset += 2;
  const value = buffer.subarray(offset, offset + length).toString();
  return { type, length: length + 2, value };
}

function parseProxyData(header, buffer) {
  const fields = {
    tlv: [],
  };

  console.log(buffer.toString('hex'));

  let offset = 0;
  if (header.family === 0x01) {
    fields.remoteAddress = decodeV4Address(buffer, offset);
    offset += 4;
    fields.localAddress = decodeV4Address(buffer, offset);
    offset += 4;
    fields.remotePort = buffer.readUInt16BE(8);
    fields.localPort = buffer.readUInt16BE(10);
    offset += 4;
  } else if (header.family === 0x02) {
    // TODO: decode ipv6
  }

  while (offset < header.length - 1) {
    const record = parseTLV(buffer, offset);
    fields.tlv.push(record);
    offset += record.length;
  }

  console.log(fields);
  fields.length = offset;

  return fields;
}

function parseProxyHeader(buffer) {
  const fields = {};

  console.log(buffer.toString('hex'));
  // check magic:
  const preamble = buffer.subarray(0, 12);
  if (preamble.toString() !== MAGIC) {
    throw new Error('Invalid proxy protocol preamble');
  }

  const famProt = buffer.readUInt8(13);
  fields.length = buffer.readUInt16BE(14);

  fields.family = (famProt & 0xf0) >> 4;
  fields.protocol = famProt & 0x0f;

  console.log(fields);

  return fields;
}

function createHandler(domains, emitter) {
  return (c) => {
    c.on('error', (e) => DEBUG('Error handling user http request: %O', e));
    c.once('data', (buffer) => {
      c.pause();

      const addr = c.address();
      const header = parseProxyHeader(buffer);
      const fields = parseProxyData(header, buffer.subarray(16));
      const host = fields.tlv[0].value;

      // get host connection info.
      const info = domains[host];
      if (!info) {
        emitter.emit('invalid', host);
        return;
      }

      // establish connection via tunnel.
      info.client.forwardOut(
        info.bindAddr,
        info.bindPort,
        addr.address,
        addr.port,
        (e, channel) => {
          if (e) {
            DEBUG('Error forwarding: %O', e);
            return;
          }
          // Connect client socket and SSH channel.
          DEBUG('Connecting client<->channel');

          channel.write(buffer.subarray(16 + header.length));

          c
            .pipe(channel)
            .pipe(c);

          c.on('end', () => {
            channel.end();
            DEBUG('TCP forwarding closed by client');
          });

          channel.on('end', () => {
            c.end();
            DEBUG('TCP forwarding closed by tunnel');
          });
        }
      );
    });
  };
}

function start(port, host, domains) {
  const emitter = new EventEmitter();
  const handler = createHandler(domains, emitter);
  const s = net.createServer(handler);

  s.listen(port, host, 100, () => {
    const addr = s.address();
    DEBUG('Proxy server listening at %s:%i', addr.address, addr.port);
  });

  return emitter;
}

module.exports = {
  parseProxyData,
  parseProxyHeader,
  start,
};
