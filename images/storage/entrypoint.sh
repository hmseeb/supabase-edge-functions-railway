#!/bin/sh
set -eu

export ANON_KEY_VAR=ANON_KEY
export SERVICE_KEY_VAR=SERVICE_KEY
exec /usr/local/bin/derive-keys.sh docker-entrypoint.sh "$@"
