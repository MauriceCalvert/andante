"""Tests for builder.realisation module.

Category A tests: Pure functions, specification-based.

Specification source: architecture.md Realisation section
- Anchors are converted directly to notes
- Duration extends from anchor to next anchor
- Lyrics added at anchor positions
"""
from fractions import Fraction

import pytest

from builder.realisation import (
    _bar_beat_to_offset,
    realise,
)
from builder.types import (
    Anchor, AffectConfig, FormConfig, GenreConfig, KeyConfig,
    MotiveWeights, Note, NoteFile,
)
from shared.key import Key


class TestBarBeatConversions:
    """Tests for bar.beat conversion functions."""

    def test_bar_beat_to_offset_1_1(self) -> None:
        assert _bar_beat_to_offset("1.1", beats_per_bar=4) == Fraction(0)

    def test_bar_beat_to_offset_1_3(self) -> None:
        assert _bar_beat_to_offset("1.3", beats_per_bar=4) == Fraction(1, 2)

    def test_bar_beat_to_offset_2_1(self) -> None:
        assert _bar_beat_to_offset("2.1", beats_per_bar=4) == Fraction(1)

    def test_bar_beat_to_offset_3_1(self) -> None:
        assert _bar_beat_to_offset("3.1", beats_per_bar=4) == Fraction(2)


class TestRealise:
    """Integration tests for realise function."""

    @pytest.fixture
    def c_major(self) -> Key:
        return Key("C", "major")

    @pytest.fixture
    def minimal_configs(self):
        """Minimal configuration for testing."""
        key_config = KeyConfig(
            name="C Major",
            pitch_class_set=frozenset({0, 2, 4, 5, 7, 9, 11}),
            bridge_pitch_set=frozenset({0, 2, 4, 7, 9}),
        )
        affect_config = AffectConfig(
            name="default",
            density="high",
            articulation="detached",
            tempo_modifier=5,
            tonal_path={"narratio": ("I", "V", "vi")},
            answer_interval=5,
            anacrusis=False,
            motive_weights=MotiveWeights(),
            direction_limit=4,
            density_minimum=0.75,
            rhythm_states={},
        )
        genre_config = GenreConfig(
            name="invention",
            voices=2,
            form="through_composed",
            metre="4/4",
            rhythmic_unit="1/16",
            sections=(),
            imitation="mandatory",
            treatment_sequence=(),
            rhythmic_vocabulary={"tempo_range": [72, 88]},
            subject_constraints={},
            tessitura={"soprano": 70, "bass": 48},
        )
        form_config = FormConfig(
            name="through_composed",
            bar_allocation={"exordium": (1, 4)},
            schema_allocation={},
            phrase_boundaries=(),
            minimum_bars=20,
        )
        return key_config, affect_config, genre_config, form_config

    def test_realise_produces_note_file(self, minimal_configs, c_major) -> None:
        """Realise returns valid NoteFile."""
        key_config, affect_config, genre_config, form_config = minimal_configs
        anchors = [
            Anchor("1.1", 1, 1, c_major, "test", 1),
            Anchor("1.3", 2, 2, c_major, "test", 2),
        ]
        result = realise(
            anchors,
            None,
            key_config,
            affect_config,
            genre_config,
            form_config,
        )
        assert isinstance(result, NoteFile)
        assert len(result.soprano) == 2
        assert len(result.bass) == 2
        assert result.bass[0].voice == 3

    def test_realise_sets_tempo(self, minimal_configs, c_major) -> None:
        """Realise applies tempo modifier."""
        key_config, affect_config, genre_config, form_config = minimal_configs
        anchors = [Anchor("1.1", 1, 1, c_major, "test", 1)]
        result = realise(
            anchors,
            None,
            key_config,
            affect_config,
            genre_config,
            form_config,
        )
        base_tempo = (72 + 88) // 2
        assert result.tempo == base_tempo + 5

    def test_realise_duration_to_next_anchor(self, minimal_configs, c_major) -> None:
        """Duration extends from anchor to next anchor."""
        key_config, affect_config, genre_config, form_config = minimal_configs
        anchors = [
            Anchor("1.1", 1, 1, c_major, "test", 1),
            Anchor("1.3", 2, 2, c_major, "test", 2),
            Anchor("2.1", 3, 3, c_major, "test", 3),
        ]
        result = realise(
            anchors,
            None,
            key_config,
            affect_config,
            genre_config,
            form_config,
        )
        assert result.soprano[0].duration == Fraction(1, 2)
        assert result.soprano[1].duration == Fraction(1, 2)
        assert result.soprano[2].duration == Fraction(19)

    def test_realise_adds_lyrics(self, minimal_configs, c_major) -> None:
        """Lyrics are added at anchor positions."""
        key_config, affect_config, genre_config, form_config = minimal_configs
        anchors = [Anchor("1.1", 1, 1, c_major, "do_re_mi", 1)]
        result = realise(
            anchors,
            None,
            key_config,
            affect_config,
            genre_config,
            form_config,
        )
        assert result.soprano[0].lyric == "do_re_mi"

    def test_realise_sorts_anchors(self, minimal_configs, c_major) -> None:
        """Anchors are sorted by time."""
        key_config, affect_config, genre_config, form_config = minimal_configs
        anchors = [
            Anchor("2.1", 3, 3, c_major, "test", 2),
            Anchor("1.1", 1, 1, c_major, "test", 1),
        ]
        result = realise(
            anchors,
            None,
            key_config,
            affect_config,
            genre_config,
            form_config,
        )
        # Degree 1 in C major at soprano median (70) -> C5 (72)
        # Degree 3 in C major -> E5 (76)
        assert result.soprano[0].offset < result.soprano[1].offset
