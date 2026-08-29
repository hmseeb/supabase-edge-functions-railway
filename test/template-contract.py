#!/usr/bin/env python3
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
config = json.loads((root / "template.json").read_text())
services = config["services"]
expected = {
    "db", "gateway", "auth", "rest", "realtime-dev", "storage",
    "imgproxy", "meta", "functions", "studio", "pooler",
}
assert set(services) == expected
assert config["bucket"]["name"] == "supabase-storage"
assert [name for name, service in services.items() if "domain" in service] == ["gateway"]
assert services["gateway"]["domain"]["targetPortOnSource"] == 8000
assert services["gateway"]["healthcheckPath"] == "/healthz"
assert services["db"]["volume"]["mountPath"] == "/var/lib/postgresql/data"
assert all("latest" not in service["image"] for service in services.values())

blob = json.dumps(config)
assert "—" not in blob, "em dash is forbidden in template copy"
refs = re.findall(r"\$\{\{([^}]+)\}\}", blob)
for ref in refs:
    assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-", ref), f"UUID reference: {ref}"
    namespace = ref.split(".", 1)[0].strip()
    if namespace.startswith("secret(") or namespace in {"RAILWAY_PUBLIC_DOMAIN"}:
        continue
    assert namespace in expected | {"supabase-storage"}, f"unknown reference namespace: {ref}"

print("ok: template topology and references")
