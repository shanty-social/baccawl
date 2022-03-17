FROM python:3-alpine3.15

ADD ./sshc /app
ADD ./docker/sshc/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /app
RUN apk add --no-cache py3-pip build-base libffi libffi-dev && \
    pip3 install pipenv && \
    pipenv install --system --skip-lock && \
    apk del build-base libffi-dev

ENTRYPOINT [ "/entrypoint.sh" ]
