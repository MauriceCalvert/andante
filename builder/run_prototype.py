"""End-to-end test for the builder prototype."""
from fractions import Fraction
from pathlib import Path
from typing import Any, TextIO

import yaml

from builder.tree import Node, yaml_to_tree
from builder.handlers import elaborate
from builder.export import export_midi, collect_notes

OUTPUT_DIR: Path = Path(__file__).parent.parent / "output"


def main() -> None:
    input_path: Path = Path(__file__).parent.parent / "output" / "tests" / "level_01_full.yaml"
    output_path: Path = OUTPUT_DIR / "prototype"

    print(f"Loading {input_path}...")
    f: TextIO
    with open(input_path, encoding="utf-8") as f:
        data: Any = yaml.safe_load(f)

    print("Converting to tree...")
    root: Node | None = yaml_to_tree(data)

    print("Elaborating tree...")
    result: Node = elaborate(root)

    print("\n=== Result tree ===")
    result.print_tree()

    print("\n=== Collecting notes ===")
    notes: list[tuple[str, int, Fraction, Fraction]] = collect_notes(result)
    print(f"Collected {len(notes)} notes:")
    role: str
    diatonic: int
    duration: Fraction
    offset: Fraction
    for role, diatonic, duration, offset in notes[:10]:
        print(f"  {role}: diatonic={diatonic}, duration={duration}, offset={offset}")
    if len(notes) > 10:
        print(f"  ... and {len(notes) - 10} more")

    print(f"\n=== Exporting to {output_path}.mid ===")
    success: bool = export_midi(
        result,
        str(output_path),
        key_offset=0,
        tempo=80,
        time_signature=(3, 4),
    )

    if success:
        print(f"SUCCESS: MIDI file written to {output_path}.mid")
    else:
        print("FAILED: Could not write MIDI file")


if __name__ == "__main__":
    main()
