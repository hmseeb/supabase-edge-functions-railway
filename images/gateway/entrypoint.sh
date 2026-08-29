#!/bin/sh
set -eu

export ANON_KEY_VAR=ANON_KEY
export SERVICE_KEY_VAR=SERVICE_ROLE_KEY
export ANON_KEY_ASYMMETRIC="${ANON_KEY_ASYMMETRIC:-}"
export SERVICE_ROLE_KEY_ASYMMETRIC="${SERVICE_ROLE_KEY_ASYMMETRIC:-}"
export SUPABASE_PUBLISHABLE_KEY="${SUPABASE_PUBLISHABLE_KEY:-}"
export SUPABASE_SECRET_KEY="${SUPABASE_SECRET_KEY:-}"

exec /usr/local/bin/derive-keys.sh \
  /usr/local/bin/supabase-envoy-entrypoint.sh "$@"
