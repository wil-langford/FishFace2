#!/bin/sh

# See http://slurm.schedmd.com/sbatch.html for all options
# The SBATCH lines are commented out but are still read by the scheduler
# ***Leave them commented out!***

#SBATCH --job-name=celery_workers

# max run time HH:MM:SS
#SBATCH --time=1:00:00

# -N, --nodes=<minnodes[-maxnodes]>
# Request that a minimum of minnodes nodes (servers) be allocated to this job.
# A maximum node count may also be specified with maxnodes.

# -n, --ntasks=<number>
# This option advises the SLURM controller that job steps run within the
# allocation will launch a maximum of number tasks and to provide for
# sufficient resources. The default is one task per node, but note
# that the --cpus-per-task option will change this default.

#SBATCH -n 100

#SBATCH --partition CLUSTER

# command(s) to run

ALT_ROOT=/home/wsl
VARRUN=${ALT_ROOT}/var/run
#VARLOG=${ALT_ROOT}/var/log

#SLUG=${HOSTNAME}_${SLURM_JOB_ID}_${SLURM_LOCALID}_${SLURM_TASK_PID}

JIDFILE=${VARRUN}/celery.jid

echo ${SLURM_JOB_ID} > ${JIDFILE}

. ${ALT_ROOT}/.pyenv.sh
pyenv activate FishFace2

srun celery -A tasks worker -l warning
