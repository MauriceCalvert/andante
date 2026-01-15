"""Voice configuration for N-voice architecture.

Dataclasses are pure (registers passed as parameters).
YAML loading provides convenience functions with loaded registers.
"""
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class VoiceConfig:
    """Configuration for a single voice."""
    index: int
    median: int
    name: str


@dataclass(frozen=True)
class VoiceSet:
    """Complete voice configuration for a piece."""
    voices: tuple[VoiceConfig, ...]

    def __post_init__(self) -> None:
        assert len(self.voices) >= 2, "VoiceSet requires at least 2 voices"
        for i, v in enumerate(self.voices):
            assert v.index == i, f"Voice index mismatch: {v.index} != {i}"

    @property
    def count(self) -> int:
        return len(self.voices)

    def by_name(self, name: str) -> VoiceConfig:
        for v in self.voices:
            if v.name == name:
                return v
        raise KeyError(f"No voice named {name}")

    def by_index(self, index: int) -> VoiceConfig:
        assert 0 <= index < len(self.voices), f"Invalid voice index: {index}"
        return self.voices[index]

    @staticmethod
    def from_count(n: int, registers: dict[str, int]) -> "VoiceSet":
        """Create VoiceSet for n voices using standard SATB naming."""
        assert 2 <= n <= 4, f"Voice count must be 2-4, got {n}"
        if n == 2:
            return VoiceSet.two_voice(registers)
        if n == 3:
            return VoiceSet.trio(registers)
        return VoiceSet.satb(registers)

    @staticmethod
    def two_voice(registers: dict[str, int]) -> "VoiceSet":
        return VoiceSet(voices=(
            VoiceConfig(0, registers["soprano"], "soprano"),
            VoiceConfig(1, registers["bass"], "bass"),
        ))

    @staticmethod
    def trio(registers: dict[str, int]) -> "VoiceSet":
        return VoiceSet(voices=(
            VoiceConfig(0, registers["soprano"], "soprano"),
            VoiceConfig(1, registers["alto"], "alto"),
            VoiceConfig(2, registers["bass"], "bass"),
        ))

    @staticmethod
    def satb(registers: dict[str, int]) -> "VoiceSet":
        return VoiceSet(voices=(
            VoiceConfig(0, registers["soprano"], "soprano"),
            VoiceConfig(1, registers["alto"], "alto"),
            VoiceConfig(2, registers["tenor"], "tenor"),
            VoiceConfig(3, registers["bass"], "bass"),
        ))

    @staticmethod
    def interleaved(interleaved_ranges: dict[str, tuple[int, int]]) -> "VoiceSet":
        """Create VoiceSet for interleaved counterpoint (Goldberg-style).
        Both voices share the same tessitura, enabling free voice crossing.
        """
        range_1 = interleaved_ranges["voice_1"]
        range_2 = interleaved_ranges["voice_2"]
        median_1 = (range_1[0] + range_1[1]) // 2
        median_2 = (range_2[0] + range_2[1]) // 2
        return VoiceSet(voices=(
            VoiceConfig(0, median_1, "voice_1"),
            VoiceConfig(1, median_2, "voice_2"),
        ))


# YAML-loaded registers for convenience functions
DATA_DIR: Path = Path(__file__).parent.parent / "data"
with open(DATA_DIR / "predicates.yaml", encoding="utf-8") as _f:
    _predicates: dict = yaml.safe_load(_f)
    REGISTERS: dict[str, int] = _predicates["registers"]
    INTERLEAVED_RANGES: dict[str, tuple[int, int]] = {
        k: tuple(v) for k, v in _predicates.get("interleaved_ranges", {}).items()
    }


def voice_set_from_count(n: int) -> VoiceSet:
    """Create VoiceSet for n voices using standard SATB naming."""
    return VoiceSet.from_count(n, REGISTERS)


def create_interleaved_voices() -> VoiceSet:
    """Create VoiceSet for interleaved (Goldberg-style) counterpoint."""
    return VoiceSet.interleaved(INTERLEAVED_RANGES)


__all__ = [
    "VoiceConfig",
    "VoiceSet",
    "REGISTERS",
    "INTERLEAVED_RANGES",
    "voice_set_from_count",
    "create_interleaved_voices",
]
