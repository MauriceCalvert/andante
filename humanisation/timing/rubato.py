"""Rubato timing model for humanisation.

Phrase-level tempo flexibility implemented as a continuous tempo curve.
"""
import math
from dataclasses import dataclass

from humanisation.context.types import NoteContext, TimingProfile


@dataclass(frozen=True)
class TempoMultiplier:
    """Tempo multiplier at a phrase position."""

    phrase_id: int
    position: float  # 0.0 to 1.0
    multiplier: float  # e.g., 1.08 = 8% faster


def _compute_tempo_multiplier(
    position: float,
    profile: TimingProfile,
) -> float:
    """Compute tempo multiplier for a position in phrase.

    Shape:
    - Steady tempo 0.0 -> cadence_start
    - Gentle ritardando cadence_start -> 1.0 (cadential)

    The early-acceleration model was removed because its cumulative
    effect caused notes to arrive early overall, negating the ritardando.

    Args:
        position: Position in phrase (0.0 to 1.0)
        profile: Timing parameters

    Returns:
        Tempo multiplier (1.0 = no change)
    """
    cadence_start = profile.rubato_cadence_start
    max_decel = profile.rubato_max_decel

    if position < cadence_start:
        # Steady tempo before cadence
        multiplier = 1.0
    else:
        # Cadential ritardando: 1.0 -> max_decel
        t = (position - cadence_start) / (1.0 - cadence_start)
        # Ease-in curve for gradual slowdown
        multiplier = 1.0 - (1.0 - max_decel) * math.sin(t * math.pi / 2)

    return multiplier


def compute_rubato_offsets(
    contexts: list[NoteContext],
    base_tempo_bpm: int,
    profile: TimingProfile,
) -> list[float]:
    """Compute rubato timing offsets for each note.

    Rubato is multiplicative and cumulative - it affects the tempo curve
    which then changes note onset times. This function computes the
    cumulative offset in seconds for each note.

    Args:
        contexts: Analysis contexts for each note
        base_tempo_bpm: Base tempo in BPM
        profile: Timing parameters

    Returns:
        List of timing offsets in seconds, one per note
    """
    if not contexts:
        return []

    # Seconds per beat at base tempo
    seconds_per_beat = 60.0 / base_tempo_bpm

    # Group notes by phrase
    phrase_notes: dict[int, list[tuple[int, NoteContext]]] = {}
    for i, ctx in enumerate(contexts):
        phrase_id = ctx.phrase.phrase_id
        phrase_notes.setdefault(phrase_id, []).append((i, ctx))

    # Compute cumulative offset for each note
    offsets = [0.0] * len(contexts)

    for phrase_id, notes in phrase_notes.items():
        # Sort by original note index (maintains temporal order)
        notes.sort(key=lambda x: x[0])

        cumulative_offset = 0.0
        prev_position = 0.0

        for i, (note_idx, ctx) in enumerate(notes):
            position = ctx.phrase.position_in_phrase
            multiplier = _compute_tempo_multiplier(position, profile)

            # Compute time delta from previous note in phrase
            if i > 0:
                # Position delta represents fraction of phrase
                pos_delta = position - prev_position
                # Base time for this segment (arbitrary units, normalized later)
                base_time = pos_delta * seconds_per_beat

                # Adjusted time with tempo multiplier
                # Faster tempo = shorter time = negative offset relative to mechanical
                adjusted_time = base_time / multiplier
                time_diff = adjusted_time - base_time

                cumulative_offset += time_diff

            offsets[note_idx] = cumulative_offset
            prev_position = position

    return offsets
