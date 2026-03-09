"""Phrase-level types for phrase planner and writer.

Pure data containers for phrase planning and generation.
"""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING
from shared.key import Key
from shared.music_math import parse_metre
from shared.voice_types import Range

if TYPE_CHECKING:
    from builder.types import Note
    from planner.register_plan import RegisterTarget


@dataclass(frozen=True)
class BeatPosition:
    """Position of a schema degree within a phrase."""
    bar: int
    beat: int


@dataclass(frozen=True)
class BarVoiceDensity:
    """Per-voice, per-bar density override for rhythm generation.

    Used in thematic phrases to assign reduced companion density when one
    voice has material (SUBJECT/ANSWER/CS) and the other is FREE.
    """
    bar: int      # 1-based bar number (relative to phrase)
    voice: int    # 0=soprano, 1=bass
    density: str  # "high", "medium", or "low"


@dataclass(frozen=True)
class HeadMotif:
    """Lightweight descriptor of the opening soprano figuration.

    Captured after the first non-cadential phrase to enable motivic recall.
    """
    interval_sequence: tuple[int, ...]   # signed semitone deltas between consecutive notes
    duration_sequence: tuple[Fraction, ...]  # note durations
    figure_name: str  # diminution table figure that produced it


@dataclass(frozen=True)
class PhrasePlan:
    """Complete specification for writing one phrase (one schema)."""
    schema_name: str
    degrees_upper: tuple[int, ...]
    degrees_lower: tuple[int, ...]
    degree_positions: tuple[BeatPosition, ...]
    local_key: Key
    bar_span: int
    start_bar: int
    start_offset: Fraction
    phrase_duration: Fraction
    metre: str
    rhythm_profile: str
    is_cadential: bool
    cadence_type: str | None
    prev_exit_upper: int | None
    prev_exit_lower: int | None
    section_name: str
    upper_range: Range
    lower_range: Range
    upper_median: int
    lower_median: int
    bass_texture: str = "pillar"
    bass_pattern: str | None = None
    degree_keys: tuple[Key, ...] = ()
    character: str = "plain"
    anacrusis: Fraction = Fraction(0)
    registral_bias: int = 0
    recall_motif: bool = False
    lead_voice: int | None = None
    thematic_roles: tuple | None = None  # BeatRole slice for this phrase (TP-A)
    voice_densities: tuple[BarVoiceDensity, ...] | None = None  # Per-voice, per-bar density overrides (B1)
    cadential_approach: bool = False
    register_target: "RegisterTarget | None" = None
    episode_type: str | None = None
    # Production episode texture for EPISODE phrases. One of:
    # "sequential_episode", "parallel_sixths", "circle_of_fifths".
    # None = paired-kernel path (current default).
    # Populated by entry_layout.py using bar-count gate and adjacency
    # avoidance. Trajectory-delta criterion deferred — register_target
    # is not available at entry_layout time.
    knot_midi_upper: tuple[int, ...] = ()
    knot_midi_lower: tuple[int, ...] = ()


@dataclass(frozen=True)
class PhraseResult:
    """Output of phrase writer for one phrase."""
    upper_notes: tuple[Note, ...]
    lower_notes: tuple[Note, ...]
    exit_upper: int
    exit_lower: int
    schema_name: str
    faults: tuple[str, ...] = ()
    soprano_figures: tuple[str, ...] = ()
    bass_pattern_name: str | None = None


def phrase_bar_start(plan: PhrasePlan, bar_num: int, bar_length: Fraction) -> Fraction:
    """Absolute offset where bar_num begins, accounting for anacrusis."""
    if bar_num == 1:
        return plan.start_offset
    if plan.anacrusis > 0:
        return plan.start_offset + plan.anacrusis + (bar_num - 2) * bar_length
    return plan.start_offset + (bar_num - 1) * bar_length


def phrase_bar_duration(plan: PhrasePlan, bar_num: int, bar_length: Fraction) -> Fraction:
    """Duration of a bar, accounting for partial anacrusis bar."""
    if bar_num == 1 and plan.anacrusis > 0:
        return plan.anacrusis
    return bar_length


def phrase_degree_offset(
    plan: PhrasePlan,
    pos: BeatPosition,
    bar_length: Fraction,
    beat_unit: Fraction,
) -> Fraction:
    """Absolute offset for a BeatPosition, accounting for anacrusis."""
    return phrase_bar_start(plan=plan, bar_num=pos.bar, bar_length=bar_length) + (pos.beat - 1) * beat_unit


def phrase_offset_to_bar(
    plan: PhrasePlan,
    offset: Fraction,
    bar_length: Fraction,
) -> int:
    """Reverse mapping: absolute offset to bar number, accounting for anacrusis."""
    rel: Fraction = offset - plan.start_offset
    if plan.anacrusis > 0:
        if rel < plan.anacrusis:
            return 1
        return int((rel - plan.anacrusis) // bar_length) + 2
    return int(rel // bar_length) + 1


def make_free_companion_plan(
    plan: PhrasePlan,
    start_bar_relative: int,
    bar_count: int,
    start_offset: Fraction,
    prev_exit_upper: int | None,
    prev_exit_lower: int | None,
    genre: str | None = None,
) -> PhrasePlan:
    """Build a PhrasePlan for FREE companion bars alongside material (B1).

    Unlike make_tail_plan, this allows start_bar_relative=1 (companion from phrase start).

    Args:
        plan: Parent PhrasePlan
        start_bar_relative: Starting bar number relative to phrase (1-based)
        bar_count: Number of bars in the FREE run
        start_offset: Absolute offset where FREE run starts
        prev_exit_upper: Previous soprano exit pitch
        prev_exit_lower: Previous bass exit pitch
        genre: Optional genre name override (workaround for rhythm_profile bug)

    Returns:
        PhrasePlan covering the FREE bar run with simplified degree structure.
    """
    assert bar_count >= 1, f"bar_count must be >= 1, got {bar_count}"
    bar_length: Fraction = parse_metre(metre=plan.metre)[0]
    run_duration: Fraction = bar_length * bar_count

    # Workaround: rhythm_profile sometimes contains rhythmic_unit (e.g., "1/16")
    # instead of genre name. If genre is provided, use it; otherwise try to fix.
    rhythm_profile_value: str = plan.rhythm_profile
    if genre is not None:
        rhythm_profile_value = genre
    elif "/" in rhythm_profile_value:
        # Looks like a rhythmic unit, not a genre - use fallback
        # This is a workaround for a pre-existing bug in PhrasePlan creation
        rhythm_profile_value = "invention"  # Safe default for imitative genres

    # Provide minimal structural degrees: single tonic at start
    # (Viterbi will add final knot at phrase_end automatically)
    from builder.phrase_types import BeatPosition
    run_positions = (
        BeatPosition(bar=1, beat=1),
    )
    run_degrees_upper = (1,)
    run_degrees_lower = (1,)
    run_degree_keys = (plan.local_key,)

    return PhrasePlan(
        schema_name=plan.schema_name,
        degrees_upper=run_degrees_upper,
        degrees_lower=run_degrees_lower,
        degree_positions=run_positions,
        local_key=plan.local_key,
        bar_span=bar_count,
        start_bar=plan.start_bar + start_bar_relative - 1,
        start_offset=start_offset,
        phrase_duration=run_duration,
        metre=plan.metre,
        rhythm_profile=rhythm_profile_value,
        is_cadential=False,
        cadence_type=None,
        prev_exit_upper=prev_exit_upper,
        prev_exit_lower=prev_exit_lower,
        section_name=plan.section_name,
        upper_range=plan.upper_range,
        lower_range=plan.lower_range,
        upper_median=plan.upper_median,
        lower_median=plan.lower_median,
        bass_texture=plan.bass_texture,
        bass_pattern=plan.bass_pattern,
        degree_keys=run_degree_keys,
        character=plan.character,
        anacrusis=Fraction(0),
        registral_bias=plan.registral_bias,
        recall_motif=False,
        lead_voice=None,
    )


def make_tail_plan(
    plan: PhrasePlan,
    tail_start_bar: int,
    tail_start_offset: Fraction,
    prev_exit_upper: int | None,
    prev_exit_lower: int | None,
) -> PhrasePlan:
    """Build a PhrasePlan covering bars tail_start_bar..bar_span after a subject entry.

    The tail is free counterpoint (not imitative), generated via normal
    soprano/bass writers. Degree arrays are filtered to only positions in
    the tail range, with bar numbers remapped so tail_start_bar becomes 1.
    """
    assert tail_start_bar > 1, (
        f"tail_start_bar must be > 1 (subject must occupy at least 1 bar), got {tail_start_bar}"
    )
    tail_bar_span: int = plan.bar_span - tail_start_bar + 1
    assert tail_bar_span > 0, (
        f"No tail bars: bar_span={plan.bar_span}, tail_start_bar={tail_start_bar}"
    )
    bar_length: Fraction = parse_metre(metre=plan.metre)[0]
    tail_duration: Fraction = bar_length * tail_bar_span

    # Filter degree_positions to those in the tail range, remap bar numbers
    tail_indices: list[int] = [
        i for i, pos in enumerate(plan.degree_positions)
        if pos.bar >= tail_start_bar
    ]
    bar_shift: int = tail_start_bar - 1
    # If no schema degrees fall in the tail, inject the last parent degree
    # at the tail downbeat so generators have a structural target.
    if len(tail_indices) == 0 and len(plan.degrees_upper) > 0:
        last_idx: int = len(plan.degrees_upper) - 1
        tail_positions = (BeatPosition(bar=1, beat=1),)
        tail_degrees_upper = (plan.degrees_upper[last_idx],)
        tail_degrees_lower = (plan.degrees_lower[last_idx],) if last_idx < len(plan.degrees_lower) else ()
        tail_degree_keys: tuple[Key, ...] = (
            (plan.degree_keys[last_idx],)
            if last_idx < len(plan.degree_keys)
            else (plan.local_key,)
        )
    else:
        tail_positions = tuple(
            BeatPosition(bar=plan.degree_positions[i].bar - bar_shift, beat=plan.degree_positions[i].beat)
            for i in tail_indices
        )
        tail_degrees_upper = tuple(
            plan.degrees_upper[i] for i in tail_indices
            if i < len(plan.degrees_upper)
        )
        tail_degrees_lower = tuple(
            plan.degrees_lower[i] for i in tail_indices
            if i < len(plan.degrees_lower)
        )
        tail_degree_keys = tuple(
            plan.degree_keys[i] if i < len(plan.degree_keys) else plan.local_key
            for i in tail_indices
        )

    return PhrasePlan(
        schema_name=plan.schema_name,
        degrees_upper=tail_degrees_upper,
        degrees_lower=tail_degrees_lower,
        degree_positions=tail_positions,
        local_key=plan.local_key,
        bar_span=tail_bar_span,
        start_bar=plan.start_bar + bar_shift,
        start_offset=tail_start_offset,
        phrase_duration=tail_duration,
        metre=plan.metre,
        rhythm_profile=plan.rhythm_profile,
        is_cadential=False,
        cadence_type=None,
        prev_exit_upper=prev_exit_upper,
        prev_exit_lower=prev_exit_lower,
        section_name=plan.section_name,
        upper_range=plan.upper_range,
        lower_range=plan.lower_range,
        upper_median=plan.upper_median,
        lower_median=plan.lower_median,
        bass_texture=plan.bass_texture,
        bass_pattern=plan.bass_pattern,
        degree_keys=tail_degree_keys,
        character="plain",
        anacrusis=Fraction(0),
        registral_bias=plan.registral_bias,
        recall_motif=False,
        lead_voice=None,
    )
