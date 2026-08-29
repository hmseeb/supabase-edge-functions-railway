#!/usr/bin/env python3
"""Build the Supabase regeneration project in the Auromations workspace."""

import base64
import hashlib
import hmac
import json
import pathlib
import re
import secrets
import string
import sys
from typing import Any

SKILL = pathlib.Path("~/.claude/skills/create-template-for-railway/scripts").expanduser()
sys.path.insert(0, str(SKILL))
import rw  # pyright: ignore[reportMissingImports]

WORKSPACE = "fc4796db-2c6c-4354-a564-d4a1d900af53"
ROOT = pathlib.Path(__file__).parent
BUILD_SHEET = ROOT / "template.json"
STATE = ROOT / ".state" / "source.json"
CREDENTIALS = pathlib.Path("/tmp/supabase-source-credentials.json")
PLACEHOLDER_ORIGIN = "https://placeholder.invalid"
REFERENCE = re.compile(r"\$\{\{([^}]+)}}")
GENERATOR = re.compile(r'^secret\((\d+)(?:,\s*"([^"]+)")?\)$')


def gql(document: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    return rw.gql(document, variables)


def random_value(length: int, alphabet: str | None = None) -> str:
    chars = alphabet or string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


def derive_api_key(jwt_secret: str, role: str) -> str:
    def b64url(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode().rstrip("=")

    header = b64url(b'{"alg":"HS256","typ":"JWT"}')
    payload = b64url(
        json.dumps(
            {
                "role": role,
                "iss": "supabase",
                "iat": 1735689600,
                "exp": 2524608000,
            },
            separators=(",", ":"),
        ).encode()
    )
    signature = b64url(
        hmac.new(jwt_secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    )
    return f"{header}.{payload}.{signature}"


class Variables:
    def __init__(self, sheet: dict[str, Any]) -> None:
        self.services = sheet["services"]
        self.origin = PLACEHOLDER_ORIGIN
        self.cache: dict[tuple[str, str], str] = {}

    def value(self, service: str, key: str) -> str:
        cache_key = (service, key)
        if cache_key in self.cache:
            return self.cache[cache_key]
        raw = self.services[service].get("variables", {})[key]
        generated = GENERATOR.fullmatch(raw.removeprefix("${{").removesuffix("}}").strip())
        if raw.startswith("${{") and raw.endswith("}}") and generated:
            value = random_value(int(generated.group(1)), generated.group(2))
            self.cache[cache_key] = value
            return value

        def replace(match: re.Match[str]) -> str:
            reference = match.group(1).strip()
            if reference.startswith("secret("):
                generator = GENERATOR.fullmatch(reference)
                if not generator:
                    raise ValueError(f"invalid generator: {reference}")
                return random_value(int(generator.group(1)), generator.group(2))
            namespace, separator, attribute = reference.partition(".")
            if not separator:
                raise ValueError(f"unqualified reference: {reference}")
            if attribute == "RAILWAY_PRIVATE_DOMAIN":
                return f"{namespace}.railway.internal"
            if attribute == "RAILWAY_PUBLIC_DOMAIN" and namespace == "gateway":
                return self.origin.removeprefix("https://")
            if namespace in self.services and attribute in self.services[namespace].get("variables", {}):
                return self.value(namespace, attribute)
            raise ValueError(f"unknown reference: {reference}")

        value = REFERENCE.sub(replace, raw)
        self.cache[cache_key] = value
        return value

    def for_service(self, service: str) -> dict[str, str]:
        return {
            key: self.value(service, key)
            for key in self.services[service].get("variables", {})
        }

    def set_origin(self, origin: str) -> None:
        self.origin = origin
        for cache_key in list(self.cache):
            service, key = cache_key
            raw = self.services[service].get("variables", {}).get(key, "")
            if "gateway.RAILWAY_PUBLIC_DOMAIN" in raw:
                del self.cache[cache_key]


def create_service(
    project_id: str,
    environment_id: str,
    name: str,
    image: str,
    variables: dict[str, str],
    *,
    start: str | None = None,
    healthcheck: str | None = None,
) -> str:
    service = gql(
        """mutation($input: ServiceCreateInput!) {
             serviceCreate(input: $input) { id name }
           }""",
        {
            "input": {
                "projectId": project_id,
                "environmentId": environment_id,
                "name": name,
                "source": {"image": image},
                "variables": variables,
            }
        },
    )["serviceCreate"]
    update: dict[str, Any] = {"restartPolicyType": "ALWAYS"}
    if start:
        update["startCommand"] = start
    if healthcheck:
        update["healthcheckPath"] = healthcheck
    gql(
        """mutation($serviceId: String!, $environmentId: String!, $input: ServiceInstanceUpdateInput!) {
             serviceInstanceUpdate(serviceId: $serviceId, environmentId: $environmentId, input: $input)
           }""",
        {"serviceId": service["id"], "environmentId": environment_id, "input": update},
    )
    print(f"created {name}: {service['id']}")
    return service["id"]


def main() -> None:
    sheet = json.loads(BUILD_SHEET.read_text())
    values = Variables(sheet)
    project = gql(
        """mutation($input: ProjectCreateInput!) {
             projectCreate(input: $input) {
               id
               environments { edges { node { id name } } }
             }
           }""",
        {"input": {"name": "supabase-edge-functions-source", "workspaceId": WORKSPACE}},
    )["projectCreate"]
    project_id = project["id"]
    environment_id = next(
        edge["node"]["id"]
        for edge in project["environments"]["edges"]
        if edge["node"]["name"] == "production"
    )
    print(f"project: {project_id}")

    services: dict[str, str] = {}

    def attach_volume(service_id: str, mount_path: str) -> None:
        gql(
            """mutation($input: VolumeCreateInput!) { volumeCreate(input: $input) { id } }""",
            {
                "input": {
                    "projectId": project_id,
                    "environmentId": environment_id,
                    "serviceId": service_id,
                    "mountPath": mount_path,
                }
            },
        )

    db_spec = sheet["services"]["db"]
    services["db"] = create_service(
        project_id,
        environment_id,
        "db",
        db_spec["image"],
        values.for_service("db"),
    )
    attach_volume(services["db"], db_spec["volume"]["mountPath"])

    gateway_spec = sheet["services"]["gateway"]
    services["gateway"] = create_service(
        project_id,
        environment_id,
        "gateway",
        gateway_spec["image"],
        values.for_service("gateway"),
        healthcheck=gateway_spec["healthcheckPath"],
    )
    domain = gql(
        """mutation($input: ServiceDomainCreateInput!) {
             serviceDomainCreate(input: $input) { domain }
           }""",
        {
            "input": {
                "environmentId": environment_id,
                "serviceId": services["gateway"],
                "targetPort": gateway_spec["domain"]["targetPortOnSource"],
            }
        },
    )["serviceDomainCreate"]["domain"]
    origin = f"https://{domain}"
    values.set_origin(origin)
    gql(
        """mutation($input: VariableCollectionUpsertInput!) {
             variableCollectionUpsert(input: $input)
           }""",
        {
            "input": {
                "projectId": project_id,
                "environmentId": environment_id,
                "serviceId": services["gateway"],
                "replace": False,
                "variables": values.for_service("gateway"),
            }
        },
    )
    print(f"gateway: {origin}")

    for name, spec in sheet["services"].items():
        if name in services:
            continue
        services[name] = create_service(
            project_id,
            environment_id,
            name,
            spec["image"],
            values.for_service(name),
            start=spec.get("startCommand"),
            healthcheck=spec.get("healthcheckPath"),
        )
        if spec.get("volume"):
            attach_volume(services[name], spec["volume"]["mountPath"])

    for service_id in services.values():
        gql(
            """mutation($serviceId: String!, $environmentId: String!) {
                 serviceInstanceDeployV2(serviceId: $serviceId, environmentId: $environmentId)
               }""",
            {"serviceId": service_id, "environmentId": environment_id},
        )

    state = {
        "projectId": project_id,
        "environmentId": environment_id,
        "origin": origin,
        "services": services,
    }
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2) + "\n")

    jwt_secret = values.value("db", "JWT_SECRET")
    credentials = {
        "origin": origin,
        "dashboardUsername": values.value("gateway", "DASHBOARD_USERNAME"),
        "dashboardPassword": values.value("gateway", "DASHBOARD_PASSWORD"),
        "anonKey": derive_api_key(jwt_secret, "anon"),
        "serviceRoleKey": derive_api_key(jwt_secret, "service_role"),
        "postgresPassword": values.value("db", "POSTGRES_PASSWORD"),
    }
    CREDENTIALS.write_text(json.dumps(credentials, indent=2) + "\n")
    CREDENTIALS.chmod(0o600)
    print(json.dumps(state, indent=2))
    print(f"credentials: {CREDENTIALS}")


if __name__ == "__main__":
    main()
