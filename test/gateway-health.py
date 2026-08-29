#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
upstream = (root / "images/gateway/lds.upstream.template.yaml").read_text()
custom = (root / "images/gateway/lds.template.yaml").read_text()
begin = "                      # RAILWAY_HEALTHCHECK_BEGIN\n"
end = "                      # RAILWAY_HEALTHCHECK_END\n"

assert custom.count(begin) == 1, "missing Railway healthcheck block"
assert custom.count(end) == 1, "missing Railway healthcheck block terminator"
prefix, remainder = custom.split(begin, 1)
block, suffix = remainder.split(end, 1)
assert prefix + suffix == upstream, "gateway config changed outside the healthcheck block"
assert "prefix: /healthz" in block
assert "status: 200" in block
assert "envoy.filters.http.basic_auth" in block
assert block.count("disabled: true") == 1
assert "envoy.filters.http.rbac" in block
assert "action: ALLOW" in block
assert "allow_all:" in block
print("ok: /healthz is the only Envoy route change")
