FROM ${ARCH}node:17-alpine AS server

ADD ./proxy /app

WORKDIR /app
RUN npm i -g node-pre-gyp && \
    npm i --unsafe-perms

ENTRYPOINT [ "npm", "run", "server" ]

FROM server AS client

ENTRYPOINT [ "npm", "run", "client" ]
