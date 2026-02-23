"""CP-SAT prototype: stretto-first subject enumeration.

Two-phase sampling: random-objective anchor + feasibility enumeration per restart.
"""
import random
import time
from ortools.sat.python import cp_model

# ── Scale data ───────────────────────────────────────────────────────
MAJOR_SEMITONES = (0, 2, 4, 5, 7, 9, 11)

CONSONANT_MOD12 = frozenset({0, 3, 4, 5, 7, 8, 9})

# ── Sampling constants ───────────────────────────────────────────────
NUM_RESTARTS = 40
SOLUTIONS_PER_RESTART = 50
SOLVER_TIMEOUT_SECONDS = 3.0

# ── Same-sign automaton ─────────────────────────────────────────────
_AUTOMATON_START = 0
_AUTOMATON_ACCEPTING = list(range(11))
_AUTOMATON_TRANSITIONS = [
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


def degree_to_semitone(
    degree: int,
    mode_semitones: tuple[int, ...] = MAJOR_SEMITONES,
) -> int:
    """Convert signed degree offset to semitone offset."""
    octave, step = divmod(degree, 7)
    return octave * 12 + mode_semitones[step]


def build_consonant_spans(
    mode_semitones: tuple[int, ...],
) -> set[tuple[int, int]]:
    """Return (start_degree_mod7, degree_span) pairs producing consonant intervals."""
    valid = set()
    for start in range(7):
        for span in range(-14, 15):
            s1 = degree_to_semitone(start, mode_semitones)
            oct2, step2 = divmod(start + span, 7)
            s2 = oct2 * 12 + mode_semitones[step2]
            interval_mod12 = abs(s2 - s1) % 12
            if interval_mod12 in CONSONANT_MOD12:
                valid.add((start, span))
    return valid


def _build_model(
    num_notes: int,
    stretto_k: int,
    allowed_pairs: list[tuple[int, int]],
) -> tuple[cp_model.CpModel, list, list]:
    """Build fresh CP-SAT model. Returns (model, pitches, ivs)."""
    model = cp_model.CpModel()
    n_iv = num_notes - 1
    pitches = [model.new_int_var(-7, 7, f"p_{i}") for i in range(num_notes)]
    ivs = [model.new_int_var(-5, 5, f"iv_{i}") for i in range(n_iv)]
    model.add(pitches[0] == 0)
    for i in range(n_iv):
        model.add(pitches[i + 1] == pitches[i] + ivs[i])
        model.add(ivs[i] != 0)
    # Range
    pitch_min = model.new_int_var(-7, 7, "pmin")
    pitch_max = model.new_int_var(-7, 7, "pmax")
    model.add_min_equality(pitch_min, pitches)
    model.add_max_equality(pitch_max, pitches)
    span = model.new_int_var(0, 14, "span")
    model.add(span == pitch_max - pitch_min)
    model.add(span >= 4)
    model.add(span <= 11)
    # Finals
    model.add_allowed_assignments([pitches[-1]], [(0,), (2,), (4,)])
    # Step fraction
    abs_ivs = []
    is_step = [model.new_bool_var(f"step_{i}") for i in range(n_iv)]
    for i in range(n_iv):
        abs_iv = model.new_int_var(0, 5, f"abs_iv_{i}")
        model.add_abs_equality(abs_iv, ivs[i])
        abs_ivs.append(abs_iv)
        model.add(abs_iv <= 1).only_enforce_if(is_step[i])
        model.add(abs_iv >= 2).only_enforce_if(is_step[i].negated())
    model.add(sum(is_step) >= (n_iv + 1) // 2)
    # Large leaps
    is_large = [model.new_bool_var(f"large_{i}") for i in range(n_iv)]
    for i in range(n_iv):
        model.add(abs_ivs[i] >= 3).only_enforce_if(is_large[i])
        model.add(abs_ivs[i] <= 2).only_enforce_if(is_large[i].negated())
    model.add(sum(is_large) <= 4)
    # Same-sign automaton
    signs = [model.new_int_var(0, 1, f"sign_{i}") for i in range(n_iv)]
    for i in range(n_iv):
        model.add(ivs[i] >= 1).only_enforce_if(signs[i])
        model.add(ivs[i] <= -1).only_enforce_if(signs[i].negated())
    model.add_automaton(
        signs, _AUTOMATON_START, _AUTOMATON_ACCEPTING, _AUTOMATON_TRANSITIONS,
    )
    # Pitch frequency
    for d in range(-7, 8):
        hits = [model.new_bool_var(f"freq_{d}_{i}") for i in range(num_notes)]
        for i in range(num_notes):
            model.add(pitches[i] == d).only_enforce_if(hits[i])
            model.add(pitches[i] != d).only_enforce_if(hits[i].negated())
        model.add(sum(hits) <= 3)
    # Stretto consonance
    for i in range(num_notes - stretto_k):
        start_mod7 = model.new_int_var(0, 6, f"sm7_{i}")
        model.add_modulo_equality(start_mod7, pitches[i], 7)
        degree_span = model.new_int_var(-14, 14, f"dspan_{i}")
        model.add(degree_span == pitches[i + stretto_k] - pitches[i])
        model.add_allowed_assignments([start_mod7, degree_span], allowed_pairs)
    return model, pitches, ivs


def solve(
    num_notes: int = 9,
    stretto_k: int = 4,
):
    """Sample stretto-compatible subjects: anchor + enumerate per restart."""
    t0 = time.time()
    consonant_spans = build_consonant_spans(MAJOR_SEMITONES)
    allowed_pairs = [(s, d) for s, d in consonant_spans if -14 <= d <= 14]
    rng = random.Random(42)
    all_solutions: set[tuple[int, ...]] = set()
    for seed in range(NUM_RESTARTS):
        # ── Phase A: find one diverse anchor via random objective ──
        model_a, pitches_a, _ = _build_model(num_notes, stretto_k, allowed_pairs)
        weights = [rng.randint(-10, 10) for _ in range(num_notes)]
        model_a.maximize(sum(w * p for w, p in zip(weights, pitches_a)))
        solver_a = cp_model.CpSolver()
        solver_a.parameters.max_time_in_seconds = 1.0
        solver_a.parameters.random_seed = seed
        status_a = solver_a.solve(model_a)
        if status_a not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            continue
        anchor = tuple(solver_a.value(pitches_a[i]) for i in range(num_notes))
        all_solutions.add(anchor)
        # ── Phase B: enumerate from anchor neighbourhood ──────────
        model_b, pitches_b, _ = _build_model(num_notes, stretto_k, allowed_pairs)
        # Hint the solver toward the anchor region
        for i in range(num_notes):
            model_b.add_hint(pitches_b[i], anchor[i])
        solver_b = cp_model.CpSolver()
        solver_b.parameters.max_time_in_seconds = SOLVER_TIMEOUT_SECONDS
        solver_b.parameters.random_seed = seed
        solver_b.parameters.enumerate_all_solutions = True

        class Collector(cp_model.CpSolverSolutionCallback):
            def __init__(self, limit: int):
                super().__init__()
                self.batch: list[tuple[int, ...]] = []
                self._limit = limit
            def on_solution_callback(self):
                degs = tuple(self.value(pitches_b[i]) for i in range(num_notes))
                self.batch.append(degs)
                if len(self.batch) >= self._limit:
                    self.stop_search()

        cb = Collector(limit=SOLUTIONS_PER_RESTART)
        solver_b.solve(model_b, cb)
        all_solutions.update(cb.batch)
    elapsed = time.time() - t0
    print(f"Notes {num_notes}  k={stretto_k}  "
          f"Distinct: {len(all_solutions):,}  Time: {elapsed:.2f}s")
    # Show diverse sample: first, middle, last from sorted list
    sorted_sols = sorted(all_solutions)
    n_show = min(10, len(sorted_sols))
    step = max(1, len(sorted_sols) // n_show)
    for i in range(n_show):
        idx = min(i * step, len(sorted_sols) - 1)
        print(f"  [{idx:>4}] {sorted_sols[idx]}")


if __name__ == "__main__":
    for n in range(5, 13):
        k = n // 2
        solve(num_notes=n, stretto_k=k)
        print()
