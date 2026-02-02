"""Staggered strategy: delayed entry then hold source pitch.

Used for accompanying voices that enter after the lead.
Delay is computed and applied by VoiceWriter._compute_delay.
This strategy fills only the sounding portion after the delay.
"""
from fractions import Fraction
from random import Random
from typing import Callable
from builder.writing_strategy import WritingStrategy
from shared.diatonic_pitch import DiatonicPitch
from shared.key import Key
from shared.plan_types import GapPlan


class StaggeredStrategy(WritingStrategy):
    """Hold source pitch for the sounding portion after delay."""

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
        """Return single held note at source pitch for sounding duration."""
        assert gap.gap_duration > 0, (
            f"Gap duration must be positive, got {gap.gap_duration}"
        )
        assert candidate_filter(source_pitch, Fraction(0)), (
            f"Staggered source pitch fails filter at bar {gap.bar_num}"
        )
        return ((source_pitch, gap.gap_duration),)
