#!/usr/bin/env python3
"""Publish the verified template and set its listing metadata."""

import json
import pathlib
import sys

SKILL = pathlib.Path("~/.claude/skills/create-template-for-railway/scripts").expanduser()
sys.path.insert(0, str(SKILL))
import rw  # pyright: ignore[reportMissingImports]

ROOT = pathlib.Path(__file__).parent
WORKSPACE = "fc4796db-2c6c-4354-a564-d4a1d900af53"
LISTING = json.loads((ROOT / "listing.json").read_text())
README = (ROOT / "TEMPLATE_OVERVIEW.md").read_text()
STATE = ROOT / ".state" / "template.json"


def main() -> None:
    template = json.loads(STATE.read_text())
    published = rw.gql(
        """mutation($id: String!, $input: TemplatePublishInput!) {
             templatePublish(id: $id, input: $input) { id code name isApproved }
           }""",
        {
            "id": template["id"],
            "input": {
                "category": LISTING["category"],
                "description": LISTING["description"],
                "readme": README,
                "workspaceId": WORKSPACE,
            },
        },
    )["templatePublish"]

    rw.gql(
        """mutation($id: String!, $input: TemplateUpsertSettingsInput!) {
             templateUpsertSettings(id: $id, input: $input) { id code }
           }""",
        {
            "id": published["id"],
            "input": {
                "workspaceId": WORKSPACE,
                "name": LISTING["name"],
                "image": LISTING["image"],
                "description": LISTING["description"],
            },
        },
        internal=True,
    )

    listing = rw.gql(
        """query($code: String!) {
             template(code: $code) {
               id code name description category image isApproved
             }
           }""",
        {"code": published["code"]},
    )["template"]
    STATE.write_text(json.dumps({**template, **listing}, indent=2) + "\n")
    print(json.dumps(listing, indent=2))
    print(f"deploy url: https://railway.com/deploy/{listing['code']}")


if __name__ == "__main__":
    main()
