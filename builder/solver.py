"""Counterpoint solver entry point."""

from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from ortools.sat.python import cp_model

from shared.errors import SolverTimeoutError, SolverInfeasibleError
from builder.costs import VoiceMode
from builder.slice import extract_slices


# S10 cost weights (multiplied by COST_MULTIPLIER in _add_cost_terms)
CONSECUTIVE_REPEAT_COST: float = 0.3
OSCILLATION_COST: float = 0.5


@dataclass(frozen=True)
class FixedPitch:
    """Fixed pitch at a specific position (solver input)."""
    offset: Fraction
    voice: int
    midi: int


@dataclass(frozen=True)
class Slot:
    """Position requiring a pitch."""
    offset: Fraction
    voice: int
    duration: Fraction


@dataclass(frozen=True)
class SolverConfig:
    """Solver parameters."""
    voice_count: int
    pitch_class_set: frozenset[int]
    tessitura_medians: dict[int, int]
    tessitura_span: int
    invertible_at: int | None
    voice_mode: VoiceMode
    motive_weights: dict[str, float]
    metre_numerator: int


@dataclass(frozen=True)
class SolverResult:
    """Solver output with sparse pitch map."""
    pitches: dict[tuple[Fraction, int], int]
    cost: float


# =============================================================================
# Validation
# =============================================================================


def _validate_inputs(
    fixed_pitches: list[FixedPitch],
    slots: list[Slot],
    config: SolverConfig,
) -> None:
    """Validate solver inputs. Raises AssertionError on invalid input."""
    assert config.voice_count in {2, 3, 4}, (
        f"voice_count must be 2, 3, or 4, got {config.voice_count}"
    )
    for fp in fixed_pitches:
        assert 0 <= fp.voice < config.voice_count, (
            f"FixedPitch voice {fp.voice} out of range [0, {config.voice_count})"
        )
    for slot in slots:
        assert 0 <= slot.voice < config.voice_count, (
            f"Slot voice {slot.voice} out of range [0, {config.voice_count})"
        )
    for fp in fixed_pitches:
        pc: int = fp.midi % 12
        assert pc in config.pitch_class_set, (
            f"FixedPitch pitch {fp.midi} (pc={pc}) not in pitch_class_set "
            f"{config.pitch_class_set}"
        )
    assert config.invertible_at in {None, 10, 12}, (
        f"invertible_at must be None, 10, or 12, got {config.invertible_at}"
    )
    required_keys: set[str] = {"step", "skip", "leap", "large_leap"}
    assert required_keys <= set(config.motive_weights.keys()), (
        f"motive_weights missing keys: {required_keys - set(config.motive_weights.keys())}"
    )
    for voice in range(config.voice_count):
        assert voice in config.tessitura_medians, (
            f"tessitura_medians missing voice {voice}"
        )
    slot_keys: list[tuple[Fraction, int]] = [(s.offset, s.voice) for s in slots]
    assert len(slot_keys) == len(set(slot_keys)), "Duplicate (offset, voice) in slots"
    fp_keys: list[tuple[Fraction, int]] = [(fp.offset, fp.voice) for fp in fixed_pitches]
    assert len(fp_keys) == len(set(fp_keys)), "Duplicate (offset, voice) in fixed_pitches"
    slot_key_set: set[tuple[Fraction, int]] = set(slot_keys)
    for fp in fixed_pitches:
        key = (fp.offset, fp.voice)
        assert key in slot_key_set, f"FixedPitch at {key} has no corresponding slot"


# =============================================================================
# Domain Computation
# =============================================================================


def _compute_domain(
    voice: int,
    config: SolverConfig,
) -> list[int]:
    """Compute valid MIDI pitches for a voice."""
    median: int = config.tessitura_medians[voice]
    span: int = config.tessitura_span
    low: int = median - span
    high: int = median + span
    domain: list[int] = []
    for midi in range(low, high + 1):
        if midi % 12 in config.pitch_class_set:
            domain.append(midi)
    return domain


# =============================================================================
# CP-SAT Model Building
# =============================================================================


def _build_model(
    fixed_pitches: list[FixedPitch],
    slots: list[Slot],
    config: SolverConfig,
) -> tuple[cp_model.CpModel, dict[tuple[Fraction, int], Any], Any]:
    """Build CP-SAT model with variables and constraints."""
    model = cp_model.CpModel()
    fixed_pitch_map: dict[tuple[Fraction, int], int] = {
        (fp.offset, fp.voice): fp.midi for fp in fixed_pitches
    }
    sorted_slots = sorted(slots, key=lambda s: (s.offset, s.voice))
    variables: dict[tuple[Fraction, int], Any] = {}
    for slot in sorted_slots:
        key = (slot.offset, slot.voice)
        if key in fixed_pitch_map:
            midi = fixed_pitch_map[key]
            var = model.NewIntVar(midi, midi, f"pitch_{slot.offset}_{slot.voice}")
        else:
            domain = _compute_domain(slot.voice, config)
            assert len(domain) > 0, (
                f"Empty domain for voice {slot.voice} with median "
                f"{config.tessitura_medians[slot.voice]} and span {config.tessitura_span}"
            )
            var = model.NewIntVarFromDomain(
                cp_model.Domain.FromValues(domain),
                f"pitch_{slot.offset}_{slot.voice}"
            )
        variables[key] = var
    _add_parallel_constraints(model, variables, sorted_slots, config.voice_count)
    cost_var = _add_cost_terms(model, variables, sorted_slots, config)
    model.Minimize(cost_var)
    return model, variables, cost_var


# =============================================================================
# Parallel Constraint Encoding
# =============================================================================


def _add_parallel_constraints(
    model: cp_model.CpModel,
    variables: dict[tuple[Fraction, int], Any],
    slots: list[Slot],
    voice_count: int,
) -> None:
    """Add constraints forbidding parallel unisons, fifths, octaves."""
    slots_by_offset: dict[Fraction, dict[int, Slot]] = {}
    for slot in slots:
        if slot.offset not in slots_by_offset:
            slots_by_offset[slot.offset] = {}
        slots_by_offset[slot.offset][slot.voice] = slot
    sorted_offsets: list[Fraction] = sorted(slots_by_offset.keys())
    for voice_a in range(voice_count):
        for voice_b in range(voice_a + 1, voice_count):
            for i in range(len(sorted_offsets) - 1):
                offset1 = sorted_offsets[i]
                offset2 = sorted_offsets[i + 1]
                if voice_a not in slots_by_offset[offset1]:
                    continue
                if voice_b not in slots_by_offset[offset1]:
                    continue
                if voice_a not in slots_by_offset[offset2]:
                    continue
                if voice_b not in slots_by_offset[offset2]:
                    continue
                va_t1 = variables[(offset1, voice_a)]
                vb_t1 = variables[(offset1, voice_b)]
                va_t2 = variables[(offset2, voice_a)]
                vb_t2 = variables[(offset2, voice_b)]
                _add_parallel_constraint_for_interval(
                    model, va_t1, vb_t1, va_t2, vb_t2, 0,
                    f"no_parallel_octave_{voice_a}_{voice_b}_{offset1}_{offset2}"
                )
                _add_parallel_constraint_for_interval(
                    model, va_t1, vb_t1, va_t2, vb_t2, 7,
                    f"no_parallel_fifth_{voice_a}_{voice_b}_{offset1}_{offset2}"
                )


def _add_parallel_constraint_for_interval(
    model: cp_model.CpModel,
    va_t1: Any,
    vb_t1: Any,
    va_t2: Any,
    vb_t2: Any,
    target_interval: int,
    name: str,
) -> None:
    """Add constraint forbidding parallel motion at target_interval."""
    diff_t1 = model.NewIntVar(-127, 127, f"{name}_diff_t1")
    diff_t2 = model.NewIntVar(-127, 127, f"{name}_diff_t2")
    model.Add(diff_t1 == va_t1 - vb_t1)
    model.Add(diff_t2 == va_t2 - vb_t2)
    interval1_is_target = model.NewBoolVar(f"{name}_int1_target")
    interval2_is_target = model.NewBoolVar(f"{name}_int2_target")
    valid_diffs: list[int] = [d for d in range(-127, 128) if abs(d) % 12 == target_interval]
    model.AddAllowedAssignments([diff_t1], [[d] for d in valid_diffs]).OnlyEnforceIf(interval1_is_target)
    model.AddForbiddenAssignments([diff_t1], [[d] for d in valid_diffs]).OnlyEnforceIf(interval1_is_target.Not())
    model.AddAllowedAssignments([diff_t2], [[d] for d in valid_diffs]).OnlyEnforceIf(interval2_is_target)
    model.AddForbiddenAssignments([diff_t2], [[d] for d in valid_diffs]).OnlyEnforceIf(interval2_is_target.Not())
    motion_a = model.NewIntVar(-127, 127, f"{name}_motion_a")
    motion_b = model.NewIntVar(-127, 127, f"{name}_motion_b")
    model.Add(motion_a == va_t2 - va_t1)
    model.Add(motion_b == vb_t2 - vb_t1)
    a_up = model.NewBoolVar(f"{name}_a_up")
    a_down = model.NewBoolVar(f"{name}_a_down")
    b_up = model.NewBoolVar(f"{name}_b_up")
    b_down = model.NewBoolVar(f"{name}_b_down")
    model.Add(motion_a > 0).OnlyEnforceIf(a_up)
    model.Add(motion_a <= 0).OnlyEnforceIf(a_up.Not())
    model.Add(motion_a < 0).OnlyEnforceIf(a_down)
    model.Add(motion_a >= 0).OnlyEnforceIf(a_down.Not())
    model.Add(motion_b > 0).OnlyEnforceIf(b_up)
    model.Add(motion_b <= 0).OnlyEnforceIf(b_up.Not())
    model.Add(motion_b < 0).OnlyEnforceIf(b_down)
    model.Add(motion_b >= 0).OnlyEnforceIf(b_down.Not())
    same_direction_up = model.NewBoolVar(f"{name}_same_up")
    same_direction_down = model.NewBoolVar(f"{name}_same_down")
    model.AddBoolAnd([a_up, b_up]).OnlyEnforceIf(same_direction_up)
    model.AddBoolOr([a_up.Not(), b_up.Not()]).OnlyEnforceIf(same_direction_up.Not())
    model.AddBoolAnd([a_down, b_down]).OnlyEnforceIf(same_direction_down)
    model.AddBoolOr([a_down.Not(), b_down.Not()]).OnlyEnforceIf(same_direction_down.Not())
    model.AddBoolOr([
        interval1_is_target.Not(),
        interval2_is_target.Not(),
        same_direction_up.Not()
    ])
    model.AddBoolOr([
        interval1_is_target.Not(),
        interval2_is_target.Not(),
        same_direction_down.Not()
    ])


# =============================================================================
# Cost Term Encoding
# =============================================================================


def _add_cost_terms(
    model: cp_model.CpModel,
    variables: dict[tuple[Fraction, int], Any],
    slots: list[Slot],
    config: SolverConfig,
) -> Any:
    """Add soft constraint cost terms to model."""
    COST_MULTIPLIER: int = 1000
    cost_terms: list[Any] = []
    slots_by_voice: dict[int, list[Slot]] = {}
    for slot in slots:
        if slot.voice not in slots_by_voice:
            slots_by_voice[slot.voice] = []
        slots_by_voice[slot.voice].append(slot)
    for voice in slots_by_voice:
        slots_by_voice[voice].sort(key=lambda s: s.offset)
    # S06: Tessitura deviation cost
    for voice in range(config.voice_count):
        if voice not in slots_by_voice:
            continue
        median: int = config.tessitura_medians[voice]
        for slot in slots_by_voice[voice]:
            var = variables[(slot.offset, slot.voice)]
            abs_dev = model.NewIntVar(0, 127, f"abs_dev_{slot.offset}_{voice}")
            diff = model.NewIntVar(-127, 127, f"tess_diff_{slot.offset}_{voice}")
            model.Add(diff == var - median)
            model.AddAbsEquality(abs_dev, diff)
            cost_term = model.NewIntVar(0, 127 * 100, f"tess_cost_{slot.offset}_{voice}")
            model.Add(cost_term == abs_dev * 100)
            cost_terms.append(cost_term)
    # S01-S04: Melodic motion costs
    step_cost: int = int(config.motive_weights["step"] * COST_MULTIPLIER)
    skip_cost: int = int(config.motive_weights["skip"] * COST_MULTIPLIER)
    leap_cost: int = int(config.motive_weights["leap"] * COST_MULTIPLIER)
    large_leap_cost: int = int(config.motive_weights["large_leap"] * COST_MULTIPLIER)
    for voice in range(config.voice_count):
        if voice not in slots_by_voice:
            continue
        voice_slots = slots_by_voice[voice]
        for i in range(len(voice_slots) - 1):
            slot1 = voice_slots[i]
            slot2 = voice_slots[i + 1]
            var1 = variables[(slot1.offset, slot1.voice)]
            var2 = variables[(slot2.offset, slot2.voice)]
            mel_diff = model.NewIntVar(-127, 127, f"mel_diff_{voice}_{i}")
            abs_mel = model.NewIntVar(0, 127, f"abs_mel_{voice}_{i}")
            model.Add(mel_diff == var2 - var1)
            model.AddAbsEquality(abs_mel, mel_diff)
            is_step = model.NewBoolVar(f"is_step_{voice}_{i}")
            is_skip = model.NewBoolVar(f"is_skip_{voice}_{i}")
            is_leap = model.NewBoolVar(f"is_leap_{voice}_{i}")
            is_large = model.NewBoolVar(f"is_large_{voice}_{i}")
            model.Add(abs_mel <= 2).OnlyEnforceIf(is_step)
            model.Add(abs_mel > 2).OnlyEnforceIf(is_step.Not())
            model.Add(abs_mel >= 3).OnlyEnforceIf(is_skip)
            model.Add(abs_mel <= 4).OnlyEnforceIf(is_skip)
            model.AddBoolOr([is_step, is_skip.Not()])
            model.Add(abs_mel >= 5).OnlyEnforceIf(is_leap)
            model.Add(abs_mel <= 7).OnlyEnforceIf(is_leap)
            model.AddBoolOr([is_step, is_skip, is_leap.Not()])
            model.Add(abs_mel >= 8).OnlyEnforceIf(is_large)
            model.AddBoolOr([is_step, is_skip, is_leap, is_large.Not()])
            model.AddExactlyOne([is_step, is_skip, is_leap, is_large])
            mel_cost = model.NewIntVar(0, large_leap_cost, f"mel_cost_{voice}_{i}")
            model.Add(mel_cost == step_cost).OnlyEnforceIf(is_step)
            model.Add(mel_cost == skip_cost).OnlyEnforceIf(is_skip)
            model.Add(mel_cost == leap_cost).OnlyEnforceIf(is_leap)
            model.Add(mel_cost == large_leap_cost).OnlyEnforceIf(is_large)
            cost_terms.append(mel_cost)
    # S10: Repetition penalty
    consecutive_cost: int = int(CONSECUTIVE_REPEAT_COST * COST_MULTIPLIER)
    oscillation_cost: int = int(OSCILLATION_COST * COST_MULTIPLIER)
    for voice in range(config.voice_count):
        if voice not in slots_by_voice:
            continue
        voice_slots = slots_by_voice[voice]
        # S10a: Consecutive identical pitches
        for i in range(len(voice_slots) - 1):
            var1 = variables[(voice_slots[i].offset, voice)]
            var2 = variables[(voice_slots[i + 1].offset, voice)]
            is_same = model.NewBoolVar(f"same_{voice}_{i}")
            model.Add(var1 == var2).OnlyEnforceIf(is_same)
            model.Add(var1 != var2).OnlyEnforceIf(is_same.Not())
            repeat_cost = model.NewIntVar(0, consecutive_cost, f"repeat_cost_{voice}_{i}")
            model.Add(repeat_cost == consecutive_cost).OnlyEnforceIf(is_same)
            model.Add(repeat_cost == 0).OnlyEnforceIf(is_same.Not())
            cost_terms.append(repeat_cost)
        # S10b: Oscillation (A-B-A pattern where A != B)
        for i in range(len(voice_slots) - 2):
            var0 = variables[(voice_slots[i].offset, voice)]
            var1 = variables[(voice_slots[i + 1].offset, voice)]
            var2 = variables[(voice_slots[i + 2].offset, voice)]
            is_osc_a = model.NewBoolVar(f"osc_a_{voice}_{i}")
            is_osc_b = model.NewBoolVar(f"osc_b_{voice}_{i}")
            is_osc = model.NewBoolVar(f"osc_{voice}_{i}")
            model.Add(var0 == var2).OnlyEnforceIf(is_osc_a)
            model.Add(var0 != var2).OnlyEnforceIf(is_osc_a.Not())
            model.Add(var0 != var1).OnlyEnforceIf(is_osc_b)
            model.Add(var0 == var1).OnlyEnforceIf(is_osc_b.Not())
            model.AddBoolAnd([is_osc_a, is_osc_b]).OnlyEnforceIf(is_osc)
            model.AddBoolOr([is_osc_a.Not(), is_osc_b.Not()]).OnlyEnforceIf(is_osc.Not())
            osc_cost = model.NewIntVar(0, oscillation_cost, f"osc_cost_{voice}_{i}")
            model.Add(osc_cost == oscillation_cost).OnlyEnforceIf(is_osc)
            model.Add(osc_cost == 0).OnlyEnforceIf(is_osc.Not())
            cost_terms.append(osc_cost)
    # Total cost
    total_cost = model.NewIntVar(0, 100000000, "total_cost")
    model.Add(total_cost == sum(cost_terms))
    return total_cost


# =============================================================================
# Main Solve Function
# =============================================================================


def solve(
    fixed_pitches: list[FixedPitch],
    slots: list[Slot],
    config: SolverConfig,
    timeout_seconds: float = 10.0,
) -> SolverResult:
    """Fill slots with pitches satisfying all hard constraints."""
    _validate_inputs(fixed_pitches, slots, config)
    if not slots:
        return SolverResult(pitches={}, cost=0.0)
    model, variables, cost_var = _build_model(fixed_pitches, slots, config)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout_seconds
    status = solver.Solve(model)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        pitches: dict[tuple[Fraction, int], int] = {}
        for key, var in variables.items():
            pitches[key] = solver.Value(var)
        cost: float = solver.ObjectiveValue() / 1000.0
        return SolverResult(pitches=pitches, cost=cost)
    if status == cp_model.INFEASIBLE:
        raise SolverInfeasibleError("No solution satisfies all hard constraints")
    raise SolverTimeoutError(f"CP-SAT solver exceeded {timeout_seconds}s time limit")
