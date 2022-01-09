FROM ${ARCH}openresty/openresty:alpine-fat

ADD ./docker/proxy/nginx.conf /usr/local/openresty/nginx/conf/nginx.conf

RUN luarocks install lua-resty-jwt 0.1.10

EXPOSE 443
EXPOSE 80
