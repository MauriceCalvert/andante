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

from planner.planner import generate_to_files
from builder.types import NoteFile


SCRIPT_DIR: Path = Path(__file__).resolve().parent
PROJECT_DIR: Path = SCRIPT_DIR.parent
DEFAULT_OUTPUT_DIR: Path = PROJECT_DIR / "output"

# Normalize affect names to config file names
AFFECT_ALIASES: dict[str, str] = {
    "joy": "Freudigkeit",
    "bright": "Freudigkeit",
    "confident": "Entschlossenheit",
}

# Normalize key names to config file names
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
) -> NoteFile:
    """Generate from explicit genre/affect arguments.

    When key is None, derives appropriate key from affect using
    Mattheson's Affektenlehre.
    """
    # Normalize inputs
    affect = normalize_affect(affect)
    if key is not None:
        key = normalize_key(key)
    name: str = output_name or f"{genre}_{affect}"

    if verbose:
        print(f"  Genre: {genre}")
        print(f"  Key: {key if key else '(from affect)'}")
        print(f"  Affect: {affect}")

    key_display: str = key if key else "(derived from affect)"
    print(f"Generating {genre} with {affect} affect in {key_display}...")
    result = generate_to_files(genre, affect, output_dir, name, key)

    print(f"  Soprano: {len(result.soprano)} notes")
    print(f"  Bass: {len(result.bass)} notes")
    print(f"  Tempo: {result.tempo} BPM")
    print(f"Output: {output_dir / name}.note, {output_dir / name}.midi")

    return result


def run_from_brief(
    brief_path: Path,
    output_dir: Path,
    verbose: bool = False,
) -> NoteFile:
    """Generate from a .brief file.

    If key is not specified in the brief, derives from affect per Mattheson.
    """
    print(f"Loading {brief_path.name}...")

    with open(brief_path, encoding="utf-8") as f:
        data: dict = yaml.safe_load(f)

    brief_data: dict = data.get("brief", data)
    frame_data: dict = data.get("frame", {})
    genre: str = brief_data.get("genre", "invention")
    # Key can be in brief.key or frame.key+frame.mode
    key: str | None = brief_data.get("key")
    if key is None and "key" in frame_data:
        tonic: str = frame_data["key"].lower()
        mode: str = frame_data.get("mode", "major").lower()
        key = f"{tonic}_{mode}"
    affect: str = brief_data.get("affect", "default")

    output_name: str = brief_path.stem

    return run_from_args(genre, affect, output_dir, key, output_name, verbose)


def run_from_directory(
    directory: Path,
    output_dir: Path,
    verbose: bool = False,
) -> int:
    """Generate from all .brief files in a directory."""
    briefs: list[Path] = sorted(directory.glob("*.brief"))

    if not briefs:
        print(f"No .brief files found in {directory}")
        return 0

    print(f"Found {len(briefs)} brief files in {directory}\n")

    total_notes: int = 0
    for brief_path in briefs:
        result = run_from_brief(brief_path, output_dir, verbose)
        total_notes += len(result.soprano) + len(result.bass)
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

    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    first_arg: str = args.args[0]
    # Strip leading slashes to treat as relative path
    first_arg_clean: str = first_arg.lstrip("/\\")
    first_path: Path = Path(first_arg_clean)

    # Try to resolve path relative to project dir if not found
    if not first_path.exists() and (PROJECT_DIR / first_arg_clean).exists():
        first_path = PROJECT_DIR / first_arg_clean

    # Case 1: Directory of briefs
    if first_path.is_dir():
        run_from_directory(first_path, args.output_dir, args.verbose)
        return

    # Case 2: Single .brief file
    if first_path.suffix == ".brief" or (first_path.exists() and first_path.is_file()):
        if not first_path.exists():
            print(f"File not found: {first_arg_clean}")
            print(f"  (also checked: {PROJECT_DIR / first_arg_clean})")
            return
        run_from_brief(first_path, args.output_dir, args.verbose)
        print("\nDone!")
        return

    # Case 3: Direct genre/affect [key] arguments
    if len(args.args) < 2:
        parser.print_help()
        print("\nError: Need at least genre and affect arguments")
        return

    genre: str = args.args[0]
    affect: str = args.args[1]
    # Key is optional - if present, contains '_' (e.g., "c_major")
    key: str | None = None
    output_name: str | None = None

    if len(args.args) >= 3:
        # Check if third arg looks like a key (contains '_')
        if "_" in args.args[2]:
            key = args.args[2]
            output_name = args.args[3] if len(args.args) > 3 else None
        else:
            # Third arg is output name, no key specified
            output_name = args.args[2]

    run_from_args(genre, affect, args.output_dir, key, output_name, args.verbose)
    print("\nDone!")


if __name__ == "__main__":
    main()
