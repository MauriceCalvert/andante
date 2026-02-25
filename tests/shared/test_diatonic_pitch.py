"""Tests for shared/diatonic_pitch.py — DiatonicPitch dataclass."""
from shared.diatonic_pitch import DiatonicPitch


class TestDegree:
    def test_step_0_is_degree_1(self) -> None:
        assert DiatonicPitch(step=0).degree == 1

    def test_step_6_is_degree_7(self) -> None:
        assert DiatonicPitch(step=6).degree == 7

    def test_step_7_wraps_to_degree_1(self) -> None:
        assert DiatonicPitch(step=7).degree == 1

    def test_step_9_is_degree_3(self) -> None:
        assert DiatonicPitch(step=9).degree == 3

    def test_negative_step(self) -> None:
        dp: DiatonicPitch = DiatonicPitch(step=-1)
        assert dp.degree == 7  # -1 % 7 == 6, +1 == 7


class TestOctave:
    def test_step_0_octave_0(self) -> None:
        assert DiatonicPitch(step=0).octave == 0

    def test_step_7_octave_1(self) -> None:
        assert DiatonicPitch(step=7).octave == 1

    def test_step_14_octave_2(self) -> None:
        assert DiatonicPitch(step=14).octave == 2

    def test_step_6_octave_0(self) -> None:
        assert DiatonicPitch(step=6).octave == 0

    def test_negative_step_octave(self) -> None:
        assert DiatonicPitch(step=-7).octave == -1


class TestIntervalTo:
    def test_ascending_third(self) -> None:
        a: DiatonicPitch = DiatonicPitch(step=0)
        b: DiatonicPitch = DiatonicPitch(step=2)
        assert a.interval_to(b) == 2

    def test_descending_fourth(self) -> None:
        a: DiatonicPitch = DiatonicPitch(step=5)
        b: DiatonicPitch = DiatonicPitch(step=2)
        assert a.interval_to(b) == -3

    def test_unison(self) -> None:
        a: DiatonicPitch = DiatonicPitch(step=4)
        assert a.interval_to(a) == 0

    def test_octave(self) -> None:
        a: DiatonicPitch = DiatonicPitch(step=0)
        b: DiatonicPitch = DiatonicPitch(step=7)
        assert a.interval_to(b) == 7


class TestTranspose:
    def test_up(self) -> None:
        assert DiatonicPitch(step=3).transpose(steps=2).step == 5

    def test_down(self) -> None:
        assert DiatonicPitch(step=3).transpose(steps=-4).step == -1

    def test_zero(self) -> None:
        dp: DiatonicPitch = DiatonicPitch(step=5)
        assert dp.transpose(steps=0) == dp

    def test_immutable(self) -> None:
        dp: DiatonicPitch = DiatonicPitch(step=3)
        result: DiatonicPitch = dp.transpose(steps=1)
        assert dp.step == 3
        assert result.step == 4
