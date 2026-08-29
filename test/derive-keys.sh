#!/bin/sh
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
SCRIPT="$ROOT/boot/derive-keys.sh"
SECRET=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef # nosemgrep: generic.secrets.security.detected-generic-secret.detected-generic-secret
EXPECTED_ANON='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiIsImlzcyI6InN1cGFiYXNlIiwiaWF0IjoxNzM1Njg5NjAwLCJleHAiOjI1MjQ2MDgwMDB9.AoJA3uzSAiOjplMFO4jya3k2jpGOfH8De7dOOQ5dJCk' # nosemgrep: generic.secrets.security.detected-jwt-token.detected-jwt-token
EXPECTED_SERVICE='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIiwiaXNzIjoic3VwYWJhc2UiLCJpYXQiOjE3MzU2ODk2MDAsImV4cCI6MjUyNDYwODAwMH0.IweWqju2SCgcb_zNt_Ob5_p9Pf0gukHO3vxlRYaDDiU' # nosemgrep: generic.secrets.security.detected-jwt-token.detected-jwt-token

# The child shell must expand the generated keys, not this test process.
# shellcheck disable=SC2016
actual=$(
  JWT_SECRET="$SECRET" \
  ANON_KEY_VAR=ANON_KEY \
  SERVICE_KEY_VAR=SERVICE_ROLE_KEY \
  "$SCRIPT" /bin/sh -c 'printf "%s\n%s\n" "$ANON_KEY" "$SERVICE_ROLE_KEY"'
)

expected=$(printf '%s\n%s' "$EXPECTED_ANON" "$EXPECTED_SERVICE")
[ "$actual" = "$expected" ] || {
  echo "derived keys do not match the pinned HS256 vectors" >&2
  exit 1
}

echo "ok: deterministic Supabase API keys"
