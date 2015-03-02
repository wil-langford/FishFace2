#!/bin/bash

ALT_ROOT="${HOME}"
WORKDIR="${ALT_ROOT}"
VARRUN="${ALT_ROOT}/var/run"
#VARLOG="${ALT_ROOT}/var/log"


JIDFILE=${VARRUN}/learn_worker.jid

if [ "$1" == "" ]; then
    echo "$0" '[start|stop|status]'
    exit 0
fi

if [ "$(squeue -h -o '%all' | grep -c learn_worker)" -eq "0" -a -f "${JIDFILE}" ]; then
    echo WARNING: The jidfile exists, but no learn_worker job is running.  Removing jidfile.
    rm "${JIDFILE}"
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
            ;;
        status)
            /usr/bin/scontrol show job ${JID}
            ;;
        remove_jidfile)
            echo Removing jidfile.  I HOPE YOU KNOW WHAT YOU ARE DOING.
            rm "${JIDFILE}"
            ;;
    esac

else
    case "$1" in
        start)
            /usr/bin/sbatch -D "${WORKDIR}" "${ALT_ROOT}"/celery_worker/sbatch_learn.sh
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