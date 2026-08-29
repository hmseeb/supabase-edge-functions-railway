#!/bin/sh
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)

"$ROOT/test/derive-keys.sh"
"$ROOT/test/upstream-assets.sh"
"$ROOT/test/gateway-networking.py"
"$ROOT/test/gateway-health.py"
"$ROOT/test/template-contract.py"
"$ROOT/test/image-contract.sh"
