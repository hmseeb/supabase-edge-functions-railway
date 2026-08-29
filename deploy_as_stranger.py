#!/usr/bin/env python3
"""Deploy the repaired template into a fresh project exactly like the button."""

import json
import pathlib
import sys
import time
from typing import Any

SKILL = pathlib.Path("~/.claude/skills/create-template-for-railway/scripts").expanduser()
sys.path.insert(0, str(SKILL))
import build_source
import rw  # pyright: ignore[reportMissingImports]

ROOT = pathlib.Path(__file__).parent
WORKSPACE = "fc4796db-2c6c-4354-a564-d4a1d900af53"
TEMPLATE_STATE = ROOT / ".state" / "template.json"
SCRATCH_STATE = ROOT / ".state" / "scratch.json"


def gql(document: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    return rw.gql(document, variables)


def main() -> None:
    template_state = json.loads(TEMPLATE_STATE.read_text())
    template = gql(
        "query($code: String!) { template(code: $code) { id serializedConfig } }",
        {"code": template_state["code"]},
    )["template"]
    deployed = gql(
        """mutation($input: TemplateDeployV2Input!) {
             templateDeployV2(input: $input) { projectId workflowId }
           }""",
        {
            "input": {
                "templateId": template["id"],
                "workspaceId": WORKSPACE,
                "serializedConfig": template["serializedConfig"],
            }
        },
    )["templateDeployV2"]
    project_id = deployed["projectId"]
    print(f"scratch project: {project_id}")

    deadline = time.monotonic() + 300
    environment_id = ""
    services: dict[str, str] = {}
    while time.monotonic() < deadline:
        project = gql(
            """query($id: String!) {
                 project(id: $id) {
                   environments { edges { node { id name } } }
                   services { edges { node { id name } } }
                 }
               }""",
            {"id": project_id},
        )["project"]
        production = [
            edge["node"]["id"]
            for edge in project["environments"]["edges"]
            if edge["node"]["name"] == "production"
        ]
        services = {
            edge["node"]["name"]: edge["node"]["id"]
            for edge in project["services"]["edges"]
        }
        if production and len(services) == 11:
            environment_id = production[0]
            break
        time.sleep(5)
    if not environment_id:
        raise RuntimeError(f"template workflow did not create all services: {sorted(services)}")

    domains = gql(
        """query($projectId: String!, $environmentId: String!, $serviceId: String!) {
             domains(projectId: $projectId, environmentId: $environmentId, serviceId: $serviceId) {
               serviceDomains { domain targetPort }
             }
           }""",
        {
            "projectId": project_id,
            "environmentId": environment_id,
            "serviceId": services["gateway"],
        },
    )["domains"]["serviceDomains"]
    if len(domains) != 1 or domains[0]["targetPort"] != 8000:
        raise RuntimeError(f"unexpected gateway domains: {domains}")
    origin = f"https://{domains[0]['domain']}"

    def variables(service: str) -> dict[str, str]:
        return gql(
            """query($projectId: String!, $environmentId: String!, $serviceId: String!) {
                 variables(
                   projectId: $projectId,
                   environmentId: $environmentId,
                   serviceId: $serviceId,
                   unrendered: false
                 )
               }""",
            {
                "projectId": project_id,
                "environmentId": environment_id,
                "serviceId": services[service],
            },
        )["variables"]

    db_variables = variables("db")
    gateway_variables = variables("gateway")
    jwt_secret = db_variables["JWT_SECRET"]
    credentials = {
        "origin": origin,
        "dashboardUsername": gateway_variables["DASHBOARD_USERNAME"],
        "dashboardPassword": gateway_variables["DASHBOARD_PASSWORD"],
        "anonKey": build_source.derive_api_key(jwt_secret, "anon"),
        "serviceRoleKey": build_source.derive_api_key(jwt_secret, "service_role"),
        "postgresPassword": db_variables["POSTGRES_PASSWORD"],
    }
    credentials_path = pathlib.Path(f"/tmp/supabase-scratch-{project_id}-credentials.json")
    credentials_path.write_text(json.dumps(credentials, indent=2) + "\n")
    credentials_path.chmod(0o600)

    state = {
        "projectId": project_id,
        "environmentId": environment_id,
        "origin": origin,
        "workflowId": deployed["workflowId"],
        "services": services,
        "credentialsPath": str(credentials_path),
    }
    SCRATCH_STATE.parent.mkdir(exist_ok=True)
    SCRATCH_STATE.write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
