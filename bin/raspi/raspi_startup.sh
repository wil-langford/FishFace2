#!/bin/bash

# Session name argument
SES_NAME='FishFaceServers'

# start in detached mode
/usr/bin/screen -dmS "${SES_NAME}" /usr/bin/python /home/pi/raspi_imagery_server.py