"""Countersubject generator using CP-SAT optimisation.

Generates a countersubject that:
1. Forms invertible counterpoint at the octave with the subject
2. Has melodic independence (contrary motion, distinct contour)
3. Respects voice-leading conventions (stepwise preference, leap recovery)

Works entirely in scale degrees mod 7 for mode-independence.
"""
from dataclasses import dataclass
from fractions import Fraction
from typing import Tuple

from ortools.sat.python import cp_model

from motifs.head_generator import degrees_to_midi
from motifs.subject_generator import GeneratedSubject
from shared.constants import TONIC_TRIAD_DEGREES


MIN_CS_DEGREE = -7
MAX_CS_DEGREE = 14
INVERTIBLE_CONSONANCES = frozenset({0, 2, 5})
WEAK_BEAT_ALLOWED = frozenset({0, 1, 2, 4, 5, 6})
TRITONE_INTERVAL = 3
PENALTY_WEAK_BEAT_FIFTH = 20
PENALTY_WEAK_BEAT_DISSONANCE = 10
PENALTY_LARGE_LEAP = 30
PENALTY_REPEATED_PITCH = 25
PENALTY_INTERIOR_UNISON = 15
PENALTY_PARALLEL_MOTION = 10
REWARD_CONTRARY_MOTION = 15
REWARD_STEPWISE = 5
REWARD_STABLE_BOUNDARY = 10
LARGE_LEAP_THRESHOLD = 4
SOLVER_TIMEOUT_SECONDS = 5


@dataclass(frozen=True)
class GeneratedCountersubject:
    """Result of countersubject generation."""
    scale_indices: Tuple[int, ...]
    durations: Tuple[float, ...]
    midi_pitches: Tuple[int, ...]
    vertical_intervals: Tuple[int, ...]


def _compute_beat_positions(
    durations: tuple[float, ...],
    metre: tuple[int, int],
) -> list[int]:
    """Compute beat number (1-indexed) for each note onset."""
    beats_per_bar = metre[0]
    beat_duration = Fraction(1, metre[1])
    positions = []
    cumulative = Fraction(0)
    for dur in durations:
        beat_in_bar = int(cumulative / beat_duration) % beats_per_bar + 1
        positions.append(beat_in_bar)
        cumulative += Fraction(dur).limit_denominator(64)
    return positions


def _get_strong_beats(metre: tuple[int, int]) -> frozenset[int]:
    """Return strong beat numbers for the given metre."""
    if metre[0] == 4:
        return frozenset({1, 3})
    if metre[0] == 3:
        return frozenset({1})
    if metre[0] == 2:
        return frozenset({1})
    if metre[0] == 6:
        return frozenset({1, 4})
    return frozenset({1})


def _interval_mod7(diff: int) -> int:
    """Compute vertical interval class from degree difference."""
    return abs(diff) % 7


def generate_countersubject(
    subject: GeneratedSubject,
    metre: tuple[int, int] = (4, 4),
    tonic_midi: int = 60,
    min_degree: int = MIN_CS_DEGREE,
    max_degree: int = MAX_CS_DEGREE,
    answer_degrees: tuple[int, ...] | None = None,
) -> GeneratedCountersubject | None:
    """Generate countersubject using CP-SAT optimisation.

    When answer_degrees is provided, the solver also constrains the CS
    to be consonant against the answer (dual validation for invertible
    counterpoint). This narrows the solution space but never widens it.
    """
    n = len(subject.scale_indices)
    assert n >= 2, f"Subject too short: {n} notes"
    if answer_degrees is not None:
        assert len(answer_degrees) == n, (
            f"answer_degrees length {len(answer_degrees)} != subject length {n}"
        )
    subj_degrees = subject.scale_indices
    beat_positions = _compute_beat_positions(
        durations=subject.durations,
        metre=metre,
    )
    strong_beats = _get_strong_beats(metre=metre)
    model = cp_model.CpModel()
    cs = [model.NewIntVar(min_degree, max_degree, f"cs_{i}") for i in range(n)]
    interval_mod7 = []
    for i in range(n):
        imod = model.NewIntVar(0, 6, f"imod_{i}")
        diff = model.NewIntVar(-28, 28, f"diff_{i}")
        model.Add(diff == cs[i] - subj_degrees[i])
        abs_diff = model.NewIntVar(0, 28, f"abs_{i}")
        model.AddAbsEquality(abs_diff, diff)
        model.AddModuloEquality(imod, abs_diff, 7)
        interval_mod7.append(imod)
    for i in range(n):
        is_strong = beat_positions[i] in strong_beats
        if is_strong:
            model.AddAllowedAssignments([interval_mod7[i]], [(0,), (2,), (5,)])
        else:
            model.AddAllowedAssignments([interval_mod7[i]], [(0,), (1,), (2,), (4,), (5,), (6,)])
    # --- Answer interval variables and constraints (dual validation) ---
    answer_imod7: list[cp_model.IntVar] = []
    if answer_degrees is not None:
        for i in range(n):
            aimod = model.NewIntVar(0, 6, f"aimod_{i}")
            adiff = model.NewIntVar(-28, 28, f"adiff_{i}")
            model.Add(adiff == cs[i] - answer_degrees[i])
            aabs = model.NewIntVar(0, 28, f"aabs_{i}")
            model.AddAbsEquality(aabs, adiff)
            model.AddModuloEquality(aimod, aabs, 7)
            answer_imod7.append(aimod)
        for i in range(n):
            is_strong = beat_positions[i] in strong_beats
            if is_strong:
                model.AddAllowedAssignments([answer_imod7[i]], [(0,), (2,), (5,)])
            else:
                model.AddAllowedAssignments([answer_imod7[i]], [(0,), (1,), (2,), (4,), (5,), (6,)])
    penalties = []
    rewards = []
    for i in range(n):
        is_strong = beat_positions[i] in strong_beats
        if not is_strong:
            is_fifth = model.NewBoolVar(f"fifth_{i}")
            model.Add(interval_mod7[i] == 4).OnlyEnforceIf(is_fifth)
            model.Add(interval_mod7[i] != 4).OnlyEnforceIf(is_fifth.Not())
            penalties.append((is_fifth, PENALTY_WEAK_BEAT_FIFTH))
            is_dissonant = model.NewBoolVar(f"diss_{i}")
            model.Add(interval_mod7[i] == 1).OnlyEnforceIf(is_dissonant)
            model.Add(interval_mod7[i] != 1).OnlyEnforceIf(is_dissonant.Not())
            is_dissonant6 = model.NewBoolVar(f"diss6_{i}")
            model.Add(interval_mod7[i] == 6).OnlyEnforceIf(is_dissonant6)
            model.Add(interval_mod7[i] != 6).OnlyEnforceIf(is_dissonant6.Not())
            penalties.append((is_dissonant, PENALTY_WEAK_BEAT_DISSONANCE))
            penalties.append((is_dissonant6, PENALTY_WEAK_BEAT_DISSONANCE))
        if 0 < i < n - 1:
            is_unison = model.NewBoolVar(f"uni_{i}")
            model.Add(interval_mod7[i] == 0).OnlyEnforceIf(is_unison)
            model.Add(interval_mod7[i] != 0).OnlyEnforceIf(is_unison.Not())
            penalties.append((is_unison, PENALTY_INTERIOR_UNISON))
    # --- Answer weak-beat penalties (parallel to subject penalties) ---
    if answer_degrees is not None:
        for i in range(n):
            is_strong = beat_positions[i] in strong_beats
            if not is_strong:
                a_fifth = model.NewBoolVar(f"afifth_{i}")
                model.Add(answer_imod7[i] == 4).OnlyEnforceIf(a_fifth)
                model.Add(answer_imod7[i] != 4).OnlyEnforceIf(a_fifth.Not())
                penalties.append((a_fifth, PENALTY_WEAK_BEAT_FIFTH))
                a_diss = model.NewBoolVar(f"adiss_{i}")
                model.Add(answer_imod7[i] == 1).OnlyEnforceIf(a_diss)
                model.Add(answer_imod7[i] != 1).OnlyEnforceIf(a_diss.Not())
                a_diss6 = model.NewBoolVar(f"adiss6_{i}")
                model.Add(answer_imod7[i] == 6).OnlyEnforceIf(a_diss6)
                model.Add(answer_imod7[i] != 6).OnlyEnforceIf(a_diss6.Not())
                penalties.append((a_diss, PENALTY_WEAK_BEAT_DISSONANCE))
                penalties.append((a_diss6, PENALTY_WEAK_BEAT_DISSONANCE))
    for i in range(n - 1):
        uni_i = model.NewBoolVar(f"u_{i}")
        uni_j = model.NewBoolVar(f"u_{i + 1}")
        model.Add(interval_mod7[i] == 0).OnlyEnforceIf(uni_i)
        model.Add(interval_mod7[i] != 0).OnlyEnforceIf(uni_i.Not())
        model.Add(interval_mod7[i + 1] == 0).OnlyEnforceIf(uni_j)
        model.Add(interval_mod7[i + 1] != 0).OnlyEnforceIf(uni_j.Not())
        model.AddBoolOr([uni_i.Not(), uni_j.Not()])
    for i in range(n - 1):
        cs_mot = model.NewIntVar(-28, 28, f"csmot_{i}")
        model.Add(cs_mot == cs[i + 1] - cs[i])
        subj_mot = subj_degrees[i + 1] - subj_degrees[i]
        if subj_mot != 0:
            same_dir = model.NewBoolVar(f"same_{i}")
            if subj_mot > 0:
                model.Add(cs_mot > 0).OnlyEnforceIf(same_dir)
                model.Add(cs_mot <= 0).OnlyEnforceIf(same_dir.Not())
            else:
                model.Add(cs_mot < 0).OnlyEnforceIf(same_dir)
                model.Add(cs_mot >= 0).OnlyEnforceIf(same_dir.Not())
            tgt_uni = model.NewBoolVar(f"tgtu_{i}")
            model.Add(interval_mod7[i + 1] == 0).OnlyEnforceIf(tgt_uni)
            model.Add(interval_mod7[i + 1] != 0).OnlyEnforceIf(tgt_uni.Not())
            model.AddBoolOr([same_dir.Not(), tgt_uni.Not()])
            contrary = model.NewBoolVar(f"ctr_{i}")
            if subj_mot > 0:
                model.Add(cs_mot < 0).OnlyEnforceIf(contrary)
                model.Add(cs_mot >= 0).OnlyEnforceIf(contrary.Not())
            else:
                model.Add(cs_mot > 0).OnlyEnforceIf(contrary)
                model.Add(cs_mot <= 0).OnlyEnforceIf(contrary.Not())
            rewards.append((contrary, REWARD_CONTRARY_MOTION))
            penalties.append((same_dir, PENALTY_PARALLEL_MOTION))
        abs_mot = model.NewIntVar(0, 28, f"absmot_{i}")
        model.AddAbsEquality(abs_mot, cs_mot)
        big_leap = model.NewBoolVar(f"leap_{i}")
        model.Add(abs_mot > LARGE_LEAP_THRESHOLD).OnlyEnforceIf(big_leap)
        model.Add(abs_mot <= LARGE_LEAP_THRESHOLD).OnlyEnforceIf(big_leap.Not())
        penalties.append((big_leap, PENALTY_LARGE_LEAP))
        stepwise = model.NewBoolVar(f"step_{i}")
        model.Add(abs_mot <= 2).OnlyEnforceIf(stepwise)
        model.Add(abs_mot > 2).OnlyEnforceIf(stepwise.Not())
        rewards.append((stepwise, REWARD_STEPWISE))
        repeated = model.NewBoolVar(f"rep_{i}")
        model.Add(cs_mot == 0).OnlyEnforceIf(repeated)
        model.Add(cs_mot != 0).OnlyEnforceIf(repeated.Not())
        penalties.append((repeated, PENALTY_REPEATED_PITCH))
    stable_degrees = [(d % 7) for d in TONIC_TRIAD_DEGREES]
    for idx in [0, n - 1]:
        cs_pos = model.NewIntVar(0, max_degree + 7, f"cspos_{idx}")
        model.Add(cs_pos == cs[idx] + 7)
        cs_m7 = model.NewIntVar(0, 6, f"csm7_{idx}")
        model.AddModuloEquality(cs_m7, cs_pos, 7)
        stable = model.NewBoolVar(f"stab_{idx}")
        model.AddAllowedAssignments([cs_m7], [(d,) for d in stable_degrees]).OnlyEnforceIf(stable)
        model.AddForbiddenAssignments([cs_m7], [(d,) for d in stable_degrees]).OnlyEnforceIf(stable.Not())
        rewards.append((stable, REWARD_STABLE_BOUNDARY))
    total_penalty = sum(var * weight for var, weight in penalties)
    total_reward = sum(var * weight for var, weight in rewards)
    model.Maximize(total_reward - total_penalty)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = SOLVER_TIMEOUT_SECONDS
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    cs_degrees = tuple(solver.Value(cs[i]) for i in range(n))
    intervals = tuple(solver.Value(interval_mod7[i]) for i in range(n))
    midi_pitches = degrees_to_midi(
        degrees=cs_degrees,
        tonic_midi=tonic_midi,
        mode=subject.mode,
    )
    return GeneratedCountersubject(
        scale_indices=cs_degrees,
        durations=subject.durations,
        midi_pitches=midi_pitches,
        vertical_intervals=intervals,
    )


def verify_countersubject(
    subject: GeneratedSubject,
    cs: GeneratedCountersubject,
    metre: tuple[int, int],
) -> list[str]:
    """Verify countersubject satisfies all constraints."""
    violations = []
    beat_positions = _compute_beat_positions(
        durations=subject.durations,
        metre=metre,
    )
    strong_beats = _get_strong_beats(metre=metre)
    for i, interval in enumerate(cs.vertical_intervals):
        is_strong = beat_positions[i] in strong_beats
        if is_strong and interval not in INVERTIBLE_CONSONANCES:
            violations.append(f"Note {i}: strong-beat interval {interval} not invertible")
        if interval == TRITONE_INTERVAL:
            violations.append(f"Note {i}: tritone interval")
    for i in range(len(cs.vertical_intervals) - 1):
        if cs.vertical_intervals[i] == 0 and cs.vertical_intervals[i + 1] == 0:
            violations.append(f"Notes {i}-{i+1}: consecutive unisons")
    return violations


if __name__ == "__main__":
    from motifs.subject_generator import generate_subject
    from motifs.answer_generator import generate_answer
    print("Testing countersubject generation (dual validation)...")
    print("=" * 60)
    success_count = 0
    for seed in range(5):
        print(f"Seed {seed}...", end=" ", flush=True)
        subject = generate_subject(
            mode="minor",
            metre=(4, 4),
            seed=seed,
            tonic_midi=67,
            verbose=False,
        )
        answer = generate_answer(
            subject=subject,
            tonic_midi=67,
        )
        cs = generate_countersubject(
            subject=subject,
            metre=(4, 4),
            tonic_midi=67,
            answer_degrees=answer.scale_indices,
        )
        if cs:
            violations = verify_countersubject(
                subject=subject,
                cs=cs,
                metre=(4, 4),
            )
            if violations:
                print(f"VIOLATIONS")
                for v in violations:
                    print(f"  {v}")
            else:
                print("OK")
                success_count += 1
                print(f"  Subject:  {subject.scale_indices}")
                print(f"  Answer:   {answer.scale_indices} ({answer.answer_type})")
                print(f"  CS:       {cs.scale_indices}")
                print(f"  Intervals (vs subj): {cs.vertical_intervals}")
        else:
            print("FAILED (no solution)")
    print(f"\n{success_count}/5 subjects produced valid countersubjects (dual validation)")
