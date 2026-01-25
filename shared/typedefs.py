"""Shared types for andante packages."""
from dataclasses import dataclass
from fractions import Fraction

from shared.pitch import Pitch


@dataclass(frozen=True)
class Motif:
    """Musical subject with degrees and durations."""
    degrees: tuple[int, ...]
    durations: tuple[Fraction, ...]
    bars: int

    def __post_init__(self) -> None:
        assert len(self.degrees) == len(self.durations)
        assert all(1 <= d <= 7 for d in self.degrees)


@dataclass(frozen=True)
class Frame:
    """Derived musical parameters."""
    key: str
    mode: str
    metre: str
    tempo: str
    voices: int
    upbeat: Fraction
    form: str


@dataclass(frozen=True)
class VoiceMaterial:
    """Material for a single voice in a phrase."""
    voice_index: int
    pitches: list[Pitch]
    durations: list[Fraction]

    def __post_init__(self) -> None:
        assert len(self.pitches) == len(self.durations), \
            f"Pitch/duration mismatch: {len(self.pitches)} != {len(self.durations)}"

    @property
    def budget(self) -> Fraction:
        return sum(self.durations, Fraction(0))

    @property
    def note_count(self) -> int:
        return len(self.pitches)


@dataclass(frozen=True)
class ExpandedVoices:
    """All voices expanded for a phrase."""
    voices: list[VoiceMaterial]

    def __post_init__(self) -> None:
        assert len(self.voices) >= 2, "ExpandedVoices requires at least 2 voices"
        for i, v in enumerate(self.voices):
            assert v.voice_index == i, f"Voice index mismatch: {v.voice_index} != {i}"

    @property
    def soprano(self) -> VoiceMaterial:
        return self.voices[0]

    @property
    def bass(self) -> VoiceMaterial:
        return self.voices[-1]

    @property
    def count(self) -> int:
        return len(self.voices)

    def inner_voices(self) -> list[VoiceMaterial]:
        return self.voices[1:-1]

    @staticmethod
    def from_two_voices(
        soprano_pitches: list[Pitch],
        soprano_durations: list[Fraction],
        bass_pitches: list[Pitch],
        bass_durations: list[Fraction],
    ) -> "ExpandedVoices":
        """Create ExpandedVoices from two-voice data."""
        return ExpandedVoices(voices=[
            VoiceMaterial(0, soprano_pitches, soprano_durations),
            VoiceMaterial(1, bass_pitches, bass_durations),
        ])

    @staticmethod
    def from_three_voices(
        voice1_pitches: list[Pitch],
        voice1_durations: list[Fraction],
        voice2_pitches: list[Pitch],
        voice2_durations: list[Fraction],
        bass_pitches: list[Pitch],
        bass_durations: list[Fraction],
    ) -> "ExpandedVoices":
        """Create ExpandedVoices from three-voice data (e.g., interleaved + bass)."""
        return ExpandedVoices(voices=[
            VoiceMaterial(0, voice1_pitches, voice1_durations),
            VoiceMaterial(1, voice2_pitches, voice2_durations),
            VoiceMaterial(2, bass_pitches, bass_durations),
        ])
