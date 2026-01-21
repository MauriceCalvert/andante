"""Layer 4: Thematic.

Category A: Pure functions, no I/O, no validation.
Input: Opening schema + rhythmic vocabulary + density
Output: Subject (pitches + durations)

Delegates to CP-SAT solver for enumeration.
"""
from fractions import Fraction
from typing import Any

from builder.solver import (
    solve as cpsat_solve,
    Anchor as SolverAnchor,
    Slot,
    SolverConfig,
    Solution as SolverSolution,
)
from builder.costs import VoiceMode
from builder.types import (
    AffectConfig,
    Anchor as LegacyAnchor,
    GenreConfig,
    KeyConfig,
    MotiveWeights,
    SchemaChain,
    SchemaConfig,
    Solution as LegacySolution,
)

# Slots per bar for 4/4 time with 1/16 primary value
SLOTS_PER_BAR: int = 16
TESSITURA_SPAN: int = 12


def _bar_beat_to_offset(bar_beat: str) -> Fraction:
    """Convert bar.beat string to Fraction offset in whole notes."""
    parts: list[str] = bar_beat.split(".")
    bar: int = int(parts[0])
    beat: float = float(parts[1]) if len(parts) > 1 else 1.0
    # Assuming 4/4 time: each bar is 1 whole note, each beat is 1/4
    slot_in_bar: int = int((beat - 1) * 4)
    slot: int = (bar - 1) * SLOTS_PER_BAR + slot_in_bar
    return Fraction(slot, SLOTS_PER_BAR)


def _convert_anchors(
    legacy_anchors: list[LegacyAnchor],
) -> list[SolverAnchor]:
    """Convert legacy anchors (bar.beat, soprano/bass) to solver anchors (offset, voice, midi)."""
    solver_anchors: list[SolverAnchor] = []
    for anchor in legacy_anchors:
        offset: Fraction = _bar_beat_to_offset(anchor.bar_beat)
        # Voice 0 = soprano, Voice 1 = bass
        solver_anchors.append(SolverAnchor(offset=offset, voice=0, midi=anchor.soprano_midi))
        solver_anchors.append(SolverAnchor(offset=offset, voice=1, midi=anchor.bass_midi))
    return solver_anchors


def _generate_slots(
    total_bars: int,
    voice_count: int,
) -> list[Slot]:
    """Generate slots for all time positions."""
    slots: list[Slot] = []
    total_slots: int = total_bars * SLOTS_PER_BAR
    slot_duration: Fraction = Fraction(1, SLOTS_PER_BAR)
    for slot_idx in range(total_slots):
        offset: Fraction = Fraction(slot_idx, SLOTS_PER_BAR)
        for voice in range(voice_count):
            slots.append(Slot(offset=offset, voice=voice, duration=slot_duration))
    return slots


def _motive_weights_to_dict(weights: MotiveWeights) -> dict[str, float]:
    """Convert MotiveWeights dataclass to dict."""
    return {
        "step": weights.step,
        "skip": weights.skip,
        "leap": weights.leap,
        "large_leap": weights.large_leap,
    }


def _convert_solution(
    solver_solution: SolverSolution,
    total_bars: int,
) -> LegacySolution:
    """Convert solver solution to legacy solution format."""
    total_slots: int = total_bars * SLOTS_PER_BAR
    slot_duration: Fraction = Fraction(1, SLOTS_PER_BAR)

    soprano_pitches: list[int] = []
    bass_pitches: list[int] = []
    soprano_durations: list[Fraction] = []
    bass_durations: list[Fraction] = []

    for slot_idx in range(total_slots):
        offset: Fraction = Fraction(slot_idx, SLOTS_PER_BAR)
        soprano_pitches.append(solver_solution.pitches.get((offset, 0), 60))
        bass_pitches.append(solver_solution.pitches.get((offset, 1), 48))
        soprano_durations.append(slot_duration)
        bass_durations.append(slot_duration)

    return LegacySolution(
        soprano_pitches=tuple(soprano_pitches),
        bass_pitches=tuple(bass_pitches),
        soprano_durations=tuple(soprano_durations),
        bass_durations=tuple(bass_durations),
        cost=solver_solution.cost,
    )


def layer_4_thematic(
    schema_chain: SchemaChain,
    rhythm_vocab: dict[str, Any],
    density: str,
    affect_config: AffectConfig,
    key_config: KeyConfig,
    genre_config: GenreConfig,
    schemas: dict[str, SchemaConfig],
    total_bars: int,
    anchors: list[LegacyAnchor],
) -> LegacySolution:
    """Execute Layer 4.

    Returns:
        Solution with subject pitches and durations.
    """
    # Convert legacy anchors to solver anchors
    solver_anchors: list[SolverAnchor] = _convert_anchors(anchors)

    # Generate all slots
    voice_count: int = genre_config.voices
    slots: list[Slot] = _generate_slots(total_bars, voice_count)

    # Build tessitura medians dict from genre config
    tessitura_medians: dict[int, int] = {}
    if "soprano" in genre_config.tessitura:
        tessitura_medians[0] = genre_config.tessitura["soprano"]
    if "bass" in genre_config.tessitura:
        tessitura_medians[1] = genre_config.tessitura["bass"]
    # Fill in any missing voices with defaults
    for v in range(voice_count):
        if v not in tessitura_medians:
            tessitura_medians[v] = 60  # Middle C default

    # Create solver config
    config = SolverConfig(
        voice_count=voice_count,
        pitch_class_set=key_config.pitch_class_set,
        tessitura_medians=tessitura_medians,
        tessitura_span=TESSITURA_SPAN,
        invertible_at=None,
        voice_mode=VoiceMode.STANDARD,
        motive_weights=_motive_weights_to_dict(affect_config.motive_weights),
        metre_numerator=4,  # Assuming 4/4 time
    )

    # Solve
    solver_solution: SolverSolution = cpsat_solve(solver_anchors, slots, config)

    # Convert back to legacy solution format
    return _convert_solution(solver_solution, total_bars)
