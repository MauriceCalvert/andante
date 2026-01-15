"""Duration modification for humanisation articulation.

Adjusts note durations based on context for expressive articulation.
"""
from engine.note import Note
from humanisation.context.types import ArticulationProfile, NoteContext


def compute_duration_factor(
    note: Note,
    ctx: NoteContext,
    profile: ArticulationProfile,
) -> float:
    """Compute duration factor for a single note.

    Factors that affect duration:
    - Default: slight shortening (notes don't perfectly connect)
    - Phrase boundaries: more separation (breath)
    - Fast passages: crisper articulation
    - Could extend for legato contexts (not implemented yet)

    Args:
        note: Original Note object
        ctx: Analysis context for the note
        profile: Articulation parameters

    Returns:
        Duration factor (1.0 = no change)
    """
    factor = profile.default_gate

    # Phrase endings: additional separation for breath
    if ctx.phrase.is_phrase_boundary:
        factor *= profile.phrase_end_gate

    # Fast passages (short notes): crisper
    if note.Duration < 0.125:  # Sixteenth or shorter
        factor = min(factor, profile.fast_passage_gate)

    # Leaps: slight separation helps clarity
    if ctx.melodic.is_leap:
        factor *= 0.95

    # Peak notes: sustain more for emphasis
    if ctx.melodic.is_peak:
        factor = max(factor, 0.95)

    # Resolution notes: sustain for clarity
    if ctx.harmonic.is_resolution:
        factor = max(factor, 0.92)

    return factor
