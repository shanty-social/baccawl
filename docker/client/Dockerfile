FROM ${ARCH}alpine:3.15

ADD ./docker/client/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV SSH_KEY=/etc/ssh/keys/id_ecdsa

RUN apk add --no-cache jq curl dropbear dropbear-ssh

ENTRYPOINT [ "/entrypoint.sh" ]
