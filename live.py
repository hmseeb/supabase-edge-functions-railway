#!/usr/bin/env python3
"""Inspect or freshly deploy services in the live source or scratch project."""

import argparse
import json
import pathlib
import sys
from typing import Any

SKILL = pathlib.Path("~/.claude/skills/create-template-for-railway/scripts").expanduser()
sys.path.insert(0, str(SKILL))
import rw  # pyright: ignore[reportMissingImports]

ROOT = pathlib.Path(__file__).parent


def gql(document: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    return rw.gql(document, variables)


def latest(project_id: str, environment_id: str, service_id: str) -> dict[str, Any] | None:
    deployments = gql(
        """query($projectId: String!, $environmentId: String!, $serviceId: String!) {
             deployments(
               first: 1,
               input: {
                 projectId: $projectId,
                 environmentId: $environmentId,
                 serviceId: $serviceId
               }
             ) { edges { node { id status createdAt } } }
           }""",
        {
            "projectId": project_id,
            "environmentId": environment_id,
            "serviceId": service_id,
        },
    )["deployments"]["edges"]
    return deployments[0]["node"] if deployments else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("status", "deploy", "logs", "events"))
    parser.add_argument("services", nargs="*")
    parser.add_argument("--state", type=pathlib.Path, default=ROOT / ".state" / "source.json")
    args = parser.parse_args()
    state = json.loads(args.state.read_text())
    project_id = state["projectId"]
    environment_id = state["environmentId"]
    services = state["services"]
    targets = args.services or sorted(services)

    if args.command == "status":
        for name in targets:
            deployment = latest(project_id, environment_id, services[name])
            status = deployment["status"] if deployment else "NO_DEPLOY"
            deployment_id = deployment["id"] if deployment else ""
            print(f"{name:14} {status:12} {deployment_id}")
        return

    if args.command == "deploy":
        for name in targets:
            gql(
                """mutation($serviceId: String!, $environmentId: String!) {
                     serviceInstanceDeployV2(
                       serviceId: $serviceId,
                       environmentId: $environmentId
                     )
                   }""",
                {"serviceId": services[name], "environmentId": environment_id},
            )
            print(f"deploying {name}")
        return

    for name in targets:
        deployment = latest(project_id, environment_id, services[name])
        if not deployment:
            print(f"{name}: no deployment")
            continue
        if args.command == "logs":
            print(f"--- {name} ({deployment['status']})")
            for kind in ("buildLogs", "deploymentLogs"):
                logs = gql(
                    f"""query($id: String!) {{
                          {kind}(deploymentId: $id, limit: 150) {{ message severity }}
                        }}""",
                    {"id": deployment["id"]},
                )[kind]
                for line in logs:
                    print(line["message"])
        else:
            print(f"--- {name} ({deployment['status']})")
            events = gql(
                """query($id: String!) {
                     deploymentEvents(id: $id) {
                       edges { node { step status reason createdAt } }
                     }
                   }""",
                {"id": deployment["id"]},
            )["deploymentEvents"]["edges"]
            for edge in events:
                event = edge["node"]
                print(
                    f"{event['createdAt']} {event['step']:24} "
                    f"{event['status']:10} {event.get('reason') or ''}"
                )


if __name__ == "__main__":
    main()
