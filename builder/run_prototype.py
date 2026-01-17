"""End-to-end test for the builder prototype."""
from pathlib import Path

import yaml

from builder.tree import yaml_to_tree
from builder.handlers import elaborate
from builder.export import export_midi, collect_notes

OUTPUT_DIR = Path(__file__).parent.parent / "output"


def main() -> None:
    input_path = Path(__file__).parent.parent / "output" / "tests" / "level_01_full.yaml"
    output_path = OUTPUT_DIR / "prototype"

    print(f"Loading {input_path}...")
    with open(input_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    print("Converting to tree...")
    root = yaml_to_tree(data)

    print("Elaborating tree...")
    result = elaborate(root)

    print("\n=== Result tree ===")
    result.print_tree()

    print("\n=== Collecting notes ===")
    notes = collect_notes(result)
    print(f"Collected {len(notes)} notes:")
    for role, diatonic, duration, offset in notes[:10]:
        print(f"  {role}: diatonic={diatonic}, duration={duration}, offset={offset}")
    if len(notes) > 10:
        print(f"  ... and {len(notes) - 10} more")

    print(f"\n=== Exporting to {output_path}.mid ===")
    success = export_midi(
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
