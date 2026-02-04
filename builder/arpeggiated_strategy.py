"""Arpeggiated strategy: bass accompaniment patterns.

Realises bass patterns from YAML data into (DiatonicPitch, duration) pairs.
Auto-detects BassPattern (degree offsets) vs RhythmPattern (schema pitches).
"""
import logging
from fractions import Fraction
from random import Random
from typing import Callable

from builder.figuration.bass import (
    BassPattern,
    RhythmPattern,
    get_bass_pattern,
    get_rhythm_pattern,
)
from builder.writing_strategy import WritingStrategy
from shared.diatonic_pitch import DiatonicPitch
from shared.key import Key
from shared.plan_types import GapPlan

_log: logging.Logger = logging.getLogger(__name__)


def _beats_per_bar(metre: str) -> int:
    """Extract numerator from metre string like '3/4'."""
    num_str, _ = metre.split("/")
    return int(num_str)


class ArpeggiatedStrategy(WritingStrategy):
    """Bass pattern strategy using predefined accompaniment patterns.

    Loads pattern by name, auto-detecting whether it is a BassPattern
    (degree offsets from root) or RhythmPattern (schema-driven pitches).
    """

    def __init__(self, pattern_name: str) -> None:
        self._pattern_name: str = pattern_name
        self._bass_pattern: BassPattern | None = get_bass_pattern(name=pattern_name)
        self._rhythm_pattern: RhythmPattern | None = (
            get_rhythm_pattern(name=pattern_name)
            if self._bass_pattern is None
            else None
        )
        assert self._bass_pattern is not None or self._rhythm_pattern is not None, (
            f"Unknown bass pattern '{pattern_name}': "
            f"not found in bass_patterns or rhythm_patterns"
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
        """Return (pitch, duration) pairs from the bass pattern."""
        if self._rhythm_pattern is not None:
            return self._fill_rhythm(
                gap=gap, source_pitch=source_pitch, target_pitch=target_pitch, metre=metre, candidate_filter=candidate_filter,
            )
        assert self._bass_pattern is not None
        return self._fill_bass_pattern(
            gap=gap, source_pitch=source_pitch, metre=metre, candidate_filter=candidate_filter,
        )

    def _fill_bass_pattern(
        self,
        gap: GapPlan,
        source_pitch: DiatonicPitch,
        metre: str,
        candidate_filter: Callable[[DiatonicPitch, Fraction, bool], str | None],
    ) -> tuple[tuple[DiatonicPitch, Fraction], ...]:
        """Realise BassPattern: degree offsets from source pitch."""
        assert self._bass_pattern is not None
        pattern: BassPattern = self._bass_pattern
        effective_metre: str = metre if pattern.metre == "any" else pattern.metre
        bpb: int = _beats_per_bar(metre=effective_metre)
        beat_unit: Fraction = gap.gap_duration / bpb
        result: list[tuple[DiatonicPitch, Fraction]] = []
        for beat in pattern.beats:
            if beat.bar != 1:
                continue
            local_offset: Fraction = (beat.beat - 1) * beat_unit
            if local_offset >= gap.gap_duration:
                continue
            dur: Fraction = _resolve_duration(
                raw=beat.duration, gap_duration=gap.gap_duration, beat_unit=beat_unit,
            )
            if local_offset + dur > gap.gap_duration:
                dur = gap.gap_duration - local_offset
            if dur <= 0:
                continue
            pitch: DiatonicPitch = source_pitch.transpose(steps=beat.degree_offset)
            is_first: bool = len(result) == 0
            reason: str | None = candidate_filter(pitch, local_offset, is_first)
            if reason is not None:
                pitch = source_pitch
                reason = candidate_filter(pitch, local_offset, is_first)
                if reason is not None:
                    _log.debug(
                        "Arpeggiated bar %d: skipping beat at offset %s (%s)",
                        gap.bar_num, local_offset, reason,
                    )
                    continue
            result.append((pitch, dur))
        if not result:
            return ((source_pitch, gap.gap_duration),)
        return tuple(result)

    def _fill_rhythm(
        self,
        gap: GapPlan,
        source_pitch: DiatonicPitch,
        target_pitch: DiatonicPitch,
        metre: str,
        candidate_filter: Callable[[DiatonicPitch, Fraction, bool], str | None],
    ) -> tuple[tuple[DiatonicPitch, Fraction], ...]:
        """Realise RhythmPattern: pitches from schema, timing from pattern."""
        assert self._rhythm_pattern is not None
        pattern: RhythmPattern = self._rhythm_pattern
        effective_metre: str = metre if pattern.metre == "any" else pattern.metre
        bpb: int = _beats_per_bar(metre=effective_metre)
        beat_unit: Fraction = gap.gap_duration / bpb
        result: list[tuple[DiatonicPitch, Fraction]] = []
        for beat in pattern.beats:
            local_offset: Fraction = (beat.beat - 1) * beat_unit
            if local_offset >= gap.gap_duration:
                continue
            dur: Fraction = _resolve_duration(
                raw=beat.duration, gap_duration=gap.gap_duration, beat_unit=beat_unit,
            )
            if local_offset + dur > gap.gap_duration:
                dur = gap.gap_duration - local_offset
            if dur <= 0:
                continue
            pitch: DiatonicPitch = target_pitch if beat.use_next else source_pitch
            is_first: bool = len(result) == 0
            reason: str | None = candidate_filter(pitch, local_offset, is_first)
            if reason is not None:
                pitch = source_pitch
                reason = candidate_filter(pitch, local_offset, is_first)
                if reason is not None:
                    _log.debug(
                        "Rhythm bar %d: skipping beat at offset %s (%s)",
                        gap.bar_num, local_offset, reason,
                    )
                    continue
            result.append((pitch, dur))
        if not result:
            return ((source_pitch, gap.gap_duration),)
        return tuple(result)


def _resolve_duration(
    raw: Fraction,
    gap_duration: Fraction,
    beat_unit: Fraction,
) -> Fraction:
    """Convert pattern duration token to actual Fraction.

    Fraction(-1) = full bar, Fraction(-2) = half bar,
    positive = multiple of beat_unit.
    """
    if raw == Fraction(-1):
        return gap_duration
    if raw == Fraction(-2):
        return gap_duration / 2
    return raw * beat_unit
