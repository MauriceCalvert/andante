"""Phrase orchestrator: delegates soprano and bass generation to dedicated modules."""
from dataclasses import replace
from fractions import Fraction

from builder.bass_viterbi import generate_bass_viterbi
from builder.bass_writer import generate_bass_phrase
from builder.cadence_writer import write_cadence
from builder.imitation import (
    countersubject_to_voice_notes,
    subject_bar_count,
    subject_to_voice_notes,
)
from shared.constants import TRACK_BASS, TRACK_SOPRANO
from builder.phrase_types import PhrasePlan, PhraseResult, make_tail_plan, phrase_bar_start
from builder.soprano_writer import (
    build_structural_soprano,
    generate_soprano_phrase,
    generate_soprano_viterbi,
)
from builder.types import Note
from motifs.fugue_loader import LoadedFugue
from shared.key import Key
from shared.music_math import parse_metre


def _pad_to_offset(
    notes: tuple[Note, ...],
    target_offset: Fraction,
) -> tuple[Note, ...]:
    """Extend last note to reach target_offset (subject-to-tail boundary)."""
    note_end: Fraction = notes[-1].offset + notes[-1].duration
    if note_end >= target_offset:
        return notes
    last: Note = notes[-1]
    return notes[:-1] + (
        replace(last, duration=last.duration + (target_offset - note_end)),
    )


def _is_walking(plan: PhrasePlan) -> bool:
    """True if plan uses walking bass texture (Viterbi path)."""
    return (
        plan.bass_texture == "walking"
        or (plan.bass_pattern is not None
            and plan.bass_pattern.startswith("continuo_walking"))
    )


def _bass_for_plan(
    plan: PhrasePlan,
    soprano_notes: tuple[Note, ...],
    prior_bass: tuple[Note, ...],
) -> tuple[Note, ...]:
    """Dispatch bass generation: Viterbi for walking, greedy otherwise."""
    if _is_walking(plan=plan):
        return generate_bass_viterbi(
            plan=plan,
            soprano_notes=soprano_notes,
            prior_lower=prior_bass,
        )
    return generate_bass_phrase(
        plan=plan,
        soprano_notes=soprano_notes,
        prior_bass=prior_bass,
    )


def _write_subject_phrase(
    plan: PhrasePlan,
    fugue: LoadedFugue,
    prior_upper: tuple[Note, ...],
    prior_lower: tuple[Note, ...],
    next_phrase_entry_degree: int | None,
    next_phrase_entry_key: Key | None,
) -> PhraseResult:
    """Write subject entry: lead voice gets subject, tail bars get schema-based generation."""
    subj_bars: int = subject_bar_count(fugue=fugue)
    assert subj_bars <= plan.bar_span, (
        f"Subject occupies {subj_bars} bars but phrase only has {plan.bar_span} bars"
    )
    lead_voice: int = plan.lead_voice if plan.lead_voice is not None else 0
    is_monophonic: bool = lead_voice == 0 and len(prior_lower) == 0
    needs_tail: bool = subj_bars < plan.bar_span
    tail_start_bar: int = subj_bars + 1

    bar_length: Fraction = parse_metre(metre=plan.metre)[0]

    if lead_voice == 0:
        # Soprano leads with subject transposed to local key
        soprano_subject: tuple[Note, ...] = subject_to_voice_notes(
            fugue=fugue,
            start_offset=plan.start_offset,
            target_key=plan.local_key,
            target_track=TRACK_SOPRANO,
            target_range=plan.upper_range,
        )
        soprano_subject = (replace(soprano_subject[0], lyric="subject"),) + soprano_subject[1:]

        if needs_tail:
            tail_offset: Fraction = phrase_bar_start(
                plan=plan, bar_num=tail_start_bar, bar_length=bar_length,
            )
            soprano_subject = _pad_to_offset(notes=soprano_subject, target_offset=tail_offset)
            tail_plan: PhrasePlan = make_tail_plan(
                plan=plan,
                tail_start_bar=tail_start_bar,
                tail_start_offset=tail_offset,
                prev_exit_upper=soprano_subject[-1].pitch,
                prev_exit_lower=plan.prev_exit_lower,
            )
            tail_soprano: tuple[Note, ...]
            tail_soprano, _ = generate_soprano_phrase(
                plan=tail_plan,
                prior_upper=soprano_subject,
            )
            soprano_notes: tuple[Note, ...] = soprano_subject + tail_soprano
        else:
            soprano_notes = soprano_subject

        if is_monophonic:
            exit_upper: int = soprano_notes[-1].pitch
            exit_lower: int = max(
                plan.lower_range.low,
                min(exit_upper - 12, plan.lower_range.high),
            )
            return PhraseResult(
                upper_notes=soprano_notes,
                lower_notes=(),
                exit_upper=exit_upper,
                exit_lower=exit_lower,
                schema_name=plan.schema_name,
                soprano_figures=(),
                bass_pattern_name=None,
            )

        # Generate bass against pre-composed soprano (full plan)
        bass_notes: tuple[Note, ...] = _bass_for_plan(
            plan=plan,
            soprano_notes=prior_upper + soprano_notes,
            prior_bass=prior_lower,
        )
        return PhraseResult(
            upper_notes=soprano_notes,
            lower_notes=bass_notes,
            exit_upper=soprano_notes[-1].pitch,
            exit_lower=bass_notes[-1].pitch,
            schema_name=plan.schema_name,
            soprano_figures=(),
            bass_pattern_name=None,
        )

    # lead_voice == 1: Bass leads with subject — Viterbi soprano path
    bass_subject: tuple[Note, ...] = subject_to_voice_notes(
        fugue=fugue,
        start_offset=plan.start_offset,
        target_key=plan.local_key,
        target_track=TRACK_BASS,
        target_range=plan.lower_range,
    )
    bass_subject = (replace(bass_subject[0], lyric="subject"),) + bass_subject[1:]

    prev_exit_midi: int | None = prior_upper[-1].pitch if prior_upper else None

    if needs_tail:
        tail_offset: Fraction = phrase_bar_start(
            plan=plan, bar_num=tail_start_bar, bar_length=bar_length,
        )
        bass_subject = _pad_to_offset(notes=bass_subject, target_offset=tail_offset)
        structural_soprano: tuple[Note, ...] = build_structural_soprano(
            plan=plan, prev_exit_midi=prev_exit_midi,
        )
        tail_plan: PhrasePlan = make_tail_plan(
            plan=plan,
            tail_start_bar=tail_start_bar,
            tail_start_offset=tail_offset,
            prev_exit_upper=structural_soprano[-1].pitch,
            prev_exit_lower=bass_subject[-1].pitch,
        )
        tail_bass: tuple[Note, ...] = _bass_for_plan(
            plan=tail_plan,
            soprano_notes=prior_upper + structural_soprano,
            prior_bass=bass_subject,
        )
        full_bass: tuple[Note, ...] = bass_subject + tail_bass
    else:
        full_bass = bass_subject

    soprano_notes, _ = generate_soprano_viterbi(
        plan=plan,
        bass_notes=full_bass,
        prior_upper=prior_upper,
        next_phrase_entry_degree=next_phrase_entry_degree,
        next_phrase_entry_key=next_phrase_entry_key,
    )

    return PhraseResult(
        upper_notes=soprano_notes,
        lower_notes=full_bass,
        exit_upper=soprano_notes[-1].pitch,
        exit_lower=full_bass[-1].pitch,
        schema_name=plan.schema_name,
        soprano_figures=(),
        bass_pattern_name=None,
    )


def _write_answer_phrase(
    plan: PhrasePlan,
    fugue: LoadedFugue,
    prior_upper: tuple[Note, ...],
    prior_lower: tuple[Note, ...],
    next_phrase_entry_degree: int | None,
    next_phrase_entry_key: Key | None,
) -> PhraseResult:
    """Write answer entry: subject at dominant, tail bars get schema-based generation."""
    lead_voice: int = plan.lead_voice if plan.lead_voice is not None else 0
    dominant_key: Key = plan.local_key.modulate_to(target="V")
    subj_bars: int = subject_bar_count(fugue=fugue)
    needs_tail: bool = subj_bars < plan.bar_span
    tail_start_bar: int = subj_bars + 1
    bar_length: Fraction = parse_metre(metre=plan.metre)[0]

    if lead_voice == 0:
        # Bass gets the answer (subject at dominant)
        bass_answer: tuple[Note, ...] = subject_to_voice_notes(
            fugue=fugue,
            start_offset=plan.start_offset,
            target_key=dominant_key,
            target_track=TRACK_BASS,
            target_range=plan.lower_range,
        )
        bass_answer = (replace(bass_answer[0], lyric="answer"),) + bass_answer[1:]

        # Soprano gets the countersubject (at tonic, not dominant)
        soprano_cs: tuple[Note, ...] = countersubject_to_voice_notes(
            fugue=fugue,
            start_offset=plan.start_offset,
            target_key=plan.local_key,
            target_track=TRACK_SOPRANO,
            target_range=plan.upper_range,
        )
        soprano_cs = (replace(soprano_cs[0], lyric="cs"),) + soprano_cs[1:]

        if needs_tail:
            tail_offset: Fraction = phrase_bar_start(
                plan=plan, bar_num=tail_start_bar, bar_length=bar_length,
            )
            bass_answer = _pad_to_offset(notes=bass_answer, target_offset=tail_offset)
            soprano_cs = _pad_to_offset(notes=soprano_cs, target_offset=tail_offset)
            tail_plan: PhrasePlan = make_tail_plan(
                plan=plan,
                tail_start_bar=tail_start_bar,
                tail_start_offset=tail_offset,
                prev_exit_upper=soprano_cs[-1].pitch,
                prev_exit_lower=bass_answer[-1].pitch,
            )
            tail_soprano: tuple[Note, ...]
            tail_soprano, _ = generate_soprano_phrase(
                plan=tail_plan,
                prior_upper=soprano_cs,
                lower_notes=bass_answer,
            )
            soprano_notes: tuple[Note, ...] = soprano_cs + tail_soprano
            tail_bass: tuple[Note, ...] = _bass_for_plan(
                plan=tail_plan,
                soprano_notes=prior_upper + soprano_notes,
                prior_bass=bass_answer,
            )
            bass_notes: tuple[Note, ...] = bass_answer + tail_bass
        else:
            soprano_notes = soprano_cs
            bass_notes = bass_answer

        return PhraseResult(
            upper_notes=soprano_notes,
            lower_notes=bass_notes,
            exit_upper=soprano_notes[-1].pitch,
            exit_lower=bass_notes[-1].pitch,
            schema_name=plan.schema_name,
            soprano_figures=(),
            bass_pattern_name=None,
        )

    # lead_voice == 1: Soprano gets the answer (subject at dominant), bass generates
    soprano_answer: tuple[Note, ...] = subject_to_voice_notes(
        fugue=fugue,
        start_offset=plan.start_offset,
        target_key=dominant_key,
        target_track=TRACK_SOPRANO,
        target_range=plan.upper_range,
    )
    soprano_answer = (replace(soprano_answer[0], lyric="answer"),) + soprano_answer[1:]

    if needs_tail:
        tail_offset = phrase_bar_start(
            plan=plan, bar_num=tail_start_bar, bar_length=bar_length,
        )
        soprano_answer = _pad_to_offset(notes=soprano_answer, target_offset=tail_offset)
        tail_plan = make_tail_plan(
            plan=plan,
            tail_start_bar=tail_start_bar,
            tail_start_offset=tail_offset,
            prev_exit_upper=soprano_answer[-1].pitch,
            prev_exit_lower=plan.prev_exit_lower,
        )
        tail_soprano: tuple[Note, ...]
        tail_soprano, _ = generate_soprano_phrase(
            plan=tail_plan,
            prior_upper=soprano_answer,
        )
        soprano_notes = soprano_answer + tail_soprano
    else:
        soprano_notes = soprano_answer

    bass_notes = _bass_for_plan(
        plan=plan,
        soprano_notes=prior_upper + soprano_notes,
        prior_bass=prior_lower,
    )
    return PhraseResult(
        upper_notes=soprano_notes,
        lower_notes=bass_notes,
        exit_upper=soprano_notes[-1].pitch,
        exit_lower=bass_notes[-1].pitch,
        schema_name=plan.schema_name,
        soprano_figures=(),
        bass_pattern_name=None,
    )


def write_phrase(
    plan: PhrasePlan,
    prior_upper: tuple[Note, ...] = (),
    prior_lower: tuple[Note, ...] = (),
    next_phrase_entry_degree: int | None = None,
    next_phrase_entry_key: Key | None = None,
    recall_figure_name: str | None = None,
    fugue: LoadedFugue | None = None,
) -> PhraseResult:
    """Write complete phrase (soprano + bass) and return result."""
    soprano_figures: tuple[str, ...] = ()
    bass_pattern_name: str | None = None
    # Imitation dispatch: pre-composed material from FugueTriple
    if (plan.imitation_role is not None
            and fugue is not None
            and not plan.is_cadential):
        if plan.imitation_role == "subject":
            return _write_subject_phrase(
                plan=plan,
                fugue=fugue,
                prior_upper=prior_upper,
                prior_lower=prior_lower,
                next_phrase_entry_degree=next_phrase_entry_degree,
                next_phrase_entry_key=next_phrase_entry_key,
            )
        if plan.imitation_role == "answer":
            return _write_answer_phrase(
                plan=plan,
                fugue=fugue,
                prior_upper=prior_upper,
                prior_lower=prior_lower,
                next_phrase_entry_degree=next_phrase_entry_degree,
                next_phrase_entry_key=next_phrase_entry_key,
            )
        assert False, f"Unknown imitation_role: {plan.imitation_role!r}"
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
        # Galant path: build structural soprano, generate bass, then Viterbi soprano
        prev_exit_upper: int | None = prior_upper[-1].pitch if prior_upper else None
        structural_soprano: tuple[Note, ...] = build_structural_soprano(
            plan=plan,
            prev_exit_midi=prev_exit_upper,
        )
        bass_notes = _bass_for_plan(
            plan=plan,
            soprano_notes=prior_upper + structural_soprano,
            prior_bass=prior_lower,
        )
        soprano_notes, soprano_figures = generate_soprano_viterbi(
            plan=plan,
            bass_notes=bass_notes,
            prior_upper=prior_upper,
            next_phrase_entry_degree=next_phrase_entry_degree,
            next_phrase_entry_key=next_phrase_entry_key,
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
