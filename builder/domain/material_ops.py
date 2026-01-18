"""Material transformation operations.

Category A: Pure functions, no validation, no I/O.
Assumes all inputs are valid — validation happens in orchestrators.

SIZE: 124 lines — MIDI-to-diatonic conversion requires complete algorithm
including chromatic note handling and octave adjustment. Splitting would
fragment a cohesive transformation pipeline.

Functions:
    apply_pitch_shift      — Shift all pitches by an interval
    fit_to_duration        — Fit notes to target duration by cycling/truncating
    convert_midi_to_diatonic — Convert MIDI pitches to diatonic
    convert_degrees_to_diatonic — Convert scale degrees to diatonic pitches
"""
from fractions import Fraction

from builder.types import Notes
from shared.constants import MAJOR_SCALE, NATURAL_MINOR_SCALE, NOTE_NAME_MAP


def apply_pitch_shift(notes: Notes, shift: int) -> Notes:
    """Shift all pitches by an interval.

    Args:
        notes: Input notes
        shift: Interval to shift (positive or negative)

    Returns:
        Notes with shifted pitches
    """
    shifted: tuple[int, ...] = tuple(p + shift for p in notes.pitches)
    return Notes(shifted, notes.durations)


def fit_to_duration(notes: Notes, target: Fraction) -> Notes:
    """Fit notes to target duration by cycling or truncating.

    Args:
        notes: Input notes
        target: Target duration to fill

    Returns:
        Notes that exactly fill target duration
    """
    result_pitches: list[int] = []
    result_durations: list[Fraction] = []
    remaining: Fraction = target
    idx: int = 0
    max_iterations: int = 1000

    while remaining > 0 and idx < max_iterations:
        p: int = notes.pitches[idx % len(notes.pitches)]
        d: Fraction = notes.durations[idx % len(notes.durations)]
        use_dur: Fraction = min(d, remaining)
        result_pitches.append(p)
        result_durations.append(use_dur)
        remaining -= use_dur
        idx += 1

    return Notes(tuple(result_pitches), tuple(result_durations))


def convert_midi_to_diatonic(
    notes: Notes,
    source_key: str,
    target_key: str,
    target_mode: str,
    min_diatonic: int,
) -> Notes:
    """Convert MIDI pitches to diatonic, transposing from source to target key.

    Args:
        notes: Notes with MIDI pitches
        source_key: Original key (e.g., "G")
        target_key: Target key (e.g., "C")
        target_mode: Target mode ("major" or "minor")
        min_diatonic: Minimum allowed diatonic pitch (e.g., 28 for C4)

    Returns:
        Notes with diatonic pitch values
    """
    source_tonic: int = NOTE_NAME_MAP[source_key]
    target_tonic: int = NOTE_NAME_MAP[target_key]
    transpose: int = target_tonic - source_tonic
    scale: tuple[int, ...] = MAJOR_SCALE if target_mode == "major" else NATURAL_MINOR_SCALE

    pc_to_degree: dict[int, int] = {semitones: deg_idx for deg_idx, semitones in enumerate(scale)}

    diatonic_pitches: list[int] = []
    for midi in notes.pitches:
        transposed: int = midi + transpose
        octave: int = transposed // 12 - 1
        pc: int = (transposed - target_tonic) % 12
        degree: int = pc_to_degree.get(pc, _find_nearest_degree(pc, pc_to_degree))
        diatonic_pitches.append(octave * 7 + degree)

    min_pitch: int = min(diatonic_pitches)
    if min_pitch < min_diatonic:
        octaves_up: int = (min_diatonic - min_pitch + 6) // 7
        diatonic_pitches = [p + octaves_up * 7 for p in diatonic_pitches]

    return Notes(tuple(diatonic_pitches), notes.durations)


def convert_degrees_to_diatonic(notes: Notes, base_octave: int) -> Notes:
    """Convert scale degrees (1-7) to diatonic pitch values.

    Args:
        notes: Notes with scale degrees as pitches
        base_octave: Base octave for conversion

    Returns:
        Notes with diatonic pitch values
    """
    diatonic: tuple[int, ...] = tuple(
        base_octave * 7 + ((d - 1) % 7) for d in notes.pitches
    )
    return Notes(diatonic, notes.durations)


def _find_nearest_degree(pc: int, pc_to_degree: dict[int, int]) -> int:
    """Find nearest scale degree for a chromatic pitch class."""
    for offset in [1, -1, 2, -2]:
        test_pc: int = (pc + offset) % 12
        if test_pc in pc_to_degree:
            return pc_to_degree[test_pc]
    return 0
