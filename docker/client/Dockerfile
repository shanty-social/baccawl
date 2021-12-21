FROM arm64v8/node:17-alpine

ENV DEBUG=weproxy*
ADD ./proxy /app

WORKDIR /app
RUN npm install

ENTRYPOINT [ "npm", "run", "client" ]
