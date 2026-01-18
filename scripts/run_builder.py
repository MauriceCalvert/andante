"""Generate music from brief/plan using builder (tree elaboration).

Usage:
    python -m scripts.run_builder <brief_name> [-v]

Examples:
    python -m scripts.run_builder freude_invention.brief
    python -m scripts.run_builder freude_invention.brief -v
"""
import argparse
from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml

from builder.export import collect_notes, export_midi, export_note
from builder.handlers import elaborate
from builder.tree import Node, yaml_to_tree
from planner.planner import build_plan
from planner.plannertypes import Brief, Frame, Motif
from planner.serializer import serialize_plan
from shared.constants import NOTE_NAME_MAP

PROJECT_DIR: Path = Path(__file__).parent.parent

BRIEFS_DIR: Path = Path(__file__).parent.parent / "briefs" / "builder"
OUTPUT_DIR: Path = Path(__file__).parent.parent / "output" / "builder"


def load_subject_from_subject_file(file_path: Path, max_notes: int = 12) -> Motif:
    """Load subject from .subject file (YAML with diatonic degrees).

    Args:
        file_path: Path to .subject file
        max_notes: Maximum number of notes to extract (default 12)

    Returns:
        Motif with diatonic degrees and source_key
    """
    assert file_path.exists(), f"Subject file not found: {file_path}"

    with open(file_path, encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)

    assert "degrees" in data, f"Subject file missing 'degrees': {file_path}"
    assert "durations" in data, f"Subject file missing 'durations': {file_path}"

    degrees: list[int] = data["degrees"][:max_notes]
    durations: list[Fraction] = [Fraction(d) for d in data["durations"][:max_notes]]
    source_key: str = data.get("source_key", "C")

    assert len(degrees) == len(durations), (
        f"Degrees ({len(degrees)}) and durations ({len(durations)}) mismatch"
    )

    total_dur: Fraction = sum(durations, Fraction(0))
    bars: int = max(1, int(total_dur.limit_denominator(1)))

    return Motif(
        degrees=tuple(degrees),
        durations=tuple(durations),
        bars=bars,
        source_key=source_key,
    )


def get_frame_from_tree(root: Node) -> dict[str, Any]:
    """Extract frame info from tree."""
    assert "frame" in root, "Tree missing 'frame' node"
    frame: Node = root["frame"]
    return {
        "key": frame["key"].value if "key" in frame else "C",
        "mode": frame["mode"].value if "mode" in frame else "major",
        "metre": frame["metre"].value if "metre" in frame else "4/4",
        "tempo": frame["tempo"].value if "tempo" in frame else "allegro",
    }


def get_key_offset(key: str, mode: str) -> int:
    """Get semitone offset for key from C."""
    offset: int = NOTE_NAME_MAP.get(key, 0)
    if mode == "minor":
        offset -= 3
    return offset % 12


def parse_metre(metre: str) -> tuple[int, int]:
    """Parse metre string like '4/4' to tuple."""
    parts: list[str] = metre.split("/")
    return (int(parts[0]), int(parts[1]))


def tempo_to_bpm(tempo: str) -> int:
    """Convert tempo name to BPM."""
    tempos: dict[str, int] = {
        "largo": 50,
        "adagio": 66,
        "andante": 76,
        "moderato": 96,
        "allegretto": 112,
        "allegro": 120,
        "vivace": 140,
        "presto": 168,
    }
    return tempos.get(tempo.lower(), 100)


def is_plan_yaml(data: dict[str, Any]) -> bool:
    """Check if data is a complete plan (has frame and structure)."""
    return "frame" in data and "structure" in data


def load_brief_and_plan(path: Path) -> tuple[dict[str, Any], str]:
    """Load file and generate plan if needed.

    Returns:
        Tuple of (data dict, plan yaml string)
    """
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)
    if is_plan_yaml(data):
        with open(path, encoding="utf-8") as f:
            return data, f.read()
    brief_data: dict[str, Any] = data.get("brief", data)
    brief: Brief = Brief(
        affect=brief_data["affect"],
        genre=brief_data["genre"],
        forces=brief_data["forces"],
        bars=brief_data["bars"],
    )
    user_frame: Frame | None = None
    if "frame" in data:
        fd: dict[str, Any] = data["frame"]
        user_frame = Frame(
            key=fd.get("key", "C"),
            mode=fd.get("mode", "major"),
            metre=fd.get("metre", "4/4"),
            tempo=fd.get("tempo", "allegro"),
            voices=fd.get("voices", 2),
            upbeat=fd.get("upbeat", 0),
            form=fd.get("form", "through_composed"),
        )
    user_motif: Motif | None = None
    if "material" in data and "subject" in data["material"]:
        subj: dict[str, Any] = data["material"]["subject"]
        if "file" in subj:
            file_rel: str = subj["file"].replace("\\", "/")
            file_path: Path = PROJECT_DIR / file_rel
            max_notes: int = subj.get("notes", 12)
            assert file_path.suffix == ".subject", (
                f"Subject file must be .subject, got: {file_path.suffix}"
            )
            user_motif = load_subject_from_subject_file(file_path, max_notes)
        elif "degrees" in subj:
            user_motif = Motif(
                degrees=tuple(subj["degrees"]),
                durations=tuple(Fraction(d) for d in subj["durations"]),
                bars=subj.get("bars", 1),
            )
    plan = build_plan(brief, user_motif=user_motif, user_frame=user_frame)
    yaml_str: str = serialize_plan(plan)
    plan_data: dict[str, Any] = yaml.safe_load(yaml_str)
    return plan_data, yaml_str


def run_builder(input_path: Path, output_path: Path, verbose: bool = False) -> int:
    """Run builder on input file and export to output path.

    Returns:
        Number of notes generated
    """
    print(f"Loading {input_path}...")
    data, yaml_str = load_brief_and_plan(input_path)
    plan_path: Path = output_path.with_suffix(".plan.yaml")
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    with open(plan_path, "w", encoding="utf-8") as f:
        f.write(yaml_str)
    print(f"  Plan written to {plan_path}")
    print("Converting to tree...")
    root: Node | None = yaml_to_tree(data)
    assert root is not None, f"Empty or invalid YAML: {input_path}"
    print("Elaborating tree...")
    result: Node = elaborate(root)
    if verbose:
        print("\n=== Result tree ===")
        result.print_tree()
    print("Collecting notes...")
    notes: list[tuple[str, int, Fraction, Fraction]] = collect_notes(result)
    print(f"  Collected {len(notes)} notes")
    frame_info: dict[str, Any] = get_frame_from_tree(result)
    key_offset: int = get_key_offset(frame_info["key"], frame_info["mode"])
    time_sig: tuple[int, int] = parse_metre(frame_info["metre"])
    bpm: int = tempo_to_bpm(frame_info["tempo"])
    print(f"  Frame: {frame_info['key']} {frame_info['mode']}, {frame_info['metre']}, {frame_info['tempo']} ({bpm} bpm)")
    print(f"Exporting to {output_path}...")
    midi_ok: bool = export_midi(
        result,
        str(output_path),
        key_offset=key_offset,
        tempo=bpm,
        time_signature=time_sig,
    )
    note_ok: bool = export_note(
        result,
        str(output_path),
        key_offset=key_offset,
        time_signature=time_sig,
    )
    if midi_ok:
        print(f"  MIDI: {output_path}.midi")
    if note_ok:
        print(f"  Note: {output_path}.note")
    return len(notes)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate music from brief/plan using builder"
    )
    parser.add_argument("input", help="Brief name (e.g., freude_invention.brief)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print elaborated tree")
    args = parser.parse_args()
    input_name: str = args.input
    if not input_name.endswith(".brief"):
        input_name += ".brief"
    input_path: Path = BRIEFS_DIR / input_name
    assert input_path.exists(), f"Brief not found: {input_path}"
    output_path: Path = OUTPUT_DIR / input_path.stem
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    note_count: int = run_builder(input_path, output_path, verbose=args.verbose)
    print(f"\nDone: {note_count} notes generated")


if __name__ == "__main__":
    main()
