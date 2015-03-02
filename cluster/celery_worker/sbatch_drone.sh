#!/bin/sh

#SBATCH --job-name=drone_workers
#SBATCH -c 8
#SBATCH --share
#SBATCH --mail-type=FAIL

#SBATCH --nice=5000

#SBATCH --open-mode=append
#SBATCH --output=var/log/drone_workers.log


### DEVELOPMENT
##SBATCH --time=12:00:00
##SBATCH -n 2
##SBATCH -N 2-4

### PRODUCTION
#SBATCH --time=0
#SBATCH -n 16
#SBATCH -N 16-20

ALT_ROOT="${HOME}"

DRONE_DIR="${ALT_ROOT}/celery_worker"
cd "${DRONE_DIR}"

VARRUN="${ALT_ROOT}/var/run"
JIDFILE="${VARRUN}/drone_workers.jid"
echo "${SLURM_JOB_ID}" > "${JIDFILE}"

VARLOG="${ALT_ROOT}/var/log"
LOGFILE="${VARLOG}/drone_workers.log"
SLUG="${HOSTNAME}_${SLURM_JOB_ID}_${SLURM_LOCALID}_${SLURM_TASK_PID}"
echo "============================ START NEW LOG ============================" >> "${LOGFILE}"
echo "${SLUG}" >> "${LOGFILE}"

. "${ALT_ROOT}/.pyenv.sh"


srun celery worker --app=drone_tasks --loglevel=WARNING --concurrency=16 -Q tasks