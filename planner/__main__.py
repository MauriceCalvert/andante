"""CLI entry point: python -m planner brief.yaml > plan.yaml"""
import sys
from pathlib import Path

import yaml

from planner.planner import build_plan
from planner.serializer import serialize_plan
from planner.plannertypes import Brief
from engine.validate import validate_brief_yaml


def main() -> None:
    """Run planner CLI."""
    if len(sys.argv) < 2:
        print("Usage: python -m planner <brief.yaml> [--seed N]", file=sys.stderr)
        print("       Reads brief, outputs plan YAML to stdout", file=sys.stderr)
        sys.exit(1)
    brief_path: Path = Path(sys.argv[1])
    seed: int | None = None
    if "--seed" in sys.argv:
        seed_idx: int = sys.argv.index("--seed")
        if seed_idx + 1 < len(sys.argv):
            seed = int(sys.argv[seed_idx + 1])
    if not brief_path.exists():
        print(f"Error: File not found: {brief_path}", file=sys.stderr)
        sys.exit(1)
    with open(brief_path, encoding="utf-8") as f:
        content: str = f.read()
    # YAML doesn't allow tabs for indentation - convert to spaces
    content = content.replace("\t", "  ")
    data: dict = yaml.safe_load(content)
    validate_brief_yaml(data)
    brief_data: dict = data.get("brief", data)
    brief: Brief = Brief(
        affect=brief_data["affect"],
        genre=brief_data["genre"],
        forces=brief_data["forces"],
        bars=brief_data["bars"],
        virtuosic=brief_data.get("virtuosic", False),
    )
    plan = build_plan(brief, seed=seed)
    yaml_str: str = serialize_plan(plan)
    print(yaml_str)


if __name__ == "__main__":
    main()
