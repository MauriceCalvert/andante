"""Pitch representation for scale degrees and rests."""
from dataclasses import dataclass
from typing import TYPE_CHECKING, Union

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
    base_pc = key.degree_to_midi(degree, octave=0) + alter  # pitch class
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
    pitch = place_degree(key, degree, median, prev_pitch, alter, direction)
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


def place_anchor_pitch(
    key: "Key",
    degree: int,
    voice_range: tuple[int, int],
    prev_midi: int | None,
    direction: str | None,
) -> int:
    """Place a schema anchor degree as absolute MIDI pitch.
    
    Anchors are placed in a narrower "comfort zone" leaving headroom for
    figuration (±7 diatonic steps). This prevents tessitura excursions.
    
    When direction is explicit ("up"/"down"), voice-leading takes priority
    over comfort zone to ensure smooth melodic motion.
    
    Args:
        key: Musical key for degree-to-pitch conversion.
        degree: Scale degree (1-7).
        voice_range: (low, high) MIDI bounds for this voice.
        prev_midi: Previous anchor's MIDI pitch, or None for first.
        direction: Explicit direction (up/down/same) or None.
    
    Returns:
        MIDI pitch within voice range.
    """
    assert 1 <= degree <= 7, f"degree must be 1-7, got {degree}"
    low, high = voice_range
    assert low < high, f"invalid range: {voice_range}"
    headroom = 7
    comfort_low = low + headroom
    comfort_high = high - headroom
    if comfort_low >= comfort_high:
        comfort_low = low
        comfort_high = high
    base_pc = key.degree_to_midi(degree, octave=0)
    full_candidates: list[int] = []
    for octave in range(0, 10):
        midi = base_pc + octave * 12
        if low <= midi <= high:
            full_candidates.append(midi)
    if not full_candidates:
        median = (low + high) // 2
        best_octave = round((median - base_pc) / 12)
        fallback = base_pc + best_octave * 12
        return max(low, min(high, fallback))
    if prev_midi is None:
        comfort_candidates = [m for m in full_candidates if comfort_low <= m <= comfort_high]
        if comfort_candidates:
            median = (comfort_low + comfort_high) // 2
            return min(comfort_candidates, key=lambda m: abs(m - median))
        return min(full_candidates, key=lambda m: abs(m - (low + high) // 2))
    if direction == "up":
        above = [m for m in full_candidates if m > prev_midi]
        if above:
            return min(above)
        return max(full_candidates)
    if direction == "down":
        below = [m for m in full_candidates if m < prev_midi]
        if below:
            return max(below)
        return min(full_candidates)
    comfort_candidates = [m for m in full_candidates if comfort_low <= m <= comfort_high]
    if comfort_candidates:
        return min(comfort_candidates, key=lambda m: abs(m - prev_midi))
    return min(full_candidates, key=lambda m: abs(m - prev_midi))


def place_anchors_in_tessitura(
    anchors: list,
    upper_range: tuple[int, int],
    lower_range: tuple[int, int],
) -> list:
    """Place all anchors in tessitura, returning new anchors with MIDI set.
    
    Voice-leads from anchor to anchor within each voice's range.
    Uses direction hints from anchor definitions.
    
    Args:
        anchors: List of Anchor objects (with upper_midi/lower_midi as None).
        upper_range: (low, high) MIDI for upper voice (e.g., soprano).
        lower_range: (low, high) MIDI for lower voice (e.g., bass).
    
    Returns:
        New list of Anchor objects with upper_midi and lower_midi populated.
    """
    from dataclasses import replace
    if not anchors:
        return []
    result: list = []
    prev_upper: int | None = None
    prev_lower: int | None = None
    for anchor in anchors:
        upper_midi = place_anchor_pitch(
            key=anchor.local_key,
            degree=anchor.upper_degree,
            voice_range=upper_range,
            prev_midi=prev_upper,
            direction=anchor.upper_direction,
        )
        lower_midi = place_anchor_pitch(
            key=anchor.local_key,
            degree=anchor.lower_degree,
            voice_range=lower_range,
            prev_midi=prev_lower,
            direction=anchor.lower_direction,
        )
        new_anchor = replace(anchor, upper_midi=upper_midi, lower_midi=lower_midi)
        result.append(new_anchor)
        prev_upper = upper_midi
        prev_lower = lower_midi
    return result
