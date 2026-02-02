"""Abstract base class for voice writing strategies.

One method.  Concrete strategies implement fill_gap to produce
(DiatonicPitch, Fraction) pairs filling a gap between anchors.
"""
from abc import ABC, abstractmethod
from fractions import Fraction
from random import Random
from typing import Callable

from shared.diatonic_pitch import DiatonicPitch
from shared.key import Key
from shared.plan_types import GapPlan


class WritingStrategy(ABC):
    """Strategy for filling a gap between two anchors."""

    @abstractmethod
    def fill_gap(
        self,
        gap: GapPlan,
        source_pitch: DiatonicPitch,
        target_pitch: DiatonicPitch,
        home_key: Key,
        metre: str,
        rng: Random,
        candidate_filter: Callable[[DiatonicPitch, Fraction], bool],
    ) -> tuple[tuple[DiatonicPitch, Fraction], ...]:
        """Return (pitch, duration) pairs filling the gap.

        candidate_filter: called for each candidate note.
        Returns True if the note passes counterpoint and range checks.
        The strategy must not emit notes that fail the filter.
        """
        ...
