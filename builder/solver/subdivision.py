"""Subdivision alignment for N-voice constraint checking.

At each subdivision (attack point), extract the sounding pitch for each voice.
This creates "vertical slices" for checking dissonances, parallel motion, etc.

Adapted from engine/subdivision.py for builder's diatonic Notes type.
"""
from dataclasses import dataclass
from fractions import Fraction

from builder.types import Notes


@dataclass(frozen=True)
class VerticalSlice:
    """All voices at a single subdivision point.

    offset: Time position of this slice (in whole notes from phrase start).
    pitches: Diatonic pitch for each voice (index = voice_index). None if rest.
    """

    offset: Fraction
    pitches: tuple[int | None, ...]

    @property
    def voice_count(self) -> int:
        """Number of voices in this slice."""
        return len(self.pitches)

    def pitch_for_voice(self, index: int) -> int | None:
        """Get pitch for a specific voice index."""
        assert 0 <= index < len(self.pitches), f"Invalid voice index: {index}"
        return self.pitches[index]


@dataclass(frozen=True)
class SliceSequence:
    """Sequence of vertical slices across a phrase."""

    slices: tuple[VerticalSlice, ...]

    @property
    def slice_count(self) -> int:
        """Number of slices in sequence."""
        return len(self.slices)

    def at(self, index: int) -> VerticalSlice:
        """Get slice at index."""
        return self.slices[index]


def collect_attack_points(voices: list[Notes]) -> list[Fraction]:
    """Collect all unique attack points across all voices.

    Returns sorted list of time offsets where any voice attacks a new note.
    """
    offsets: set[Fraction] = set()
    for voice in voices:
        offset: Fraction = Fraction(0)
        for dur in voice.durations:
            offsets.add(offset)
            offset += dur
    return sorted(offsets)


def pitch_at_offset(voice: Notes, target_offset: Fraction) -> int | None:
    """Get the diatonic pitch sounding at target_offset in voice.

    Returns the pitch that was attacked at or before target_offset.
    A pitch of -999 indicates a rest.
    """
    offset: Fraction = Fraction(0)
    sounding_pitch: int | None = None
    for pitch, dur in zip(voice.pitches, voice.durations, strict=True):
        if offset > target_offset:
            break
        # Treat -999 as rest marker (convention)
        sounding_pitch = None if pitch == -999 else pitch
        offset += dur
    return sounding_pitch


def build_slice_sequence(voices: list[Notes]) -> SliceSequence:
    """Build sequence of vertical slices from voice Notes.

    Each slice represents all voices sounding at a single attack point.
    Held notes appear in subsequent slices until their duration ends.
    """
    assert len(voices) > 0, "At least one voice required"
    attack_points: list[Fraction] = collect_attack_points(voices)
    slices: list[VerticalSlice] = []
    for offset in attack_points:
        pitches: list[int | None] = []
        for voice in voices:
            pitch: int | None = pitch_at_offset(voice, offset)
            pitches.append(pitch)
        slices.append(VerticalSlice(offset=offset, pitches=tuple(pitches)))
    return SliceSequence(slices=tuple(slices))


def consecutive_slice_pairs(
    seq: SliceSequence,
) -> list[tuple[VerticalSlice, VerticalSlice]]:
    """Get pairs of consecutive slices for motion checking.

    Parallel motion is checked between consecutive slices.
    """
    pairs: list[tuple[VerticalSlice, VerticalSlice]] = []
    for i in range(1, seq.slice_count):
        pairs.append((seq.at(i - 1), seq.at(i)))
    return pairs
