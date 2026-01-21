"""Generate all exercise pieces from briefs/tests/*.brief.

Usage:
    python -m scripts.run_exercises [filter]
    python -m scripts.run_exercises showcase

This generates music from brief files using the 6-layer architecture.
"""
import argparse
from pathlib import Path

import yaml

from planner.planner import generate_to_files


EXERCISES_SRC: Path = Path(__file__).parent.parent / "briefs" / "tests"
EXERCISES_OUT: Path = Path(__file__).parent.parent / "output" / "tests"


def run_exercise(brief_path: Path) -> int:
    """Generate one exercise from brief file.

    Returns:
        Number of notes generated
    """
    name: str = brief_path.stem
    print(f"  {name}...", end=" ", flush=True)

    with open(brief_path, encoding="utf-8") as f:
        data: dict = yaml.safe_load(f)

    # Extract brief fields
    brief_data: dict = data.get("brief", data)
    genre: str = brief_data.get("genre", "invention")
    key: str = brief_data.get("key", "c_major")
    affect: str = brief_data.get("affect", "confident")

    result = generate_to_files(genre, key, affect, EXERCISES_OUT, name)

    note_count: int = len(result.soprano) + len(result.bass)
    print(f"{note_count} notes, tempo {result.tempo}")

    return note_count


def main() -> None:
    """Generate exercises. Accepts path to .brief file or filter name."""
    parser = argparse.ArgumentParser(description="Generate exercises from brief files")
    parser.add_argument("target", nargs="?", help="Path to .brief file or filter name")
    args = parser.parse_args()

    EXERCISES_OUT.mkdir(parents=True, exist_ok=True)

    # Check if target is a path to a .brief file
    if args.target and (args.target.endswith(".brief") or Path(args.target).exists()):
        brief_path = Path(args.target)
        if not brief_path.exists():
            print(f"Brief file not found: {brief_path}")
            return
        print(f"Running single brief: {brief_path}\n")
        run_exercise(brief_path)
        print(f"\nGenerated 1 exercise in {EXERCISES_OUT}")
        return

    # Otherwise treat as filter name for exercises in EXERCISES_SRC
    briefs: list[Path] = sorted(EXERCISES_SRC.glob("*.brief"))
    if args.target:
        briefs = [b for b in briefs if args.target in b.stem]
    if not briefs:
        print(f"No brief files found in {EXERCISES_SRC}")
        return

    print(f"Found {len(briefs)} exercises in {EXERCISES_SRC}\n")
    total_notes: int = 0
    for brief_path in briefs:
        total_notes += run_exercise(brief_path)

    print(f"\nGenerated {len(briefs)} exercises ({total_notes} notes) in {EXERCISES_OUT}")


if __name__ == "__main__":
    main()
