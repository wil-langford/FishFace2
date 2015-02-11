#!/bin/bash

ALT_ROOT=$HOME
VARRUN=${ALT_ROOT}/var/run
#VARLOG=${ALT_ROOT}/var/log

JIDFILE=${VARRUN}/redis.jid

if [ "$1" == "" ]; then
    echo "$0" '[start|stop|status]'
    exit 0
fi

if [ -f "${JIDFILE}" ]; then
    JID=$(cat "${JIDFILE}")

    case "$1" in
        start)
            echo Already running.
            exit 1
            ;;
        stop)
            /usr/bin/scancel ${JID}
            rm "${JIDFILE}"
            rm "${VARRUN}/redis.meta"
            ;;
        status)
            /usr/bin/scontrol show job ${JID}
            ;;
        remove_jidfile)
            echo Removing jidfile.  I HOPE YOU KNOW WHAT YOU ARE DOING.
            rm "${JIDFILE}"
            rm "${VARRUN}/redis.meta"
            ;;
    esac

else
    case "$1" in
        start)
            /usr/bin/sbatch "${ALT_ROOT}"/redis/sbatch_redis.sh
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