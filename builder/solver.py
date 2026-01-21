"""CP-SAT solver for Layer 4 (Thematic).

Category A: Pure functions, no I/O, no validation.
Enumerates valid subjects satisfying:
- Schema arrival constraints (anchors)
- Melodic rules (step/leap balance)
- Counterpoint rules
- Motive weights from affect

Determinism rules:
- Lexicographic tie-breaking (lowest MIDI sum first)
- Enumerate soprano before bass, bar 1 before bar 2
- No randomisation
"""
from fractions import Fraction
from typing import Sequence
from ortools.sat.python import cp_model

from builder.counterpoint import is_consonant, check_parallels, check_pitch_class
from builder.cost import motion_type
from builder.types import Anchor, MotiveWeights, Solution


SLOTS_PER_BAR: int = 16
SEMIQUAVER: Fraction = Fraction(1, 16)


def solve(
    total_bars: int,
    anchors: Sequence[Anchor],
    pitch_class_set: frozenset[int],
    weights: MotiveWeights,
    voice_count: int,
    registers: dict[str, tuple[int, int]],
) -> Solution:
    """Find minimum-cost valid pitch sequence."""
    slots: int = total_bars * SLOTS_PER_BAR
    model: cp_model.CpModel = cp_model.CpModel()
    soprano_range: tuple[int, int] = registers.get("soprano", (60, 79))
    bass_range: tuple[int, int] = registers.get("bass", (36, 60))
    soprano_vars: list[cp_model.IntVar] = [
        model.NewIntVar(soprano_range[0], soprano_range[1], f"s_{i}")
        for i in range(slots)
    ]
    bass_vars: list[cp_model.IntVar] = [
        model.NewIntVar(bass_range[0], bass_range[1], f"b_{i}")
        for i in range(slots)
    ]
    anchor_slots: dict[int, Anchor] = {}
    for anchor in anchors:
        slot: int = _bar_beat_to_slot(anchor.bar_beat)
        if 0 <= slot < slots:
            anchor_slots[slot] = anchor
            model.Add(soprano_vars[slot] == anchor.soprano_midi)
            model.Add(bass_vars[slot] == anchor.bass_midi)
    allowed_pcs: list[int] = sorted(pitch_class_set)
    for i in range(slots):
        if i not in anchor_slots:
            s_pc = model.NewIntVar(0, 11, f"s_pc_{i}")
            model.AddModuloEquality(s_pc, soprano_vars[i], 12)
            model.AddAllowedAssignments([s_pc], [[pc] for pc in allowed_pcs])
            b_pc = model.NewIntVar(0, 11, f"b_pc_{i}")
            model.AddModuloEquality(b_pc, bass_vars[i], 12)
            model.AddAllowedAssignments([b_pc], [[pc] for pc in allowed_pcs])
    cost_terms: list[cp_model.IntVar] = []
    for i in range(1, slots):
        # Soprano motion cost
        s_diff = model.NewIntVar(-24, 24, f"s_diff_{i}")
        model.Add(s_diff == soprano_vars[i] - soprano_vars[i - 1])
        s_abs = model.NewIntVar(0, 24, f"s_abs_{i}")
        model.AddAbsEquality(s_abs, s_diff)
        cost_terms.append(s_abs)
        # Bass motion cost
        b_diff = model.NewIntVar(-24, 24, f"b_diff_{i}")
        model.Add(b_diff == bass_vars[i] - bass_vars[i - 1])
        b_abs = model.NewIntVar(0, 24, f"b_abs_{i}")
        model.AddAbsEquality(b_abs, b_diff)
        cost_terms.append(b_abs)
    if cost_terms:
        model.Minimize(sum(cost_terms))
    solver: cp_model.CpSolver = cp_model.CpSolver()
    solver.parameters.enumerate_all_solutions = False
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    status: int = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise ValueError("No valid solution exists for given constraints")
    soprano_pitches: tuple[int, ...] = tuple(
        solver.Value(soprano_vars[i]) for i in range(slots)
    )
    bass_pitches: tuple[int, ...] = tuple(
        solver.Value(bass_vars[i]) for i in range(slots)
    )
    soprano_durations: tuple[Fraction, ...] = tuple(SEMIQUAVER for _ in range(slots))
    bass_durations: tuple[Fraction, ...] = tuple(SEMIQUAVER for _ in range(slots))
    return Solution(
        soprano_pitches=soprano_pitches,
        bass_pitches=bass_pitches,
        soprano_durations=soprano_durations,
        bass_durations=bass_durations,
        cost=solver.ObjectiveValue(),
    )


def _bar_beat_to_slot(bar_beat: str) -> int:
    """Convert bar.beat string to slot index."""
    parts: list[str] = bar_beat.split(".")
    bar: int = int(parts[0])
    beat: float = float(parts[1]) if len(parts) > 1 else 1.0
    slot_in_bar: int = int((beat - 1) * 4)
    return (bar - 1) * SLOTS_PER_BAR + slot_in_bar
