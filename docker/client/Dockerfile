FROM ${ARCH}alpine:3.15

ADD ./docker/client/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN apk add --no-cache dropbear-ssh

ENTRYPOINT [ "/entrypoint.sh" ]
