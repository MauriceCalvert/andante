"""Staggered strategy: delayed entry then fill with figuration.

Used for accompanying voices that enter after the lead.
Delay is computed and applied by VoiceWriter._compose_gap.
This strategy fills only the sounding portion after the delay,
delegating to a provided fill strategy (typically FigurationStrategy).
"""
from fractions import Fraction
from random import Random
from typing import Callable
from builder.writing_strategy import WritingStrategy
from shared.diatonic_pitch import DiatonicPitch
from shared.key import Key
from shared.plan_types import GapPlan


class StaggeredStrategy(WritingStrategy):
    """Delayed entry then fill with inner strategy."""

    def __init__(self, fill_strategy: WritingStrategy) -> None:
        self._fill: WritingStrategy = fill_strategy

    def fill_gap(
        self,
        gap: GapPlan,
        source_pitch: DiatonicPitch,
        target_pitch: DiatonicPitch,
        home_key: Key,
        metre: str,
        rng: Random,
        candidate_filter: Callable[[DiatonicPitch, Fraction, bool], str | None],
    ) -> tuple[tuple[DiatonicPitch, Fraction], ...]:
        """Delegate to fill strategy for the sounding portion."""
        assert gap.gap_duration > 0, (
            f"Gap duration must be positive, got {gap.gap_duration}"
        )
        return self._fill.fill_gap(
            gap=gap, source_pitch=source_pitch, target_pitch=target_pitch,
            home_key=home_key, metre=metre, rng=rng, candidate_filter=candidate_filter,
        )
