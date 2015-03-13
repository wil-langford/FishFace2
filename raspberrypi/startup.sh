#!/bin/bash

# Session name argument
SES_NAME='FishFaceWorkers'

# set up the imagery server
/usr/bin/screen -dmS $SES_NAME -X screen /usr/bin/python /home/pi/raspi_imagery_server.py