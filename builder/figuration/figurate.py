"""Main figuration entry points for baroque melodic patterns."""
import random
from fractions import Fraction
from typing import Sequence

from builder.figuration.junction import check_junction, find_valid_figure
from builder.figuration.loader import get_cadential
from builder.figuration.realiser import realise_figure_to_bar
from builder.figuration.selector import (
    apply_misbehaviour,
    compute_interval,
    determine_phrase_position,
    filter_by_character,
    filter_by_compensation,
    filter_by_density,
    filter_by_direction,
    filter_by_minor_safety,
    filter_by_tension,
    filter_cadential_safe,
    get_figures_for_interval,
    select_figure,
    sort_by_weight,
)
from builder.figuration.sequencer import SequencerState, apply_fortspinnung
from builder.figuration.types import (
    CadentialFigure,
    Figure,
    FiguredBar,
    PhrasePosition,
)
from builder.types import Anchor
from shared.key import Key

# Sequential schemas that trigger Fortspinnung
SEQUENTIAL_SCHEMAS: frozenset[str] = frozenset({"monte", "fonte", "meyer", "ponte"})
# Maximum anchors in a sequential section (Rule of Three: 3 repetitions = 4 anchors)
MAX_SEQUENCE_ANCHORS: int = 4
# Probability of phrase deformation
DEFORMATION_PROBABILITY: float = 0.15
# Probability of cadential understatement at weak cadences
CADENTIAL_UNDERSTATEMENT_PROBABILITY: float = 0.10


def figurate(
    anchors: Sequence[Anchor],
    key: Key,
    metre: str,
    seed: int,
    density: str = "medium",
    affect_character: str = "plain",
) -> list[FiguredBar]:
    """Main entry point: Convert anchors to figured bars."""
    if len(anchors) < 2:
        return []
    rng = random.Random(seed)
    sorted_anchors = sorted(anchors, key=lambda a: _parse_bar_beat(a.bar_beat))
    is_minor = key.mode == "minor"
    total_bars = _count_bars(sorted_anchors)
    phrase_deformation = _select_phrase_deformation(rng, total_bars)
    sequential_sections = _detect_sequential_sections(sorted_anchors)
    compound_melody_active = False
    figured_bars: list[FiguredBar] = []
    sequencer_state = SequencerState()
    prev_leaped = False
    leap_direction: str | None = None
    i = 0
    while i < len(sorted_anchors) - 1:
        anchor_a = sorted_anchors[i]
        anchor_b = sorted_anchors[i + 1]
        bar_num = _parse_bar_beat(anchor_a.bar_beat)[0]
        seq_info = _in_sequential_section(i, sequential_sections)
        if seq_info is not None:
            seq_start, seq_end = seq_info
            seq_anchors = sorted_anchors[seq_start:seq_end + 1]
            seq_bars = _apply_fortspinnung_to_section(
                seq_anchors, metre, seed + i, density, is_minor, sequencer_state,
            )
            figured_bars.extend(seq_bars)
            i = seq_end
            if seq_bars:
                prev_leaped = _is_leap_from_figured_bar(seq_bars[-1])
            continue
        interval = compute_interval(anchor_a.soprano_degree, anchor_b.soprano_degree)
        ascending = anchor_b.soprano_degree > anchor_a.soprano_degree
        phrase_pos = _determine_position_with_deformation(
            bar_num, total_bars, anchor_a.schema, phrase_deformation,
        )
        harmonic_tension = _compute_harmonic_tension(anchor_a, phrase_pos)
        bar_function = _compute_bar_function(phrase_pos, bar_num, total_bars)
        use_hemiola = _should_use_hemiola(bar_num, total_bars, metre, phrase_deformation)
        next_anchor_strength = _compute_next_anchor_strength(i, sorted_anchors, total_bars)
        if phrase_pos.position == "cadence":
            figure = _select_cadential_figure(
                anchor_b.soprano_degree, interval, is_minor, seed + i, rng,
            )
        else:
            figure = None
        if figure is None:
            figure = _select_figure_with_filters(
                interval=interval,
                ascending=ascending,
                harmonic_tension=harmonic_tension,
                character=affect_character if phrase_pos.position == "opening" else phrase_pos.character,
                density=density,
                is_minor=is_minor,
                prev_leaped=prev_leaped,
                leap_direction=leap_direction,
                near_cadence=phrase_pos.position == "cadence",
                seed=seed + i,
            )
        if figure is None:
            figure = _create_direct_figure(interval, anchor_a.soprano_degree, anchor_b.soprano_degree)
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
            if not check_junction(figure, next_anchor.soprano_degree):
                candidates = get_figures_for_interval(interval)
                alt_figure = find_valid_figure(candidates, next_anchor.soprano_degree)
                if alt_figure:
                    figure = alt_figure
        offset_a = _bar_beat_to_offset(anchor_a.bar_beat, metre)
        offset_b = _bar_beat_to_offset(anchor_b.bar_beat, metre)
        gap = offset_b - offset_a
        figured_bar = realise_figure_to_bar(
            figure=figure,
            bar=bar_num,
            start_degree=anchor_a.soprano_degree,
            gap_duration=gap,
            metre=metre,
            bar_function=bar_function,
            rhythmic_unit=_get_rhythmic_unit(metre),
            next_anchor_strength=next_anchor_strength,
            use_hemiola=use_hemiola,
            overdotted=_should_use_overdotted(affect_character, phrase_pos),
        )
        figured_bars.append(figured_bar)
        prev_leaped = _is_leap(figure)
        leap_direction = "up" if ascending else "down"
        i += 1
    return figured_bars


def figurate_single_bar(
    anchor_a: Anchor,
    anchor_b: Anchor,
    key: Key,
    metre: str,
    seed: int,
    bar_num: int,
    total_bars: int,
    density: str = "medium",
    character: str = "plain",
    prev_leaped: bool = False,
    leap_direction: str | None = None,
) -> FiguredBar | None:
    """Figurate a single bar between two anchors."""
    interval = compute_interval(anchor_a.soprano_degree, anchor_b.soprano_degree)
    ascending = anchor_b.soprano_degree > anchor_a.soprano_degree
    is_minor = key.mode == "minor"
    phrase_pos = determine_phrase_position(bar_num, total_bars, anchor_a.schema)
    harmonic_tension = _compute_harmonic_tension(anchor_a, phrase_pos)
    bar_function = _compute_bar_function(phrase_pos, bar_num, total_bars)
    rng = random.Random(seed)
    figure: Figure | None = None
    if phrase_pos.position == "cadence":
        figure = _select_cadential_figure(
            anchor_b.soprano_degree, interval, is_minor, seed, rng,
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
        start_degree=anchor_a.soprano_degree,
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
) -> Figure | None:
    """Apply full filter pipeline and select figure."""
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
    candidates = apply_misbehaviour(candidates, all_figures, seed)
    candidates = sort_by_weight(candidates)
    return select_figure(candidates, seed)


def _select_cadential_figure(
    to_degree: int,
    interval: str,
    is_minor: bool,
    seed: int,
    rng: random.Random,
) -> Figure | None:
    """Select from cadential table for phrase endings."""
    if rng.random() < CADENTIAL_UNDERSTATEMENT_PROBABILITY:
        return None
    cadential = get_cadential()
    if to_degree == 1:
        target = "target_1"
    elif to_degree == 5:
        target = "target_5"
    else:
        return None
    if target not in cadential:
        return None
    approaches = cadential[target]
    approach_key = _interval_to_approach_key(interval)
    if approach_key not in approaches:
        if "unison" in approaches:
            approach_key = "unison"
        else:
            return None
    cadential_figures = approaches[approach_key]
    if not cadential_figures:
        return None
    if is_minor:
        cadential_figures = [cf for cf in cadential_figures if _cadential_minor_safe(cf)]
        if not cadential_figures:
            cadential_figures = approaches[approach_key]
    rng_local = random.Random(seed)
    selected_cf = rng_local.choice(cadential_figures)
    return _cadential_to_figure(selected_cf)


def _cadential_to_figure(cf: CadentialFigure) -> Figure:
    """Convert CadentialFigure to regular Figure for realisation."""
    return Figure(
        name=cf.name,
        degrees=cf.degrees,
        contour=cf.contour,
        polarity="balanced",
        arrival="stepwise" if len(cf.degrees) > 2 else "direct",
        placement="end",
        character="plain",
        harmonic_tension="low",
        max_density="high" if len(cf.degrees) > 4 else "medium",
        cadential_safe=True,
        repeatable=False,
        requires_compensation=False,
        compensation_direction=None,
        is_compound=False,
        minor_safe=True,
        requires_leading_tone=cf.contour in ("trilled_resolution", "leading_tone_resolution"),
        weight=1.0,
    )


def _cadential_minor_safe(cf: CadentialFigure) -> bool:
    """Check if cadential figure is safe in minor key."""
    return cf.contour not in ("trilled_resolution",)


def _interval_to_approach_key(interval: str) -> str:
    """Map interval name to cadential approach key."""
    mapping = {
        "unison": "unison",
        "step_up": "step_up",
        "step_down": "step_down",
        "third_up": "third_up",
        "third_down": "third_down",
        "fourth_up": "fourth_up",
        "fourth_down": "fourth_down",
        "fifth_up": "fifth_up",
        "fifth_down": "fifth_down",
    }
    return mapping.get(interval, "step_down")


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


def _apply_fortspinnung_to_section(
    anchors: Sequence[Anchor],
    metre: str,
    seed: int,
    density: str,
    is_minor: bool,
    state: SequencerState,
) -> list[FiguredBar]:
    """Apply Fortspinnung (spinning out) to a sequential section."""
    if len(anchors) < 2:
        return []
    anchor_a = anchors[0]
    anchor_b = anchors[1]
    interval = compute_interval(anchor_a.soprano_degree, anchor_b.soprano_degree)
    ascending = anchor_b.soprano_degree > anchor_a.soprano_degree
    initial_figure = _select_figure_with_filters(
        interval=interval,
        ascending=ascending,
        harmonic_tension="low",
        character="energetic",
        density=density,
        is_minor=is_minor,
        prev_leaped=False,
        leap_direction=None,
        near_cadence=False,
        seed=seed,
    )
    if initial_figure is None:
        initial_figure = _create_direct_figure(interval, anchor_a.soprano_degree, anchor_b.soprano_degree)
    target_degrees = [a.soprano_degree for a in anchors[:-1]]
    figures = apply_fortspinnung(initial_figure, target_degrees, state)
    result: list[FiguredBar] = []
    for i, figure in enumerate(figures):
        if i + 1 >= len(anchors):
            break
        anchor_a = anchors[i]
        anchor_b = anchors[i + 1]
        bar_num = _parse_bar_beat(anchor_a.bar_beat)[0]
        offset_a = _bar_beat_to_offset(anchor_a.bar_beat, metre)
        offset_b = _bar_beat_to_offset(anchor_b.bar_beat, metre)
        gap = offset_b - offset_a
        figured_bar = realise_figure_to_bar(
            figure=figure,
            bar=bar_num,
            start_degree=anchor_a.soprano_degree,
            gap_duration=gap,
            metre=metre,
        )
        result.append(figured_bar)
    return result


def _detect_sequential_sections(anchors: Sequence[Anchor]) -> list[tuple[int, int]]:
    """Detect sequential schema sections in anchor sequence."""
    sections: list[tuple[int, int]] = []
    i = 0
    while i < len(anchors):
        schema = anchors[i].schema.lower() if anchors[i].schema else ""
        if schema in SEQUENTIAL_SCHEMAS:
            start = i
            while i < len(anchors) and anchors[i].schema and anchors[i].schema.lower() == schema:
                if i - start >= MAX_SEQUENCE_ANCHORS:
                    break
                i += 1
            if i - start >= 2:
                sections.append((start, i))
        else:
            i += 1
    return sections


def _in_sequential_section(idx: int, sections: list[tuple[int, int]]) -> tuple[int, int] | None:
    """Check if index is start of a sequential section."""
    for start, end in sections:
        if idx == start:
            return (start, end)
    return None


def _select_phrase_deformation(rng: random.Random, total_bars: int) -> str | None:
    """Select phrase deformation type with low probability."""
    if total_bars < 6:
        return None
    if rng.random() > DEFORMATION_PROBABILITY:
        return None
    return rng.choice(["early_cadence", "extended_continuation"])


def _determine_position_with_deformation(
    bar: int,
    total_bars: int,
    schema_type: str | None,
    deformation: str | None,
) -> PhrasePosition:
    """Determine phrase position accounting for deformation."""
    base_pos = determine_phrase_position(bar, total_bars, schema_type)
    if deformation is None:
        return base_pos
    if deformation == "early_cadence":
        cadence_start = max(2, (3 * total_bars) // 4)
        if bar == cadence_start - 1:
            return PhrasePosition(
                position="cadence",
                bars=(cadence_start - 1, total_bars),
                character="plain",
                sequential=False,
            )
    elif deformation == "extended_continuation":
        cadence_start = max(2, (3 * total_bars) // 4)
        if bar == cadence_start:
            return PhrasePosition(
                position="continuation",
                bars=(base_pos.bars[0], cadence_start),
                character="energetic",
                sequential=base_pos.sequential,
            )
    return base_pos


def _compute_harmonic_tension(
    anchor_a: Anchor,
    phrase_pos: PhrasePosition,
) -> str:
    """Compute harmonic tension from schema type, bass degree, and bar function."""
    if phrase_pos.position == "cadence":
        base_tension = "low"
    elif phrase_pos.position == "continuation":
        base_tension = "medium"
    else:
        base_tension = "low"
    bass = anchor_a.bass_degree
    if bass in (2, 4, 7):
        if base_tension == "low":
            return "medium"
        return "high"
    if bass in (5,):
        return "medium"
    schema = anchor_a.schema.lower() if anchor_a.schema else ""
    if schema in ("monte", "fonte"):
        return "medium"
    return base_tension


def _compute_bar_function(phrase_pos: PhrasePosition, bar_num: int, total_bars: int) -> str:
    """Compute bar function for rhythm realisation."""
    if phrase_pos.position == "cadence":
        return "cadential"
    if phrase_pos.sequential:
        return "schema_arrival"
    if bar_num == total_bars - 2:
        return "preparatory"
    return "passing"


def _should_use_hemiola(bar_num: int, total_bars: int, metre: str, deformation: str | None) -> bool:
    """Determine if hemiola should be used for this bar."""
    if metre != "3/4":
        return False
    if total_bars < 6:
        return False
    hemiola_bar = total_bars - 2
    if bar_num == hemiola_bar or bar_num == hemiola_bar + 1:
        if deformation == "early_cadence":
            return False
        return True
    return False


def _compute_next_anchor_strength(
    idx: int,
    anchors: Sequence[Anchor],
    total_bars: int,
) -> str:
    """Compute strength of next anchor for anacrusis handling."""
    if idx + 2 >= len(anchors):
        return "strong"
    next_bar = _parse_bar_beat(anchors[idx + 1].bar_beat)[0]
    if next_bar == 1 or next_bar == (total_bars // 2) + 1:
        return "strong"
    if next_bar >= total_bars - 1:
        return "strong"
    return "weak"


def _should_use_overdotted(affect_character: str, phrase_pos: PhrasePosition) -> bool:
    """Determine if overdotted rhythms should be used."""
    return affect_character == "ornate"


def _get_rhythmic_unit(metre: str) -> Fraction:
    """Get characteristic rhythmic unit for metre."""
    parts = metre.split("/")
    denom = int(parts[1])
    return Fraction(1, denom)


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
