FROM ${ARCH}node:17-alpine3.15

ADD ./docker/sshd/entrypoint.sh /entrypoint.sh
ADD ./docker/sshd/keys /etc/sshd/keys
RUN chmod +x /entrypoint.sh

ENV SSHD_HOST_KEY_DIR=/etc/sshd/keys

ADD ./sshd /app

WORKDIR /app

RUN npm i -g
EXPOSE 22

ENTRYPOINT [ "/entrypoint.sh" ]
