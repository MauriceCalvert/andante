"""Entry point: execute phrase-based composition.

Given a sequence of PhrasePlans, composes each phrase in order using
the phrase writer, threading exit pitches between consecutive phrases.
"""
from fractions import Fraction
from builder.phrase_types import PhrasePlan, PhraseResult
from builder.phrase_writer import write_phrase
from builder.types import Composition, Note
from shared.key import Key


def compose_phrases(
    phrase_plans: tuple[PhrasePlan, ...],
    home_key: Key,
    metre: str,
    tempo: int,
    upbeat: Fraction,
) -> Composition:
    """Compose a piece phrase by phrase using the phrase writer.

    Args:
        phrase_plans: Sequence of PhrasePlans, one per schema in the chain.
        home_key: Home key of the composition.
        metre: Time signature string (e.g., "3/4").
        tempo: Tempo in BPM.
        upbeat: Anacrusis duration in whole notes.

    Returns:
        Composition with "soprano" and "bass" voice entries.
    """
    assert len(phrase_plans) > 0, "Must have at least one PhrasePlan"
    upper_notes: list[Note] = []
    lower_notes: list[Note] = []
    prev_upper_pitch: int | None = None
    prev_lower_pitch: int | None = None
    for plan in phrase_plans:
        result: PhraseResult = write_phrase(
            plan=plan,
            prev_upper_midi=prev_upper_pitch,
            prev_lower_midi=prev_lower_pitch,
        )
        upper_notes.extend(result.upper_notes)
        lower_notes.extend(result.lower_notes)
        if result.upper_notes:
            prev_upper_pitch = result.upper_notes[-1].pitch
        if result.lower_notes:
            prev_lower_pitch = result.lower_notes[-1].pitch
    return Composition(
        voices={
            "soprano": tuple(upper_notes),
            "bass": tuple(lower_notes),
        },
        metre=metre,
        tempo=tempo,
        upbeat=upbeat,
    )
