"""CP-SAT solver strategy for diatonic inner voice resolution.

Solves ALL inner voice degrees across ALL slices simultaneously using
Google OR-Tools CP-SAT solver. This provides global optimization,
finding solutions that local greedy search cannot.

All operations are in degree space (1-7). No MIDI conversion.
"""
from fractions import Fraction

from ortools.sat.python import cp_model

from engine.diatonic_solver.core import DiatonicPitch, DiatonicSlice
from engine.diatonic_solver.constraints import (
    PARALLEL_FIFTH_COST,
    PARALLEL_OCTAVE_COST,
    UNISON_COST,
    NON_CHORD_TONE_COST,
    STATIC_VOICE_COST,
    STEP_REWARD,
    SMALL_LEAP_COST,
    MEDIUM_LEAP_COST,
    LARGE_LEAP_COST,
    THEMATIC_MATCH_REWARD,
    get_chord_tones,
)
from shared.parallels import is_parallel_fifth_diatonic, is_parallel_octave_diatonic


def solve_cpsat(
    slices: list[DiatonicSlice],
    voice_count: int,
    is_strong_beat: dict[int, bool] | None = None,
    thematic_targets: dict[tuple[int, int], int] | None = None,
    timeout_seconds: float = 5.0,
) -> list[DiatonicSlice] | None:
    """Solve all inner voice degrees using CP-SAT.

    Args:
        slices: List of DiatonicSlice with soprano/bass set, inner voices None
        voice_count: Total number of voices (e.g., 4 for SATB)
        is_strong_beat: Optional dict mapping slice_idx to whether it's a strong beat
        thematic_targets: Optional dict mapping (slice_idx, voice_idx) to target degree
        timeout_seconds: Solver time limit

    Returns:
        List of DiatonicSlice with all voices filled, or None if infeasible.
    """
    if not slices:
        return slices

    n_slices = len(slices)
    inner_count = voice_count - 2

    if inner_count <= 0:
        return slices

    # Create CP-SAT model
    model = cp_model.CpModel()

    # Variables: degree[slice_idx][voice_idx] = degree value (1-7)
    degree_vars: dict[tuple[int, int], cp_model.IntVar] = {}
    for si in range(n_slices):
        for vi in range(1, voice_count - 1):  # Inner voices only
            degree_vars[(si, vi)] = model.NewIntVar(1, 7, f"d_{si}_{vi}")

    # === Hard constraints: no parallel fifths/octaves ===
    for si in range(1, n_slices):
        prev_slice = slices[si - 1]
        curr_slice = slices[si]

        # Get fixed outer voice degrees
        prev_soprano = prev_slice.get_degree(0)
        curr_soprano = curr_slice.get_degree(0)
        prev_bass = prev_slice.get_degree(voice_count - 1)
        curr_bass = curr_slice.get_degree(voice_count - 1)

        if any(d is None for d in [prev_soprano, curr_soprano, prev_bass, curr_bass]):
            continue

        # Check all voice pairs for forbidden parallel patterns
        for upper in range(voice_count):
            for lower in range(upper + 1, voice_count):
                _add_parallel_constraints(
                    model, degree_vars, si, upper, lower, voice_count,
                    prev_soprano, curr_soprano, prev_bass, curr_bass,
                    prev_slice, curr_slice,
                )

    # === Soft constraints via costs ===
    costs: list = []

    for si, slice_data in enumerate(slices):
        bass_deg = slice_data.get_degree(voice_count - 1)
        if bass_deg is None:
            continue

        chord_tones = get_chord_tones(bass_deg)
        strong_beat = is_strong_beat.get(si, False) if is_strong_beat else False
        multiplier = 2 if strong_beat else 1

        for vi in range(1, voice_count - 1):
            var = degree_vars[(si, vi)]

            # Chord tone preference: penalize non-chord tones
            for deg in range(1, 8):
                if deg not in chord_tones:
                    indicator = model.NewBoolVar(f"nct_{si}_{vi}_{deg}")
                    model.Add(var == deg).OnlyEnforceIf(indicator)
                    model.Add(var != deg).OnlyEnforceIf(indicator.Not())
                    costs.append(NON_CHORD_TONE_COST * multiplier * indicator)

            # Unison penalty with outer voices
            soprano_deg = slice_data.get_degree(0)
            if soprano_deg is not None:
                uni_sop = model.NewBoolVar(f"uni_sop_{si}_{vi}")
                model.Add(var == soprano_deg).OnlyEnforceIf(uni_sop)
                model.Add(var != soprano_deg).OnlyEnforceIf(uni_sop.Not())
                costs.append(UNISON_COST * uni_sop)

            if bass_deg is not None:
                uni_bass = model.NewBoolVar(f"uni_bass_{si}_{vi}")
                model.Add(var == bass_deg).OnlyEnforceIf(uni_bass)
                model.Add(var != bass_deg).OnlyEnforceIf(uni_bass.Not())
                costs.append(UNISON_COST * uni_bass)

            # Thematic matching reward
            if thematic_targets and (si, vi) in thematic_targets:
                target = thematic_targets[(si, vi)]
                match_ind = model.NewBoolVar(f"thm_{si}_{vi}")
                model.Add(var == target).OnlyEnforceIf(match_ind)
                model.Add(var != target).OnlyEnforceIf(match_ind.Not())
                costs.append(-THEMATIC_MATCH_REWARD * match_ind)  # Negative = reward

    # Inner-inner unison penalties
    for si in range(n_slices):
        inner_voices = list(range(1, voice_count - 1))
        for i, vi1 in enumerate(inner_voices):
            for vi2 in inner_voices[i + 1:]:
                for deg in range(1, 8):
                    b1 = model.NewBoolVar(f"ii1_{si}_{vi1}_{vi2}_{deg}")
                    b2 = model.NewBoolVar(f"ii2_{si}_{vi1}_{vi2}_{deg}")
                    b_both = model.NewBoolVar(f"iib_{si}_{vi1}_{vi2}_{deg}")

                    model.Add(degree_vars[(si, vi1)] == deg).OnlyEnforceIf(b1)
                    model.Add(degree_vars[(si, vi1)] != deg).OnlyEnforceIf(b1.Not())
                    model.Add(degree_vars[(si, vi2)] == deg).OnlyEnforceIf(b2)
                    model.Add(degree_vars[(si, vi2)] != deg).OnlyEnforceIf(b2.Not())

                    model.AddBoolAnd([b1, b2]).OnlyEnforceIf(b_both)
                    model.AddBoolOr([b1.Not(), b2.Not()]).OnlyEnforceIf(b_both.Not())

                    costs.append(UNISON_COST * b_both)

    # Voice leading costs between consecutive slices
    for si in range(1, n_slices):
        for vi in range(1, voice_count - 1):
            prev_var = degree_vars[(si - 1, vi)]
            curr_var = degree_vars[(si, vi)]

            for prev_deg in range(1, 8):
                for curr_deg in range(1, 8):
                    motion = abs(curr_deg - prev_deg)

                    if motion == 0:
                        cost = STATIC_VOICE_COST
                    elif motion == 1:
                        cost = STEP_REWARD
                    elif motion == 2:
                        cost = SMALL_LEAP_COST
                    elif motion == 3:
                        cost = MEDIUM_LEAP_COST
                    else:
                        cost = LARGE_LEAP_COST

                    if cost != 0:
                        b1 = model.NewBoolVar(f"vl1_{si}_{vi}_{prev_deg}_{curr_deg}")
                        b2 = model.NewBoolVar(f"vl2_{si}_{vi}_{prev_deg}_{curr_deg}")
                        b_trans = model.NewBoolVar(f"vlt_{si}_{vi}_{prev_deg}_{curr_deg}")

                        model.Add(prev_var == prev_deg).OnlyEnforceIf(b1)
                        model.Add(prev_var != prev_deg).OnlyEnforceIf(b1.Not())
                        model.Add(curr_var == curr_deg).OnlyEnforceIf(b2)
                        model.Add(curr_var != curr_deg).OnlyEnforceIf(b2.Not())

                        model.AddBoolAnd([b1, b2]).OnlyEnforceIf(b_trans)
                        model.AddBoolOr([b1.Not(), b2.Not()]).OnlyEnforceIf(b_trans.Not())

                        costs.append(cost * b_trans)

    # Minimize total cost
    if costs:
        model.Minimize(sum(costs))

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout_seconds
    solver.parameters.num_search_workers = 4

    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    # Extract solution and build result slices
    result_slices: list[DiatonicSlice] = []

    for si, slice_data in enumerate(slices):
        pitches: list[DiatonicPitch | None] = []

        for vi in range(voice_count):
            if vi == 0 or vi == voice_count - 1:
                # Outer voice - preserve original
                pitches.append(slice_data.pitches[vi])
            else:
                # Inner voice - use solved degree
                deg = solver.Value(degree_vars[(si, vi)])
                pitches.append(DiatonicPitch(deg))

        result_slices.append(DiatonicSlice(
            offset=slice_data.offset,
            pitches=tuple(pitches),
        ))

    return result_slices


def _add_parallel_constraints(
    model: cp_model.CpModel,
    degree_vars: dict[tuple[int, int], cp_model.IntVar],
    si: int,
    upper: int,
    lower: int,
    voice_count: int,
    prev_soprano: int,
    curr_soprano: int,
    prev_bass: int,
    curr_bass: int,
    prev_slice: DiatonicSlice,
    curr_slice: DiatonicSlice,
) -> None:
    """Add parallel fifth/octave constraints for a voice pair."""

    def get_prev_deg(vi: int) -> int | None:
        if vi == 0:
            return prev_soprano
        elif vi == voice_count - 1:
            return prev_bass
        else:
            return None  # Variable

    def get_curr_deg(vi: int) -> int | None:
        if vi == 0:
            return curr_soprano
        elif vi == voice_count - 1:
            return curr_bass
        else:
            return None  # Variable

    prev_upper_fixed = get_prev_deg(upper)
    prev_lower_fixed = get_prev_deg(lower)
    curr_upper_fixed = get_curr_deg(upper)
    curr_lower_fixed = get_curr_deg(lower)

    # Case 1: Both voices are outer (fixed) - just check
    if prev_upper_fixed and prev_lower_fixed and curr_upper_fixed and curr_lower_fixed:
        if is_parallel_fifth_diatonic(prev_upper_fixed, prev_lower_fixed,
                                       curr_upper_fixed, curr_lower_fixed):
            model.Add(False)  # Infeasible
        if is_parallel_octave_diatonic(prev_upper_fixed, prev_lower_fixed,
                                        curr_upper_fixed, curr_lower_fixed):
            model.Add(False)
        return

    # Case 2: One voice is variable - enumerate forbidden values
    if prev_upper_fixed and curr_upper_fixed:
        # Upper is outer, lower is inner variable
        prev_var = degree_vars[(si - 1, lower)]
        curr_var = degree_vars[(si, lower)]

        forbidden = []
        for prev_deg in range(1, 8):
            for curr_deg in range(1, 8):
                if is_parallel_fifth_diatonic(prev_upper_fixed, prev_deg,
                                               curr_upper_fixed, curr_deg):
                    forbidden.append((prev_deg, curr_deg))
                if is_parallel_octave_diatonic(prev_upper_fixed, prev_deg,
                                                curr_upper_fixed, curr_deg):
                    forbidden.append((prev_deg, curr_deg))

        if forbidden:
            # Convert to constraint tuples (need index into 1-7)
            for prev_forbidden, curr_forbidden in forbidden:
                b1 = model.NewBoolVar(f"par_l_{si}_{upper}_{lower}_{prev_forbidden}_{curr_forbidden}_1")
                b2 = model.NewBoolVar(f"par_l_{si}_{upper}_{lower}_{prev_forbidden}_{curr_forbidden}_2")
                model.Add(prev_var == prev_forbidden).OnlyEnforceIf(b1)
                model.Add(prev_var != prev_forbidden).OnlyEnforceIf(b1.Not())
                model.Add(curr_var == curr_forbidden).OnlyEnforceIf(b2)
                model.Add(curr_var != curr_forbidden).OnlyEnforceIf(b2.Not())
                model.AddBoolOr([b1.Not(), b2.Not()])

    elif prev_lower_fixed and curr_lower_fixed:
        # Lower is outer, upper is inner variable
        prev_var = degree_vars[(si - 1, upper)]
        curr_var = degree_vars[(si, upper)]

        forbidden = []
        for prev_deg in range(1, 8):
            for curr_deg in range(1, 8):
                if is_parallel_fifth_diatonic(prev_deg, prev_lower_fixed,
                                               curr_deg, curr_lower_fixed):
                    forbidden.append((prev_deg, curr_deg))
                if is_parallel_octave_diatonic(prev_deg, prev_lower_fixed,
                                                curr_deg, curr_lower_fixed):
                    forbidden.append((prev_deg, curr_deg))

        if forbidden:
            for prev_forbidden, curr_forbidden in forbidden:
                b1 = model.NewBoolVar(f"par_u_{si}_{upper}_{lower}_{prev_forbidden}_{curr_forbidden}_1")
                b2 = model.NewBoolVar(f"par_u_{si}_{upper}_{lower}_{prev_forbidden}_{curr_forbidden}_2")
                model.Add(prev_var == prev_forbidden).OnlyEnforceIf(b1)
                model.Add(prev_var != prev_forbidden).OnlyEnforceIf(b1.Not())
                model.Add(curr_var == curr_forbidden).OnlyEnforceIf(b2)
                model.Add(curr_var != curr_forbidden).OnlyEnforceIf(b2.Not())
                model.AddBoolOr([b1.Not(), b2.Not()])

    else:
        # Both voices are inner variables - enumerate all forbidden 4-tuples
        prev_upper_var = degree_vars[(si - 1, upper)]
        curr_upper_var = degree_vars[(si, upper)]
        prev_lower_var = degree_vars[(si - 1, lower)]
        curr_lower_var = degree_vars[(si, lower)]

        for pu in range(1, 8):
            for cu in range(1, 8):
                for pl in range(1, 8):
                    for cl in range(1, 8):
                        if is_parallel_fifth_diatonic(pu, pl, cu, cl) or \
                           is_parallel_octave_diatonic(pu, pl, cu, cl):
                            # Forbid this combination
                            b1 = model.NewBoolVar(f"par4_{si}_{upper}_{lower}_{pu}_{cu}_{pl}_{cl}_1")
                            b2 = model.NewBoolVar(f"par4_{si}_{upper}_{lower}_{pu}_{cu}_{pl}_{cl}_2")
                            b3 = model.NewBoolVar(f"par4_{si}_{upper}_{lower}_{pu}_{cu}_{pl}_{cl}_3")
                            b4 = model.NewBoolVar(f"par4_{si}_{upper}_{lower}_{pu}_{cu}_{pl}_{cl}_4")

                            model.Add(prev_upper_var == pu).OnlyEnforceIf(b1)
                            model.Add(prev_upper_var != pu).OnlyEnforceIf(b1.Not())
                            model.Add(curr_upper_var == cu).OnlyEnforceIf(b2)
                            model.Add(curr_upper_var != cu).OnlyEnforceIf(b2.Not())
                            model.Add(prev_lower_var == pl).OnlyEnforceIf(b3)
                            model.Add(prev_lower_var != pl).OnlyEnforceIf(b3.Not())
                            model.Add(curr_lower_var == cl).OnlyEnforceIf(b4)
                            model.Add(curr_lower_var != cl).OnlyEnforceIf(b4.Not())

                            model.AddBoolOr([b1.Not(), b2.Not(), b3.Not(), b4.Not()])
