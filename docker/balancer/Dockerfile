FROM ${ARCH}openresty/openresty:alpine-fat

ADD ./docker/balancer/conf.d /etc/nginx/conf.d
ADD ./docker/balancer/nginx.conf /etc/nginx/nginx.conf
ADD ./docker/balancer/lua/proxy.lua /usr/local/openresty/lualib/

RUN luarocks install lua-resty-jwt 0.1.10

EXPOSE 443
EXPOSE 80
