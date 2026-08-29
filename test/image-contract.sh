#!/bin/sh
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)

assert_from() {
  file=$1
  expected=$2
  actual=$(awk '/^FROM / { print; exit }' "$ROOT/$file")
  [ "$actual" = "FROM $expected" ] || {
    echo "$file: expected FROM $expected, got: $actual" >&2
    exit 1
  }
}

assert_from images/db/Dockerfile supabase/postgres:17.6.1.136
assert_from images/gateway/Dockerfile envoyproxy/envoy:v1.39.0
assert_from images/functions/Dockerfile supabase/edge-runtime:v1.74.0
assert_from images/pooler/Dockerfile supabase/supavisor:2.9.5
assert_from images/storage/Dockerfile supabase/storage-api:v1.60.4
assert_from images/studio/Dockerfile supabase/studio:2026.08.03-sha-022b374

if rg -n '(^|[/:])latest([[:space:]]|$)' "$ROOT/images"; then
  echo "wrapper images must not use latest tags" >&2
  exit 1
fi

for script in \
  boot/derive-keys.sh \
  images/db/entrypoint.sh \
  images/gateway/entrypoint.sh \
  images/gateway/upstream-entrypoint.sh \
  images/pooler/entrypoint.sh
do
  shellcheck "$ROOT/$script"
done

for dockerfile in "$ROOT"/images/*/Dockerfile; do
  docker build --check -f "$dockerfile" "$ROOT"
done

echo "ok: wrapper image contracts"
