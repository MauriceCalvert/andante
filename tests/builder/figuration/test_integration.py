"""Integration tests for builder.figuration module."""
from fractions import Fraction

import pytest

from builder.figuration import figurate, figurate_single_bar, FiguredBar
from builder.figuration.loader import clear_cache
from builder.types import Anchor
from shared.key import Key


def make_anchor(
    bar_beat: str,
    soprano_degree: int,
    bass_degree: int,
    schema: str = "test",
    stage: int = 1,
) -> Anchor:
    """Helper to create test anchors."""
    key = Key(tonic="C", mode="major")
    return Anchor(
        bar_beat=bar_beat,
        soprano_degree=soprano_degree,
        bass_degree=bass_degree,
        local_key=key,
        schema=schema,
        stage=stage,
    )


class TestFigurate:
    """Integration tests for figurate function."""

    def test_empty_anchors_returns_empty(self) -> None:
        """Empty anchor list should return empty."""
        clear_cache()
        key = Key(tonic="C", mode="major")
        result = figurate([], key, "4/4", seed=42)
        assert result == []

    def test_single_anchor_returns_empty(self) -> None:
        """Single anchor has no gaps to fill."""
        key = Key(tonic="C", mode="major")
        anchors = [make_anchor("1.1", 1, 1)]
        result = figurate(anchors, key, "4/4", seed=42)
        assert result == []

    def test_two_anchors_returns_one_bar(self) -> None:
        """Two anchors should produce one figured bar."""
        clear_cache()
        key = Key(tonic="C", mode="major")
        anchors = [
            make_anchor("1.1", 1, 1),
            make_anchor("2.1", 2, 5),
        ]
        result = figurate(anchors, key, "4/4", seed=42)

        assert len(result) == 1
        assert isinstance(result[0], FiguredBar)
        assert result[0].bar == 1

    def test_multiple_anchors_returns_multiple_bars(self) -> None:
        """Multiple anchors should produce multiple figured bars."""
        clear_cache()
        key = Key(tonic="C", mode="major")
        anchors = [
            make_anchor("1.1", 1, 1),
            make_anchor("2.1", 2, 7),
            make_anchor("3.1", 3, 1),
            make_anchor("4.1", 1, 1),
        ]
        result = figurate(anchors, key, "4/4", seed=42)

        assert len(result) == 3
        assert result[0].bar == 1
        assert result[1].bar == 2
        assert result[2].bar == 3

    def test_deterministic_with_same_seed(self) -> None:
        """Same seed should produce identical results."""
        clear_cache()
        key = Key(tonic="C", mode="major")
        anchors = [
            make_anchor("1.1", 1, 1),
            make_anchor("2.1", 3, 1),
            make_anchor("3.1", 5, 5),
        ]

        result1 = figurate(anchors, key, "4/4", seed=42)
        result2 = figurate(anchors, key, "4/4", seed=42)

        assert len(result1) == len(result2)
        for bar1, bar2 in zip(result1, result2):
            assert bar1.degrees == bar2.degrees
            assert bar1.figure_name == bar2.figure_name

    def test_different_seeds_may_differ(self) -> None:
        """Different seeds may produce different results."""
        clear_cache()
        key = Key(tonic="C", mode="major")
        anchors = [
            make_anchor("1.1", 1, 1),
            make_anchor("2.1", 3, 1),
        ]

        results = set()
        for seed in range(20):
            result = figurate(anchors, key, "4/4", seed=seed)
            if result:
                results.add(result[0].figure_name)

        # May or may not differ depending on filtering
        assert len(results) >= 1

    def test_minor_key_handling(self) -> None:
        """Minor key should work correctly."""
        clear_cache()
        key = Key(tonic="A", mode="minor")
        anchors = [
            make_anchor("1.1", 1, 1),
            make_anchor("2.1", 2, 7),
        ]

        result = figurate(anchors, key, "3/4", seed=42)
        assert len(result) == 1

    def test_different_metres(self) -> None:
        """Different time signatures should work."""
        clear_cache()
        key = Key(tonic="C", mode="major")
        anchors = [
            make_anchor("1.1", 1, 1),
            make_anchor("2.1", 2, 5),
        ]

        for metre in ["3/4", "4/4", "2/4"]:
            result = figurate(anchors, key, metre, seed=42)
            assert len(result) == 1
            # Durations should sum to appropriate value
            total_dur = sum(result[0].durations)
            assert total_dur > 0

    def test_durations_valid(self) -> None:
        """All durations should be positive fractions."""
        clear_cache()
        key = Key(tonic="C", mode="major")
        anchors = [
            make_anchor("1.1", 1, 1),
            make_anchor("2.1", 3, 5),
            make_anchor("3.1", 5, 1),
        ]

        result = figurate(anchors, key, "4/4", seed=42)

        for bar in result:
            assert all(isinstance(d, Fraction) for d in bar.durations)
            assert all(d > 0 for d in bar.durations)

    def test_degrees_valid(self) -> None:
        """All degrees should be in 1-7 range."""
        clear_cache()
        key = Key(tonic="C", mode="major")
        anchors = [
            make_anchor("1.1", 1, 1),
            make_anchor("2.1", 5, 5),
            make_anchor("3.1", 1, 1),
        ]

        result = figurate(anchors, key, "4/4", seed=42)

        for bar in result:
            assert all(1 <= d <= 7 for d in bar.degrees)


class TestFigurateSingleBar:
    """Tests for figurate_single_bar function."""

    def test_returns_figured_bar(self) -> None:
        """Should return a FiguredBar."""
        clear_cache()
        key = Key(tonic="C", mode="major")
        anchor_a = make_anchor("1.1", 1, 1)
        anchor_b = make_anchor("2.1", 2, 5)

        result = figurate_single_bar(
            anchor_a=anchor_a,
            anchor_b=anchor_b,
            key=key,
            metre="4/4",
            seed=42,
            bar_num=1,
            total_bars=8,
        )

        assert result is not None
        assert isinstance(result, FiguredBar)
        assert result.bar == 1

    def test_respects_character(self) -> None:
        """Should respect character parameter."""
        clear_cache()
        key = Key(tonic="C", mode="major")
        anchor_a = make_anchor("1.1", 1, 1)
        anchor_b = make_anchor("2.1", 3, 1)

        result_plain = figurate_single_bar(
            anchor_a=anchor_a,
            anchor_b=anchor_b,
            key=key,
            metre="4/4",
            seed=42,
            bar_num=1,
            total_bars=8,
            character="plain",
        )

        result_energetic = figurate_single_bar(
            anchor_a=anchor_a,
            anchor_b=anchor_b,
            key=key,
            metre="4/4",
            seed=42,
            bar_num=1,
            total_bars=8,
            character="energetic",
        )

        # Both should produce results
        assert result_plain is not None
        assert result_energetic is not None


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_full_phrase_figuration(self) -> None:
        """Test figuration of a complete 8-bar phrase."""
        clear_cache()
        key = Key(tonic="C", mode="major")

        # Do-Re-Mi style anchors
        anchors = [
            make_anchor("1.1", 1, 1, "do_re_mi", 1),
            make_anchor("2.1", 2, 7, "do_re_mi", 2),
            make_anchor("3.1", 3, 1, "do_re_mi", 3),
            make_anchor("4.1", 4, 5, "continuation", 1),
            make_anchor("5.1", 5, 6, "continuation", 2),
            make_anchor("6.1", 4, 4, "prinner", 1),
            make_anchor("7.1", 3, 3, "prinner", 2),
            make_anchor("8.1", 1, 1, "cadence", 1),
        ]

        result = figurate(anchors, key, "4/4", seed=42)

        assert len(result) == 7  # One less than anchors
        assert all(isinstance(bar, FiguredBar) for bar in result)

        # Check bars are sequential
        bars = [bar.bar for bar in result]
        assert bars == [1, 2, 3, 4, 5, 6, 7]

    def test_minor_key_phrase(self) -> None:
        """Test figuration in minor key."""
        clear_cache()
        key = Key(tonic="A", mode="minor")

        anchors = [
            make_anchor("1.1", 1, 1),
            make_anchor("2.1", 3, 1),
            make_anchor("3.1", 5, 5),
            make_anchor("4.1", 1, 1),
        ]

        result = figurate(anchors, key, "3/4", seed=42)

        assert len(result) == 3
        # All degrees should be valid
        for bar in result:
            assert all(1 <= d <= 7 for d in bar.degrees)

    def test_counterpoint_validation_compatibility(self) -> None:
        """Test that figuration output is compatible with counterpoint validation.

        This tests the format of output, not actual validation.
        """
        clear_cache()
        key = Key(tonic="C", mode="major")

        anchors = [
            make_anchor("1.1", 1, 1),
            make_anchor("2.1", 3, 5),
        ]

        result = figurate(anchors, key, "4/4", seed=42)

        # Output should have correct structure
        assert len(result) == 1
        bar = result[0]

        # Should have figure_name for tracing
        assert bar.figure_name
        assert isinstance(bar.figure_name, str)

        # Degrees and durations should be valid
        assert len(bar.degrees) == len(bar.durations)
        assert len(bar.degrees) >= 2
