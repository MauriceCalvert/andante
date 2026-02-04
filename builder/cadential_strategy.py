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
from builder.types import FigureRejection, FigureRejectionError
from builder.voice_checks import check_melodic_interval
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
        candidate_filter: Callable[[DiatonicPitch, Fraction, bool], str | None],
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
            figures = sorted(figures, key=lambda f: not f.hemiola)
        rejections: list[FigureRejection] = []
        for fig in figures:
            note_count: int = len(fig.degrees)
            durations: tuple[Fraction, ...] = self._get_rhythm(
                note_count=note_count, gap=gap, metre=metre,
            )
            pairs, rejection = _expand_cadential(
                figure=fig, source_pitch=source_pitch, durations=durations, candidate_filter=candidate_filter, home_key=home_key,
            )
            if pairs is not None:
                return pairs
            if rejection is not None:
                rejections.append(rejection)
        raise FigureRejectionError(
            bar_num=gap.bar_num,
            interval=gap.interval,
            writing_mode="CADENTIAL",
            rejections=rejections,
        )

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
    candidate_filter: Callable[[DiatonicPitch, Fraction, bool], str | None],
    home_key: Key,
) -> tuple[
    tuple[tuple[DiatonicPitch, Fraction], ...] | None,
    FigureRejection | None,
]:
    """Expand cadential figure; return (pairs, None) or (None, rejection)."""
    assert len(figure.degrees) == len(durations), (
        f"Degree count {len(figure.degrees)} != duration count {len(durations)}"
    )
    pairs: list[tuple[DiatonicPitch, Fraction]] = []
    elapsed: Fraction = Fraction(0)
    prev_midi: int | None = None
    for i, deg in enumerate(figure.degrees):
        dp: DiatonicPitch = source_pitch.transpose(steps=deg)
        midi: int = home_key.diatonic_to_midi(dp=dp)
        is_first: bool = i == 0
        reason: str | None = candidate_filter(dp, elapsed, is_first)
        if reason is not None:
            return None, FigureRejection(
                figure_name=figure.name,
                note_index=i,
                pitch=str(dp),
                offset=str(elapsed),
                reason=reason,
            )
        if prev_midi is not None and not check_melodic_interval(prev_midi=prev_midi, curr_midi=midi):
            interval: int = midi - prev_midi
            return None, FigureRejection(
                figure_name=figure.name,
                note_index=i,
                pitch=str(dp),
                offset=str(elapsed),
                reason=f"internal_melodic({interval})",
            )
        pairs.append((dp, durations[i]))
        prev_midi = midi
        elapsed += durations[i]
    return tuple(pairs), None
