"""Cadential strategy: fill gap with cadential figure.

Used at phrase endings where GapPlan.writing_mode == CADENTIAL.
Selects from cadential.yaml indexed by target degree and approach interval.
"""
import logging
from fractions import Fraction
from random import Random
from typing import Callable

from builder.figuration.loader import get_cadential
from builder.figuration.types import CadentialFigure
from builder.writing_strategy import WritingStrategy
from shared.diatonic_pitch import DiatonicPitch
from shared.key import Key
from shared.plan_types import GapPlan

_log: logging.Logger = logging.getLogger(__name__)

# Map interval names to cadential target/approach keys
_CADENTIAL_TARGET_DEGREE: dict[str, str] = {
    "step_down": "target_1",
    "step_up": "target_5",
    "third_down": "target_1",
    "third_up": "target_5",
    "unison": "target_1",
}


class CadentialStrategy(WritingStrategy):
    """Fill a gap with a cadential figure for phrase endings."""

    def __init__(self) -> None:
        self._cadential: dict[str, dict[str, list[CadentialFigure]]] = (
            get_cadential()
        )

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
        """Select and expand a cadential figure."""
        target_key: str = _CADENTIAL_TARGET_DEGREE.get(
            gap.interval, "target_1",
        )
        approach_figs: dict[str, list[CadentialFigure]] = (
            self._cadential.get(target_key, {})
        )
        figures: list[CadentialFigure] = approach_figs.get(
            gap.interval, [],
        )
        if gap.use_hemiola:
            hemiola_figs: list[CadentialFigure] = [
                f for f in figures if f.hemiola
            ]
            if hemiola_figs:
                figures = hemiola_figs
        for fig in figures:
            pairs: tuple[tuple[DiatonicPitch, Fraction], ...] | None = (
                _expand_cadential(
                    fig, source_pitch, gap.gap_duration,
                    candidate_filter,
                )
            )
            if pairs is not None:
                return pairs
        _log.warning(
            "No cadential figure fits at bar %d — using simple resolution",
            gap.bar_num,
        )
        assert candidate_filter(source_pitch, Fraction(0)), (
            f"Cadential fallback fails at bar {gap.bar_num}"
        )
        return ((source_pitch, gap.gap_duration),)


def _expand_cadential(
    figure: CadentialFigure,
    source_pitch: DiatonicPitch,
    gap_duration: Fraction,
    candidate_filter: Callable[[DiatonicPitch, Fraction], bool],
) -> tuple[tuple[DiatonicPitch, Fraction], ...] | None:
    """Expand cadential figure; return None if any note fails filter."""
    count: int = len(figure.degrees)
    dur_each: Fraction = Fraction(gap_duration, count)
    assert dur_each > 0, (
        f"Cadential duration must be positive: {gap_duration}/{count}"
    )
    pairs: list[tuple[DiatonicPitch, Fraction]] = []
    elapsed: Fraction = Fraction(0)
    for deg in figure.degrees:
        dp: DiatonicPitch = source_pitch.transpose(deg)
        if not candidate_filter(dp, elapsed):
            return None
        pairs.append((dp, dur_each))
        elapsed += dur_each
    return tuple(pairs)
