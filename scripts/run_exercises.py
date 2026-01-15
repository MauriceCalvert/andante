"""Generate all exercise pieces from briefs/exercises/*.brief."""
import sys
from fractions import Fraction
from pathlib import Path

import yaml

from planner.planner import build_plan
from planner.serializer import serialize_plan
from planner.plannertypes import Brief
from planner.motif_loader import load_motif
from engine.pipeline import execute_and_export
from engine.key import Key
from engine.pitch import FloatingNote
from engine.note import Note
from engine.output import Music21Writer

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


def has_structure(data: dict) -> bool:
    """Check if YAML has frame and structure (composed exercise)."""
    return "frame" in data and "structure" in data


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
    seed = brief.get("seed", 42)

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


def run_exercise(brief_path: Path) -> None:
    """Generate one exercise from brief or composed file."""
    name: str = brief_path.stem
    print(f"  {name}...", end=" ", flush=True)
    with open(brief_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Case 1: Has frame + structure but no material -> inject material
    if has_structure(data) and not has_material(data):
        data = inject_material(data)
        yaml_str = yaml.dump(data, default_flow_style=None, sort_keys=False, allow_unicode=True)
        plan_path: Path = EXERCISES_OUT / f"{name}_full.yaml"
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(yaml_str)
        output_path: Path = EXERCISES_OUT / name
        notes = execute_and_export(yaml_str, str(output_path))
        bars: int = data["brief"]["bars"]
        print(f"{len(notes)} notes, {bars} bars (generated material)")
        # Export subject MIDI - parse plan to get material
        from engine.plan_parser import parse_yaml
        plan = parse_yaml(yaml_str)
        export_subject_midi(plan, EXERCISES_OUT / f"{name}_subject")

    # Case 2: Complete plan with material -> execute directly
    elif has_structure(data) and has_material(data):
        with open(brief_path, encoding="utf-8") as f:
            yaml_str: str = f.read()
        plan_path: Path = EXERCISES_OUT / f"{name}_full.yaml"
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(yaml_str)
        output_path: Path = EXERCISES_OUT / name
        notes = execute_and_export(yaml_str, str(output_path))
        bars: int = data["brief"]["bars"]
        print(f"{len(notes)} notes, {bars} bars (composed)")
        # Export subject MIDI - parse plan to get material
        from engine.plan_parser import parse_yaml
        plan = parse_yaml(yaml_str)
        export_subject_midi(plan, EXERCISES_OUT / f"{name}_subject")
    else:
        brief_data = data.get("brief", data)
        brief: Brief = Brief(
            affect=brief_data["affect"],
            genre=brief_data["genre"],
            forces=brief_data["forces"],
            bars=brief_data["bars"],
            motif_source=brief_data.get("motif_source"),
        )
        # Load user motif if specified
        user_motif = None
        if brief.motif_source:
            user_motif = load_motif(brief.motif_source)
        plan = build_plan(brief, user_motif=user_motif)
        yaml_str: str = serialize_plan(plan)
        plan_path: Path = EXERCISES_OUT / f"{name}_full.yaml"
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(yaml_str)
        output_path: Path = EXERCISES_OUT / name
        notes = execute_and_export(yaml_str, str(output_path))
        print(f"{len(notes)} notes, {plan.actual_bars} bars")
        export_subject_midi(plan, EXERCISES_OUT / f"{name}_subject")


def main() -> None:
    """Generate exercises. Accepts path to .brief file or filter name."""
    EXERCISES_OUT.mkdir(parents=True, exist_ok=True)
    arg: str | None = sys.argv[1] if len(sys.argv) > 1 else None

    # Check if arg is a path to a .brief file
    if arg and (arg.endswith(".brief") or Path(arg).exists()):
        brief_path = Path(arg)
        if not brief_path.exists():
            print(f"Brief file not found: {brief_path}")
            return
        print(f"Running single brief: {brief_path}\n")
        run_exercise(brief_path)
        print(f"\nGenerated 1 exercise in {EXERCISES_OUT}")
        return

    # Otherwise treat as filter name for exercises in EXERCISES_SRC
    briefs: list[Path] = sorted(EXERCISES_SRC.glob("*.brief"))
    if arg:
        briefs = [b for b in briefs if arg in b.stem]
    if not briefs:
        print(f"No brief files found in {EXERCISES_SRC}")
        return
    print(f"Found {len(briefs)} exercises in {EXERCISES_SRC}\n")
    for brief_path in briefs:
        run_exercise(brief_path)
    print(f"\nGenerated {len(briefs)} exercises in {EXERCISES_OUT}")


if __name__ == "__main__":
    main()
