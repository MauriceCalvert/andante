"""Dynamics engine for humanisation.

Combines all dynamics models to produce final velocity values.
"""
from engine.note import Note
from humanisation.context.types import HumanisationProfile, NoteContext
from humanisation.dynamics.balance import compute_balance_offset
from humanisation.dynamics.contour import compute_contour_offset
from humanisation.dynamics.harmonic_tension import compute_harmonic_tension_offset
from humanisation.dynamics.metric_weight import compute_metric_weight_offset
from humanisation.dynamics.phrase_envelope import compute_phrase_envelope
from humanisation.dynamics.touch import compute_touch_variation


def apply_dynamics(
    notes: list[Note],
    contexts: list[NoteContext],
    profile: HumanisationProfile,
    seed: int,
) -> list[Note]:
    """Apply all dynamics models to set note velocities.

    Combines:
    - Phrase envelope: bell curve shaping (multiplicative base)
    - Metric weight: downbeat emphasis (additive)
    - Harmonic tension: dissonance emphasis (additive)
    - Contour: pitch height correlation (additive)
    - Voice balance: melody prominence (additive)
    - Touch variation: random noise (additive)

    Args:
        notes: Note objects (with existing velocity as base)
        contexts: Analysis contexts for each note
        profile: Humanisation profile
        seed: Random seed for reproducibility

    Returns:
        New list of Note objects with adjusted velocity
    """
    if not notes:
        return []

    dynamics = profile.dynamics

    # Compute adjustments from each model
    envelope_multipliers = compute_phrase_envelope(contexts, dynamics)
    metric_offsets = compute_metric_weight_offset(contexts, dynamics)
    tension_offsets = compute_harmonic_tension_offset(contexts, dynamics)
    contour_offsets = compute_contour_offset(notes, dynamics)
    balance_offsets = compute_balance_offset(contexts, dynamics)
    touch_offsets = compute_touch_variation(len(notes), dynamics, seed)

    # Combine and create new notes
    result: list[Note] = []
    for i, note in enumerate(notes):
        # Start with base velocity multiplied by envelope
        base_velocity = note.velocity * envelope_multipliers[i]

        # Add all offsets
        velocity = int(base_velocity
                      + metric_offsets[i]
                      + tension_offsets[i]
                      + contour_offsets[i]
                      + balance_offsets[i]
                      + touch_offsets[i])

        # Clamp to profile range
        velocity = max(dynamics.velocity_min, min(dynamics.velocity_max, velocity))

        # Create new note with adjusted velocity
        new_note = Note(
            midiNote=note.midiNote,
            Offset=note.Offset,
            Duration=note.Duration,
            track=note.track,
            Length=note.Length,
            bar=note.bar,
            beat=note.beat,
            lyric=note.lyric,
            velocity=velocity,
        )
        result.append(new_note)

    return result
