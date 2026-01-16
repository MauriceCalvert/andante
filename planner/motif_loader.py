"""Load motifs from .note files and convert to Motif objects."""
from fractions import Fraction
from pathlib import Path
import csv
import re

from planner.plannertypes import Motif
from shared.constants import NOTE_NAME_MAP

MOTIFS_DIR: Path = Path(__file__).parent.parent / "motifs"
BASE_DIR: Path = Path(__file__).parent.parent

# Note name to pitch class (0-11), handles sharps and flats
NOTE_TO_PC: dict[str, int] = {
    'C': 0, 'C#': 1, 'Db': 1,
    'D': 2, 'D#': 3, 'Eb': 3,
    'E': 4, 'Fb': 4, 'E#': 5,
    'F': 5, 'F#': 6, 'Gb': 6,
    'G': 7, 'G#': 8, 'Ab': 8,
    'A': 9, 'A#': 10, 'Bb': 10,
    'B': 11, 'Cb': 11, 'B#': 0,
}

# G major scale: G=0, A=2, B=4, C=5, D=7, E=9, F#=11
MAJOR_SCALE_SEMITONES: tuple[int, ...] = (0, 2, 4, 5, 7, 9, 11)

# Valid musical duration denominators (powers of 2, with triplet variants)
VALID_DENOMINATORS: frozenset[int] = frozenset({1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64})


def parse_note_name(note_str: str) -> int:
    """Parse note name like 'G4', 'F#5' to MIDI pitch."""
    match = re.match(r'([A-G][#b]?)(\d+)', note_str.strip())
    if not match:
        raise ValueError(f"Invalid note name: {note_str}")
    note, octave = match.groups()
    pc = NOTE_TO_PC[note]
    return pc + (int(octave) + 1) * 12


def midi_to_degree(midi: int, tonic_pc: int = 7, mode: str = "major") -> int:
    """Convert MIDI pitch to scale degree (1-7).

    Default tonic_pc=7 is G. The motif is analyzed relative to its apparent tonic.
    """
    pc = midi % 12
    relative_pc = (pc - tonic_pc) % 12

    # Find closest scale degree
    scale = MAJOR_SCALE_SEMITONES if mode == "major" else (0, 2, 3, 5, 7, 8, 10)
    for i, semitones in enumerate(scale):
        if relative_pc == semitones:
            return i + 1  # 1-indexed

    # Chromatic note - find nearest diatonic
    for i, semitones in enumerate(scale):
        if abs(relative_pc - semitones) <= 1:
            return i + 1
    return 1  # fallback


def infer_tonic(pitches: list[int]) -> int:
    """Infer tonic pitch class from a list of MIDI pitches.

    Heuristic: first and last note are often the tonic.
    """
    if not pitches:
        return 0
    first_pc = pitches[0] % 12
    last_pc = pitches[-1] % 12
    if first_pc == last_pc:
        return first_pc
    return first_pc  # trust the first note


def load_motif(name: str, mode: str = "major") -> Motif:
    """Load motif from .note file in motifs/ directory.

    Args:
        name: Motif name (e.g., "motif_002")
        mode: Target mode for degree conversion

    Returns:
        Motif with degrees relative to inferred tonic
    """
    note_path = MOTIFS_DIR / f"{name}.note"
    if not note_path.exists():
        raise FileNotFoundError(f"Motif not found: {note_path}")

    with open(note_path, encoding="utf-8") as f:
        content = f.read()

    # Parse header comments for pitches and durations
    pitches_line = None
    durations_line = None

    for line in content.splitlines():
        if line.startswith("# Pitches:"):
            pitches_line = line.split(":", 1)[1].strip()
        elif line.startswith("# Durations:"):
            durations_line = line.split(":", 1)[1].strip()

    if not pitches_line or not durations_line:
        raise ValueError(f"Motif file missing Pitches or Durations header: {note_path}")

    # Parse pitches
    pitch_names = pitches_line.split()
    midi_pitches = [parse_note_name(p) for p in pitch_names]

    # Parse durations (as decimals, convert to fractions)
    duration_strs = durations_line.split()
    durations: list[Fraction] = []
    for d in duration_strs:
        # Convert decimal to fraction with musical denominator
        frac = Fraction(d).limit_denominator(64)
        if frac.denominator not in VALID_DENOMINATORS:
            raise ValueError(
                f"Invalid duration {d} -> {frac} in {note_path}: "
                f"denominator {frac.denominator} not in {sorted(VALID_DENOMINATORS)}"
            )
        durations.append(frac)

    # Infer tonic and convert to degrees
    tonic_pc = infer_tonic(midi_pitches)
    degrees = tuple(midi_to_degree(m, tonic_pc, mode) for m in midi_pitches)

    # Calculate bar count from total duration (don't normalize - preserve rhythm)
    total_dur = sum(durations)

    # Validate: total duration must be exact integer bars
    if total_dur.denominator != 1:
        raise ValueError(
            f"Motif durations in {note_path} sum to {total_dur} - "
            f"must be exact integer bars. Fix the source .note file."
        )
    bars = int(total_dur)
    if bars < 1:
        raise ValueError(f"Motif in {note_path} has zero duration")

    return Motif(
        degrees=degrees,
        durations=tuple(durations),
        bars=bars,
    )


def load_motif_from_file(file_path: str, mode: str = "minor") -> Motif:
    """Load motif from CSV-formatted .note file.

    Supports the standard .note CSV format:
        offset,midi,duration,track,length,bar,beat,pitch,lyric

    Args:
        file_path: Path relative to andante/ directory or absolute path
        mode: Target mode for degree conversion (default minor for fugue subjects)

    Returns:
        Motif with degrees relative to inferred tonic
    """
    # Resolve path relative to andante/ if not absolute
    path = Path(file_path)
    if not path.is_absolute():
        path = BASE_DIR / file_path

    if not path.exists():
        raise FileNotFoundError(f"Motif file not found: {path}")

    midi_pitches: list[int] = []
    durations: list[Fraction] = []

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip comments and header
            if line.startswith("#") or line.startswith("offset,"):
                continue
            if not line:
                continue

            parts = line.split(",")
            if len(parts) < 3:
                continue

            try:
                midi = int(parts[1])
                dur = Fraction(parts[2]).limit_denominator(64)
            except (ValueError, IndexError):
                continue

            midi_pitches.append(midi)
            durations.append(dur)

    if not midi_pitches:
        raise ValueError(f"No valid notes found in {path}")

    # Infer tonic and convert to degrees
    tonic_pc = infer_tonic(midi_pitches)
    degrees = tuple(midi_to_degree(m, tonic_pc, mode) for m in midi_pitches)

    # Calculate bar count from total duration
    total_dur = sum(durations)
    if total_dur == 0:
        raise ValueError(f"Motif in {path} has zero duration")

    # Round to nearest integer bars (CSV files may have slight rounding)
    bars = max(1, round(float(total_dur)))

    return Motif(
        degrees=degrees,
        durations=tuple(durations),
        bars=bars,
    )
