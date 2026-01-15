"""100% coverage tests for engine.voice_pair.

Tests import only:
- engine.voice_pair (module under test)
- stdlib
"""
import pytest
from engine.voice_pair import VoicePair, VoicePairSet


class TestVoicePairConstruction:
    """Test VoicePair dataclass construction."""

    def test_valid_construction(self) -> None:
        vp = VoicePair(upper_index=0, lower_index=1)
        assert vp.upper_index == 0
        assert vp.lower_index == 1

    def test_same_indices(self) -> None:
        vp = VoicePair(upper_index=2, lower_index=2)
        assert vp.upper_index == 2
        assert vp.lower_index == 2

    def test_frozen(self) -> None:
        vp = VoicePair(upper_index=0, lower_index=1)
        with pytest.raises(Exception):
            vp.upper_index = 2

    def test_equality(self) -> None:
        vp1 = VoicePair(0, 1)
        vp2 = VoicePair(0, 1)
        vp3 = VoicePair(0, 2)
        assert vp1 == vp2
        assert vp1 != vp3

    def test_hashable(self) -> None:
        vp1 = VoicePair(0, 1)
        vp2 = VoicePair(0, 1)
        s = {vp1, vp2}
        assert len(s) == 1


class TestVoicePairSetConstruction:
    """Test VoicePairSet dataclass construction."""

    def test_valid_construction(self) -> None:
        pairs = (VoicePair(0, 1), VoicePair(0, 2))
        vps = VoicePairSet(pairs=pairs)
        assert vps.pairs == pairs

    def test_empty_pairs(self) -> None:
        vps = VoicePairSet(pairs=())
        assert vps.pairs == ()
        assert vps.count == 0


class TestVoicePairSetCompute:
    """Test VoicePairSet.compute static method."""

    def test_two_voices(self) -> None:
        vps = VoicePairSet.compute(2)
        assert vps.count == 1
        assert vps.pairs[0] == VoicePair(0, 1)

    def test_three_voices(self) -> None:
        vps = VoicePairSet.compute(3)
        assert vps.count == 3
        pair_tuples = {(p.upper_index, p.lower_index) for p in vps.pairs}
        assert pair_tuples == {(0, 1), (0, 2), (1, 2)}

    def test_four_voices(self) -> None:
        vps = VoicePairSet.compute(4)
        assert vps.count == 6
        pair_tuples = {(p.upper_index, p.lower_index) for p in vps.pairs}
        assert pair_tuples == {(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)}

    def test_five_voices(self) -> None:
        vps = VoicePairSet.compute(5)
        assert vps.count == 10  # 5*4/2 = 10

    def test_pair_count_formula(self) -> None:
        for n in range(2, 8):
            vps = VoicePairSet.compute(n)
            expected = n * (n - 1) // 2
            assert vps.count == expected

    def test_one_voice_raises(self) -> None:
        with pytest.raises(AssertionError, match="at least 2 voices"):
            VoicePairSet.compute(1)

    def test_zero_voices_raises(self) -> None:
        with pytest.raises(AssertionError, match="at least 2 voices"):
            VoicePairSet.compute(0)

    def test_negative_voices_raises(self) -> None:
        with pytest.raises(AssertionError, match="at least 2 voices"):
            VoicePairSet.compute(-1)


class TestVoicePairSetProperties:
    """Test VoicePairSet property methods."""

    def test_count_two_voice(self) -> None:
        vps = VoicePairSet.compute(2)
        assert vps.count == 1

    def test_count_manual_construction(self) -> None:
        pairs = (VoicePair(0, 1), VoicePair(1, 2), VoicePair(2, 3))
        vps = VoicePairSet(pairs=pairs)
        assert vps.count == 3


class TestVoicePairSetPairOrder:
    """Test that pairs are generated in consistent order."""

    def test_upper_always_less_than_lower(self) -> None:
        for n in range(2, 6):
            vps = VoicePairSet.compute(n)
            for pair in vps.pairs:
                assert pair.upper_index < pair.lower_index

    def test_pairs_sorted_by_upper_then_lower(self) -> None:
        vps = VoicePairSet.compute(4)
        pairs = list(vps.pairs)
        expected = [
            VoicePair(0, 1), VoicePair(0, 2), VoicePair(0, 3),
            VoicePair(1, 2), VoicePair(1, 3),
            VoicePair(2, 3),
        ]
        assert pairs == expected
