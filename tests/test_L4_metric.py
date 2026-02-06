"""L4 Metric layer contract tests."""
import pytest
from builder.config_loader import load_configs
from builder.types import Anchor
from planner.metric.layer import layer_4_metric
from planner.schematic import layer_3_schematic
from planner.tonal import layer_2_tonal
from shared.key import Key
from tests.conftest import GENRES


# TODO: L4-13, L4-14 (home key checks) deferred - requires reliable home key extraction
# TODO: L4-17, L4-18 (cadential degree checks) deferred - requires linking anchors to schema types


def _parse_bar_beat(bar_beat: str) -> tuple[int, int]:
    """Parse '3.1' to (bar=3, beat=1)."""
    parts = bar_beat.split(".")
    return int(parts[0]), int(parts[1])


@pytest.fixture(params=GENRES)
def metric_result(request):
    """Run L2+L3+L4 for each genre."""
    genre = request.param
    config = load_configs(genre=genre, key="c_major", affect="Zierlich")
    tonal_plan = layer_2_tonal(
        affect_config=config["affect"],
        genre_config=config["genre"],
        seed=42,
    )
    chain = layer_3_schematic(
        tonal_plan=tonal_plan,
        genre_config=config["genre"],
        form_config=config["form"],
        schemas=config["schemas"],
        seed=43,
    )
    bar_assignments, anchors, total_bars = layer_4_metric(
        schema_chain=chain,
        genre_config=config["genre"],
        form_config=config["form"],
        key_config=config["key"],
        schemas=config["schemas"],
        tonal_plan=tonal_plan,
    )
    return bar_assignments, anchors, total_bars, config["genre"], config["key"]


def test_bar_assignments_complete(metric_result):
    """L4-01: bar_assignments has entry for each genre section."""
    bar_assignments, _, _, genre_config, _ = metric_result
    for section in genre_config.sections:
        section_name = section["name"]
        assert section_name in bar_assignments, (
            f"Section '{section_name}' missing from bar_assignments"
        )


def test_bar_assignments_contiguous(metric_result):
    """L4-02: bar assignments are contiguous with no gaps."""
    bar_assignments, _, _, genre_config, _ = metric_result
    section_names = [s["name"] for s in genre_config.sections]
    ranges = [bar_assignments[name] for name in section_names]
    ranges_sorted = sorted(ranges, key=lambda r: r[0])
    assert ranges_sorted[0][0] == 1, "First section must start at bar 1"
    for i in range(len(ranges_sorted) - 1):
        _, end = ranges_sorted[i]
        next_start, _ = ranges_sorted[i + 1]
        assert next_start == end + 1, (
            f"Gap between ranges {ranges_sorted[i]} and {ranges_sorted[i + 1]}"
        )


def test_total_bars_positive(metric_result):
    """L4-03: total_bars is at least 1."""
    _, _, total_bars, _, _ = metric_result
    assert total_bars >= 1


def test_anchors_are_anchors(metric_result):
    """L4-04: every element is an Anchor instance."""
    _, anchors, _, _, _ = metric_result
    for i, a in enumerate(anchors):
        assert isinstance(a, Anchor), f"Element {i} is not an Anchor"


def test_anchor_count_minimum(metric_result):
    """L4-05: at least 2 anchors exist."""
    _, anchors, _, _, _ = metric_result
    assert len(anchors) >= 2


def test_anchors_sorted(metric_result):
    """L4-06: anchors are sorted by bar_beat."""
    _, anchors, _, _, _ = metric_result
    for i in range(len(anchors) - 1):
        bar_a, beat_a = _parse_bar_beat(anchors[i].bar_beat)
        bar_b, beat_b = _parse_bar_beat(anchors[i + 1].bar_beat)
        val_a = bar_a + beat_a / 10.0
        val_b = bar_b + beat_b / 10.0
        assert val_a <= val_b, (
            f"Anchors not sorted: {anchors[i].bar_beat} > {anchors[i + 1].bar_beat}"
        )


def test_anchors_no_duplicates(metric_result):
    """L4-07: no two anchors share the same bar_beat."""
    _, anchors, _, _, _ = metric_result
    bar_beats = [a.bar_beat for a in anchors]
    assert len(bar_beats) == len(set(bar_beats)), "Duplicate bar_beat values found"


def test_upper_degrees_valid(metric_result):
    """L4-08: every upper_degree is in range 1-7."""
    _, anchors, _, _, _ = metric_result
    for a in anchors:
        assert 1 <= a.upper_degree <= 7, (
            f"Invalid upper_degree {a.upper_degree} at {a.bar_beat}"
        )


def test_lower_degrees_valid(metric_result):
    """L4-09: every lower_degree is in range 1-7."""
    _, anchors, _, _, _ = metric_result
    for a in anchors:
        assert 1 <= a.lower_degree <= 7, (
            f"Invalid lower_degree {a.lower_degree} at {a.bar_beat}"
        )


def test_local_keys_valid(metric_result):
    """L4-10: every local_key is a Key instance."""
    _, anchors, _, _, _ = metric_result
    for a in anchors:
        assert isinstance(a.local_key, Key), (
            f"Invalid local_key type at {a.bar_beat}"
        )


def test_first_anchor_tonic(metric_result):
    """L4-11: first anchor has upper_degree=1 and lower_degree=1."""
    _, anchors, _, _, _ = metric_result
    assert anchors[0].upper_degree == 1, (
        f"First anchor upper_degree is {anchors[0].upper_degree}, expected 1"
    )
    assert anchors[0].lower_degree == 1, (
        f"First anchor lower_degree is {anchors[0].lower_degree}, expected 1"
    )


def test_last_anchor_tonic(metric_result):
    """L4-12: last anchor has upper_degree=1 and lower_degree=1."""
    _, anchors, _, _, _ = metric_result
    assert anchors[-1].upper_degree == 1, (
        f"Last anchor upper_degree is {anchors[-1].upper_degree}, expected 1"
    )
    assert anchors[-1].lower_degree == 1, (
        f"Last anchor lower_degree is {anchors[-1].lower_degree}, expected 1"
    )


def test_bar_numbers_in_range(metric_result):
    """L4-15: bar numbers are within [0, total_bars]."""
    _, anchors, total_bars, _, _ = metric_result
    for a in anchors:
        bar, _ = _parse_bar_beat(a.bar_beat)
        assert 0 <= bar <= total_bars, (
            f"Bar {bar} out of range [0, {total_bars}] at {a.bar_beat}"
        )


def test_beat_numbers_valid(metric_result):
    """L4-16: beat numbers are at least 1."""
    _, anchors, _, _, _ = metric_result
    for a in anchors:
        _, beat = _parse_bar_beat(a.bar_beat)
        assert beat >= 1, f"Beat {beat} < 1 at {a.bar_beat}"
