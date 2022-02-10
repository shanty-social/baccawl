#!/bin/sh -x

MD5_PREV=""
MD5_CURR=""

configure() {
    # Fetch config from console and write ${CONF}
    envsubst < ${CONF}.tmpl > ${CONF}
    MD5_CURR=$(md5sum ${CONF})

    if [ -f ${PID} ] && kill -0 $(cat ${PID}); then
        # It's already running, did config change?
        if [ "${MD5_CURR}" != "${MD5_PREV}" ]; then
            kill -HUP $(cat ${PID})
        fi
    else
        # Not running, first run? Start it.
        ddclient -verbose -file ${CONF} -foreground -daemon 5m -pid ${PID} &
    fi
    MD5_PREV=${MD5_CURR}
}

# HUP should immediately rebuild config.
trap 'configure' 1

while true; do
    configure
    sleep 300
done
