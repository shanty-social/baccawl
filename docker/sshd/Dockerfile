FROM node:17-alpine3.15

ADD ./docker/sshd/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ADD ./sshd /app

WORKDIR /app

RUN npm i -g
EXPOSE 22

ENTRYPOINT [ "/entrypoint.sh" ]
