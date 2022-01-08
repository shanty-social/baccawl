FROM ${ARCH}alpine:3.15

ADD ./docker/client/entrypoint.sh /entrypoint.sh
ADD ./docker/client/keys /etc/ssh/keys/
RUN chmod +x /entrypoint.sh

ENV SSH_KEY=/etc/ssh/keys/id_rsa

RUN apk add --no-cache dropbear-ssh

ENTRYPOINT [ "/entrypoint.sh" ]
