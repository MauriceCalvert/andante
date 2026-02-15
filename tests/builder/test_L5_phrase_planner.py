"""L5 Phrase Planner contract tests."""
from fractions import Fraction
from typing import Any

import pytest

from builder.config_loader import load_configs
from builder.phrase_planner import build_phrase_plans
from builder.phrase_types import BeatPosition, PhrasePlan
from builder.types import GenreConfig, SchemaChain
from planner.metric.layer import layer_4_metric
from planner.schematic import layer_3_schematic
from planner.tonal import layer_2_tonal
from shared.constants import CADENTIAL_POSITION
from shared.key import Key
from tests.conftest import GENRES, KEYS

# L5 uses 2 affects: Zierlich (light) and Dolore (dark) per remediation plan 4.2
_L5_AFFECTS: tuple[str, ...] = ("Zierlich", "Dolore")


def _bar_length(metre: str) -> Fraction:
    """Parse metre to bar length."""
    num, den = metre.split("/")
    return Fraction(int(num), int(den))


def _max_beat(metre: str) -> int:
    """Get maximum beat number for a metre."""
    num, _ = metre.split("/")
    return int(num)


_L5_PARAMS: list[tuple[str, str, str]] = [
    (g, k, a) for g in GENRES for k in KEYS for a in _L5_AFFECTS
]


@pytest.fixture(params=_L5_PARAMS, ids=[f"{g}_{k}_{a}" for g, k, a in _L5_PARAMS])
def phrase_plans_result(
    request: pytest.FixtureRequest,
) -> tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain]:
    """Run pipeline through L5 for each genre+key+affect combination."""
    genre, key, affect = request.param
    config = load_configs(genre=genre, key=key, affect=affect)
    gc: GenreConfig = config["genre"]
    tonal_plan = layer_2_tonal(affect_config=config["affect"], genre_config=gc, seed=42)
    chain: SchemaChain = layer_3_schematic(
        tonal_plan=tonal_plan, genre_config=gc,
        form_config=config["form"], schemas=config["schemas"], seed=43,
    )
    bar_assignments, anchors, total_bars = layer_4_metric(
        schema_chain=chain, genre_config=gc, form_config=config["form"],
        key_config=config["key"], schemas=config["schemas"], tonal_plan=tonal_plan,
    )
    plans: tuple[PhrasePlan, ...] = build_phrase_plans(
        schema_chain=chain, anchors=anchors, genre_config=gc,
        schemas=config["schemas"], total_bars=total_bars,
    )
    return plans, gc, config["schemas"], total_bars, chain


def test_output_type(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-01: output is tuple of PhrasePlan."""
    plans, _, _, _, _ = phrase_plans_result
    assert isinstance(plans, tuple)
    for i, plan in enumerate(plans):
        assert isinstance(plan, PhrasePlan), f"Element {i} is not PhrasePlan"


def test_plans_nonempty(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-02: at least one plan exists."""
    plans, _, _, _, _ = phrase_plans_result
    assert len(plans) >= 1


def test_schema_names_valid(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-03: every schema_name is in the schemas dict."""
    plans, _, schemas, _, _ = phrase_plans_result
    for plan in plans:
        assert plan.schema_name in schemas, (
            f"Schema '{plan.schema_name}' not in catalogue"
        )


def test_upper_degrees_match_schema(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-04: degrees_upper matches schema soprano_degrees."""
    plans, _, schemas, _, _ = phrase_plans_result
    for plan in plans:
        schema_def = schemas[plan.schema_name]
        if schema_def.position == CADENTIAL_POSITION:
            # Cadential schemas use templates — validated by cadence_writer tests
            continue
        if schema_def.sequential:
            per_seg: tuple[int, ...] = schema_def.soprano_degrees
            expected = per_seg * plan.bar_span
            assert plan.degrees_upper == expected, (
                f"Sequential plan degrees_upper {plan.degrees_upper} != "
                f"expected {expected} ({plan.bar_span} segments, {len(per_seg)} per segment)"
            )
            continue
        expected = schema_def.soprano_degrees
        assert plan.degrees_upper == expected, (
            f"Plan degrees_upper {plan.degrees_upper} != "
            f"expected {expected}"
        )


def test_lower_degrees_match_schema(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-05: degrees_lower matches schema bass_degrees."""
    plans, _, schemas, _, _ = phrase_plans_result
    for plan in plans:
        schema_def = schemas[plan.schema_name]
        if schema_def.position == CADENTIAL_POSITION:
            # Cadential schemas use templates — validated by cadence_writer tests
            continue
        if schema_def.sequential:
            per_seg: tuple[int, ...] = schema_def.bass_degrees
            expected = per_seg * plan.bar_span
            assert plan.degrees_lower == expected, (
                f"Sequential plan degrees_lower {plan.degrees_lower} != "
                f"expected {expected} ({plan.bar_span} segments, {len(per_seg)} per segment)"
            )
            continue
        expected = schema_def.bass_degrees
        assert plan.degrees_lower == expected, (
            f"Plan degrees_lower {plan.degrees_lower} != "
            f"expected {expected}"
        )


def test_positions_count(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-06: degree_positions count matches degrees_upper count."""
    plans, _, _, _, _ = phrase_plans_result
    for plan in plans:
        assert len(plan.degree_positions) == len(plan.degrees_upper), (
            f"degree_positions count {len(plan.degree_positions)} != "
            f"degrees_upper count {len(plan.degrees_upper)}"
        )


def test_position_bars_in_range(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-07: every position bar is in 1..bar_span."""
    plans, _, _, _, _ = phrase_plans_result
    for plan in plans:
        for pos in plan.degree_positions:
            assert 1 <= pos.bar <= plan.bar_span, (
                f"Position bar {pos.bar} not in range [1, {plan.bar_span}]"
            )


def test_position_beats_in_range(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-08: every position beat is in valid range for metre."""
    plans, gc, _, _, _ = phrase_plans_result
    max_b: int = _max_beat(gc.metre)
    for plan in plans:
        for pos in plan.degree_positions:
            assert 1 <= pos.beat <= max_b, (
                f"Position beat {pos.beat} not in range [1, {max_b}]"
            )


def test_positions_chronological(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-09: degree_positions are chronologically ordered."""
    plans, _, _, _, _ = phrase_plans_result
    for plan in plans:
        for i in range(len(plan.degree_positions) - 1):
            pos_a: BeatPosition = plan.degree_positions[i]
            pos_b: BeatPosition = plan.degree_positions[i + 1]
            assert (pos_a.bar, pos_a.beat) <= (pos_b.bar, pos_b.beat), (
                f"Positions not chronological: {pos_a} > {pos_b}"
            )


def test_bar_span_positive(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-10: bar_span is at least 1."""
    plans, _, _, _, _ = phrase_plans_result
    for plan in plans:
        assert plan.bar_span >= 1


def test_phrase_duration_consistent(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-11: phrase_duration equals bar_span times bar_length (adjusted for anacrusis)."""
    plans, _, _, _, _ = phrase_plans_result
    bar_len: Fraction = _bar_length(plans[0].metre)
    for plan in plans:
        if plan.anacrusis > 0:
            expected: Fraction = plan.anacrusis + (plan.bar_span - 1) * bar_len
        else:
            expected = plan.bar_span * bar_len
        assert plan.phrase_duration == expected, (
            f"phrase_duration {plan.phrase_duration} != expected {expected} "
            f"(bar_span={plan.bar_span}, bar_length={bar_len}, anacrusis={plan.anacrusis})"
        )


def test_phrases_tile_exactly(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-12: consecutive phrases tile exactly (or within tolerance for upbeat)."""
    plans, gc, _, _, _ = phrase_plans_result
    upbeat: Fraction = gc.upbeat if hasattr(gc, "upbeat") and gc.upbeat else Fraction(0)
    bar_len: Fraction = _bar_length(gc.metre)
    for i in range(len(plans) - 1):
        expected_next: Fraction = plans[i].start_offset + plans[i].phrase_duration
        diff: Fraction = abs(plans[i + 1].start_offset - expected_next)
        if upbeat > 0:
            assert diff <= bar_len, (
                f"Plan {i+1} start_offset {plans[i + 1].start_offset} "
                f"differs from expected {expected_next} by more than one bar"
            )
        else:
            assert plans[i + 1].start_offset == expected_next, (
                f"Plan {i+1} start_offset {plans[i + 1].start_offset} != "
                f"expected {expected_next}"
            )


def test_first_phrase_offset(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-13: first phrase starts at 0 or -upbeat."""
    plans, gc, _, _, _ = phrase_plans_result
    upbeat: Fraction = gc.upbeat if hasattr(gc, "upbeat") and gc.upbeat else Fraction(0)
    if plans[0].start_bar == 0:
        assert plans[0].start_offset <= Fraction(0), (
            f"Upbeat phrase start_offset {plans[0].start_offset} > 0"
        )
    else:
        assert plans[0].start_offset >= Fraction(0), (
            f"Non-upbeat phrase start_offset {plans[0].start_offset} < 0"
        )


def test_total_duration_matches_bars(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-14: sum of phrase durations approximately equals total_bars times bar_length."""
    plans, gc, _, total_bars, _ = phrase_plans_result
    total_duration: Fraction = sum(p.phrase_duration for p in plans)
    bar_len: Fraction = _bar_length(gc.metre)
    upbeat: Fraction = gc.upbeat if hasattr(gc, "upbeat") and gc.upbeat else Fraction(0)
    expected: Fraction = total_bars * bar_len
    tolerance: Fraction = bar_len * 2 if upbeat > 0 else bar_len
    assert abs(total_duration - expected) <= tolerance, (
        f"Total duration {total_duration} differs from expected {expected} "
        f"by more than {tolerance}"
    )


def test_prev_exit_upper_first_only_none(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-15: first plan has prev_exit_upper None."""
    plans, _, _, _, _ = phrase_plans_result
    assert plans[0].prev_exit_upper is None


def test_prev_exit_lower_first_only_none(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-16: first plan has prev_exit_lower None."""
    plans, _, _, _, _ = phrase_plans_result
    assert plans[0].prev_exit_lower is None


def test_cadential_flag_consistent(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-17: is_cadential matches schema position == cadential."""
    plans, _, schemas, _, _ = phrase_plans_result
    for plan in plans:
        schema_def = schemas[plan.schema_name]
        expected: bool = schema_def.position == CADENTIAL_POSITION
        assert plan.is_cadential == expected, (
            f"is_cadential {plan.is_cadential} != expected {expected} "
            f"for schema {plan.schema_name} with position {schema_def.position}"
        )


def test_cadence_type_consistent(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-18: cadence_type None implies not at section boundary OR not cadential."""
    plans, _, _, _, chain = phrase_plans_result
    for i, plan in enumerate(plans):
        if plan.cadence_type is not None:
            assert plan.is_cadential, (
                f"Non-cadential plan {plan.schema_name} has cadence_type {plan.cadence_type}"
            )
        at_section_end: bool = chain.cadences[i] is not None if i < len(chain.cadences) else False
        if plan.is_cadential and at_section_end:
            assert plan.cadence_type is not None, (
                f"Cadential plan {plan.schema_name} at section end has cadence_type None"
            )


def test_local_key_valid(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-19: local_key is a Key instance."""
    plans, _, _, _, _ = phrase_plans_result
    for plan in plans:
        assert isinstance(plan.local_key, Key), (
            f"local_key is not Key: {type(plan.local_key)}"
        )


def test_upper_range_valid(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-20: upper_range.low < upper_range.high."""
    plans, _, _, _, _ = phrase_plans_result
    for plan in plans:
        assert plan.upper_range.low < plan.upper_range.high


def test_lower_range_valid(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-21: lower_range.low < lower_range.high."""
    plans, _, _, _, _ = phrase_plans_result
    for plan in plans:
        assert plan.lower_range.low < plan.lower_range.high


def test_upper_median_in_range(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-22: upper_median within upper_range."""
    plans, _, _, _, _ = phrase_plans_result
    for plan in plans:
        assert plan.upper_range.low <= plan.upper_median <= plan.upper_range.high


def test_lower_median_in_range(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-23: lower_median within lower_range."""
    plans, _, _, _, _ = phrase_plans_result
    for plan in plans:
        assert plan.lower_range.low <= plan.lower_median <= plan.lower_range.high


def test_rhythm_profile_nonempty(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-24: rhythm_profile is non-empty."""
    plans, _, _, _, _ = phrase_plans_result
    for plan in plans:
        assert len(plan.rhythm_profile) > 0


def test_section_name_valid(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-25: section_name is a valid genre section name."""
    plans, gc, _, _, _ = phrase_plans_result
    valid_names: set[str] = {s["name"] for s in gc.sections}
    for plan in plans:
        assert plan.section_name in valid_names, (
            f"section_name '{plan.section_name}' not in {valid_names}"
        )


def test_start_bar_in_range(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-26: start_bar is in valid range."""
    plans, _, _, total_bars, _ = phrase_plans_result
    for plan in plans:
        assert 0 <= plan.start_bar <= total_bars, (
            f"start_bar {plan.start_bar} not in [0, {total_bars}]"
        )


def test_degree_keys_for_sequential(
    phrase_plans_result: tuple[tuple[PhrasePlan, ...], GenreConfig, dict[str, Any], int, SchemaChain],
) -> None:
    """P-27: all schemas have degree_keys; sequential have per-segment keys."""
    plans, _, schemas, _, _ = phrase_plans_result
    for plan in plans:
        schema_def = schemas[plan.schema_name]
        assert len(plan.degree_keys) > 0, (
            f"Schema '{plan.schema_name}' has empty degree_keys"
        )
        assert len(plan.degree_keys) == len(plan.degrees_upper), (
            f"degree_keys length {len(plan.degree_keys)} != "
            f"degrees_upper length {len(plan.degrees_upper)}"
        )
        if not schema_def.sequential:
            # Non-sequential: all degree_keys should be the same (local_key)
            assert all(dk == plan.local_key for dk in plan.degree_keys), (
                f"Non-sequential schema '{plan.schema_name}' has varying degree_keys"
            )
