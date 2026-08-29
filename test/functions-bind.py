#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
dockerfile = (root / "images/functions/Dockerfile").read_text()
assert '"--ip", "::"' in dockerfile, (
    "Edge Runtime must listen on :: because Railway private networking is IPv6"
)
print("ok: Edge Runtime binds IPv6")
