"""Pitch representation for scale degrees and rests."""
from dataclasses import dataclass
from typing import TYPE_CHECKING, Union

from shared.constants import SKIP_SEMITONES, UGLY_INTERVALS

if TYPE_CHECKING:
    from shared.key import Key


@dataclass(frozen=True)
class FloatingNote:
    """Scale degree without octave. Realiser chooses placement."""
    degree: int  # 1-7
    exempt: bool = False
    alter: int = 0

    def __post_init__(self) -> None:
        assert 1 <= self.degree <= 7, f"degree must be 1-7, got {self.degree}"
        assert -2 <= self.alter <= 2, f"alter must be -2 to +2, got {self.alter}"

    def shift(self, interval: int) -> "FloatingNote":
        """Shift by interval, wrapping to 1-7."""
        return FloatingNote(degree=wrap_degree(deg=self.degree + interval), exempt=self.exempt, alter=self.alter)

    def as_exempt(self) -> "FloatingNote":
        """Return copy marked as guard-exempt."""
        return FloatingNote(degree=self.degree, exempt=True, alter=self.alter)

    def with_alter(self, alter: int) -> "FloatingNote":
        """Return copy with specified chromatic alteration."""
        return FloatingNote(degree=self.degree, exempt=self.exempt, alter=alter)

    def flatten(self) -> "FloatingNote":
        """Return copy lowered by a semitone."""
        return FloatingNote(degree=self.degree, exempt=self.exempt, alter=self.alter - 1)

    def sharpen(self) -> "FloatingNote":
        """Return copy raised by a semitone."""
        return FloatingNote(degree=self.degree, exempt=self.exempt, alter=self.alter + 1)


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


def degree_to_nearest_midi(
    degree: int,
    key: "Key",
    target_midi: int,
    midi_range: tuple[int, int],
    ceiling: int | None = None,
    prev_midi: int | None = None,
    prev_prev_midi: int | None = None,
) -> int:
    """Place degree in octave nearest to target_midi, within range and below ceiling."""
    candidates: list[int] = [
        key.degree_to_midi(degree=degree, octave=octave) for octave in range(2, 7)
    ]
    valid: list[int] = [
        m for m in candidates if midi_range[0] <= m <= midi_range[1]
    ]
    if ceiling is not None:
        below: list[int] = [m for m in valid if m < ceiling]
        if below:
            valid = below
    assert len(valid) > 0, (
        f"No valid octave for degree {degree} in range {midi_range}"
    )
    pool: list[int] = valid
    # Prefer candidates that don't form ugly intervals with previous pitch
    if prev_midi is not None:
        non_ugly: list[int] = [
            m for m in pool
            if abs(m - prev_midi) % 12 not in UGLY_INTERVALS
        ]
        if non_ugly:
            pool = non_ugly
    # Prefer candidates that don't create consecutive same-direction leaps
    if prev_midi is not None and prev_prev_midi is not None:
        prev_interval: int = prev_midi - prev_prev_midi
        if abs(prev_interval) > SKIP_SEMITONES:
            no_consec: list[int] = [
                m for m in pool
                if abs(m - prev_midi) <= SKIP_SEMITONES
                or (m - prev_midi > 0) != (prev_interval > 0)
            ]
            if no_consec:
                pool = no_consec
    return min(pool, key=lambda m: abs(m - target_midi))


def wrap_degree(deg: int) -> int:
    """Wrap degree to 1-7 range."""
    assert isinstance(deg, int), f"wrap_degree requires int, got {type(deg).__name__}"
    result: int = ((deg - 1) % 7) + 1
    assert 1 <= result <= 7, f"wrap_degree failed: {deg} -> {result}"
    return result


def place_degree(
    key: "Key",
    degree: int,
    median: int,
    prev_pitch: int | None = None,
    alter: int = 0,
    direction: str | None = None,
) -> int:
    """Place a scale degree as MIDI pitch.

    First note: nearest to median.
    Subsequent notes: follow direction from prev_pitch.

    No selection, no filtering, no cleverness. Pure arithmetic.

    Args:
        key: Musical key
        degree: Scale degree (1-7)
        median: Tessitura median (first note only)
        prev_pitch: Previous MIDI pitch, or None for first note
        alter: Chromatic alteration in semitones
        direction: "up", "down", or "same"

    Returns:
        MIDI pitch.
    """
    assert 1 <= degree <= 7, f"degree must be 1-7, got {degree}"
    base_pc = key.degree_to_midi(degree=degree, octave=0) + alter  # pitch class
    if prev_pitch is None:
        # First note: find octave nearest median
        octave = round((median - base_pc) / 12)
        return base_pc + (octave * 12)
    # Subsequent note: follow direction
    if direction == "up":
        # Find this degree above prev_pitch
        result = base_pc + ((prev_pitch - base_pc) // 12 + 1) * 12
        if result <= prev_pitch:
            result += 12
        return result
    elif direction == "down":
        # Find this degree below prev_pitch
        result = base_pc + ((prev_pitch - base_pc) // 12) * 12
        if result >= prev_pitch:
            result -= 12
        return result
    else:
        # "same" or None: nearest
        above = base_pc + ((prev_pitch - base_pc) // 12 + 1) * 12
        below = above - 12
        if abs(above - prev_pitch) <= abs(below - prev_pitch):
            return above
        return below



def select_octave(
    key: "Key",
    degree: int,
    median: int,
    prev_pitch: int | None = None,
    alter: int = 0,
    direction: str | None = None,
    voice_range: tuple[int, int] | None = None,
) -> int:
    """Place scale degree as MIDI pitch, constrained to voice range."""
    pitch = place_degree(key=key, degree=degree, median=median, prev_pitch=prev_pitch, alter=alter, direction=direction)
    if voice_range is None:
        return pitch
    low, high = voice_range
    # Shift octaves to fit within range
    while pitch > high:
        pitch -= 12
    while pitch < low:
        pitch += 12
    # If still out of range (range < octave), clamp to nearest bound
    if pitch > high:
        pitch = high
    if pitch < low:
        pitch = low
    return pitch

