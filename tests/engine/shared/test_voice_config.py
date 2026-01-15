"""100% coverage tests for engine.voice_config.

Tests import only:
- engine.voice_config (module under test)
- stdlib
"""
import pytest
from engine.voice_config import (
    VoiceConfig,
    VoiceSet,
)


# Test registers to use across all tests (no YAML loading)
TEST_REGISTERS: dict[str, int] = {
    "soprano": 72,
    "alto": 60,
    "tenor": 53,
    "bass": 48,
}


class TestVoiceConfigConstruction:
    """Test VoiceConfig dataclass construction."""

    def test_valid_construction(self) -> None:
        vc = VoiceConfig(index=0, median=72, name="soprano")
        assert vc.index == 0
        assert vc.median == 72
        assert vc.name == "soprano"

    def test_frozen(self) -> None:
        vc = VoiceConfig(index=0, median=72, name="soprano")
        with pytest.raises(Exception):
            vc.index = 1


class TestVoiceSetConstruction:
    """Test VoiceSet dataclass construction."""

    def test_valid_two_voice(self) -> None:
        vs = VoiceSet(voices=(
            VoiceConfig(0, 72, "soprano"),
            VoiceConfig(1, 48, "bass"),
        ))
        assert vs.count == 2

    def test_valid_four_voice(self) -> None:
        vs = VoiceSet(voices=(
            VoiceConfig(0, 72, "soprano"),
            VoiceConfig(1, 60, "alto"),
            VoiceConfig(2, 53, "tenor"),
            VoiceConfig(3, 48, "bass"),
        ))
        assert vs.count == 4

    def test_less_than_two_voices_raises(self) -> None:
        with pytest.raises(AssertionError, match="at least 2 voices"):
            VoiceSet(voices=(VoiceConfig(0, 72, "soprano"),))

    def test_voice_index_mismatch_raises(self) -> None:
        with pytest.raises(AssertionError, match="Voice index mismatch"):
            VoiceSet(voices=(
                VoiceConfig(0, 72, "soprano"),
                VoiceConfig(2, 48, "bass"),  # Should be index 1
            ))

    def test_frozen(self) -> None:
        vs = VoiceSet(voices=(
            VoiceConfig(0, 72, "soprano"),
            VoiceConfig(1, 48, "bass"),
        ))
        with pytest.raises(Exception):
            vs.voices = ()


class TestVoiceSetProperties:
    """Test VoiceSet property methods."""

    def test_count_two_voice(self) -> None:
        vs = VoiceSet(voices=(
            VoiceConfig(0, 72, "soprano"),
            VoiceConfig(1, 48, "bass"),
        ))
        assert vs.count == 2

    def test_count_three_voice(self) -> None:
        vs = VoiceSet(voices=(
            VoiceConfig(0, 72, "soprano"),
            VoiceConfig(1, 60, "alto"),
            VoiceConfig(2, 48, "bass"),
        ))
        assert vs.count == 3


class TestVoiceSetByName:
    """Test VoiceSet.by_name method."""

    def test_find_soprano(self) -> None:
        vs = VoiceSet(voices=(
            VoiceConfig(0, 72, "soprano"),
            VoiceConfig(1, 48, "bass"),
        ))
        vc = vs.by_name("soprano")
        assert vc.name == "soprano"
        assert vc.index == 0

    def test_find_bass(self) -> None:
        vs = VoiceSet(voices=(
            VoiceConfig(0, 72, "soprano"),
            VoiceConfig(1, 60, "alto"),
            VoiceConfig(2, 48, "bass"),
        ))
        vc = vs.by_name("bass")
        assert vc.name == "bass"
        assert vc.index == 2

    def test_not_found_raises(self) -> None:
        vs = VoiceSet(voices=(
            VoiceConfig(0, 72, "soprano"),
            VoiceConfig(1, 48, "bass"),
        ))
        with pytest.raises(KeyError, match="No voice named"):
            vs.by_name("tenor")


class TestVoiceSetByIndex:
    """Test VoiceSet.by_index method."""

    def test_find_index_0(self) -> None:
        vs = VoiceSet(voices=(
            VoiceConfig(0, 72, "soprano"),
            VoiceConfig(1, 48, "bass"),
        ))
        vc = vs.by_index(0)
        assert vc.index == 0
        assert vc.name == "soprano"

    def test_find_index_1(self) -> None:
        vs = VoiceSet(voices=(
            VoiceConfig(0, 72, "soprano"),
            VoiceConfig(1, 48, "bass"),
        ))
        vc = vs.by_index(1)
        assert vc.index == 1
        assert vc.name == "bass"

    def test_negative_index_raises(self) -> None:
        vs = VoiceSet(voices=(
            VoiceConfig(0, 72, "soprano"),
            VoiceConfig(1, 48, "bass"),
        ))
        with pytest.raises(AssertionError, match="Invalid voice index"):
            vs.by_index(-1)

    def test_out_of_range_index_raises(self) -> None:
        vs = VoiceSet(voices=(
            VoiceConfig(0, 72, "soprano"),
            VoiceConfig(1, 48, "bass"),
        ))
        with pytest.raises(AssertionError, match="Invalid voice index"):
            vs.by_index(5)


class TestVoiceSetFromCount:
    """Test VoiceSet.from_count static method."""

    def test_two_voice(self) -> None:
        vs = VoiceSet.from_count(2, TEST_REGISTERS)
        assert vs.count == 2
        assert vs.voices[0].name == "soprano"
        assert vs.voices[1].name == "bass"

    def test_three_voice(self) -> None:
        vs = VoiceSet.from_count(3, TEST_REGISTERS)
        assert vs.count == 3
        assert vs.voices[0].name == "soprano"
        assert vs.voices[1].name == "alto"
        assert vs.voices[2].name == "bass"

    def test_four_voice(self) -> None:
        vs = VoiceSet.from_count(4, TEST_REGISTERS)
        assert vs.count == 4
        assert vs.voices[0].name == "soprano"
        assert vs.voices[1].name == "alto"
        assert vs.voices[2].name == "tenor"
        assert vs.voices[3].name == "bass"

    def test_invalid_count_1_raises(self) -> None:
        with pytest.raises(AssertionError, match="Voice count must be 2-4"):
            VoiceSet.from_count(1, TEST_REGISTERS)

    def test_invalid_count_5_raises(self) -> None:
        with pytest.raises(AssertionError, match="Voice count must be 2-4"):
            VoiceSet.from_count(5, TEST_REGISTERS)


class TestVoiceSetTwoVoice:
    """Test VoiceSet.two_voice static method."""

    def test_creates_two_voices(self) -> None:
        vs = VoiceSet.two_voice(TEST_REGISTERS)
        assert vs.count == 2

    def test_soprano_properties(self) -> None:
        vs = VoiceSet.two_voice(TEST_REGISTERS)
        assert vs.voices[0].name == "soprano"
        assert vs.voices[0].index == 0
        assert vs.voices[0].median == TEST_REGISTERS["soprano"]

    def test_bass_properties(self) -> None:
        vs = VoiceSet.two_voice(TEST_REGISTERS)
        assert vs.voices[1].name == "bass"
        assert vs.voices[1].index == 1
        assert vs.voices[1].median == TEST_REGISTERS["bass"]


class TestVoiceSetTrio:
    """Test VoiceSet.trio static method."""

    def test_creates_three_voices(self) -> None:
        vs = VoiceSet.trio(TEST_REGISTERS)
        assert vs.count == 3

    def test_voice_names(self) -> None:
        vs = VoiceSet.trio(TEST_REGISTERS)
        assert vs.voices[0].name == "soprano"
        assert vs.voices[1].name == "alto"
        assert vs.voices[2].name == "bass"

    def test_voice_indices(self) -> None:
        vs = VoiceSet.trio(TEST_REGISTERS)
        assert vs.voices[0].index == 0
        assert vs.voices[1].index == 1
        assert vs.voices[2].index == 2

    def test_voice_medians(self) -> None:
        vs = VoiceSet.trio(TEST_REGISTERS)
        assert vs.voices[0].median == TEST_REGISTERS["soprano"]
        assert vs.voices[1].median == TEST_REGISTERS["alto"]
        assert vs.voices[2].median == TEST_REGISTERS["bass"]


class TestVoiceSetSATB:
    """Test VoiceSet.satb static method."""

    def test_creates_four_voices(self) -> None:
        vs = VoiceSet.satb(TEST_REGISTERS)
        assert vs.count == 4

    def test_voice_names(self) -> None:
        vs = VoiceSet.satb(TEST_REGISTERS)
        assert vs.voices[0].name == "soprano"
        assert vs.voices[1].name == "alto"
        assert vs.voices[2].name == "tenor"
        assert vs.voices[3].name == "bass"

    def test_voice_indices(self) -> None:
        vs = VoiceSet.satb(TEST_REGISTERS)
        for i in range(4):
            assert vs.voices[i].index == i

    def test_voice_medians(self) -> None:
        vs = VoiceSet.satb(TEST_REGISTERS)
        assert vs.voices[0].median == TEST_REGISTERS["soprano"]
        assert vs.voices[1].median == TEST_REGISTERS["alto"]
        assert vs.voices[2].median == TEST_REGISTERS["tenor"]
        assert vs.voices[3].median == TEST_REGISTERS["bass"]
