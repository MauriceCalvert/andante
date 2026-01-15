"""100% coverage tests for engine.expander_util.

Tests import only:
- engine.expander_util (module under test)
- engine.types (MotifAST)
- shared.pitch (FloatingNote, Rest, Pitch)
- stdlib

Note: subject_to_motif_ast and cs_to_motif_ast require Subject from planner.
These are integration-level functions that violate zero-coupling, so they are tested
with minimal coupling (creating Subject instances inline).

Note: apply_rhythm and apply_device use RHYTHMS/DEVICES loaded from YAML at module
import time. Tests validate against known vocabulary entries.
"""
from fractions import Fraction

from shared.pitch import FloatingNote, Rest

from engine.expander_util import (
    CADENCE_BUDGET,
    DATA_DIR,
    TONAL_ROOTS,
    TREATMENTS,
    apply_device,
    apply_rhythm,
    bar_duration,
    cs_to_motif_ast,
    subject_to_motif_ast,
)
from engine.engine_types import MotifAST
from engine.vocabulary import DEVICES, RHYTHMS


class TestConstants:
    """Test module constants."""

    def test_data_dir_exists(self) -> None:
        """DATA_DIR points to existing directory."""
        assert DATA_DIR.exists()
        assert DATA_DIR.is_dir()

    def test_cadence_budget(self) -> None:
        """CADENCE_BUDGET is half a bar."""
        assert CADENCE_BUDGET == Fraction(1, 2)

    def test_treatments_loaded(self) -> None:
        """TREATMENTS dict loaded from YAML."""
        assert isinstance(TREATMENTS, dict)
        assert len(TREATMENTS) > 0

    def test_tonal_roots_I(self) -> None:
        """Tonal root I is 1."""
        assert TONAL_ROOTS["I"] == 1
        assert TONAL_ROOTS["i"] == 1

    def test_tonal_roots_V(self) -> None:
        """Tonal root V is 5."""
        assert TONAL_ROOTS["V"] == 5
        assert TONAL_ROOTS["v"] == 5

    def test_tonal_roots_IV(self) -> None:
        """Tonal root IV is 4."""
        assert TONAL_ROOTS["IV"] == 4
        assert TONAL_ROOTS["iv"] == 4

    def test_tonal_roots_vi(self) -> None:
        """Tonal root vi is 6."""
        assert TONAL_ROOTS["vi"] == 6
        assert TONAL_ROOTS["VI"] == 6

    def test_tonal_roots_ii(self) -> None:
        """Tonal root ii is 2."""
        assert TONAL_ROOTS["ii"] == 2

    def test_tonal_roots_iii(self) -> None:
        """Tonal root iii is 3."""
        assert TONAL_ROOTS["iii"] == 3
        assert TONAL_ROOTS["III"] == 3

    def test_tonal_roots_VII(self) -> None:
        """Tonal root VII is 7."""
        assert TONAL_ROOTS["VII"] == 7
        assert TONAL_ROOTS["vii"] == 7

    def test_all_tonal_roots(self) -> None:
        """All expected tonal roots present."""
        expected_keys = {"I", "i", "V", "v", "IV", "iv", "vi", "VI", "ii", "iii", "III", "VII", "vii"}
        assert set(TONAL_ROOTS.keys()) == expected_keys


class TestBarDuration:
    """Test bar_duration function."""

    def test_4_4(self) -> None:
        """4/4 metre has bar duration of 1."""
        assert bar_duration("4/4") == Fraction(1)

    def test_3_4(self) -> None:
        """3/4 metre has bar duration of 3/4."""
        assert bar_duration("3/4") == Fraction(3, 4)

    def test_2_4(self) -> None:
        """2/4 metre has bar duration of 1/2."""
        assert bar_duration("2/4") == Fraction(1, 2)

    def test_6_8(self) -> None:
        """6/8 metre has bar duration of 3/4."""
        assert bar_duration("6/8") == Fraction(6, 8)

    def test_2_2(self) -> None:
        """2/2 (cut time) has bar duration of 1."""
        assert bar_duration("2/2") == Fraction(1)

    def test_12_8(self) -> None:
        """12/8 metre has bar duration of 3/2."""
        assert bar_duration("12/8") == Fraction(12, 8)


class TestSubjectToMotifAst:
    """Test subject_to_motif_ast function.

    Note: This function requires Subject from planner, creating coupling.
    We test it with actual Subject instances since it's essentially an integration point.
    """

    def test_converts_degrees_to_floating_notes(self) -> None:
        """Subject degrees become FloatingNote pitches."""
        # Create Subject directly to avoid solver dependency
        from planner.subject import Subject
        subj = Subject(
            degrees=(1, 2, 3),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
            bars=1,
        )
        result = subject_to_motif_ast(subj)
        assert isinstance(result, MotifAST)
        assert len(result.pitches) == 3
        assert all(isinstance(p, FloatingNote) for p in result.pitches)

    def test_preserves_durations(self) -> None:
        """Subject durations preserved."""
        from planner.subject import Subject
        subj = Subject(
            degrees=(1, 2, 3),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
            bars=1,
        )
        result = subject_to_motif_ast(subj)
        assert result.durations == (Fraction(1, 4), Fraction(1, 4), Fraction(1, 2))

    def test_preserves_bars(self) -> None:
        """Subject bars count preserved."""
        from planner.subject import Subject
        subj = Subject(
            degrees=(1, 2, 3, 4),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            bars=2,
        )
        result = subject_to_motif_ast(subj)
        assert result.bars == 2

    def test_degree_values(self) -> None:
        """FloatingNote degrees match subject degrees."""
        from planner.subject import Subject
        subj = Subject(
            degrees=(1, 5, 3),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
            bars=1,
        )
        result = subject_to_motif_ast(subj)
        assert result.pitches[0].degree == 1
        assert result.pitches[1].degree == 5
        assert result.pitches[2].degree == 3


class TestCsToMotifAst:
    """Test cs_to_motif_ast function.

    Note: This function requires Subject from planner, creating coupling.
    Counter-subject is lazily generated, so we test with a Subject that has one.
    """

    def test_converts_cs_to_motif_ast(self) -> None:
        """Counter-subject converted to MotifAST."""
        from planner.subject import Subject
        subj = Subject(
            degrees=(1, 3, 5, 1),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            bars=1,
        )
        result = cs_to_motif_ast(subj)
        assert isinstance(result, MotifAST)
        assert all(isinstance(p, FloatingNote) for p in result.pitches)

    def test_cs_has_durations(self) -> None:
        """Counter-subject has durations."""
        from planner.subject import Subject
        subj = Subject(
            degrees=(1, 3, 5, 1),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            bars=1,
        )
        result = cs_to_motif_ast(subj)
        assert len(result.durations) > 0
        assert sum(result.durations) == Fraction(1)  # One bar

    def test_cs_preserves_bars(self) -> None:
        """Counter-subject preserves bars count."""
        from planner.subject import Subject
        subj = Subject(
            degrees=(1, 3, 5, 1),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            bars=1,
        )
        result = cs_to_motif_ast(subj)
        assert result.bars == 1


class TestApplyRhythm:
    """Test apply_rhythm function."""

    def test_straight_rhythm(self) -> None:
        """Straight rhythm applies quarter notes."""
        pitches = (FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(4))
        durations = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4))
        result_p, result_d = apply_rhythm(pitches, durations, "straight", Fraction(1))
        assert sum(result_d) == Fraction(1)
        # Straight rhythm: 1/4, 1/4, 1/4, 1/4
        assert all(d == Fraction(1, 4) for d in result_d)

    def test_dotted_rhythm(self) -> None:
        """Dotted rhythm applies long-short pairs."""
        pitches = (FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(4))
        durations = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4))
        result_p, result_d = apply_rhythm(pitches, durations, "dotted", Fraction(1))
        assert sum(result_d) == Fraction(1)
        # Dotted rhythm: 3/8, 1/8, 3/8, 1/8
        assert Fraction(3, 8) in result_d
        assert Fraction(1, 8) in result_d

    def test_running_rhythm(self) -> None:
        """Running rhythm applies eighth notes."""
        pitches = (FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(4))
        durations = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4))
        result_p, result_d = apply_rhythm(pitches, durations, "running", Fraction(1))
        assert sum(result_d) == Fraction(1)
        # Running rhythm: all 1/8
        assert all(d == Fraction(1, 8) for d in result_d)
        assert len(result_d) == 8

    def test_lombardic_rhythm(self) -> None:
        """Lombardic rhythm applies short-long pairs."""
        pitches = (FloatingNote(1), FloatingNote(2))
        durations = (Fraction(1, 2), Fraction(1, 2))
        result_p, result_d = apply_rhythm(pitches, durations, "lombardic", Fraction(1))
        assert sum(result_d) == Fraction(1)
        # Lombardic: 1/8, 3/8, 1/8, 3/8

    def test_budget_truncation(self) -> None:
        """Rhythm truncated to budget."""
        pitches = (FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(4))
        durations = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4))
        result_p, result_d = apply_rhythm(pitches, durations, "straight", Fraction(1, 2))
        assert sum(result_d) == Fraction(1, 2)

    def test_cycles_pitches_with_variety(self) -> None:
        """Pitches cycle with variety when needed."""
        pitches = (FloatingNote(1), FloatingNote(2))
        durations = (Fraction(1, 4), Fraction(1, 4))
        # Running rhythm needs 8 pitches but we only have 2, so it cycles
        result_p, result_d = apply_rhythm(pitches, durations, "running", Fraction(1))
        assert len(result_p) == 8
        # First two should be original
        assert result_p[0].degree == 1
        assert result_p[1].degree == 2

    def test_unknown_rhythm_raises(self) -> None:
        """Unknown rhythm name raises AssertionError."""
        pitches = (FloatingNote(1),)
        durations = (Fraction(1),)
        try:
            apply_rhythm(pitches, durations, "nonexistent_rhythm", Fraction(1))
            assert False, "Should have raised AssertionError"
        except AssertionError as e:
            assert "Unknown rhythm" in str(e)

    def test_hemiola_rhythm(self) -> None:
        """Hemiola rhythm applies half notes."""
        pitches = (FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(4))
        durations = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4))
        result_p, result_d = apply_rhythm(pitches, durations, "hemiola", Fraction(2))
        # Hemiola: half notes (1/2)
        assert Fraction(1, 2) in result_d

    def test_zero_budget(self) -> None:
        """Zero budget returns empty result."""
        pitches = (FloatingNote(1),)
        durations = (Fraction(1, 4),)
        result_p, result_d = apply_rhythm(pitches, durations, "straight", Fraction(0))
        assert result_p == ()
        assert result_d == ()


class TestApplyDevice:
    """Test apply_device function."""

    def test_augmentation_doubles_durations(self) -> None:
        """Augmentation doubles note durations."""
        pitches = (FloatingNote(1), FloatingNote(2))
        durations = (Fraction(1, 4), Fraction(1, 4))
        result_p, result_d = apply_device(pitches, durations, "augmentation", Fraction(1))
        # Augmentation factor is 2, so 1/4 -> 1/2
        # Budget is 1, so we get two notes of 1/2 each
        assert sum(result_d) == Fraction(1)

    def test_diminution_halves_durations(self) -> None:
        """Diminution halves note durations."""
        pitches = (FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(4))
        durations = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4))
        result_p, result_d = apply_device(pitches, durations, "diminution", Fraction(1))
        # Diminution factor is 1/2, so 1/4 -> 1/8
        # With 8 notes of 1/8, total is 1
        assert all(d == Fraction(1, 8) for d in result_d)
        assert sum(result_d) == Fraction(1)
        assert len(result_d) == 8

    def test_stretto_no_duration_change(self) -> None:
        """Stretto doesn't change durations (only imitation offset)."""
        pitches = (FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(4))
        durations = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4))
        result_p, result_d = apply_device(pitches, durations, "stretto", Fraction(1))
        # Stretto has no duration_factor, so durations unchanged
        assert result_d == durations
        assert sum(result_d) == Fraction(1)

    def test_invertible_no_duration_change(self) -> None:
        """Invertible doesn't change durations (only voice_swap)."""
        pitches = (FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(4))
        durations = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4))
        result_p, result_d = apply_device(pitches, durations, "invertible", Fraction(1))
        # Invertible has no duration_factor
        assert result_d == durations

    def test_budget_truncation(self) -> None:
        """Device output truncated to budget."""
        pitches = (FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(4))
        durations = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4))
        result_p, result_d = apply_device(pitches, durations, "stretto", Fraction(1, 2))
        assert sum(result_d) == Fraction(1, 2)

    def test_unknown_device_raises(self) -> None:
        """Unknown device name raises AssertionError."""
        pitches = (FloatingNote(1),)
        durations = (Fraction(1),)
        try:
            apply_device(pitches, durations, "nonexistent_device", Fraction(1))
            assert False, "Should have raised AssertionError"
        except AssertionError as e:
            assert "Unknown device" in str(e)

    def test_cycles_pitches_with_variety(self) -> None:
        """Pitches cycle with variety when device extends material."""
        pitches = (FloatingNote(1), FloatingNote(2))
        durations = (Fraction(1, 4), Fraction(1, 4))
        # Diminution makes durations 1/8, so we need 8 pitches
        result_p, result_d = apply_device(pitches, durations, "diminution", Fraction(1))
        assert len(result_p) == 8
        # cycle_pitch_with_variety adds offset per cycle
        assert result_p[0].degree == 1
        assert result_p[1].degree == 2

    def test_zero_budget(self) -> None:
        """Zero budget returns empty result."""
        pitches = (FloatingNote(1),)
        durations = (Fraction(1, 4),)
        result_p, result_d = apply_device(pitches, durations, "stretto", Fraction(0))
        assert result_p == ()
        assert result_d == ()

    def test_partial_note_at_budget_end(self) -> None:
        """Partial note truncated at budget boundary."""
        pitches = (FloatingNote(1), FloatingNote(2), FloatingNote(3))
        durations = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4))
        # Budget 3/8 with 1/4 notes means last note truncated to 1/8
        result_p, result_d = apply_device(pitches, durations, "stretto", Fraction(3, 8))
        assert sum(result_d) == Fraction(3, 8)
        assert result_d[-1] == Fraction(1, 8)  # Truncated


class TestIntegration:
    """Integration tests for expander_util module."""

    def test_rhythm_then_device(self) -> None:
        """Apply rhythm then device in sequence."""
        pitches = (FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(4))
        durations = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4))
        # First apply straight rhythm
        rp, rd = apply_rhythm(pitches, durations, "straight", Fraction(1))
        # Then apply diminution
        dp, dd = apply_device(rp, rd, "diminution", Fraction(1))
        # Result should have eighth notes
        assert all(d == Fraction(1, 8) for d in dd)
        assert sum(dd) == Fraction(1)

    def test_bar_duration_matches_rhythm_budget(self) -> None:
        """Bar duration can be used as rhythm budget."""
        bar_dur = bar_duration("4/4")
        pitches = (FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(4))
        durations = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4))
        result_p, result_d = apply_rhythm(pitches, durations, "straight", bar_dur)
        assert sum(result_d) == bar_dur

    def test_tonal_roots_cover_diatonic_degrees(self) -> None:
        """All seven diatonic degrees represented in TONAL_ROOTS."""
        degrees = set(TONAL_ROOTS.values())
        assert degrees == {1, 2, 3, 4, 5, 6, 7}
