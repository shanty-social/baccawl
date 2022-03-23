FROM python:3-alpine3.15

ENV SSH_HOST=ssh.homeland-social.com \
    SSH_PORT=2222 \
    SSH_USER= \
    SSH_KEY= \
    LOG_LEVEL=error

ADD ./client /app
ADD ./docker/client/entrypoint.py /entrypoint.py
RUN chmod +x /entrypoint.py

WORKDIR /app
RUN apk add --no-cache py3-pip build-base libffi libffi-dev && \
    pip3 install pipenv && \
    pipenv install --system --dev --skip-lock && \
    apk del build-base libffi-dev

ENTRYPOINT [ "/entrypoint.py" ]
