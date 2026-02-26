"""FREE bar fill: companion voice and tail generation for thematic phrases.

Fills bars where one or both voices have no thematic material (FREE role).
"""
from fractions import Fraction

from builder.bass_viterbi import BassOptions, generate_bass_viterbi
from builder.knot_builder import enrich_companion_knots
from builder.galant.soprano_writer import build_structural_soprano
from builder.phrase_types import (
    PhrasePlan,
    make_free_companion_plan,
    make_tail_plan,
    phrase_bar_start,
    phrase_offset_to_bar,
)
from builder.soprano_viterbi import SopranoOptions, generate_soprano_viterbi
from builder.types import Note
from builder.voice_types import VoiceBias
from motifs.subject_loader import ThematicBias
from motifs.thematic_transform import (
    build_thematic_knots,
    diminish,
    invert,
    nearest_degree_for_midi,
    retrograde,
    sequence_cell_knots,
)
from planner.thematic import BeatRole, ThematicRole
from shared.key import Key
from viterbi.mtypes import Knot


def _companion_density(material_character: str) -> str:
    """Determine companion density (one level below leader)."""
    from builder.figuration.soprano import character_to_density

    material_density: str = character_to_density(character=material_character)

    if material_density == "high":
        return "medium"
    if material_density == "medium":
        return "low"
    # Low stays low (no reduction below low)
    return "low"


def fill_free_bars(
    plan: PhrasePlan,
    material_entries: list[dict],
    soprano_notes: tuple[Note, ...],
    bass_notes: tuple[Note, ...],
    prior_upper: tuple[Note, ...],
    prior_lower: tuple[Note, ...],
    next_phrase_entry_degree: int | None,
    next_phrase_entry_key: Key | None,
    bar_length: Fraction,
    bias: ThematicBias | None = None,
) -> tuple[tuple[Note, ...], tuple[Note, ...]]:
    """Fill FREE bars (companion alongside material + tail after material).

    Args:
        plan: PhrasePlan for the phrase
        material_entries: List of entry dicts with material
        soprano_notes: Accumulated soprano notes so far
        bass_notes: Accumulated bass notes so far
        prior_upper: Prior soprano notes from previous phrase
        prior_lower: Prior bass notes from previous phrase
        next_phrase_entry_degree: Degree of next phrase's first note (for tail)
        next_phrase_entry_key: Key of next phrase's first note (for tail)
        bar_length: Length of one bar

    Returns:
        Tuple of (soprano_notes, bass_notes) with FREE bars filled
    """
    phrase_first_bar: int = plan.thematic_roles[0].bar if plan.thematic_roles else plan.start_bar
    phrase_last_bar: int = plan.thematic_roles[-1].bar if plan.thematic_roles else plan.start_bar + plan.bar_span - 1

    # Build map of which bars have material in which voice
    voice_material_map: dict[int, dict[int, bool]] = {}  # bar → voice → has_material

    for entry in material_entries:
        entry_first_bar: int = entry["first_bar"]
        entry_bar_count: int = entry["bar_count"]
        voice0_role: ThematicRole = entry["voice0_role"]
        voice1_role: ThematicRole = entry["voice1_role"]

        for bar_offset in range(entry_bar_count):
            bar: int = entry_first_bar + bar_offset
            if bar not in voice_material_map:
                voice_material_map[bar] = {0: False, 1: False}
            # Mark voice as having material if role is not FREE
            # For hold_exchange entries, mark BOTH voices as having material
            if voice0_role == ThematicRole.HOLD or voice1_role == ThematicRole.HOLD:
                voice_material_map[bar][0] = True
                voice_material_map[bar][1] = True
            else:
                if voice0_role != ThematicRole.FREE:
                    voice_material_map[bar][0] = True
                if voice1_role != ThematicRole.FREE:
                    voice_material_map[bar][1] = True

    # Mark silent voices as occupied (solo exposition entries)
    silent_bars: set[tuple[int, int]] = set()  # (bar, voice) pairs marked silent
    if plan.thematic_roles:
        for role in plan.thematic_roles:
            if role.texture == "silent" and role.beat == Fraction(0):
                if role.bar not in voice_material_map:
                    voice_material_map[role.bar] = {0: False, 1: False}
                voice_material_map[role.bar][role.voice] = True
                silent_bars.add((role.bar, role.voice))

    # Reconcile: downgrade "has material" to False where no notes exist.
    # Stretto/subject entries may span more bars in the role map than the
    # rendered notes actually cover (e.g. a 2-bar subject in a 3-bar stretto
    # window leaves bar 3 empty despite the role claiming SUBJECT).
    # Skip bars marked silent — they have no notes by design.
    soprano_bars_covered: set[int] = set()
    bass_bars_covered: set[int] = set()
    phrase_start: Fraction = plan.start_offset
    for n in soprano_notes:
        if n.offset >= phrase_start:
            covered_bar: int = phrase_first_bar + int((n.offset - phrase_start) / bar_length)
            soprano_bars_covered.add(covered_bar)
    for n in bass_notes:
        if n.offset >= phrase_start:
            covered_bar = phrase_first_bar + int((n.offset - phrase_start) / bar_length)
            bass_bars_covered.add(covered_bar)
    for bar_num in list(voice_material_map.keys()):
        if voice_material_map[bar_num][0] and bar_num not in soprano_bars_covered:
            if (bar_num, 0) not in silent_bars:
                voice_material_map[bar_num][0] = False
        if voice_material_map[bar_num][1] and bar_num not in bass_bars_covered:
            if (bar_num, 1) not in silent_bars:
                voice_material_map[bar_num][1] = False

    # Identify FREE bar runs (consecutive bars where exactly one voice is FREE)
    free_runs: list[tuple[int, int, int]] = []
    current_run_voice: int | None = None
    current_run_start: int | None = None
    current_run_count: int = 0

    for bar in range(phrase_first_bar, phrase_last_bar + 1):
        if bar not in voice_material_map:
            # Close current run
            if current_run_start is not None:
                assert current_run_voice is not None
                free_runs.append((current_run_start, current_run_count, current_run_voice))
                current_run_start = None
                current_run_voice = None
                current_run_count = 0
            continue

        # Check which voice is FREE and which has material
        soprano_free: bool = not voice_material_map[bar][0]
        bass_free: bool = not voice_material_map[bar][1]
        soprano_has_material: bool = voice_material_map[bar][0]
        bass_has_material: bool = voice_material_map[bar][1]

        # Only handle bars where exactly one voice is FREE
        if soprano_free and bass_has_material:
            free_voice: int = 0  # soprano
        elif bass_free and soprano_has_material:
            free_voice = 1  # bass
        else:
            # Both FREE or both have material — close current run
            if current_run_start is not None:
                assert current_run_voice is not None
                free_runs.append((current_run_start, current_run_count, current_run_voice))
                current_run_start = None
                current_run_voice = None
                current_run_count = 0
            continue

        # Extend or start run
        if current_run_voice == free_voice and current_run_start is not None:
            # Extend current run
            current_run_count += 1
        else:
            # Close previous run and start new one
            if current_run_start is not None:
                assert current_run_voice is not None
                free_runs.append((current_run_start, current_run_count, current_run_voice))
            current_run_start = bar
            current_run_voice = free_voice
            current_run_count = 1

    # Close final run
    if current_run_start is not None:
        assert current_run_voice is not None
        free_runs.append((current_run_start, current_run_count, current_run_voice))

    # Generate Viterbi fill for each FREE bar run with companion density
    run_counter: int = 0
    for first_bar, bar_count, free_voice_idx in free_runs:
        bars_from_phrase_start: int = first_bar - phrase_first_bar
        run_start_offset: Fraction = plan.start_offset + bars_from_phrase_start * bar_length
        start_bar_relative: int = first_bar - phrase_first_bar + 1

        # Build plan for this FREE bar run (B1: use make_free_companion_plan)
        run_plan: PhrasePlan = make_free_companion_plan(
            plan=plan,
            start_bar_relative=start_bar_relative,
            bar_count=bar_count,
            start_offset=run_start_offset,
            prev_exit_upper=soprano_notes[-1].pitch if soprano_notes else plan.prev_exit_upper,
            prev_exit_lower=bass_notes[-1].pitch if bass_notes else plan.prev_exit_lower,
        )

        # Determine companion density (one level below character)
        companion_density_level: str = _companion_density(material_character=plan.character)

        if free_voice_idx == 0:
            # Soprano is FREE, bass has material

            # Build thematic knots for companion soprano (CS-derived pattern)
            companion_sop_knots: list[Knot] | None = None
            prev_sop_midi: int = (
                (soprano_notes[-1].pitch if soprano_notes else run_plan.prev_exit_upper)
                or run_plan.upper_median
            )
            if bias is not None and bias.cell_catalogue is not None and bias.cell_catalogue.all_cells:
                candidate_sop_knots: list[Knot] = sequence_cell_knots(
                    catalogue=bias.cell_catalogue,
                    span_duration=run_plan.phrase_duration,
                    prefer_family="cs",
                    start_midi=prev_sop_midi,
                    key=plan.local_key,
                    start_offset=run_start_offset,
                    range_low=run_plan.upper_range.low,
                    range_high=run_plan.upper_range.high,
                    max_offset=run_start_offset + run_plan.phrase_duration,
                    seed=run_counter,
                )
                if candidate_sop_knots:
                    companion_sop_knots = candidate_sop_knots
            elif bias is not None:
                # Fallback: whole-pattern approach (TB-3b)
                cs_pattern = bias.cs_pattern
                transform_choice: int = run_counter % 3
                if transform_choice == 0:
                    transformed_sop = invert(cs_pattern)
                elif transform_choice == 1:
                    transformed_sop = cs_pattern  # identity (transpose via start_degree)
                else:
                    transformed_sop = retrograde(cs_pattern)
                sop_start_degree: int
                sop_start_octave: int
                sop_start_degree, sop_start_octave = nearest_degree_for_midi(
                    target_midi=prev_sop_midi, key=plan.local_key,
                )
                fallback_sop_knots: list[Knot] = build_thematic_knots(
                    pattern=transformed_sop,
                    start_degree=sop_start_degree,
                    key=plan.local_key,
                    octave=sop_start_octave,
                    start_offset=run_start_offset,
                    range_low=run_plan.upper_range.low,
                    range_high=run_plan.upper_range.high,
                    max_offset=run_start_offset + run_plan.phrase_duration,
                )
                if fallback_sop_knots:
                    companion_sop_knots = fallback_sop_knots

            # USI-1: Supplement sparse thematic knots with consonant strong-beat pitches.
            companion_sop_knots = enrich_companion_knots(
                existing_knots=companion_sop_knots,
                material_notes=bass_notes,
                run_start_offset=run_start_offset,
                run_end_offset=run_start_offset + run_plan.phrase_duration,
                bar_length=bar_length,
                companion_range_low=run_plan.upper_range.low,
                companion_range_high=run_plan.upper_range.high,
                companion_is_above=True,
                seed_pitch=soprano_notes[-1].pitch if soprano_notes else None,
            )

            structural_free: tuple[Note, ...] = build_structural_soprano(
                plan=run_plan,
                prev_exit_midi=soprano_notes[-1].pitch if soprano_notes else plan.prev_exit_upper,
            )
            # I5: Compute bar-relative bass onsets for rhythmic independence
            bass_onsets_by_bar: dict[int, set[Fraction]] = {}
            run_end: Fraction = run_plan.start_offset + run_plan.phrase_duration
            for bn in bass_notes:
                if run_plan.start_offset <= bn.offset < run_end:
                    bar_num_b: int = phrase_offset_to_bar(
                        plan=run_plan, offset=bn.offset, bar_length=bar_length,
                    )
                    bar_s: Fraction = phrase_bar_start(
                        plan=run_plan, bar_num=bar_num_b, bar_length=bar_length,
                    )
                    bass_onsets_by_bar.setdefault(bar_num_b, set()).add(bn.offset - bar_s)
            avoid_onsets: dict[int, frozenset[Fraction]] = {
                k: frozenset(v) for k, v in bass_onsets_by_bar.items()
            }

            sop_bias: VoiceBias = VoiceBias(
                degree_affinity=bias.degree_affinity if bias else None,
                interval_affinity=bias.cs_interval_affinity if bias else None,
                structural_knots=companion_sop_knots,
                vertical_genome=bias.vertical_genome if bias else None,
            )
            free_soprano: tuple[Note, ...]
            free_soprano, _ = generate_soprano_viterbi(
                plan=run_plan,
                bass_notes=bass_notes,
                prior_upper=soprano_notes,
                next_phrase_entry_degree=None,
                next_phrase_entry_key=None,
                options=SopranoOptions(
                    density_override=companion_density_level,
                    avoid_onsets_by_bar=avoid_onsets,
                    bias=sop_bias,
                ),
            )
            soprano_notes = soprano_notes + free_soprano
        else:
            # Bass is FREE, soprano has material

            # Build thematic knots for companion bass (subject-derived pattern)
            companion_bass_knots: list[Knot] | None = None
            prev_bass_midi: int = (
                (bass_notes[-1].pitch if bass_notes else run_plan.prev_exit_lower)
                or run_plan.lower_median
            )
            if bias is not None and bias.cell_catalogue is not None and bias.cell_catalogue.all_cells:
                candidate_bass_knots: list[Knot] = sequence_cell_knots(
                    catalogue=bias.cell_catalogue,
                    span_duration=run_plan.phrase_duration,
                    prefer_family="subject",
                    start_midi=prev_bass_midi,
                    key=plan.local_key,
                    start_offset=run_start_offset,
                    range_low=run_plan.lower_range.low,
                    range_high=run_plan.lower_range.high,
                    max_offset=run_start_offset + run_plan.phrase_duration,
                    seed=run_counter,
                )
                if candidate_bass_knots:
                    companion_bass_knots = candidate_bass_knots
            elif bias is not None:
                # Fallback: whole-pattern approach (TB-3b)
                subj_pattern = bias.subject_pattern
                bass_transform_choice: int = run_counter % 2
                if bass_transform_choice == 0:
                    transformed_bass = subj_pattern  # identity
                else:
                    transformed_bass = invert(subj_pattern)
                bass_start_degree: int
                bass_start_octave: int
                bass_start_degree, bass_start_octave = nearest_degree_for_midi(
                    target_midi=prev_bass_midi, key=plan.local_key,
                )
                fallback_bass_knots: list[Knot] = build_thematic_knots(
                    pattern=transformed_bass,
                    start_degree=bass_start_degree,
                    key=plan.local_key,
                    octave=bass_start_octave,
                    start_offset=run_start_offset,
                    range_low=run_plan.lower_range.low,
                    range_high=run_plan.lower_range.high,
                    max_offset=run_start_offset + run_plan.phrase_duration,
                )
                if fallback_bass_knots:
                    companion_bass_knots = fallback_bass_knots

            # USI-1: Supplement sparse thematic knots with consonant strong-beat pitches.
            companion_bass_knots = enrich_companion_knots(
                existing_knots=companion_bass_knots,
                material_notes=soprano_notes,
                run_start_offset=run_start_offset,
                run_end_offset=run_start_offset + run_plan.phrase_duration,
                bar_length=bar_length,
                companion_range_low=run_plan.lower_range.low,
                companion_range_high=run_plan.lower_range.high,
                companion_is_above=False,
                seed_pitch=bass_notes[-1].pitch if bass_notes else None,
            )

            bass_bias: VoiceBias = VoiceBias(
                degree_affinity=bias.degree_affinity if bias else None,
                interval_affinity=bias.subject_interval_affinity if bias else None,
                structural_knots=companion_bass_knots,
                vertical_genome=bias.vertical_genome if bias else None,
            )
            free_bass: tuple[Note, ...] = generate_bass_viterbi(
                plan=run_plan,
                soprano_notes=soprano_notes,
                prior_lower=bass_notes,
                options=BassOptions(density_override=companion_density_level, bias=bass_bias),
            )
            bass_notes = bass_notes + free_bass

        run_counter += 1

    # Handle FREE tail bars after last material entry (both voices FREE)
    if material_entries:
        last_material_bar: int = material_entries[-1]["first_bar"] + material_entries[-1]["bar_count"] - 1

        if last_material_bar < phrase_last_bar:
            # There are tail bars: generate Viterbi fill (galant order)
            tail_start_bar_absolute: int = last_material_bar + 1
            tail_start_bar: int = tail_start_bar_absolute - phrase_first_bar + 1
            bars_from_phrase_start: int = tail_start_bar_absolute - phrase_first_bar
            tail_start_offset: Fraction = plan.start_offset + bars_from_phrase_start * bar_length

            # Build tail plan
            tail_plan: PhrasePlan = make_tail_plan(
                plan=plan,
                tail_start_bar=tail_start_bar,
                tail_start_offset=tail_start_offset,
                prev_exit_upper=soprano_notes[-1].pitch if soprano_notes else plan.prev_exit_upper,
                prev_exit_lower=bass_notes[-1].pitch if bass_notes else plan.prev_exit_lower,
            )

            # Galant order: structural soprano → bass Viterbi → soprano Viterbi

            # Build thematic knots for tail bass (subject identity) and soprano (diminished)
            tail_bass_knots: list[Knot] | None = None
            tail_sop_knots: list[Knot] | None = None
            prev_tail_bass_midi: int = (
                (bass_notes[-1].pitch if bass_notes else tail_plan.prev_exit_lower)
                or tail_plan.lower_median
            )
            prev_tail_sop_midi: int = (
                (soprano_notes[-1].pitch if soprano_notes else tail_plan.prev_exit_upper)
                or tail_plan.upper_median
            )
            if bias is not None and bias.cell_catalogue is not None and bias.cell_catalogue.all_cells:
                # Tail bass: subject cells (seed=100)
                candidate_tail_bass_knots: list[Knot] = sequence_cell_knots(
                    catalogue=bias.cell_catalogue,
                    span_duration=tail_plan.phrase_duration,
                    prefer_family="subject",
                    start_midi=prev_tail_bass_midi,
                    key=plan.local_key,
                    start_offset=tail_start_offset,
                    range_low=tail_plan.lower_range.low,
                    range_high=tail_plan.lower_range.high,
                    max_offset=tail_start_offset + tail_plan.phrase_duration,
                    seed=100,
                )
                if candidate_tail_bass_knots:
                    tail_bass_knots = candidate_tail_bass_knots

                # Tail soprano: CS cells (seed=200)
                candidate_tail_sop_knots: list[Knot] = sequence_cell_knots(
                    catalogue=bias.cell_catalogue,
                    span_duration=tail_plan.phrase_duration,
                    prefer_family="cs",
                    start_midi=prev_tail_sop_midi,
                    key=plan.local_key,
                    start_offset=tail_start_offset,
                    range_low=tail_plan.upper_range.low,
                    range_high=tail_plan.upper_range.high,
                    max_offset=tail_start_offset + tail_plan.phrase_duration,
                    seed=200,
                )
                if candidate_tail_sop_knots:
                    tail_sop_knots = candidate_tail_sop_knots
            elif bias is not None:
                # Fallback: whole-pattern approach (TB-3b)
                subj_pattern_tail = bias.subject_pattern

                # Tail bass: subject identity
                tb_start_degree: int
                tb_start_octave: int
                tb_start_degree, tb_start_octave = nearest_degree_for_midi(
                    target_midi=prev_tail_bass_midi, key=plan.local_key,
                )
                fallback_tail_bass_knots: list[Knot] = build_thematic_knots(
                    pattern=subj_pattern_tail,
                    start_degree=tb_start_degree,
                    key=plan.local_key,
                    octave=tb_start_octave,
                    start_offset=tail_start_offset,
                    range_low=tail_plan.lower_range.low,
                    range_high=tail_plan.lower_range.high,
                    max_offset=tail_start_offset + tail_plan.phrase_duration,
                )
                if fallback_tail_bass_knots:
                    tail_bass_knots = fallback_tail_bass_knots

                # Tail soprano: diminished subject
                diminished_subj = diminish(subj_pattern_tail)
                ts_start_degree: int
                ts_start_octave: int
                ts_start_degree, ts_start_octave = nearest_degree_for_midi(
                    target_midi=prev_tail_sop_midi, key=plan.local_key,
                )
                fallback_tail_sop_knots: list[Knot] = build_thematic_knots(
                    pattern=diminished_subj,
                    start_degree=ts_start_degree,
                    key=plan.local_key,
                    octave=ts_start_octave,
                    start_offset=tail_start_offset,
                    range_low=tail_plan.upper_range.low,
                    range_high=tail_plan.upper_range.high,
                    max_offset=tail_start_offset + tail_plan.phrase_duration,
                )
                if fallback_tail_sop_knots:
                    tail_sop_knots = fallback_tail_sop_knots

            structural_tail: tuple[Note, ...] = build_structural_soprano(
                plan=tail_plan,
                prev_exit_midi=soprano_notes[-1].pitch if soprano_notes else plan.prev_exit_upper,
            )

            tail_bass_bias: VoiceBias = VoiceBias(
                degree_affinity=bias.degree_affinity if bias else None,
                interval_affinity=bias.subject_interval_affinity if bias else None,
                structural_knots=tail_bass_knots,
                vertical_genome=bias.vertical_genome if bias else None,
            )
            tail_bass: tuple[Note, ...] = generate_bass_viterbi(
                plan=tail_plan,
                soprano_notes=prior_upper + soprano_notes + structural_tail,
                prior_lower=bass_notes,
                options=BassOptions(bias=tail_bass_bias),
            )
            bass_notes = bass_notes + tail_bass

            tail_sop_bias: VoiceBias = VoiceBias(
                degree_affinity=bias.degree_affinity if bias else None,
                interval_affinity=bias.cs_interval_affinity if bias else None,
                structural_knots=tail_sop_knots,
                vertical_genome=bias.vertical_genome if bias else None,
            )
            tail_soprano: tuple[Note, ...]
            tail_soprano, _ = generate_soprano_viterbi(
                plan=tail_plan,
                bass_notes=bass_notes,
                prior_upper=soprano_notes,
                next_phrase_entry_degree=next_phrase_entry_degree,
                next_phrase_entry_key=next_phrase_entry_key,
                options=SopranoOptions(bias=tail_sop_bias),
            )
            soprano_notes = soprano_notes + tail_soprano

    return (soprano_notes, bass_notes)
