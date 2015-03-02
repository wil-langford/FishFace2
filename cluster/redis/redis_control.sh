#!/bin/bash

ALT_ROOT="$HOME"
VARRUN="${ALT_ROOT}/var/run"
ETC="${ALT_ROOT}/etc/redis"
#VARLOG="${ALT_ROOT}/var/log"

JID_FILE="${VARRUN}/redis.jid"
HOSTNAME_FILE="${VARRUN}/redis.hostname"
CONF_FILE="${ETC}/redis.conf"
SBATCH_FILE="${ALT_ROOT}/redis/sbatch_redis.sh"
PASSWORD_FILE="${ETC}/redis_password"

if [ "$1" == "" ]; then
    echo "$0" '[start|stop|status]'
    exit 0
fi

if [ -f "${JID_FILE}" ]; then
    JID=$(cat "${JID_FILE}")

    case "$1" in
        start)
            echo Already running.
            exit 1
            ;;
        stop)
            /usr/bin/scancel ${JID}
            rm "${JID_FILE}"
            rm "${HOSTNAME_FILE}"
            rm
            ;;
        status)
            /usr/bin/scontrol show job ${JID}
            ;;
        remove_jidfile)
            echo Removing jidfile.  I HOPE YOU KNOW WHAT YOU ARE DOING.
            rm "${JID_FILE}"
            ;;
    esac

else
    case "$1" in
        start)
            cp "${CONF_FILE}.base" "${CONF_FILE}"
            if [ -f "${PASSWORD_FILE}" ]; then
                echo requirepass $(cat "${PASSWORD_FILE}") >> "${CONF_FILE}"
            fi
            /usr/bin/sbatch "${SBATCH_FILE}"
            ;;
        stop)
            echo Not running.
            exit 1
            ;;
        status)
            echo Not running.
            ;;
        remove_jidfile)
            echo No jidfile to remove.
            ;;
    esac
fi