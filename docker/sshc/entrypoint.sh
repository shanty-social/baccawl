#!/bin/sh -x

while true; do
    CONSOLE_UUID=$(curl \
        -H "Authorization: Bearer ${CONSOLE_AUTH_TOKEN}" \
        ${CONSOLE_URL}/api/settings/CONSOLE_UUID/?format=text \
            | awk -F= ' { print $2 } ' \
            | tr -d \")
    if [ ! -z "${CONSOLE_UUID}" ]; then
        break
    fi
done

while true; do
    DOMAINS=$(curl \
        -H "Authorization: Bearer ${CONSOLE_AUTH_TOKEN}" \
        ${CONSOLE_URL}/api/domains/ \
            | jq --raw-output '.objects[].name')
    if [ ! -z "${DOMAINS}" ]; then
        break
    fi
done

while true; do
    ACCESS_TOKEN=$(curl \
        -H "Authorization: Bearer ${CONSOLE_AUTH_TOKEN}" \
        ${CONSOLE_URL}/api/settings/OAUTH_TOKEN_SHANTY/?format=text \
            | grep OAUTH_TOKEN_SHANTY.access_token \
            | awk -F= ' { print $2 } ' \
            | tr -d \")
    if [ ! -z "${ACCESS_TOKEN}" ]; then
        break
    fi
done

if [ ! -f "${SSH_KEY_PATH}" ]; then
    echo "Generating keys..."
    TMP_KEY=$(mktemp -u)
    PUB_KEY=$(dropbearkey -t ${SSH_KEY_TYPE} -f ${TMP_KEY} \
        -s 384 | grep "^${SSH_KEY_TYPE}")
    PUB_KEY_TYPE=$(echo ${PUB_KEY} | awk ' { print $1 } ')
    PUB_KEY_KEY=$(echo ${PUB_KEY} | awk ' { print $2 } ')

    # Upload ssh public key, we can't connect until this succeeds, so retry.
    while true; do
        HTTP_STATUS=$(curl -d "{\"key\":\"${PUB_KEY_KEY}\",\"type\":\"${PUB_KEY_TYPE}\"}"\
            -H 'Content-Type: application/json' \
            -H "Authorization: Bearer ${ACCESS_TOKEN}" \
            --write-out '%{http_code}' --silent --output /dev/null \
            -X PUT ${SHANTY_URL}/api/sshkeys/${CONSOLE_UUID}/)

        if [ ${HTTP_STATUS} -eq 200 ]; then
            # Now that the key has been uploaded, save it to the final
            # location. This ensures we won't regenerate the key next
            # restart.
            mkdir -p $(dirname ${SSH_KEY_PATH})
            mv ${TMP_KEY} ${SSH_KEY}
            break
        fi
        sleep 60
    done
fi

# Options:
# -T don't allocate a pty
# -i identity file
# -K keepalive (seconds?)
# -y accept host key
# -R remote port forwarding

# We open an ssh connection, and open a remote port to receive HTTP traffic.
# Also run a command passing the domain list, which is used to identify traffic
# to be directed through the tcp tunnel.

while true; do
    echo "Starting ssh client..."
    ssh -Ty -K 300 -i ${SSH_KEY_PATH} \
        -R 0.0.0.0:0:${SSH_FORWARD_HOST}:${SSH_FORWARD_PORT} \
        ${CONSOLE_UUID}@conduit-sshd/22 "proxy ${ACCESS_TOKEN} ${DOMAINS}"
    echo "SSH client died, restarting..."
    sleep 3
done
