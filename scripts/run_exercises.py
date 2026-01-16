"""Generate all exercise pieces from briefs/exercises/*.brief."""
import sys
from fractions import Fraction
from pathlib import Path

import yaml

from planner.planner import build_plan
from planner.serializer import serialize_plan
from planner.plannertypes import Brief, Frame, Motif
from planner.motif_loader import load_motif, load_motif_from_file
from engine.pipeline import execute_and_export
from engine.key import Key
from engine.bob import diagnose
from engine.plan_parser import parse_yaml as parse_plan_yaml
from engine.expander import expand_piece, bar_duration
from engine.realiser import realise_phrases
from engine.pitch import FloatingNote
from engine.note import Note
from engine.output import Music21Writer
from engine.validate import validate_brief_yaml

EXERCISES_SRC = Path(__file__).parent.parent / "briefs" / "exercises"
EXERCISES_OUT = Path(__file__).parent.parent / "output" / "exercises"


def export_subject_midi(plan, output_path: Path) -> None:
    """Export subject + empty bar + counter_subject as a separate MIDI file.

    Handles both Plan objects (from build_plan) and PieceAST objects (from parse_yaml).
    """
    # Handle both Plan (frame.key) and PieceAST (key) structures
    if hasattr(plan, 'frame'):
        tonic: str = plan.frame.key
        mode: str = plan.frame.mode
        subject = plan.material.subject
        cs = plan.material.counter_subject
        metre: str = plan.frame.metre
    else:
        # PieceAST structure
        tonic = plan.key
        mode = plan.mode
        subject = plan.subject
        cs = plan.subject.counter_subject
        metre = plan.metre
    key: Key = Key(tonic=tonic, mode=mode)
    num_str, den_str = metre.split("/")
    bar_dur: Fraction = Fraction(int(num_str), int(den_str))
    notes: list[Note] = []
    offset: Fraction = Fraction(0)
    median: int = 72
    prev_midi: int = median
    for deg, dur in zip(subject.degrees, subject.durations):
        midi: int = key.floating_to_midi(FloatingNote(deg), prev_midi, median)
        notes.append(Note(midiNote=midi, Offset=float(offset), Duration=float(dur), track=0))
        offset += dur
        prev_midi = midi
    offset = bar_dur * 2
    prev_midi = median
    for deg, dur in zip(cs.degrees, cs.durations):
        midi = key.floating_to_midi(FloatingNote(deg), prev_midi, median)
        notes.append(Note(midiNote=midi, Offset=float(offset), Duration=float(dur), track=0))
        offset += dur
        prev_midi = midi
    writer: Music21Writer = Music21Writer()
    writer.write(
        path=str(output_path),
        notes=notes,
        timenum=int(num_str),
        timeden=int(den_str),
        tonic=tonic,
        mode=mode,
        bpm=100,
    )
    print(f"  Exported subject MIDI to {output_path.with_suffix('.midi')}")


def has_material(data: dict) -> bool:
    """Check if YAML has material with subject defined."""
    if "material" not in data:
        return False
    return "subject" in data["material"]


def expand_file_material(data: dict) -> dict:
    """Expand file references in material section to inline degrees/durations/bars.

    If material.subject has 'file:', load it and replace with inline data.
    Same for counter_subject.

    File references can specify source mode:
        file: path/to/file.note
        mode: minor  # optional, defaults to frame mode
    """
    if "material" not in data:
        return data

    material = data["material"]
    frame_mode = data.get("frame", {}).get("mode", "minor")

    # Expand subject if it's a file reference
    if "subject" in material and "file" in material["subject"]:
        file_path = material["subject"]["file"]
        # Use source mode if specified, otherwise frame mode
        source_mode = material["subject"].get("mode", frame_mode)
        motif = load_motif_from_file(file_path, source_mode)
        material["subject"] = {
            "degrees": list(motif.degrees),
            "durations": [str(d) for d in motif.durations],
            "bars": motif.bars,
        }

    # Expand counter_subject if it's a file reference
    if "counter_subject" in material and "file" in material["counter_subject"]:
        file_path = material["counter_subject"]["file"]
        source_mode = material["counter_subject"].get("mode", frame_mode)
        motif = load_motif_from_file(file_path, source_mode)
        material["counter_subject"] = {
            "degrees": list(motif.degrees),
            "durations": [str(d) for d in motif.durations],
            "bars": motif.bars,
        }

    return data


def parse_frame(frame_data: dict) -> Frame:
    """Parse Frame from YAML data."""
    return Frame(
        key=frame_data["key"],
        mode=frame_data["mode"],
        metre=frame_data.get("metre", "4/4"),
        tempo=frame_data.get("tempo", "allegro"),
        voices=frame_data.get("voices", 2),
        upbeat=Fraction(frame_data.get("upbeat", 0)),
        form=frame_data.get("form", "through_composed"),
    )


def has_structure(data: dict) -> bool:
    """Check if YAML has frame and structure (composed exercise)."""
    return "frame" in data and "structure" in data


def get_total_bars(data: dict) -> int:
    """Get total bars from brief.bars or sum from structure phrases."""
    if "bars" in data.get("brief", {}):
        return data["brief"]["bars"]
    # Sum bars from structure
    total: int = 0
    for section in data.get("structure", {}).get("sections", []):
        for episode in section.get("episodes", []):
            for phrase in episode.get("phrases", []):
                total += phrase.get("bars", 0)
    return total


def allocate_structure_bars(data: dict) -> dict:
    """Distribute brief.bars across structure phrases when not explicitly set."""
    brief_bars: int = data.get("brief", {}).get("bars")
    if not brief_bars:
        return data

    # Collect all phrases needing bars
    sections = data["structure"]["sections"]
    phrases_needing_bars: list[dict] = []
    for sec in sections:
        for ep in sec.get("episodes", []):
            for phrase in ep.get("phrases", []):
                if "bars" not in phrase:
                    phrases_needing_bars.append(phrase)

    if not phrases_needing_bars:
        return data

    # Distribute evenly, last phrase gets remainder
    phrase_count = len(phrases_needing_bars)
    base_bars = brief_bars // phrase_count
    remainder = brief_bars % phrase_count

    for i, phrase in enumerate(phrases_needing_bars):
        phrase["bars"] = base_bars + (remainder if i == phrase_count - 1 else 0)

    # Set episode bars as sum of phrase bars
    for section in sections:
        for episode in section.get("episodes", []):
            if "bars" not in episode:
                episode["bars"] = sum(p.get("bars", 0) for p in episode.get("phrases", []))

    return data


def inject_material(data: dict) -> dict:
    """Generate and inject material into data dict."""
    from motifs.subject_generator import generate_subject
    from planner.subject import Subject

    frame = data["frame"]
    mode = frame["mode"]
    metre_str = frame.get("metre", "4/4")
    # Parse metre string like "3/4" to tuple (3, 4)
    metre_parts = metre_str.split("/")
    metre = (int(metre_parts[0]), int(metre_parts[1]))
    brief = data.get("brief", {})
    genre = brief.get("genre", "invention")
    affect = brief.get("affect")
    seed = brief.get("seed")  # None = random

    # Generate subject using head+tail system with affect-aware figurae
    generated = generate_subject(mode=mode, metre=metre, seed=seed, affect=affect)

    # Convert to 1-based degrees
    degrees = [((d % 7) + 1) for d in generated.scale_indices]

    # Convert durations to fraction strings
    dur_map = {0.0625: "1/16", 0.125: "1/8", 0.1875: "3/16", 0.25: "1/4", 0.375: "3/8", 0.5: "1/2"}
    durations = [dur_map.get(d, str(d)) for d in generated.durations]

    # Get number of bars from generated subject
    bars = generated.bars

    # Create Subject to generate counter-subject via CP-SAT
    from fractions import Fraction
    subj_degrees = tuple(degrees)
    subj_durations = tuple(Fraction(d) for d in durations)
    voice_count = frame.get("voices", 2)
    subj = Subject(subj_degrees, subj_durations, bars=bars, mode=mode, genre=genre, voice_count=voice_count)

    # Get counter-subject
    cs_degrees = list(subj.counter_subject.degrees)
    cs_durations = [str(d) for d in subj.counter_subject.durations]

    # Inject material
    data["material"] = {
        "subject": {
            "degrees": degrees,
            "durations": durations,
            "bars": bars,
        },
        "counter_subject": {
            "degrees": cs_degrees,
            "durations": cs_durations,
            "bars": bars,
        },
    }
    return data


def run_bob_diagnostic(yaml_str: str) -> None:
    """Run Bob diagnostic on a piece and print the report."""
    piece = parse_plan_yaml(yaml_str)
    expanded = expand_piece(piece)
    bar_dur = bar_duration(piece.metre)
    key = Key(tonic=piece.key, mode=piece.mode)
    # Use strict=False to get diagnostics even with violations
    realised = realise_phrases(expanded, key, bar_dur, piece.metre, strict=False)
    report = diagnose(realised, bar_duration=bar_dur, key=key)
    print(report.to_clipboard())


def run_exercise(brief_path: Path, humanise: bool = False) -> None:
    """Generate one exercise from brief or composed file."""
    name: str = brief_path.stem
    print(f"  {name}...", end=" ", flush=True)
    with open(brief_path, encoding="utf-8") as f:
        content = f.read()
    # YAML doesn't allow tabs for indentation - convert to spaces
    content = content.replace("\t", "  ")
    data = yaml.safe_load(content)

    # Validate YAML structure (catches frame fields under brief)
    validate_brief_yaml(data)

    # Expand file references in material section
    data = expand_file_material(data)

    # Case 1: Has frame + structure but no material -> allocate bars, inject material
    if has_structure(data) and not has_material(data):
        data = allocate_structure_bars(data)
        data = inject_material(data)
        yaml_str = yaml.dump(data, default_flow_style=None, sort_keys=False, allow_unicode=True)
        plan_path: Path = EXERCISES_OUT / f"{name}_full.yaml"
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(yaml_str)
        output_path: Path = EXERCISES_OUT / name
        notes = execute_and_export(yaml_str, str(output_path), humanise_output=humanise, strict=False)
        bars: int = get_total_bars(data)
        print(f"{len(notes)} notes, {bars} bars (generated material){' [humanised]' if humanise else ''}")
        # Export subject MIDI - parse plan to get material
        from engine.plan_parser import parse_yaml
        plan = parse_yaml(yaml_str)
        export_subject_midi(plan, EXERCISES_OUT / f"{name}_subject")
        run_bob_diagnostic(yaml_str)

    # Case 2: Complete plan with material -> execute directly
    elif has_structure(data) and has_material(data):
        with open(brief_path, encoding="utf-8") as f:
            yaml_str: str = f.read()
        plan_path: Path = EXERCISES_OUT / f"{name}_full.yaml"
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(yaml_str)
        output_path: Path = EXERCISES_OUT / name
        notes = execute_and_export(yaml_str, str(output_path), humanise_output=humanise, strict=False)
        bars: int = get_total_bars(data)
        print(f"{len(notes)} notes, {bars} bars (composed){' [humanised]' if humanise else ''}")
        # Export subject MIDI - parse plan to get material
        from engine.plan_parser import parse_yaml
        plan = parse_yaml(yaml_str)
        export_subject_midi(plan, EXERCISES_OUT / f"{name}_subject")
        run_bob_diagnostic(yaml_str)
    else:
        brief_data = data.get("brief", data)
        brief: Brief = Brief(
            affect=brief_data["affect"],
            genre=brief_data["genre"],
            forces=brief_data["forces"],
            bars=brief_data["bars"],
            motif_source=brief_data.get("motif_source"),
        )
        # Load user motif: from material section (file or inline) or motif_source
        user_motif = None
        user_cs = None
        if has_material(data):
            # Material already provided (expanded from file or inline)
            subj = data["material"]["subject"]
            user_motif = Motif(
                degrees=tuple(subj["degrees"]),
                durations=tuple(Fraction(d) for d in subj["durations"]),
                bars=subj["bars"],
            )
            # Also load counter_subject if provided
            if "counter_subject" in data["material"]:
                cs = data["material"]["counter_subject"]
                user_cs = Motif(
                    degrees=tuple(cs["degrees"]),
                    durations=tuple(Fraction(d) for d in cs["durations"]),
                    bars=cs["bars"],
                )
        elif brief.motif_source:
            user_motif = load_motif(brief.motif_source)
        # Parse explicit frame if provided
        user_frame = None
        if "frame" in data:
            user_frame = parse_frame(data["frame"])
        plan = build_plan(brief, user_motif=user_motif, user_frame=user_frame, user_cs=user_cs)
        yaml_str: str = serialize_plan(plan)
        plan_path: Path = EXERCISES_OUT / f"{name}_full.yaml"
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(yaml_str)
        output_path: Path = EXERCISES_OUT / name
        notes = execute_and_export(yaml_str, str(output_path), humanise_output=humanise, strict=False)
        print(f"{len(notes)} notes, {plan.actual_bars} bars{' [humanised]' if humanise else ''}")
        export_subject_midi(plan, EXERCISES_OUT / f"{name}_subject")
        run_bob_diagnostic(yaml_str)


def main() -> None:
    """Generate exercises. Accepts path to .brief file or filter name."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate exercises from brief files")
    parser.add_argument("target", nargs="?", help="Path to .brief file or filter name")
    parser.add_argument("--humanise", action="store_true", help="Apply humanisation for expressive timing/dynamics")
    args = parser.parse_args()

    EXERCISES_OUT.mkdir(parents=True, exist_ok=True)

    # Check if target is a path to a .brief file
    if args.target and (args.target.endswith(".brief") or Path(args.target).exists()):
        brief_path = Path(args.target)
        if not brief_path.exists():
            print(f"Brief file not found: {brief_path}")
            return
        print(f"Running single brief: {brief_path}\n")
        run_exercise(brief_path, humanise=args.humanise)
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
    for brief_path in briefs:
        run_exercise(brief_path, humanise=args.humanise)
    print(f"\nGenerated {len(briefs)} exercises in {EXERCISES_OUT}")


if __name__ == "__main__":
    main()
