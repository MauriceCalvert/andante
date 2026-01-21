"""Run the showcase generation for auditory verification.

Generates a piece demonstrating the full pipeline.

Usage:
    python -m scripts.run_showcase
"""
from pathlib import Path

from planner.planner import generate_to_files


OUTPUT_DIR: Path = Path(__file__).parent.parent / "output" / "showcase"


def main() -> None:
    """Run the showcase."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Running showcase generation...")
    print("This generates an invention in C major with confident affect.\n")

    result = generate_to_files("invention", "c_major", "confident", OUTPUT_DIR, "showcase")

    print(f"\nGenerated:")
    print(f"  Soprano notes: {len(result.soprano)}")
    print(f"  Bass notes: {len(result.bass)}")
    print(f"  Tempo: {result.tempo} BPM")
    print(f"  Metre: {result.metre}")
    print(f"\nOutput files in {OUTPUT_DIR}/showcase.*")
    print("Open showcase.midi in a MIDI player or DAW to listen.")


if __name__ == "__main__":
    main()
