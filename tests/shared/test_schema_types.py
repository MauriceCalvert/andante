"""Tests for shared/schema_types.py — Schema and Arrival dataclasses."""
from shared.schema_types import Arrival, Schema


def _make_schema(**overrides) -> Schema:
    """Create a Schema with sensible defaults, overridden as needed."""
    defaults: dict = dict(
        name="test_schema",
        soprano_degrees=(1, 3, 5),
        soprano_directions=(None, "up", "up"),
        bass_degrees=(1, 5, 1),
        bass_directions=(None, "down", "same"),
        entry=Arrival(soprano=1, bass=1),
        exit=Arrival(soprano=5, bass=1),
        min_bars=2,
        max_bars=4,
        position="opening",
        cadence_type=None,
        sequential=False,
        segments=(1,),
        direction=None,
        segment_direction=None,
        pedal=None,
        chromatic=False,
        figuration_profile="default",
        cadence_approach=False,
        typical_keys=None,
        harmony=None,
    )
    defaults.update(overrides)
    return Schema(**defaults)


class TestArrival:
    def test_frozen(self) -> None:
        a: Arrival = Arrival(soprano=1, bass=5)
        assert a.soprano == 1
        assert a.bass == 5

    def test_equality(self) -> None:
        a: Arrival = Arrival(soprano=3, bass=1)
        b: Arrival = Arrival(soprano=3, bass=1)
        assert a == b


class TestSchema:
    def test_stage_count_non_sequential(self) -> None:
        s: Schema = _make_schema(
            soprano_degrees=(1, 3, 5),
            sequential=False,
            segments=(1,),
        )
        assert s.stage_count == 3

    def test_stage_count_sequential(self) -> None:
        s: Schema = _make_schema(
            soprano_degrees=(1, 5),
            sequential=True,
            segments=(2, 3),
        )
        # base=2 * max(segments)=3 = 6
        assert s.stage_count == 6

    def test_backward_compat_bars(self) -> None:
        s: Schema = _make_schema(min_bars=2, max_bars=4)
        assert s.bars_min == 2
        assert s.bars_max == 4

    def test_backward_compat_entry_exit(self) -> None:
        s: Schema = _make_schema(
            entry=Arrival(soprano=3, bass=1),
            exit=Arrival(soprano=5, bass=5),
        )
        assert s.entry_soprano == 3
        assert s.entry_bass == 1
        assert s.exit_soprano == 5
        assert s.exit_bass == 5

    def test_frozen(self) -> None:
        s: Schema = _make_schema()
        assert s.name == "test_schema"
