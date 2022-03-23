FROM haproxytech/haproxy-alpine:2.6

ENV TUNNELS_MAP=/usr/local/etc/haproxy/tunnels.map \
    SSHD_BACKEND=sshd \
    ANNOUNCE_PORT=1337

ADD ./docker/haproxy/lua /usr/local/etc/haproxy/lua
ADD ./docker/haproxy/tunnels.map /usr/local/etc/haproxy/
ADD ./docker/haproxy/errors/* /usr/local/etc/haproxy/errors/
