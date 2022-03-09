FROM ${ARCH}openresty/openresty:alpine-fat

ADD ./docker/reverse/conf.d /etc/nginx/conf.d
ADD ./docker/reverse/nginx.conf /etc/nginx/nginx.conf
ADD ./docker/reverse/lua/backend.lua /usr/local/openresty/lualib/

RUN luarocks install luasocket

EXPOSE 80
EXPOSE 443