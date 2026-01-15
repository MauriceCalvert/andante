"""Pitch representation for scale degrees and rests."""
from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class FloatingNote:
    """Scale degree without octave. Realiser chooses placement."""
    degree: int  # 1-7
    exempt: bool = False  # When True, guards skip this note (e.g., subject material)

    def __post_init__(self) -> None:
        assert 1 <= self.degree <= 7, f"degree must be 1-7, got {self.degree}"

    def shift(self, interval: int) -> "FloatingNote":
        """Shift by interval, wrapping to 1-7."""
        return FloatingNote(wrap_degree(self.degree + interval), self.exempt)

    def as_exempt(self) -> "FloatingNote":
        """Return copy marked as guard-exempt."""
        return FloatingNote(self.degree, exempt=True)


@dataclass(frozen=True)
class Rest:
    """Represents silence for a duration."""
    pass


@dataclass(frozen=True)
class MidiPitch:
    """Direct MIDI pitch. No conversion needed in realiser."""
    midi: int

    def __post_init__(self) -> None:
        assert 0 <= self.midi <= 127, f"MIDI must be 0-127, got {self.midi}"


Pitch = Union[FloatingNote, MidiPitch, Rest]


def wrap_degree(deg: int) -> int:
    """Wrap degree to 1-7 range."""
    assert isinstance(deg, int), f"wrap_degree requires int, got {type(deg).__name__}"
    result: int = ((deg - 1) % 7) + 1
    assert 1 <= result <= 7, f"wrap_degree failed: {deg} -> {result}"
    return result


def is_rest(p: Pitch) -> bool:
    """Check if pitch is a rest."""
    return isinstance(p, Rest)


def is_floating(p: Pitch) -> bool:
    """Check if pitch is a FloatingNote."""
    return isinstance(p, FloatingNote)


def is_midi_pitch(p: Pitch) -> bool:
    """Check if pitch is a MidiPitch."""
    return isinstance(p, MidiPitch)


CONSONANT_DEGREE_INTERVALS: frozenset[int] = frozenset({0, 2, 4, 5})


def degree_interval(d1: int, d2: int) -> int:
    """Calculate interval between two degrees (mod 7, always positive)."""
    return abs(d1 - d2) % 7


def is_degree_consonant(soprano_deg: int, bass_deg: int) -> bool:
    """Check if two degrees form a consonant interval."""
    interval: int = degree_interval(soprano_deg, bass_deg)
    return interval in CONSONANT_DEGREE_INTERVALS


def cycle_pitch_with_variety(pitches: tuple[Pitch, ...], idx: int) -> Pitch:
    """Get pitch at index with sequential transposition."""
    src_len: int = len(pitches)
    base_idx: int = idx % src_len
    cycle: int = idx // src_len
    p: Pitch = pitches[base_idx]
    if cycle == 0 or not isinstance(p, FloatingNote):
        return p
    return FloatingNote(wrap_degree(p.degree + cycle))
