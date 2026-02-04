"""CLI entry point: python -m planner invention default [key]

When key is omitted, derives appropriate key from affect using Mattheson's
Affektenlehre (baroque_theory.md section 8.1).
"""
import sys
from pathlib import Path

from planner.planner import generate_to_files


def main() -> None:
    """Run planner CLI."""
    if len(sys.argv) < 3:
        print("Usage: python -m planner <genre> <affect> [key] [output_dir] [name]", file=sys.stderr)
        print("       Example: python -m planner invention default", file=sys.stderr)
        print("       Example: python -m planner invention default c_major", file=sys.stderr)
        print("       When key is omitted, derives from affect per Mattheson", file=sys.stderr)
        sys.exit(1)
    genre: str = sys.argv[1]
    affect: str = sys.argv[2]
    key: str | None = sys.argv[3] if len(sys.argv) > 3 and "_" in sys.argv[3] else None
    # Skip key arg if present when finding output_dir/name
    arg_offset: int = 4 if key else 3
    output_dir: Path = Path(sys.argv[arg_offset]) if len(sys.argv) > arg_offset else Path("output")
    name: str = sys.argv[arg_offset + 1] if len(sys.argv) > arg_offset + 1 else f"{genre}_{affect}"
    output_dir.mkdir(parents=True, exist_ok=True)
    result = generate_to_files(genre=genre, affect=affect, output_dir=output_dir, name=name, key=key)
    key_used: str = key if key else "(derived from affect)"
    print(f"Generated {len(result.soprano)} soprano notes, {len(result.bass)} bass notes")
    print(f"Key: {key_used}")
    print(f"Output: {output_dir / name}.note, {output_dir / name}.midi")


if __name__ == "__main__":
    main()
