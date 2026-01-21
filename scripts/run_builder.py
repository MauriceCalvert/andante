"""Generate music from a brief file.

Usage:
    python -m scripts.run_builder <brief_name> [-v]

Examples:
    python -m scripts.run_builder freude_invention
    python -m scripts.run_builder freude_invention -v

Brief files are YAML with genre, key, affect fields.
"""
import argparse
from pathlib import Path

import yaml

from planner.planner import generate_to_files


BRIEFS_DIR: Path = Path(__file__).parent.parent / "briefs" / "builder"
OUTPUT_DIR: Path = Path(__file__).parent.parent / "output" / "builder"


def run_builder(input_path: Path, output_name: str, verbose: bool = False) -> int:
    """Run builder on brief file and export to output path.

    Returns:
        Number of notes generated
    """
    print(f"Loading {input_path}...")

    with open(input_path, encoding="utf-8") as f:
        data: dict = yaml.safe_load(f)

    # Extract brief fields
    brief_data: dict = data.get("brief", data)
    genre: str = brief_data.get("genre", "invention")
    key: str = brief_data.get("key", "c_major")
    affect: str = brief_data.get("affect", "confident")

    if verbose:
        print(f"  Genre: {genre}")
        print(f"  Key: {key}")
        print(f"  Affect: {affect}")

    print(f"Generating {genre} in {key} with {affect} affect...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    result = generate_to_files(genre, key, affect, OUTPUT_DIR, output_name)

    note_count: int = len(result.soprano) + len(result.bass)
    print(f"  Generated {note_count} notes")
    print(f"  Tempo: {result.tempo} BPM")
    print(f"Output written to:")
    print(f"  {OUTPUT_DIR / output_name}.note")
    print(f"  {OUTPUT_DIR / output_name}.midi")

    return note_count


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate music from brief file"
    )
    parser.add_argument("input", help="Brief name (e.g., freude_invention)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    input_name: str = args.input
    if not input_name.endswith(".brief"):
        input_name += ".brief"

    input_path: Path = BRIEFS_DIR / input_name
    if not input_path.exists():
        print(f"Brief not found: {input_path}")
        print(f"Available briefs in {BRIEFS_DIR}:")
        for brief in BRIEFS_DIR.glob("*.brief"):
            print(f"  {brief.stem}")
        return

    output_name: str = input_path.stem
    note_count: int = run_builder(input_path, output_name, verbose=args.verbose)
    print(f"\nDone: {note_count} notes generated")


if __name__ == "__main__":
    main()
