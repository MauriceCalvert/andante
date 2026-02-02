"""Pillar strategy: hold source anchor pitch for gap duration.

Used for sustained bass notes, held tones, pedal points.
"""
from fractions import Fraction
from random import Random
from typing import Callable

from builder.writing_strategy import WritingStrategy
from shared.diatonic_pitch import DiatonicPitch
from shared.key import Key
from shared.plan_types import GapPlan


class PillarStrategy(WritingStrategy):
    """Hold the source anchor pitch for the entire gap."""

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
        """Return single held note at source pitch."""
        assert gap.gap_duration > 0, f"Gap duration must be positive, got {gap.gap_duration}"
        if not candidate_filter(source_pitch, Fraction(0)):
            assert False, (
                f"Pillar source pitch {source_pitch} fails candidate filter "
                f"at bar {gap.bar_num} — planner placed anchor out of range"
            )
        return ((source_pitch, gap.gap_duration),)
