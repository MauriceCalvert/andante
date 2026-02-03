"""Cadential strategy: fill gap with cadential figure.

Used at phrase endings where GapPlan.writing_mode == CADENTIAL.
Selects from cadential.yaml indexed by target degree and approach interval.
"""
import logging
from fractions import Fraction
from random import Random
from typing import Callable
from builder.figuration.loader import (
    get_cadential,
    get_hemiola_templates,
    get_rhythm_templates,
)
from builder.figuration.types import CadentialFigure, RhythmTemplate
from builder.writing_strategy import WritingStrategy
from shared.diatonic_pitch import DiatonicPitch
from shared.key import Key
from shared.plan_types import GapPlan

_log: logging.Logger = logging.getLogger(__name__)

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
        self._rhythm_templates: dict[tuple[int, str, bool], RhythmTemplate] = (
            get_rhythm_templates()
        )
        self._hemiola_templates: dict[tuple[int, str], RhythmTemplate] = (
            get_hemiola_templates()
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
            note_count: int = len(fig.degrees)
            durations: tuple[Fraction, ...] = self._get_rhythm(
                note_count, gap, metre,
            )
            pairs: tuple[tuple[DiatonicPitch, Fraction], ...] | None = (
                _expand_cadential(
                    fig, source_pitch, durations, candidate_filter,
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

    def _get_rhythm(
        self,
        note_count: int,
        gap: GapPlan,
        metre: str,
    ) -> tuple[Fraction, ...]:
        """Look up rhythm template and convert to whole-note durations."""
        template: RhythmTemplate | None = None
        if gap.use_hemiola:
            template = self._hemiola_templates.get((note_count, metre))
        if template is None:
            template = self._rhythm_templates.get(
                (note_count, metre, gap.overdotted),
            )
        if template is None and gap.overdotted:
            template = self._rhythm_templates.get(
                (note_count, metre, False),
            )
        if template is None:
            dur_each: Fraction = Fraction(gap.gap_duration, note_count)
            return tuple(dur_each for _ in range(note_count))
        total_beats: Fraction = Fraction(0)
        for d in template.durations:
            total_beats += d
        assert total_beats > 0, (
            f"Template total beats must be positive, got {total_beats}"
        )
        return tuple(
            d * gap.gap_duration / total_beats
            for d in template.durations
        )


def _expand_cadential(
    figure: CadentialFigure,
    source_pitch: DiatonicPitch,
    durations: tuple[Fraction, ...],
    candidate_filter: Callable[[DiatonicPitch, Fraction], bool],
) -> tuple[tuple[DiatonicPitch, Fraction], ...] | None:
    """Expand cadential figure; return None if any note fails filter."""
    assert len(figure.degrees) == len(durations), (
        f"Degree count {len(figure.degrees)} != duration count {len(durations)}"
    )
    pairs: list[tuple[DiatonicPitch, Fraction]] = []
    elapsed: Fraction = Fraction(0)
    for i, deg in enumerate(figure.degrees):
        dp: DiatonicPitch = source_pitch.transpose(deg)
        if not candidate_filter(dp, elapsed):
            return None
        pairs.append((dp, durations[i]))
        elapsed += durations[i]
    return tuple(pairs)
