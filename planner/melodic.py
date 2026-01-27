"""Layer 7: Melodic.

Category A: Pure functions, no I/O, no validation.
Input: Phrase-grouped anchors + rhythmic vocabulary + density + rhythm plan
Output: Pitches for active slots only

Uses greedy solver for fast generation.
Respects RhythmPlan for voice independence.
"""
from fractions import Fraction
from typing import Any

from builder.greedy_solver import (
    solve_greedy,
    solve_greedy_legacy,
    GreedyConfig,
    GreedySolution,
)
from builder.types import (
    AffectConfig,
    Anchor,
    GenreConfig,
    KeyConfig,
    MotiveWeights,
    RhythmPlan,
    SchemaChain,
    SchemaConfig,
    Solution,
)
from shared.constants import DEFAULT_TESSITURA_MEDIANS
from shared.pitch import select_octave

SLOTS_PER_BAR: int = 16
TESSITURA_SPAN: int = 18
DEBUG: bool = True


def _debug(msg: str) -> None:
    """Print debug message if DEBUG is enabled."""
    if DEBUG:
        print(f"[L7] {msg}")


def _bar_beat_to_offset(bar_beat: str) -> Fraction:
    """Convert bar.beat string to Fraction offset in whole notes."""
    parts: list[str] = bar_beat.split(".")
    bar: int = int(parts[0])
    beat: float = float(parts[1]) if len(parts) > 1 else 1.0
    slot_in_bar: int = int((beat - 1) * 4)
    slot: int = (bar - 1) * SLOTS_PER_BAR + slot_in_bar
    return Fraction(slot, SLOTS_PER_BAR)


def _convert_anchors_to_dict(
    anchors: list[Anchor],
    soprano_median: int,
    bass_median: int,
) -> dict[tuple[Fraction, int], int]:
    """Convert anchors to dict mapping (offset, voice) -> midi."""
    anchor_dict: dict[tuple[Fraction, int], int] = {}
    sorted_anchors: list[Anchor] = sorted(anchors, key=lambda a: _bar_beat_to_offset(a.bar_beat))
    prev_soprano: int | None = None
    prev_bass: int | None = None
    for anchor in sorted_anchors:
        offset: Fraction = _bar_beat_to_offset(anchor.bar_beat)
        s_midi: int = select_octave(
            anchor.local_key, anchor.soprano_degree, soprano_median, prev_soprano,
        )
        b_midi: int = select_octave(
            anchor.local_key, anchor.bass_degree, bass_median, prev_bass,
        )
        anchor_dict[(offset, 0)] = s_midi
        anchor_dict[(offset, 1)] = b_midi
        prev_soprano = s_midi
        prev_bass = b_midi
    return anchor_dict


def _rhythm_plan_to_active_slots(
    rhythm_plan: RhythmPlan,
) -> dict[int, frozenset[int]]:
    """Convert RhythmPlan to active_slots format for solver."""
    return {
        0: rhythm_plan.soprano_active,
        1: rhythm_plan.bass_active,
    }


def _build_tessitura_medians(voice_count: int) -> dict[int, int]:
    """Build tessitura medians dict from defaults."""
    tessitura_medians: dict[int, int] = dict(DEFAULT_TESSITURA_MEDIANS)
    for v in range(voice_count):
        if v not in tessitura_medians:
            tessitura_medians[v] = 60
    return tessitura_medians


def _convert_solution(
    greedy_solution: GreedySolution,
    rhythm_plan: RhythmPlan,
    total_bars: int,
) -> Solution:
    """Convert greedy solution to Solution format."""
    total_slots: int = total_bars * SLOTS_PER_BAR
    default_duration: Fraction = Fraction(1, SLOTS_PER_BAR)
    soprano_pitches: list[int] = []
    bass_pitches: list[int] = []
    soprano_durations: list[Fraction] = []
    bass_durations: list[Fraction] = []
    last_soprano: int = 60
    last_bass: int = 48
    for slot_idx in range(total_slots):
        offset: Fraction = Fraction(slot_idx, SLOTS_PER_BAR)
        if slot_idx in rhythm_plan.soprano_active:
            pitch = greedy_solution.pitches.get((offset, 0), last_soprano)
            last_soprano = pitch
            soprano_pitches.append(pitch)
            soprano_durations.append(rhythm_plan.soprano_durations.get(slot_idx, default_duration))
        else:
            soprano_pitches.append(last_soprano)
            soprano_durations.append(default_duration)
        if slot_idx in rhythm_plan.bass_active:
            pitch = greedy_solution.pitches.get((offset, 1), last_bass)
            last_bass = pitch
            bass_pitches.append(pitch)
            bass_durations.append(rhythm_plan.bass_durations.get(slot_idx, default_duration))
        else:
            bass_pitches.append(last_bass)
            bass_durations.append(default_duration)
    return Solution(
        soprano_pitches=tuple(soprano_pitches),
        bass_pitches=tuple(bass_pitches),
        soprano_durations=tuple(soprano_durations),
        bass_durations=tuple(bass_durations),
        cost=greedy_solution.cost,
    )


def layer_7_melodic(
    schema_chain: SchemaChain,
    rhythm_vocab: dict[str, Any],
    density: str,
    affect_config: AffectConfig,
    key_config: KeyConfig,
    genre_config: GenreConfig,
    schemas: dict[str, SchemaConfig],
    total_bars: int,
    anchors: list[Anchor],
    rhythm_plan: RhythmPlan | None = None,
) -> Solution:
    """Execute Layer 7: greedy pitch filling for active slots only."""
    voice_count: int = genre_config.voices
    tessitura_medians: dict[int, int] = _build_tessitura_medians(voice_count)
    _debug(f"tessitura_medians={tessitura_medians}, span={TESSITURA_SPAN}")
    config = GreedyConfig(
        voice_count=voice_count,
        pitch_class_set=key_config.pitch_class_set,
        tessitura_medians=tessitura_medians,
        tessitura_span=TESSITURA_SPAN,
    )
    soprano_median: int = tessitura_medians.get(0, 70)
    bass_median: int = tessitura_medians.get(1, 48)
    anchor_dict: dict[tuple[Fraction, int], int] = _convert_anchors_to_dict(
        anchors, soprano_median, bass_median,
    )
    if rhythm_plan is not None:
        active_slots: dict[int, frozenset[int]] = _rhythm_plan_to_active_slots(rhythm_plan)
        _debug(f"Using rhythm plan: {len(rhythm_plan.soprano_active)} soprano slots, {len(rhythm_plan.bass_active)} bass slots")
        _debug(f"Using greedy solver for {total_bars} bars, {len(anchors)} anchors")
        greedy_solution: GreedySolution = solve_greedy(anchor_dict, active_slots, config)
        _debug(f"Greedy solution cost: {greedy_solution.cost:.2f}")
        return _convert_solution(greedy_solution, rhythm_plan, total_bars)
    else:
        total_slots: int = total_bars * SLOTS_PER_BAR
        offsets: list[Fraction] = [Fraction(slot_idx, SLOTS_PER_BAR) for slot_idx in range(total_slots)]
        _debug(f"No rhythm plan: filling all {len(offsets)} slots (legacy mode)")
        _debug(f"Using greedy solver for {total_bars} bars, {len(anchors)} anchors")
        greedy_solution = solve_greedy_legacy(anchor_dict, offsets, config)
        _debug(f"Greedy solution cost: {greedy_solution.cost:.2f}")
        return _convert_solution_legacy(greedy_solution, total_bars)


def _convert_solution_legacy(
    greedy_solution: GreedySolution,
    total_bars: int,
) -> Solution:
    """Legacy conversion for backward compatibility (fills all slots)."""
    total_slots: int = total_bars * SLOTS_PER_BAR
    slot_duration: Fraction = Fraction(1, SLOTS_PER_BAR)
    soprano_pitches: list[int] = []
    bass_pitches: list[int] = []
    soprano_durations: list[Fraction] = []
    bass_durations: list[Fraction] = []
    for slot_idx in range(total_slots):
        offset: Fraction = Fraction(slot_idx, SLOTS_PER_BAR)
        soprano_pitches.append(greedy_solution.pitches.get((offset, 0), 60))
        bass_pitches.append(greedy_solution.pitches.get((offset, 1), 48))
        soprano_durations.append(slot_duration)
        bass_durations.append(slot_duration)
    return Solution(
        soprano_pitches=tuple(soprano_pitches),
        bass_pitches=tuple(bass_pitches),
        soprano_durations=tuple(soprano_durations),
        bass_durations=tuple(bass_durations),
        cost=greedy_solution.cost,
    )
