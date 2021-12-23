FROM node:17-alpine

ADD ./proxy /app

WORKDIR /app
RUN apk add --no-cache build-base && \
    npm i -g node-pre-gyp && \
    npm i --unsafe-perms && \
    apk del build-base

ENTRYPOINT [ "npm", "run", "server" ]
