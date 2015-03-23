#!/bin/sh
#SBATCH --job-name=redis_server
#SBATCH --time=0
#SBATCH --nodes 1-1
#SBATCH -n 1
#SBATCH --exclusive
#SBATCH --mail-type=FAIL

#SBATCH --open-mode=append
#SBATCH --output=/home/wsl/var/log/redis.log

ALT_ROOT=/home/wsl

cd "${ALT_ROOT}/redis/"

VARRUN="${ALT_ROOT}/var/run"
echo "${HOSTNAME}" > "${VARRUN}/redis.hostname"
JIDFILE="${VARRUN}/redis.jid"
echo "${SLURM_JOB_ID}" > "${JIDFILE}"

VARLOG="${ALT_ROOT}/var/log"
LOGFILE="${VARLOG}/redis.log"
SLUG="${HOSTNAME}_${SLURM_JOB_ID}_${SLURM_LOCALID}_${SLURM_TASK_PID}"
echo "============================ START NEW LOG ============================" >> "${LOGFILE}"
echo "${SLUG}" >> "${LOGFILE}"


mpiexec "${ALT_ROOT}/bin/redis-server" "${ALT_ROOT}/etc/redis/redis.conf"
