FROM python:3-alpine3.15

ARG CACHE_PATH=/var/lib/dyndns.cache
ENV CACHE_PATH=${CACHE_PATH}

ADD ./docker/dyndns/entrypoint.py /entrypoint.py
RUN chmod +x /entrypoint.py

RUN apk --no-cache add build-base linux-headers && \
    pip3 install python-ddns && \
    addgroup -S -g 1000 dyndns && \
    adduser -H -s /bin/nologin -G dyndns -u 1000 -S -D dyndns && \
    apk del build-base linux-headers && \
    touch ${CACHE_PATH} && \
    chown dyndns ${CACHE_PATH}

USER dyndns
WORKDIR /

ENTRYPOINT [ "/entrypoint.py" ]
