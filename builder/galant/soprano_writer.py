"""Galant structural soprano skeleton builder."""
from fractions import Fraction

from builder.phrase_types import PhrasePlan
from builder.soprano_viterbi import place_structural_tones
from builder.types import Note
from shared.key import Key
from shared.constants import TRACK_SOPRANO
from shared.music_math import parse_metre


def build_structural_soprano(
    plan: PhrasePlan,
    prev_exit_midi: int | None,
) -> tuple[Note, ...]:
    """Build structural soprano skeleton (held notes at schema arrival positions).

    Returns one Note per structural tone, each held until the next structural
    tone (or phrase end for the final tone). Bass writer checks against this
    coarse skeleton; Viterbi soprano generation replaces it with full surface.
    """
    structural_tones: list[tuple[Fraction, int, Key]] = place_structural_tones(
        plan=plan, prev_exit_midi=prev_exit_midi,
    )
    bar_length, beat_unit = parse_metre(metre=plan.metre)
    notes: list[Note] = []
    for i, (offset, midi, key) in enumerate(structural_tones):
        # Duration: until next structural tone, or phrase end for final tone
        if i < len(structural_tones) - 1:
            next_offset: Fraction = structural_tones[i + 1][0]
            duration: Fraction = next_offset - offset
        else:
            phrase_end: Fraction = plan.start_offset + plan.phrase_duration
            duration = phrase_end - offset
        notes.append(Note(
            offset=offset,
            pitch=midi,
            duration=duration,
            voice=TRACK_SOPRANO,
        ))
    return tuple(notes)
