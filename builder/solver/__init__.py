"""Voice solver for SATB coordination.

Handles attack points, sounding notes, dissonance avoidance,
and parallel 5th/8ve avoidance.
"""
from builder.solver.subdivision import (
    VerticalSlice,
    SliceSequence,
    collect_attack_points,
    pitch_at_offset,
    build_slice_sequence,
    consecutive_slice_pairs,
)
from builder.solver.constraints import (
    is_dissonant_diatonic,
    check_slice_dissonances,
    is_parallel_fifth_diatonic,
    is_parallel_octave_diatonic,
    check_parallel_motion,
)
from builder.solver.solver import generate_voice
from builder.solver.cpsat_voice import generate_voice_cpsat
from builder.solver.pattern_loader import Pattern, load_pattern, get_default_pattern

__all__ = [
    "VerticalSlice",
    "SliceSequence",
    "collect_attack_points",
    "pitch_at_offset",
    "build_slice_sequence",
    "consecutive_slice_pairs",
    "is_dissonant_diatonic",
    "check_slice_dissonances",
    "is_parallel_fifth_diatonic",
    "is_parallel_octave_diatonic",
    "check_parallel_motion",
    "generate_voice",
    "generate_voice_cpsat",
    "Pattern",
    "load_pattern",
    "get_default_pattern",
]
