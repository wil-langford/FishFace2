#!/usr/bin/env bash

REDIS_PASSWORD=$(cat ~/etc/redis/redis_password)

echo "redis://:${REDIS_PASSWORD}@localhost"