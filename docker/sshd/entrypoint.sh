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

# This is only temporary, key management will be done during registration...
while [ ! -f "${SSH_KEY}" ]; do
    sleep 1
done

cd /app

node index.js
