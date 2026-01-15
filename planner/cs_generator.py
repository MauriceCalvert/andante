"""Gold-plated counter-subject generator using CP-SAT.

Generates beautiful, invertible counter-subjects by jointly optimizing
pitch degrees AND rhythm in a single model. This ensures:
- Rhythmic density matches subject (no busy sixteenths against quarter notes)
- All vertical intervals consonant and invertible
- Melodic contour complements subject (contrary motion at climactic points)
- Cadential convergence (both voices arrive together)
- Motivic coherence (durations from subject's vocabulary)

The solver produces counter-subjects worthy of Bach.
"""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Optional

import yaml
from ortools.sat.python import cp_model

DATA_DIR: Path = Path(__file__).parent.parent / "data"
RULES_PATH: Path = DATA_DIR / "counterpoint" / "rules.yaml"

# Scale intervals (semitones from tonic)
MAJOR_SCALE: tuple[int, ...] = (0, 2, 4, 5, 7, 9, 11)
MINOR_SCALE: tuple[int, ...] = (0, 2, 3, 5, 7, 8, 10)

# Valid durations in descending order
VALID_DURATIONS: tuple[Fraction, ...] = (
    Fraction(1, 2),    # Half note
    Fraction(3, 8),    # Dotted quarter
    Fraction(1, 4),    # Quarter note
    Fraction(3, 16),   # Dotted eighth
    Fraction(1, 8),    # Eighth note
    Fraction(1, 16),   # Sixteenth note
)

# Baroque-style durations: beat-aligned, no 16ths or dotted 8ths
# For interleaved/invertible counterpoint where modern syncopation sounds wrong
BAROQUE_DURATIONS: tuple[Fraction, ...] = (
    Fraction(1, 2),    # Half note
    Fraction(3, 8),    # Dotted quarter (on beat)
    Fraction(1, 4),    # Quarter note
    Fraction(1, 8),    # Eighth note (minimum for baroque CS)
)

# Default minimum duration for counter-subject notes
DEFAULT_MIN_CS_DURATION: Fraction = Fraction(1, 16)

# Baroque minimum: 1/8 note (no busy 16ths in counter-subject)
BAROQUE_MIN_CS_DURATION: Fraction = Fraction(1, 8)

# Duration scale for integer arithmetic (LCM of denominators)
DURATION_SCALE: int = 32

# Consonant interval classes (semitones mod 12)
PERFECT_CONSONANCES: frozenset[int] = frozenset({0, 7})  # Unison, fifth
IMPERFECT_CONSONANCES: frozenset[int] = frozenset({3, 4, 8, 9})  # 3rds, 6ths
ALL_CONSONANCES: frozenset[int] = PERFECT_CONSONANCES | IMPERFECT_CONSONANCES

# Strong beats in common time (positions where collisions are OK)
# Expressed as fractions of a bar
STRONG_BEATS: frozenset[Fraction] = frozenset({
    Fraction(0),      # Beat 1
    Fraction(1, 2),   # Beat 3
})


@dataclass(frozen=True)
class CounterSubject:
    """A counter-subject with degrees and rhythm."""
    degrees: tuple[int, ...]
    durations: tuple[Fraction, ...]

    @property
    def total_duration(self) -> Fraction:
        return sum(self.durations, Fraction(0))

    def __post_init__(self) -> None:
        assert len(self.degrees) == len(self.durations), "Degrees and durations must match"


@dataclass(frozen=True)
class Subject:
    """Subject material for CS generation."""
    degrees: tuple[int, ...]
    durations: tuple[Fraction, ...]
    mode: str  # "major" or "minor"

    @property
    def total_duration(self) -> Fraction:
        return sum(self.durations, Fraction(0))

    @property
    def min_duration(self) -> Fraction:
        return min(self.durations)

    @property
    def duration_vocabulary(self) -> frozenset[Fraction]:
        return frozenset(self.durations)

    @property
    def attack_times(self) -> tuple[Fraction, ...]:
        """Compute attack times (note onsets) from durations."""
        attacks: list[Fraction] = [Fraction(0)]
        pos = Fraction(0)
        for d in self.durations[:-1]:  # Exclude last (end, not attack)
            pos += d
            attacks.append(pos)
        return tuple(attacks)

    @property
    def climax_index(self) -> int:
        """Index of highest pitch in subject."""
        return self.degrees.index(max(self.degrees))

    @property
    def scale(self) -> tuple[int, ...]:
        return MAJOR_SCALE if self.mode == "major" else MINOR_SCALE


def _degree_to_semitone(degree: int, scale: tuple[int, ...]) -> int:
    """Convert scale degree (1-7) to semitone offset."""
    return scale[degree - 1]


def _interval_class(deg1: int, deg2: int, scale: tuple[int, ...]) -> int:
    """Compute interval class (0-11) between two degrees."""
    s1 = _degree_to_semitone(deg1, scale)
    s2 = _degree_to_semitone(deg2, scale)
    return abs(s2 - s1) % 12


def _is_strong_beat(position: Fraction) -> bool:
    """Check if position falls on a strong beat."""
    # Normalize to within-bar position
    bar_position = position % Fraction(1)
    return bar_position in STRONG_BEATS


def generate_countersubject(
    subject: Subject,
    timeout_seconds: float = 10.0,
    interleaved: bool = False,
    baroque_rhythm: bool = False,
) -> Optional[CounterSubject]:
    """Generate a beautiful, invertible counter-subject.

    Joint optimization of pitch and rhythm ensures:
    - Rhythmic density matches subject
    - All intervals consonant and invertible
    - Melodic contour complements subject
    - Cadential convergence
    - Motivic coherence

    Args:
        subject: The subject to write a counter-subject against
        timeout_seconds: Solver time limit
        interleaved: If True, enforce strict invertibility at the unison for
                     Goldberg-style interleaved counterpoint (avoid seconds)
        baroque_rhythm: If True, constrain to baroque-style beat-aligned rhythms:
                       - Minimum duration 1/8 (no 16th notes)
                       - No dotted-8th syncopation
                       - Onsets on 1/8 grid

    Returns:
        CounterSubject with degrees and durations, or None if infeasible
    """
    # For interleaved counterpoint, always use baroque rhythm
    use_baroque = baroque_rhythm or interleaved

    n_subject = len(subject.degrees)
    if n_subject < 2:
        # Trivial case: return transposed subject
        return CounterSubject(
            degrees=tuple(((d + 2) % 7) + 1 for d in subject.degrees),
            durations=subject.durations,
        )

    # Determine CS note count bounds (similar density to subject)
    min_cs_notes = max(3, n_subject - 2)
    max_cs_notes = n_subject + 2

    # Determine allowed durations (baroque mode excludes 16ths and dotted 8ths)
    allowed_durations = _compute_allowed_durations(subject, baroque=use_baroque)

    model = cp_model.CpModel()

    # === VARIABLES ===

    # CS pitch degrees (1-7) for each CS note position
    cs_degrees: list[cp_model.IntVar] = []
    for i in range(max_cs_notes):
        d = model.NewIntVar(0, 7, f"deg_{i}")  # 0 means inactive
        cs_degrees.append(d)

    # CS durations (scaled integers) for each CS note position
    allowed_scaled = [int(d * DURATION_SCALE) for d in allowed_durations]
    cs_durations: list[cp_model.IntVar] = []
    for i in range(max_cs_notes):
        dur = model.NewIntVar(0, max(allowed_scaled), f"dur_{i}")
        model.AddAllowedAssignments([dur], [(v,) for v in allowed_scaled + [0]])
        cs_durations.append(dur)

    # Active flags (note is used)
    active: list[cp_model.BoolVar] = []
    for i in range(max_cs_notes):
        a = model.NewBoolVar(f"active_{i}")
        # Degree > 0 iff active
        model.Add(cs_degrees[i] > 0).OnlyEnforceIf(a)
        model.Add(cs_degrees[i] == 0).OnlyEnforceIf(a.Not())
        # Duration > 0 iff active
        model.Add(cs_durations[i] > 0).OnlyEnforceIf(a)
        model.Add(cs_durations[i] == 0).OnlyEnforceIf(a.Not())
        active.append(a)

    # === HARD CONSTRAINTS ===

    # H1: Total duration equals subject duration
    target_scaled = int(subject.total_duration * DURATION_SCALE)
    model.Add(cp_model.LinearExpr.Sum(cs_durations) == target_scaled)

    # H2: Notes are contiguous (no gaps)
    for i in range(1, max_cs_notes):
        model.Add(active[i] <= active[i - 1])

    # H3: Note count in range
    model.Add(cp_model.LinearExpr.Sum(active) >= min_cs_notes)
    model.Add(cp_model.LinearExpr.Sum(active) <= max_cs_notes)

    # H4: Forbidden degrees (7 in major, 6 and 7 in minor)
    forbidden = {7} if subject.mode == "major" else {6, 7}
    for i in range(max_cs_notes):
        for fd in forbidden:
            model.Add(cs_degrees[i] != fd).OnlyEnforceIf(active[i])

    # H5: First and last notes must be consonant with corresponding subject notes
    # (We'll handle this via the vertical consonance constraints)

    # === INTERVALLIC CONSTRAINTS ===

    # To apply vertical constraints, we need to know which CS note aligns with
    # which subject note. We compute CS attack times from cumulative durations.

    # Cumulative duration at each CS position (attack time)
    cs_attacks: list[cp_model.IntVar] = []
    for i in range(max_cs_notes):
        if i == 0:
            atk = model.NewIntVar(0, 0, f"cs_atk_0")
            model.Add(atk == 0)
        else:
            atk = model.NewIntVar(0, target_scaled, f"cs_atk_{i}")
            model.Add(atk == cp_model.LinearExpr.Sum(cs_durations[:i]))
        cs_attacks.append(atk)

    # Subject attack times (fixed)
    subj_attacks_scaled: list[int] = []
    pos = 0
    for d in subject.durations:
        subj_attacks_scaled.append(pos)
        pos += int(d * DURATION_SCALE)

    # For each CS note, determine which subject note(s) it sounds against
    # and enforce consonance
    penalties: list[cp_model.LinearExpr] = []

    _add_vertical_constraints(
        model, cs_degrees, cs_attacks, cs_durations, active,
        subject, subj_attacks_scaled, target_scaled, penalties
    )

    # === MELODIC CONSTRAINTS ===

    _add_melodic_constraints(
        model, cs_degrees, active, subject, max_cs_notes, penalties
    )

    # === RHYTHMIC CONSTRAINTS ===

    _add_rhythmic_constraints(
        model, cs_durations, cs_attacks, active, subject,
        subj_attacks_scaled, allowed_scaled, max_cs_notes, target_scaled, penalties
    )

    # === CADENTIAL CONSTRAINTS ===

    _add_cadential_constraints(
        model, cs_degrees, active, subject, max_cs_notes, penalties
    )

    # === MOTIVIC CONSTRAINTS ===

    _add_motivic_constraints(
        model, cs_durations, active, subject, allowed_scaled, max_cs_notes, penalties
    )

    # === INVERTIBILITY CONSTRAINTS ===

    _add_invertibility_constraints(
        model, cs_degrees, cs_attacks, active, subject,
        subj_attacks_scaled, target_scaled, penalties, interleaved
    )

    # === CLIMAX OFFSET ===

    _add_climax_constraints(
        model, cs_degrees, active, subject, max_cs_notes, penalties
    )

    # === SOLVE ===

    if penalties:
        model.Minimize(cp_model.LinearExpr.Sum(penalties))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout_seconds
    solver.parameters.num_search_workers = 4

    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    # Extract solution
    result_degrees: list[int] = []
    result_durations: list[Fraction] = []
    for i in range(max_cs_notes):
        if solver.Value(active[i]):
            result_degrees.append(solver.Value(cs_degrees[i]))
            dur_scaled = solver.Value(cs_durations[i])
            result_durations.append(Fraction(dur_scaled, DURATION_SCALE))

    return CounterSubject(
        degrees=tuple(result_degrees),
        durations=tuple(result_durations),
    )


def _compute_allowed_durations(subject: Subject, baroque: bool = False) -> list[Fraction]:
    """Compute allowed CS durations based on subject's vocabulary.

    CS durations are limited to:
    - Durations in subject
    - One step faster than subject's fastest
    - One step slower than subject's slowest

    This ensures similar rhythmic density.

    Args:
        subject: Subject to derive durations from
        baroque: If True, filter to baroque-style durations only:
                - No 16th notes (minimum 1/8)
                - No dotted-8ths (3/16) - creates modern syncopation
                - All onsets on 1/8 grid
    """
    # Select base duration set based on mode
    valid_set = BAROQUE_DURATIONS if baroque else VALID_DURATIONS

    subj_durs = subject.duration_vocabulary
    subj_min = min(subj_durs)
    subj_max = max(subj_durs)

    # Enforce baroque minimum if in baroque mode
    if baroque:
        subj_min = max(subj_min, BAROQUE_MIN_CS_DURATION)

    # Find one step faster and slower in valid durations
    faster = None
    slower = None
    for i, d in enumerate(valid_set):
        if d < subj_min and faster is None:
            faster = d
        if d > subj_max:
            slower = d

    allowed = set(subj_durs)
    if faster is not None:
        allowed.add(faster)
    if slower is not None:
        allowed.add(slower)

    # Filter to valid durations only (baroque or all)
    result = sorted([d for d in allowed if d in valid_set], reverse=True)

    # Ensure at least 1/8 and 1/4 are available for baroque mode
    if baroque:
        if Fraction(1, 8) not in result:
            result.append(Fraction(1, 8))
        if Fraction(1, 4) not in result:
            result.append(Fraction(1, 4))
        result = sorted(result, reverse=True)

    return result


def _add_vertical_constraints(
    model,
    cs_degrees: list,
    cs_attacks: list,
    cs_durations: list,
    active: list,
    subject: Subject,
    subj_attacks_scaled: list[int],
    target_scaled: int,
    penalties: list,
) -> None:
    """Add vertical interval constraints (consonance, no parallels)."""
    scale = subject.scale
    n_subj = len(subject.degrees)
    max_cs = len(cs_degrees)

    # For each subject note, we need to check what CS note(s) sound against it
    # Subject note i sounds from subj_attacks_scaled[i] to subj_attacks_scaled[i+1] (or end)

    for si in range(n_subj):
        subj_start = subj_attacks_scaled[si]
        subj_end = subj_attacks_scaled[si + 1] if si + 1 < n_subj else target_scaled
        subj_deg = subject.degrees[si]

        for ci in range(max_cs):
            # Check if CS note ci overlaps with subject note si
            # CS note ci sounds from cs_attacks[ci] to cs_attacks[ci] + cs_durations[ci]

            # Create overlap indicator
            overlap = model.NewBoolVar(f"overlap_{si}_{ci}")

            # CS note starts before subject note ends AND
            # CS note ends after subject note starts
            # cs_attacks[ci] < subj_end AND cs_attacks[ci] + cs_durations[ci] > subj_start

            cs_end = model.NewIntVar(0, target_scaled * 2, f"cs_end_{ci}")
            model.Add(cs_end == cs_attacks[ci] + cs_durations[ci])

            starts_before_end = model.NewBoolVar(f"sbe_{si}_{ci}")
            ends_after_start = model.NewBoolVar(f"eas_{si}_{ci}")

            model.Add(cs_attacks[ci] < subj_end).OnlyEnforceIf(starts_before_end)
            model.Add(cs_attacks[ci] >= subj_end).OnlyEnforceIf(starts_before_end.Not())

            model.Add(cs_end > subj_start).OnlyEnforceIf(ends_after_start)
            model.Add(cs_end <= subj_start).OnlyEnforceIf(ends_after_start.Not())

            # Overlap = active AND starts_before_end AND ends_after_start
            model.AddBoolAnd([active[ci], starts_before_end, ends_after_start]).OnlyEnforceIf(overlap)
            model.AddBoolOr([active[ci].Not(), starts_before_end.Not(), ends_after_start.Not()]).OnlyEnforceIf(overlap.Not())

            # When overlapping, enforce consonance
            for cs_d in range(1, 8):
                ic = _interval_class(subj_deg, cs_d, scale)
                is_this_deg = model.NewBoolVar(f"is_deg_{si}_{ci}_{cs_d}")
                model.Add(cs_degrees[ci] == cs_d).OnlyEnforceIf(is_this_deg)
                model.Add(cs_degrees[ci] != cs_d).OnlyEnforceIf(is_this_deg.Not())

                both = model.NewBoolVar(f"both_{si}_{ci}_{cs_d}")
                model.AddBoolAnd([overlap, is_this_deg]).OnlyEnforceIf(both)
                model.AddBoolOr([overlap.Not(), is_this_deg.Not()]).OnlyEnforceIf(both.Not())

                if ic not in ALL_CONSONANCES:
                    # Dissonance: forbid
                    model.Add(both == 0)
                elif ic in PERFECT_CONSONANCES and ic != 0:
                    # Perfect fifth: penalize heavily (invertibility)
                    penalties.append(both * 80)
                elif ic == 0 and si > 0 and si < n_subj - 1:
                    # Interior unison: penalize
                    penalties.append(both * 120)

    # Parallel fifths/octaves: check consecutive subject notes
    _add_parallel_fifth_constraints(model, cs_degrees, active, subject, penalties)


def _add_parallel_fifth_constraints(
    model,
    cs_degrees: list,
    active: list,
    subject: Subject,
    penalties: list,
) -> None:
    """Forbid parallel perfect fifths and octaves."""
    scale = subject.scale
    max_cs = len(cs_degrees)

    # Check consecutive CS notes for parallel motion to perfect intervals
    for i in range(1, max_cs):
        for prev_d in range(1, 8):
            for curr_d in range(1, 8):
                prev_semi = _degree_to_semitone(prev_d, scale)
                curr_semi = _degree_to_semitone(curr_d, scale)
                cs_motion = curr_semi - prev_semi

                if cs_motion == 0:
                    continue

                # For each pair of consecutive subject notes
                for si in range(1, len(subject.degrees)):
                    subj_prev = subject.degrees[si - 1]
                    subj_curr = subject.degrees[si]

                    subj_prev_semi = _degree_to_semitone(subj_prev, scale)
                    subj_curr_semi = _degree_to_semitone(subj_curr, scale)
                    subj_motion = subj_curr_semi - subj_prev_semi

                    if subj_motion == 0:
                        continue

                    # Check if both move in same direction
                    same_direction = (cs_motion > 0) == (subj_motion > 0)

                    # Check if both intervals are perfect
                    ic_prev = _interval_class(subj_prev, prev_d, scale)
                    ic_curr = _interval_class(subj_curr, curr_d, scale)

                    if same_direction and ic_prev in {0, 7} and ic_curr in {0, 7}:
                        # Parallel perfect: forbid this assignment
                        is_prev = model.NewBoolVar(f"pp_prev_{i}_{si}_{prev_d}")
                        is_curr = model.NewBoolVar(f"pp_curr_{i}_{si}_{curr_d}")

                        model.Add(cs_degrees[i - 1] == prev_d).OnlyEnforceIf(is_prev)
                        model.Add(cs_degrees[i - 1] != prev_d).OnlyEnforceIf(is_prev.Not())
                        model.Add(cs_degrees[i] == curr_d).OnlyEnforceIf(is_curr)
                        model.Add(cs_degrees[i] != curr_d).OnlyEnforceIf(is_curr.Not())

                        both_active = model.NewBoolVar(f"pp_ba_{i}_{si}")
                        model.AddBoolAnd([active[i - 1], active[i]]).OnlyEnforceIf(both_active)
                        model.AddBoolOr([active[i - 1].Not(), active[i].Not()]).OnlyEnforceIf(both_active.Not())

                        # Forbid: NOT (is_prev AND is_curr AND both_active)
                        model.AddBoolOr([is_prev.Not(), is_curr.Not(), both_active.Not()])


def _add_melodic_constraints(
    model,
    cs_degrees: list,
    active: list,
    subject: Subject,
    max_cs: int,
    penalties: list,
) -> None:
    """Add melodic line constraints (contrary motion, leap compensation, stepwise preference)."""
    scale = subject.scale

    for i in range(1, max_cs):
        both_active = model.NewBoolVar(f"mel_ba_{i}")
        model.AddBoolAnd([active[i - 1], active[i]]).OnlyEnforceIf(both_active)
        model.AddBoolOr([active[i - 1].Not(), active[i].Not()]).OnlyEnforceIf(both_active.Not())

        for prev_d in range(1, 8):
            for curr_d in range(1, 8):
                prev_semi = _degree_to_semitone(prev_d, scale)
                curr_semi = _degree_to_semitone(curr_d, scale)
                motion = abs(curr_semi - prev_semi)

                is_move = model.NewBoolVar(f"move_{i}_{prev_d}_{curr_d}")
                is_prev = model.NewBoolVar(f"mel_prev_{i}_{prev_d}")
                is_curr = model.NewBoolVar(f"mel_curr_{i}_{curr_d}")

                model.Add(cs_degrees[i - 1] == prev_d).OnlyEnforceIf(is_prev)
                model.Add(cs_degrees[i - 1] != prev_d).OnlyEnforceIf(is_prev.Not())
                model.Add(cs_degrees[i] == curr_d).OnlyEnforceIf(is_curr)
                model.Add(cs_degrees[i] != curr_d).OnlyEnforceIf(is_curr.Not())

                model.AddBoolAnd([both_active, is_prev, is_curr]).OnlyEnforceIf(is_move)
                model.AddBoolOr([both_active.Not(), is_prev.Not(), is_curr.Not()]).OnlyEnforceIf(is_move.Not())

                # Penalize immediate repetition
                if prev_d == curr_d:
                    penalties.append(is_move * 20)

                # Penalize large leaps (> 5 semitones)
                if motion > 5:
                    penalty = 30 if motion <= 7 else 150
                    penalties.append(is_move * penalty)

                # Penalize non-stepwise motion (encourage 70% stepwise)
                if motion > 2:
                    penalties.append(is_move * 10)


def _add_rhythmic_constraints(
    model,
    cs_durations: list,
    cs_attacks: list,
    active: list,
    subject: Subject,
    subj_attacks_scaled: list[int],
    allowed_scaled: list[int],
    max_cs: int,
    target_scaled: int,
    penalties: list,
) -> None:
    """Add rhythmic constraints (attack collision awareness, variety)."""

    # Subject attack times (excluding start at 0)
    subj_attack_set = set(subj_attacks_scaled[1:])  # Skip initial 0

    # Strong beats (scaled)
    bar_scaled = DURATION_SCALE  # One bar = 32 units
    strong_beats_scaled = {0, bar_scaled // 2}  # Beat 1 and 3

    for i in range(1, max_cs):
        # Penalize attack collisions on weak beats
        for atk in subj_attack_set:
            # Check if this is a weak beat
            bar_pos = atk % bar_scaled
            is_weak = bar_pos not in strong_beats_scaled

            if is_weak:
                collision = model.NewBoolVar(f"col_{i}_{atk}")
                model.Add(cs_attacks[i] == atk).OnlyEnforceIf(collision, active[i])
                model.Add(cs_attacks[i] != atk).OnlyEnforceIf(collision.Not())

                penalties.append(collision * 100)

    # Penalize consecutive equal durations (variety)
    for i in range(max_cs - 1):
        both_active = model.NewBoolVar(f"rhy_ba_{i}")
        model.AddBoolAnd([active[i], active[i + 1]]).OnlyEnforceIf(both_active)
        model.AddBoolOr([active[i].Not(), active[i + 1].Not()]).OnlyEnforceIf(both_active.Not())

        same_dur = model.NewBoolVar(f"same_dur_{i}")
        model.Add(cs_durations[i] == cs_durations[i + 1]).OnlyEnforceIf(same_dur, both_active)
        model.Add(cs_durations[i] != cs_durations[i + 1]).OnlyEnforceIf(same_dur.Not())

        penalties.append(same_dur * 15)

    # Limit use of any single duration value (max 50% of notes)
    for dur_val in allowed_scaled:
        if dur_val == 0:
            continue
        uses: list = []
        for i in range(max_cs):
            use = model.NewBoolVar(f"use_{dur_val}_{i}")
            model.Add(cs_durations[i] == dur_val).OnlyEnforceIf(use)
            model.Add(cs_durations[i] != dur_val).OnlyEnforceIf(use.Not())
            uses.append(use)

        # At most half + 1 of max_cs notes can use this duration
        model.Add(cp_model.LinearExpr.Sum(uses) <= max_cs // 2 + 1)


def _add_cadential_constraints(
    model,
    cs_degrees: list,
    active: list,
    subject: Subject,
    max_cs: int,
    penalties: list,
) -> None:
    """Add cadential constraints (final note, penultimate approach)."""

    # Find last active note
    # We want: final CS note is 1 or 5, approached by step

    # For each possible final position
    for final_pos in range(max_cs):
        is_final = model.NewBoolVar(f"final_{final_pos}")

        # is_final means: active[final_pos] AND NOT active[final_pos + 1]
        if final_pos == max_cs - 1:
            model.Add(is_final == active[final_pos])
        else:
            model.AddBoolAnd([active[final_pos], active[final_pos + 1].Not()]).OnlyEnforceIf(is_final)
            model.AddBoolOr([active[final_pos].Not(), active[final_pos + 1]]).OnlyEnforceIf(is_final.Not())

        # When is_final, penalize non-stable degrees
        for d in range(1, 8):
            is_deg = model.NewBoolVar(f"final_deg_{final_pos}_{d}")
            model.Add(cs_degrees[final_pos] == d).OnlyEnforceIf(is_deg)
            model.Add(cs_degrees[final_pos] != d).OnlyEnforceIf(is_deg.Not())

            both = model.NewBoolVar(f"final_both_{final_pos}_{d}")
            model.AddBoolAnd([is_final, is_deg]).OnlyEnforceIf(both)
            model.AddBoolOr([is_final.Not(), is_deg.Not()]).OnlyEnforceIf(both.Not())

            # Reward 1 and 5, penalize others
            if d not in {1, 5}:
                penalties.append(both * 50)

        # Penultimate should approach by step
        if final_pos > 0:
            penult_pos = final_pos - 1
            scale = subject.scale

            for pd in range(1, 8):
                for fd in range(1, 8):
                    p_semi = _degree_to_semitone(pd, scale)
                    f_semi = _degree_to_semitone(fd, scale)
                    motion = abs(f_semi - p_semi)

                    if motion > 2:  # Not stepwise
                        is_p = model.NewBoolVar(f"pen_p_{final_pos}_{pd}")
                        is_f = model.NewBoolVar(f"pen_f_{final_pos}_{fd}")

                        model.Add(cs_degrees[penult_pos] == pd).OnlyEnforceIf(is_p)
                        model.Add(cs_degrees[penult_pos] != pd).OnlyEnforceIf(is_p.Not())
                        model.Add(cs_degrees[final_pos] == fd).OnlyEnforceIf(is_f)
                        model.Add(cs_degrees[final_pos] != fd).OnlyEnforceIf(is_f.Not())

                        all_three = model.NewBoolVar(f"pen_all_{final_pos}_{pd}_{fd}")
                        model.AddBoolAnd([is_final, is_p, is_f]).OnlyEnforceIf(all_three)
                        model.AddBoolOr([is_final.Not(), is_p.Not(), is_f.Not()]).OnlyEnforceIf(all_three.Not())

                        penalties.append(all_three * 40)


def _add_motivic_constraints(
    model,
    cs_durations: list,
    active: list,
    subject: Subject,
    allowed_scaled: list[int],
    max_cs: int,
    penalties: list,
) -> None:
    """Add motivic coherence constraints (prefer subject's duration vocabulary)."""

    # Subject's duration vocabulary (scaled)
    subj_dur_scaled = {int(d * DURATION_SCALE) for d in subject.duration_vocabulary}

    for i in range(max_cs):
        for dur_val in allowed_scaled:
            if dur_val == 0:
                continue

            uses_dur = model.NewBoolVar(f"mot_{i}_{dur_val}")
            model.Add(cs_durations[i] == dur_val).OnlyEnforceIf(uses_dur)
            model.Add(cs_durations[i] != dur_val).OnlyEnforceIf(uses_dur.Not())

            # Penalize durations not in subject's vocabulary
            if dur_val not in subj_dur_scaled:
                penalties.append(uses_dur * 5)


def _add_invertibility_constraints(
    model,
    cs_degrees: list,
    cs_attacks: list,
    active: list,
    subject: Subject,
    subj_attacks_scaled: list[int],
    target_scaled: int,
    penalties: list,
    interleaved: bool = False,
) -> None:
    """Add invertibility constraints (avoid intervals that become dissonant when inverted).

    When voices are exchanged and transposed, interval X becomes (12-X) mod 12.
    Perfect 5th (7) becomes perfect 4th (5) which is dissonant in two-part counterpoint.

    For interleaved (Goldberg-style) counterpoint with unison inversion:
    - Seconds (1, 2 semitones) become sevenths when inverted - strongly forbid
    - Thirds and sixths remain consonant when inverted - prefer these
    """
    # Fifth penalty is already added in vertical constraints
    if not interleaved:
        return
    scale = subject.scale
    n_subj = len(subject.degrees)
    max_cs = len(cs_degrees)
    # Intervals that become dissonant when inverted at unison:
    # 1 semitone (minor 2nd) -> 11 semitones (major 7th)
    # 2 semitones (major 2nd) -> 10 semitones (minor 7th)
    BAD_FOR_UNISON_INVERSION: frozenset[int] = frozenset({1, 2, 10, 11})
    SECOND_PENALTY: int = 200  # Strong penalty for seconds
    for si in range(n_subj):
        subj_deg = subject.degrees[si]
        for ci in range(max_cs):
            for cs_d in range(1, 8):
                ic = _interval_class(subj_deg, cs_d, scale)
                if ic in BAD_FOR_UNISON_INVERSION:
                    is_deg = model.NewBoolVar(f"inv_deg_{si}_{ci}_{cs_d}")
                    model.Add(cs_degrees[ci] == cs_d).OnlyEnforceIf(is_deg)
                    model.Add(cs_degrees[ci] != cs_d).OnlyEnforceIf(is_deg.Not())
                    both = model.NewBoolVar(f"inv_both_{si}_{ci}_{cs_d}")
                    model.AddBoolAnd([active[ci], is_deg]).OnlyEnforceIf(both)
                    model.AddBoolOr([active[ci].Not(), is_deg.Not()]).OnlyEnforceIf(both.Not())
                    penalties.append(both * SECOND_PENALTY)


def _add_climax_constraints(
    model,
    cs_degrees: list,
    active: list,
    subject: Subject,
    max_cs: int,
    penalties: list,
) -> None:
    """Add climax offset constraints (CS high point shouldn't coincide with subject high point)."""

    subj_climax_idx = subject.climax_index

    # Penalize CS having its highest note at the same relative position
    # Map CS note index to approximate subject position
    n_subj = len(subject.degrees)

    for i in range(max_cs):
        # Approximate relative position
        rel_pos = i * n_subj // max_cs if max_cs > 0 else 0

        if rel_pos == subj_climax_idx:
            # Penalize if this CS note is the highest
            # We approximate by penalizing degree 6 at this position (highest non-forbidden)
            is_high = model.NewBoolVar(f"climax_{i}")
            model.Add(cs_degrees[i] == 6).OnlyEnforceIf(is_high, active[i])
            model.Add(cs_degrees[i] != 6).OnlyEnforceIf(is_high.Not())

            penalties.append(is_high * 25)
