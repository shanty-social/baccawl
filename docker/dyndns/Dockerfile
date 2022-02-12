FROM python:3-alpine3.15

ADD ./docker/dyndns/entrypoint.py /entrypoint.py
RUN chmod +x /entrypoint.py

RUN apk --no-cache add build-base linux-headers && \
    pip3 install python-ddns && \
    addgroup -S -g 1000 dyndns && \
    adduser -H -s /bin/nologin -G dyndns -u 1000 -S -D dyndns && \
    apk del build-base linux-headers

USER dyndns
WORKDIR /

ENTRYPOINT [ "/entrypoint.py" ]
