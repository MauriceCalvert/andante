"""Phrase orchestrator: delegates soprano and bass generation to dedicated modules."""
from dataclasses import replace
from fractions import Fraction

from builder.bass_viterbi import generate_bass_viterbi
from builder.bass_writer import generate_bass_phrase
from builder.cadence_writer import write_cadence
from builder.harmony import build_harmonic_grid, HarmonicGrid
from builder.imitation import (
    countersubject_to_voice_notes,
    DURATION_DENOMINATOR_LIMIT,
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
from planner.schema_loader import get_schema
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
    harmonic_grid: HarmonicGrid | None = None,
) -> tuple[Note, ...]:
    """Dispatch bass generation: Viterbi for walking, greedy otherwise."""
    if _is_walking(plan=plan):
        return generate_bass_viterbi(
            plan=plan,
            soprano_notes=soprano_notes,
            prior_lower=prior_bass,
            harmonic_grid=harmonic_grid,
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

        # Non-monophonic: place countersubject in bass (INV-1)
        bass_cs: tuple[Note, ...] = countersubject_to_voice_notes(
            fugue=fugue,
            start_offset=plan.start_offset,
            target_key=plan.local_key,
            target_track=TRACK_BASS,
            target_range=plan.lower_range,
        )
        bass_cs = (replace(bass_cs[0], lyric="cs"),) + bass_cs[1:]

        if needs_tail:
            tail_offset: Fraction = phrase_bar_start(
                plan=plan, bar_num=tail_start_bar, bar_length=bar_length,
            )
            bass_cs = _pad_to_offset(notes=bass_cs, target_offset=tail_offset)
            tail_plan: PhrasePlan = make_tail_plan(
                plan=plan,
                tail_start_bar=tail_start_bar,
                tail_start_offset=tail_offset,
                prev_exit_upper=soprano_notes[-1].pitch,
                prev_exit_lower=bass_cs[-1].pitch,
            )
            tail_bass: tuple[Note, ...] = _bass_for_plan(
                plan=tail_plan,
                soprano_notes=prior_upper + soprano_notes,
                prior_bass=bass_cs,
            )
            bass_notes: tuple[Note, ...] = bass_cs + tail_bass
        else:
            bass_notes = bass_cs

        return PhraseResult(
            upper_notes=soprano_notes,
            lower_notes=bass_notes,
            exit_upper=soprano_notes[-1].pitch,
            exit_lower=bass_notes[-1].pitch,
            schema_name=plan.schema_name,
            soprano_figures=(),
            bass_pattern_name=None,
        )

    # lead_voice == 1: Bass leads with subject, soprano gets CS (INV-1)
    bass_subject: tuple[Note, ...] = subject_to_voice_notes(
        fugue=fugue,
        start_offset=plan.start_offset,
        target_key=plan.local_key,
        target_track=TRACK_BASS,
        target_range=plan.lower_range,
    )
    bass_subject = (replace(bass_subject[0], lyric="subject"),) + bass_subject[1:]

    # Generate countersubject in soprano
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
        bass_subject = _pad_to_offset(notes=bass_subject, target_offset=tail_offset)
        soprano_cs = _pad_to_offset(notes=soprano_cs, target_offset=tail_offset)
        tail_plan: PhrasePlan = make_tail_plan(
            plan=plan,
            tail_start_bar=tail_start_bar,
            tail_start_offset=tail_offset,
            prev_exit_upper=soprano_cs[-1].pitch,
            prev_exit_lower=bass_subject[-1].pitch,
        )
        tail_soprano: tuple[Note, ...]
        tail_soprano, _ = generate_soprano_viterbi(
            plan=tail_plan,
            bass_notes=bass_subject,
            prior_upper=soprano_cs,
            next_phrase_entry_degree=next_phrase_entry_degree,
            next_phrase_entry_key=next_phrase_entry_key,
        )
        soprano_notes: tuple[Note, ...] = soprano_cs + tail_soprano
        tail_bass: tuple[Note, ...] = _bass_for_plan(
            plan=tail_plan,
            soprano_notes=prior_upper + soprano_notes,
            prior_bass=bass_subject,
        )
        full_bass: tuple[Note, ...] = bass_subject + tail_bass
    else:
        soprano_notes = soprano_cs
        full_bass = bass_subject

    return PhraseResult(
        upper_notes=soprano_notes,
        lower_notes=full_bass,
        exit_upper=soprano_notes[-1].pitch,
        exit_lower=full_bass[-1].pitch,
        schema_name=plan.schema_name,
        soprano_figures=(),
        bass_pattern_name=None,
    )


def _write_stretto_phrase(
    plan: PhrasePlan,
    fugue: LoadedFugue,
    prior_upper: tuple[Note, ...],
    prior_lower: tuple[Note, ...],
) -> PhraseResult:
    """Write stretto phrase: both voices state subject with delay.

    Voice A (lead) states subject at phrase start. Voice B (follower) enters
    1 bar later with the same subject. During overlap, both voices carry
    pre-composed material. After overlap, remaining bars are Viterbi fill.
    """
    bar_length: Fraction = parse_metre(metre=plan.metre)[0]
    lead_voice: int = plan.lead_voice if plan.lead_voice is not None else 0
    follow_voice: int = 1 - lead_voice

    # Stretto parameters (close stretto: 1 beat delay to fit in short phrases)
    # For 4/4 time, 1 beat = 0.25 bars
    STRETTO_DELAY_BEATS: int = 1
    beat_duration: Fraction = parse_metre(metre=plan.metre)[1]
    delay_offset: Fraction = STRETTO_DELAY_BEATS * beat_duration

    # Subject duration
    subject_duration: Fraction = sum(
        Fraction(d).limit_denominator(DURATION_DENOMINATOR_LIMIT)
        for d in fugue.subject.durations
    )

    # Validate stretto fits in phrase
    assert delay_offset < subject_duration, (
        f"Stretto delay ({delay_offset}) must be less than subject duration ({subject_duration})"
    )

    stretto_end: Fraction = delay_offset + subject_duration
    if stretto_end > plan.phrase_duration:
        # Phrase too short for stretto — fall back to subject entry
        from shared.errors import brief_warning
        brief_warning(
            what_failed=f"Stretto in {plan.schema_name} ({plan.phrase_duration} bars)",
            why=f"needs {stretto_end} bars but the phrase only has {plan.phrase_duration}",
            suggestion="give the peroratio a longer non-cadential schema so stretto has room to breathe",
        )
        return _write_subject_phrase(
            plan=plan,
            fugue=fugue,
            prior_upper=prior_upper,
            prior_lower=prior_lower,
            next_phrase_entry_degree=None,
            next_phrase_entry_key=None,
        )

    # Place voice A (lead) subject
    if lead_voice == 0:
        lead_track = TRACK_SOPRANO
        lead_range = plan.upper_range
        follow_track = TRACK_BASS
        follow_range = plan.lower_range
    else:
        lead_track = TRACK_BASS
        lead_range = plan.lower_range
        follow_track = TRACK_SOPRANO
        follow_range = plan.upper_range

    voice_a_subject: tuple[Note, ...] = subject_to_voice_notes(
        fugue=fugue,
        start_offset=plan.start_offset,
        target_key=plan.local_key,
        target_track=lead_track,
        target_range=lead_range,
    )
    voice_a_subject = (replace(voice_a_subject[0], lyric="stretto"),) + voice_a_subject[1:]

    # Place voice B (follower) subject with delay
    voice_b_subject: tuple[Note, ...] = subject_to_voice_notes(
        fugue=fugue,
        start_offset=plan.start_offset + delay_offset,
        target_key=plan.local_key,
        target_track=follow_track,
        target_range=follow_range,
    )
    voice_b_subject = (replace(voice_b_subject[0], lyric="stretto-2"),) + voice_b_subject[1:]

    # Before voice B's entry: hold exit pitch from prior notes
    voice_b_pre_notes: tuple[Note, ...] = ()
    if lead_voice == 0:
        # Voice B is bass
        prior_bass_pitch: int | None = prior_lower[-1].pitch if prior_lower else None
        if prior_bass_pitch is not None:
            voice_b_pre_notes = (Note(
                offset=plan.start_offset,
                pitch=prior_bass_pitch,
                duration=delay_offset,
                voice=TRACK_BASS,
            ),)
    else:
        # Voice B is soprano
        prior_soprano_pitch: int | None = prior_upper[-1].pitch if prior_upper else None
        if prior_soprano_pitch is not None:
            voice_b_pre_notes = (Note(
                offset=plan.start_offset,
                pitch=prior_soprano_pitch,
                duration=delay_offset,
                voice=TRACK_SOPRANO,
            ),)

    # Combine pre-entry hold + subject for voice B
    voice_b_notes: tuple[Note, ...] = voice_b_pre_notes + voice_b_subject

    # Assign to soprano/bass based on lead_voice
    if lead_voice == 0:
        soprano_notes = voice_a_subject
        bass_notes = voice_b_notes
    else:
        soprano_notes = voice_b_notes
        bass_notes = voice_a_subject

    # After both subjects end: generate Viterbi tail if needed
    voice_a_end: Fraction = plan.start_offset + subject_duration
    voice_b_end: Fraction = plan.start_offset + delay_offset + subject_duration
    final_end: Fraction = max(voice_a_end, voice_b_end)
    # Gap zone: voice A ends before voice B (always, since B is delayed).
    # Pad voice A's last note to bridge the gap.
    if voice_a_end < final_end:
        if lead_voice == 0:
            soprano_notes = _pad_to_offset(notes=soprano_notes, target_offset=final_end)
        else:
            bass_notes = _pad_to_offset(notes=bass_notes, target_offset=final_end)
    if final_end < plan.start_offset + plan.phrase_duration:
        # Build tail plan for remaining bars
        tail_plan: PhrasePlan = make_tail_plan(
            plan=plan,
            tail_start_bar=int((final_end - plan.start_offset) // bar_length) + 1,
            tail_start_offset=final_end,
            prev_exit_upper=soprano_notes[-1].pitch,
            prev_exit_lower=bass_notes[-1].pitch,
        )
        # Galant order: structural soprano → bass → Viterbi soprano
        structural_tail: tuple[Note, ...] = build_structural_soprano(
            plan=tail_plan,
            prev_exit_midi=soprano_notes[-1].pitch,
        )
        tail_bass: tuple[Note, ...] = generate_bass_viterbi(
            plan=tail_plan,
            soprano_notes=soprano_notes + structural_tail,
            prior_lower=bass_notes,
            harmonic_grid=None,
        )
        bass_notes = bass_notes + tail_bass
        tail_soprano: tuple[Note, ...]
        tail_soprano, _ = generate_soprano_viterbi(
            plan=tail_plan,
            bass_notes=bass_notes,
            prior_upper=soprano_notes,
            next_phrase_entry_degree=None,
            next_phrase_entry_key=None,
            harmonic_grid=None,
        )
        soprano_notes = soprano_notes + tail_soprano

    return PhraseResult(
        upper_notes=soprano_notes,
        lower_notes=bass_notes,
        exit_upper=soprano_notes[-1].pitch,
        exit_lower=bass_notes[-1].pitch,
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
    is_final: bool = False,
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
        if plan.imitation_role == "episode":
            if plan.degree_keys and len(plan.degree_keys) > 0:
                from builder.episode_writer import write_episode
                return write_episode(
                    plan=plan,
                    fugue=fugue,
                    prior_upper=prior_upper,
                    prior_lower=prior_lower,
                )
            from shared.errors import brief_warning
            brief_warning(
                what_failed=f"Episode on schema '{plan.schema_name}'",
                why="schema has no degree_keys so there is nothing to sequence the fragment through",
                suggestion="use a sequential schema (fonte, monte) for episode phrases, or don't assign imitation_role='episode' here",
            )
            # fall through to galant path below
        if plan.imitation_role == "stretto":
            return _write_stretto_phrase(
                plan=plan,
                fugue=fugue,
                prior_upper=prior_upper,
                prior_lower=prior_lower,
            )
        if plan.imitation_role not in ("episode",):
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
            is_final=is_final,
        )
    else:
        # Galant path: build structural soprano, generate bass, then Viterbi soprano
        # HRL-2: Build harmonic grid from schema annotations
        schema = get_schema(name=plan.schema_name)
        harmonic_grid: HarmonicGrid | None = None
        if schema.harmony is not None:
            harmonic_grid = build_harmonic_grid(
                plan=plan,
                schema_harmony=schema.harmony,
            )

        prev_exit_upper: int | None = prior_upper[-1].pitch if prior_upper else None
        structural_soprano: tuple[Note, ...] = build_structural_soprano(
            plan=plan,
            prev_exit_midi=prev_exit_upper,
        )
        bass_notes = _bass_for_plan(
            plan=plan,
            soprano_notes=prior_upper + structural_soprano,
            prior_bass=prior_lower,
            harmonic_grid=harmonic_grid,
        )
        soprano_notes, soprano_figures = generate_soprano_viterbi(
            plan=plan,
            bass_notes=bass_notes,
            prior_upper=prior_upper,
            next_phrase_entry_degree=next_phrase_entry_degree,
            next_phrase_entry_key=next_phrase_entry_key,
            harmonic_grid=harmonic_grid,
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
