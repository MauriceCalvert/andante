"""Figuration strategy: fill gap with baroque diminution figure.

Reuses vocabulary from builder/figuration/loader.py and rhythm
templates from builder/figuration/loader.py.  Makes zero
compositional decisions — all criteria arrive in the GapPlan.
"""
import logging
from fractions import Fraction
from random import Random
from typing import Callable
from builder.figuration.loader import (
    get_diminutions,
    get_hemiola_templates,
    get_rhythm_templates,
)
from builder.figuration.types import Figure, RhythmTemplate
from builder.writing_strategy import WritingStrategy
from shared.diatonic_pitch import DiatonicPitch
from shared.key import Key
from shared.plan_types import GapPlan

_log: logging.Logger = logging.getLogger(__name__)

_TENSION_RANK: dict[str, int] = {"low": 0, "medium": 1, "high": 2}
_DENSITY_RANK: dict[str, int] = {"low": 0, "medium": 1, "high": 2}
_CHARACTER_RANK: dict[str, int] = {
    "plain": 0, "expressive": 1, "energetic": 2, "ornate": 3, "bold": 4,
}
MAX_FIGURE_ATTEMPTS: int = 20
MIN_NOTE_COUNT: int = 2


class FigurationStrategy(WritingStrategy):
    """Fill a gap with a baroque diminution figure."""

    def __init__(self) -> None:
        self._diminutions: dict[str, list[Figure]] = get_diminutions()
        self._rhythm_templates: dict[tuple[int, str, bool], RhythmTemplate] = (
            get_rhythm_templates()
        )
        self._hemiola_templates: dict[tuple[int, str], RhythmTemplate] = (
            get_hemiola_templates()
        )

    def expand_figure(
        self,
        figure: Figure,
        source_pitch: DiatonicPitch,
        target_pitch: DiatonicPitch,
        gap: GapPlan,
        home_key: Key,
        metre: str,
        candidate_filter: Callable[[DiatonicPitch, Fraction], bool],
    ) -> tuple[tuple[DiatonicPitch, Fraction], ...] | None:
        """Expand a single figure; return None if any note fails filter."""
        note_count: int = self._target_note_count(gap)
        durations: tuple[Fraction, ...] = self._get_rhythm(
            note_count, gap, metre,
        )
        return _expand_and_check(
            figure, note_count, source_pitch, durations, candidate_filter,
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
        """Select and expand a diminution figure for this gap."""
        all_figures: list[Figure] = self._diminutions.get(gap.interval, [])
        assert len(all_figures) > 0, (
            f"No diminution figures for interval '{gap.interval}'"
        )
        note_count: int = self._target_note_count(gap)
        while note_count >= MIN_NOTE_COUNT:
            filtered: list[Figure] = self.filter_figures(
                gap, all_figures, note_count, home_key, strict_density=True,
            )
            if not filtered:
                filtered = self.filter_figures(
                    gap, all_figures, note_count, home_key, strict_density=False,
                )
            if filtered:
                durations: tuple[Fraction, ...] = self._get_rhythm(
                    note_count, gap, metre,
                )
                rng.shuffle(filtered)
                ranked: list[Figure] = sorted(filtered, key=lambda f: -f.weight)
                for figure in ranked[:MAX_FIGURE_ATTEMPTS]:
                    pairs: tuple[tuple[DiatonicPitch, Fraction], ...] | None = (
                        _expand_and_check(
                            figure, note_count, source_pitch,
                            durations, candidate_filter,
                        )
                    )
                    if pairs is not None:
                        return pairs
            note_count = note_count // 2
        _log.warning(
            "All figures rejected at bar %d — falling back to pillar",
            gap.bar_num,
        )
        return ((source_pitch, gap.gap_duration),)

    def filter_figures(
        self,
        gap: GapPlan,
        figures: list[Figure],
        note_count: int,
        home_key: Key,
        strict_density: bool = True,
    ) -> list[Figure]:
        """Return figures passing all GapPlan criteria."""
        result: list[Figure] = []
        gap_density: int = _DENSITY_RANK[gap.density]
        gap_tension: int = _TENSION_RANK[gap.harmonic_tension]
        gap_char: int = _CHARACTER_RANK.get(gap.character, 1)
        is_minor: bool = home_key.mode == "minor"
        for fig in figures:
            if not _count_compatible(fig, note_count):
                continue
            if strict_density and _DENSITY_RANK[fig.max_density] < gap_density:
                continue
            if _TENSION_RANK[fig.harmonic_tension] > gap_tension:
                continue
            if abs(_CHARACTER_RANK.get(fig.character, 1) - gap_char) > 1:
                continue
            if gap.near_cadence and not fig.cadential_safe:
                continue
            if not gap.compound_allowed and fig.is_compound:
                continue
            if is_minor and not fig.minor_safe:
                continue
            result.append(fig)
        return result

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

    def _target_note_count(self, gap: GapPlan) -> int:
        """Determine target note count for this gap."""
        if gap.required_note_count is not None:
            return gap.required_note_count
        from builder.figuration.rhythm_calc import compute_rhythmic_distribution
        count: int
        count, _ = compute_rhythmic_distribution(
            gap.gap_duration, gap.density,
        )
        return count


# ── Expand ────────────────────────────────────────────────────────────────────

def _count_compatible(fig: Figure, target: int) -> bool:
    """Check if figure can produce exactly target notes."""
    if fig.note_count == target:
        return True
    if fig.chainable:
        unit: int = fig.effective_chain_unit
        if unit > 0 and target >= unit and target % unit == 0:
            return True
    return False


def _expand_and_check(
    figure: Figure,
    note_count: int,
    source_pitch: DiatonicPitch,
    durations: tuple[Fraction, ...],
    candidate_filter: Callable[[DiatonicPitch, Fraction], bool],
) -> tuple[tuple[DiatonicPitch, Fraction], ...] | None:
    """Expand figure to (pitch, duration) pairs; return None if any fails filter."""
    degrees: tuple[int, ...] = _tile_degrees(figure, note_count)
    assert len(degrees) == len(durations), (
        f"Degree count {len(degrees)} != duration count {len(durations)}"
    )
    pairs: list[tuple[DiatonicPitch, Fraction]] = []
    elapsed: Fraction = Fraction(0)
    for i, deg in enumerate(degrees):
        dp: DiatonicPitch = source_pitch.transpose(deg)
        if not candidate_filter(dp, elapsed):
            return None
        pairs.append((dp, durations[i]))
        elapsed += durations[i]
    return tuple(pairs)


def _tile_degrees(figure: Figure, target_count: int) -> tuple[int, ...]:
    """Tile chainable figure degrees to reach target count."""
    if figure.note_count == target_count:
        return figure.degrees
    assert figure.chainable, (
        f"Figure '{figure.name}' is not chainable but count "
        f"{figure.note_count} != target {target_count}"
    )
    unit: int = figure.effective_chain_unit
    repetitions: int = target_count // unit
    base: tuple[int, ...] = figure.degrees[:unit]
    result: list[int] = []
    offset: int = 0
    for _ in range(repetitions):
        for deg in base:
            result.append(deg + offset)
        offset = result[-1]
    return tuple(result)
