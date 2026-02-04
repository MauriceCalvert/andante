"""Pillar strategy: hold source anchor pitch for gap duration.

Used for sustained bass notes, held tones, pedal points.
When anchor pitch fails candidate filter, tries consonant alternatives.
"""
import logging
from fractions import Fraction
from random import Random
from typing import Callable

from builder.types import FigureRejection, FigureRejectionError
from builder.writing_strategy import WritingStrategy
from shared.diatonic_pitch import DiatonicPitch
from shared.key import Key
from shared.plan_types import GapPlan

_log: logging.Logger = logging.getLogger(__name__)
_CONSONANT_OFFSETS: tuple[int, ...] = (0, -7, 7, -2, 2, -4, 4, -5, 5, -3, 3)


class PillarStrategy(WritingStrategy):
    """Hold a consonant pitch for the entire gap."""

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
        """Return single held note, preferring source pitch if it passes filter.

        Tries source pitch first, then alternatives at consonant intervals.
        All alternatives are checked with candidate_filter which includes
        melodic interval, consonance, and voice overlap checks.
        """
        assert gap.gap_duration > 0, f"Gap duration must be positive, got {gap.gap_duration}"
        rejections: list[FigureRejection] = []
        for offset in _CONSONANT_OFFSETS:
            pitch: DiatonicPitch = source_pitch.transpose(steps=offset)
            reason: str | None = candidate_filter(pitch, Fraction(0), True)
            if reason is None:
                if offset != 0:
                    _log.debug(
                        "Pillar at bar %d: using %s instead of %s",
                        gap.bar_num, pitch, source_pitch,
                    )
                return ((pitch, gap.gap_duration),)
            rejections.append(FigureRejection(
                figure_name=f"pillar(offset={offset})",
                note_index=0,
                pitch=str(pitch),
                offset="0",
                reason=reason,
            ))
        raise FigureRejectionError(
            bar_num=gap.bar_num,
            interval=gap.interval,
            writing_mode="PILLAR",
            rejections=rejections,
        )
