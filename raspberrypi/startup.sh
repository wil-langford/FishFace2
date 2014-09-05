#!/bin/bash

export PYRO_SERIALIZERS_ACCEPTED=json

# which address should the Pyro nameserver run on?
PYRO_HOST_IP='127.0.0.1'

# Session name argument
SES_NAME='FishFaceStartup'

# start in detached mode
/usr/bin/screen -dmS $SES_NAME /usr/bin/python -m Pyro4.naming --host=$PYRO_HOST_IP

# wait 4 seconds to make sure Pyro has had time to start up
sleep 4

# set up the imagery server
/usr/bin/screen -S $SES_NAME -X screen /usr/bin/python /home/pi/raspi_imagery_server.py