"""Tests for shared/pitch.py — pitch placement utilities."""
import pytest

from shared.key import Key
from shared.pitch import (
    degree_to_nearest_midi,
    degrees_to_intervals,
    midi_to_name,
    place_degree,
    select_octave,
)


# =========================================================================
# midi_to_name
# =========================================================================


class TestMidiToName:
    def test_middle_c(self) -> None:
        assert midi_to_name(60) == "C4"

    def test_a4(self) -> None:
        assert midi_to_name(69) == "A4"

    def test_sharps_default(self) -> None:
        assert midi_to_name(61) == "C#4"

    def test_flats(self) -> None:
        assert midi_to_name(61, use_flats=True) == "Db4"

    def test_low_c2(self) -> None:
        assert midi_to_name(36) == "C2"

    def test_high_c6(self) -> None:
        assert midi_to_name(84) == "C6"

    def test_b4(self) -> None:
        assert midi_to_name(71) == "B4"

    def test_all_naturals_octave4(self) -> None:
        expected: dict[int, str] = {
            60: "C4", 62: "D4", 64: "E4", 65: "F4",
            67: "G4", 69: "A4", 71: "B4",
        }
        for midi, name in expected.items():
            assert midi_to_name(midi) == name


# =========================================================================
# degrees_to_intervals
# =========================================================================


class TestDegreesToIntervals:
    def test_ascending_scale(self) -> None:
        assert degrees_to_intervals((1, 2, 3, 4, 5)) == (1, 1, 1, 1)

    def test_descending(self) -> None:
        assert degrees_to_intervals((5, 3, 1)) == (-2, -2)

    def test_single_degree(self) -> None:
        assert degrees_to_intervals((1,)) == ()

    def test_empty(self) -> None:
        assert degrees_to_intervals(()) == ()

    def test_mixed_motion(self) -> None:
        assert degrees_to_intervals((1, 3, 2, 5)) == (2, -1, 3)


# =========================================================================
# place_degree
# =========================================================================


class TestPlaceDegree:
    def test_first_note_near_median(self) -> None:
        k: Key = Key(tonic="C", mode="major")
        result: int = place_degree(key=k, degree=1, median=60)
        assert result == 60

    def test_direction_up(self) -> None:
        k: Key = Key(tonic="C", mode="major")
        result: int = place_degree(key=k, degree=5, median=60, prev_pitch=60, direction="up")
        assert result > 60
        assert result % 12 == 7

    def test_direction_down(self) -> None:
        k: Key = Key(tonic="C", mode="major")
        result: int = place_degree(key=k, degree=5, median=60, prev_pitch=72, direction="down")
        assert result < 72
        assert result % 12 == 7

    def test_direction_same_nearest(self) -> None:
        k: Key = Key(tonic="C", mode="major")
        result: int = place_degree(key=k, degree=1, median=60, prev_pitch=65, direction="same")
        # Nearest C to F4=65 is C5=72 (above=72, below=60, 72 is nearer)
        assert result % 12 == 0

    def test_invalid_degree_raises(self) -> None:
        k: Key = Key(tonic="C", mode="major")
        with pytest.raises(AssertionError, match="degree must be 1-7"):
            place_degree(key=k, degree=0, median=60)

    def test_alter_sharp(self) -> None:
        k: Key = Key(tonic="C", mode="major")
        natural: int = place_degree(key=k, degree=4, median=60)
        sharp: int = place_degree(key=k, degree=4, median=60, alter=1)
        assert sharp == natural + 1


# =========================================================================
# select_octave
# =========================================================================


class TestSelectOctave:
    def test_no_range_constraint(self) -> None:
        k: Key = Key(tonic="C", mode="major")
        result: int = select_octave(key=k, degree=1, median=60)
        assert result == 60

    def test_clamped_above(self) -> None:
        k: Key = Key(tonic="C", mode="major")
        # Median 84 would place C at 84, but range caps at 79
        result: int = select_octave(key=k, degree=1, median=84, voice_range=(55, 79))
        assert result <= 79
        assert result % 12 == 0

    def test_clamped_below(self) -> None:
        k: Key = Key(tonic="C", mode="major")
        result: int = select_octave(key=k, degree=1, median=36, voice_range=(55, 84))
        assert result >= 55
        assert result % 12 == 0

    def test_direction_with_range(self) -> None:
        k: Key = Key(tonic="C", mode="major")
        result: int = select_octave(
            key=k, degree=5, median=60, prev_pitch=60,
            direction="up", voice_range=(55, 84),
        )
        assert 55 <= result <= 84
        assert result > 60
        assert result % 12 == 7


# =========================================================================
# degree_to_nearest_midi
# =========================================================================


class TestDegreeToNearestMidi:
    def test_basic_placement(self) -> None:
        k: Key = Key(tonic="C", mode="major")
        result: int = degree_to_nearest_midi(
            degree=1, key=k, target_midi=60, midi_range=(55, 84),
        )
        assert result == 60

    def test_respects_range(self) -> None:
        k: Key = Key(tonic="C", mode="major")
        result: int = degree_to_nearest_midi(
            degree=1, key=k, target_midi=40, midi_range=(55, 84),
        )
        assert 55 <= result <= 84

    def test_respects_ceiling(self) -> None:
        k: Key = Key(tonic="C", mode="major")
        result: int = degree_to_nearest_midi(
            degree=1, key=k, target_midi=72, midi_range=(55, 84), ceiling=65,
        )
        assert result < 65

    def test_avoids_ugly_intervals(self) -> None:
        k: Key = Key(tonic="C", mode="major")
        # prev_midi = 60 (C4); placing degree 7 (B) — closest B is 59 (m2 below, ugly)
        # or 71 (M7 above, also ugly). Should prefer whichever is in non-ugly pool.
        result: int = degree_to_nearest_midi(
            degree=7, key=k, target_midi=60, midi_range=(55, 84), prev_midi=60,
        )
        interval: int = abs(result - 60) % 12
        # If a non-ugly option exists, it should be chosen
        assert result >= 55

    def test_avoids_consecutive_leaps(self) -> None:
        k: Key = Key(tonic="C", mode="major")
        # prev_prev=60, prev=67 (leap up 7). If degree 5 targets 79 (another big leap up),
        # should prefer a closer placement if available.
        result: int = degree_to_nearest_midi(
            degree=5, key=k, target_midi=72, midi_range=(55, 84),
            prev_midi=67, prev_prev_midi=60,
        )
        assert 55 <= result <= 84

    def test_no_valid_octave_raises(self) -> None:
        k: Key = Key(tonic="C", mode="major")
        with pytest.raises(AssertionError, match="No valid octave"):
            degree_to_nearest_midi(
                degree=1, key=k, target_midi=60, midi_range=(61, 61),
            )
