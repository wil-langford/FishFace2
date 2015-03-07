#!/bin/bash

/bin/bash $HOME/celery_worker/drone_control.sh stop
/bin/bash $HOME/celery_worker/learn_control.sh stop
sleep 5
/bin/bash $HOME/redis/redis_control.sh stop
