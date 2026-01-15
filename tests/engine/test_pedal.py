"""100% coverage tests for engine.pedal.

Tests import only:
- engine.pedal (module under test)
- shared (pitch, timed_material)
- stdlib
"""
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote
from shared.timed_material import TimedMaterial

from engine.pedal import (
    PEDAL_DEGREES,
    generate_pedal_bass,
    generate_inverted_pedal,
    is_pedal_treatment,
    get_pedal_type,
)


class TestPedalDegreesConstant:
    """Test PEDAL_DEGREES constant."""

    def test_tonic_is_degree_one(self) -> None:
        """Tonic pedal uses scale degree 1."""
        assert PEDAL_DEGREES["tonic"] == 1

    def test_dominant_is_degree_five(self) -> None:
        """Dominant pedal uses scale degree 5."""
        assert PEDAL_DEGREES["dominant"] == 5

    def test_only_two_pedal_types(self) -> None:
        """Only tonic and dominant pedals defined."""
        assert len(PEDAL_DEGREES) == 2
        assert set(PEDAL_DEGREES.keys()) == {"tonic", "dominant"}


class TestGeneratePedalBass:
    """Test generate_pedal_bass function."""

    def test_tonic_pedal_uses_degree_one(self) -> None:
        """Tonic pedal generates degree 1 throughout."""
        result: TimedMaterial = generate_pedal_bass("tonic", Fraction(2))
        for pitch in result.pitches:
            assert isinstance(pitch, FloatingNote)
            assert pitch.degree == 1

    def test_dominant_pedal_uses_degree_five(self) -> None:
        """Dominant pedal generates degree 5 throughout."""
        result: TimedMaterial = generate_pedal_bass("dominant", Fraction(2))
        for pitch in result.pitches:
            assert isinstance(pitch, FloatingNote)
            assert pitch.degree == 5

    def test_budget_exactly_filled(self) -> None:
        """Total duration equals budget exactly."""
        budget: Fraction = Fraction(3)
        result: TimedMaterial = generate_pedal_bass("tonic", budget)
        assert sum(result.durations) == budget
        assert result.budget == budget

    def test_default_pulse_half_note(self) -> None:
        """Default pulse is half note (1/2)."""
        result: TimedMaterial = generate_pedal_bass("tonic", Fraction(2))
        # With 2 bars and 1/2 pulse, should have 4 notes
        assert len(result.pitches) == 4
        for dur in result.durations:
            assert dur == Fraction(1, 2)

    def test_custom_pulse_quarter_note(self) -> None:
        """Custom quarter-note pulse produces more notes."""
        result: TimedMaterial = generate_pedal_bass(
            "tonic", Fraction(1), pulse=Fraction(1, 4)
        )
        # 1 bar with 1/4 pulse = 4 notes
        assert len(result.pitches) == 4
        for dur in result.durations:
            assert dur == Fraction(1, 4)

    def test_partial_final_note(self) -> None:
        """Final note truncated if budget not multiple of pulse."""
        # 3/4 bar with 1/2 pulse = one 1/2, one 1/4
        result: TimedMaterial = generate_pedal_bass(
            "tonic", Fraction(3, 4), pulse=Fraction(1, 2)
        )
        assert len(result.pitches) == 2
        assert result.durations[0] == Fraction(1, 2)
        assert result.durations[1] == Fraction(1, 4)

    def test_budget_smaller_than_pulse(self) -> None:
        """Budget smaller than pulse produces single shortened note."""
        result: TimedMaterial = generate_pedal_bass(
            "dominant", Fraction(1, 4), pulse=Fraction(1, 2)
        )
        assert len(result.pitches) == 1
        assert result.durations[0] == Fraction(1, 4)

    def test_unknown_pedal_type_raises(self) -> None:
        """Unknown pedal type raises AssertionError."""
        with pytest.raises(AssertionError, match="Unknown pedal type"):
            generate_pedal_bass("subdominant", Fraction(1))

    def test_timed_material_invariant_holds(self) -> None:
        """Result satisfies TimedMaterial invariant."""
        result: TimedMaterial = generate_pedal_bass("tonic", Fraction(5, 4))
        # TimedMaterial validates sum(durations) == budget on construction
        assert result.budget == Fraction(5, 4)


class TestGenerateInvertedPedal:
    """Test generate_inverted_pedal function."""

    def test_soprano_holds_pedal_degree(self) -> None:
        """Soprano voice holds the specified pedal degree."""
        bass: TimedMaterial = TimedMaterial(
            (FloatingNote(1), FloatingNote(2)),
            (Fraction(1, 2), Fraction(1, 2)),
            Fraction(1),
        )
        soprano, returned_bass = generate_inverted_pedal(5, bass, Fraction(1))
        for pitch in soprano.pitches:
            assert isinstance(pitch, FloatingNote)
            assert pitch.degree == 5

    def test_bass_material_unchanged(self) -> None:
        """Bass material passed through unchanged."""
        bass: TimedMaterial = TimedMaterial(
            (FloatingNote(1), FloatingNote(3), FloatingNote(5)),
            (Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
            Fraction(1),
        )
        soprano, returned_bass = generate_inverted_pedal(1, bass, Fraction(1))
        assert returned_bass is bass

    def test_soprano_budget_matches(self) -> None:
        """Soprano duration matches budget."""
        bass: TimedMaterial = TimedMaterial(
            (FloatingNote(5),), (Fraction(2),), Fraction(2)
        )
        soprano, _ = generate_inverted_pedal(1, bass, Fraction(2))
        assert soprano.budget == Fraction(2)
        assert sum(soprano.durations) == Fraction(2)

    def test_soprano_uses_half_note_pulse(self) -> None:
        """Soprano pedal uses fixed half-note pulse."""
        bass: TimedMaterial = TimedMaterial(
            (FloatingNote(1),), (Fraction(2),), Fraction(2)
        )
        soprano, _ = generate_inverted_pedal(5, bass, Fraction(2))
        # 2 bars with 1/2 pulse = 4 notes
        assert len(soprano.pitches) == 4
        for dur in soprano.durations:
            assert dur == Fraction(1, 2)

    def test_partial_final_soprano_note(self) -> None:
        """Final soprano note truncated for non-even budget."""
        bass: TimedMaterial = TimedMaterial(
            (FloatingNote(1),), (Fraction(3, 4),), Fraction(3, 4)
        )
        soprano, _ = generate_inverted_pedal(1, bass, Fraction(3, 4))
        assert soprano.durations[-1] == Fraction(1, 4)

    def test_returns_tuple(self) -> None:
        """Function returns tuple of two TimedMaterial."""
        bass: TimedMaterial = TimedMaterial(
            (FloatingNote(5),), (Fraction(1),), Fraction(1)
        )
        result = generate_inverted_pedal(1, bass, Fraction(1))
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], TimedMaterial)
        assert isinstance(result[1], TimedMaterial)


class TestIsPedalTreatment:
    """Test is_pedal_treatment function."""

    def test_pedal_tonic_is_pedal(self) -> None:
        """pedal_tonic is a pedal treatment."""
        assert is_pedal_treatment("pedal_tonic") is True

    def test_pedal_dominant_is_pedal(self) -> None:
        """pedal_dominant is a pedal treatment."""
        assert is_pedal_treatment("pedal_dominant") is True

    def test_pedal_prefix_matches(self) -> None:
        """Any pedal_ prefix matches."""
        assert is_pedal_treatment("pedal_something") is True

    def test_statement_not_pedal(self) -> None:
        """statement is not a pedal treatment."""
        assert is_pedal_treatment("statement") is False

    def test_imitation_not_pedal(self) -> None:
        """imitation is not a pedal treatment."""
        assert is_pedal_treatment("imitation") is False

    def test_tonic_without_prefix_not_pedal(self) -> None:
        """tonic alone is not a pedal treatment."""
        assert is_pedal_treatment("tonic") is False

    def test_empty_string_not_pedal(self) -> None:
        """Empty string is not a pedal treatment."""
        assert is_pedal_treatment("") is False


class TestGetPedalType:
    """Test get_pedal_type function."""

    def test_pedal_tonic_returns_tonic(self) -> None:
        """pedal_tonic returns 'tonic'."""
        assert get_pedal_type("pedal_tonic") == "tonic"

    def test_pedal_dominant_returns_dominant(self) -> None:
        """pedal_dominant returns 'dominant'."""
        assert get_pedal_type("pedal_dominant") == "dominant"

    def test_statement_returns_none(self) -> None:
        """Non-pedal treatment returns None."""
        assert get_pedal_type("statement") is None

    def test_pedal_other_returns_none(self) -> None:
        """Unknown pedal type returns None."""
        assert get_pedal_type("pedal_subdominant") is None

    def test_empty_string_returns_none(self) -> None:
        """Empty string returns None."""
        assert get_pedal_type("") is None

    def test_partial_match_returns_none(self) -> None:
        """Partial match not accepted."""
        assert get_pedal_type("pedal_toni") is None
        assert get_pedal_type("tonic_pedal") is None


class TestPedalIntegration:
    """Integration tests for pedal module."""

    def test_tonic_pedal_for_four_bar_phrase(self) -> None:
        """Tonic pedal fills 4-bar phrase correctly."""
        budget: Fraction = Fraction(4)  # 4 bars
        result: TimedMaterial = generate_pedal_bass("tonic", budget)
        # Default pulse 1/2, so 8 half-notes
        assert len(result.pitches) == 8
        assert all(p.degree == 1 for p in result.pitches)
        assert sum(result.durations) == budget

    def test_dominant_pedal_under_melodic_soprano(self) -> None:
        """Dominant pedal under varied soprano melody."""
        soprano_pitches = (FloatingNote(3), FloatingNote(2), FloatingNote(1))
        soprano_durations = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 2))
        bass: TimedMaterial = generate_pedal_bass("dominant", Fraction(1))
        # Bass repeats degree 5, soprano moves
        assert all(p.degree == 5 for p in bass.pitches)
        assert bass.budget == Fraction(1)

    def test_inverted_tonic_pedal(self) -> None:
        """Inverted pedal: soprano holds 1, bass moves."""
        bass_line: TimedMaterial = TimedMaterial(
            (FloatingNote(5), FloatingNote(4), FloatingNote(3), FloatingNote(2)),
            (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            Fraction(1),
        )
        soprano, bass = generate_inverted_pedal(1, bass_line, Fraction(1))
        # Soprano holds degree 1
        assert all(p.degree == 1 for p in soprano.pitches)
        # Bass has melodic motion
        bass_degrees = [p.degree for p in bass.pitches]
        assert bass_degrees == [5, 4, 3, 2]
