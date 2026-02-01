"""Main figuration entry points for baroque melodic patterns."""
import random
from fractions import Fraction
from typing import Sequence

from builder.figuration.bar_context import (
    compute_bar_function,
    compute_beat_class,
    compute_effective_gap,
    compute_harmonic_tension,
    compute_next_anchor_strength,
    get_accompany_texture_for_bar,
    get_schema_cadence_approach,
    get_schema_texture,
    reduce_density,
    should_generate_anacrusis,
    should_use_hemiola,
    should_use_overdotted,
)
from builder.figuration.cadential import select_cadential_figure
from builder.figuration.junction import check_junction, find_valid_figure
from builder.figuration.phrase import (
    detect_schema_sections,
    determine_position_with_deformation,
    in_schema_section,
    select_phrase_deformation,
)
from builder.figuration.realiser import realise_figure_to_bar
from builder.figuration.selection import apply_misbehaviour, select_figure, sort_by_weight
from builder.figuration.selector import (
    compute_interval,
    determine_phrase_position,
    filter_by_character,
    filter_by_compensation,
    filter_by_density,
    filter_by_direction,
    filter_by_max_leap,
    filter_by_minor_safety,
    filter_by_note_count,
    filter_by_tension,
    filter_cadential_safe,
    filter_cross_relation,
    filter_parallel_direct,
    get_figures_for_interval,
)
from builder.figuration.rhythm_calc import compute_rhythmic_distribution
from builder.figuration.strategies import (
    apply_strategy,
    get_profile_for_schema,
    get_strategy_for_schema,
)
from builder.figuration.types import (
    Figure,
    FiguredBar,
    PhrasePosition,
)
from builder.types import Anchor, PassageAssignment, Role
from shared.constants import RHYTHMIC_CONTRAST_THRESHOLD


def _would_create_parallel_or_direct_realized(
    soprano_degrees: tuple[int, ...],
    bass_degrees: tuple[int, ...],
    soprano_start: int,
    bass_start: int,
) -> bool:
    """Check realized degree sequences for parallel/direct fifths/octaves.

    Uses scale degrees directly (not MIDI) since both voices share key.
    Interval in degrees mod 7: 0 = unison/octave, 4 = fifth.
    """
    PERFECT_DEGREE_INTERVALS = {0, 4}
    min_len = min(len(soprano_degrees), len(bass_degrees))
    if min_len < 2:
        return False
    for i in range(min_len - 1):
        s1 = soprano_start + soprano_degrees[i] if i < len(soprano_degrees) else soprano_start
        s2 = soprano_start + soprano_degrees[i + 1] if i + 1 < len(soprano_degrees) else soprano_start
        b1 = bass_start + bass_degrees[i] if i < len(bass_degrees) else bass_start
        b2 = bass_start + bass_degrees[i + 1] if i + 1 < len(bass_degrees) else bass_start
        interval1 = abs(s1 - b1) % 7
        interval2 = abs(s2 - b2) % 7
        s_delta = s2 - s1
        b_delta = b2 - b1
        if s_delta == 0 or b_delta == 0:
            continue
        if (s_delta > 0) != (b_delta > 0):
            continue
        if interval1 in PERFECT_DEGREE_INTERVALS and interval1 == interval2:
            return True
        if interval2 in PERFECT_DEGREE_INTERVALS and abs(s_delta) > 2:
            return True
    return False


def _check_pillar_creates_direct_motion(
    prev_soprano_bar: "FiguredBar | None",
    curr_soprano_bar: "FiguredBar | None",
    prev_bass_degree: int | None,
    curr_bass_degree: int,
) -> bool:
    """Check if bass pillar would create direct fifth/octave with soprano.

    Direct motion: both voices move same direction, arrive at perfect interval,
    and soprano leaps (> 2 degree steps).
    """
    if prev_soprano_bar is None or curr_soprano_bar is None:
        return False
    if prev_bass_degree is None:
        return False
    prev_soprano = prev_soprano_bar.degrees[-1] if prev_soprano_bar.degrees else None
    curr_soprano = curr_soprano_bar.degrees[0] if curr_soprano_bar.degrees else None
    if prev_soprano is None or curr_soprano is None:
        return False
    soprano_motion = curr_soprano - prev_soprano
    bass_motion = curr_bass_degree - prev_bass_degree
    if soprano_motion == 0 or bass_motion == 0:
        return False
    if (soprano_motion > 0) != (bass_motion > 0):
        return False
    interval = abs(curr_soprano - curr_bass_degree) % 7
    PERFECT_DEGREE_INTERVALS = {0, 4}
    if interval not in PERFECT_DEGREE_INTERVALS:
        return False
    if abs(soprano_motion) > 2:
        return True
    return False


def _check_pillar_creates_unprepared_dissonance(
    curr_soprano_bar: "FiguredBar | None",
    curr_bass_degree: int,
) -> bool:
    """Check if bass pillar would create unprepared dissonance with soprano.

    Dissonant intervals (mod 7): 1 (second), 6 (seventh).
    On strong beat (pillar entry), these require preparation.
    """
    if curr_soprano_bar is None:
        return False
    curr_soprano = curr_soprano_bar.degrees[0] if curr_soprano_bar.degrees else None
    if curr_soprano is None:
        return False
    interval = abs(curr_soprano - curr_bass_degree) % 7
    DISSONANT_INTERVALS = {1, 6}
    return interval in DISSONANT_INTERVALS


def _get_direction(anchor: Anchor, role: Role) -> str | None:
    """Get the direction to reach this anchor based on voice role."""
    if role == Role.SCHEMA_LOWER:
        return anchor.lower_direction
    return anchor.upper_direction


def _direction_to_ascending(direction: str | None, degree_a: int, degree_b: int) -> bool:
    """Convert direction to ascending boolean."""
    if direction == "up":
        return True
    if direction == "down":
        return False
    return degree_b > degree_a


def _get_degree(anchor: Anchor, role: Role) -> int:
    """Get the appropriate degree from anchor based on voice role."""
    if role == Role.SCHEMA_LOWER:
        return anchor.lower_degree
    return anchor.upper_degree


def _role_from_voice_string(voice: str) -> Role:
    """Convert legacy voice string to Role enum."""
    if voice == "bass":
        return Role.SCHEMA_LOWER
    return Role.SCHEMA_UPPER


def figurate(
    anchors: Sequence[Anchor],
    key: "Key",
    metre: str,
    seed: int,
    density: str = "medium",
    affect_character: str = "plain",
    voice: str = "soprano",
    soprano_figured_bars: list[FiguredBar] | None = None,
    passage_assignments: Sequence[PassageAssignment] | None = None,
) -> list[FiguredBar]:
    """Main entry point: Convert anchors to figured bars."""
    if len(anchors) < 2:
        return []
    rng = random.Random(seed)
    sorted_anchors = sorted(anchors, key=lambda a: _parse_bar_beat(a.bar_beat))
    is_minor = key.mode == "minor"
    total_bars = _count_bars(sorted_anchors)
    phrase_deformation = select_phrase_deformation(rng, total_bars)
    schema_sections = detect_schema_sections(sorted_anchors)
    compound_melody_active = False
    figured_bars: list[FiguredBar] = []
    prev_leaped = False
    leap_direction: str | None = None
    prev_figure_name: str | None = None
    role: Role = _role_from_voice_string(voice)
    i = 0
    while i < len(sorted_anchors) - 1:
        anchor_a = sorted_anchors[i]
        anchor_b = sorted_anchors[i + 1]
        bar_num = _parse_bar_beat(anchor_a.bar_beat)[0]
        seq_info = in_schema_section(i, schema_sections)
        if seq_info is not None:
            seq_start, seq_end = seq_info
            seq_anchors = sorted_anchors[seq_start:seq_end]
            soprano_slice: list[FiguredBar] | None = None
            if voice == "bass" and soprano_figured_bars is not None:
                soprano_slice = soprano_figured_bars[seq_start:seq_end - 1]
            seq_bars = _apply_schema_figuration(
                anchors=seq_anchors,
                metre=metre,
                seed=seed + i,
                density=density,
                is_minor=is_minor,
                role=role,
                total_bars=total_bars,
                voice=voice,
                passage_assignments=passage_assignments,
                soprano_figured_bars=soprano_slice,
            )
            figured_bars.extend(seq_bars)
            i = seq_end - 1
            if seq_bars:
                prev_leaped = _is_leap_from_figured_bar(seq_bars[-1])
                prev_figure_name = seq_bars[-1].figure_name
            continue
        interval = compute_interval(_get_degree(anchor_a, role), _get_degree(anchor_b, role))
        direction = _get_direction(anchor_b, role)
        ascending = _direction_to_ascending(
            direction, _get_degree(anchor_a, role), _get_degree(anchor_b, role),
        )
        phrase_pos = determine_position_with_deformation(
            bar_num, total_bars, anchor_a.schema, phrase_deformation,
        )
        harmonic_tension = compute_harmonic_tension(anchor_a, phrase_pos, role)
        bar_function = compute_bar_function(phrase_pos, bar_num, total_bars, anchor_b)
        use_hemiola = should_use_hemiola(bar_num, total_bars, metre, phrase_deformation)
        next_anchor_strength = compute_next_anchor_strength(i, sorted_anchors, total_bars)
        if phrase_pos.position == "cadence":
            figure = select_cadential_figure(
                _get_degree(anchor_b, role), interval, is_minor, seed + i, rng,
            )
        else:
            figure = None
        if figure is None:
            soprano_degrees: tuple[int, ...] | None = None
            soprano_start_midi: int = 70
            bass_start_midi: int = 48
            if voice == "bass" and soprano_figured_bars is not None and i < len(soprano_figured_bars):
                sop_abs = soprano_figured_bars[i].degrees
                sop_start = sop_abs[0]
                soprano_degrees = tuple(d - sop_start for d in sop_abs)
                assert anchor_a.upper_midi is not None, f"Anchor at {anchor_a.bar_beat} missing upper_midi"
                assert anchor_a.lower_midi is not None, f"Anchor at {anchor_a.bar_beat} missing lower_midi"
                soprano_start_midi = anchor_a.upper_midi
                bass_start_midi = anchor_a.lower_midi
            start_beat_for_filter = compute_beat_class(voice, bar_num, passage_assignments)
            filter_density = reduce_density(density) if start_beat_for_filter == 2 else density
            figure = _select_figure_with_filters(
                interval=interval,
                ascending=ascending,
                harmonic_tension=harmonic_tension,
                character=affect_character if phrase_pos.position == "opening" else phrase_pos.character,
                density=filter_density,
                is_minor=is_minor,
                prev_leaped=prev_leaped,
                leap_direction=leap_direction,
                near_cadence=phrase_pos.position == "cadence",
                seed=seed + i,
                avoid_figure=prev_figure_name,
                soprano_degrees=soprano_degrees,
                soprano_start_midi=soprano_start_midi,
                bass_start_midi=bass_start_midi,
            )
        if figure is None:
            figure = _create_direct_figure(interval, _get_degree(anchor_a, role), _get_degree(anchor_b, role))
        if bar_num == 1 and figure.is_compound:
            compound_melody_active = True
        elif bar_num == 1:
            compound_melody_active = False
        if compound_melody_active and not figure.is_compound and phrase_pos.position != "cadence":
            compound_fig = _try_select_compound_figure(
                interval, ascending, harmonic_tension, density, is_minor, seed + i,
            )
            if compound_fig is not None:
                figure = compound_fig
        if i + 2 < len(sorted_anchors):
            next_anchor = sorted_anchors[i + 2]
            start_degree = _get_degree(anchor_a, role)
            if not check_junction(figure, start_degree, _get_degree(next_anchor, role)):
                candidates = get_figures_for_interval(interval)
                alt_figure = find_valid_figure(candidates, start_degree, _get_degree(next_anchor, role))
                if alt_figure:
                    figure = alt_figure
        offset_a = _bar_beat_to_offset(anchor_a.bar_beat, metre)
        offset_b = _bar_beat_to_offset(anchor_b.bar_beat, metre)
        raw_gap = offset_b - offset_a
        start_beat = compute_beat_class(voice, bar_num, passage_assignments)
        effective_gap = compute_effective_gap(raw_gap, start_beat, metre)
        effective_density = reduce_density(density) if start_beat == 2 else density
        if start_beat == 2:
            schema_texture = get_schema_texture(anchor_a.schema)
            texture = get_accompany_texture_for_bar(bar_num, passage_assignments, schema_texture)
            if texture == "pillar":
                bass_degree = _get_degree(anchor_a, role)
                prev_bass_degree = figured_bars[-1].degrees[-1] if figured_bars else None
                prev_soprano = soprano_figured_bars[i - 1] if soprano_figured_bars and i > 0 else None
                curr_soprano = soprano_figured_bars[i] if soprano_figured_bars and i < len(soprano_figured_bars) else None
                if _check_pillar_creates_direct_motion(prev_soprano, curr_soprano, prev_bass_degree, bass_degree):
                    texture = "staggered"
            if texture == "pillar":
                figured_bar = _create_pillar_bar(
                    bar_num=bar_num,
                    start_degree=_get_degree(anchor_a, role),
                    gap_duration=effective_gap,
                )
                figured_bars.append(figured_bar)
                prev_leaped = False
                prev_figure_name = "pillar"
                i += 1
                continue
            elif texture == "staggered":
                figured_bar = _create_staggered_bar(
                    figure=figure,
                    bar_num=bar_num,
                    start_degree=_get_degree(anchor_a, role),
                    gap_duration=raw_gap,
                    metre=metre,
                    density=effective_density,
                )
                figured_bars.append(figured_bar)
                prev_leaped = _is_leap(figure)
                leap_direction = "up" if ascending else "down"
                prev_figure_name = figure.name
                i += 1
                continue
            start_beat = 1
            effective_gap = raw_gap
        figured_bar = realise_figure_to_bar(
            figure=figure,
            bar=bar_num,
            start_degree=_get_degree(anchor_a, role),
            gap_duration=effective_gap,
            metre=metre,
            bar_function=bar_function,
            rhythmic_unit=_get_rhythmic_unit(metre),
            next_anchor_strength=next_anchor_strength,
            use_hemiola=use_hemiola,
            overdotted=should_use_overdotted(affect_character, phrase_pos),
            start_beat=start_beat,
            density=effective_density,
            use_baroque_rhythm=True,
        )
        figured_bars.append(figured_bar)
        prev_leaped = _is_leap(figure)
        leap_direction = "up" if ascending else "down"
        prev_figure_name = figure.name
        i += 1
    if voice == "soprano" and sorted_anchors:
        first_bar = _parse_bar_beat(sorted_anchors[0].bar_beat)[0]
        if should_generate_anacrusis(first_bar, voice, passage_assignments):
            anacrusis_bar = _generate_soprano_anacrusis(
                target_degree=_get_degree(sorted_anchors[0], role),
                seed=seed,
            )
            figured_bars.insert(0, anacrusis_bar)
    return figured_bars


def _generate_soprano_anacrusis(
    target_degree: int,
    seed: int,
) -> FiguredBar:
    """Generate a 4-note anacrusis leading to target degree."""
    rng = random.Random(seed)
    if rng.random() < 0.6:
        degrees = [target_degree - 3, target_degree - 2, target_degree - 1, target_degree]
    else:
        degrees = [target_degree + 3, target_degree + 2, target_degree + 1, target_degree]
    normalized: list[int] = []
    for d in degrees:
        while d < 1:
            d += 7
        while d > 7:
            d -= 7
        normalized.append(d)
    return FiguredBar(
        bar=0,
        degrees=tuple(normalized),
        durations=(Fraction(1, 16), Fraction(1, 16), Fraction(1, 16), Fraction(1, 16)),
        figure_name="anacrusis_run",
        start_beat=1,
    )


def _create_pillar_bar(
    bar_num: int,
    start_degree: int,
    gap_duration: Fraction,
) -> FiguredBar:
    """Create a pillar (sustained) bar with single note."""
    return FiguredBar(
        bar=bar_num,
        degrees=(start_degree,),
        durations=(gap_duration,),
        figure_name="pillar",
        start_beat=1,
    )


def _create_staggered_bar(
    figure: Figure,
    bar_num: int,
    start_degree: int,
    gap_duration: Fraction,
    metre: str,
    density: str,
) -> FiguredBar:
    """Create a staggered bar: rest for 1 beat, then fill remainder."""
    parts = metre.split("/")
    beat_value = Fraction(1, int(parts[1]))
    stagger_amount = beat_value
    remaining_gap = gap_duration - stagger_amount
    if remaining_gap <= 0:
        remaining_gap = beat_value
    note_count, _ = compute_rhythmic_distribution(remaining_gap, density)
    if note_count < 1:
        note_count = 1
    note_duration = remaining_gap / note_count
    base_degrees = figure.degrees
    result_degrees: list[int] = []
    for i in range(note_count):
        if i < len(base_degrees):
            result_degrees.append(start_degree + base_degrees[i])
        else:
            result_degrees.append(result_degrees[-1] if result_degrees else start_degree)
    return FiguredBar(
        bar=bar_num,
        degrees=tuple(result_degrees),
        durations=tuple([note_duration] * note_count),
        figure_name=f"staggered_{figure.name}",
        start_beat=2,
    )


def figurate_single_bar(
    anchor_a: Anchor,
    anchor_b: Anchor,
    key: "Key",
    metre: str,
    seed: int,
    bar_num: int,
    total_bars: int,
    density: str = "medium",
    character: str = "plain",
    prev_leaped: bool = False,
    leap_direction: str | None = None,
    voice: str = "soprano",
) -> FiguredBar | None:
    """Figurate a single bar between two anchors."""
    role: Role = _role_from_voice_string(voice)
    interval = compute_interval(_get_degree(anchor_a, role), _get_degree(anchor_b, role))
    direction = _get_direction(anchor_b, role)
    ascending = _direction_to_ascending(
        direction, _get_degree(anchor_a, role), _get_degree(anchor_b, role),
    )
    is_minor = key.mode == "minor"
    phrase_pos = determine_phrase_position(bar_num, total_bars, anchor_a.schema)
    harmonic_tension = compute_harmonic_tension(anchor_a, phrase_pos, role)
    bar_function = compute_bar_function(phrase_pos, bar_num, total_bars, anchor_b)
    rng = random.Random(seed)
    figure: Figure | None = None
    if phrase_pos.position == "cadence":
        figure = select_cadential_figure(
            _get_degree(anchor_b, role), interval, is_minor, seed, rng,
        )
    if figure is None:
        figure = _select_figure_with_filters(
            interval=interval,
            ascending=ascending,
            harmonic_tension=harmonic_tension,
            character=character,
            density=density,
            is_minor=is_minor,
            prev_leaped=prev_leaped,
            leap_direction=leap_direction,
            near_cadence=phrase_pos.position == "cadence",
            seed=seed,
        )
    if figure is None:
        return None
    offset_a = _bar_beat_to_offset(anchor_a.bar_beat, metre)
    offset_b = _bar_beat_to_offset(anchor_b.bar_beat, metre)
    gap = offset_b - offset_a
    return realise_figure_to_bar(
        figure=figure,
        bar=bar_num,
        start_degree=_get_degree(anchor_a, role),
        gap_duration=gap,
        metre=metre,
        bar_function=bar_function,
        rhythmic_unit=_get_rhythmic_unit(metre),
        next_anchor_strength="strong",
        use_hemiola=False,
        overdotted=False,
        density=density,
        use_baroque_rhythm=True,
    )


def _select_figure_with_filters(
    interval: str,
    ascending: bool,
    harmonic_tension: str,
    character: str,
    density: str,
    is_minor: bool,
    prev_leaped: bool,
    leap_direction: str | None,
    near_cadence: bool,
    seed: int,
    avoid_figure: str | None = None,
    soprano_degrees: tuple[int, ...] | None = None,
    soprano_start_midi: int = 70,
    bass_start_midi: int = 48,
    required_count: int | None = None,
) -> Figure | None:
    """Apply full filter pipeline and select figure."""
    all_figures = get_figures_for_interval(interval)
    if not all_figures:
        return None
    if required_count is not None:
        all_figures = filter_by_note_count(all_figures, required_count)
        if not all_figures:
            return None
    candidates = list(all_figures)
    candidates = filter_by_direction(candidates, ascending)
    candidates = filter_by_tension(candidates, harmonic_tension)
    candidates = filter_by_character(candidates, character)
    candidates = filter_by_density(candidates, density)
    candidates = filter_by_minor_safety(candidates, is_minor)
    candidates = filter_by_compensation(candidates, prev_leaped, leap_direction)
    candidates = filter_cadential_safe(candidates, near_cadence)
    candidates = filter_by_max_leap(candidates)
    if soprano_degrees is not None:
        candidates = filter_parallel_direct(
            candidates, soprano_degrees, soprano_start_midi, bass_start_midi
        )
        candidates = filter_cross_relation(
            candidates, soprano_degrees, soprano_start_midi, bass_start_midi
        )
    if avoid_figure and len(candidates) > 1:
        candidates = [f for f in candidates if f.name != avoid_figure] or candidates
    candidates = apply_misbehaviour(candidates, all_figures, seed)
    candidates = sort_by_weight(candidates)
    return select_figure(candidates, seed)


def _try_select_compound_figure(
    interval: str,
    ascending: bool,
    harmonic_tension: str,
    density: str,
    is_minor: bool,
    seed: int,
) -> Figure | None:
    """Try to select a compound figure to maintain compound melody texture."""
    all_figures = get_figures_for_interval(interval)
    compound_figures = [f for f in all_figures if f.is_compound]
    if not compound_figures:
        return None
    candidates = filter_by_direction(compound_figures, ascending)
    candidates = filter_by_tension(candidates, harmonic_tension)
    candidates = filter_by_density(candidates, density)
    candidates = filter_by_minor_safety(candidates, is_minor)
    if not candidates:
        return None
    candidates = sort_by_weight(candidates)
    return select_figure(candidates, seed)


def _apply_schema_figuration(
    anchors: Sequence[Anchor],
    metre: str,
    seed: int,
    density: str,
    is_minor: bool,
    role: Role,
    total_bars: int,
    voice: str = "soprano",
    passage_assignments: Sequence[PassageAssignment] | None = None,
    soprano_figured_bars: list[FiguredBar] | None = None,
) -> list[FiguredBar]:
    """Apply schema-aware figuration to a schema section."""
    if len(anchors) < 2:
        return []
    schema_name = anchors[0].schema or ""
    strategy = get_strategy_for_schema(schema_name)
    profile = get_profile_for_schema(schema_name)
    character = _profile_to_character(profile)
    direction = anchors[1].upper_direction if len(anchors) > 1 else None
    anchor_a = anchors[0]
    anchor_b = anchors[1]
    interval = compute_interval(_get_degree(anchor_a, role), _get_degree(anchor_b, role))
    dir_hint = _get_direction(anchor_b, role)
    ascending = _direction_to_ascending(
        dir_hint, _get_degree(anchor_a, role), _get_degree(anchor_b, role),
    )
    offset_a = _bar_beat_to_offset(anchor_a.bar_beat, metre)
    offset_b = _bar_beat_to_offset(anchor_b.bar_beat, metre)
    bar_num = _parse_bar_beat(anchor_a.bar_beat)[0]
    start_beat = compute_beat_class(voice, bar_num, passage_assignments)
    raw_gap = offset_b - offset_a
    effective_gap = compute_effective_gap(raw_gap, start_beat, metre)
    effective_density = reduce_density(density) if start_beat == 2 else density
    required_count, _ = compute_rhythmic_distribution(effective_gap, effective_density)
    initial_figure = _select_figure_with_filters(
        interval=interval,
        ascending=ascending,
        harmonic_tension="low",
        character=character,
        density=effective_density,
        is_minor=is_minor,
        prev_leaped=False,
        leap_direction=None,
        near_cadence=False,
        seed=seed,
        required_count=required_count,
    )
    if initial_figure is None:
        initial_figure = _create_direct_figure(interval, _get_degree(anchor_a, role), _get_degree(anchor_b, role))
    target_degrees = [_get_degree(a, role) for a in anchors[:-1]]
    figures = apply_strategy(
        strategy=strategy,
        initial_figure=initial_figure,
        target_degrees=target_degrees,
        direction=direction,
    )
    result: list[FiguredBar] = []
    for i, figure in enumerate(figures):
        if i + 1 >= len(anchors):
            break
        anchor_a = anchors[i]
        anchor_b = anchors[i + 1]
        bar_num = _parse_bar_beat(anchor_a.bar_beat)[0]
        start_beat = compute_beat_class(voice, bar_num, passage_assignments)
        bar_effective_density = density
        if start_beat == 2:
            soprano_is_sparse = False
            if soprano_figured_bars is not None and i < len(soprano_figured_bars):
                soprano_note_count = len(soprano_figured_bars[i].durations)
                soprano_is_sparse = soprano_note_count <= RHYTHMIC_CONTRAST_THRESHOLD
            if not soprano_is_sparse:
                bar_effective_density = reduce_density(density)
        is_final_stage = (i == len(figures) - 1)
        offset_a = _bar_beat_to_offset(anchor_a.bar_beat, metre)
        offset_b = _bar_beat_to_offset(anchor_b.bar_beat, metre)
        raw_gap = offset_b - offset_a
        effective_gap = compute_effective_gap(raw_gap, start_beat, metre)
        if start_beat == 2:
            schema_texture = get_schema_texture(schema_name)
            texture = get_accompany_texture_for_bar(bar_num, passage_assignments, schema_texture)
            if texture == "pillar":
                bass_degree = _get_degree(anchor_a, role)
                prev_bass_degree = result[-1].degrees[-1] if result else None
                prev_soprano = soprano_figured_bars[i - 1] if soprano_figured_bars and i > 0 else None
                curr_soprano = soprano_figured_bars[i] if soprano_figured_bars and i < len(soprano_figured_bars) else None
                if _check_pillar_creates_direct_motion(prev_soprano, curr_soprano, prev_bass_degree, bass_degree):
                    texture = "staggered"
            if texture == "pillar":
                figured_bar = _create_pillar_bar(
                    bar_num=bar_num,
                    start_degree=_get_degree(anchor_a, role),
                    gap_duration=effective_gap,
                )
                result.append(figured_bar)
                continue
            elif texture == "staggered":
                figured_bar = _create_staggered_bar(
                    figure=figure,
                    bar_num=bar_num,
                    start_degree=_get_degree(anchor_a, role),
                    gap_duration=raw_gap,
                    metre=metre,
                    density=bar_effective_density,
                )
                result.append(figured_bar)
                continue
            start_beat = 1
            effective_gap = raw_gap
        figured_bar = realise_figure_to_bar(
            figure=figure,
            bar=bar_num,
            start_degree=_get_degree(anchor_a, role),
            gap_duration=effective_gap,
            metre=metre,
            start_beat=start_beat,
            density=bar_effective_density,
            use_baroque_rhythm=True,
        )
        if soprano_figured_bars is not None and i < len(soprano_figured_bars):
            soprano_bar = soprano_figured_bars[i]
            bass_start = _get_degree(anchor_a, role)
            soprano_start = soprano_bar.degrees[0] if soprano_bar.degrees else 1
            bass_rel = tuple(d - bass_start for d in figured_bar.degrees)
            soprano_rel = tuple(d - soprano_start for d in soprano_bar.degrees)
            if _would_create_parallel_or_direct_realized(soprano_rel, bass_rel, soprano_start, bass_start):
                bar_interval = compute_interval(
                    _get_degree(anchor_a, role), _get_degree(anchor_b, role)
                )
                alt_figure = _select_figure_with_filters(
                    interval=bar_interval,
                    ascending=ascending,
                    harmonic_tension="low",
                    character=character,
                    density=bar_effective_density,
                    is_minor=is_minor,
                    prev_leaped=False,
                    leap_direction=None,
                    near_cadence=False,
                    seed=seed + i + 1000,
                    avoid_figure=figure.name,
                )
                if alt_figure is not None:
                    alt_bar = realise_figure_to_bar(
                        figure=alt_figure,
                        bar=bar_num,
                        start_degree=_get_degree(anchor_a, role),
                        gap_duration=effective_gap,
                        metre=metre,
                        start_beat=start_beat,
                        density=bar_effective_density,
                        use_baroque_rhythm=True,
                    )
                    alt_rel = tuple(d - bass_start for d in alt_bar.degrees)
                    if not _would_create_parallel_or_direct_realized(soprano_rel, alt_rel, soprano_start, bass_start):
                        figured_bar = alt_bar
        result.append(figured_bar)
    return result


def _get_rhythmic_unit(metre: str) -> Fraction:
    """Get characteristic rhythmic unit for metre."""
    parts = metre.split("/")
    denom = int(parts[1])
    return Fraction(1, denom)


def _profile_to_character(profile: str) -> str:
    """Map figuration profile to figure character."""
    if profile.startswith("sequence_"):
        return "energetic"
    if profile == "stepwise_descent":
        return "expressive"
    if profile in ("repeated_tone", "pedal"):
        return "plain"
    if profile == "stepwise_ascent":
        return "energetic"
    if profile == "stepwise_mixed":
        return "expressive"
    return "plain"


def _create_direct_figure(interval: str, from_degree: int, to_degree: int) -> Figure:
    """Create a simple direct figure when no candidates match."""
    diff = to_degree - from_degree
    while diff > 7:
        diff -= 7
    while diff < -7:
        diff += 7
    return Figure(
        name=f"direct_{interval}",
        degrees=(0, diff),
        contour="direct",
        polarity="balanced",
        arrival="direct",
        placement="span",
        character="plain",
        harmonic_tension="low",
        max_density="low",
        cadential_safe=True,
        repeatable=True,
        requires_compensation=abs(diff) > 2,
        compensation_direction="down" if diff > 0 else "up" if diff < 0 else None,
        is_compound=False,
        minor_safe=True,
        requires_leading_tone=False,
        weight=0.5,
    )


def _is_leap(figure: Figure) -> bool:
    """Check if figure ends with a leap (interval > 2)."""
    degrees = figure.degrees
    if len(degrees) < 2:
        return False
    return abs(degrees[-1] - degrees[-2]) > 2


def _is_leap_from_figured_bar(bar: FiguredBar) -> bool:
    """Check if figured bar ends with a leap."""
    degrees = bar.degrees
    if len(degrees) < 2:
        return False
    return abs(degrees[-1] - degrees[-2]) > 2


def _parse_bar_beat(bar_beat: str) -> tuple[int, float]:
    """Parse bar.beat string into (bar, beat) tuple."""
    parts = bar_beat.split(".")
    bar = int(parts[0])
    beat = float(parts[1]) if len(parts) > 1 else 1.0
    return (bar, beat)


def _bar_beat_to_offset(bar_beat: str, metre: str) -> Fraction:
    """Convert bar.beat string to offset in whole notes."""
    bar, beat = _parse_bar_beat(bar_beat)
    parts = metre.split("/")
    beats_per_bar = int(parts[0])
    beat_value = Fraction(1, int(parts[1]))
    offset = Fraction(bar - 1) * beats_per_bar * beat_value
    offset += Fraction(int(beat) - 1) * beat_value
    return offset


def _count_bars(anchors: Sequence[Anchor]) -> int:
    """Count total bars from anchor sequence."""
    if not anchors:
        return 0
    max_bar = max(_parse_bar_beat(a.bar_beat)[0] for a in anchors)
    return max_bar
