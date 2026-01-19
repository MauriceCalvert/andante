"""SATB Voice Generator.

Generates voices considering all previously decided voices.
No fallbacks - throws VoiceGenerationError with actionable message if no solution.
"""
from fractions import Fraction

from builder.solver.subdivision import pitch_at_offset
from builder.solver.constraints import is_dissonant_diatonic
from builder.types import Notes
from shared.constants import DIATONIC_DEFAULTS, TONAL_ROOTS
from shared.errors import VoiceGenerationError


# Chord tones as diatonic intervals from root: root (0), third (2), fifth (4)
# Order determines preference when multiple options work
CHORD_TONE_INTERVALS: tuple[int, ...] = (0, 4, 2)


def generate_voice(
    existing_voices: list[Notes],
    harmony: tuple[str, ...],
    voice_role: str,
    bar_duration: Fraction,
) -> Notes:
    """Generate a voice that satisfies all constraints against existing voices.

    For each bar, picks a chord tone that doesn't create dissonances with
    any existing voice at any attack point during that bar.

    Args:
        existing_voices: Already decided voices (e.g., [soprano] for bass).
        harmony: Chord symbols per bar (e.g., ("I", "V", "I")).
        voice_role: Voice being generated ("bass", "alto", "tenor").
        bar_duration: Duration of one bar.

    Returns:
        Notes with generated pitches and durations.

    Raises:
        VoiceGenerationError: If no valid pitch exists for any bar.
    """
    assert voice_role in DIATONIC_DEFAULTS, f"Unknown voice role: {voice_role}"
    assert len(existing_voices) > 0, "Need at least one existing voice"
    assert len(harmony) > 0, "Need at least one chord in harmony"

    base_octave: int = DIATONIC_DEFAULTS[voice_role] // 7

    # Collect all attack points from existing voices
    all_attacks: list[Fraction] = _collect_all_attacks(existing_voices)

    pitches: list[int] = []
    durations: list[Fraction] = []

    for bar_idx, chord in enumerate(harmony):
        assert chord in TONAL_ROOTS, f"Unknown chord: '{chord}'"

        bar_start: Fraction = bar_duration * bar_idx
        bar_end: Fraction = bar_start + bar_duration

        # Get attacks in this bar
        attacks_in_bar: list[Fraction] = [
            t for t in all_attacks if bar_start <= t < bar_end
        ]

        # Get chord tones for this chord
        root_degree: int = TONAL_ROOTS[chord] - 1  # Convert 1-7 to 0-6
        chord_tones: list[int] = [
            base_octave * 7 + (root_degree + interval) % 7
            for interval in CHORD_TONE_INTERVALS
        ]

        # Find first chord tone that works at ALL attack points
        valid_pitch: int | None = None
        for candidate in chord_tones:
            if _is_valid_at_all_attacks(candidate, existing_voices, attacks_in_bar):
                valid_pitch = candidate
                break

        if valid_pitch is None:
            # Build detailed error message
            soprano_pitches: list[int] = _get_pitches_in_range(
                existing_voices[0], bar_start, bar_end, all_attacks
            )
            chord_names: list[str] = [
                _diatonic_to_name(ct) for ct in chord_tones
            ]
            soprano_names: list[str] = [
                _diatonic_to_name(p) for p in soprano_pitches
            ]
            raise VoiceGenerationError(
                f"Cannot generate {voice_role} for bar {bar_idx + 1} (chord {chord}): "
                f"all chord tones ({', '.join(chord_names)}) create dissonance "
                f"with existing voices. Soprano in bar: {soprano_names}"
            )

        pitches.append(valid_pitch)
        durations.append(bar_duration)

    return Notes(tuple(pitches), tuple(durations))


def _collect_all_attacks(voices: list[Notes]) -> list[Fraction]:
    """Collect all unique attack points from all voices."""
    offsets: set[Fraction] = set()
    for voice in voices:
        offset: Fraction = Fraction(0)
        for dur in voice.durations:
            offsets.add(offset)
            offset += dur
    return sorted(offsets)


def _is_valid_at_all_attacks(
    candidate: int,
    existing_voices: list[Notes],
    attacks: list[Fraction],
) -> bool:
    """Check if candidate pitch is valid at all attack points."""
    for attack_offset in attacks:
        for voice in existing_voices:
            sounding: int | None = pitch_at_offset(voice, attack_offset)
            if sounding is not None:
                if is_dissonant_diatonic(candidate, sounding):
                    return False
    return True


def _get_pitches_in_range(
    voice: Notes,
    start: Fraction,
    end: Fraction,
    all_attacks: list[Fraction],
) -> list[int]:
    """Get all pitches sounding in a time range."""
    pitches: list[int] = []
    for t in all_attacks:
        if start <= t < end:
            p: int | None = pitch_at_offset(voice, t)
            if p is not None and p not in pitches:
                pitches.append(p)
    return pitches


def _diatonic_to_name(diatonic: int) -> str:
    """Convert diatonic pitch to note name for error messages."""
    names: tuple[str, ...] = ("C", "D", "E", "F", "G", "A", "B")
    octave: int = diatonic // 7
    degree: int = diatonic % 7
    return f"{names[degree]}{octave}"
