"""Phrase orchestrator: delegates soprano and bass generation to dedicated modules."""
from builder.bass_writer import generate_bass_phrase
from builder.cadence_writer import write_cadence
from builder.phrase_types import PhrasePlan, PhraseResult
from builder.soprano_writer import generate_soprano_phrase
from builder.types import Note
from shared.key import Key


def write_phrase(
    plan: PhrasePlan,
    prior_upper: tuple[Note, ...] = (),
    prior_lower: tuple[Note, ...] = (),
    next_phrase_entry_degree: int | None = None,
    next_phrase_entry_key: Key | None = None,
) -> PhraseResult:
    """Write complete phrase (soprano + bass) and return result."""
    soprano_figures: tuple[str, ...] = ()
    bass_pattern_name: str | None = None
    if plan.is_cadential:
        soprano_notes, bass_notes = write_cadence(
            schema_name=plan.schema_name,
            metre=plan.metre,
            local_key=plan.local_key,
            start_offset=plan.start_offset,
            prior_upper=prior_upper,
            prior_lower=prior_lower,
            upper_range=(plan.upper_range.low, plan.upper_range.high),
            lower_range=(plan.lower_range.low, plan.lower_range.high),
            upper_median=plan.upper_median,
            lower_median=plan.lower_median,
        )
    else:
        soprano_notes, soprano_figures = generate_soprano_phrase(
            plan=plan,
            prior_upper=prior_upper,
            next_phrase_entry_degree=next_phrase_entry_degree,
            next_phrase_entry_key=next_phrase_entry_key,
        )
        bass_notes = generate_bass_phrase(
            plan=plan,
            soprano_notes=prior_upper + soprano_notes,
            prior_bass=prior_lower,
        )
        bass_pattern_name = plan.bass_pattern
    return PhraseResult(
        upper_notes=soprano_notes,
        lower_notes=bass_notes,
        exit_upper=soprano_notes[-1].pitch,
        exit_lower=bass_notes[-1].pitch,
        schema_name=plan.schema_name,
        soprano_figures=soprano_figures,
        bass_pattern_name=bass_pattern_name,
    )
