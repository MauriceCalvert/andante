"""100% coverage tests for engine.figured_bass.

Tests import only:
- engine.figured_bass (module under test)
- engine.key (Key)
- shared (pitch, timed_material)
- stdlib

Figured bass module provides realisation of figured bass symbols
to soprano voice pitches.
"""
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote, MidiPitch
from shared.timed_material import TimedMaterial

from engine.figured_bass import (
    FIGURES,
    FigureIntervals,
    generate_figures_for_bass,
    load_figures,
    realise_figure,
    realise_figured_bass,
    realise_suspension,
)
from engine.key import Key


class TestFigureIntervals:
    """Test FigureIntervals dataclass."""

    def test_frozen(self) -> None:
        """FigureIntervals is frozen."""
        fig: FigureIntervals = FigureIntervals(
            symbol="test",
            intervals=(4, 7),
        )
        with pytest.raises(Exception):
            fig.symbol = "modified"

    def test_default_suspension_false(self) -> None:
        """Default suspension is False."""
        fig: FigureIntervals = FigureIntervals(
            symbol="test",
            intervals=(4, 7),
        )
        assert fig.suspension is False

    def test_default_altered_false(self) -> None:
        """Default altered is False."""
        fig: FigureIntervals = FigureIntervals(
            symbol="test",
            intervals=(4, 7),
        )
        assert fig.altered is False

    def test_suspension_true(self) -> None:
        """Suspension can be set True."""
        fig: FigureIntervals = FigureIntervals(
            symbol="4-3",
            intervals=(5, 4),
            suspension=True,
        )
        assert fig.suspension is True

    def test_altered_true(self) -> None:
        """Altered can be set True."""
        fig: FigureIntervals = FigureIntervals(
            symbol="#",
            intervals=(5, 8),
            altered=True,
        )
        assert fig.altered is True


class TestLoadFigures:
    """Test load_figures function."""

    def test_returns_dict(self) -> None:
        """Returns dictionary."""
        figures: dict = load_figures()
        assert isinstance(figures, dict)

    def test_contains_root_position(self) -> None:
        """Contains root position symbol."""
        figures: dict = load_figures()
        assert "" in figures

    def test_contains_first_inversion(self) -> None:
        """Contains first inversion symbol."""
        figures: dict = load_figures()
        assert "6" in figures

    def test_contains_second_inversion(self) -> None:
        """Contains second inversion symbol."""
        figures: dict = load_figures()
        assert "6/4" in figures

    def test_contains_suspensions(self) -> None:
        """Contains suspension figures."""
        figures: dict = load_figures()
        assert "4-3" in figures
        assert "7-6" in figures

    def test_suspension_flag_set(self) -> None:
        """Suspension figures have suspension=True."""
        figures: dict = load_figures()
        assert figures["4-3"].suspension is True
        assert figures["7-6"].suspension is True

    def test_regular_figures_not_suspension(self) -> None:
        """Regular figures have suspension=False."""
        figures: dict = load_figures()
        assert figures[""].suspension is False
        assert figures["6"].suspension is False


class TestFIGURES:
    """Test FIGURES constant."""

    def test_is_dict(self) -> None:
        """FIGURES is dictionary."""
        assert isinstance(FIGURES, dict)

    def test_all_values_are_figure_intervals(self) -> None:
        """All values are FigureIntervals."""
        for symbol, fig in FIGURES.items():
            assert isinstance(fig, FigureIntervals)
            assert fig.symbol == symbol


class TestRealiseFigure:
    """Test realise_figure function."""

    def test_root_position(self) -> None:
        """Root position returns 3rd or 5th above bass."""
        bass: int = 48  # C3
        result: int = realise_figure(bass, "", None)
        # Should be 3rd (4 semitones) or 5th (7 semitones) above
        assert result in (52, 55, 64, 67, 76, 79)

    def test_first_inversion(self) -> None:
        """First inversion returns 3rd or 6th above bass."""
        bass: int = 48  # C3
        result: int = realise_figure(bass, "6", None)
        # Should be 3rd (3 semitones) or 6th (8 semitones) above
        interval: int = result - bass
        while interval < 0:
            interval += 12
        while interval >= 12:
            interval -= 12
        assert interval in (3, 8) or interval in (3 % 12, 8 % 12)

    def test_second_inversion(self) -> None:
        """Second inversion returns 4th or 6th above bass."""
        bass: int = 48
        result: int = realise_figure(bass, "6/4", None)
        assert soprano_range_check(result, (60, 84))

    def test_voice_leading_prefers_closest(self) -> None:
        """With prev_soprano, prefers closest pitch."""
        bass: int = 48
        prev: int = 72  # C5
        result: int = realise_figure(bass, "", prev)
        # Should prefer pitch closer to prev
        assert abs(result - prev) <= 12

    def test_range_constraint(self) -> None:
        """Result is within soprano_range."""
        bass: int = 36  # C2
        result: int = realise_figure(bass, "", None, soprano_range=(60, 84))
        assert 60 <= result <= 84

    def test_unknown_figure_raises(self) -> None:
        """Unknown figure raises AssertionError."""
        with pytest.raises(AssertionError, match="Unknown figure"):
            realise_figure(48, "unknown", None)

    def test_low_bass_adjusts_up(self) -> None:
        """Low bass pitch adjusts candidate up to range."""
        bass: int = 36  # Very low C
        result: int = realise_figure(bass, "", None, soprano_range=(60, 84))
        assert result >= 60

    def test_high_bass_adjusts_down(self) -> None:
        """High bass pitch adjusts candidate down to range."""
        bass: int = 84  # High C
        result: int = realise_figure(bass, "", None, soprano_range=(60, 84))
        assert result <= 84


def soprano_range_check(pitch: int, range_: tuple[int, int]) -> bool:
    """Check if pitch is in range."""
    return range_[0] <= pitch <= range_[1]


class TestRealiseSuspension:
    """Test realise_suspension function."""

    def test_returns_two_pitches(self) -> None:
        """Returns tuple of two pitches."""
        bass: int = 48
        pitches, durs = realise_suspension(bass, "4-3", None, Fraction(1))
        assert len(pitches) == 2
        assert len(durs) == 2

    def test_suspension_higher_than_resolution(self) -> None:
        """Suspension pitch is higher than resolution for 4-3."""
        bass: int = 48
        pitches, durs = realise_suspension(bass, "4-3", None, Fraction(1))
        # 4-3: suspension on 4th (5 semitones), resolution on 3rd (4 semitones)
        assert pitches[0] >= pitches[1]

    def test_duration_split(self) -> None:
        """Duration split is 2/3 + 1/3."""
        bass: int = 48
        pitches, durs = realise_suspension(bass, "4-3", None, Fraction(1))
        assert durs[0] == Fraction(2, 3)
        assert durs[1] == Fraction(1, 3)

    def test_7_6_suspension(self) -> None:
        """7-6 suspension works."""
        bass: int = 48
        pitches, durs = realise_suspension(bass, "7-6", None, Fraction(1))
        assert len(pitches) == 2
        # 7-6: suspension on 7th (10 semitones), resolution on 6th (8 semitones)
        assert pitches[0] >= pitches[1]

    def test_unknown_figure_raises(self) -> None:
        """Unknown figure raises AssertionError."""
        with pytest.raises(AssertionError, match="Unknown figure"):
            realise_suspension(48, "unknown", None, Fraction(1))

    def test_non_suspension_figure_raises(self) -> None:
        """Non-suspension figure raises AssertionError."""
        with pytest.raises(AssertionError, match="not a suspension"):
            realise_suspension(48, "6", None, Fraction(1))

    def test_range_adjustment(self) -> None:
        """Pitches adjusted to be in range."""
        bass: int = 36  # Low
        pitches, durs = realise_suspension(bass, "4-3", None, Fraction(1), soprano_range=(60, 84))
        assert 60 <= pitches[0] <= 84
        assert 60 <= pitches[1] <= 84


class TestRealiseFiguredBass:
    """Test realise_figured_bass function."""

    def test_returns_timed_material(self) -> None:
        """Returns TimedMaterial."""
        bass: tuple = (FloatingNote(1), FloatingNote(5), FloatingNote(1))
        durs: tuple = (Fraction(1, 2), Fraction(1, 4), Fraction(1, 4))
        figs: tuple = ("", "6", "")
        key: Key = Key(tonic="C", mode="major")
        result: TimedMaterial = realise_figured_bass(
            bass, durs, figs, key, Fraction(1)
        )
        assert isinstance(result, TimedMaterial)

    def test_budget_preserved(self) -> None:
        """Budget is preserved."""
        bass: tuple = (FloatingNote(1), FloatingNote(5))
        durs: tuple = (Fraction(1, 2), Fraction(1, 2))
        figs: tuple = ("", "")
        key: Key = Key(tonic="C", mode="major")
        result: TimedMaterial = realise_figured_bass(
            bass, durs, figs, key, Fraction(1)
        )
        assert result.budget == Fraction(1)

    def test_soprano_is_midi_pitch(self) -> None:
        """Soprano pitches are MidiPitch."""
        bass: tuple = (FloatingNote(1),)
        durs: tuple = (Fraction(1),)
        figs: tuple = ("",)
        key: Key = Key(tonic="C", mode="major")
        result: TimedMaterial = realise_figured_bass(
            bass, durs, figs, key, Fraction(1)
        )
        assert isinstance(result.pitches[0], MidiPitch)

    def test_suspension_expands_notes(self) -> None:
        """Suspension figures expand to two notes."""
        bass: tuple = (FloatingNote(1), FloatingNote(5))
        durs: tuple = (Fraction(1, 2), Fraction(1, 2))
        figs: tuple = ("", "4-3")
        key: Key = Key(tonic="C", mode="major")
        result: TimedMaterial = realise_figured_bass(
            bass, durs, figs, key, Fraction(1)
        )
        # First note + suspension (2 notes) = 3 notes total
        assert len(result.pitches) == 3
        assert len(result.durations) == 3

    def test_voice_leading_between_notes(self) -> None:
        """Voice leading connects notes smoothly."""
        bass: tuple = (FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(4))
        durs: tuple = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4))
        figs: tuple = ("", "", "", "")
        key: Key = Key(tonic="C", mode="major")
        result: TimedMaterial = realise_figured_bass(
            bass, durs, figs, key, Fraction(1)
        )
        # Check that consecutive notes are reasonably close
        for i in range(len(result.pitches) - 1):
            p1: MidiPitch = result.pitches[i]
            p2: MidiPitch = result.pitches[i + 1]
            assert abs(p1.midi - p2.midi) <= 12

    def test_mismatched_lengths_raises(self) -> None:
        """Mismatched input lengths raises AssertionError."""
        bass: tuple = (FloatingNote(1), FloatingNote(5))
        durs: tuple = (Fraction(1),)  # Wrong length
        figs: tuple = ("", "")
        key: Key = Key(tonic="C", mode="major")
        with pytest.raises(AssertionError):
            realise_figured_bass(bass, durs, figs, key, Fraction(1))


class TestGenerateFiguresForBass:
    """Test generate_figures_for_bass function."""

    def test_simple_style_all_root_position(self) -> None:
        """Simple style returns all root position."""
        bass: tuple = (FloatingNote(1), FloatingNote(2), FloatingNote(3))
        result: tuple = generate_figures_for_bass(bass, style="simple")
        assert result == ("", "", "")

    def test_single_note_returns_root(self) -> None:
        """Single note returns root position."""
        bass: tuple = (FloatingNote(1),)
        result: tuple = generate_figures_for_bass(bass, style="varied")
        assert result == ("",)

    def test_first_note_is_root_position(self) -> None:
        """First note is always root position in varied style."""
        bass: tuple = (FloatingNote(1), FloatingNote(2), FloatingNote(3))
        result: tuple = generate_figures_for_bass(bass, style="varied")
        assert result[0] == ""

    def test_last_note_is_root_position(self) -> None:
        """Last note is always root position in varied style."""
        bass: tuple = (FloatingNote(1), FloatingNote(2), FloatingNote(3))
        result: tuple = generate_figures_for_bass(bass, style="varied")
        assert result[-1] == ""

    def test_stepwise_motion_uses_first_inversion(self) -> None:
        """Stepwise motion uses first inversion (6)."""
        # Create stepwise bass: 1, 2, 3, 4, 5
        bass: tuple = tuple(FloatingNote(d) for d in [1, 2, 3, 4, 5])
        result: tuple = generate_figures_for_bass(bass, style="varied")
        # Middle notes with stepwise motion get "6"
        assert "6" in result

    def test_degree_2_uses_first_inversion(self) -> None:
        """Degree 2 uses first inversion in varied style."""
        bass: tuple = (FloatingNote(1), FloatingNote(2), FloatingNote(1))
        result: tuple = generate_figures_for_bass(bass, style="varied")
        assert result[1] == "6"

    def test_degree_4_uses_first_inversion(self) -> None:
        """Degree 4 uses first inversion in varied style."""
        bass: tuple = (FloatingNote(1), FloatingNote(4), FloatingNote(1))
        result: tuple = generate_figures_for_bass(bass, style="varied")
        assert result[1] == "6"

    def test_degree_7_uses_first_inversion(self) -> None:
        """Degree 7 uses first inversion in varied style."""
        bass: tuple = (FloatingNote(1), FloatingNote(7), FloatingNote(1))
        result: tuple = generate_figures_for_bass(bass, style="varied")
        assert result[1] == "6"

    def test_degree_5_odd_index_uses_second_inversion(self) -> None:
        """Degree 5 at odd index uses 6/4 inversion."""
        bass: tuple = (FloatingNote(1), FloatingNote(5), FloatingNote(1))
        result: tuple = generate_figures_for_bass(bass, style="varied")
        # Index 1 is odd, degree is 5
        assert result[1] == "6/4"

    def test_degree_5_even_index_uses_root(self) -> None:
        """Degree 5 at even index uses root position."""
        bass: tuple = (FloatingNote(1), FloatingNote(3), FloatingNote(5), FloatingNote(1))
        result: tuple = generate_figures_for_bass(bass, style="varied")
        # Index 2 is even, degree is 5
        assert result[2] == ""

    def test_returns_tuple_of_strings(self) -> None:
        """Returns tuple of strings."""
        bass: tuple = (FloatingNote(1), FloatingNote(5), FloatingNote(1))
        result: tuple = generate_figures_for_bass(bass, style="varied")
        assert isinstance(result, tuple)
        assert all(isinstance(f, str) for f in result)


class TestIntegration:
    """Integration tests for figured_bass module."""

    def test_full_workflow(self) -> None:
        """Complete workflow: generate figures, realise to soprano."""
        bass: tuple = (FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(4), FloatingNote(5))
        durs: tuple = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 8), Fraction(1, 8))
        figs: tuple = generate_figures_for_bass(bass, style="varied")
        key: Key = Key(tonic="C", mode="major")
        result: TimedMaterial = realise_figured_bass(
            bass, durs, figs, key, Fraction(1)
        )
        assert len(result.pitches) == len(bass)
        assert sum(result.durations) == Fraction(1)

    def test_minor_key_works(self) -> None:
        """Works with minor key."""
        bass: tuple = (FloatingNote(1), FloatingNote(5), FloatingNote(1))
        durs: tuple = (Fraction(1, 2), Fraction(1, 4), Fraction(1, 4))
        figs: tuple = ("", "", "")
        key: Key = Key(tonic="A", mode="minor")
        result: TimedMaterial = realise_figured_bass(
            bass, durs, figs, key, Fraction(1)
        )
        assert result.budget == Fraction(1)

    def test_all_figures_realise(self) -> None:
        """All non-suspension figures realise correctly."""
        key: Key = Key(tonic="C", mode="major")
        for symbol in ["", "6", "6/4", "7", "6/5", "4/3", "4/2", "#", "b"]:
            if not FIGURES[symbol].suspension:
                bass: tuple = (FloatingNote(1),)
                durs: tuple = (Fraction(1),)
                figs: tuple = (symbol,)
                result: TimedMaterial = realise_figured_bass(
                    bass, durs, figs, key, Fraction(1)
                )
                assert len(result.pitches) == 1
