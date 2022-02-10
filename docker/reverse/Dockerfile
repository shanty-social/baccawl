FROM nginx:1.21.6-alpine

ENV PID=/var/run/nginx/nginx.pid
ENV CONF=/etc/nginx/nginx.conf

ADD ./docker/reverse/nginx.conf.tmpl /etc/nginx/nginx.conf.tmpl
ADD ./docker/reverse/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN apk add --no-cache -X http://dl-cdn.alpinelinux.org/alpine/edge/testing envsubst && \
    mkdir -p $(dirname ${PID}) && \
    chown nginx:nginx $(dirname ${PID})

ENTRYPOINT [ "/entrypoint.sh" ]
