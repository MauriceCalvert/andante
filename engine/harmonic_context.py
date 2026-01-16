"""Harmonic context inference from outer voices.

Infers chord from soprano and bass pitches, generates chord tone candidates
for inner voice filling. Core of the slice solver's candidate generation.

Also provides consonant bass generation for 2-voice textures.
"""
from dataclasses import dataclass
from fractions import Fraction
from typing import Tuple

from engine.key import Key
from shared.pitch import FloatingNote, MidiPitch, Pitch, is_rest


@dataclass(frozen=True)
class HarmonicContext:
    """Harmonic context inferred from outer voices at a vertical slice."""
    root_pc: int
    chord_tones: Tuple[int, ...]
    scale: Tuple[int, ...]
    bass_degree: int

    def is_chord_tone(self, pc: int) -> bool:
        """Check if pitch class is a chord tone."""
        return pc in self.chord_tones


def degree_to_pc(degree: int, key: Key) -> int:
    """Convert scale degree (1-7) to pitch class (0-11)."""
    assert 1 <= degree <= 7, f"Degree must be 1-7, got {degree}"
    scale: Tuple[int, ...] = key.scale
    semitones: int = scale[degree - 1]
    return (key.tonic_pc + semitones) % 12


def pc_to_degree(pc: int, key: Key) -> int | None:
    """Convert pitch class (0-11) to scale degree (1-7), or None if chromatic.

    Maps a pitch class to its scale degree in the given key.
    Returns None if the pitch class is not in the scale (chromatic note).
    """
    for degree in range(1, 8):
        if degree_to_pc(degree, key) == pc:
            return degree
    return None


def infer_chord_from_bass(bass_degree: int, key: Key) -> Tuple[int, ...]:
    """Infer triad chord tones from bass degree.

    Assumes root position triad built on bass. Returns pitch classes.
    In baroque practice, bass usually indicates chord root.
    """
    assert 1 <= bass_degree <= 7, f"Bass degree must be 1-7, got {bass_degree}"
    root_pc: int = degree_to_pc(bass_degree, key)
    third_degree: int = ((bass_degree - 1 + 2) % 7) + 1
    fifth_degree: int = ((bass_degree - 1 + 4) % 7) + 1
    third_pc: int = degree_to_pc(third_degree, key)
    fifth_pc: int = degree_to_pc(fifth_degree, key)
    return (root_pc, third_pc, fifth_pc)


def infer_harmony_from_outer(
    soprano_pitch: Pitch,
    bass_pitch: Pitch,
    key: Key,
) -> HarmonicContext:
    """Infer harmonic context from soprano and bass pitches.

    Bass pitch determines chord root (baroque figured bass convention).
    Soprano pitch confirms membership (should be chord tone in good voicing).
    Accepts FloatingNote or MidiPitch.
    """
    assert not is_rest(soprano_pitch), "Soprano cannot be rest"
    assert not is_rest(bass_pitch), "Bass cannot be rest"
    # Extract bass degree from pitch type
    if isinstance(bass_pitch, FloatingNote):
        bass_norm = bass_pitch.degree
    elif isinstance(bass_pitch, MidiPitch):
        bass_pc: int = bass_pitch.midi % 12
        degree: int | None = pc_to_degree(bass_pc, key)
        if degree is None:
            # Chromatic note: default to degree 1 (tonic) as fallback
            bass_norm = 1
        else:
            bass_norm = degree
    else:
        raise TypeError(f"Unexpected bass pitch type: {type(bass_pitch)}")
    chord_tones: Tuple[int, ...] = infer_chord_from_bass(bass_norm, key)
    return HarmonicContext(
        root_pc=chord_tones[0],
        chord_tones=chord_tones,
        scale=key.scale,
        bass_degree=bass_norm,
    )


def generate_chord_tone_candidates(
    context: HarmonicContext,
    voice_low: int,
    voice_high: int,
    key: Key,
) -> Tuple[int, ...]:
    """Generate all chord tones within voice range as MIDI pitches."""
    assert voice_low < voice_high, f"Invalid range: {voice_low}-{voice_high}"
    candidates: list[int] = []
    for pc in context.chord_tones:
        midi: int = pc
        while midi < voice_low:
            midi += 12
        while midi <= voice_high:
            candidates.append(midi)
            midi += 12
    return tuple(sorted(candidates))


def generate_scale_candidates(
    context: HarmonicContext,
    voice_low: int,
    voice_high: int,
    key: Key,
) -> Tuple[int, ...]:
    """Generate all scale degrees within voice range as MIDI pitches.

    Used as fallback when no chord tones fit constraints.
    """
    assert voice_low < voice_high, f"Invalid range: {voice_low}-{voice_high}"
    candidates: list[int] = []
    for semitone in context.scale:
        pc: int = (key.tonic_pc + semitone) % 12
        midi: int = pc
        while midi < voice_low:
            midi += 12
        while midi <= voice_high:
            candidates.append(midi)
            midi += 12
    return tuple(sorted(candidates))


# =============================================================================
# Consonant Bass Generation (for 2-voice accompaniment textures)
# =============================================================================

# Tonal roots mapping (same as expander_util.TONAL_ROOTS)
_TONAL_ROOTS: dict[str, int] = {
    "I": 1, "i": 1, "V": 5, "v": 5, "IV": 4, "iv": 4,
    "vi": 6, "VI": 6, "ii": 2, "iii": 3, "III": 3, "VII": 7, "vii": 7,
}

# Consonant intervals (semitones mod 12)
# unison, minor 3rd, major 3rd, perfect 5th, minor 6th, major 6th
_CONSONANT_INTERVALS: frozenset[int] = frozenset({0, 3, 4, 7, 8, 9})


def get_chord_for_tonal_target(tonal_target: str, key: Key) -> Tuple[int, ...]:
    """Get chord tone degrees (1-7) for a tonal target like 'V' or 'IV'.

    Returns triad degrees built on the tonal target's root.
    Example: 'V' in any key → (5, 7, 2) = root, third, fifth of V chord
    """
    root: int = _TONAL_ROOTS.get(tonal_target, 1)
    third: int = ((root - 1 + 2) % 7) + 1  # 3rd above root in scale
    fifth: int = ((root - 1 + 4) % 7) + 1  # 5th above root in scale
    return (root, third, fifth)


def _is_consonant_interval(soprano_degree: int, bass_degree: int, key: Key) -> bool:
    """Check if soprano and bass degrees form a consonant interval."""
    soprano_pc: int = degree_to_pc(soprano_degree, key)
    bass_pc: int = degree_to_pc(bass_degree, key)
    interval: int = (soprano_pc - bass_pc) % 12
    return interval in _CONSONANT_INTERVALS


def _find_consonant_bass(
    soprano_degree: int,
    chord_degrees: Tuple[int, ...],
    key: Key,
    prev_bass: int | None,
) -> int | None:
    """Find best bass degree from chord that is consonant with soprano.

    Preference order:
    1. Consonant chord tones, preferring root
    2. Closest to previous bass (voice leading)
    3. Return None if nothing consonant (caller should hold previous)

    Returns:
        Bass degree, or None if no consonant option exists (soprano on passing tone)
    """
    consonant_options: list[int] = []
    for degree in chord_degrees:
        if _is_consonant_interval(soprano_degree, degree, key):
            consonant_options.append(degree)

    if not consonant_options:
        # No consonant bass - soprano is on a non-chord/passing tone
        # Return None to signal caller should hold previous bass
        return None

    if prev_bass is None:
        # First note: prefer root
        if chord_degrees[0] in consonant_options:
            return chord_degrees[0]
        return consonant_options[0]

    # Voice leading: prefer smallest interval from previous bass
    def voice_lead_cost(degree: int) -> int:
        # Distance in scale degrees (wrap around)
        diff = abs(degree - prev_bass)
        return min(diff, 7 - diff)

    # Prefer root, then closest
    consonant_options.sort(key=lambda d: (d != chord_degrees[0], voice_lead_cost(d)))
    return consonant_options[0]


def generate_consonant_bass(
    soprano_pitches: Tuple[Pitch, ...],
    soprano_durations: Tuple[Fraction, ...],
    tonal_target: str,
    key: Key,
    budget: Fraction,
    bar_duration: Fraction = Fraction(3, 4),
) -> Tuple[Tuple[Pitch, ...], Tuple[Fraction, ...]]:
    """Generate bass line consonant with soprano using chord tones.

    Baroque dance style: bass moves on strong beats (bar starts) only.
    At each bar, bass picks chord tone that's consonant with the soprano
    note at that beat. This creates a simple, supportive bass line that
    avoids the complexity of note-by-note consonance checking.

    Also avoids hidden fifths by checking voice motion before committing
    to a bass note.

    Args:
        soprano_pitches: Soprano melody as FloatingNotes
        soprano_durations: Durations for each soprano note
        tonal_target: Roman numeral (e.g., "V", "IV", "I")
        key: Key object for pitch class calculation
        budget: Total duration to fill
        bar_duration: Duration of one bar (default 3/4 for minuet)

    Returns:
        (bass_pitches, bass_durations) tuple
    """
    chord_degrees: Tuple[int, ...] = get_chord_for_tonal_target(tonal_target, key)

    # Build soprano timeline: (offset, degree) for each note
    soprano_timeline: list[Tuple[Fraction, int, Fraction]] = []
    offset: Fraction = Fraction(0)
    for pitch, dur in zip(soprano_pitches, soprano_durations):
        if is_rest(pitch):
            soprano_timeline.append((offset, 0, dur))  # 0 = rest marker
        elif isinstance(pitch, FloatingNote):
            soprano_timeline.append((offset, pitch.degree, dur))
        elif isinstance(pitch, MidiPitch):
            deg: int | None = pc_to_degree(pitch.midi % 12, key)
            soprano_timeline.append((offset, deg if deg is not None else 1, dur))
        else:
            soprano_timeline.append((offset, 1, dur))
        offset += dur

    # Generate bass: one note per bar, picking best chord tone
    bass_pitches: list[Pitch] = []
    bass_durations: list[Fraction] = []
    num_bars: int = max(1, int(budget / bar_duration))
    prev_bass: int | None = None
    prev_soprano: int | None = None

    for bar_idx in range(num_bars):
        bar_start: Fraction = bar_duration * bar_idx
        bar_end: Fraction = min(bar_duration * (bar_idx + 1), budget)
        this_bar_dur: Fraction = bar_end - bar_start

        # Find soprano note at bar start (or first note in this bar)
        soprano_at_bar: int = 1  # default
        for sop_offset, sop_deg, sop_dur in soprano_timeline:
            # Note is active at bar_start if it starts at or before bar_start
            # and ends after bar_start
            if sop_offset <= bar_start < sop_offset + sop_dur:
                if sop_deg != 0:  # not a rest
                    soprano_at_bar = sop_deg
                break
            # Or note starts exactly at bar_start
            if sop_offset == bar_start and sop_deg != 0:
                soprano_at_bar = sop_deg
                break

        # Find best bass for this soprano
        bass_deg: int | None = _find_consonant_bass(soprano_at_bar, chord_degrees, key, prev_bass)
        if bass_deg is None:
            # No consonant option - use root
            bass_deg = chord_degrees[0]

        bass_pitches.append(FloatingNote(bass_deg))
        bass_durations.append(this_bar_dur)
        prev_bass = bass_deg

    # Extend or truncate to fit budget
    total: Fraction = sum(bass_durations, Fraction(0))
    if total < budget:
        # Extend last note
        if bass_durations:
            bass_durations[-1] += budget - total
        else:
            bass_pitches.append(FloatingNote(chord_degrees[0]))
            bass_durations.append(budget)
    elif total > budget:
        # Truncate from end
        new_pitches: list[Pitch] = []
        new_durations: list[Fraction] = []
        remaining: Fraction = budget
        for p, d in zip(bass_pitches, bass_durations):
            if remaining <= Fraction(0):
                break
            if d <= remaining:
                new_pitches.append(p)
                new_durations.append(d)
                remaining -= d
            else:
                new_pitches.append(p)
                new_durations.append(remaining)
                remaining = Fraction(0)
        bass_pitches = new_pitches
        bass_durations = new_durations

    return tuple(bass_pitches), tuple(bass_durations)
