"""Entry point: execute phrase-based composition.

Given a sequence of PhrasePlans, composes each phrase in order using
the phrase writer, threading exit pitches between consecutive phrases.
"""
import logging
from dataclasses import replace
from fractions import Fraction

from builder.cadence_writer import cadence_entry_degree
from builder.phrase_types import HeadMotif, PhrasePlan, PhraseResult, phrase_bar_start, phrase_degree_offset
from builder.phrase_writer import write_phrase
from builder.types import Composition, Note
from motifs.episode_dialogue import EpisodeDialogue
from motifs.subject_loader import SubjectTriple
from shared.key import Key
from shared.music_math import parse_metre
from shared.tracer import get_tracer, _key_str

logger = logging.getLogger(__name__)


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


def _stamp_lyrics(plan: PhrasePlan, result: PhraseResult) -> tuple[Note, ...]:
    """Annotate soprano notes with schema/section/character/figuration lyrics.

    Preserves existing thematic lyrics (subject, answer, cs) from thematic phrases.
    """
    if not result.upper_notes:
        return result.upper_notes

    notes: list[Note] = list(result.upper_notes)
    first_parts: list[str] = [plan.schema_name, plan.section_name, plan.character]
    if plan.is_cadential and plan.cadence_type:
        first_parts.append(plan.cadence_type)
    first_lyric: str = "/".join(first_parts)

    thematic_exact: frozenset[str] = frozenset({"subject", "answer", "stretto", "stretto-2", "episode"})

    if not plan.is_cadential and result.soprano_figures:
        bar_length, beat_unit = parse_metre(metre=plan.metre)
        structural_offsets: list[Fraction] = [
            phrase_degree_offset(
                plan=plan, pos=pos,
                bar_length=bar_length, beat_unit=beat_unit,
            )
            for pos in plan.degree_positions
        ]
        offset_to_figure: dict[Fraction, str] = {}
        for fig_idx, fig_name in enumerate(result.soprano_figures):
            offset_to_figure[structural_offsets[fig_idx]] = fig_name
        for j, sn in enumerate(notes):
            # Preserve existing thematic lyrics
            if sn.lyric and (sn.lyric in thematic_exact or sn.lyric.startswith("cs")):
                continue
            parts: list[str] = []
            if j == 0:
                parts.append(first_lyric)
            if sn.offset in offset_to_figure:
                parts.append(offset_to_figure[sn.offset])
            if parts:
                notes[j] = replace(sn, lyric="/".join(parts))
    else:
        # Only stamp first note if it doesn't have a thematic lyric
        if not (notes[0].lyric in thematic_exact or notes[0].lyric.startswith("cs")):
            notes[0] = replace(notes[0], lyric=first_lyric)

    return tuple(notes)


def _extract_head_motif(
    upper_notes: tuple[Note, ...],
    soprano_figures: tuple[str, ...],
    plan: PhrasePlan,
) -> HeadMotif | None:
    """Extract the head motif from the first non-cadential phrase's soprano.

    Captures the interval and duration sequence of the first figuration span
    (from the first structural tone to the second).
    """
    if not soprano_figures or not upper_notes:
        return None
    bar_length, beat_unit = parse_metre(metre=plan.metre)
    # Find the second structural tone offset
    if len(plan.degree_positions) < 2:
        return None
    first_struct: Fraction = phrase_degree_offset(
        plan=plan, pos=plan.degree_positions[0],
        bar_length=bar_length, beat_unit=beat_unit,
    )
    second_struct: Fraction = phrase_degree_offset(
        plan=plan, pos=plan.degree_positions[1],
        bar_length=bar_length, beat_unit=beat_unit,
    )
    # Collect notes in the first span [first_struct, second_struct)
    span_notes: list[Note] = [
        n for n in upper_notes
        if first_struct <= n.offset < second_struct
    ]
    if len(span_notes) < 2:
        return None
    intervals: list[int] = [
        span_notes[i + 1].pitch - span_notes[i].pitch
        for i in range(len(span_notes) - 1)
    ]
    durations: list[Fraction] = [n.duration for n in span_notes]
    return HeadMotif(
        interval_sequence=tuple(intervals),
        duration_sequence=tuple(durations),
        figure_name=soprano_figures[0],
    )


def _ensure_beat1_coverage(
    plan: PhrasePlan,
    result: PhraseResult,
    prior_upper: tuple[Note, ...],
    prior_lower: tuple[Note, ...],
) -> PhraseResult:
    """Ensure every bar in this phrase has at least one voice sounding on beat 1 (I8).

    If a bar has no note covering its downbeat in either voice, extend the
    latest-ending note before that downbeat (prefer bass) to cover beat 1.
    """
    bar_length, beat_unit = parse_metre(metre=plan.metre)
    upper_list: list[Note] = list(result.upper_notes)
    lower_list: list[Note] = list(result.lower_notes)
    changed: bool = False

    for bar_num in range(1, plan.bar_span + 1):
        bar_start: Fraction = phrase_bar_start(
            plan=plan, bar_num=bar_num, bar_length=bar_length,
        )
        # Check coverage across prior + current phrase notes (current may be mutated)
        covered: bool = any(
            n.offset <= bar_start < n.offset + n.duration
            for n in (*prior_upper, *upper_list, *prior_lower, *lower_list)
        )
        if covered:
            continue

        # Find latest-ending bass note before bar_start in current phrase
        bass_best_idx: int | None = None
        bass_best_end: Fraction = Fraction(-1)
        for i, n in enumerate(lower_list):
            end: Fraction = n.offset + n.duration
            if end <= bar_start and end > bass_best_end:
                bass_best_idx = i
                bass_best_end = end

        # Find latest-ending soprano note before bar_start in current phrase
        sop_best_idx: int | None = None
        sop_best_end: Fraction = Fraction(-1)
        for i, n in enumerate(upper_list):
            end: Fraction = n.offset + n.duration
            if end <= bar_start and end > sop_best_end:
                sop_best_idx = i
                sop_best_end = end

        # Prefer bass extension (grounding voice)
        if bass_best_idx is not None:
            note: Note = lower_list[bass_best_idx]
            new_duration: Fraction = bar_start + beat_unit - note.offset
            lower_list[bass_best_idx] = replace(note, duration=new_duration)
            changed = True
            logger.warning(
                "Beat-1 gap filled at bar %d by extending bass voice",
                plan.start_bar + bar_num - 1,
            )
        elif sop_best_idx is not None:
            note = upper_list[sop_best_idx]
            new_duration = bar_start + beat_unit - note.offset
            upper_list[sop_best_idx] = replace(note, duration=new_duration)
            changed = True
            logger.warning(
                "Beat-1 gap filled at bar %d by extending soprano voice",
                plan.start_bar + bar_num - 1,
            )

    if not changed:
        return result
    return replace(
        result,
        upper_notes=tuple(upper_list),
        lower_notes=tuple(lower_list),
    )


def _assert_no_polyphony(notes: tuple[Note, ...], voice_name: str) -> None:
    """Assert no two notes overlap in the same voice."""
    sorted_notes: list[Note] = sorted(notes, key=lambda n: (n.offset, -n.duration))
    for i in range(len(sorted_notes) - 1):
        a: Note = sorted_notes[i]
        b: Note = sorted_notes[i + 1]
        if a.offset + a.duration > b.offset:
            assert False, (
                f"Polyphony in {voice_name}: "
                f"{a.pitch}@{float(a.offset)} dur={float(a.duration)} "
                f"(creator={a.creator!r}) overlaps "
                f"{b.pitch}@{float(b.offset)} dur={float(b.duration)} "
                f"(creator={b.creator!r})"
            )


def compose_phrases(
    phrase_plans: tuple[PhrasePlan, ...],
    home_key: Key,
    metre: str,
    tempo: int,
    upbeat: Fraction,
    fugue: SubjectTriple | None = None,
) -> Composition:
    """Compose a piece phrase by phrase using the phrase writer."""
    assert len(phrase_plans) > 0, "Must have at least one PhrasePlan"
    upper_notes: list[Note] = []
    lower_notes: list[Note] = []
    upper_structural: set[Fraction] = set()
    lower_structural: set[Fraction] = set()
    head_motif: HeadMotif | None = None

    # Create episode kernel source if fugue is present
    episode_source: EpisodeDialogue | None = None
    if fugue is not None:
        episode_source = EpisodeDialogue(triple=fugue)

    # Compute and inject register targets for episode phrases (REG-1).
    if fugue is not None:
        from planner.register_plan import compute_register_targets
        _reg_targets = compute_register_targets(
            phrases=list(phrase_plans),
            upper_range=phrase_plans[0].upper_range,
            lower_range=phrase_plans[0].lower_range,
            fugue=fugue,
        )
        _plans_list: list[PhrasePlan] = list(phrase_plans)
        _tracer = get_tracer()
        for _idx, _target in _reg_targets.items():
            _plans_list[_idx] = replace(_plans_list[_idx], register_target=_target)
            _plan = _plans_list[_idx]
            _tracer.trace_L5r_register(
                phrase_index=_idx,
                start_bar=_plan.start_bar,
                end_bar=_plan.start_bar + _plan.bar_span - 1,
                key_str=_key_str(key=_plan.local_key),
                start_upper=_target.start_upper_midi,
                end_upper=_target.end_upper_midi,
                start_lower=_target.start_lower_midi,
                end_lower=_target.end_lower_midi,
            )
        phrase_plans = tuple(_plans_list)

    for plan_idx, plan in enumerate(phrase_plans):
        # Compute next phrase's first soprano degree/key for cross-phrase guard
        next_entry_degree: int | None = None
        next_entry_key: Key | None = None
        if plan_idx < len(phrase_plans) - 1:
            next_plan: PhrasePlan = phrase_plans[plan_idx + 1]
            if next_plan.is_cadential:
                next_entry_degree = cadence_entry_degree(
                    schema_name=next_plan.schema_name,
                    metre=next_plan.metre,
                    fugue=fugue,
                )
                next_entry_key = next_plan.local_key
            elif next_plan.degrees_upper and next_plan.degree_keys:
                # Guard for imitative phrases with empty degree arrays
                next_entry_degree = next_plan.degrees_upper[0]
                next_entry_key = next_plan.degree_keys[0]
        # B5: Flag pre-cadential phrases in minor keys for raised 7th
        if (plan_idx < len(phrase_plans) - 1
            and next_plan.is_cadential
            and plan.local_key.mode == "minor"
            and plan.thematic_roles is None):  # schematic only, not thematic
            plan = replace(plan, cadential_approach=True)
        # Determine recall figure name for motivic return
        recall_figure: str | None = None
        if plan.recall_motif and head_motif is not None:
            recall_figure = head_motif.figure_name
        is_last_phrase: bool = plan_idx == len(phrase_plans) - 1
        result: PhraseResult = write_phrase(
            plan=plan,
            prior_upper=tuple(upper_notes),
            prior_lower=tuple(lower_notes),
            next_phrase_entry_degree=next_entry_degree,
            next_phrase_entry_key=next_entry_key,
            recall_figure_name=recall_figure,
            fugue=fugue,
            is_final=is_last_phrase,
            episode_source=episode_source,
        )
        # I8: Ensure beat-1 coverage
        result = _ensure_beat1_coverage(
            plan=plan,
            result=result,
            prior_upper=tuple(upper_notes),
            prior_lower=tuple(lower_notes),
        )
        # Extract head motif after first non-cadential phrase
        if head_motif is None and not plan.is_cadential:
            head_motif = _extract_head_motif(
                upper_notes=result.upper_notes,
                soprano_figures=result.soprano_figures,
                plan=plan,
            )
        upper_notes.extend(_stamp_lyrics(plan=plan, result=result))
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
    get_tracer().trace_L6_header(
        total_upper=len(upper_notes),
        total_lower=len(lower_notes),
    )
    _assert_no_polyphony(notes=tuple(upper_notes), voice_name="soprano")
    _assert_no_polyphony(notes=tuple(lower_notes), voice_name="bass")
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
