#!/usr/bin/env python3
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
config = json.loads((root / "template.json").read_text())
services = config["services"]
expected = {
    "db", "gateway", "auth", "rest", "realtime-dev", "storage",
    "meta", "functions", "studio", "pooler",
}
assert set(services) == expected
assert "bucket" not in config, "Railway's API cannot provision bucket instances"
assert [name for name, service in services.items() if "domain" in service] == ["gateway"]
assert services["gateway"]["domain"]["targetPortOnSource"] == 8000
assert services["gateway"]["healthcheckPath"] == "/healthz"
assert services["db"]["volume"]["mountPath"] == "/var/lib/postgresql/data"
assert services["storage"]["volume"]["mountPath"] == "/var/lib/storage"
assert services["storage"]["variables"]["STORAGE_BACKEND"] == "file"
assert services["storage"]["variables"]["FILE_STORAGE_BACKEND_PATH"] == "/var/lib/storage"
assert services["auth"]["variables"]["GOTRUE_API_HOST"] == "::"
assert all("latest" not in service["image"] for service in services.values())
for name in ("gateway", "storage", "studio", "functions"):
    assert "JWT_SECRET" in services[name]["variables"], f"{name} needs JWT_SECRET to derive API keys"

blob = json.dumps(config)
assert "—" not in blob, "em dash is forbidden in template copy"
refs = re.findall(r"\$\{\{([^}]+)\}\}", blob)
for ref in refs:
    assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-", ref), f"UUID reference: {ref}"
    namespace = ref.split(".", 1)[0].strip()
    if namespace.startswith("secret(") or namespace in {"RAILWAY_PUBLIC_DOMAIN"}:
        continue
    assert namespace in expected, f"unknown reference namespace: {ref}"

print("ok: template topology and references")
