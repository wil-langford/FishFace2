#!/bin/sh

#SBATCH --job-name=celery_workers
#SBATCH -c 8
#SBATCH --share
#SBATCH --mail-type=FAIL

#SBATCH --nice=5000

#SBATCH --open-mode=append
#SBATCH --output=var/log/celery.log


### DEVELOPMENT
#SBATCH --time=12:00:00
#SBATCH -n 2
#SBATCH -N 2-4

### PRODUCTION
##SBATCH --time=6:23:59:50
##SBATCH -n 16
##SBATCH -N 16-20

ALT_ROOT="${HOME}"

DRONE_DIR="${ALT_ROOT}/celery_worker"
cd "${DRONE_DIR}"

VARRUN="${ALT_ROOT}/var/run"
JIDFILE="${VARRUN}/celery.jid"
echo "${SLURM_JOB_ID}" > "${JIDFILE}"

VARLOG="${ALT_ROOT}/var/log"
LOGFILE="${VARLOG}/celery.log"
SLUG="${HOSTNAME}_${SLURM_JOB_ID}_${SLURM_LOCALID}_${SLURM_TASK_PID}"
echo "${SLUG}" >> "${LOGFILE}"

. "${ALT_ROOT}/.pyenv.sh"


### DEVELOPMENT
srun celery -A tasks worker --loglevel=WARNING --concurrency=16 --autoreload

### PRODUCTION
#srun celery -A tasks worker --loglevel=WARNING --concurrency=16