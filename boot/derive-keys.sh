#!/bin/sh
# Derive Supabase's legacy anon and service-role API keys from one JWT secret.
# Fixed claims make independently starting services produce byte-identical keys.
set -eu

: "${JWT_SECRET:?JWT_SECRET is required}"
: "${ANON_KEY_VAR:=ANON_KEY}"
: "${SERVICE_KEY_VAR:=SERVICE_ROLE_KEY}"
: "${JWT_ISS:=supabase}"
: "${JWT_IAT:=1735689600}"
: "${JWT_EXP_AT:=2524608000}"

b64url() {
  openssl base64 -A | tr '+/' '-_' | tr -d '='
}

jwt_for_role() {
  role=$1
  header=$(printf '%s' '{"alg":"HS256","typ":"JWT"}' | b64url)
  payload=$(printf '{"role":"%s","iss":"%s","iat":%s,"exp":%s}' \
    "$role" "$JWT_ISS" "$JWT_IAT" "$JWT_EXP_AT" | b64url)
  signature=$(printf '%s.%s' "$header" "$payload" \
    | openssl dgst -sha256 -hmac "$JWT_SECRET" -binary | b64url)
  printf '%s.%s.%s' "$header" "$payload" "$signature"
}

set_if_empty() {
  variable=$1
  role=$2
  eval "current=\${$variable:-}"
  if [ -z "$current" ]; then
    value=$(jwt_for_role "$role")
    export "$variable=$value"
    echo "derive-keys: generated $variable for role $role" >&2
  else
    echo "derive-keys: using operator-supplied $variable" >&2
  fi
}

set_if_empty "$ANON_KEY_VAR" anon
set_if_empty "$SERVICE_KEY_VAR" service_role

exec "$@"
