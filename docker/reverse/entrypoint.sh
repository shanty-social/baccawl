#!/bin/sh -x

MD5_CURR=""
MD5_PREV=""

configure() {
    envsubst < ${CONF}.tmpl > ${CONF}
    MD5_CURR=$(md5sum ${CONF})

    if [ -f ${PID} ] && kill -0 $(cat ${PID}); then
        # It's already running, did config change?
        if [ "${MD5_CURR}" != "${MD5_PREV}" ]; then
            kill -HUP $(cat ${PID})
        fi
    else
        nginx -g 'daemon off;' &
        echo -n "$!" > ${PID}
    fi
    MD5_PREV=${MD5_CURR}
}

trap 'configure' 1

while true; do
    configure
    sleep 300
done
