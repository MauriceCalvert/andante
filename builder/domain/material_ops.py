"""Material transformation operations.

Category A: Pure functions, no validation, no I/O.
Assumes all inputs are valid — validation happens in orchestrators.

SIZE: 180 lines — MIDI-to-diatonic conversion requires complete algorithm
including chromatic note handling and octave adjustment. Harmonize melody
adds chord-tone awareness. Splitting would fragment a cohesive pipeline.

Functions:
    apply_pitch_shift      — Shift all pitches by an interval
    fit_to_duration        — Fit notes to target duration by cycling/truncating
    convert_midi_to_diatonic — Convert MIDI pitches to diatonic
    convert_degrees_to_diatonic — Convert scale degrees to diatonic pitches
    harmonize_melody       — Nudge strong-beat pitches toward chord tones
"""
from fractions import Fraction

from builder.types import Notes, ParsedTreatment
from shared.constants import MAJOR_SCALE, NATURAL_MINOR_SCALE, NOTE_NAME_MAP, TONAL_ROOTS


def parse_treatment(treatment_str: str) -> ParsedTreatment:
    """Parse treatment string like 'inversion[circulatio+groppo]'.

    Returns ParsedTreatment with base transform and ornaments.
    """
    if "[" not in treatment_str:
        return ParsedTreatment(base=treatment_str, ornaments=())
    bracket_start: int = treatment_str.index("[")
    bracket_end: int = treatment_str.index("]")
    base: str = treatment_str[:bracket_start]
    ornament_str: str = treatment_str[bracket_start + 1 : bracket_end]
    ornaments: tuple[str, ...] = tuple(ornament_str.split("+"))
    return ParsedTreatment(base=base, ornaments=ornaments)


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


def fit_to_duration(notes: Notes, target: Fraction, offset: Fraction = Fraction(0)) -> Notes:
    """Extract notes for a target duration, starting from offset.

    Args:
        notes: Input notes
        target: Target duration to fill
        offset: Time offset to start from (skips notes before this point)

    Returns:
        Notes that exactly fill target duration
    """
    result_pitches: list[int] = []
    result_durations: list[Fraction] = []
    remaining: Fraction = target
    current_time: Fraction = Fraction(0)
    idx: int = 0
    max_iterations: int = 1000

    # Skip notes before offset
    while idx < len(notes.pitches) and current_time + notes.durations[idx] <= offset:
        current_time += notes.durations[idx]
        idx += 1

    # Handle partial note at offset boundary
    if idx < len(notes.pitches) and current_time < offset:
        partial: Fraction = offset - current_time
        available: Fraction = notes.durations[idx] - partial
        use_dur: Fraction = min(available, remaining)
        result_pitches.append(notes.pitches[idx])
        result_durations.append(use_dur)
        remaining -= use_dur
        idx += 1

    # Fill remaining duration
    iterations: int = 0
    while remaining > 0 and iterations < max_iterations:
        p: int = notes.pitches[idx % len(notes.pitches)]
        d: Fraction = notes.durations[idx % len(notes.durations)]
        use_dur = min(d, remaining)
        result_pitches.append(p)
        result_durations.append(use_dur)
        remaining -= use_dur
        idx += 1
        iterations += 1

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
    """Convert scale degrees to diatonic pitch values.

    Degrees 1-7 are in the base octave. Degrees 8-14 are one octave higher,
    degrees -6 to 0 are one octave lower, etc. This preserves octave information.

    Args:
        notes: Notes with scale degrees as pitches (1=tonic, 8=octave above tonic)
        base_octave: Base octave for conversion

    Returns:
        Notes with diatonic pitch values
    """
    diatonic: tuple[int, ...] = tuple(
        (base_octave + (d - 1) // 7) * 7 + ((d - 1) % 7) for d in notes.pitches
    )
    return Notes(diatonic, notes.durations)


def _find_nearest_degree(pc: int, pc_to_degree: dict[int, int]) -> int:
    """Find nearest scale degree for a chromatic pitch class."""
    for offset in [1, -1, 2, -2]:
        test_pc: int = (pc + offset) % 12
        if test_pc in pc_to_degree:
            return pc_to_degree[test_pc]
    return 0


def harmonize_melody(
    notes: Notes,
    chord: str,
    key: str,
    mode: str,
) -> Notes:
    """Nudge strong-beat pitches toward chord tones.

    On strong beats (accumulating to 0, 1/2 of a bar in 4/4), prefer chord tones.
    Non-chord tones are OK on weak beats. Preserves melodic contour by choosing
    the nearest chord tone.

    Args:
        notes: Notes with scale degrees (1-7) as pitches
        chord: Roman numeral (e.g., "V", "I", "iv")
        key: Key (e.g., "C", "G")
        mode: Mode ("major" or "minor")

    Returns:
        Notes with adjusted pitches for harmony
    """
    chord_tones: tuple[int, ...] = _get_chord_tones(chord)
    strong_beat_positions: frozenset[Fraction] = frozenset({
        Fraction(0), Fraction(1, 2), Fraction(1), Fraction(3, 2)
    })
    result_pitches: list[int] = []
    cumulative: Fraction = Fraction(0)
    for i, pitch in enumerate(notes.pitches):
        dur: Fraction = notes.durations[i]
        is_strong: bool = any(
            abs(cumulative - pos) < Fraction(1, 16) for pos in strong_beat_positions
        )
        degree: int = ((pitch - 1) % 7) + 1
        if is_strong and degree not in chord_tones:
            adjusted: int = _nearest_chord_tone(pitch, chord_tones)
            result_pitches.append(adjusted)
        else:
            result_pitches.append(pitch)
        cumulative += dur
    return Notes(tuple(result_pitches), notes.durations)


def _get_chord_tones(chord: str) -> tuple[int, ...]:
    """Get chord tones as scale degrees for a Roman numeral chord.

    Args:
        chord: Roman numeral (e.g., "I", "V", "vi")

    Returns:
        Tuple of scale degrees (1-7) that are chord tones
    """
    root: int = TONAL_ROOTS.get(chord, 1)
    third: int = ((root - 1 + 2) % 7) + 1
    fifth: int = ((root - 1 + 4) % 7) + 1
    return (root, third, fifth)


def _nearest_chord_tone(pitch: int, chord_tones: tuple[int, ...]) -> int:
    """Find nearest chord tone to a pitch while preserving octave."""
    degree: int = ((pitch - 1) % 7) + 1
    octave_offset: int = pitch - degree
    best_dist: int = 999
    best_tone: int = pitch
    for tone in chord_tones:
        for delta in [0, 7, -7]:
            candidate: int = tone + delta
            dist: int = abs(candidate - degree)
            if dist < best_dist:
                best_dist = dist
                best_tone = octave_offset + candidate
    return best_tone
