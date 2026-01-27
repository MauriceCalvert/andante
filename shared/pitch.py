"""Pitch representation for scale degrees and rests."""
from dataclasses import dataclass
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from shared.key import Key

from shared.constants import TESSITURA_DRIFT_THRESHOLD


@dataclass(frozen=True)
class FloatingNote:
    """Scale degree without octave. Realiser chooses placement.

    Supports chromatic alterations via the `alter` field:
    - alter=0: diatonic (default)
    - alter=-1: lowered (flat)
    - alter=+1: raised (sharp)

    Examples:
    - FloatingNote(7) = diatonic 7th (leading tone in major)
    - FloatingNote(7, alter=-1) = lowered 7th (b7)
    - FloatingNote(7, alter=+1) = raised 7th (#7, rare)
    """
    degree: int  # 1-7
    exempt: bool = False  # When True, guards skip this note (e.g., subject material)
    alter: int = 0  # Chromatic alteration: -1=flat, 0=natural, +1=sharp

    def __post_init__(self) -> None:
        assert 1 <= self.degree <= 7, f"degree must be 1-7, got {self.degree}"
        assert -2 <= self.alter <= 2, f"alter must be -2 to +2, got {self.alter}"

    def shift(self, interval: int) -> "FloatingNote":
        """Shift by interval, wrapping to 1-7."""
        return FloatingNote(wrap_degree(self.degree + interval), self.exempt, self.alter)

    def as_exempt(self) -> "FloatingNote":
        """Return copy marked as guard-exempt."""
        return FloatingNote(self.degree, exempt=True, alter=self.alter)

    def with_alter(self, alter: int) -> "FloatingNote":
        """Return copy with specified chromatic alteration."""
        return FloatingNote(self.degree, self.exempt, alter)

    def flatten(self) -> "FloatingNote":
        """Return copy lowered by a semitone."""
        return FloatingNote(self.degree, self.exempt, self.alter - 1)

    def sharpen(self) -> "FloatingNote":
        """Return copy raised by a semitone."""
        return FloatingNote(self.degree, self.exempt, self.alter + 1)


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


def select_octave(
    key: "Key",
    degree: int,
    median: int,
    prev_pitch: int | None = None,
    alter: int = 0,
) -> int:
    """Select octave for a scale degree — canonical pitch placement.

    Two modes:
        Initial (prev_pitch=None): Place degree in octave nearest to median.
        Voice-leading (prev_pitch given): Place nearest to prev_pitch,
            but snap back to median if drift exceeds threshold.

    Args:
        key: Musical key
        degree: Scale degree (1-7)
        median: Tessitura median (gravity centre)
        prev_pitch: Previous MIDI pitch, or None for initial placement
        alter: Chromatic alteration in semitones (default 0)

    Returns:
        MIDI pitch for the degree in the selected octave.
    """
    assert 1 <= degree <= 7, f"degree must be 1-7, got {degree}"
    candidates: list[int] = []
    for octave in range(1, 8):
        midi: int = key.degree_to_midi(degree, octave=octave) + alter
        candidates.append(midi)
    if prev_pitch is None:
        candidates.sort(key=lambda m: abs(m - median))
        return candidates[0]
    candidates.sort(key=lambda m: abs(m - prev_pitch))
    nearest: int = candidates[0]
    if abs(nearest - median) <= TESSITURA_DRIFT_THRESHOLD:
        return nearest
    candidates.sort(key=lambda m: abs(m - median))
    return candidates[0]
