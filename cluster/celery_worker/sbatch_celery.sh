#!/bin/sh

#SBATCH --job-name=celery_workers
#SBATCH --time=12:00:00
#SBATCH -n 50
#SBATCH --share
#SBATCH --mail-type=FAIL

#SBATCH --nice=5000

#SBATCH --open-mode=append
#SBATCH --output=/home/wsl/var/log/celery.log

ALT_ROOT=/home/wsl

cd "${ALT_ROOT}/celery_worker/"

VARRUN="${ALT_ROOT}/var/run"
JIDFILE="${VARRUN}/celery.jid"
echo "${SLURM_JOB_ID}" > "${JIDFILE}"

VARLOG="${ALT_ROOT}/var/log"
LOGFILE="${VARLOG}/celery.log"
SLUG="${HOSTNAME}_${SLURM_JOB_ID}_${SLURM_LOCALID}_${SLURM_TASK_PID}"
echo "${SLUG}" >> "${LOGFILE}"


. "${ALT_ROOT}/.pyenv.sh"
pyenv activate FishFace2

srun celery -A tasks worker -l warning
