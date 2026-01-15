"""CLI entry point: python -m engine plan.yaml > expanded.yaml"""
import sys
from pathlib import Path

from engine.expander import expand_piece
from engine.plan_parser import parse_file, parse_yaml
from engine.serializer import serialize_expanded


def main() -> None:
    """Run engine CLI."""
    if len(sys.argv) < 2:
        print("Usage: python -m engine <plan.yaml> [--seed N]", file=sys.stderr)
        print("       Reads plan, outputs expanded YAML to stdout", file=sys.stderr)
        sys.exit(1)
    plan_path: Path = Path(sys.argv[1])
    seed: int = 0
    if "--seed" in sys.argv:
        seed_idx: int = sys.argv.index("--seed")
        if seed_idx + 1 < len(sys.argv):
            seed = int(sys.argv[seed_idx + 1])
    if plan_path.exists():
        piece = parse_file(plan_path)
    else:
        yaml_str: str = sys.stdin.read()
        piece = parse_yaml(yaml_str)
    expanded = expand_piece(piece)
    yaml_str = serialize_expanded(piece, expanded)
    print(yaml_str)


if __name__ == "__main__":
    main()
