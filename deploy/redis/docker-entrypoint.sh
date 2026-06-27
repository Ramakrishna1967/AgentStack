#!/bin/sh
set -e

if [ -z "${REDIS_PASSWORD}" ]; then
    echo "ERROR: REDIS_PASSWORD environment variable is not set. Refusing to start Redis without authentication." >&2
    exit 1
fi

exec redis-server /usr/local/etc/redis/redis.conf --requirepass "$REDIS_PASSWORD"
