"""CP-SAT Voice Generator with pattern-driven rhythm.

Generates voices using patterns from YAML that define:
- Rhythm (durations per bar)
- Interval types (root, step, fifth relative to chord)

CP-SAT optimizes pitches across the entire phrase for:
- Consonance with existing voices at all attack points
- No parallel fifths/octaves
- Good voice leading (minimize leaps, prefer contrary motion)
"""
from fractions import Fraction
from typing import NamedTuple

from ortools.sat.python import cp_model

from builder.solver.pattern_loader import Pattern
from builder.types import Notes
from shared.constants import DIATONIC_DEFAULTS, TONAL_ROOTS
from shared.errors import VoiceGenerationError


# Consonance: 2nds (interval 1) and 7ths (interval 6) are dissonant
DISSONANT_INTERVALS: frozenset[int] = frozenset({1, 6})

# Voice leading costs
STEP_REWARD: int = -10      # Step motion (1 degree) - reward
SMALL_LEAP_COST: int = 5    # 2-3 degrees
LARGE_LEAP_COST: int = 20   # 4+ degrees
HUGE_LEAP_COST: int = 50    # 5+ degrees

# Contrary motion reward
CONTRARY_MOTION_REWARD: int = -5


class AttackPoint(NamedTuple):
    """A point in time where a note attacks."""
    offset: Fraction
    bar_idx: int
    is_strong_beat: bool


def generate_voice_cpsat(
    existing_voices: list[Notes],
    harmony: tuple[str, ...],
    voice_role: str,
    bar_duration: Fraction,
    pattern: Pattern,
    timeout_seconds: float = 10.0,
) -> Notes:
    """Generate a voice using CP-SAT with pattern-driven rhythm.

    The pattern defines the rhythmic structure (durations per bar).
    CP-SAT solves for optimal pitches across the entire phrase.

    Args:
        existing_voices: Already decided voices (e.g., [soprano] for bass).
        harmony: Chord symbols per bar (e.g., ("I", "V", "I")).
        voice_role: Voice being generated ("bass", "alto", "tenor").
        bar_duration: Duration of one bar.
        pattern: Rhythmic pattern defining durations and interval types.
        timeout_seconds: Solver time limit.

    Returns:
        Notes with generated pitches and durations.

    Raises:
        VoiceGenerationError: If no valid solution exists.
    """
    assert voice_role in DIATONIC_DEFAULTS, f"Unknown voice role: {voice_role}"
    assert len(existing_voices) > 0, "Need at least one existing voice"
    assert len(harmony) > 0, "Need at least one chord in harmony"

    soprano: Notes = existing_voices[0]
    bar_count: int = len(harmony)
    base_diatonic: int = DIATONIC_DEFAULTS[voice_role]

    # Build attack points from pattern (repeated per bar)
    attacks: list[AttackPoint] = _build_pattern_attacks(pattern, bar_duration, bar_count)

    if not attacks:
        raise VoiceGenerationError(
            f"Cannot generate {voice_role}: no attack points from pattern {pattern.name}"
        )

    # Build candidate pitches for each attack point based on interval type
    candidates: list[tuple[int, ...]] = _build_interval_candidates(
        attacks, pattern, harmony, base_diatonic
    )

    # Collect all attack times from all voices for consonance checking
    all_attack_times: list[Fraction] = _collect_all_attack_times(
        existing_voices, attacks
    )

    # Build CP-SAT model
    model = cp_model.CpModel()

    # Variables: one pitch per pattern position
    pitch_vars: list[cp_model.IntVar] = []
    for i, cands in enumerate(candidates):
        assert len(cands) > 0, f"No candidates at attack {i}"
        var = model.NewIntVar(0, len(cands) - 1, f"p_{i}")
        pitch_vars.append(var)

    # === HARD CONSTRAINTS ===

    # Consonance with all existing voices at all attack times
    for voice in existing_voices:
        _add_consonance_constraints(
            model, pitch_vars, candidates, attacks,
            voice, all_attack_times, bar_duration
        )

    # No parallel fifths/octaves
    for voice in existing_voices:
        _add_parallel_constraints(model, pitch_vars, candidates, attacks, voice)

    # === SOFT CONSTRAINTS (optimization) ===
    costs: list = []

    # Voice leading costs
    _add_voice_leading_costs(model, pitch_vars, candidates, costs)

    # Contrary motion reward
    _add_contrary_motion_costs(model, pitch_vars, candidates, attacks, soprano, costs)

    # Minimize total cost
    if costs:
        model.Minimize(cp_model.LinearExpr.Sum(costs))

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout_seconds
    solver.parameters.num_search_workers = 4

    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise VoiceGenerationError(
            f"Cannot generate {voice_role}: CP-SAT found no solution. "
            f"Pattern: {pattern.name}, Harmony: {harmony}, Bars: {bar_count}"
        )

    # Extract solution - build full note sequence
    pitches: list[int] = []
    durations: list[Fraction] = []

    for i, var in enumerate(pitch_vars):
        idx = solver.Value(var)
        pitches.append(candidates[i][idx])
        # Duration comes from pattern position within bar
        pattern_pos = i % len(pattern.durations)
        durations.append(pattern.durations[pattern_pos])

    return Notes(tuple(pitches), tuple(durations))


def _build_pattern_attacks(
    pattern: Pattern,
    bar_duration: Fraction,
    bar_count: int,
) -> list[AttackPoint]:
    """Build attack points by repeating pattern across bars."""
    attacks: list[AttackPoint] = []

    for bar_idx in range(bar_count):
        bar_offset: Fraction = bar_duration * bar_idx
        pattern_offset: Fraction = Fraction(0)

        for dur in pattern.durations:
            offset: Fraction = bar_offset + pattern_offset
            bar_position: Fraction = pattern_offset

            # Strong beat = downbeat or mid-bar
            is_strong: bool = (
                bar_position == Fraction(0) or
                bar_position == bar_duration / 2
            )

            attacks.append(AttackPoint(
                offset=offset,
                bar_idx=bar_idx,
                is_strong_beat=is_strong,
            ))
            pattern_offset += dur

    return attacks


def _build_interval_candidates(
    attacks: list[AttackPoint],
    pattern: Pattern,
    harmony: tuple[str, ...],
    base_diatonic: int,
) -> list[tuple[int, ...]]:
    """Build candidate pitches based on pattern interval types.

    Interval meanings:
    - 0 = chord root
    - 1, 2, 3 = scale steps above root (for passing motion)
    - 4 = chord fifth
    - -1, -2 = scale steps below root

    Always includes chord root and fifth as baseline options for solver flexibility.
    """
    base_octave: int = base_diatonic // 7
    candidates: list[tuple[int, ...]] = []

    for i, attack in enumerate(attacks):
        chord: str = harmony[attack.bar_idx]
        root_degree: int = TONAL_ROOTS.get(chord, 1) - 1  # 0-indexed
        fifth_degree: int = (root_degree + 4) % 7
        third_degree: int = (root_degree + 2) % 7

        # Get interval type from pattern (cycling through pattern)
        pattern_pos: int = i % len(pattern.intervals)
        interval_type: int = pattern.intervals[pattern_pos]

        # Start with chord tones as baseline (always available)
        cands: list[int] = []
        for degree in [root_degree, third_degree, fifth_degree]:
            for oct_offset in [-1, 0, 1]:
                pitch = (base_octave + oct_offset) * 7 + degree
                if _in_voice_range(pitch, base_diatonic):
                    cands.append(pitch)

        # Add interval-specific candidates (for voice leading preferences)
        if interval_type not in (0, 2, 4):
            # Scale steps: add target degree and neighbors
            target_degree: int = (root_degree + interval_type) % 7
            for oct_offset in [-1, 0, 1]:
                pitch = (base_octave + oct_offset) * 7 + target_degree
                if pitch not in cands and _in_voice_range(pitch, base_diatonic):
                    cands.append(pitch)

            # Also allow neighboring scale degrees for flexibility
            for neighbor in [-1, 1]:
                neighbor_degree: int = (target_degree + neighbor) % 7
                for oct_offset in [-1, 0]:
                    pitch = (base_octave + oct_offset) * 7 + neighbor_degree
                    if pitch not in cands and _in_voice_range(pitch, base_diatonic):
                        cands.append(pitch)

        # Ensure we have at least one candidate
        if not cands:
            cands.append(base_diatonic)

        candidates.append(tuple(sorted(set(cands))))

    return candidates


def _in_voice_range(pitch: int, base_diatonic: int) -> bool:
    """Check if pitch is within reasonable range for voice."""
    # Allow +/- 1 octave from base
    return base_diatonic - 7 <= pitch <= base_diatonic + 7


def _collect_all_attack_times(
    existing_voices: list[Notes],
    pattern_attacks: list[AttackPoint],
) -> list[Fraction]:
    """Collect union of all attack times from all voices."""
    times: set[Fraction] = set()

    # Add pattern attack times
    for attack in pattern_attacks:
        times.add(attack.offset)

    # Add existing voice attack times
    for voice in existing_voices:
        offset: Fraction = Fraction(0)
        for dur in voice.durations:
            times.add(offset)
            offset += dur

    return sorted(times)


def _pitch_at_time(voice: Notes, t: Fraction) -> int | None:
    """Get pitch sounding at time t (handles held notes)."""
    offset: Fraction = Fraction(0)
    for pitch, dur in zip(voice.pitches, voice.durations):
        if offset <= t < offset + dur:
            return pitch
        offset += dur
    return None


def _add_consonance_constraints(
    model: cp_model.CpModel,
    pitch_vars: list[cp_model.IntVar],
    candidates: list[tuple[int, ...]],
    attacks: list[AttackPoint],
    reference_voice: Notes,
    all_attack_times: list[Fraction],
    bar_duration: Fraction,
) -> None:
    """Add consonance constraints at all attack times."""
    for attack_idx, attack in enumerate(attacks):
        # Get reference pitch sounding at this time
        ref_pitch: int | None = _pitch_at_time(reference_voice, attack.offset)
        if ref_pitch is None:
            continue

        ref_degree: int = ref_pitch % 7

        # On strong beats, forbid dissonant intervals
        if attack.is_strong_beat:
            forbidden_indices: list[int] = []
            for ci, cand_pitch in enumerate(candidates[attack_idx]):
                cand_degree: int = cand_pitch % 7
                interval: int = abs(ref_degree - cand_degree)
                interval = min(interval, 7 - interval)

                if interval in DISSONANT_INTERVALS:
                    forbidden_indices.append(ci)

            for ci in forbidden_indices:
                model.Add(pitch_vars[attack_idx] != ci)


def _add_parallel_constraints(
    model: cp_model.CpModel,
    pitch_vars: list[cp_model.IntVar],
    candidates: list[tuple[int, ...]],
    attacks: list[AttackPoint],
    reference_voice: Notes,
) -> None:
    """Add constraints to forbid parallel fifths and octaves."""
    for i in range(1, len(attacks)):
        prev_attack = attacks[i - 1]
        curr_attack = attacks[i]

        prev_ref: int | None = _pitch_at_time(reference_voice, prev_attack.offset)
        curr_ref: int | None = _pitch_at_time(reference_voice, curr_attack.offset)

        if prev_ref is None or curr_ref is None:
            continue

        ref_motion: int = curr_ref - prev_ref

        # Skip if reference is static
        if ref_motion == 0:
            continue

        prev_cands = candidates[i - 1]
        curr_cands = candidates[i]

        forbidden: list[tuple[int, int]] = []

        for pi, prev_pitch in enumerate(prev_cands):
            for ci, curr_pitch in enumerate(curr_cands):
                voice_motion: int = curr_pitch - prev_pitch

                if voice_motion == 0:
                    continue

                # Same direction?
                same_direction: bool = (ref_motion > 0) == (voice_motion > 0)
                if not same_direction:
                    continue

                # Check intervals
                prev_interval: int = abs(prev_ref - prev_pitch) % 7
                curr_interval: int = abs(curr_ref - curr_pitch) % 7

                # Parallel fifth or octave
                is_parallel_fifth: bool = prev_interval == 4 and curr_interval == 4
                is_parallel_octave: bool = prev_interval == 0 and curr_interval == 0

                if is_parallel_fifth or is_parallel_octave:
                    forbidden.append((pi, ci))

        if forbidden:
            model.AddForbiddenAssignments(
                [pitch_vars[i - 1], pitch_vars[i]],
                forbidden
            )


def _add_voice_leading_costs(
    model: cp_model.CpModel,
    pitch_vars: list[cp_model.IntVar],
    candidates: list[tuple[int, ...]],
    costs: list,
) -> None:
    """Add voice leading costs (prefer stepwise motion)."""
    for i in range(1, len(pitch_vars)):
        prev_cands = candidates[i - 1]
        curr_cands = candidates[i]

        for pi, prev_pitch in enumerate(prev_cands):
            for ci, curr_pitch in enumerate(curr_cands):
                motion: int = abs(curr_pitch - prev_pitch)

                if motion == 1:
                    cost = STEP_REWARD
                elif motion <= 3:
                    cost = SMALL_LEAP_COST
                elif motion <= 4:
                    cost = LARGE_LEAP_COST
                else:
                    cost = HUGE_LEAP_COST

                if cost != 0:
                    b_prev = model.NewBoolVar(f"vl_prev_{i}_{pi}")
                    b_curr = model.NewBoolVar(f"vl_curr_{i}_{ci}")

                    model.Add(pitch_vars[i - 1] == pi).OnlyEnforceIf(b_prev)
                    model.Add(pitch_vars[i - 1] != pi).OnlyEnforceIf(b_prev.Not())
                    model.Add(pitch_vars[i] == ci).OnlyEnforceIf(b_curr)
                    model.Add(pitch_vars[i] != ci).OnlyEnforceIf(b_curr.Not())

                    b_both = model.NewBoolVar(f"vl_both_{i}_{pi}_{ci}")
                    model.AddBoolAnd([b_prev, b_curr]).OnlyEnforceIf(b_both)
                    model.AddBoolOr([b_prev.Not(), b_curr.Not()]).OnlyEnforceIf(b_both.Not())

                    costs.append(cost * b_both)


def _add_contrary_motion_costs(
    model: cp_model.CpModel,
    pitch_vars: list[cp_model.IntVar],
    candidates: list[tuple[int, ...]],
    attacks: list[AttackPoint],
    soprano: Notes,
    costs: list,
) -> None:
    """Reward contrary motion with soprano."""
    for i in range(1, len(attacks)):
        prev_attack = attacks[i - 1]
        curr_attack = attacks[i]

        prev_sop: int | None = _pitch_at_time(soprano, prev_attack.offset)
        curr_sop: int | None = _pitch_at_time(soprano, curr_attack.offset)

        if prev_sop is None or curr_sop is None:
            continue

        sop_motion: int = curr_sop - prev_sop
        if sop_motion == 0:
            continue

        prev_cands = candidates[i - 1]
        curr_cands = candidates[i]

        for pi, prev_pitch in enumerate(prev_cands):
            for ci, curr_pitch in enumerate(curr_cands):
                voice_motion: int = curr_pitch - prev_pitch

                # Reward contrary motion
                is_contrary: bool = (sop_motion > 0) != (voice_motion > 0) and voice_motion != 0

                if is_contrary:
                    b_prev = model.NewBoolVar(f"cm_prev_{i}_{pi}")
                    b_curr = model.NewBoolVar(f"cm_curr_{i}_{ci}")

                    model.Add(pitch_vars[i - 1] == pi).OnlyEnforceIf(b_prev)
                    model.Add(pitch_vars[i - 1] != pi).OnlyEnforceIf(b_prev.Not())
                    model.Add(pitch_vars[i] == ci).OnlyEnforceIf(b_curr)
                    model.Add(pitch_vars[i] != ci).OnlyEnforceIf(b_curr.Not())

                    b_both = model.NewBoolVar(f"cm_both_{i}_{pi}_{ci}")
                    model.AddBoolAnd([b_prev, b_curr]).OnlyEnforceIf(b_both)
                    model.AddBoolOr([b_prev.Not(), b_curr.Not()]).OnlyEnforceIf(b_both.Not())

                    costs.append(CONTRARY_MOTION_REWARD * b_both)
