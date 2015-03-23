#!/bin/bash

/bin/bash $HOME/redis/redis_control.sh start
sleep 5
/bin/bash $HOME/celery_worker/drone_control.sh start
/bin/bash $HOME/celery_worker/learn_control.sh start
