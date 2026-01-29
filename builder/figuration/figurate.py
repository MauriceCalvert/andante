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
    reduce_density,
    should_use_hemiola,
    should_use_overdotted,
)
from builder.figuration.cadential import (
    CADENTIAL_UNDERSTATEMENT_PROBABILITY,
    select_cadential_figure,
)
from builder.figuration.junction import check_junction, find_valid_figure
from builder.figuration.phrase import (
    DEFORMATION_PROBABILITY,
    MAX_SCHEMA_SECTION_ANCHORS,
    MIN_SCHEMA_SECTION_ANCHORS,
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
    filter_by_tension,
    filter_cadential_safe,
    filter_parallel_direct,
    get_figures_for_interval,
)
# sequencer functions used through strategies module
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


def _get_direction(anchor: Anchor, role: Role) -> str | None:
    """Get the direction to reach this anchor based on voice role.
    
    Args:
        anchor: Schema anchor with upper_direction and lower_direction.
        role: Voice role determining which direction to select.
    
    Returns:
        Direction string (up/down/same) or None for first anchor.
    """
    if role == Role.SCHEMA_LOWER:
        return anchor.lower_direction
    return anchor.upper_direction


def _direction_to_ascending(direction: str | None, degree_a: int, degree_b: int) -> bool:
    """Convert direction to ascending boolean.
    
    If direction is explicit, use it directly.
    If direction is None or same, fall back to degree comparison.
    
    Args:
        direction: Explicit direction (up/down/same) or None.
        degree_a: Starting degree (1-7).
        degree_b: Ending degree (1-7).
    
    Returns:
        True if ascending motion, False otherwise.
    """
    if direction == "up":
        return True
    if direction == "down":
        return False
    # For 'same' or None, use degree comparison as fallback
    return degree_b > degree_a


def _get_degree(anchor: Anchor, role: Role) -> int:
    """Get the appropriate degree from anchor based on voice role.
    
    Args:
        anchor: Schema anchor with upper_degree and lower_degree.
        role: Voice role determining which degree to select.
    
    Returns:
        Degree value (1-7) for the voice role.
    """
    if role == Role.SCHEMA_LOWER:
        return anchor.lower_degree
    return anchor.upper_degree


def _role_from_voice_string(voice: str) -> Role:
    """Convert legacy voice string to Role enum.
    
    Args:
        voice: Legacy string "soprano" or "bass".
    
    Returns:
        Corresponding Role enum value.
    """
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
    """Main entry point: Convert anchors to figured bars.

    Args:
        voice: Which anchor degree to use - "soprano" (upper) or "bass" (lower).
               Maps to Role.SCHEMA_UPPER or Role.SCHEMA_LOWER.
        soprano_figured_bars: When figurating bass, pass soprano bars to avoid
               parallel/direct fifths and octaves.
        passage_assignments: Lead voice assignments for rhythm complementarity.
    """
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
            seq_anchors = sorted_anchors[seq_start:seq_end + 1]
            seq_bars = _apply_schema_figuration(
                anchors=seq_anchors,
                metre=metre,
                seed=seed + i,
                density=density,
                is_minor=is_minor,
                role=role,
                voice=voice,
                passage_assignments=passage_assignments,
            )
            figured_bars.extend(seq_bars)
            i = seq_end
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
        bar_function = compute_bar_function(phrase_pos, bar_num, total_bars)
        use_hemiola = should_use_hemiola(bar_num, total_bars, metre, phrase_deformation)
        next_anchor_strength = compute_next_anchor_strength(i, sorted_anchors, total_bars)
        if phrase_pos.position == "cadence":
            figure = select_cadential_figure(
                _get_degree(anchor_b, role), interval, is_minor, seed + i, rng,
            )
        else:
            figure = None
        if figure is None:
            # Get soprano figure info for bass parallel/direct check
            soprano_degrees: tuple[int, ...] | None = None
            soprano_start_midi: int = 70  # Default soprano median
            bass_start_midi: int = 48  # Default bass median
            if voice == "bass" and soprano_figured_bars is not None and i < len(soprano_figured_bars):
                soprano_degrees = soprano_figured_bars[i].degrees
                # Approximate starting MIDI from anchor degrees
                soprano_start_midi = 60 + (anchor_a.upper_degree - 1) * 2
                bass_start_midi = 36 + (anchor_a.lower_degree - 1) * 2
            # Compute beat class for rhythm complementarity (used in figure selection)
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
            if not check_junction(figure, _get_degree(next_anchor, role)):
                candidates = get_figures_for_interval(interval)
                alt_figure = find_valid_figure(candidates, _get_degree(next_anchor, role))
                if alt_figure:
                    figure = alt_figure
        offset_a = _bar_beat_to_offset(anchor_a.bar_beat, metre)
        offset_b = _bar_beat_to_offset(anchor_b.bar_beat, metre)
        raw_gap = offset_b - offset_a
        # Compute beat class for rhythm complementarity
        start_beat = compute_beat_class(voice, bar_num, passage_assignments)
        effective_gap = compute_effective_gap(raw_gap, start_beat, metre)
        # Accompanying voice uses sparser density
        effective_density = reduce_density(density) if start_beat == 2 else density
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
        )
        figured_bars.append(figured_bar)
        prev_leaped = _is_leap(figure)
        leap_direction = "up" if ascending else "down"
        prev_figure_name = figure.name
        i += 1
    return figured_bars


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
    bar_function = compute_bar_function(phrase_pos, bar_num, total_bars)
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
) -> Figure | None:
    """Apply full filter pipeline and select figure.

    Args:
        avoid_figure: Name of figure to avoid (for variety).
        soprano_degrees: When selecting bass, soprano degrees to check against.
        soprano_start_midi: Soprano starting MIDI pitch for parallel/direct check.
        bass_start_midi: Bass starting MIDI pitch for parallel/direct check.
    """
    all_figures = get_figures_for_interval(interval)
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
    # Filter parallel/direct fifths and octaves when bass has soprano info
    if soprano_degrees is not None:
        candidates = filter_parallel_direct(
            candidates, soprano_degrees, soprano_start_midi, bass_start_midi
        )
    # Avoid repeating the same figure consecutively
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
    voice: str = "soprano",
    passage_assignments: Sequence[PassageAssignment] | None = None,
) -> list[FiguredBar]:
    """Apply schema-aware figuration to a schema section.

    Uses schema-specific strategies (accelerating, relaxing, static, dyadic)
    to generate appropriate figure sequences for each schema type.
    The figuration profile influences pattern selection character.
    """
    if len(anchors) < 2:
        return []
    # Determine schema and get strategy and profile
    schema_name = anchors[0].schema or ""
    strategy = get_strategy_for_schema(schema_name)
    profile = get_profile_for_schema(schema_name)
    # Determine character from profile type
    character = _profile_to_character(profile)
    # Get direction from schema definition if available
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
    initial_figure = _select_figure_with_filters(
        interval=interval,
        ascending=ascending,
        harmonic_tension="low",
        character=character,
        density=density,
        is_minor=is_minor,
        prev_leaped=False,
        leap_direction=None,
        near_cadence=False,
        seed=seed,
    )
    if initial_figure is None:
        initial_figure = _create_direct_figure(interval, _get_degree(anchor_a, role), _get_degree(anchor_b, role))
    target_degrees = [_get_degree(a, role) for a in anchors[:-1]]
    # Apply schema-aware strategy instead of generic Fortspinnung
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
        offset_a = _bar_beat_to_offset(anchor_a.bar_beat, metre)
        offset_b = _bar_beat_to_offset(anchor_b.bar_beat, metre)
        raw_gap = offset_b - offset_a
        # Compute beat class for rhythm complementarity
        start_beat = compute_beat_class(voice, bar_num, passage_assignments)
        effective_gap = compute_effective_gap(raw_gap, start_beat, metre)
        figured_bar = realise_figure_to_bar(
            figure=figure,
            bar=bar_num,
            start_degree=_get_degree(anchor_a, role),
            gap_duration=effective_gap,
            metre=metre,
            start_beat=start_beat,
        )
        result.append(figured_bar)
    return result


def _get_rhythmic_unit(metre: str) -> Fraction:
    """Get characteristic rhythmic unit for metre."""
    parts = metre.split("/")
    denom = int(parts[1])
    return Fraction(1, denom)


def _profile_to_character(profile: str) -> str:
    """Map figuration profile to figure character.

    Profiles indicate the type of melodic motion, which maps to character:
    - sequence_* profiles are energetic (driving motion)
    - stepwise_descent is expressive (relaxed)
    - repeated_tone/pedal are plain (stable)
    - Others default to plain
    """
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
