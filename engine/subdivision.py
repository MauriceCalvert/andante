"""Subdivision alignment: align attack points for N-voice constraint checking.

At each subdivision (attack point), we extract the sounding pitch for each voice.
This creates "vertical slices" for checking parallel motion, voice crossing, etc.
"""
from dataclasses import dataclass
from fractions import Fraction

from shared.pitch import Pitch, is_rest
from engine.voice_material import VoiceMaterial


@dataclass(frozen=True)
class VerticalSlice:
    """All voices at a single subdivision point.

    offset: Time position of this slice.
    pitches: Pitch for each voice (index = voice_index). None if rest.
    """
    offset: Fraction
    pitches: tuple[Pitch | None, ...]

    @property
    def voice_count(self) -> int:
        return len(self.pitches)

    def pitch_for_voice(self, index: int) -> Pitch | None:
        assert 0 <= index < len(self.pitches), f"Invalid voice index: {index}"
        return self.pitches[index]


@dataclass(frozen=True)
class SliceSequence:
    """Sequence of vertical slices for a phrase."""
    slices: tuple[VerticalSlice, ...]

    @property
    def slice_count(self) -> int:
        return len(self.slices)

    def at(self, index: int) -> VerticalSlice:
        return self.slices[index]


def collect_attack_points(voices: list[VoiceMaterial]) -> list[Fraction]:
    """Collect all unique attack points across all voices."""
    offsets: set[Fraction] = set()
    for voice in voices:
        offset: Fraction = Fraction(0)
        for dur in voice.durations:
            offsets.add(offset)
            offset += dur
    return sorted(offsets)


def pitch_at_offset(voice: VoiceMaterial, target_offset: Fraction) -> Pitch | None:
    """Get the pitch sounding at target_offset in voice.

    Returns the pitch that was attacked at or before target_offset.
    Returns None if the voice is resting at that point.
    """
    offset: Fraction = Fraction(0)
    sounding_pitch: Pitch | None = None
    for pitch, dur in zip(voice.pitches, voice.durations, strict=True):
        if offset > target_offset:
            break
        if is_rest(pitch):
            sounding_pitch = None
        else:
            sounding_pitch = pitch
        offset += dur
    return sounding_pitch


def build_slice_sequence(voices: list[VoiceMaterial]) -> SliceSequence:
    """Build sequence of vertical slices from voice materials."""
    attack_points: list[Fraction] = collect_attack_points(voices)
    slices: list[VerticalSlice] = []
    for offset in attack_points:
        pitches: list[Pitch | None] = []
        for voice in voices:
            pitch: Pitch | None = pitch_at_offset(voice, offset)
            pitches.append(pitch)
        slices.append(VerticalSlice(offset=offset, pitches=tuple(pitches)))
    return SliceSequence(slices=tuple(slices))


def consecutive_slice_pairs(seq: SliceSequence) -> list[tuple[VerticalSlice, VerticalSlice]]:
    """Get pairs of consecutive slices for motion checking."""
    pairs: list[tuple[VerticalSlice, VerticalSlice]] = []
    for i in range(1, seq.slice_count):
        pairs.append((seq.at(i - 1), seq.at(i)))
    return pairs
