#!/bin/sh
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
EXPECTED_VERSION='self-hosted/v0.8.0 241bb11c0627f2981746d37033f57dbfa81d29b0'

actual_version=$(cat "$ROOT/UPSTREAM_VERSION")
[ "$actual_version" = "$EXPECTED_VERSION" ] || {
  echo "UPSTREAM_VERSION is not the reviewed Supabase release" >&2
  exit 1
}

(
  cd "$ROOT"
  shasum -a 256 -c test/upstream.sha256
)

echo "ok: vendored files match Supabase $EXPECTED_VERSION"
