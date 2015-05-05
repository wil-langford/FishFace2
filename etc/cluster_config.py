import os
import etc.fishface_config as ff_conf

# These can probably be left alone.
SCP_PORT = 22
SCP_SECRET_KEYFILE = os.path.join(os.environ['HOME'], '.ssh', 'id_rsa')
JOB_FILE_DIR = os.path.join(ff_conf.VAR, 'lib', 'cluster_jobs')

# This will get determined automatically if you leave it as None
SLURM_COMPUTE_NODE_CORES = None

# These might be overridden in cluster_local_config.py
SCP_USER = 'fishface'
SCP_HOST = 'localhost'
LOCAL_CACHE_DIR = '/tmp/fishface'

try:
    from etc.local_cluster_config import *
except ImportError:
    pass