"""CLI for Bob diagnostic module.

Usage:
    python -m engine.bob path/to/piece.yaml
    python -m engine.bob path/to/piece.note

Output goes to stdout for clipboard copy.
"""
import sys
from fractions import Fraction
from pathlib import Path

from engine.bob.checker import diagnose
from engine.bob.formatter import Report
from engine.engine_types import RealisedNote, RealisedPhrase, RealisedVoice
from engine.expander import bar_duration, expand_piece
from engine.key import Key
from engine.plan_parser import parse_yaml
from engine.realiser import realise_phrases


def _load_note_file(path: Path) -> tuple[list[RealisedPhrase], Fraction, Key]:
    """Load .note file and reconstruct basic RealisedPhrases.

    Note files don't preserve phrase boundaries, so we create a single
    pseudo-phrase containing all notes grouped by voice.
    """
    lines = path.read_text().strip().split("\n")
    if not lines or lines[0].startswith("Offset"):
        lines = lines[1:]  # Skip header

    # Group notes by track (voice)
    voices_notes: dict[int, list[RealisedNote]] = {}
    for line in lines:
        parts = line.split(",")
        if len(parts) < 5:
            continue
        offset = Fraction(parts[0]).limit_denominator(64)
        midi_note = int(parts[1])
        duration = Fraction(parts[2]).limit_denominator(64)
        track = int(parts[3])

        if track not in voices_notes:
            voices_notes[track] = []

        voice_name = ["soprano", "alto", "tenor", "bass"][track] if track < 4 else f"v{track}"
        voices_notes[track].append(RealisedNote(
            offset=offset,
            pitch=midi_note,
            duration=duration,
            voice=voice_name,
        ))

    # Create RealisedVoices
    voice_count = max(voices_notes.keys()) + 1 if voices_notes else 2
    realised_voices = []
    for i in range(voice_count):
        notes = sorted(voices_notes.get(i, []), key=lambda n: n.offset)
        realised_voices.append(RealisedVoice(voice_index=i, notes=notes))

    # Single pseudo-phrase
    phrase = RealisedPhrase(index=0, voices=realised_voices)

    # Default to 4/4 and C major (metadata not preserved in .note)
    return [phrase], Fraction(4), Key(tonic="c", mode="major")


def _load_yaml_file(path: Path) -> tuple[list[RealisedPhrase], Fraction, Key]:
    """Load .yaml file and realise to get RealisedPhrases."""
    yaml_str = path.read_text()
    piece = parse_yaml(yaml_str)
    expanded = expand_piece(piece)
    bar_dur = bar_duration(piece.metre)
    key = Key(tonic=piece.key, mode=piece.mode)
    # Use strict=False to allow diagnosis even when blockers are found
    realised = realise_phrases(expanded, key, bar_dur, piece.metre, strict=False)
    return realised, bar_dur, key


def main() -> None:
    """Run Bob diagnostic on a piece file."""
    if len(sys.argv) < 2:
        print("Usage: python -m engine.bob <path/to/piece.yaml|.note>", file=sys.stderr)
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    suffix = path.suffix.lower()
    if suffix == ".yaml" or suffix == ".yml":
        phrases, bar_dur, key = _load_yaml_file(path)
    elif suffix == ".note":
        phrases, bar_dur, key = _load_note_file(path)
    else:
        print(f"Unsupported file type: {suffix}", file=sys.stderr)
        print("Supported: .yaml, .yml, .note", file=sys.stderr)
        sys.exit(1)

    report: Report = diagnose(phrases, bar_duration=bar_dur, key=key)
    print(report.to_clipboard())


if __name__ == "__main__":
    main()
