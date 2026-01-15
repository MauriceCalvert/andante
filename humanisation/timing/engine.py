"""Timing engine for humanisation.

Combines all timing models to produce final onset adjustments.
"""
from dataclasses import replace

from engine.note import Note
from humanisation.context.types import HumanisationProfile, NoteContext
from humanisation.timing.agogic import compute_agogic_offsets
from humanisation.timing.melodic_lead import compute_melodic_lead_offsets
from humanisation.timing.motor import compute_motor_offsets
from humanisation.timing.notes_inegales import compute_notes_inegales
from humanisation.timing.rubato import compute_rubato_offsets
from humanisation.timing.stochastic import compute_stochastic_offsets


def apply_timing(
    notes: list[Note],
    contexts: list[NoteContext],
    profile: HumanisationProfile,
    base_tempo_bpm: int,
    seed: int,
) -> list[Note]:
    """Apply all timing models to adjust note onsets.

    Combines:
    - Rubato: phrase-level tempo curve (multiplicative)
    - Agogic: micro-delays for emphasis (additive)
    - Melodic lead: melody arrives early (additive)
    - Motor: physical constraints (additive)
    - Stochastic: correlated drift (additive)
    - Notes inégales: duration/offset adjustment for paired notes

    Args:
        notes: Original Note objects
        contexts: Analysis contexts for each note
        profile: Humanisation profile
        base_tempo_bpm: Base tempo in BPM
        seed: Random seed for reproducibility

    Returns:
        New list of Note objects with adjusted Offset (and Duration for inégales)
    """
    if not notes:
        return []

    timing = profile.timing

    # Compute offsets from each model
    rubato_offsets = compute_rubato_offsets(contexts, base_tempo_bpm, timing)
    agogic_offsets = compute_agogic_offsets(contexts, timing)
    melodic_lead_offsets = compute_melodic_lead_offsets(contexts, timing)
    motor_offsets = compute_motor_offsets(notes, contexts, timing)
    stochastic_offsets = compute_stochastic_offsets(contexts, timing, seed)

    # Compute notes inégales adjustments
    inegales = compute_notes_inegales(notes, contexts, profile.articulation)
    inegales_map: dict[int, tuple[float, float]] = {}  # idx -> (offset_delta, duration_delta)
    for adj in inegales:
        inegales_map[adj.note_index] = (adj.offset_delta, adj.duration_delta)

    # Combine all offsets and create new notes
    result: list[Note] = []
    for i, note in enumerate(notes):
        total_offset = (
            rubato_offsets[i]
            + agogic_offsets[i]
            + melodic_lead_offsets[i]
            + motor_offsets[i]
            + stochastic_offsets[i]
        )

        # Add notes inégales adjustment if applicable
        inegales_offset, inegales_duration = inegales_map.get(i, (0.0, 0.0))
        total_offset += inegales_offset

        # Apply offset to note
        new_offset = note.Offset + total_offset

        # Ensure offset doesn't go negative
        new_offset = max(0.0, new_offset)

        # Apply duration adjustment from notes inégales
        new_duration = note.Duration + inegales_duration
        new_duration = max(0.01, new_duration)  # Minimum duration

        # Create new note with adjusted timing
        new_note = Note(
            midiNote=note.midiNote,
            Offset=new_offset,
            Duration=new_duration,
            track=note.track,
            Length=note.Length,
            bar=note.bar,
            beat=note.beat,
            lyric=note.lyric,
            velocity=note.velocity,
        )
        result.append(new_note)

    return result
