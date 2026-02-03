"""Pillar strategy: hold source anchor pitch for gap duration.

Used for sustained bass notes, held tones, pedal points.
"""
import logging
from fractions import Fraction
from random import Random
from typing import Callable

from builder.writing_strategy import WritingStrategy
from shared.diatonic_pitch import DiatonicPitch
from shared.key import Key
from shared.plan_types import GapPlan

_log: logging.Logger = logging.getLogger(__name__)


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
        """Return single held note at source pitch.

        Note: Pillar notes are structural anchors placed by the planner.
        If the candidate filter rejects them (e.g. due to dissonance with
        prior voices), we log a warning but still return the anchor pitch.
        Structural integrity of the schema takes precedence.
        """
        assert gap.gap_duration > 0, f"Gap duration must be positive, got {gap.gap_duration}"
        if not candidate_filter(source_pitch, Fraction(0)):
            _log.warning(
                "Pillar at bar %d: anchor pitch %s rejected by filter "
                "(likely dissonant with prior voice) — using anyway",
                gap.bar_num, source_pitch,
            )
        return ((source_pitch, gap.gap_duration),)
