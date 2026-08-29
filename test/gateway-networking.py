#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
gateway = root / "images/gateway"
upstream = (gateway / "cds.upstream.yaml").read_text()
custom = (gateway / "cds.yaml").read_text()

replacements = {
    "address: auth\n": "address: auth.railway.internal\n",
    "address: rest\n": "address: rest.railway.internal\n",
    "address: realtime-dev.supabase-realtime\n": "address: realtime-dev.railway.internal\n",
    "address: storage\n": "address: storage.railway.internal\n",
    "address: functions\n": "address: functions.railway.internal\n",
    "address: meta\n": "address: meta.railway.internal\n",
    "address: studio\n": "address: studio.railway.internal\n",
}
expected = upstream
for old, new in replacements.items():
    assert expected.count(old) == 1, f"upstream address changed: {old.strip()}"
    expected = expected.replace(old, new)

assert custom == expected, "CDS changed beyond Railway private DNS hostnames"
print("ok: Envoy uses only audited Railway private DNS changes")
