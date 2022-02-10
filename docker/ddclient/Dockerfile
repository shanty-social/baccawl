FROM alpine:3.15

ARG DDCLIENT_VERSION=3.9.1

ENV PID=/var/run/ddclient/ddclient.pid
ENV CONF=/etc/ddclient/ddclient.conf

ADD ./docker/ddclient/ddclient.conf.tmpl /etc/ddclient/ddclient.conf.tmpl
ADD ./docker/ddclient/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN apk add --no-cache -X http://dl-cdn.alpinelinux.org/alpine/edge/testing envsubst && \
    apk add --no-cache gcc libc-dev libc6-compat make perl perl-utils \
                       perl-test-taint perl-netaddr-ip perl-net-ip jq \
                       perl-json perl-io-socket-ssl perl-io-socket-inet6 && \
    cpan Data::Validate::IP && \
    wget -qc https://github.com/ddclient/ddclient/archive/v${DDCLIENT_VERSION}.tar.gz -O ddclient.tar.gz && \
    tar -xvzf ddclient.tar.gz && \
    mv ddclient*/ddclient /usr/bin && \
    rm -rf ddclient* && \
    apk del --nocache --purge gcc libc-dev libc6-compat make && \
    rm -rf /tmp/cpan* /root/.cpan && \
    mkdir -p $(dirname ${CONF}) /var/cache/ddclient $(dirname ${PID}) && \
    addgroup -S -g 1000 ddclient && \
    adduser -H -s /bin/nologin -G ddclient  -u 1000 -S -D ddclient && \
    chown ddclient:ddclient -R $(dirname ${CONF}) /var/cache/ddclient $(dirname ${PID})

USER ddclient
WORKDIR /

LABEL social.shanty.config="HUP"

ENTRYPOINT [ "/entrypoint.sh" ]
