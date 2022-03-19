#!/bin/sh

if [ ! -d "${SSHD_HOST_KEY_DIR}" ]; then
    mkdir -p ${SSHD_HOST_KEY_DIR}
fi

if [ ! -f "${SSHD_HOST_KEY_DIR}/ssh_host_dsa_key" ]; then
    ssh-keygen -f ${SSHD_HOST_KEY_DIR}/ssh_host_dsa_key -N '' -t dsa
fi

if [ ! -f "${SSHD_HOST_KEY_DIR}/ssh_host_rsa_key" ]; then
    ssh-keygen -f ${SSHD_HOST_KEY_DIR}/ssh_host_rsa_key -N '' -t rsa
fi

if [ ! -f "${SSHD_HOST_KEY_DIR}/ssh_host_ecdsa_key" ]; then
    ssh-keygen -f ${SSHD_HOST_KEY_DIR}/ssh_host_ecdsa_key -N '' -t ecdsa
fi

if [ "${AUTORELOAD}" == "yes" ] || [ "${AUTORELOAD}" == "true" ]; then
    CMD=node_modules/.bin/nodemon
else
    CMD=node
fi

cd /app

${CMD} lib/index.js
