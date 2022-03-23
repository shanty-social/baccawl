FROM ${ARCH}node:17-alpine3.15

ENV DEBUG= \
    AUTORELOAD=false \
    SSHD_HOST_KEY_DIR=/etc/sshd/keys/ \
    SSHD_HOST=0.0.0.0 \
    SSHD_PORT=22 \
    PROXY_HOST=0.0.0.0 \
    PROXY_PORT=10088 \
    ANNOUNCE_HOST=0.0.0.0 \
    ANNOUNCE_PORT=1337 \
    SHANTY_URL=http://www.homeland-social.com \
    HAPROXY_HOST=haproxy \
    HAPROXY_PORT=9999

ADD ./docker/sshd/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV SSHD_HOST_KEY_DIR=/etc/sshd/keys

ADD ./sshd /app

WORKDIR /app

RUN apk add --no-cache openssh-keygen && \
    npm i -g
EXPOSE 22

ENTRYPOINT [ "/entrypoint.sh" ]
