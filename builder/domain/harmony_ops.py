"""Harmony operations for melody-aware chord selection.
Category A: Pure functions, no validation, no I/O.
Assumes all inputs are valid — validation happens in orchestrators.
Functions:
    generate_melody_compatible_harmony — Select chords compatible with melody
    is_consonant_diatonic              — Check if two degrees are consonant
    has_consonant_tone                 — Check if any chord tone works with melody
"""
from fractions import Fraction
from builder.types import Notes
from shared.constants import TONAL_ROOTS
from shared.errors import HarmonyGenerationError

# Chord preference order: primary chords first, then secondary
CHORD_PREFERENCE: tuple[str, ...] = ("I", "V", "IV", "vi", "ii", "iii", "vii")


def generate_melody_compatible_harmony(
    melody: Notes,
    bar_duration: Fraction,
) -> tuple[str, ...]:
    """Generate harmony that is consonant with the melody.

    For each bar:
    1. Collect all melody pitches (as 0-6 scale degree indices)
    2. For each candidate chord in preference order:
       - Check if ANY chord tone is consonant with ALL melody pitches
    3. Select best chord from compatible options

    Args:
        melody: Notes with diatonic pitches (from convert_degrees_to_diatonic)
        bar_duration: Duration of one bar

    Returns:
        Tuple of Roman numerals, one per bar

    Raises:
        HarmonyGenerationError: If no compatible chord found for any bar
    """
    bar_count: int = _compute_bar_count(melody, bar_duration)
    harmony: list[str] = []

    for bar_idx in range(bar_count):
        melody_indices: list[int] = _get_degrees_in_bar(melody, bar_idx, bar_duration)

        # Try chords in preference order
        chord_found: bool = False
        for chord in CHORD_PREFERENCE:
            chord_tones: tuple[int, ...] = _get_chord_tone_indices(chord)
            if has_consonant_tone(chord_tones, melody_indices):
                harmony.append(chord)
                chord_found = True
                break

        assert chord_found, (
            f"No chord compatible with melody in bar {bar_idx + 1}. "
            f"Melody degree indices: {melody_indices}. "
            f"Tried chords: {CHORD_PREFERENCE}"
        )

    return tuple(harmony)


def _compute_bar_count(melody: Notes, bar_duration: Fraction) -> int:
    """Compute number of bars from melody duration."""
    total_duration: Fraction = sum(melody.durations, Fraction(0))
    return max(1, int((total_duration + bar_duration - Fraction(1, 32)) // bar_duration))


def _get_degrees_in_bar(
    melody: Notes,
    bar_idx: int,
    bar_duration: Fraction,
) -> list[int]:
    """Get melody pitches on STRONG BEATS in a bar as 0-6 scale degree indices.

    Only checks downbeat and mid-bar beat (positions 0 and 0.5 within bar).
    This allows passing tones on weak beats without affecting harmony selection.

    Args:
        melody: Notes with diatonic pitches
        bar_idx: 0-based bar index
        bar_duration: Duration of one bar

    Returns:
        List of 0-6 scale degree indices for notes on strong beats
    """
    offset: Fraction = bar_duration * bar_idx
    window_end: Fraction = offset + bar_duration
    # Strong beat positions within the bar (0 = downbeat, 0.5 = mid-bar)
    strong_beats: tuple[Fraction, ...] = (
        offset,
        offset + bar_duration / 2,
    )
    tolerance: Fraction = Fraction(1, 16)  # Allow slight timing variance

    indices: list[int] = []
    current: Fraction = Fraction(0)

    for pitch, dur in zip(melody.pitches, melody.durations):
        note_start: Fraction = current
        current += dur

        # Skip notes that start before this bar
        if note_start < offset:
            continue
        # Stop if past this bar
        if note_start >= window_end:
            break

        # Only include notes on or near strong beats
        is_strong_beat: bool = any(
            abs(note_start - beat) <= tolerance for beat in strong_beats
        )
        if is_strong_beat:
            degree_index: int = pitch % 7
            indices.append(degree_index)

    return indices


def _get_chord_tone_indices(chord: str) -> tuple[int, ...]:
    """Get chord tones as 0-6 scale degree indices.

    Args:
        chord: Roman numeral (e.g., "I", "V", "vi")

    Returns:
        Tuple of 0-6 indices for root, third, fifth
    """
    root: int = TONAL_ROOTS.get(chord, 1)  # 1-based
    # Convert to 0-based and compute third/fifth
    root_idx: int = (root - 1) % 7
    third_idx: int = (root_idx + 2) % 7
    fifth_idx: int = (root_idx + 4) % 7
    return (root_idx, third_idx, fifth_idx)


def is_consonant_diatonic(deg1_idx: int, deg2_idx: int) -> bool:
    """Check if two diatonic indices (0-6) are consonant.

    Dissonant intervals: 2nd and 7th (which invert to each other).
    All other intervals (unison, 3rd, 4th, 5th, 6th) are consonant.

    Args:
        deg1_idx: First scale degree index (0-6)
        deg2_idx: Second scale degree index (0-6)

    Returns:
        True if interval is consonant
    """
    interval: int = abs(deg1_idx - deg2_idx)
    # Handle inversion (7th becomes 2nd, etc.)
    interval = min(interval, 7 - interval)
    # Only 2nd/7th (interval=1) is dissonant
    return interval != 1


def has_consonant_tone(
    chord_tone_indices: tuple[int, ...],
    melody_indices: list[int],
) -> bool:
    """Check if any chord tone is consonant with ALL melody notes.

    For a chord to work with the melody, at least one of its tones
    must not create a dissonant interval with any melody note.

    Args:
        chord_tone_indices: 0-6 indices for chord tones (root, 3rd, 5th)
        melody_indices: 0-6 indices for all melody notes in the bar

    Returns:
        True if any chord tone is consonant with all melody notes
    """
    # Empty melody is compatible with any chord
    if not melody_indices:
        return True

    for tone_idx in chord_tone_indices:
        # Check if this tone is consonant with ALL melody notes
        all_consonant: bool = all(
            is_consonant_diatonic(tone_idx, melody_idx)
            for melody_idx in melody_indices
        )
        if all_consonant:
            return True

    return False
