#!/usr/bin/env python3
"""Generate a Railway template skeleton from the live source project."""

import json
import pathlib
import sys

SKILL = pathlib.Path("~/.claude/skills/create-template-for-railway/scripts").expanduser()
sys.path.insert(0, str(SKILL))
import rw  # pyright: ignore[reportMissingImports]

ROOT = pathlib.Path(__file__).parent
SOURCE = ROOT / ".state" / "source.json"
OUTPUT = ROOT / ".state" / "generated.json"


def main() -> None:
    source = json.loads(SOURCE.read_text())
    generated = rw.gql(
        """mutation($input: TemplateGenerateInput!) {
             templateGenerate(input: $input) { id code serializedConfig canvasConfig }
           }""",
        {
            "input": {
                "projectId": source["projectId"],
                "environmentId": source["environmentId"],
            }
        },
    )["templateGenerate"]
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(generated, indent=2) + "\n")
    print(json.dumps({"id": generated["id"], "code": generated["code"]}, indent=2))
    print(f"generated config: {OUTPUT}")


if __name__ == "__main__":
    main()
