FROM node:17-alpine

ADD ./proxy /app

WORKDIR /app
RUN npm i -g

ENTRYPOINT [ "npm", "run", "server" ]
