"""100% coverage tests for engine.cadence.

Tests import only:
- engine.cadence (module under test)
- shared (pitch, timed_material)
- stdlib

Cadence module provides cadence formulas for phrase endings, including
internal cadences (half-bar) and final cadences (2-bar approach + resolution).
"""
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote

from engine.cadence import (
    CADENCE_FORMULAS,
    TONAL_OFFSET,
    apply_final_cadence,
    get_cadence_material,
    get_internal_cadence_formulas,
    load_cadences,
    load_final_cadences,
    offset_pitch,
    parse_fraction,
)


class TestTonalOffset:
    """Test TONAL_OFFSET constant."""

    def test_tonic_is_zero(self) -> None:
        """I (tonic) has offset 0."""
        assert TONAL_OFFSET["I"] == 0

    def test_dominant_is_4(self) -> None:
        """V (dominant) has offset 4."""
        assert TONAL_OFFSET["V"] == 4

    def test_subdominant_is_minus_1(self) -> None:
        """IV (subdominant) has offset -1."""
        assert TONAL_OFFSET["IV"] == -1

    def test_relative_minor_is_5(self) -> None:
        """vi (relative minor) has offset 5."""
        assert TONAL_OFFSET["vi"] == 5

    def test_supertonic_is_1(self) -> None:
        """ii (supertonic) has offset 1."""
        assert TONAL_OFFSET["ii"] == 1

    def test_mediant_is_2(self) -> None:
        """iii (mediant) has offset 2."""
        assert TONAL_OFFSET["iii"] == 2


class TestLoadCadences:
    """Test load_cadences function."""

    def test_returns_dict(self) -> None:
        """Returns a dictionary."""
        result: dict = load_cadences()
        assert isinstance(result, dict)

    def test_has_internal_key(self) -> None:
        """Has 'internal' key."""
        result: dict = load_cadences()
        assert "internal" in result

    def test_has_final_key(self) -> None:
        """Has 'final' key."""
        result: dict = load_cadences()
        assert "final" in result

    def test_internal_has_authentic(self) -> None:
        """Internal cadences include authentic."""
        result: dict = load_cadences()
        assert "authentic" in result["internal"]

    def test_internal_has_half(self) -> None:
        """Internal cadences include half."""
        result: dict = load_cadences()
        assert "half" in result["internal"]

    def test_internal_has_deceptive(self) -> None:
        """Internal cadences include deceptive."""
        result: dict = load_cadences()
        assert "deceptive" in result["internal"]


class TestGetInternalCadenceFormulas:
    """Test get_internal_cadence_formulas function."""

    def test_returns_dict(self) -> None:
        """Returns a dictionary."""
        result = get_internal_cadence_formulas()
        assert isinstance(result, dict)

    def test_authentic_formula(self) -> None:
        """Authentic cadence has correct formula.

        Domain knowledge: Authentic cadence is 7-1 soprano over 5-1 bass.
        """
        result = get_internal_cadence_formulas()
        soprano, bass = result["authentic"]
        sop_degrees: list[int] = [p.degree for p in soprano]
        bass_degrees: list[int] = [p.degree for p in bass]
        assert sop_degrees == [7, 1]
        assert bass_degrees == [5, 1]

    def test_half_formula(self) -> None:
        """Half cadence has correct formula.

        Domain knowledge: Half cadence ends on dominant, 1-7 soprano over 4-5 bass.
        """
        result = get_internal_cadence_formulas()
        soprano, bass = result["half"]
        sop_degrees: list[int] = [p.degree for p in soprano]
        bass_degrees: list[int] = [p.degree for p in bass]
        assert sop_degrees == [1, 7]
        assert bass_degrees == [4, 5]

    def test_deceptive_formula(self) -> None:
        """Deceptive cadence has correct formula.

        Domain knowledge: Deceptive cadence resolves to vi instead of I.
        """
        result = get_internal_cadence_formulas()
        soprano, bass = result["deceptive"]
        bass_degrees: list[int] = [p.degree for p in bass]
        assert bass_degrees == [5, 6]  # Goes to vi instead of I

    def test_all_formulas_are_tuples(self) -> None:
        """All formulas are (soprano, bass) tuples of Pitch tuples."""
        result = get_internal_cadence_formulas()
        for name, (soprano, bass) in result.items():
            assert isinstance(soprano, tuple), f"{name} soprano not tuple"
            assert isinstance(bass, tuple), f"{name} bass not tuple"
            for p in soprano:
                assert isinstance(p, FloatingNote), f"{name} soprano has non-FloatingNote"
            for p in bass:
                assert isinstance(p, FloatingNote), f"{name} bass has non-FloatingNote"


class TestCadenceFormulasConstant:
    """Test CADENCE_FORMULAS constant."""

    def test_is_dict(self) -> None:
        """CADENCE_FORMULAS is a dictionary."""
        assert isinstance(CADENCE_FORMULAS, dict)

    def test_contains_standard_cadences(self) -> None:
        """Contains standard internal cadence types."""
        standard: list[str] = ["authentic", "half", "deceptive", "plagal", "phrygian"]
        for name in standard:
            assert name in CADENCE_FORMULAS, f"Missing cadence: {name}"


class TestOffsetPitch:
    """Test offset_pitch function."""

    def test_zero_offset(self) -> None:
        """Zero offset returns same degree."""
        pitch: FloatingNote = FloatingNote(3)
        result = offset_pitch(pitch, 0)
        assert result.degree == 3

    def test_positive_offset(self) -> None:
        """Positive offset increases degree."""
        pitch: FloatingNote = FloatingNote(1)
        result = offset_pitch(pitch, 4)
        assert result.degree == 5  # 1 + 4 = 5

    def test_negative_offset(self) -> None:
        """Negative offset decreases degree."""
        pitch: FloatingNote = FloatingNote(5)
        result = offset_pitch(pitch, -2)
        assert result.degree == 3  # 5 - 2 = 3

    def test_wraps_to_valid_range(self) -> None:
        """Offset wraps to 1-7 range."""
        pitch: FloatingNote = FloatingNote(7)
        result = offset_pitch(pitch, 3)
        # 7 + 3 = 10 -> wrap to 3
        assert result.degree == 3


class TestParseFraction:
    """Test parse_fraction function."""

    def test_simple_fraction(self) -> None:
        """Parses simple fraction string."""
        result: Fraction = parse_fraction("1/2")
        assert result == Fraction(1, 2)

    def test_quarter(self) -> None:
        """Parses quarter note duration."""
        result: Fraction = parse_fraction("1/4")
        assert result == Fraction(1, 4)

    def test_dotted_half(self) -> None:
        """Parses dotted half note duration."""
        result: Fraction = parse_fraction("3/4")
        assert result == Fraction(3, 4)

    def test_whole_number(self) -> None:
        """Parses whole number as fraction."""
        result: Fraction = parse_fraction("2")
        assert result == Fraction(2)

    def test_one(self) -> None:
        """Parses '1' as whole note."""
        result: Fraction = parse_fraction("1")
        assert result == Fraction(1)


class TestGetCadenceMaterial:
    """Test get_cadence_material function."""

    def test_returns_tuple_of_timed_materials(self) -> None:
        """Returns tuple of (soprano, bass) TimedMaterial."""
        from shared.timed_material import TimedMaterial
        soprano, bass = get_cadence_material("authentic", Fraction(1))
        assert isinstance(soprano, TimedMaterial)
        assert isinstance(bass, TimedMaterial)

    def test_budget_preserved(self) -> None:
        """Budget is preserved in both voices."""
        soprano, bass = get_cadence_material("authentic", Fraction(1))
        assert soprano.budget == Fraction(1)
        assert bass.budget == Fraction(1)

    def test_durations_sum_to_budget(self) -> None:
        """Durations sum to budget."""
        soprano, bass = get_cadence_material("half", Fraction(1))
        assert sum(soprano.durations) == Fraction(1)
        assert sum(bass.durations) == Fraction(1)

    def test_two_notes_per_voice(self) -> None:
        """Each voice has 2 notes (half-bar cadence)."""
        soprano, bass = get_cadence_material("authentic", Fraction(1))
        assert len(soprano.pitches) == 2
        assert len(bass.pitches) == 2

    def test_tonic_target_no_offset(self) -> None:
        """Tonic target (I) has no offset."""
        soprano, bass = get_cadence_material("authentic", Fraction(1), tonal_target="I")
        sop_degrees: list[int] = [p.degree for p in soprano.pitches]
        assert sop_degrees == [7, 1]  # No offset

    def test_dominant_target_offset(self) -> None:
        """Dominant target (V) offsets by 4."""
        soprano, bass = get_cadence_material("authentic", Fraction(1), tonal_target="V")
        sop_degrees: list[int] = [p.degree for p in soprano.pitches]
        # 7 + 4 = 11 -> 4, 1 + 4 = 5
        assert sop_degrees == [4, 5]

    def test_unknown_cadence_raises(self) -> None:
        """Unknown cadence type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown cadence type"):
            get_cadence_material("nonexistent_cadence", Fraction(1))

    def test_unknown_tonal_target_defaults_to_zero(self) -> None:
        """Unknown tonal target defaults to offset 0."""
        soprano, bass = get_cadence_material("authentic", Fraction(1), tonal_target="unknown")
        sop_degrees: list[int] = [p.degree for p in soprano.pitches]
        assert sop_degrees == [7, 1]  # No offset (default 0)


class TestLoadFinalCadences:
    """Test load_final_cadences function."""

    def test_returns_dict(self) -> None:
        """Returns a dictionary."""
        result: dict = load_final_cadences()
        assert isinstance(result, dict)

    def test_contains_stepwise(self) -> None:
        """Contains stepwise cadence."""
        result: dict = load_final_cadences()
        assert "stepwise" in result

    def test_contains_leap(self) -> None:
        """Contains leap cadence."""
        result: dict = load_final_cadences()
        assert "leap" in result

    def test_contains_decorated(self) -> None:
        """Contains decorated cadence."""
        result: dict = load_final_cadences()
        assert "decorated" in result

    def test_each_has_approach_and_resolution(self) -> None:
        """Each final cadence has approach and resolution."""
        result: dict = load_final_cadences()
        for name, formula in result.items():
            assert "approach" in formula, f"{name} missing approach"
            assert "resolution" in formula, f"{name} missing resolution"


class TestApplyFinalCadence:
    """Test apply_final_cadence function."""

    def test_returns_four_tuples(self) -> None:
        """Returns (sop_pitches, sop_durs, bass_pitches, bass_durs)."""
        sop_p: tuple[FloatingNote, ...] = tuple(FloatingNote(i) for i in [1, 2, 3, 4, 5, 6, 7, 1])
        sop_d: tuple[Fraction, ...] = tuple(Fraction(1, 4) for _ in range(8))
        bass_p: tuple[FloatingNote, ...] = tuple(FloatingNote(i) for i in [1, 5, 1, 5, 1, 5, 1, 5])
        bass_d: tuple[Fraction, ...] = tuple(Fraction(1, 4) for _ in range(8))
        result = apply_final_cadence(sop_p, sop_d, bass_p, bass_d, Fraction(1), Fraction(4))
        assert len(result) == 4
        new_sop_p, new_sop_d, new_bass_p, new_bass_d = result
        assert isinstance(new_sop_p, tuple)
        assert isinstance(new_sop_d, tuple)
        assert isinstance(new_bass_p, tuple)
        assert isinstance(new_bass_d, tuple)

    def test_preserves_phrase_budget(self) -> None:
        """Result durations sum to phrase budget."""
        sop_p: tuple[FloatingNote, ...] = tuple(FloatingNote(i) for i in [1, 2, 3, 4, 5, 6, 7, 1])
        sop_d: tuple[Fraction, ...] = tuple(Fraction(1, 4) for _ in range(8))
        bass_p: tuple[FloatingNote, ...] = tuple(FloatingNote(i) for i in [1, 5, 1, 5, 1, 5, 1, 5])
        bass_d: tuple[Fraction, ...] = tuple(Fraction(1, 4) for _ in range(8))
        budget: Fraction = Fraction(4)
        _, new_sop_d, _, new_bass_d = apply_final_cadence(
            sop_p, sop_d, bass_p, bass_d, Fraction(1), budget
        )
        assert sum(new_sop_d) == budget
        assert sum(new_bass_d) == budget

    def test_stepwise_cadence(self) -> None:
        """Stepwise cadence type works."""
        sop_p: tuple[FloatingNote, ...] = tuple(FloatingNote(i) for i in [1, 2, 3, 4, 5, 6, 7, 1])
        sop_d: tuple[Fraction, ...] = tuple(Fraction(1, 4) for _ in range(8))
        bass_p: tuple[FloatingNote, ...] = tuple(FloatingNote(i) for i in [1, 5, 1, 5, 1, 5, 1, 5])
        bass_d: tuple[Fraction, ...] = tuple(Fraction(1, 4) for _ in range(8))
        result = apply_final_cadence(
            sop_p, sop_d, bass_p, bass_d, Fraction(1), Fraction(4),
            cadence_type="stepwise"
        )
        assert len(result) == 4

    def test_leap_cadence(self) -> None:
        """Leap cadence type works."""
        sop_p: tuple[FloatingNote, ...] = tuple(FloatingNote(i) for i in [1, 2, 3, 4, 5, 6, 7, 1])
        sop_d: tuple[Fraction, ...] = tuple(Fraction(1, 4) for _ in range(8))
        bass_p: tuple[FloatingNote, ...] = tuple(FloatingNote(i) for i in [1, 5, 1, 5, 1, 5, 1, 5])
        bass_d: tuple[Fraction, ...] = tuple(Fraction(1, 4) for _ in range(8))
        result = apply_final_cadence(
            sop_p, sop_d, bass_p, bass_d, Fraction(1), Fraction(4),
            cadence_type="leap"
        )
        assert len(result) == 4

    def test_decorated_cadence(self) -> None:
        """Decorated cadence type works."""
        sop_p: tuple[FloatingNote, ...] = tuple(FloatingNote(i) for i in [1, 2, 3, 4, 5, 6, 7, 1])
        sop_d: tuple[Fraction, ...] = tuple(Fraction(1, 4) for _ in range(8))
        bass_p: tuple[FloatingNote, ...] = tuple(FloatingNote(i) for i in [1, 5, 1, 5, 1, 5, 1, 5])
        bass_d: tuple[Fraction, ...] = tuple(Fraction(1, 4) for _ in range(8))
        result = apply_final_cadence(
            sop_p, sop_d, bass_p, bass_d, Fraction(1), Fraction(4),
            cadence_type="decorated"
        )
        assert len(result) == 4

    def test_tonal_target_offset(self) -> None:
        """Tonal target offsets cadence degrees."""
        sop_p: tuple[FloatingNote, ...] = tuple(FloatingNote(i) for i in [1, 2, 3, 4, 5, 6, 7, 1])
        sop_d: tuple[Fraction, ...] = tuple(Fraction(1, 4) for _ in range(8))
        bass_p: tuple[FloatingNote, ...] = tuple(FloatingNote(i) for i in [1, 5, 1, 5, 1, 5, 1, 5])
        bass_d: tuple[Fraction, ...] = tuple(Fraction(1, 4) for _ in range(8))
        _, _, _, _ = apply_final_cadence(
            sop_p, sop_d, bass_p, bass_d, Fraction(1), Fraction(4),
            tonal_target="V"
        )
        # Just verify it doesn't crash with offset

    def test_unknown_cadence_raises(self) -> None:
        """Unknown final cadence type raises ValueError."""
        sop_p: tuple[FloatingNote, ...] = (FloatingNote(1),)
        sop_d: tuple[Fraction, ...] = (Fraction(1),)
        bass_p: tuple[FloatingNote, ...] = (FloatingNote(1),)
        bass_d: tuple[Fraction, ...] = (Fraction(1),)
        with pytest.raises(ValueError, match="Unknown final cadence type"):
            apply_final_cadence(
                sop_p, sop_d, bass_p, bass_d, Fraction(1), Fraction(4),
                cadence_type="nonexistent"
            )

    def test_partial_duration_cut(self) -> None:
        """Partial duration at cut point is handled.

        Creates input where cut happens in the middle of a note duration.
        With stepwise cadence (2 bars), budget=4, cut point = 2.
        Using one 3-bar note means accumulated=0, 0+3=3 > 2, so partial cut triggers.
        """
        # One long note that spans beyond cut point
        sop_p: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(2))
        sop_d: tuple[Fraction, ...] = (Fraction(3), Fraction(1))  # Note 1 is 3 bars
        bass_p: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(5))
        bass_d: tuple[Fraction, ...] = (Fraction(3), Fraction(1))  # Note 1 is 3 bars
        # Stepwise cadence needs 2 bars, so cut at bar 2
        # accumulated=0, 0+3 > 2 triggers partial cut at lines 117-120, 130-133
        result = apply_final_cadence(
            sop_p, sop_d, bass_p, bass_d, Fraction(1), Fraction(4)
        )
        _, new_sop_d, _, new_bass_d = result
        assert sum(new_sop_d) == Fraction(4)
        assert sum(new_bass_d) == Fraction(4)


class TestIntegration:
    """Integration tests for cadence module."""

    def test_all_internal_cadences_work(self) -> None:
        """All internal cadence types can be retrieved."""
        for cadence_type in CADENCE_FORMULAS:
            soprano, bass = get_cadence_material(cadence_type, Fraction(1))
            assert sum(soprano.durations) == Fraction(1)
            assert sum(bass.durations) == Fraction(1)

    def test_all_final_cadences_work(self) -> None:
        """All final cadence types can be applied."""
        sop_p: tuple[FloatingNote, ...] = tuple(FloatingNote(i) for i in [1, 2, 3, 4, 5, 6, 7, 1])
        sop_d: tuple[Fraction, ...] = tuple(Fraction(1, 4) for _ in range(8))
        bass_p: tuple[FloatingNote, ...] = tuple(FloatingNote(i) for i in [1, 5, 1, 5, 1, 5, 1, 5])
        bass_d: tuple[Fraction, ...] = tuple(Fraction(1, 4) for _ in range(8))
        final_cadences: dict = load_final_cadences()
        for cadence_type in final_cadences:
            result = apply_final_cadence(
                sop_p, sop_d, bass_p, bass_d, Fraction(1), Fraction(4),
                cadence_type=cadence_type
            )
            assert len(result) == 4

    def test_authentic_cadence_musical_correctness(self) -> None:
        """Authentic cadence is musically correct.

        Domain knowledge: Authentic cadence resolves V-I in bass (5-1)
        with leading tone resolution 7-1 in soprano.
        """
        soprano, bass = get_cadence_material("authentic", Fraction(1))
        sop_degrees: list[int] = [p.degree for p in soprano.pitches]
        bass_degrees: list[int] = [p.degree for p in bass.pitches]
        assert sop_degrees == [7, 1]  # Leading tone to tonic
        assert bass_degrees == [5, 1]  # Dominant to tonic

    def test_half_cadence_musical_correctness(self) -> None:
        """Half cadence is musically correct.

        Domain knowledge: Half cadence ends on dominant (degree 5 in bass).
        """
        soprano, bass = get_cadence_material("half", Fraction(1))
        bass_degrees: list[int] = [p.degree for p in bass.pitches]
        assert bass_degrees[-1] == 5  # Ends on dominant
