#!/usr/bin/env python3
"""Copy a generated skeleton into an editable, fully repaired template."""

import json
import pathlib
import re
import sys
import uuid
from typing import Any

SKILL = pathlib.Path("~/.claude/skills/create-template-for-railway/scripts").expanduser()
sys.path.insert(0, str(SKILL))
import rw  # pyright: ignore[reportMissingImports]

ROOT = pathlib.Path(__file__).parent
WORKSPACE = "fc4796db-2c6c-4354-a564-d4a1d900af53"
BUILD_SHEET = ROOT / "template.json"
GENERATED = ROOT / ".state" / "generated.json"
STATE = ROOT / ".state" / "template.json"
ICON = "https://supabase.com/dashboard/img/supabase-logo.svg"

DESCRIPTIONS = {
    ("db", "POSTGRES_PASSWORD"): "Generated password shared by Supabase database roles.",
    ("db", "JWT_SECRET"): "Generated HS256 secret. Do not rotate without replacing every API key.",
    ("db", "ANON_KEY"): "Optional migration override. Leave blank to derive it from JWT_SECRET.",
    ("db", "SERVICE_ROLE_KEY"): "Optional migration override. Leave blank to derive it from JWT_SECRET.",
    ("gateway", "DASHBOARD_USERNAME"): "HTTP Basic Auth username for Studio.",
    ("gateway", "DASHBOARD_PASSWORD"): "Generated HTTP Basic Auth password for Studio.",
    ("auth", "GOTRUE_SITE_URL"): "Default redirect after authentication. Change to your application URL.",
    ("auth", "GOTRUE_URI_ALLOW_LIST"): "Comma-separated additional authentication redirect URLs.",
    ("auth", "GOTRUE_MAILER_AUTOCONFIRM"): "True for first-run testing. Set false after configuring SMTP.",
    ("auth", "GOTRUE_DISABLE_SIGNUP"): "Set true to close public registration.",
    ("storage", "FILE_SIZE_LIMIT"): "Maximum upload size in bytes. Default is 50 MB.",
    ("studio", "DEFAULT_PROJECT_NAME"): "Project name shown in Studio. Display only, safe to change anytime.",
    ("studio", "DEFAULT_ORGANIZATION_NAME"): "Organization name shown in Studio. Display only, safe to change anytime.",
}


def variable(service: str, key: str, default: str) -> dict[str, Any]:
    spec: dict[str, Any] = {"isOptional": default == "", "defaultValue": default}
    description = DESCRIPTIONS.get((service, key))
    if description:
        spec["description"] = description
    return spec


def fresh_config(config: dict[str, Any]) -> dict[str, Any]:
    service_ids = {old: str(uuid.uuid4()) for old in config["services"]}
    rebuilt: dict[str, Any] = {"services": {}}
    for old_id, service in config["services"].items():
        copied = json.loads(json.dumps(service))
        if copied.get("volumeMounts"):
            copied["volumeMounts"] = {
                service_ids.get(volume_id, str(uuid.uuid4())): mount
                for volume_id, mount in copied["volumeMounts"].items()
            }
        rebuilt["services"][service_ids[old_id]] = copied
    return rebuilt


def main() -> None:
    sheet = json.loads(BUILD_SHEET.read_text())
    generated = json.loads(GENERATED.read_text())
    config = fresh_config(generated["serializedConfig"])
    by_name = {service["name"]: service for service in config["services"].values()}
    expected_names = set(sheet["services"])
    if set(by_name) != expected_names:
        raise RuntimeError(
            f"generated services {sorted(by_name)} do not match build sheet {sorted(expected_names)}"
        )

    for name, expected in sheet["services"].items():
        service = by_name[name]
        service["variables"] = {
            key: variable(name, key, value)
            for key, value in expected.get("variables", {}).items()
        }
        service["icon"] = (
            "https://devicons.railway.app/i/postgresql.svg" if name == "db" else ICON
        )
        # Pin images from the build sheet so the template never inherits a
        # stale tag that the live source project happens to be running.
        service["source"] = {"image": expected["image"]}
        deploy = service.setdefault("deploy", {})
        deploy["restartPolicyType"] = expected.get("restartPolicy", "ALWAYS")
        if expected.get("startCommand"):
            deploy["startCommand"] = expected["startCommand"]
        if expected.get("healthcheckPath"):
            deploy["healthcheckPath"] = expected["healthcheckPath"]
        if name == "db":
            service.setdefault("networking", {})["tcpProxies"] = {"5432": {}}
        if name == "pooler":
            service.setdefault("networking", {})["tcpProxies"] = {"6543": {}}

    template_id = str(uuid.uuid4())
    saved = rw.gql(
        """mutation($id: String!, $input: TemplateUpsertConfigInput!) {
             templateUpsertConfig(id: $id, input: $input) { id code }
           }""",
        {
            "id": template_id,
            "input": {
                "name": sheet["name"],
                "workspaceId": WORKSPACE,
                "serializedConfig": config,
                "canvasConfig": {},
            },
        },
        internal=True,
    )["templateUpsertConfig"]

    readback = rw.gql(
        "query($code: String!) { template(code: $code) { id code serializedConfig } }",
        {"code": saved["code"]},
    )["template"]
    problems: list[str] = []
    returned = {
        service["name"]: service
        for service in readback["serializedConfig"]["services"].values()
    }
    for name, expected in sheet["services"].items():
        service = returned.get(name)
        if not service:
            problems.append(f"missing service {name}")
            continue
        for key, value in expected.get("variables", {}).items():
            actual = service.get("variables", {}).get(key, {}).get("defaultValue")
            if actual != value:
                problems.append(f"{name}.{key}: {actual!r} != {value!r}")
        deploy = service.get("deploy", {})
        if expected.get("healthcheckPath") and deploy.get("healthcheckPath") != expected["healthcheckPath"]:
            problems.append(f"{name}.healthcheckPath did not persist")
        if not expected.get("healthcheckPath") and deploy.get("healthcheckPath"):
            problems.append(f"{name} kept an unwanted healthcheck")
        actual_image = (service.get("source") or {}).get("image")
        if actual_image != expected["image"]:
            problems.append(f"{name}.image is {actual_image!r}, wanted {expected['image']!r}")
        for port in (expected.get("tcpProxyPort"),):
            if port and str(port) not in (service.get("networking") or {}).get("tcpProxies", {}):
                problems.append(f"{name} lost its TCP proxy on {port}")
    blob = json.dumps(readback["serializedConfig"])
    for reference in re.findall(r"\$\{\{[^}]+}}", blob):
        if re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-", reference):
            problems.append(f"UUID-keyed reference: {reference}")
    for name, expected in sheet["services"].items():
        service = returned.get(name, {})
        mounts = [
            mount.get("mountPath")
            for mount in (service.get("volumeMounts") or {}).values()
        ]
        wanted = expected.get("volume", {}).get("mountPath")
        if wanted and wanted not in mounts:
            problems.append(f"{name} lost its {wanted} volume")
    for problem in problems:
        print(f"MISMATCH {problem}")
    if problems:
        raise SystemExit(f"repair readback found {len(problems)} problems")

    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps({"id": saved["id"], "code": saved["code"]}, indent=2) + "\n")
    print(json.dumps({"id": saved["id"], "code": saved["code"]}, indent=2))
    print("clean readback")


if __name__ == "__main__":
    main()
