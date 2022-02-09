FROM ${ARCH}openresty/openresty:alpine-fat

ADD ./docker/proxy/conf.d /etc/nginx/conf.d
ADD ./docker/proxy/nginx.conf /etc/nginx/nginx.conf
ADD ./docker/proxy/lua /app

RUN luarocks install lua-resty-jwt 0.1.10

EXPOSE 443
EXPOSE 80
