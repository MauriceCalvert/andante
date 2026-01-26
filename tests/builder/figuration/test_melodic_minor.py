"""Tests for builder.figuration.melodic_minor module."""
import pytest

from builder.figuration.melodic_minor import (
    MelodicMinorMapper,
    determine_direction,
    filter_minor_unsafe_figures,
)
from builder.figuration.types import Figure
from shared.key import Key


def make_figure(name: str = "test", minor_safe: bool = True) -> Figure:
    """Helper to create test figures."""
    return Figure(
        name=name,
        degrees=(0, 1),
        contour="test",
        polarity="balanced",
        arrival="direct",
        placement="span",
        character="plain",
        harmonic_tension="low",
        max_density="medium",
        cadential_safe=True,
        repeatable=True,
        requires_compensation=False,
        compensation_direction=None,
        is_compound=False,
        minor_safe=minor_safe,
        requires_leading_tone=False,
        weight=1.0,
    )


class TestMelodicMinorMapper:
    """Tests for MelodicMinorMapper class."""

    def test_major_key_no_inflections(self) -> None:
        """Major key should have no melodic minor inflections."""
        key = Key(tonic="C", mode="major")
        mapper = MelodicMinorMapper(key)

        # Degree 7 in C major is B (71 in octave 4)
        pitch = mapper.degree_to_pitch(7, 4, "ascending")
        expected = key.degree_to_midi(7, 4)
        assert pitch == expected

    def test_minor_ascending_raises_7(self) -> None:
        """Minor key ascending should raise degree 7."""
        key = Key(tonic="A", mode="minor")
        mapper = MelodicMinorMapper(key)

        # Natural 7 in A minor is G (67)
        # Raised 7 is G# (68)
        pitch_ascending = mapper.degree_to_pitch(7, 4, "ascending")
        pitch_descending = mapper.degree_to_pitch(7, 4, "descending")

        # Ascending should be 1 semitone higher than descending
        assert pitch_ascending == pitch_descending + 1

    def test_minor_ascending_raises_6(self) -> None:
        """Minor key ascending should raise degree 6."""
        key = Key(tonic="A", mode="minor")
        mapper = MelodicMinorMapper(key)

        pitch_ascending = mapper.degree_to_pitch(6, 4, "ascending")
        pitch_descending = mapper.degree_to_pitch(6, 4, "descending")

        # Ascending should be 1 semitone higher than descending
        assert pitch_ascending == pitch_descending + 1

    def test_minor_descending_natural_7(self) -> None:
        """Minor key descending should use natural degree 7."""
        key = Key(tonic="A", mode="minor")
        mapper = MelodicMinorMapper(key)

        pitch = mapper.degree_to_pitch(7, 4, "descending")
        # G natural = 67 in octave 4 (A minor)
        natural_7 = key.degree_to_midi(7, 4)
        assert pitch == natural_7

    def test_cadential_context_raises_7(self) -> None:
        """Cadential context should raise degree 7 even if static."""
        key = Key(tonic="A", mode="minor")
        mapper = MelodicMinorMapper(key)

        pitch_static = mapper.degree_to_pitch(7, 4, "static")
        pitch_cadential = mapper.degree_to_pitch(7, 4, "static", context="cadential")

        # Cadential should raise 7
        assert pitch_cadential == pitch_static + 1


class TestAugmented2ndCheck:
    """Tests for augmented 2nd prohibition."""

    def test_detects_aug2_natural6_to_raised7(self) -> None:
        """Should detect augmented 2nd from natural 6 to raised 7."""
        key = Key(tonic="A", mode="minor")
        mapper = MelodicMinorMapper(key)

        result = mapper.check_augmented_2nd(
            degree_from=6,
            degree_to=7,
            raised_6=False,
            raised_7=True,
        )
        assert result is True

    def test_no_aug2_when_both_raised(self) -> None:
        """No augmented 2nd when both 6 and 7 raised."""
        key = Key(tonic="A", mode="minor")
        mapper = MelodicMinorMapper(key)

        result = mapper.check_augmented_2nd(
            degree_from=6,
            degree_to=7,
            raised_6=True,
            raised_7=True,
        )
        assert result is False

    def test_no_aug2_when_both_natural(self) -> None:
        """No augmented 2nd when both 6 and 7 natural."""
        key = Key(tonic="A", mode="minor")
        mapper = MelodicMinorMapper(key)

        result = mapper.check_augmented_2nd(
            degree_from=6,
            degree_to=7,
            raised_6=False,
            raised_7=False,
        )
        assert result is False

    def test_major_key_no_aug2_check(self) -> None:
        """Major key should not report augmented 2nd."""
        key = Key(tonic="C", mode="major")
        mapper = MelodicMinorMapper(key)

        result = mapper.check_augmented_2nd(
            degree_from=6,
            degree_to=7,
            raised_6=False,
            raised_7=True,
        )
        assert result is False


class TestTritoneCheck:
    """Tests for tritone prohibition."""

    def test_detects_tritone_4_to_7(self) -> None:
        """Should detect tritone from 4 to 7."""
        key = Key(tonic="A", mode="minor")
        mapper = MelodicMinorMapper(key)

        result = mapper.is_tritone(4, 7)
        assert result is True

    def test_detects_tritone_7_to_4(self) -> None:
        """Should detect tritone from 7 to 4 (descending)."""
        key = Key(tonic="A", mode="minor")
        mapper = MelodicMinorMapper(key)

        result = mapper.is_tritone(7, 4)
        assert result is True

    def test_no_tritone_other_intervals(self) -> None:
        """Other intervals should not be tritones."""
        key = Key(tonic="A", mode="minor")
        mapper = MelodicMinorMapper(key)

        assert not mapper.is_tritone(1, 5)
        assert not mapper.is_tritone(2, 6)
        assert not mapper.is_tritone(3, 7)


class TestValidateMotion:
    """Tests for validate_motion function."""

    def test_valid_motion(self) -> None:
        """Normal motion should be valid."""
        key = Key(tonic="A", mode="minor")
        mapper = MelodicMinorMapper(key)

        is_valid, error = mapper.validate_motion(1, 2, "ascending")
        assert is_valid
        assert error is None

    def test_tritone_invalid(self) -> None:
        """Tritone motion should be invalid."""
        key = Key(tonic="A", mode="minor")
        mapper = MelodicMinorMapper(key)

        is_valid, error = mapper.validate_motion(4, 7, "ascending")
        assert not is_valid
        assert "tritone" in error.lower()

    def test_tritone_allowed_in_dominant_arpeggio(self) -> None:
        """Tritone should be allowed in dominant arpeggio context."""
        key = Key(tonic="A", mode="minor")
        mapper = MelodicMinorMapper(key)

        is_valid, error = mapper.validate_motion(
            4, 7, "ascending", context="dominant_arpeggio"
        )
        assert is_valid


class TestGetInflectedScale:
    """Tests for get_inflected_scale function."""

    def test_major_key_same_both_directions(self) -> None:
        """Major key should have same scale both directions."""
        key = Key(tonic="C", mode="major")
        mapper = MelodicMinorMapper(key)

        asc = mapper.get_inflected_scale("ascending")
        desc = mapper.get_inflected_scale("descending")

        assert asc == desc

    def test_minor_ascending_melodic(self) -> None:
        """Minor ascending should use melodic minor."""
        key = Key(tonic="A", mode="minor")
        mapper = MelodicMinorMapper(key)

        scale = mapper.get_inflected_scale("ascending")
        # Melodic minor ascending: 0, 2, 3, 5, 7, 9, 11
        assert scale == (0, 2, 3, 5, 7, 9, 11)

    def test_minor_descending_natural(self) -> None:
        """Minor descending should use natural minor."""
        key = Key(tonic="A", mode="minor")
        mapper = MelodicMinorMapper(key)

        scale = mapper.get_inflected_scale("descending")
        # Natural minor: 0, 2, 3, 5, 7, 8, 10
        assert scale == key.scale


class TestDetermineDirection:
    """Tests for determine_direction function."""

    def test_ascending(self) -> None:
        """Sequence ending higher should be ascending."""
        assert determine_direction((1, 2, 3)) == "ascending"
        assert determine_direction((1, 3, 5)) == "ascending"

    def test_descending(self) -> None:
        """Sequence ending lower should be descending."""
        assert determine_direction((5, 4, 3)) == "descending"
        assert determine_direction((7, 5, 1)) == "descending"

    def test_static(self) -> None:
        """Sequence ending same should be static."""
        assert determine_direction((3, 4, 3)) == "static"
        assert determine_direction((5, 5)) == "static"

    def test_single_note_static(self) -> None:
        """Single note should be static."""
        assert determine_direction((1,)) == "static"

    def test_empty_static(self) -> None:
        """Empty sequence should be static."""
        assert determine_direction(()) == "static"


class TestFilterMinorUnsafeFigures:
    """Tests for filter_minor_unsafe_figures function."""

    def test_minor_filters_unsafe(self) -> None:
        """Minor key should filter unsafe figures."""
        figures = [
            make_figure("safe", minor_safe=True),
            make_figure("unsafe", minor_safe=False),
        ]

        result = filter_minor_unsafe_figures(figures, is_minor=True)
        names = [f.name for f in result]

        assert "safe" in names
        assert "unsafe" not in names

    def test_major_keeps_all(self) -> None:
        """Major key should keep all figures."""
        figures = [
            make_figure("safe", minor_safe=True),
            make_figure("unsafe", minor_safe=False),
        ]

        result = filter_minor_unsafe_figures(figures, is_minor=False)
        assert len(result) == 2
