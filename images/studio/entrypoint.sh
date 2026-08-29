#!/bin/sh
set -eu

export ANON_KEY_VAR=SUPABASE_ANON_KEY
export SERVICE_KEY_VAR=SUPABASE_SERVICE_KEY
exec /usr/local/bin/derive-keys.sh docker-entrypoint.sh "$@"
