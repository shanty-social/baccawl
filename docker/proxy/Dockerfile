FROM ${ARCH}openresty/openresty:alpine

ADD ./docker/proxy/nginx.conf /usr/local/openresty/nginx/conf/nginx.conf
ADD ./docker/proxy/lua /app

EXPOSE 443
EXPOSE 80
