"""Entry point: execute phrase-based composition.

Given a sequence of PhrasePlans, composes each phrase in order using
the phrase writer, threading exit pitches between consecutive phrases.
"""
from fractions import Fraction
from builder.cadence_writer import load_cadence_templates
from builder.phrase_types import PhrasePlan, PhraseResult, phrase_degree_offset
from builder.phrase_writer import write_phrase
from builder.types import Composition, Note
from shared.key import Key
from shared.music_math import parse_metre
from shared.tracer import get_tracer


def _structural_offsets_for_plan(plan: PhrasePlan) -> tuple[frozenset[Fraction], frozenset[Fraction]]:
    """Compute structural (schema-mandated) offsets for upper and lower voices.

    Cadential phrases: all note offsets are structural (fixed templates).
    Non-cadential: offsets derived from degree_positions.
    Returns (upper_structural, lower_structural).
    """
    if plan.is_cadential:
        # Cadential templates are entirely schema-mandated; actual offsets
        # determined after write_phrase, so return sentinel for "all structural"
        return frozenset(), frozenset()
    bar_length, beat_unit = parse_metre(metre=plan.metre)
    offsets: frozenset[Fraction] = frozenset(
        phrase_degree_offset(plan=plan, pos=pos, bar_length=bar_length, beat_unit=beat_unit)
        for pos in plan.degree_positions
    )
    return offsets, offsets


def compose_phrases(
    phrase_plans: tuple[PhrasePlan, ...],
    home_key: Key,
    metre: str,
    tempo: int,
    upbeat: Fraction,
) -> Composition:
    """Compose a piece phrase by phrase using the phrase writer."""
    assert len(phrase_plans) > 0, "Must have at least one PhrasePlan"
    upper_notes: list[Note] = []
    lower_notes: list[Note] = []
    upper_structural: set[Fraction] = set()
    lower_structural: set[Fraction] = set()
    prev_upper_pitch: int | None = None
    prev_lower_pitch: int | None = None
    prev_prev_lower_pitch: int | None = None
    for plan_idx, plan in enumerate(phrase_plans):
        # Compute next phrase's first soprano degree/key for cross-phrase guard
        next_entry_degree: int | None = None
        next_entry_key: Key | None = None
        if plan_idx < len(phrase_plans) - 1:
            next_plan: PhrasePlan = phrase_plans[plan_idx + 1]
            if next_plan.is_cadential:
                templates = load_cadence_templates()
                tpl_key: tuple[str, str] = (next_plan.schema_name, next_plan.metre)
                assert tpl_key in templates, (
                    f"No cadence template for '{next_plan.schema_name}' "
                    f"in metre '{next_plan.metre}'"
                )
                next_entry_degree = templates[tpl_key].soprano_degrees[0]
                next_entry_key = next_plan.local_key
            else:
                next_entry_degree = next_plan.degrees_upper[0]
                next_entry_key = (
                    next_plan.degree_keys[0]
                    if next_plan.degree_keys is not None
                    else next_plan.local_key
                )
        result: PhraseResult = write_phrase(
            plan=plan,
            prev_upper_midi=prev_upper_pitch,
            prev_lower_midi=prev_lower_pitch,
            prev_prev_lower_midi=prev_prev_lower_pitch,
            next_phrase_entry_degree=next_entry_degree,
            next_phrase_entry_key=next_entry_key,
        )
        upper_notes.extend(result.upper_notes)
        lower_notes.extend(result.lower_notes)
        get_tracer().trace_phrase_result(
            index=plan_idx,
            plan=plan,
            result=result,
        )
        # Collect structural offsets
        up_struct, lo_struct = _structural_offsets_for_plan(plan=plan)
        if plan.is_cadential:
            # All cadential note offsets are structural
            upper_structural.update(n.offset for n in result.upper_notes)
            lower_structural.update(n.offset for n in result.lower_notes)
        else:
            upper_structural.update(up_struct)
            lower_structural.update(lo_struct)
        if result.upper_notes:
            prev_upper_pitch = result.upper_notes[-1].pitch
        if result.lower_notes:
            prev_prev_lower_pitch = (
                result.lower_notes[-2].pitch
                if len(result.lower_notes) >= 2
                else prev_lower_pitch
            )
            prev_lower_pitch = result.lower_notes[-1].pitch
    get_tracer().trace_L6_header(
        total_upper=len(upper_notes),
        total_lower=len(lower_notes),
    )
    phrase_offsets: tuple[Fraction, ...] = tuple(
        p.start_offset for p in phrase_plans
    )
    return Composition(
        voices={
            "soprano": tuple(upper_notes),
            "bass": tuple(lower_notes),
        },
        metre=metre,
        tempo=tempo,
        upbeat=upbeat,
        phrase_offsets=phrase_offsets,
        structural_offsets={
            "soprano": frozenset(upper_structural),
            "bass": frozenset(lower_structural),
        },
    )
