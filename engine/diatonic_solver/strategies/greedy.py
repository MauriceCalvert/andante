"""Greedy slice-by-slice solver strategy for diatonic inner voice resolution.

Solves each slice independently, picking the best inner voice configuration
based on local scoring. Fast but may not find globally optimal solutions.

All operations are in degree space (1-7). No MIDI conversion.
"""
from fractions import Fraction
from itertools import product

from engine.diatonic_solver.core import DiatonicPitch, DiatonicSlice
from engine.diatonic_solver.constraints import (
    has_parallel_violation,
    has_unison,
    score_slice_transition,
    get_chord_tones,
    SliceScore,
)


def solve_greedy(
    slices: list[DiatonicSlice],
    voice_count: int,
    is_strong_beat: dict[int, bool] | None = None,
    thematic_targets: dict[tuple[int, int], int] | None = None,
) -> list[DiatonicSlice]:
    """Solve all inner voice degrees using greedy slice-by-slice search.

    At each slice, enumerates all valid inner voice degree combinations,
    scores each, and picks the best. No backtracking.

    Args:
        slices: List of DiatonicSlice with soprano/bass set, inner voices None
        voice_count: Total number of voices (e.g., 4 for SATB)
        is_strong_beat: Optional dict mapping slice_idx to whether it's a strong beat
        thematic_targets: Optional dict mapping (slice_idx, voice_idx) to target degree

    Returns:
        List of DiatonicSlice with all voices filled.
    """
    if not slices:
        return slices

    inner_count = voice_count - 2
    if inner_count <= 0:
        return slices

    result_slices: list[DiatonicSlice] = []
    prev_degrees: tuple[int | None, ...] | None = None

    for si, slice_data in enumerate(slices):
        soprano_deg = slice_data.get_degree(0)
        bass_deg = slice_data.get_degree(voice_count - 1)

        if soprano_deg is None or bass_deg is None:
            # Rest in outer voice - propagate as-is
            result_slices.append(slice_data)
            prev_degrees = None
            continue

        chord_tones = get_chord_tones(bass_deg)
        strong_beat = is_strong_beat.get(si, False) if is_strong_beat else False

        # Get thematic targets for this slice
        slice_thematic: dict[int, int] | None = None
        if thematic_targets:
            slice_thematic = {
                vi: thematic_targets[(si, vi)]
                for vi in range(1, voice_count - 1)
                if (si, vi) in thematic_targets
            }

        # Generate candidates: prefer chord tones, but allow all degrees
        # Order: chord tones first (sorted), then non-chord tones
        sorted_chord_tones = sorted(chord_tones)
        non_chord_tones = [d for d in range(1, 8) if d not in chord_tones]
        candidate_order = sorted_chord_tones + non_chord_tones

        # Enumerate all inner voice combinations
        all_inner_combos = list(product(candidate_order, repeat=inner_count))

        best_combo: tuple[int, ...] = (chord_tones.pop(),) * inner_count if chord_tones else (1,) * inner_count
        best_score = float('inf')

        for combo in all_inner_combos:
            # Build full degree tuple
            degrees: tuple[int | None, ...] = (soprano_deg,) + combo + (bass_deg,)

            # Check hard constraints
            if has_unison(degrees):
                continue  # Skip unisons

            if prev_degrees is not None and has_parallel_violation(prev_degrees, degrees):
                continue  # Skip parallels

            # Score this configuration
            if prev_degrees is None:
                # First slice - only score sonority
                score = _score_first_slice(degrees, bass_deg, strong_beat, slice_thematic)
            else:
                score_obj = score_slice_transition(
                    prev_degrees, degrees, bass_deg, strong_beat, slice_thematic
                )
                score = score_obj.total

            if score < best_score:
                best_score = score
                best_combo = combo

        # Build result slice with best combo
        pitches: list[DiatonicPitch | None] = [DiatonicPitch(soprano_deg)]
        for deg in best_combo:
            pitches.append(DiatonicPitch(deg))
        pitches.append(DiatonicPitch(bass_deg))

        result_slices.append(DiatonicSlice(
            offset=slice_data.offset,
            pitches=tuple(pitches),
        ))

        prev_degrees = tuple(p.degree if p else None for p in pitches)

    return result_slices


def _score_first_slice(
    degrees: tuple[int | None, ...],
    bass_deg: int,
    is_strong_beat: bool,
    thematic_targets: dict[int, int] | None,
) -> float:
    """Score the first slice (no voice leading context)."""
    from engine.diatonic_solver.constraints import (
        NON_CHORD_TONE_COST,
        THEMATIC_MATCH_REWARD,
        get_chord_tones,
    )

    chord_tones = get_chord_tones(bass_deg)
    multiplier = 2 if is_strong_beat else 1
    score = 0.0

    # Chord tone preference for inner voices
    for vi in range(1, len(degrees) - 1):
        deg = degrees[vi]
        if deg is not None and deg not in chord_tones:
            score += NON_CHORD_TONE_COST * multiplier

    # Thematic matching reward
    if thematic_targets:
        for vi, target in thematic_targets.items():
            if vi < len(degrees):
                if degrees[vi] == target:
                    score -= THEMATIC_MATCH_REWARD

    return score
