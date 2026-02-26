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
    python -m scripts.run_pipeline motifs/output/subject00_2bar.subject

Options:
    -o, --output-dir DIR    Output directory (default: output/)
    -v, --verbose           Verbose output
    -trace                  Write <piece>.trace diagnostic file
    -seed N                 RNG seed for reproducibility (default: varies per run)
"""
import argparse
import time
from dataclasses import dataclass
from pathlib import Path

import yaml

from builder.faults import find_faults_from_composition, print_faults
from motifs.subject_loader import SubjectTriple, load_triple, load_triple_path
from builder.types import Composition
from planner.planner import GeneratorOptions, generate_to_files
from shared.tracer import get_tracer, reset_tracer, set_trace_enabled


SCRIPT_DIR: Path = Path(__file__).resolve().parent
PROJECT_DIR: Path = SCRIPT_DIR.parent
DEFAULT_OUTPUT_DIR: Path = PROJECT_DIR / "output"

@dataclass(frozen=True)
class PipelineOptions:
    """Optional pipeline control params bundled for transit (M001/M002)."""
    verbose: bool = False
    trace: bool = False
    seed: int | None = None


AFFECT_ALIASES: dict[str, str] = {
    "joy": "Freudigkeit",
    "bright": "Freudigkeit",
    "confident": "Entschlossenheit",
}

# Bare note names → canonical key strings
_NOTE_LETTERS: frozenset[str] = frozenset("abcdefg")

KEY_ALIASES: dict[str, str] = {
    "cmajor": "c_major",
}


def _is_bare_key(candidate: str) -> bool:
    """True if candidate looks like a bare key name (C, Bb, F#, Am, etc.)."""
    s: str = candidate.lower().strip()
    if not s or s[0] not in _NOTE_LETTERS:
        return False
    # After the letter: optional accidental (b, #, bb) then optional mode hint (m)
    rest: str = s[1:]
    if rest in ("", "b", "bb", "#", "m", "bm", "bbm", "#m"):
        return True
    return False


def normalize_key(key: str) -> str:
    """Normalize key name to config file name."""
    normalized: str = key.lower().replace(" ", "_")
    if normalized in KEY_ALIASES:
        return KEY_ALIASES[normalized]
    # Bare note name -> tonic_major or tonic_minor
    if _is_bare_key(candidate=key):
        s: str = normalized
        if s.endswith("m"):
            tonic: str = s[:-1]
            mode: str = "minor"
        else:
            tonic = s
            mode = "major"
        # Normalise accidentals: # -> s (sharp), b stays
        tonic = tonic.replace("#", "s")
        return f"{tonic}_{mode}"
    return normalized


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
    tempo: int | None = None,
    fugue: SubjectTriple | None = None,
    sections_override: tuple[dict, ...] | None = None,
    options: PipelineOptions | None = None,
) -> Composition:
    """Generate from explicit genre/affect arguments."""
    verbose: bool = options.verbose if options else False
    trace: bool = options.trace if options else False
    seed: int | None = options.seed if options else None
    affect = normalize_affect(affect=affect)
    if key is not None:
        key = normalize_key(key=key)
    if seed is None:
        seed = hash((genre, affect, key or "", int(time.time()))) % (2**31)
    if output_name:
        name = output_name
    elif affect == "default":
        name = genre
    elif key:
        name = f"{genre}_{affect}_{key}"
    else:
        name = f"{genre}_{affect}"
    if verbose:
        print(f"  Genre: {genre}")
        print(f"  Key: {key if key else '(from affect)'}")
        print(f"  Affect: {affect}")
    key_display: str = key if key else "(derived from affect)"
    print(f"Generating {genre} with {affect} affect in {key_display}...")
    print(f"  Seed: {seed}")
    reset_tracer()
    set_trace_enabled(enabled=trace)
    result = generate_to_files(
        genre=genre,
        affect=affect,
        output_dir=output_dir,
        name=name,
        options=GeneratorOptions(key=key, tempo=tempo, fugue=fugue, sections_override=sections_override, seed=seed),
    )
    for vid, vnotes in result.voices.items():
        print(f"  {vid}: {len(vnotes)} notes")
    print(f"  Tempo: {result.tempo} BPM")
    print(f"Output: {output_dir / name}.note, {output_dir / name}.midi")
    faults = find_faults_from_composition(composition=result)
    print_faults(faults=faults)
    if trace:
        get_tracer().trace_faults(faults=faults)
        trace_path = get_tracer().write(output_dir=output_dir)
        if trace_path:
            print(f"Trace: {trace_path}")
    print()
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
    options: PipelineOptions | None = None,
) -> Composition:
    """Generate from a .brief file."""
    verbose: bool = options.verbose if options else False
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
    subject_name: str | None = brief_data.get("subject") or frame_data.get("subject")
    fugue: SubjectTriple | None = None
    if subject_name:
        fugue = load_triple(name=subject_name)
        if verbose:
            print(f"  Loaded fugue: {subject_name}")
    sections_override: tuple[dict, ...] | None = None
    if "sections" in data:
        sections_override = _convert_brief_sections(brief_sections=data["sections"])
        if verbose:
            print(f"  Sections override: {len(sections_override)} sections")
    output_name: str = brief_path.stem
    return run_from_args(genre=genre, affect=affect, output_dir=output_dir, key=key, output_name=output_name, tempo=tempo, fugue=fugue, sections_override=sections_override, options=options)


def run_from_subject(
    fugue_path: Path,
    output_dir: Path,
    options: PipelineOptions | None = None,
) -> Composition:
    """Generate an invention from a .subject file."""
    verbose: bool = options.verbose if options else False
    print(f"Loading {fugue_path.name}...")
    fugue: SubjectTriple = load_triple_path(path=fugue_path)
    tonic_letter: str = fugue.tonic.upper()
    mode: str = fugue.subject.mode
    key: str = normalize_key(key=f"{tonic_letter}{'m' if mode == 'minor' else ''}")
    output_name: str = fugue_path.stem
    if verbose:
        print(f"  Tonic: {tonic_letter} ({fugue.tonic_midi})")
        print(f"  Mode: {mode}")
        print(f"  Key: {key}")
        print(f"  Subject: {len(fugue.subject.degrees)} notes, {fugue.subject.bars} bars")
        print(f"  Stretto offsets: {len(fugue.stretto)}")
    return run_from_args(
        genre="invention",
        affect="default",
        output_dir=output_dir,
        key=key,
        output_name=output_name,
        fugue=fugue,
        options=options,
    )


def run_from_directory(
    directory: Path,
    output_dir: Path,
    options: PipelineOptions | None = None,
) -> int:
    """Generate from all .brief files in a directory."""
    briefs: list[Path] = sorted(directory.glob("*.brief"))
    if not briefs:
        print(f"No .brief files found in {directory}")
        return 0
    print(f"Found {len(briefs)} brief files in {directory}\n")
    total_notes: int = 0
    for brief_path in briefs:
        result = run_from_brief(brief_path=brief_path, output_dir=output_dir, options=options)
        total_notes += sum(len(v) for v in result.voices.values())
        print()
    print(f"Generated {len(briefs)} pieces ({total_notes} total notes)")
    return len(briefs)


def main() -> None:
    """Run the pipeline."""
    from scripts.yaml_validator import validate_all
    result = validate_all()
    if not result.valid:
        print(f"YAML validation failed ({len(result.errors)} errors):")
        for e in result.errors:
            print(f"  {e}")
        import sys
        sys.exit(1)
    # for p in result.orphaned:
    #     print(f"  INFO: orphaned YAML file: {p}")

    parser = argparse.ArgumentParser(
        description="Generate music from genre/affect or brief files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m scripts.run_pipeline invention default
  python -m scripts.run_pipeline invention default c_major
  python -m scripts.run_pipeline briefs/builder/freude_invention.brief
  python -m scripts.run_pipeline briefs/tests/ -o output/tests
  python -m scripts.run_pipeline invention default -trace

When key is omitted, derives from affect per Mattheson's Affektenlehre.
Use -trace to write a <piece>.trace diagnostic file.
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
        action="store_true",
        default=False,
        help="Write <piece>.trace diagnostic file to output dir",
    )
    parser.add_argument(
        "-seed",
        type=int,
        default=None,
        help="RNG seed for reproducibility (default: varies per run)",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    pipeline_options: PipelineOptions = PipelineOptions(
        verbose=args.verbose,
        trace=args.trace,
        seed=args.seed,
    )
    first_arg: str = args.args[0]
    first_arg_clean: str = first_arg.lstrip("/\\")
    first_path: Path = Path(first_arg_clean)
    if not first_path.exists() and (PROJECT_DIR / first_arg_clean).exists():
        first_path = PROJECT_DIR / first_arg_clean
    if first_path.is_dir():
        run_from_directory(directory=first_path, output_dir=args.output_dir, options=pipeline_options)
        return
    if first_path.suffix == ".subject":
        if not first_path.exists():
            print(f"File not found: {first_arg_clean}")
            print(f"  (also checked: {PROJECT_DIR / first_arg_clean})")
            return
        run_from_subject(fugue_path=first_path, output_dir=args.output_dir, options=pipeline_options)
        print("\nDone!")
        return
    if first_path.suffix == ".brief" or (first_path.exists() and first_path.is_file()):
        if not first_path.exists():
            print(f"File not found: {first_arg_clean}")
            print(f"  (also checked: {PROJECT_DIR / first_arg_clean})")
            return
        run_from_brief(brief_path=first_path, output_dir=args.output_dir, options=pipeline_options)
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
        candidate: str = args.args[2]
        if "_" in candidate or _is_bare_key(candidate=candidate):
            key = candidate
            output_name = args.args[3] if len(args.args) > 3 else None
        else:
            output_name = args.args[2]
    run_from_args(genre=genre, affect=affect, output_dir=args.output_dir, key=key, output_name=output_name, options=pipeline_options)
    print("\nDone!")


if __name__ == "__main__":
    main()
