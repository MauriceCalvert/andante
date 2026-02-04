"""Full pipeline: Generate music from genre/affect or brief files.

When key is omitted, derives appropriate key from affect using Mattheson's
Affektenlehre (baroque_theory.md section 8.1).

Usage:
    python -m scripts.run_pipeline <genre> <affect> [key] [output_name]
    python -m scripts.run_pipeline <brief_file>
    python -m scripts.run_pipeline <brief_directory>

Examples:
    python -m scripts.run_pipeline invention default
    python -m scripts.run_pipeline invention default c_major
    python -m scripts.run_pipeline briefs/builder/freude_invention.brief
    python -m scripts.run_pipeline briefs/tests/

Options:
    -o, --output-dir DIR    Output directory (default: output/)
    -v, --verbose           Verbose output
    -trace N                Trace level 0-3 (0=off, 1=summary, 2=detail, 3=fine)

This uses the 6-layer architecture:
    Layer 1: Rhetorical - Genre -> Trajectory + rhythm + tempo
    Layer 2: Tonal - Affect -> Tonal plan + density + modality
    Layer 3: Schematic - Tonal plan -> Schema chain
    Layer 4: Metric - Schema chain -> Bar assignments + phrase anchors
    Layer 5: Thematic - Phrase anchors -> Pitches per phrase
    Layer 6: Textural - Genre + chain + subject -> Treatment sequence
"""
import argparse
from pathlib import Path

import yaml

from builder.faults import find_faults, print_faults
from motifs.fugue_loader import LoadedFugue, load_fugue
from builder.types import Composition
from planner.planner import generate_to_files
from shared.tracer import get_tracer, reset_tracer, set_trace_level


SCRIPT_DIR: Path = Path(__file__).resolve().parent
PROJECT_DIR: Path = SCRIPT_DIR.parent
DEFAULT_OUTPUT_DIR: Path = PROJECT_DIR / "output"

AFFECT_ALIASES: dict[str, str] = {
    "joy": "Freudigkeit",
    "bright": "Freudigkeit",
    "confident": "Entschlossenheit",
}

KEY_ALIASES: dict[str, str] = {
    "c": "c_major",
    "yes. then justidfc_major": "c_major",
    "cmajor": "c_major",
}


def normalize_key(key: str) -> str:
    """Normalize key name to config file name."""
    normalized = key.lower().replace(" ", "_")
    return KEY_ALIASES.get(normalized, normalized)


def normalize_affect(affect: str) -> str:
    """Normalize affect name to config file name."""
    normalized = affect.lower().replace(" ", "_")
    return AFFECT_ALIASES.get(normalized, normalized)


def run_from_args(
    genre: str,
    affect: str,
    output_dir: Path,
    key: str | None = None,
    output_name: str | None = None,
    verbose: bool = False,
    tempo: int | None = None,
    trace_level: int = 0,
    fugue: LoadedFugue | None = None,
    sections_override: tuple[dict, ...] | None = None,
) -> Composition:
    """Generate from explicit genre/affect arguments."""
    affect = normalize_affect(affect=affect)
    if key is not None:
        key = normalize_key(key=key)
    name: str = output_name or f"{genre}_{affect}"
    if verbose:
        print(f"  Genre: {genre}")
        print(f"  Key: {key if key else '(from affect)'}")
        print(f"  Affect: {affect}")
    key_display: str = key if key else "(derived from affect)"
    print(f"Generating {genre} with {affect} affect in {key_display}...")
    result = generate_to_files(genre=genre, affect=affect, output_dir=output_dir, name=name, key=key, tempo=tempo, fugue=fugue, sections_override=sections_override)
    for vid, vnotes in result.voices.items():
        print(f"  {vid}: {len(vnotes)} notes")
    print(f"  Tempo: {result.tempo} BPM")
    print(f"Output: {output_dir / name}.note, {output_dir / name}.midi")
    if trace_level > 0:
        trace_path = output_dir / "trace.txt"
        get_tracer().write_to_file(path=trace_path)
        print(f"Trace: {trace_path}")
    print()
    voice_list: list[tuple] = list(result.voices.values())
    faults = find_faults(voices=voice_list, metre=result.metre)
    print_faults(faults=faults)
    return result


def _convert_brief_sections(brief_sections: list[dict]) -> tuple[dict, ...]:
    """Convert brief sections format to genre sections format.

    Brief format:
        - name: opening
          phrases:
            - {schema: do_re_mi, treatment: statement, bars: 2, tonal_target: I}

    Genre format:
        - name: opening
          schema_sequence: [do_re_mi, ...]
    """
    result: list[dict] = []
    for section in brief_sections:
        converted: dict = {}
        assert "name" in section, f"Section missing 'name': {section}"
        converted["name"] = section["name"]
        phrases: list[dict] = section.get("phrases", [])
        schema_sequence: list[str] = [p["schema"] for p in phrases if "schema" in p]
        converted["schema_sequence"] = schema_sequence
        if "lead_voice" in section:
            converted["lead_voice"] = section["lead_voice"]
        if "accompany_texture" in section:
            converted["accompany_texture"] = section["accompany_texture"]
        if "tonal_path" in section:
            converted["tonal_path"] = section["tonal_path"]
        if "final_cadence" in section:
            converted["final_cadence"] = section["final_cadence"]
        result.append(converted)
    return tuple(result)


def run_from_brief(
    brief_path: Path,
    output_dir: Path,
    verbose: bool = False,
    trace_level: int = 0,
) -> Composition:
    """Generate from a .brief file."""
    print(f"Loading {brief_path.name}...")
    with open(brief_path, encoding="utf-8") as f:
        data: dict = yaml.safe_load(f)
    brief_data: dict = data.get("brief", data)
    frame_data: dict = data.get("frame", {})
    genre: str = brief_data.get("genre", "invention")
    key: str | None = brief_data.get("key")
    if key is None and "key" in frame_data:
        tonic: str = frame_data["key"].lower()
        mode: str = frame_data.get("mode", "major").lower()
        key = f"{tonic}_{mode}"
    affect: str = brief_data.get("affect", "default")
    raw_tempo = brief_data.get("tempo") or frame_data.get("tempo")
    tempo: int | None = None
    if raw_tempo is not None:
        assert isinstance(raw_tempo, int), (
            f"tempo must be integer BPM, got '{raw_tempo}' ({type(raw_tempo).__name__}). "
            f"Use e.g. 'tempo: 100' not 'tempo: allegro'"
        )
        tempo = raw_tempo
    subject_name: str | None = brief_data.get("subject")
    fugue: LoadedFugue | None = None
    if subject_name:
        fugue = load_fugue(name=subject_name)
        if verbose:
            print(f"  Loaded fugue: {subject_name}")
    sections_override: tuple[dict, ...] | None = None
    if "sections" in data:
        sections_override = _convert_brief_sections(brief_sections=data["sections"])
        if verbose:
            print(f"  Sections override: {len(sections_override)} sections")
    output_name: str = brief_path.stem
    return run_from_args(genre=genre, affect=affect, output_dir=output_dir, key=key, output_name=output_name, verbose=verbose, tempo=tempo, trace_level=trace_level, fugue=fugue, sections_override=sections_override)


def run_from_directory(
    directory: Path,
    output_dir: Path,
    verbose: bool = False,
    trace_level: int = 0,
) -> int:
    """Generate from all .brief files in a directory."""
    briefs: list[Path] = sorted(directory.glob("*.brief"))
    if not briefs:
        print(f"No .brief files found in {directory}")
        return 0
    print(f"Found {len(briefs)} brief files in {directory}\n")
    total_notes: int = 0
    for brief_path in briefs:
        reset_tracer()
        set_trace_level(level=trace_level)
        result = run_from_brief(brief_path=brief_path, output_dir=output_dir, verbose=verbose, trace_level=trace_level)
        total_notes += sum(len(v) for v in result.voices.values())
        print()
    print(f"Generated {len(briefs)} pieces ({total_notes} total notes)")
    return len(briefs)


def main() -> None:
    """Run the pipeline."""
    parser = argparse.ArgumentParser(
        description="Generate music from genre/affect or brief files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m scripts.run_pipeline invention default
  python -m scripts.run_pipeline invention default c_major
  python -m scripts.run_pipeline briefs/builder/freude_invention.brief
  python -m scripts.run_pipeline briefs/tests/ -o output/tests
  python -m scripts.run_pipeline invention default -trace 2

Trace levels:
  0 = no tracing (default)
  1 = high-level layer summaries
  2 = mid-level details (schemas, bars, anchors)
  3 = fine-grained details (notes, figures)

When key is omitted, derives from affect per Mattheson's Affektenlehre.
        """,
    )
    parser.add_argument(
        "args",
        nargs="+",
        help="genre affect [key] [name], or path to .brief file, or directory",
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "-trace",
        type=int,
        default=0,
        choices=[0, 1, 2, 3],
        help="Trace level 0-3 (0=off, 1=summary, 2=detail, 3=fine)",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    reset_tracer()
    set_trace_level(level=args.trace)
    first_arg: str = args.args[0]
    first_arg_clean: str = first_arg.lstrip("/\\")
    first_path: Path = Path(first_arg_clean)
    if not first_path.exists() and (PROJECT_DIR / first_arg_clean).exists():
        first_path = PROJECT_DIR / first_arg_clean
    if first_path.is_dir():
        run_from_directory(directory=first_path, output_dir=args.output_dir, verbose=args.verbose, trace_level=args.trace)
        return
    if first_path.suffix == ".brief" or (first_path.exists() and first_path.is_file()):
        if not first_path.exists():
            print(f"File not found: {first_arg_clean}")
            print(f"  (also checked: {PROJECT_DIR / first_arg_clean})")
            return
        run_from_brief(brief_path=first_path, output_dir=args.output_dir, verbose=args.verbose, trace_level=args.trace)
        print("\nDone!")
        return
    if len(args.args) < 2:
        parser.print_help()
        print("\nError: Need at least genre and affect arguments")
        return
    genre: str = args.args[0]
    affect: str = args.args[1]
    key: str | None = None
    output_name: str | None = None
    if len(args.args) >= 3:
        if "_" in args.args[2]:
            key = args.args[2]
            output_name = args.args[3] if len(args.args) > 3 else None
        else:
            output_name = args.args[2]
    run_from_args(genre=genre, affect=affect, output_dir=args.output_dir, key=key, output_name=output_name, verbose=args.verbose, trace_level=args.trace)
    print("\nDone!")


if __name__ == "__main__":
    main()
