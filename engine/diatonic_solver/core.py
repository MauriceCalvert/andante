"""Core types for diatonic inner voice solver.

All types operate in degree space (1-7). Octave placement is a separate concern
handled only when building final output or when realising to MIDI.
"""
from dataclasses import dataclass
from fractions import Fraction
from typing import Tuple

from shared.pitch import FloatingNote, Pitch, Rest, is_rest


@dataclass(frozen=True)
class DiatonicPitch:
    """Pitch in degree space with relative octave.

    The degree is always 1-7. The octave_offset indicates relative position
    from the voice's default register (0=soprano, -1=alto, -2=tenor, -3=bass).
    """
    degree: int  # 1-7
    octave_offset: int = 0  # Relative to voice's default octave

    def __post_init__(self) -> None:
        assert 1 <= self.degree <= 7, f"degree must be 1-7, got {self.degree}"

    @classmethod
    def from_floating(cls, note: FloatingNote, octave_offset: int = 0) -> "DiatonicPitch":
        """Create from FloatingNote."""
        return cls(degree=note.degree, octave_offset=octave_offset)

    def to_floating(self) -> FloatingNote:
        """Convert to FloatingNote (loses octave info)."""
        return FloatingNote(self.degree)


@dataclass(frozen=True)
class DiatonicSlice:
    """Vertical sonority in degree space.

    Represents all sounding voices at a single point in time.
    None indicates a rest for that voice.
    """
    offset: Fraction
    pitches: Tuple[DiatonicPitch | None, ...]  # None = rest, indexed by voice

    @property
    def voice_count(self) -> int:
        return len(self.pitches)

    def get_degree(self, voice_idx: int) -> int | None:
        """Get degree for voice, or None if resting."""
        pitch = self.pitches[voice_idx]
        return pitch.degree if pitch is not None else None


@dataclass(frozen=True)
class VoiceConstraints:
    """Constraints for a single voice.

    Defines the valid degree range and preferred octave register for a voice.
    """
    voice_index: int
    degree_range: Tuple[int, int] = (1, 7)  # All degrees valid by default
    preferred_octave: int = 0  # Relative: 0=soprano, -1=alto, -2=tenor, -3=bass

    def is_valid_degree(self, degree: int) -> bool:
        """Check if degree is within valid range."""
        return self.degree_range[0] <= degree <= self.degree_range[1]


# Default voice constraints for 4-voice texture
DEFAULT_VOICE_CONSTRAINTS: dict[int, VoiceConstraints] = {
    0: VoiceConstraints(voice_index=0, preferred_octave=0),   # Soprano
    1: VoiceConstraints(voice_index=1, preferred_octave=-1),  # Alto
    2: VoiceConstraints(voice_index=2, preferred_octave=-2),  # Tenor
    3: VoiceConstraints(voice_index=3, preferred_octave=-3),  # Bass
}


def get_voice_constraints(voice_count: int) -> list[VoiceConstraints]:
    """Get default constraints for given voice count."""
    if voice_count == 2:
        return [
            VoiceConstraints(voice_index=0, preferred_octave=0),
            VoiceConstraints(voice_index=1, preferred_octave=-3),
        ]
    elif voice_count == 3:
        return [
            VoiceConstraints(voice_index=0, preferred_octave=0),
            VoiceConstraints(voice_index=1, preferred_octave=-1),
            VoiceConstraints(voice_index=2, preferred_octave=-3),
        ]
    else:  # 4 voices
        return [
            VoiceConstraints(voice_index=0, preferred_octave=0),
            VoiceConstraints(voice_index=1, preferred_octave=-1),
            VoiceConstraints(voice_index=2, preferred_octave=-2),
            VoiceConstraints(voice_index=3, preferred_octave=-3),
        ]


def extract_degrees_from_voice(
    pitches: tuple[Pitch, ...],
    durations: tuple[Fraction, ...],
) -> list[tuple[Fraction, int | None, Fraction]]:
    """Extract (offset, degree, duration) from voice material.

    Returns list of (offset, degree, duration) tuples.
    degree is None for rests.
    """
    events: list[tuple[Fraction, int | None, Fraction]] = []
    offset = Fraction(0)
    for p, d in zip(pitches, durations):
        if is_rest(p):
            events.append((offset, None, d))
        elif isinstance(p, FloatingNote):
            events.append((offset, p.degree, d))
        else:
            raise TypeError(f"Expected FloatingNote or Rest, got {type(p)}")
        offset += d
    return events


def build_slices_from_voices(
    soprano_events: list[tuple[Fraction, int | None, Fraction]],
    bass_events: list[tuple[Fraction, int | None, Fraction]],
    voice_count: int,
) -> list[DiatonicSlice]:
    """Build slice sequence from soprano and bass events.

    Creates a slice at each attack point in soprano.
    Inner voice pitches are initially None (to be solved).
    """
    # Build bass lookup by offset
    bass_by_offset: dict[Fraction, int | None] = {}
    for off, deg, _ in bass_events:
        bass_by_offset[off] = deg

    bass_offsets = sorted(bass_by_offset.keys())

    slices: list[DiatonicSlice] = []
    for sop_off, sop_deg, _ in soprano_events:
        if sop_deg is None:
            continue  # Skip rests in soprano

        # Find bass sounding at this offset
        bass_deg: int | None = None
        for b_off in reversed(bass_offsets):
            if b_off <= sop_off:
                bass_deg = bass_by_offset[b_off]
                break

        if bass_deg is None:
            continue

        # Build pitch tuple: soprano + inner voices (None) + bass
        pitches: list[DiatonicPitch | None] = [DiatonicPitch(sop_deg)]
        for _ in range(voice_count - 2):
            pitches.append(None)  # Inner voices to be solved
        pitches.append(DiatonicPitch(bass_deg))

        slices.append(DiatonicSlice(offset=sop_off, pitches=tuple(pitches)))

    return slices
