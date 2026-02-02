"""Diatonic pitch as linear step count, key-relative.

Single class.  No mod-7 wrapping.  Analogous to MIDI (which counts
semitones) but counting scale degrees.  See phase5_design.md.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class DiatonicPitch:
    """Diatonic pitch as linear step count, key-relative."""
    step: int

    @property
    def degree(self) -> int:
        """Scale degree 1-7."""
        return (self.step % 7) + 1

    @property
    def octave(self) -> int:
        """Diatonic octave (number of complete scales above reference)."""
        return self.step // 7

    def interval_to(self, other: "DiatonicPitch") -> int:
        """Signed diatonic interval.  Positive = up, negative = down."""
        return other.step - self.step

    def transpose(self, steps: int) -> "DiatonicPitch":
        """Move by diatonic steps."""
        return DiatonicPitch(step=self.step + steps)
