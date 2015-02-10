#!/bin/sh

# See http://slurm.schedmd.com/sbatch.html for all options
# The SBATCH lines are commented out but are still read by the scheduler
# ***Leave them commented out!***

#SBATCH --job-name=redis_server

# max run time HH:MM:SS
#SBATCH --time=10:00:00

# -N, --nodes=<minnodes[-maxnodes]>
# Request that a minimum of minnodes nodes (servers) be allocated to this job.
# A maximum node count may also be specified with maxnodes.

#SBATCH --nodes 1-1

# -n, --ntasks=<number>
# This option advises the SLURM controller that job steps run within the
# allocation will launch a maximum of number tasks and to provide for
# sufficient resources. The default is one task per node, but note
# that the --cpus-per-task option will change this default.

#SBATCH -n 1

#SBATCH --partition CLUSTER

ALT_ROOT=/home/wsl

SLUG=${HOSTNAME}_${SLURM_JOB_ID}_${SLURM_LOCALID}_${SLURM_TASK_PID}
echo ${SLUG} > ${ALT_ROOT}/var/run/redis.meta

mpiexec $ALT_ROOT/bin/redis-server $ALT_ROOT/etc/redis/redis.conf
