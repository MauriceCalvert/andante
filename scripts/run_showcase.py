"""Run the showcase generation.

Usage:
    python -m scripts.run_showcase

This is a shortcut for:
    python -m scripts.run_pipeline invention c_major default -o output/showcase
"""
from pathlib import Path

from scripts.run_pipeline import run_from_args


OUTPUT_DIR: Path = Path(__file__).parent.parent / "output" / "showcase"


def main() -> None:
    """Run the showcase."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating showcase: invention in C major, default affect\n")

    run_from_args(
        genre="invention",
        key="c_major",
        affect="default",
        output_dir=OUTPUT_DIR,
        output_name="showcase",
    )

    print("\nDone! Open showcase.midi in a MIDI player to listen.")


if __name__ == "__main__":
    main()
