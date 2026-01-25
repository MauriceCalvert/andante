"""Tests for builder.realisation module.

Category A tests: Pure functions, specification-based.

Specification source: architecture.md Realisation section
- Schema arrivals placed at designated strong beats
- Decoration fills weak beats
- Rhythm state machine controls density
- Lyrics added at anchor positions
"""
from fractions import Fraction

import pytest

from builder.realisation import (
    _bar_beat_to_slot,
    _bar_beat_to_offset,
    _merge_repeated_pitches,
    _add_lyrics,
    generate_free_passage,
    generate_countersubject,
    realise,
)
from builder.types import (
    Anchor, AffectConfig, FormConfig, GenreConfig, KeyConfig,
    MotiveWeights, Note, NoteFile, Solution,
)


class TestBarBeatConversions:
    """Tests for bar.beat conversion functions."""

    def test_bar_beat_to_slot_1_1(self) -> None:
        assert _bar_beat_to_slot("1.1") == 0

    def test_bar_beat_to_slot_1_3(self) -> None:
        assert _bar_beat_to_slot("1.3") == 8

    def test_bar_beat_to_slot_2_1(self) -> None:
        assert _bar_beat_to_slot("2.1") == 16

    def test_bar_beat_to_offset_1_1(self) -> None:
        assert _bar_beat_to_offset("1.1") == Fraction(0)

    def test_bar_beat_to_offset_1_3(self) -> None:
        assert _bar_beat_to_offset("1.3") == Fraction(1, 2)

    def test_bar_beat_to_offset_2_1(self) -> None:
        assert _bar_beat_to_offset("2.1") == Fraction(1)


class TestMergeRepeatedPitches:
    """Tests for _merge_repeated_pitches function."""

    def test_empty_list(self) -> None:
        assert _merge_repeated_pitches([]) == []

    def test_single_note(self) -> None:
        notes = [Note(Fraction(0), 60, Fraction(1, 16), 0)]
        result = _merge_repeated_pitches(notes)
        assert len(result) == 1
        assert result[0].duration == Fraction(1, 16)

    def test_two_same_pitches_merge(self) -> None:
        notes = [
            Note(Fraction(0), 60, Fraction(1, 16), 0),
            Note(Fraction(1, 16), 60, Fraction(1, 16), 0),
        ]
        result = _merge_repeated_pitches(notes)
        assert len(result) == 1
        assert result[0].pitch == 60
        assert result[0].duration == Fraction(1, 8)
        assert result[0].offset == Fraction(0)

    def test_different_pitches_no_merge(self) -> None:
        notes = [
            Note(Fraction(0), 60, Fraction(1, 16), 0),
            Note(Fraction(1, 16), 62, Fraction(1, 16), 0),
        ]
        result = _merge_repeated_pitches(notes)
        assert len(result) == 2

    def test_three_same_pitches_merge(self) -> None:
        notes = [
            Note(Fraction(0), 60, Fraction(1, 16), 0),
            Note(Fraction(1, 16), 60, Fraction(1, 16), 0),
            Note(Fraction(2, 16), 60, Fraction(1, 16), 0),
        ]
        result = _merge_repeated_pitches(notes)
        assert len(result) == 1
        assert result[0].duration == Fraction(3, 16)


class TestAddLyrics:
    """Tests for _add_lyrics function."""

    def test_empty_notes(self) -> None:
        result = _add_lyrics([], [])
        assert result == []

    def test_no_matching_anchors(self) -> None:
        notes = [Note(Fraction(0), 60, Fraction(1, 4), 0)]
        anchors = [Anchor("2.1", 64, 48, "do_re_mi", 1)]
        result = _add_lyrics(notes, anchors)
        assert result[0].lyric == ""

    def test_matching_anchor_adds_lyric(self) -> None:
        notes = [Note(Fraction(0), 60, Fraction(1, 4), 0)]
        anchors = [Anchor("1.1", 60, 48, "do_re_mi", 1)]
        result = _add_lyrics(notes, anchors)
        assert result[0].lyric == "do_re_mi_1"


class TestGenerateFreePassage:
    """Tests for generate_free_passage function."""

    def test_basic_passage(self) -> None:
        soprano, bass = generate_free_passage(
            exit_pitch=(64, 48),
            entry_pitch=(67, 55),
            duration_beats=2,
            bridge_pitch_set=frozenset({0, 2, 4, 7, 9}),
            metre="4/4",
        )
        assert len(soprano) > 0
        assert len(bass) > 0

    def test_passage_respects_bridge_set(self) -> None:
        bridge_set = frozenset({0, 2, 4, 7, 9})
        soprano, bass = generate_free_passage(
            exit_pitch=(64, 48),
            entry_pitch=(67, 55),
            duration_beats=2,
            bridge_pitch_set=bridge_set,
            metre="4/4",
        )
        for note in soprano:
            assert note.pitch % 12 in bridge_set
        for note in bass:
            assert note.pitch % 12 in bridge_set

    def test_passage_has_correct_duration(self) -> None:
        soprano, bass = generate_free_passage(
            exit_pitch=(64, 48),
            entry_pitch=(67, 55),
            duration_beats=4,
            bridge_pitch_set=frozenset({0, 2, 4, 7, 9}),
            metre="4/4",
        )
        expected_slots = 4 * 4
        assert len(soprano) == expected_slots


class TestGenerateCountersubject:
    """Tests for generate_countersubject function."""

    def test_empty_subject(self) -> None:
        result = generate_countersubject([], 7)
        assert result == []

    def test_contrary_motion(self) -> None:
        subject = [
            Note(Fraction(0), 60, Fraction(1, 8), 1),
            Note(Fraction(1, 8), 62, Fraction(1, 8), 1),
            Note(Fraction(1, 4), 64, Fraction(1, 8), 1),
        ]
        cs = generate_countersubject(subject, 0)
        assert len(cs) == 3
        if cs[0].pitch > cs[1].pitch:
            assert cs[1].pitch > cs[2].pitch or cs[1].pitch == cs[2].pitch

    def test_transposition_applied(self) -> None:
        subject = [Note(Fraction(0), 60, Fraction(1, 4), 1)]
        cs_0 = generate_countersubject(subject, 0)
        cs_7 = generate_countersubject(subject, 7)
        assert cs_7[0].pitch - cs_0[0].pitch == 7


class TestRealise:
    """Integration tests for realise function."""

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
            primary_value="1/16",
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

    def test_realise_produces_note_file(self, minimal_configs) -> None:
        """Realise returns valid NoteFile."""
        key_config, affect_config, genre_config, form_config = minimal_configs
        solution = Solution(
            soprano_pitches=tuple([60] * 32),
            bass_pitches=tuple([48] * 32),
            soprano_durations=tuple([Fraction(1, 16)] * 32),
            bass_durations=tuple([Fraction(1, 16)] * 32),
            cost=0.0,
        )
        anchors = [Anchor("1.1", 60, 48, "test", 1)]
        result = realise(
            solution,
            None,  # texture (now optional)
            anchors,
            key_config,
            affect_config,
            genre_config,
            form_config,
        )
        assert isinstance(result, NoteFile)
        assert len(result.soprano) > 0
        assert len(result.bass) > 0

    def test_realise_sets_tempo(self, minimal_configs) -> None:
        """Realise applies tempo modifier."""
        key_config, affect_config, genre_config, form_config = minimal_configs
        solution = Solution(
            soprano_pitches=tuple([60] * 32),
            bass_pitches=tuple([48] * 32),
            soprano_durations=tuple([Fraction(1, 16)] * 32),
            bass_durations=tuple([Fraction(1, 16)] * 32),
            cost=0.0,
        )
        result = realise(
            solution,
            None,  # texture (now optional)
            [],
            key_config,
            affect_config,
            genre_config,
            form_config,
        )
        base_tempo = (72 + 88) // 2
        assert result.tempo == base_tempo + 5
