"""CP-SAT tail generation with fixed head prefix.

For each enumerated head, enumerates degree sequences where stretto
consonance and melodic constraints are built in.
"""
import math

from ortools.sat.python import cp_model

from motifs.subject_gen.constants import (
    ALLOWED_FINALS,
    CPSAT_SOLUTIONS_PER_HEAD,
    CPSAT_TAIL_TIMEOUT,
    MAX_LARGE_LEAPS,
    MAX_PITCH_FREQ,
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
    head: tuple[int, ...],
) -> tuple[cp_model.CpModel, list, list]:
    """Build CP-SAT model with head prefix fixed."""
    assert len(head) >= 1
    assert head[0] == 0
    model = cp_model.CpModel()
    n_iv = num_notes - 1
    min_steps = math.ceil(n_iv * MIN_STEP_FRACTION)
    # ── Variables ────────────────────────────────────────────────
    pitches = [model.new_int_var(PITCH_LO, PITCH_HI, f"p_{i}") for i in range(num_notes)]
    ivs = [model.new_int_var(-5, 5, f"iv_{i}") for i in range(n_iv)]
    # ── Fix head pitches ─────────────────────────────────────────
    for i, deg in enumerate(head):
        model.add(pitches[i] == deg)
    # ── Interval definitions ─────────────────────────────────────
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


def _degree_to_semitone(
    degree: int,
    scale: tuple[int, ...],
) -> int:
    """Convert signed degree offset to semitone offset."""
    octave, step = divmod(degree, 7)
    return octave * 12 + scale[step]


def build_consonant_pairs(mode: str) -> list[tuple[int, int]]:
    """Build consonant (start_mod7, degree_span) pairs for a mode."""
    assert mode in _SCALE_BY_MODE, f"Unknown mode: {mode}"
    scale = _SCALE_BY_MODE[mode]
    return _build_consonant_pairs(scale, CONSONANT_INTERVALS)


def generate_tails_for_head(
    head: tuple[int, ...],
    num_notes: int,
    stretto_k: int,
    consonant_pairs: list[tuple[int, int]],
    max_solutions: int = CPSAT_SOLUTIONS_PER_HEAD,
    timeout: float = CPSAT_TAIL_TIMEOUT,
) -> list[tuple[int, ...]]:
    """Enumerate valid completions for a given head prefix."""
    assert len(head) < num_notes
    model, pitches, _ = _build_model(num_notes, stretto_k, consonant_pairs, head)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout
    solver.parameters.enumerate_all_solutions = True
    collected: set[tuple[int, ...]] = set()
    limit: int = max_solutions
    class _Collector(cp_model.CpSolverSolutionCallback):
        """Gather solutions up to limit."""
        def on_solution_callback(self):
            degs = tuple(self.value(pitches[i]) for i in range(num_notes))
            collected.add(degs)
            if len(collected) >= limit:
                self.stop_search()
    solver.solve(model, _Collector())
    return sorted(collected)
