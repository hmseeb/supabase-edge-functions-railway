#!/usr/bin/env python3
"""Drive a real Supabase user journey against a deployed project."""

import argparse
import base64
import json
import os
import pathlib
import secrets
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

ROOT = pathlib.Path(__file__).parent
DEFAULT_STATE = ROOT / ".state" / "source.json"
DEFAULT_CREDENTIALS = pathlib.Path("/tmp/supabase-source-credentials.json")
PIXEL = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZQmcAAAAASUVORK5CYII="
)


def request(
    origin: str,
    path: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    payload: Any | None = None,
    body: bytes | None = None,
    timeout: int = 30,
) -> tuple[int, dict[str, str], bytes]:
    parsed_origin = urllib.parse.urlsplit(origin)
    if parsed_origin.scheme != "https" or not parsed_origin.netloc:
        raise ValueError("verification origin must be an absolute HTTPS URL")
    if not path.startswith("/"):
        raise ValueError("verification path must start with /")
    data = body
    request_headers = dict(headers or {})
    if payload is not None:
        data = json.dumps(payload).encode()
        request_headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(
        f"{origin}{path}", data=data, headers=request_headers, method=method
    )
    try:
        # Origin is restricted to an absolute HTTPS URL above.
        with urllib.request.urlopen(req, timeout=timeout) as response:  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), error.read()


def require(label: str, result: tuple[int, dict[str, str], bytes], allowed: set[int]) -> bytes:
    status, _, body = result
    if status not in allowed:
        message = body.decode(errors="replace")[:500]
        raise RuntimeError(f"{label}: HTTP {status}: {message}")
    print(f"ok: {label}")
    return body


def api_headers(key: str) -> dict[str, str]:
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def wait_ready(origin: str, username: str, password: str, anon: str) -> None:
    deadline = time.monotonic() + 900
    basic = base64.b64encode(f"{username}:{password}".encode()).decode()
    pending = ""
    while time.monotonic() < deadline:
        checks = {
            "gateway": request(origin, "/healthz", timeout=10)[0] == 200,
            "studio": request(
                origin, "/", headers={"Authorization": f"Basic {basic}"}, timeout=20
            )[0]
            == 200,
            "auth": request(origin, "/auth/v1/health", headers=api_headers(anon), timeout=10)[0]
            == 200,
        }
        if all(checks.values()):
            print("ok: Gateway, Studio and Auth are ready")
            return
        pending = ", ".join(name for name, ok in checks.items() if not ok)
        time.sleep(10)
    raise RuntimeError(f"not ready within 15 minutes: {pending}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=pathlib.Path, default=DEFAULT_STATE)
    parser.add_argument("--credentials", type=pathlib.Path, default=DEFAULT_CREDENTIALS)
    parser.add_argument("--evidence", type=pathlib.Path)
    args = parser.parse_args()

    state = json.loads(args.state.read_text())
    credentials = json.loads(args.credentials.read_text())
    origin = state["origin"]
    anon = credentials["anonKey"]
    service = credentials["serviceRoleKey"]
    wait_ready(origin, credentials["dashboardUsername"], credentials["dashboardPassword"], anon)

    function_body = require(
        "Edge Function hello",
        request(origin, "/functions/v1/hello", headers=api_headers(anon)),
        {200},
    )
    if b"Hello from Edge Functions" not in function_body:
        raise RuntimeError("Edge Function returned unexpected body")

    email = f"railway-{secrets.token_hex(6)}@example.com"
    password = f"Rly-{secrets.token_urlsafe(18)}"
    signup = require(
        "Auth signup",
        request(
            origin,
            "/auth/v1/signup",
            method="POST",
            headers=api_headers(anon),
            payload={"email": email, "password": password},
        ),
        {200},
    )
    if not json.loads(signup).get("user"):
        raise RuntimeError("Auth signup returned no user")
    login = require(
        "Auth password login",
        request(
            origin,
            "/auth/v1/token?grant_type=password",
            method="POST",
            headers=api_headers(anon),
            payload={"email": email, "password": password},
        ),
        {200},
    )
    if not json.loads(login).get("access_token"):
        raise RuntimeError("Auth login returned no access token")

    sql = """
      create table if not exists public.railway_template_proof (
        id bigint generated by default as identity primary key,
        value text not null
      );
      alter table public.railway_template_proof enable row level security;
      drop policy if exists service_role_all on public.railway_template_proof;
      create policy service_role_all on public.railway_template_proof
        for all to service_role using (true) with check (true);
      do $$ begin
        if not exists (
          select 1 from pg_publication_tables
          where pubname = 'supabase_realtime'
            and schemaname = 'public'
            and tablename = 'railway_template_proof'
        ) then
          alter publication supabase_realtime add table public.railway_template_proof;
        end if;
      end $$;
      notify pgrst, 'reload schema';
    """
    require(
        "postgres-meta SQL",
        request(
            origin,
            "/pg/query",
            method="POST",
            headers=api_headers(service),
            payload={"query": sql},
        ),
        {200, 201},
    )
    time.sleep(3)
    require(
        "REST write",
        request(
            origin,
            "/rest/v1/railway_template_proof",
            method="POST",
            headers={**api_headers(service), "Prefer": "return=representation"},
            payload={"value": "write-read-proof"},
        ),
        {200, 201},
    )
    rows = require(
        "REST read",
        request(
            origin,
            "/rest/v1/railway_template_proof?value=eq.write-read-proof&select=value",
            headers=api_headers(service),
        ),
        {200},
    )
    if json.loads(rows) != [{"value": "write-read-proof"}]:
        raise RuntimeError("REST read did not return the written row")

    bucket_name = "journey-proof"
    require(
        "Storage bucket create",
        request(
            origin,
            "/storage/v1/bucket",
            method="POST",
            headers=api_headers(service),
            payload={"id": bucket_name, "name": bucket_name, "public": True},
        ),
        {200, 201, 409},
    )
    require(
        "Storage upload",
        request(
            origin,
            f"/storage/v1/object/{bucket_name}/pixel.png",
            method="POST",
            headers={
                **api_headers(service),
                "Content-Type": "image/png",
                "x-upsert": "true",
            },
            body=PIXEL,
        ),
        {200, 201},
    )
    downloaded = require(
        "Storage read",
        request(origin, f"/storage/v1/object/public/{bucket_name}/pixel.png"),
        {200},
    )
    if downloaded != PIXEL:
        raise RuntimeError("Storage read did not match uploaded bytes")

    realtime_env = {
        **os.environ,
        "SUPABASE_ORIGIN": origin,
        "SUPABASE_ANON_KEY": anon,
        "SUPABASE_SERVICE_KEY": service,
    }
    subprocess.run(
        ["node", str(ROOT / "test" / "realtime.mjs")],
        env=realtime_env,
        check=True,
        timeout=60,
    )

    evidence = {
        "projectId": state["projectId"],
        "origin": origin,
        "verified": [
            "Studio Basic Auth",
            "Auth signup and password login",
            "postgres-meta SQL",
            "REST write and read",
            "Storage upload and read",
            "Edge Function invocation",
            "Realtime database insert event",
        ],
    }
    evidence_path = args.evidence or args.state.with_name("source-evidence.json")
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"evidence: {evidence_path}")


if __name__ == "__main__":
    main()
