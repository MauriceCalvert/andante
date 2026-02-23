"""CP-SAT stretto-first pitch generation.

Produces degree sequences where stretto consonance is a built-in constraint.
Two-phase sampling: random-objective anchor + feasibility enumeration per restart.
"""
import random

from ortools.sat.python import cp_model

from motifs.subject_gen.constants import (
    ALLOWED_FINALS,
    CPSAT_NUM_RESTARTS,
    CPSAT_SOLUTIONS_PER_RESTART,
    CPSAT_SOLVER_TIMEOUT,
    MAX_LARGE_LEAPS,
    MAX_PITCH_FREQ,
    MAX_SAME_SIGN_RUN,
    MIN_STEP_FRACTION,
    PITCH_HI,
    PITCH_LO,
    RANGE_HI,
    RANGE_LO,
)
from shared.constants import (
    CONSONANT_INTERVALS,
    MAJOR_SCALE,
    NATURAL_MINOR_SCALE,
)

# ── Same-sign run automaton ─────────────────────────────────────────
# States: 0=Start, 1..5=Up1..Up5, 6..10=Down1..Down5
# Input: 0=down, 1=up.  6th consecutive same-sign is dead (rejected).
_AUTOMATON_START: int = 0
_AUTOMATON_ACCEPTING: list[int] = list(range(11))
_AUTOMATON_TRANSITIONS: list[tuple[int, int, int]] = [
    (0, 0, 6),  (0, 1, 1),
    (1, 0, 6),  (1, 1, 2),
    (2, 0, 6),  (2, 1, 3),
    (3, 0, 6),  (3, 1, 4),
    (4, 0, 6),  (4, 1, 5),
    (5, 0, 6),
    (6, 0, 7),  (6, 1, 1),
    (7, 0, 8),  (7, 1, 1),
    (8, 0, 9),  (8, 1, 1),
    (9, 0, 10), (9, 1, 1),
    (10, 1, 1),
]

_SCALE_BY_MODE: dict[str, tuple[int, ...]] = {
    "major": MAJOR_SCALE,
    "minor": NATURAL_MINOR_SCALE,
}


def _degree_to_semitone(
    degree: int,
    scale: tuple[int, ...],
) -> int:
    """Convert signed degree offset to semitone offset."""
    octave, step = divmod(degree, 7)
    return octave * 12 + scale[step]


def _build_consonant_pairs(
    scale: tuple[int, ...],
    consonance_set: frozenset[int],
) -> list[tuple[int, int]]:
    """Precompute (start_degree_mod7, degree_span) pairs producing consonant intervals."""
    pairs: list[tuple[int, int]] = []
    for start in range(7):
        s1 = _degree_to_semitone(start, scale)
        for span in range(-14, 15):
            oct2, step2 = divmod(start + span, 7)
            s2 = oct2 * 12 + scale[step2]
            interval_mod12 = abs(s2 - s1) % 12
            if interval_mod12 in consonance_set:
                pairs.append((start, span))
    return pairs


def _build_model(
    num_notes: int,
    stretto_k: int,
    consonant_pairs: list[tuple[int, int]],
) -> tuple[cp_model.CpModel, list, list]:
    """Build CP-SAT model with melodic + stretto constraints."""
    model = cp_model.CpModel()
    n_iv = num_notes - 1
    min_steps = -(-n_iv // 2)  # ceil division
    assert min_steps == (n_iv + 1) // 2
    # ── Variables ────────────────────────────────────────────────
    pitches = [model.new_int_var(PITCH_LO, PITCH_HI, f"p_{i}") for i in range(num_notes)]
    ivs = [model.new_int_var(-5, 5, f"iv_{i}") for i in range(n_iv)]
    model.add(pitches[0] == 0)
    for i in range(n_iv):
        model.add(pitches[i + 1] == pitches[i] + ivs[i])
        model.add(ivs[i] != 0)
    # ── Range ────────────────────────────────────────────────────
    pitch_min = model.new_int_var(PITCH_LO, PITCH_HI, "pmin")
    pitch_max = model.new_int_var(PITCH_LO, PITCH_HI, "pmax")
    model.add_min_equality(pitch_min, pitches)
    model.add_max_equality(pitch_max, pitches)
    span = model.new_int_var(0, PITCH_HI - PITCH_LO, "span")
    model.add(span == pitch_max - pitch_min)
    model.add(span >= RANGE_LO)
    model.add(span <= RANGE_HI)
    # ── Allowed finals ───────────────────────────────────────────
    model.add_allowed_assignments(
        [pitches[-1]],
        [(f,) for f in sorted(ALLOWED_FINALS)],
    )
    # ── Step fraction >= 50% ─────────────────────────────────────
    abs_ivs = []
    is_step = [model.new_bool_var(f"step_{i}") for i in range(n_iv)]
    for i in range(n_iv):
        abs_iv = model.new_int_var(0, 5, f"abs_iv_{i}")
        model.add_abs_equality(abs_iv, ivs[i])
        abs_ivs.append(abs_iv)
        model.add(abs_iv <= 1).only_enforce_if(is_step[i])
        model.add(abs_iv >= 2).only_enforce_if(is_step[i].negated())
    model.add(sum(is_step) >= min_steps)
    # ── Large leaps <= MAX_LARGE_LEAPS ───────────────────────────
    is_large = [model.new_bool_var(f"large_{i}") for i in range(n_iv)]
    for i in range(n_iv):
        model.add(abs_ivs[i] >= 3).only_enforce_if(is_large[i])
        model.add(abs_ivs[i] <= 2).only_enforce_if(is_large[i].negated())
    model.add(sum(is_large) <= MAX_LARGE_LEAPS)
    # ── Same-sign run automaton ──────────────────────────────────
    signs = [model.new_int_var(0, 1, f"sign_{i}") for i in range(n_iv)]
    for i in range(n_iv):
        model.add(ivs[i] >= 1).only_enforce_if(signs[i])
        model.add(ivs[i] <= -1).only_enforce_if(signs[i].negated())
    model.add_automaton(
        signs, _AUTOMATON_START, _AUTOMATON_ACCEPTING, _AUTOMATON_TRANSITIONS,
    )
    # ── Pitch frequency <= MAX_PITCH_FREQ ────────────────────────
    for d in range(PITCH_LO, PITCH_HI + 1):
        hits = [model.new_bool_var(f"freq_{d}_{i}") for i in range(num_notes)]
        for i in range(num_notes):
            model.add(pitches[i] == d).only_enforce_if(hits[i])
            model.add(pitches[i] != d).only_enforce_if(hits[i].negated())
        model.add(sum(hits) <= MAX_PITCH_FREQ)
    # ── Stretto consonance at primary offset ─────────────────────
    for i in range(num_notes - stretto_k):
        start_mod7 = model.new_int_var(0, 6, f"sm7_{i}")
        model.add_modulo_equality(start_mod7, pitches[i], 7)
        degree_span = model.new_int_var(-14, 14, f"dspan_{i}")
        model.add(degree_span == pitches[i + stretto_k] - pitches[i])
        model.add_allowed_assignments([start_mod7, degree_span], consonant_pairs)
    return model, pitches, ivs


def generate_cpsat_degrees(
    num_notes: int,
    mode: str = "major",
    stretto_k: int | None = None,
    seed: int = 42,
) -> list[tuple[int, ...]]:
    """Generate stretto-compatible degree sequences via CP-SAT sampling."""
    assert num_notes >= 3, f"Need at least 3 notes, got {num_notes}"
    assert mode in _SCALE_BY_MODE, f"Unknown mode: {mode}"
    if stretto_k is None:
        stretto_k = num_notes // 2
    assert 1 <= stretto_k < num_notes
    scale = _SCALE_BY_MODE[mode]
    consonant_pairs = _build_consonant_pairs(
        scale=scale,
        consonance_set=CONSONANT_INTERVALS,
    )
    rng = random.Random(seed)
    all_solutions: set[tuple[int, ...]] = set()
    for restart in range(CPSAT_NUM_RESTARTS):
        # ── Phase A: random-objective anchor ─────────────────────
        model_a, pitches_a, _ = _build_model(num_notes, stretto_k, consonant_pairs)
        weights = [rng.randint(-10, 10) for _ in range(num_notes)]
        model_a.maximize(sum(w * p for w, p in zip(weights, pitches_a)))
        solver_a = cp_model.CpSolver()
        solver_a.parameters.max_time_in_seconds = 1.0
        solver_a.parameters.random_seed = restart
        status_a = solver_a.solve(model_a)
        if status_a not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            continue
        anchor = tuple(solver_a.value(pitches_a[i]) for i in range(num_notes))
        all_solutions.add(anchor)
        # ── Phase B: enumerate from anchor neighbourhood ─────────
        model_b, pitches_b, _ = _build_model(num_notes, stretto_k, consonant_pairs)
        for i in range(num_notes):
            model_b.add_hint(pitches_b[i], anchor[i])
        solver_b = cp_model.CpSolver()
        solver_b.parameters.max_time_in_seconds = CPSAT_SOLVER_TIMEOUT
        solver_b.parameters.random_seed = restart
        solver_b.parameters.enumerate_all_solutions = True
        # Collector must close over pitches_b and num_notes
        collected: list[tuple[int, ...]] = []
        limit = CPSAT_SOLUTIONS_PER_RESTART
        class _Collector(cp_model.CpSolverSolutionCallback):
            """Gather solutions up to limit."""
            def on_solution_callback(self):
                degs = tuple(self.value(pitches_b[i]) for i in range(num_notes))
                collected.append(degs)
                if len(collected) >= limit:
                    self.stop_search()
        solver_b.solve(model_b, _Collector())
        all_solutions.update(collected)
    return sorted(all_solutions)
