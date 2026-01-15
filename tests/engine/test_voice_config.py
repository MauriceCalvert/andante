"""Tests for engine.voice_config.

Category A tests: verify voice configuration dataclasses and factory functions.
Tests import only:
- engine.voice_config (module under test)
- stdlib
"""
import pytest
from engine.voice_config import (
    REGISTERS,
    VoiceConfig,
    VoiceSet,
    voice_set_from_count,
)


class TestVoiceConfig:
    """Test VoiceConfig dataclass."""

    def test_attributes(self) -> None:
        """VoiceConfig has index, median, name."""
        vc: VoiceConfig = VoiceConfig(index=0, median=72, name="soprano")
        assert vc.index == 0
        assert vc.median == 72
        assert vc.name == "soprano"

    def test_frozen(self) -> None:
        """VoiceConfig is immutable."""
        vc: VoiceConfig = VoiceConfig(index=0, median=72, name="soprano")
        with pytest.raises(AttributeError):
            vc.index = 1  # type: ignore

    def test_equality(self) -> None:
        """VoiceConfigs with same values are equal."""
        vc1: VoiceConfig = VoiceConfig(index=0, median=72, name="soprano")
        vc2: VoiceConfig = VoiceConfig(index=0, median=72, name="soprano")
        assert vc1 == vc2


class TestVoiceSetBasic:
    """Test VoiceSet basic functionality."""

    def test_count(self) -> None:
        """Count returns number of voices."""
        vs: VoiceSet = VoiceSet(voices=(
            VoiceConfig(0, 72, "soprano"),
            VoiceConfig(1, 48, "bass"),
        ))
        assert vs.count == 2

    def test_by_name(self) -> None:
        """by_name returns voice by name."""
        vs: VoiceSet = VoiceSet(voices=(
            VoiceConfig(0, 72, "soprano"),
            VoiceConfig(1, 48, "bass"),
        ))
        assert vs.by_name("soprano").median == 72
        assert vs.by_name("bass").median == 48

    def test_by_name_not_found(self) -> None:
        """by_name raises KeyError for unknown name."""
        vs: VoiceSet = VoiceSet(voices=(
            VoiceConfig(0, 72, "soprano"),
            VoiceConfig(1, 48, "bass"),
        ))
        with pytest.raises(KeyError):
            vs.by_name("alto")

    def test_by_index(self) -> None:
        """by_index returns voice by index."""
        vs: VoiceSet = VoiceSet(voices=(
            VoiceConfig(0, 72, "soprano"),
            VoiceConfig(1, 48, "bass"),
        ))
        assert vs.by_index(0).name == "soprano"
        assert vs.by_index(1).name == "bass"

    def test_by_index_invalid(self) -> None:
        """by_index raises AssertionError for invalid index."""
        vs: VoiceSet = VoiceSet(voices=(
            VoiceConfig(0, 72, "soprano"),
            VoiceConfig(1, 48, "bass"),
        ))
        with pytest.raises(AssertionError):
            vs.by_index(2)

    def test_frozen(self) -> None:
        """VoiceSet is immutable."""
        vs: VoiceSet = VoiceSet(voices=(
            VoiceConfig(0, 72, "soprano"),
            VoiceConfig(1, 48, "bass"),
        ))
        with pytest.raises(AttributeError):
            vs.voices = ()  # type: ignore


class TestVoiceSetValidation:
    """Test VoiceSet validation in __post_init__."""

    def test_requires_at_least_two_voices(self) -> None:
        """VoiceSet requires at least 2 voices."""
        with pytest.raises(AssertionError, match="at least 2 voices"):
            VoiceSet(voices=(VoiceConfig(0, 72, "soprano"),))

    def test_index_mismatch_raises(self) -> None:
        """Voice index must match position."""
        with pytest.raises(AssertionError, match="index mismatch"):
            VoiceSet(voices=(
                VoiceConfig(1, 72, "soprano"),  # Wrong index
                VoiceConfig(1, 48, "bass"),
            ))


class TestVoiceSetFactories:
    """Test VoiceSet static factory methods."""

    def test_two_voice(self) -> None:
        """two_voice creates soprano and bass."""
        registers: dict[str, int] = {"soprano": 72, "bass": 48}
        vs: VoiceSet = VoiceSet.two_voice(registers)
        assert vs.count == 2
        assert vs.by_name("soprano").median == 72
        assert vs.by_name("bass").median == 48

    def test_trio(self) -> None:
        """trio creates soprano, alto, bass."""
        registers: dict[str, int] = {"soprano": 72, "alto": 65, "bass": 48}
        vs: VoiceSet = VoiceSet.trio(registers)
        assert vs.count == 3
        assert vs.by_index(0).name == "soprano"
        assert vs.by_index(1).name == "alto"
        assert vs.by_index(2).name == "bass"

    def test_satb(self) -> None:
        """satb creates soprano, alto, tenor, bass."""
        registers: dict[str, int] = {"soprano": 72, "alto": 65, "tenor": 60, "bass": 48}
        vs: VoiceSet = VoiceSet.satb(registers)
        assert vs.count == 4
        assert vs.by_index(0).name == "soprano"
        assert vs.by_index(1).name == "alto"
        assert vs.by_index(2).name == "tenor"
        assert vs.by_index(3).name == "bass"

    def test_from_count_two(self) -> None:
        """from_count(2) creates two_voice."""
        registers: dict[str, int] = {"soprano": 72, "bass": 48}
        vs: VoiceSet = VoiceSet.from_count(2, registers)
        assert vs.count == 2

    def test_from_count_three(self) -> None:
        """from_count(3) creates trio."""
        registers: dict[str, int] = {"soprano": 72, "alto": 65, "bass": 48}
        vs: VoiceSet = VoiceSet.from_count(3, registers)
        assert vs.count == 3

    def test_from_count_four(self) -> None:
        """from_count(4) creates satb."""
        registers: dict[str, int] = {"soprano": 72, "alto": 65, "tenor": 60, "bass": 48}
        vs: VoiceSet = VoiceSet.from_count(4, registers)
        assert vs.count == 4

    def test_from_count_invalid(self) -> None:
        """from_count raises for invalid count."""
        registers: dict[str, int] = {}
        with pytest.raises(AssertionError, match="2-4"):
            VoiceSet.from_count(1, registers)
        with pytest.raises(AssertionError, match="2-4"):
            VoiceSet.from_count(5, registers)


class TestRegisters:
    """Test REGISTERS constant loaded from YAML."""

    def test_registers_has_satb(self) -> None:
        """REGISTERS has soprano, alto, tenor, bass."""
        assert "soprano" in REGISTERS
        assert "alto" in REGISTERS
        assert "tenor" in REGISTERS
        assert "bass" in REGISTERS

    def test_registers_are_midi(self) -> None:
        """REGISTERS values are valid MIDI pitches."""
        for name, midi in REGISTERS.items():
            assert 21 <= midi <= 108, f"{name} has invalid MIDI: {midi}"

    def test_soprano_highest(self) -> None:
        """Soprano has highest median."""
        assert REGISTERS["soprano"] > REGISTERS["alto"]
        assert REGISTERS["soprano"] > REGISTERS["tenor"]
        assert REGISTERS["soprano"] > REGISTERS["bass"]

    def test_bass_lowest(self) -> None:
        """Bass has lowest median."""
        assert REGISTERS["bass"] < REGISTERS["soprano"]
        assert REGISTERS["bass"] < REGISTERS["alto"]
        assert REGISTERS["bass"] < REGISTERS["tenor"]


class TestVoiceSetFromCount:
    """Test voice_set_from_count convenience function."""

    def test_returns_two_voice(self) -> None:
        """voice_set_from_count(2) returns two-voice set."""
        vs: VoiceSet = voice_set_from_count(2)
        assert vs.count == 2
        assert vs.by_index(0).name == "soprano"
        assert vs.by_index(1).name == "bass"

    def test_returns_trio(self) -> None:
        """voice_set_from_count(3) returns trio."""
        vs: VoiceSet = voice_set_from_count(3)
        assert vs.count == 3

    def test_returns_satb(self) -> None:
        """voice_set_from_count(4) returns SATB."""
        vs: VoiceSet = voice_set_from_count(4)
        assert vs.count == 4

    def test_uses_loaded_registers(self) -> None:
        """Uses REGISTERS from predicates.yaml."""
        vs: VoiceSet = voice_set_from_count(4)
        assert vs.by_name("soprano").median == REGISTERS["soprano"]
        assert vs.by_name("bass").median == REGISTERS["bass"]
