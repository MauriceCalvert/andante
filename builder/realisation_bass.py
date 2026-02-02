"""Bass voice realisation."""
from fractions import Fraction

from builder.types import Note
from shared.constants import CONSONANT_INTERVALS, STRONG_BEAT_DISSONANT


CROSS_RELATION_PAIRS: frozenset[tuple[int, int]] = frozenset({
    (0, 1),   # C / C#
    (2, 3),   # D / D#
    (5, 6),   # F / F#
    (7, 8),   # G / G#
    (9, 10),  # A / A#
})


def is_dissonant_interval(soprano_midi: int, bass_midi: int) -> bool:
    """Check if vertical interval between soprano and bass is dissonant."""
    interval = abs(soprano_midi - bass_midi) % 12
    return interval in STRONG_BEAT_DISSONANT


def find_consonant_bass(
    soprano_midi: int,
    bass_midi: int,
    bass_range: tuple[int, int],
) -> int:
    """Find nearest consonant bass pitch by adjusting up or down.

    Tries moving bass by 1-2 semitones to find a consonant interval.
    Returns original if no consonant alternative found within range.
    """
    interval = abs(soprano_midi - bass_midi) % 12
    if interval not in STRONG_BEAT_DISSONANT:
        return bass_midi  # Already consonant
    low, high = bass_range
    # Try small adjustments: +/-1, +/-2 semitones
    for delta in [1, -1, 2, -2]:
        candidate = bass_midi + delta
        if candidate < low or candidate > high:
            continue
        new_interval = abs(soprano_midi - candidate) % 12
        if new_interval in CONSONANT_INTERVALS:
            return candidate
    return bass_midi  # No better option found


def pitch_sounding_at(notes: list[Note], offset: Fraction) -> int | None:
    """Get the pitch sounding at a given offset.

    Returns the pitch of the note that starts at or before the offset
    and extends past it, or None if no note is sounding.
    """
    for note in notes:
        if note.offset <= offset < note.offset + note.duration:
            return note.pitch
    return None


def adjust_downbeat_consonance(
    soprano_notes: list[Note],
    bass_notes: list[Note],
    beats_per_bar: int,
    total_bars: int,
    bass_range: tuple[int, int],
) -> list[Note]:
    """Adjust bass notes at downbeats to ensure consonance with soprano.

    For each bar downbeat, if soprano and bass form a dissonant interval,
    adjust the bass note to the nearest consonant pitch.
    """
    # Build map of downbeat offsets to bar numbers
    downbeats: list[tuple[Fraction, int]] = []
    for bar in range(1, total_bars + 1):
        offset = Fraction((bar - 1) * beats_per_bar, 4)
        downbeats.append((offset, bar))
    # Create mutable copies
    adjusted: list[Note] = list(bass_notes)
    for offset, bar in downbeats:
        s_pitch = pitch_sounding_at(soprano_notes, offset)
        if s_pitch is None:
            continue
        # Find bass note at this downbeat
        for i, note in enumerate(adjusted):
            if note.offset == offset:
                if is_dissonant_interval(s_pitch, note.pitch):
                    new_pitch = find_consonant_bass(s_pitch, note.pitch, bass_range)
                    if new_pitch != note.pitch:
                        adjusted[i] = Note(
                            offset=note.offset,
                            pitch=new_pitch,
                            duration=note.duration,
                            voice=note.voice,
                            lyric=note.lyric,
                        )
                break
    return adjusted
