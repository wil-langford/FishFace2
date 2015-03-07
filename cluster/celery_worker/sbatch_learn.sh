#!/bin/sh

#SBATCH --job-name=learn_worker
#SBATCH -c 8
#SBATCH --time=0
#SBATCH -n 1
#SBATCH -N 1-1
#SBATCH --exclusive
#SBATCH --mail-type=FAIL

#SBATCH --open-mode=append
#SBATCH --output=var/log/learn_worker.log


ALT_ROOT="${HOME}"

DRONE_DIR="${ALT_ROOT}/celery_worker"
cd "${DRONE_DIR}"

VARRUN="${ALT_ROOT}/var/run"
JIDFILE="${VARRUN}/learn_worker.jid"
echo "${SLURM_JOB_ID}" > "${JIDFILE}"

VARLOG="${ALT_ROOT}/var/log"
LOGFILE="${VARLOG}/learn_worker.log"
SLUG="${HOSTNAME}_${SLURM_JOB_ID}_${SLURM_LOCALID}_${SLURM_TASK_PID}"
echo "${SLUG}" >> "${LOGFILE}"

. "${ALT_ROOT}/.pyenv.sh"


srun celery worker --app=learn_tasks --loglevel=WARNING --concurrency=1 -Q learn -n 'learn.%h'