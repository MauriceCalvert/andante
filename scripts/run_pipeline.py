"""Full pipeline: Generate music from genre/key/affect.

Usage:
    python -m scripts.run_pipeline <genre> <key> <affect> [output_name]

Examples:
    python -m scripts.run_pipeline invention c_major confident
    python -m scripts.run_pipeline invention c_major confident my_invention

This uses the 6-layer architecture:
    Layer 1: Rhetorical - Genre -> Trajectory + rhythm + tempo
    Layer 2: Tonal - Affect -> Tonal plan + density + modality
    Layer 3: Schematic - Tonal plan -> Schema chain
    Layer 4: Thematic - Schema + rhythm -> Subject
    Layer 5: Metric - Schema chain -> Bar assignments + arrivals
    Layer 6: Textural - Genre + chain + subject -> Treatment sequence
"""
import sys
from pathlib import Path

from planner.planner import generate_to_files


OUTPUT_DIR: Path = Path(__file__).parent.parent / "output"


def main() -> None:
    """Run full pipeline."""
    if len(sys.argv) < 4:
        print("Usage: python -m scripts.run_pipeline <genre> <key> <affect> [output_name]")
        print("Example: python -m scripts.run_pipeline invention c_major confident")
        sys.exit(1)

    genre: str = sys.argv[1]
    key: str = sys.argv[2]
    affect: str = sys.argv[3]
    output_name: str = sys.argv[4] if len(sys.argv) > 4 else f"{genre}_{key}_{affect}"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Generating {genre} in {key} with {affect} affect...")
    result = generate_to_files(genre, key, affect, OUTPUT_DIR, output_name)

    print(f"  Soprano notes: {len(result.soprano)}")
    print(f"  Bass notes: {len(result.bass)}")
    print(f"  Tempo: {result.tempo} BPM")
    print(f"  Metre: {result.metre}")
    print(f"Output written to:")
    print(f"  {OUTPUT_DIR / output_name}.note")
    print(f"  {OUTPUT_DIR / output_name}.midi")
    print("Done!")


if __name__ == "__main__":
    main()
