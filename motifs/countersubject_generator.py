"""Countersubject generator using CP-SAT optimisation.

Generates a countersubject that:
1. Forms invertible counterpoint at the octave with the subject
2. Has melodic independence (contrary motion, distinct contour)
3. Respects voice-leading conventions (stepwise preference, leap recovery)

Works entirely in scale degrees mod 7 for mode-independence.
"""
from dataclasses import dataclass
from fractions import Fraction

from ortools.sat.python import cp_model

from motifs.head_generator import degrees_to_midi
from motifs.subject_gen import GeneratedSubject
from shared.constants import TONIC_TRIAD_DEGREES
from shared.music_math import VALID_DURATIONS, VALID_DURATIONS_SORTED

CS_MIN_DURATION: Fraction = Fraction(1, 8)
# Fallback range if subject analysis fails
FALLBACK_MIN_CS_DEGREE = -7
FALLBACK_MAX_CS_DEGREE = 14
# CS sits below the subject: min separation (a 3rd) to max (2 octaves)
CS_MIN_BELOW_SUBJECT = 2   # At least a 3rd below subject's lowest note
CS_MAX_BELOW_SUBJECT = 14  # At most 2 octaves below subject's highest note
CS_MAX_OVERLAP = 3         # CS may overlap up to a 4th into subject range
INVERTIBLE_CONSONANCES = frozenset({0, 2, 5})
WEAK_BEAT_ALLOWED = frozenset({0, 1, 2, 4, 5, 6})
TRITONE_INTERVAL = 3
PENALTY_WEAK_BEAT_FIFTH = 20
PENALTY_WEAK_BEAT_DISSONANCE = 10
PENALTY_DISSONANCE_NOT_PASSING = 200
PENALTY_LARGE_LEAP = 30
PENALTY_REPEATED_PITCH = 25
PENALTY_INTERIOR_UNISON = 15
PENALTY_PARALLEL_MOTION = 10
PENALTY_ZIGZAG = 12          # Alternating direction on consecutive intervals
REWARD_CONTRARY_MOTION = 15
REWARD_STEPWISE = 5
REWARD_STABLE_BOUNDARY = 10
REWARD_DIRECTIONAL_RUN = 10  # 3+ notes moving same direction
REWARD_RANGE_USAGE = 15      # Using a reasonable span of available range
LARGE_LEAP_THRESHOLD = 4
MIN_GOOD_RANGE = 4           # A 5th — minimum span for melodic interest
SOLVER_TIMEOUT_SECONDS = 5

@dataclass(frozen=True)
class GeneratedCountersubject:
    """Result of countersubject generation."""
    scale_indices: tuple[int, ...]
    durations: tuple[float, ...]
    midi_pitches: tuple[int, ...]
    vertical_intervals: tuple[int, ...]

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

def _generate_cs_rhythm(
    subject_durations: tuple[float, ...],
    metre: tuple[int, int],
) -> tuple[tuple[Fraction, ...], tuple[int, ...]]:
    """Generate CS rhythm that contrasts with the subject.

    Strategy: where the subject has short notes (eighths or less),
    the CS holds longer notes; where the subject has long notes
    (quarters or more), the CS subdivides. Total duration matches.

    Returns:
        cs_durations: CS note durations
        onset_indices: Subject-note index at the start of each CS note
    """
    subj_fracs = tuple(Fraction(d).limit_denominator(64) for d in subject_durations)
    total = sum(subj_fracs)
    quarter = Fraction(1, 4)
    eighth = Fraction(1, 8)
    max_merge = quarter  # Cap: don't merge short notes beyond a crotchet
    # Phase 1: merge runs of short subject notes into longer CS notes
    cs_durations: list[Fraction] = []
    onset_indices: list[int] = []
    i = 0
    while i < len(subj_fracs):
        if subj_fracs[i] <= eighth:
            # Merge consecutive short notes, capped at max_merge
            onset_indices.append(i)
            merged = Fraction(0)
            while i < len(subj_fracs) and subj_fracs[i] <= eighth:
                merged += subj_fracs[i]
                i += 1
            # Emit chunks of at most max_merge
            placed = Fraction(0)
            first = True
            while placed < merged:
                chunk = min(merged - placed, max_merge)
                found = False
                for vd in VALID_DURATIONS_SORTED:
                    if vd <= chunk:
                        cs_durations.append(vd)
                        if not first:
                            onset_indices.append(onset_indices[-1])
                        placed += vd
                        found = True
                        first = False
                        break
                assert found, f"Cannot fill remainder {merged - placed}"
        elif subj_fracs[i] >= quarter:
            # Split long subject notes into shorter CS notes
            onset_indices.append(i)
            dur = subj_fracs[i]
            placed = Fraction(0)
            first = True
            while placed < dur:
                remainder = dur - placed
                # Prefer eighth notes for subdivision
                if remainder >= eighth and eighth in VALID_DURATIONS:
                    cs_durations.append(eighth)
                    if not first:
                        onset_indices.append(i)
                    placed += eighth
                else:
                    for vd in VALID_DURATIONS_SORTED:
                        if vd <= remainder:
                            cs_durations.append(vd)
                            if not first:
                                onset_indices.append(i)
                            placed += vd
                            break
                first = False
            i += 1
        else:
            # Medium durations pass through
            onset_indices.append(i)
            cs_durations.append(subj_fracs[i])
            i += 1
    assert sum(cs_durations) == total, (
        f"CS duration {sum(cs_durations)} != subject duration {total}"
    )
    return tuple(cs_durations), tuple(onset_indices)

def _derive_cs_range(
    subject_degrees: tuple[int, ...],
) -> tuple[int, int]:
    """Derive CS pitch range from subject register.

    The CS should sit below the subject like a continuo line:
    - Upper bound: subject's lowest note + small overlap
    - Lower bound: subject's highest note minus 2 octaves
    """
    subj_lo = min(subject_degrees)
    subj_hi = max(subject_degrees)
    cs_max = subj_lo + CS_MAX_OVERLAP
    cs_min = subj_hi - CS_MAX_BELOW_SUBJECT
    # Ensure at least an octave of range for the solver
    if cs_max - cs_min < 7:
        cs_min = cs_max - 7
    return cs_min, cs_max

def generate_countersubject(
    subject: GeneratedSubject,
    metre: tuple[int, int] = (4, 4),
    tonic_midi: int = 60,
    answer_degrees: tuple[int, ...] | None = None,
) -> GeneratedCountersubject | None:
    """Generate countersubject using CP-SAT optimisation.

    CS range is derived from the subject's register — the CS sits
    below the subject like a continuo line.

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
    min_degree, max_degree = _derive_cs_range(subject_degrees=subject.scale_indices)

    # Generate contrasting CS rhythm
    cs_durations, onset_indices = _generate_cs_rhythm(subject.durations, metre)
    m = len(cs_durations)
    assert m >= 2, f"CS too short after aggregation: {m} notes"

    subj_degrees = subject.scale_indices
    beat_positions = _compute_beat_positions(
        durations=tuple(float(d) for d in cs_durations),
        metre=metre,
    )
    strong_beats = _get_strong_beats(metre=metre)
    model = cp_model.CpModel()
    cs = [model.NewIntVar(min_degree, max_degree, f"cs_{i}") for i in range(m)]
    interval_mod7 = []
    for i in range(m):
        imod = model.NewIntVar(0, 6, f"imod_{i}")
        diff = model.NewIntVar(-28, 28, f"diff_{i}")
        subj_idx = onset_indices[i]
        model.Add(diff == cs[i] - subj_degrees[subj_idx])
        abs_diff = model.NewIntVar(0, 28, f"abs_{i}")
        model.AddAbsEquality(abs_diff, diff)
        model.AddModuloEquality(imod, abs_diff, 7)
        interval_mod7.append(imod)
    for i in range(m):
        is_strong = beat_positions[i] in strong_beats
        if is_strong:
            model.AddAllowedAssignments([interval_mod7[i]], [(0,), (2,), (5,)])
        else:
            model.AddAllowedAssignments([interval_mod7[i]], [(0,), (1,), (2,), (4,), (5,), (6,)])
    # --- Answer interval variables and constraints (dual validation) ---
    answer_imod7: list[cp_model.IntVar] = []
    if answer_degrees is not None:
        for i in range(m):
            aimod = model.NewIntVar(0, 6, f"aimod_{i}")
            adiff = model.NewIntVar(-28, 28, f"adiff_{i}")
            subj_idx = onset_indices[i]
            model.Add(adiff == cs[i] - answer_degrees[subj_idx])
            aabs = model.NewIntVar(0, 28, f"aabs_{i}")
            model.AddAbsEquality(aabs, adiff)
            model.AddModuloEquality(aimod, aabs, 7)
            answer_imod7.append(aimod)
        for i in range(m):
            is_strong = beat_positions[i] in strong_beats
            if is_strong:
                model.AddAllowedAssignments([answer_imod7[i]], [(0,), (2,), (5,)])
            else:
                model.AddAllowedAssignments([answer_imod7[i]], [(0,), (1,), (2,), (4,), (5,), (6,)])
    penalties = []
    rewards = []
    for i in range(m):
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
        if 0 < i < m - 1:
            is_unison = model.NewBoolVar(f"uni_{i}")
            model.Add(interval_mod7[i] == 0).OnlyEnforceIf(is_unison)
            model.Add(interval_mod7[i] != 0).OnlyEnforceIf(is_unison.Not())
            penalties.append((is_unison, PENALTY_INTERIOR_UNISON))
    # --- Passing-tone constraint: dissonances must be approached and left by step ---
    for i in range(m):
        is_diss_1 = model.NewBoolVar(f"pt1_{i}")
        model.Add(interval_mod7[i] == 1).OnlyEnforceIf(is_diss_1)
        model.Add(interval_mod7[i] != 1).OnlyEnforceIf(is_diss_1.Not())
        is_diss_6 = model.NewBoolVar(f"pt6_{i}")
        model.Add(interval_mod7[i] == 6).OnlyEnforceIf(is_diss_6)
        model.Add(interval_mod7[i] != 6).OnlyEnforceIf(is_diss_6.Not())
        is_diss = model.NewBoolVar(f"ptd_{i}")
        model.AddBoolOr([is_diss_1, is_diss_6]).OnlyEnforceIf(is_diss)
        model.AddBoolAnd([is_diss_1.Not(), is_diss_6.Not()]).OnlyEnforceIf(is_diss.Not())
        if i == 0 or i == m - 1:
            # Boundary notes: forbid dissonance outright (no step context)
            model.Add(is_diss == 0)
        else:
            # Approach by step: abs(cs[i] - cs[i-1]) <= 1
            approach = model.NewIntVar(-28, 28, f"ptapp_{i}")
            model.Add(approach == cs[i] - cs[i - 1])
            abs_approach = model.NewIntVar(0, 28, f"ptaabs_{i}")
            model.AddAbsEquality(abs_approach, approach)
            step_in = model.NewBoolVar(f"ptin_{i}")
            model.Add(abs_approach <= 1).OnlyEnforceIf(step_in)
            model.Add(abs_approach > 1).OnlyEnforceIf(step_in.Not())
            # Resolution by step: abs(cs[i+1] - cs[i]) <= 1
            resolution = model.NewIntVar(-28, 28, f"ptres_{i}")
            model.Add(resolution == cs[i + 1] - cs[i])
            abs_resolution = model.NewIntVar(0, 28, f"ptrabs_{i}")
            model.AddAbsEquality(abs_resolution, resolution)
            step_out = model.NewBoolVar(f"ptout_{i}")
            model.Add(abs_resolution <= 1).OnlyEnforceIf(step_out)
            model.Add(abs_resolution > 1).OnlyEnforceIf(step_out.Not())
            # Penalise dissonance that isn't a passing tone
            not_passing = model.NewBoolVar(f"ptnp_{i}")
            model.AddBoolOr([step_in.Not(), step_out.Not()]).OnlyEnforceIf(not_passing)
            model.AddBoolAnd([step_in, step_out]).OnlyEnforceIf(not_passing.Not())
            bad_diss = model.NewBoolVar(f"ptbad_{i}")
            model.AddBoolAnd([is_diss, not_passing]).OnlyEnforceIf(bad_diss)
            model.AddBoolOr([is_diss.Not(), not_passing.Not()]).OnlyEnforceIf(bad_diss.Not())
            penalties.append((bad_diss, PENALTY_DISSONANCE_NOT_PASSING))
    # --- Answer weak-beat penalties (parallel to subject penalties) ---
    if answer_degrees is not None:
        for i in range(m):
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
    for i in range(m - 1):
        uni_i = model.NewBoolVar(f"u_{i}")
        uni_j = model.NewBoolVar(f"u_{i + 1}")
        model.Add(interval_mod7[i] == 0).OnlyEnforceIf(uni_i)
        model.Add(interval_mod7[i] != 0).OnlyEnforceIf(uni_i.Not())
        model.Add(interval_mod7[i + 1] == 0).OnlyEnforceIf(uni_j)
        model.Add(interval_mod7[i + 1] != 0).OnlyEnforceIf(uni_j.Not())
        model.AddBoolOr([uni_i.Not(), uni_j.Not()])
    for i in range(m - 1):
        cs_mot = model.NewIntVar(-28, 28, f"csmot_{i}")
        model.Add(cs_mot == cs[i + 1] - cs[i])
        # Compare CS motion to subject motion at CS onset points
        subj_idx = onset_indices[i]
        subj_idx_next = onset_indices[i + 1]
        subj_mot = subj_degrees[subj_idx_next] - subj_degrees[subj_idx]
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
    # --- Voice-leading: forbid parallel 5ths and octaves ---
    for i in range(m - 1):
        subj_idx_a = onset_indices[i]
        subj_idx_b = onset_indices[i + 1]
        if subj_idx_a == subj_idx_b:
            continue
        # CS motion and subject motion
        cs_vl = model.NewIntVar(-28, 28, f"csvl_{i}")
        model.Add(cs_vl == cs[i + 1] - cs[i])
        subj_vl = subj_degrees[subj_idx_b] - subj_degrees[subj_idx_a]
        # Both intervals are 5ths (mod 7 == 4)
        both_5th = model.NewBoolVar(f"b5_{i}")
        is_5th_a = model.NewBoolVar(f"i5a_{i}")
        is_5th_b = model.NewBoolVar(f"i5b_{i}")
        model.Add(interval_mod7[i] == 4).OnlyEnforceIf(is_5th_a)
        model.Add(interval_mod7[i] != 4).OnlyEnforceIf(is_5th_a.Not())
        model.Add(interval_mod7[i + 1] == 4).OnlyEnforceIf(is_5th_b)
        model.Add(interval_mod7[i + 1] != 4).OnlyEnforceIf(is_5th_b.Not())
        model.AddBoolAnd([is_5th_a, is_5th_b]).OnlyEnforceIf(both_5th)
        model.AddBoolOr([is_5th_a.Not(), is_5th_b.Not()]).OnlyEnforceIf(both_5th.Not())
        # Similar motion (same direction, neither static)
        sim_up = model.NewBoolVar(f"su_{i}")
        model.Add(cs_vl > 0).OnlyEnforceIf(sim_up)
        if subj_vl <= 0:
            model.Add(sim_up == 0)
        sim_dn = model.NewBoolVar(f"sd_{i}")
        model.Add(cs_vl < 0).OnlyEnforceIf(sim_dn)
        if subj_vl >= 0:
            model.Add(sim_dn == 0)
        similar = model.NewBoolVar(f"sim_{i}")
        model.AddBoolOr([sim_up, sim_dn]).OnlyEnforceIf(similar)
        model.AddBoolAnd([sim_up.Not(), sim_dn.Not()]).OnlyEnforceIf(similar.Not())
        # Forbid parallel 5ths: both 5ths + similar motion
        model.AddBoolOr([both_5th.Not(), similar.Not()])
        # Both intervals are unisons/octaves (mod 7 == 0)
        both_oct = model.NewBoolVar(f"b8_{i}")
        is_oct_a = model.NewBoolVar(f"i8a_{i}")
        is_oct_b = model.NewBoolVar(f"i8b_{i}")
        model.Add(interval_mod7[i] == 0).OnlyEnforceIf(is_oct_a)
        model.Add(interval_mod7[i] != 0).OnlyEnforceIf(is_oct_a.Not())
        model.Add(interval_mod7[i + 1] == 0).OnlyEnforceIf(is_oct_b)
        model.Add(interval_mod7[i + 1] != 0).OnlyEnforceIf(is_oct_b.Not())
        model.AddBoolAnd([is_oct_a, is_oct_b]).OnlyEnforceIf(both_oct)
        model.AddBoolOr([is_oct_a.Not(), is_oct_b.Not()]).OnlyEnforceIf(both_oct.Not())
        # Forbid parallel octaves/unisons: both octaves + similar motion
        model.AddBoolOr([both_oct.Not(), similar.Not()])
        # Forbid hidden 5ths/octaves: arriving at 5th or octave by similar motion
        # (only when target interval is perfect, regardless of source interval)
        arrive_perfect = model.NewBoolVar(f"ap_{i}")
        model.AddBoolOr([is_5th_b, is_oct_b]).OnlyEnforceIf(arrive_perfect)
        model.AddBoolAnd([is_5th_b.Not(), is_oct_b.Not()]).OnlyEnforceIf(arrive_perfect.Not())
        model.AddBoolOr([arrive_perfect.Not(), similar.Not()])
    # --- Melodic quality: directional momentum ---
    # cs_mot variables already exist from the loop above
    # Reward 3+ consecutive notes in the same direction
    for i in range(m - 2):
        cs_mot_a = model.NewIntVar(-28, 28, f"csmot_a_{i}")
        cs_mot_b = model.NewIntVar(-28, 28, f"csmot_b_{i}")
        model.Add(cs_mot_a == cs[i + 1] - cs[i])
        model.Add(cs_mot_b == cs[i + 2] - cs[i + 1])
        both_up = model.NewBoolVar(f"bothup_{i}")
        model.Add(cs_mot_a > 0).OnlyEnforceIf(both_up)
        model.Add(cs_mot_b > 0).OnlyEnforceIf(both_up)
        both_down = model.NewBoolVar(f"bothdn_{i}")
        model.Add(cs_mot_a < 0).OnlyEnforceIf(both_down)
        model.Add(cs_mot_b < 0).OnlyEnforceIf(both_down)
        run = model.NewBoolVar(f"run_{i}")
        model.AddBoolOr([both_up, both_down]).OnlyEnforceIf(run)
        model.AddBoolAnd([both_up.Not(), both_down.Not()]).OnlyEnforceIf(run.Not())
        rewards.append((run, REWARD_DIRECTIONAL_RUN))
    # Penalise zigzag: direction reversal on every pair of intervals
    for i in range(m - 2):
        cs_mot_a2 = model.NewIntVar(-28, 28, f"csmot_zz_a_{i}")
        cs_mot_b2 = model.NewIntVar(-28, 28, f"csmot_zz_b_{i}")
        model.Add(cs_mot_a2 == cs[i + 1] - cs[i])
        model.Add(cs_mot_b2 == cs[i + 2] - cs[i + 1])
        zz_up_down = model.NewBoolVar(f"zzud_{i}")
        model.Add(cs_mot_a2 > 0).OnlyEnforceIf(zz_up_down)
        model.Add(cs_mot_b2 < 0).OnlyEnforceIf(zz_up_down)
        zz_down_up = model.NewBoolVar(f"zzdu_{i}")
        model.Add(cs_mot_a2 < 0).OnlyEnforceIf(zz_down_up)
        model.Add(cs_mot_b2 > 0).OnlyEnforceIf(zz_down_up)
        zigzag = model.NewBoolVar(f"zz_{i}")
        model.AddBoolOr([zz_up_down, zz_down_up]).OnlyEnforceIf(zigzag)
        model.AddBoolAnd([zz_up_down.Not(), zz_down_up.Not()]).OnlyEnforceIf(zigzag.Not())
        penalties.append((zigzag, PENALTY_ZIGZAG))
    # --- Melodic quality: range usage ---
    cs_max_var = model.NewIntVar(min_degree, max_degree, "cs_max")
    cs_min_var = model.NewIntVar(min_degree, max_degree, "cs_min")
    model.AddMaxEquality(cs_max_var, cs)
    model.AddMinEquality(cs_min_var, cs)
    cs_range = model.NewIntVar(0, max_degree - min_degree, "cs_range")
    model.Add(cs_range == cs_max_var - cs_min_var)
    good_range = model.NewBoolVar("good_range")
    model.Add(cs_range >= MIN_GOOD_RANGE).OnlyEnforceIf(good_range)
    model.Add(cs_range < MIN_GOOD_RANGE).OnlyEnforceIf(good_range.Not())
    rewards.append((good_range, REWARD_RANGE_USAGE))
    stable_degrees = [(d % 7) for d in TONIC_TRIAD_DEGREES]
    for idx in [0, m - 1]:
        # Shift into non-negative range for modulo
        cs_shift = abs(min_degree) + 7
        cs_pos = model.NewIntVar(0, max_degree + cs_shift, f"cspos_{idx}")
        model.Add(cs_pos == cs[idx] + cs_shift)
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
    cs_degrees = tuple(solver.Value(cs[i]) for i in range(m))
    intervals = tuple(solver.Value(interval_mod7[i]) for i in range(m))
    midi_pitches = degrees_to_midi(
        degrees=cs_degrees,
        tonic_midi=tonic_midi,
        mode=subject.mode,
    )
    return GeneratedCountersubject(
        scale_indices=cs_degrees,
        durations=tuple(float(d) for d in cs_durations),
        midi_pitches=midi_pitches,
        vertical_intervals=intervals,
    )

def verify_countersubject(
    subject: GeneratedSubject,
    cs: GeneratedCountersubject,
    metre: tuple[int, int],
) -> list[str]:
    """Verify countersubject satisfies all constraints.

    CS has its own rhythm (fewer, longer notes than subject). Intervals
    are checked at CS onset positions using CS beat positions.
    """
    violations = []
    beat_positions = _compute_beat_positions(
        durations=cs.durations,
        metre=metre,
    )
    strong_beats = _get_strong_beats(metre=metre)
    m = len(cs.scale_indices)
    assert len(cs.durations) == m, (
        f"CS durations count {len(cs.durations)} != CS degree count {m}"
    )
    assert len(cs.vertical_intervals) == m, (
        f"CS intervals count {len(cs.vertical_intervals)} != CS degree count {m}"
    )
    for i, interval in enumerate(cs.vertical_intervals):
        is_strong = beat_positions[i] in strong_beats
        if is_strong and interval not in INVERTIBLE_CONSONANCES:
            violations.append(f"Note {i}: strong-beat interval {interval} not invertible")
        if interval == TRITONE_INTERVAL:
            violations.append(f"Note {i}: tritone interval")
    for i in range(m - 1):
        if cs.vertical_intervals[i] == 0 and cs.vertical_intervals[i + 1] == 0:
            violations.append(f"Notes {i}-{i+1}: consecutive unisons")
        iv_a = cs.vertical_intervals[i]
        iv_b = cs.vertical_intervals[i + 1]
        cs_dir = cs.scale_indices[i + 1] - cs.scale_indices[i]
        # Need subject motion at CS onset points — approximate from beat positions
        # For now check the simple case: both voices move same direction
        if cs_dir != 0:
            if iv_a == 4 and iv_b == 4:
                violations.append(f"Notes {i}-{i+1}: parallel 5ths")
            if iv_a == 0 and iv_b == 0:
                violations.append(f"Notes {i}-{i+1}: parallel octaves/unisons")
    return violations

if __name__ == "__main__":
    from motifs.subject_gen import select_subject
    from motifs.answer_generator import generate_answer
    print("Testing countersubject generation (dual validation)...")
    print("=" * 60)
    success_count = 0
    for seed in range(5):
        print(f"Seed {seed}...", end=" ", flush=True)
        subject = select_subject(
            mode="minor",
            metre=(4, 4),
            tonic_midi=67,
            target_bars=2,
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
                n_subj = len(subject.scale_indices)
                n_cs = len(cs.scale_indices)
                ratio = n_cs / n_subj if n_subj > 0 else 0
                print(f"OK (Subject: {n_subj} notes, CS: {n_cs} notes, ratio {ratio:.2f})")
                success_count += 1
                print(f"  Subject:  {subject.scale_indices}")
                print(f"  Subject durations: {subject.durations}")
                print(f"  Answer:   {answer.scale_indices} ({answer.answer_type})")
                print(f"  CS:       {cs.scale_indices}")
                print(f"  CS durations: {cs.durations}")
                print(f"  Intervals (vs subj): {cs.vertical_intervals}")
        else:
            print("FAILED (no solution)")
    print(f"\n{success_count}/5 subjects produced valid countersubjects (dual validation)")
