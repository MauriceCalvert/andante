"""100% coverage tests for engine.metrics.

Tests import only:
- engine.metrics (module under test)
- engine.types (ExpandedPhrase, PieceMetrics)
- shared (types used by ExpandedPhrase)
- stdlib

Note: ExpandedPhrase doesn't have treatment/bars fields directly.
compute_metrics uses hasattr() to access these if present, otherwise
calculates bars from soprano durations and defaults treatment to "statement".
We test by creating a custom object that mimics the expected interface.
"""
from dataclasses import dataclass
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote
from shared.types import VoiceMaterial, ExpandedVoices

from engine.metrics import (
    SUBJECT_TREATMENTS,
    DERIVED_TREATMENTS,
    EPISODE_TYPES,
    BASS_LEAD_EPISODES,
    compute_metrics,
)
from engine.engine_types import PieceMetrics


@dataclass
class MockExpandedPhrase:
    """Mock ExpandedPhrase with treatment and bars attributes for testing.

    compute_metrics accesses:
    - bars (or calculates from soprano_durations)
    - treatment (defaults to "statement" if missing)
    - episode_type
    - soprano_durations (property)
    """
    bars: int
    treatment: str
    episode_type: str | None
    soprano_durations: tuple[Fraction, ...]


def _make_phrase(
    bars: int,
    treatment: str = "statement",
    episode_type: str | None = None,
) -> MockExpandedPhrase:
    """Helper to create mock phrase for testing."""
    return MockExpandedPhrase(
        bars=bars,
        treatment=treatment,
        episode_type=episode_type,
        soprano_durations=tuple(Fraction(1) for _ in range(bars)),
    )


class TestConstants:
    """Test treatment/episode category constants."""

    def test_subject_treatments_contains_statement(self) -> None:
        """Statement is a subject treatment."""
        assert "statement" in SUBJECT_TREATMENTS

    def test_subject_treatments_contains_imitation(self) -> None:
        """Imitation is a subject treatment."""
        assert "imitation" in SUBJECT_TREATMENTS

    def test_subject_treatments_contains_inversion(self) -> None:
        """Inversion is a subject treatment."""
        assert "inversion" in SUBJECT_TREATMENTS

    def test_subject_treatments_contains_stretto(self) -> None:
        """Stretto is a subject treatment."""
        assert "stretto" in SUBJECT_TREATMENTS

    def test_subject_treatments_contains_repose(self) -> None:
        """Repose is a subject treatment."""
        assert "repose" in SUBJECT_TREATMENTS

    def test_derived_treatments_contains_fragmentation(self) -> None:
        """Fragmentation is a derived treatment."""
        assert "fragmentation" in DERIVED_TREATMENTS

    def test_derived_treatments_contains_diminution(self) -> None:
        """Diminution is a derived treatment."""
        assert "diminution" in DERIVED_TREATMENTS

    def test_episode_types_contains_scalar(self) -> None:
        """Scalar is an episode type."""
        assert "scalar" in EPISODE_TYPES

    def test_episode_types_contains_arpeggiated(self) -> None:
        """Arpeggiated is an episode type."""
        assert "arpeggiated" in EPISODE_TYPES

    def test_bass_lead_episodes_contains_bass_statement(self) -> None:
        """Bass statement is a bass-lead episode."""
        assert "bass_statement" in BASS_LEAD_EPISODES


class TestComputeMetrics:
    """Test compute_metrics function."""

    def test_all_subject_treatments(self) -> None:
        """Phrases with subject treatments count as subject_bars."""
        phrases = [
            _make_phrase(4, treatment="statement"),
            _make_phrase(4, treatment="imitation"),
        ]
        metrics = compute_metrics(phrases, bar_duration=Fraction(1))
        assert metrics.total_bars == 8
        assert metrics.subject_bars == 8
        assert metrics.derived_bars == 0
        assert metrics.episode_bars == 0
        assert metrics.free_bars == 0

    def test_all_derived_treatments(self) -> None:
        """Phrases with derived treatments count as derived_bars."""
        phrases = [
            _make_phrase(2, treatment="fragmentation"),
            _make_phrase(2, treatment="diminution"),
        ]
        metrics = compute_metrics(phrases, bar_duration=Fraction(1))
        assert metrics.total_bars == 4
        assert metrics.subject_bars == 0
        assert metrics.derived_bars == 4
        assert metrics.episode_bars == 0
        assert metrics.free_bars == 0

    def test_episode_type_overrides_treatment(self) -> None:
        """Episode type takes priority over treatment for categorization."""
        phrases = [
            _make_phrase(4, treatment="statement", episode_type="scalar"),
        ]
        metrics = compute_metrics(phrases, bar_duration=Fraction(1))
        # Even though treatment is "statement", episode_type="scalar" makes it episode_bars
        assert metrics.episode_bars == 4
        assert metrics.subject_bars == 0

    def test_free_bars_for_unknown_treatment(self) -> None:
        """Unknown treatments count as free_bars."""
        phrases = [
            _make_phrase(3, treatment="transition"),
        ]
        metrics = compute_metrics(phrases, bar_duration=Fraction(1))
        assert metrics.free_bars == 3
        assert metrics.subject_bars == 0
        assert metrics.derived_bars == 0

    def test_mixed_categories(self) -> None:
        """Mixed phrase types are categorized correctly."""
        phrases = [
            _make_phrase(4, treatment="statement"),  # subject
            _make_phrase(2, treatment="fragmentation"),  # derived
            _make_phrase(2, treatment="statement", episode_type="arpeggiated"),  # episode
            _make_phrase(1, treatment="cadence"),  # free
        ]
        metrics = compute_metrics(phrases, bar_duration=Fraction(1))
        assert metrics.total_bars == 9
        assert metrics.subject_bars == 4
        assert metrics.derived_bars == 2
        assert metrics.episode_bars == 2
        assert metrics.free_bars == 1

    def test_empty_phrases(self) -> None:
        """Empty phrase list returns zero metrics."""
        metrics = compute_metrics([], bar_duration=Fraction(1))
        assert metrics.total_bars == 0
        assert metrics.subject_bars == 0
        assert metrics.thematic_ratio == 0.0
        assert metrics.variety_ratio == 0.0

    def test_thematic_ratio_calculation(self) -> None:
        """Thematic ratio = (subject + derived) / total."""
        phrases = [
            _make_phrase(6, treatment="statement"),  # subject
            _make_phrase(2, treatment="fragmentation"),  # derived
            _make_phrase(2, treatment="transition"),  # free
        ]
        metrics = compute_metrics(phrases, bar_duration=Fraction(1))
        # thematic = 6 + 2 = 8, total = 10
        assert metrics.thematic_ratio == 0.8

    def test_variety_ratio_calculation(self) -> None:
        """Variety ratio = (derived + episode + free) / total."""
        phrases = [
            _make_phrase(4, treatment="statement"),  # subject
            _make_phrase(2, treatment="diminution"),  # derived
            _make_phrase(2, episode_type="scalar"),  # episode
            _make_phrase(2, treatment="cadence"),  # free
        ]
        metrics = compute_metrics(phrases, bar_duration=Fraction(1))
        # variety = 2 + 2 + 2 = 6, total = 10
        assert metrics.variety_ratio == 0.6

    def test_augmentation_is_subject(self) -> None:
        """Augmentation is a subject treatment."""
        phrases = [_make_phrase(8, treatment="augmentation")]
        metrics = compute_metrics(phrases, bar_duration=Fraction(1))
        assert metrics.subject_bars == 8

    def test_retrograde_is_subject(self) -> None:
        """Retrograde is a subject treatment."""
        phrases = [_make_phrase(4, treatment="retrograde")]
        metrics = compute_metrics(phrases, bar_duration=Fraction(1))
        assert metrics.subject_bars == 4

    def test_sequence_is_subject(self) -> None:
        """Sequence is a subject treatment (thematic development)."""
        phrases = [_make_phrase(4, treatment="sequence")]
        metrics = compute_metrics(phrases, bar_duration=Fraction(1))
        assert metrics.subject_bars == 4

    def test_cadenza_is_episode(self) -> None:
        """Cadenza is an episode type."""
        phrases = [_make_phrase(4, episode_type="cadenza")]
        metrics = compute_metrics(phrases, bar_duration=Fraction(1))
        assert metrics.episode_bars == 4

    def test_turbulent_is_episode(self) -> None:
        """Turbulent is an episode type."""
        phrases = [_make_phrase(2, episode_type="turbulent")]
        metrics = compute_metrics(phrases, bar_duration=Fraction(1))
        assert metrics.episode_bars == 2

    def test_head_sequence_is_derived(self) -> None:
        """Head sequence is a derived treatment."""
        phrases = [_make_phrase(3, treatment="head_sequence")]
        metrics = compute_metrics(phrases, bar_duration=Fraction(1))
        assert metrics.derived_bars == 3

    def test_tail_development_is_derived(self) -> None:
        """Tail development is a derived treatment."""
        phrases = [_make_phrase(3, treatment="tail_development")]
        metrics = compute_metrics(phrases, bar_duration=Fraction(1))
        assert metrics.derived_bars == 3


class TestComputeMetricsFallbacks:
    """Test compute_metrics fallback behavior for missing attributes."""

    def test_bars_calculated_from_durations(self) -> None:
        """When bars attribute missing, calculated from soprano_durations."""
        @dataclass
        class PhraseWithoutBars:
            treatment: str
            episode_type: str | None
            soprano_durations: tuple[Fraction, ...]

        # 4 quarter notes = 1 bar (bar_duration=1)
        phrase = PhraseWithoutBars(
            treatment="statement",
            episode_type=None,
            soprano_durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
        )
        metrics = compute_metrics([phrase], bar_duration=Fraction(1))
        assert metrics.total_bars == 1

    def test_treatment_defaults_to_statement(self) -> None:
        """When treatment attribute missing, defaults to 'statement'."""
        @dataclass
        class PhraseWithoutTreatment:
            bars: int
            episode_type: str | None
            soprano_durations: tuple[Fraction, ...]

        phrase = PhraseWithoutTreatment(
            bars=4,
            episode_type=None,
            soprano_durations=(Fraction(1),) * 4,
        )
        metrics = compute_metrics([phrase], bar_duration=Fraction(1))
        # Default "statement" is a subject treatment
        assert metrics.subject_bars == 4


class TestPieceMetricsIntegration:
    """Integration tests for metrics in typical musical contexts."""

    def test_typical_fugue_proportions(self) -> None:
        """A typical fugue has high thematic ratio (0.6-0.8)."""
        phrases = [
            _make_phrase(4, treatment="statement"),
            _make_phrase(4, treatment="imitation"),
            _make_phrase(4, treatment="stretto"),
            _make_phrase(2, episode_type="scalar"),
            _make_phrase(4, treatment="inversion"),
            _make_phrase(2, treatment="cadence"),
        ]
        metrics = compute_metrics(phrases, bar_duration=Fraction(1))
        # Subject bars: 4+4+4+4 = 16
        # Episode bars: 2
        # Free bars: 2
        # Total: 20
        # Thematic: 16/20 = 0.8
        assert 0.6 <= metrics.thematic_ratio <= 0.9

    def test_fantasia_proportions(self) -> None:
        """A fantasia has more episodic content."""
        phrases = [
            _make_phrase(2, treatment="statement"),
            _make_phrase(4, episode_type="scalar"),
            _make_phrase(4, episode_type="arpeggiated"),
            _make_phrase(2, treatment="imitation"),
            _make_phrase(4, episode_type="cadenza"),
        ]
        metrics = compute_metrics(phrases, bar_duration=Fraction(1))
        # Subject: 2+2 = 4
        # Episode: 4+4+4 = 12
        # Total: 16
        # Episode ratio: 12/16 = 0.75
        assert metrics.episode_bars >= metrics.subject_bars
