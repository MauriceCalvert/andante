"""Main executor: orchestrates E1-E6 pipeline."""
from fractions import Fraction
from pathlib import Path

from engine.annotate import extract_annotations
from engine.expander import bar_duration, expand_piece
from engine.formatter import format_notes, tempo_from_name
from engine.note import Note
from engine.key import Key
from engine.output import create_writer
from engine.plan_parser import parse_yaml
from engine.realiser import realise_phrases
from engine.treatment_caps import validate_or_raise
from shared.tracer import get_tracer
from engine.engine_types import Annotation, PieceAST, RealisedPhrase

get_tracer().enable()
validate_or_raise()  # Fail fast on typos in treatments.yaml interdictions

# Default annotation granularity: "none", "section", "episode", "phrase"
ANNOTATION_GRANULARITY: str = "phrase"


def execute(yaml_str: str) -> tuple[list[Note], PieceAST]:
    """Execute YAML plan to produce notes."""
    piece: PieceAST = parse_yaml(yaml_str)
    expanded = expand_piece(piece)
    bar_dur: Fraction = bar_duration(piece.metre)
    key: Key = Key(tonic=piece.key, mode=piece.mode)
    realised: list[RealisedPhrase] = realise_phrases(expanded, key, bar_dur, piece.metre)
    notes: list[Note] = format_notes(realised, piece.metre)
    return (notes, piece)


def execute_and_export(
    yaml_str: str,
    output_path: str,
    annotation_granularity: str | None = None,
    humanise_output: bool = False,
    instrument: str = "harpsichord",
    style: str = "baroque",
) -> list[Note]:
    """Execute plan and export to .mid, .note, .musicxml, and .trace files.

    Args:
        yaml_str: YAML plan string
        output_path: Output file path (without extension)
        annotation_granularity: Level of text annotations
        humanise_output: If True, apply humanisation for expressive timing/dynamics
        instrument: Instrument profile for humanisation (harpsichord, piano, clavichord)
        style: Style profile for humanisation (baroque)

    Returns:
        List of Note objects (humanised if humanise_output=True)
    """
    tracer = get_tracer()
    midi_notes, piece = execute(yaml_str)
    tempo: int = tempo_from_name(piece.tempo)
    num_str, den_str = piece.metre.split("/")
    timenum: int = int(num_str)
    timeden: int = int(den_str)
    upbeat: Fraction = piece.upbeat
    granularity: str = annotation_granularity or ANNOTATION_GRANULARITY
    annotations: tuple[Annotation, ...] = extract_annotations(piece, granularity)

    # Optional humanisation
    if humanise_output:
        from humanisation.engine import humanise
        from humanisation.profile_loader import load_profile

        profile = load_profile(instrument, style)
        midi_notes = humanise(midi_notes, profile, piece.metre, tempo)

    writer = create_writer()
    writer.write(
        path=output_path,
        notes=midi_notes,
        timenum=timenum,
        timeden=timeden,
        tonic=piece.key,
        mode=piece.mode,
        bpm=tempo,
        upbeat=upbeat,
        annotations=annotations,
    )
    tracer.write_log(f"{output_path}.trace")
    return midi_notes
