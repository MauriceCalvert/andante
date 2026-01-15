"""Texture system: voice relationship patterns.

A texture specifies how voices interact in time and pitch space.
Textures are orthogonal to treatments (melodic transformations).

Pipeline: source -> treatment -> texture -> orchestration -> realiser
"""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Optional

import yaml
from ortools.sat.python import cp_model

from shared.pitch import FloatingNote, Pitch, Rest, wrap_degree
from shared.timed_material import TimedMaterial

# Scale intervals (semitones from tonic) for consonance checking
MAJOR_SCALE: tuple[int, ...] = (0, 2, 4, 5, 7, 9, 11)
MINOR_SCALE: tuple[int, ...] = (0, 2, 3, 5, 7, 8, 10)

# Consonant interval classes (semitones mod 12)
CONSONANCES: frozenset[int] = frozenset({0, 3, 4, 7, 8, 9})  # unison, 3rds, 5th, 6ths
PERFECT_INTERVALS: frozenset[int] = frozenset({0, 7})  # unison, fifth

DATA_DIR = Path(__file__).parent.parent / "data"


@dataclass(frozen=True)
class TextureSpec:
    """Specification for a texture."""
    name: str
    time_relation: str
    pitch_relation: str
    voice_roles: dict[str, str]
    parameters: dict
    interdictions: tuple[str, ...]


def _load_textures() -> dict[str, TextureSpec]:
    """Load texture definitions from YAML."""
    with open(DATA_DIR / "textures.yaml", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    result: dict[str, TextureSpec] = {}
    for name, spec in data.items():
        result[name] = TextureSpec(
            name=name,
            time_relation=spec.get("time_relation", "independent"),
            pitch_relation=spec.get("pitch_relation", "independent"),
            voice_roles=spec.get("voice_roles", {}),
            parameters=spec.get("parameters", {}),
            interdictions=tuple(spec.get("interdictions", [])),
        )
    return result


TEXTURES: dict[str, TextureSpec] = _load_textures()


def get_texture(name: str) -> TextureSpec:
    """Get texture spec by name, defaulting to polyphonic."""
    return TEXTURES.get(name, TEXTURES["polyphonic"])


def texture_allows(texture_name: str, feature: str) -> bool:
    """Check if texture allows a processing feature."""
    texture = get_texture(texture_name)
    return feature not in texture.interdictions


def apply_texture(
    treated_soprano: TimedMaterial,
    counter_subject: TimedMaterial,
    texture: TextureSpec,
    budget: Fraction,
    voice_count: int,
    tonal_target: str,
    bar_dur: Fraction,
) -> tuple[TimedMaterial, ...]:
    """Arrange treated material according to texture spec.

    Args:
        treated_soprano: Soprano material after treatment transformation
        counter_subject: Counter-subject material
        texture: Texture specification
        budget: Total duration for the phrase
        voice_count: Number of voices
        tonal_target: Tonal target for harmonic context
        bar_dur: Duration of one bar

    Returns:
        Tuple of TimedMaterial for each voice
    """
    if texture.time_relation == "offset" and texture.name == "interleaved":
        return _apply_interleaved(
            treated_soprano, counter_subject, texture, budget, voice_count, tonal_target, bar_dur
        )
    elif texture.time_relation == "offset" and texture.name == "canon":
        return _apply_canon(
            treated_soprano, texture, budget, voice_count, tonal_target, bar_dur
        )
    elif texture.time_relation == "interlocking":
        return _apply_hocket(
            treated_soprano, counter_subject, texture, budget, voice_count
        )
    else:
        # Default: polyphonic - just return soprano and bass independently
        return _apply_polyphonic(
            treated_soprano, counter_subject, budget, voice_count
        )


def _apply_polyphonic(
    treated_soprano: TimedMaterial,
    counter_subject: TimedMaterial,
    budget: Fraction,
    voice_count: int,
) -> tuple[TimedMaterial, ...]:
    """Apply polyphonic texture: independent voices."""
    soprano = TimedMaterial.repeat_to_budget(
        list(treated_soprano.pitches), list(treated_soprano.durations), budget
    )
    # Bass uses counter-subject, shifted down
    bass_pitches: list[Pitch] = []
    for p in counter_subject.pitches:
        if isinstance(p, FloatingNote):
            # Shift down by octave equivalent (7 degrees)
            from shared.pitch import wrap_degree
            bass_pitches.append(FloatingNote(wrap_degree(p.degree - 7)))
        else:
            bass_pitches.append(p)
    bass = TimedMaterial.repeat_to_budget(
        bass_pitches, list(counter_subject.durations), budget
    )
    if voice_count == 2:
        return soprano, bass
    elif voice_count == 3:
        # Middle voice placeholder - will be filled by inner_voice_gen
        middle = TimedMaterial((Rest(),), (budget,), budget)
        return soprano, middle, bass
    else:
        # 4 voices
        alto = TimedMaterial((Rest(),), (budget,), budget)
        tenor = TimedMaterial((Rest(),), (budget,), budget)
        return soprano, alto, tenor, bass


def _degree_to_semitone(degree: int, scale: tuple[int, ...] = MAJOR_SCALE) -> int:
    """Convert scale degree (1-7) to semitone offset."""
    return scale[(degree - 1) % 7]


def _interval_class(deg1: int, deg2: int, scale: tuple[int, ...] = MAJOR_SCALE) -> int:
    """Compute interval class (0-11) between two degrees."""
    s1 = _degree_to_semitone(deg1, scale)
    s2 = _degree_to_semitone(deg2, scale)
    return abs(s2 - s1) % 12


@dataclass
class InterleavedSlice:
    """A time slice with degrees for V1, V2, and bass."""
    offset: Fraction
    duration: Fraction
    v1_deg: int
    v2_deg: int
    bass_deg: int | None  # None if bass is a variable to optimize


def _solve_interleaved_bass(
    v1_slices: list[tuple[Fraction, Fraction, int]],  # (offset, duration, degree)
    v2_slices: list[tuple[Fraction, Fraction, int]],
    bass_offsets: list[Fraction],  # quarter-note grid
    root: int,
    cadence_start: Fraction,
    timeout_seconds: float = 5.0,
) -> Optional[list[int]]:
    """Solve for optimal bass line given fixed upper voices.

    Uses CP-SAT to find bass degrees that:
    - Avoid parallel 5ths/8ves with both upper voices
    - Maintain consonance on strong beats
    - Prefer stepwise motion
    - Approach cadence properly

    Args:
        v1_slices: V1 (offset, duration, degree) tuples
        v2_slices: V2 (offset, duration, degree) tuples
        bass_offsets: Quarter-note positions for bass
        root: Target root degree (1-7)
        cadence_start: Offset where cadence begins
        timeout_seconds: Solver time limit

    Returns:
        List of bass degrees, or None if infeasible
    """
    n_bass = len(bass_offsets)
    if n_bass == 0:
        return []

    model = cp_model.CpModel()
    quarter = Fraction(1, 4)

    # Build lookup: what V1/V2 degree sounds at each bass offset
    def degree_at_offset(slices: list[tuple[Fraction, Fraction, int]], offset: Fraction) -> int:
        """Find which degree is sounding at given offset."""
        for s_off, s_dur, s_deg in slices:
            if s_off <= offset < s_off + s_dur:
                return s_deg
        # Default to last degree if past end
        return slices[-1][2] if slices else 1

    v1_at_bass = [degree_at_offset(v1_slices, off) for off in bass_offsets]
    v2_at_bass = [degree_at_offset(v2_slices, off) for off in bass_offsets]

    # === VARIABLES ===
    # Bass degree at each position (1-7)
    bass_degs: list[cp_model.IntVar] = []
    for i in range(n_bass):
        d = model.NewIntVar(1, 7, f"bass_{i}")
        bass_degs.append(d)

    # === HARD CONSTRAINTS ===

    # H1: No parallel perfect intervals (5ths/8ves) with V1
    for i in range(1, n_bass):
        v1_prev = v1_at_bass[i - 1]
        v1_curr = v1_at_bass[i]
        v1_motion = _degree_to_semitone(v1_curr) - _degree_to_semitone(v1_prev)

        if v1_motion == 0:
            continue  # No motion in V1, no parallel possible

        for prev_d in range(1, 8):
            for curr_d in range(1, 8):
                bass_motion = _degree_to_semitone(curr_d) - _degree_to_semitone(prev_d)
                if bass_motion == 0:
                    continue

                # Check parallel motion to perfect interval
                same_dir = (bass_motion > 0) == (v1_motion > 0)
                ic_prev = _interval_class(v1_prev, prev_d)
                ic_curr = _interval_class(v1_curr, curr_d)

                if same_dir and ic_prev in PERFECT_INTERVALS and ic_curr in PERFECT_INTERVALS:
                    # Forbid this bass motion
                    is_prev = model.NewBoolVar(f"v1_pp_{i}_{prev_d}")
                    is_curr = model.NewBoolVar(f"v1_pc_{i}_{curr_d}")
                    model.Add(bass_degs[i - 1] == prev_d).OnlyEnforceIf(is_prev)
                    model.Add(bass_degs[i - 1] != prev_d).OnlyEnforceIf(is_prev.Not())
                    model.Add(bass_degs[i] == curr_d).OnlyEnforceIf(is_curr)
                    model.Add(bass_degs[i] != curr_d).OnlyEnforceIf(is_curr.Not())
                    model.AddBoolOr([is_prev.Not(), is_curr.Not()])

    # H2: No parallel perfect intervals with V2
    for i in range(1, n_bass):
        v2_prev = v2_at_bass[i - 1]
        v2_curr = v2_at_bass[i]
        v2_motion = _degree_to_semitone(v2_curr) - _degree_to_semitone(v2_prev)

        if v2_motion == 0:
            continue

        for prev_d in range(1, 8):
            for curr_d in range(1, 8):
                bass_motion = _degree_to_semitone(curr_d) - _degree_to_semitone(prev_d)
                if bass_motion == 0:
                    continue

                same_dir = (bass_motion > 0) == (v2_motion > 0)
                ic_prev = _interval_class(v2_prev, prev_d)
                ic_curr = _interval_class(v2_curr, curr_d)

                if same_dir and ic_prev in PERFECT_INTERVALS and ic_curr in PERFECT_INTERVALS:
                    is_prev = model.NewBoolVar(f"v2_pp_{i}_{prev_d}")
                    is_curr = model.NewBoolVar(f"v2_pc_{i}_{curr_d}")
                    model.Add(bass_degs[i - 1] == prev_d).OnlyEnforceIf(is_prev)
                    model.Add(bass_degs[i - 1] != prev_d).OnlyEnforceIf(is_prev.Not())
                    model.Add(bass_degs[i] == curr_d).OnlyEnforceIf(is_curr)
                    model.Add(bass_degs[i] != curr_d).OnlyEnforceIf(is_curr.Not())
                    model.AddBoolOr([is_prev.Not(), is_curr.Not()])

    # H3: Consonance with V1 on downbeats (beat 1 and 3)
    for i, off in enumerate(bass_offsets):
        beat_in_bar = (off % Fraction(1)) / quarter
        is_downbeat = beat_in_bar in (0, 2)
        if not is_downbeat:
            continue

        v1_deg = v1_at_bass[i]
        for bd in range(1, 8):
            ic = _interval_class(v1_deg, bd)
            if ic not in CONSONANCES:
                # Forbid dissonant bass on downbeat
                model.Add(bass_degs[i] != bd)

    # H4: Final bass note must be root
    model.Add(bass_degs[-1] == root)

    # === SOFT CONSTRAINTS (penalties) ===
    penalties: list[cp_model.LinearExpr] = []

    # S1: Prefer stepwise motion (penalize leaps > 2 semitones)
    for i in range(1, n_bass):
        for prev_d in range(1, 8):
            for curr_d in range(1, 8):
                motion = abs(_degree_to_semitone(curr_d) - _degree_to_semitone(prev_d))
                if motion <= 2:
                    continue  # Stepwise, no penalty

                is_move = model.NewBoolVar(f"leap_{i}_{prev_d}_{curr_d}")
                is_prev = model.NewBoolVar(f"lp_{i}_{prev_d}")
                is_curr = model.NewBoolVar(f"lc_{i}_{curr_d}")

                model.Add(bass_degs[i - 1] == prev_d).OnlyEnforceIf(is_prev)
                model.Add(bass_degs[i - 1] != prev_d).OnlyEnforceIf(is_prev.Not())
                model.Add(bass_degs[i] == curr_d).OnlyEnforceIf(is_curr)
                model.Add(bass_degs[i] != curr_d).OnlyEnforceIf(is_curr.Not())
                model.AddBoolAnd([is_prev, is_curr]).OnlyEnforceIf(is_move)
                model.AddBoolOr([is_prev.Not(), is_curr.Not()]).OnlyEnforceIf(is_move.Not())

                penalty = 10 if motion <= 4 else 30 if motion <= 7 else 100
                penalties.append(is_move * penalty)

    # S2: Prefer contrary motion to V1
    for i in range(1, n_bass):
        v1_motion = _degree_to_semitone(v1_at_bass[i]) - _degree_to_semitone(v1_at_bass[i - 1])
        if v1_motion == 0:
            continue

        for prev_d in range(1, 8):
            for curr_d in range(1, 8):
                bass_motion = _degree_to_semitone(curr_d) - _degree_to_semitone(prev_d)
                # Penalize parallel motion, reward contrary
                if bass_motion != 0 and (bass_motion > 0) == (v1_motion > 0):
                    # Parallel motion - small penalty
                    is_move = model.NewBoolVar(f"par_{i}_{prev_d}_{curr_d}")
                    is_prev = model.NewBoolVar(f"parp_{i}_{prev_d}")
                    is_curr = model.NewBoolVar(f"parc_{i}_{curr_d}")

                    model.Add(bass_degs[i - 1] == prev_d).OnlyEnforceIf(is_prev)
                    model.Add(bass_degs[i - 1] != prev_d).OnlyEnforceIf(is_prev.Not())
                    model.Add(bass_degs[i] == curr_d).OnlyEnforceIf(is_curr)
                    model.Add(bass_degs[i] != curr_d).OnlyEnforceIf(is_curr.Not())
                    model.AddBoolAnd([is_prev, is_curr]).OnlyEnforceIf(is_move)
                    model.AddBoolOr([is_prev.Not(), is_curr.Not()]).OnlyEnforceIf(is_move.Not())

                    penalties.append(is_move * 5)

    # S3: Cadence approach - penultimate should be step below root
    if n_bass >= 2:
        penult_idx = n_bass - 2
        # Prefer degree below root (root - 1)
        approach_deg = wrap_degree(root - 1)
        for d in range(1, 8):
            if d == approach_deg:
                continue
            is_d = model.NewBoolVar(f"cad_pen_{d}")
            model.Add(bass_degs[penult_idx] == d).OnlyEnforceIf(is_d)
            model.Add(bass_degs[penult_idx] != d).OnlyEnforceIf(is_d.Not())
            penalties.append(is_d * 20)

    # S4: Prefer root/fifth on bar downbeats
    for i, off in enumerate(bass_offsets):
        beat_in_bar = (off % Fraction(1)) / quarter
        if beat_in_bar != 0:  # Not beat 1
            continue

        for d in range(1, 8):
            if d in (root, wrap_degree(root + 4)):  # Root or fifth
                continue
            is_d = model.NewBoolVar(f"down_{i}_{d}")
            model.Add(bass_degs[i] == d).OnlyEnforceIf(is_d)
            model.Add(bass_degs[i] != d).OnlyEnforceIf(is_d.Not())
            penalties.append(is_d * 8)

    # === SOLVE ===
    if penalties:
        model.Minimize(cp_model.LinearExpr.Sum(penalties))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout_seconds
    solver.parameters.num_search_workers = 4

    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    return [solver.Value(d) for d in bass_degs]


def _solve_interleaved_cadence(
    v1_pre_deg: int,
    v2_pre_deg: int,
    bass_pre_deg: int,
    root: int,
    n_beats: int = 4,
    timeout_seconds: float = 2.0,
) -> Optional[tuple[list[int], list[int], list[int]]]:
    """Solve for optimal cadential voice-leading.

    Args:
        v1_pre_deg: V1 degree before cadence
        v2_pre_deg: V2 degree before cadence
        bass_pre_deg: Bass degree before cadence
        root: Target root degree
        n_beats: Number of beats in cadence
        timeout_seconds: Solver time limit

    Returns:
        Tuple of (v1_degs, v2_degs, bass_degs) or None if infeasible
    """
    model = cp_model.CpModel()

    # Variables for each voice at each beat
    v1_degs = [model.NewIntVar(1, 7, f"v1_{i}") for i in range(n_beats)]
    v2_degs = [model.NewIntVar(1, 7, f"v2_{i}") for i in range(n_beats)]
    bass_degs = [model.NewIntVar(1, 7, f"bass_{i}") for i in range(n_beats)]

    # === HARD CONSTRAINTS ===

    # H1: Final notes - V1 on root, V2 on third, bass on root
    model.Add(v1_degs[-1] == root)
    model.Add(v2_degs[-1] == wrap_degree(root + 2))  # Third
    model.Add(bass_degs[-1] == root)

    # H2: No parallel 5ths/8ves between any voice pair
    all_voices = [
        ("v1", v1_degs, [v1_pre_deg]),
        ("v2", v2_degs, [v2_pre_deg]),
        ("bass", bass_degs, [bass_pre_deg]),
    ]

    for idx, (name_a, degs_a, pre_a) in enumerate(all_voices):
        for name_b, degs_b, pre_b in all_voices[idx + 1:]:
            full_a = pre_a + [None] * n_beats  # None = variable
            full_b = pre_b + [None] * n_beats

            for i in range(n_beats):
                prev_a = pre_a[0] if i == 0 else None
                prev_b = pre_b[0] if i == 0 else None
                curr_a_var = degs_a[i]
                curr_b_var = degs_b[i]
                prev_a_var = degs_a[i - 1] if i > 0 else None

                # This gets complex - simplified version: forbid both voices
                # arriving at perfect interval via similar motion
                for pa in range(1, 8):
                    for pb in range(1, 8):
                        for ca in range(1, 8):
                            for cb in range(1, 8):
                                if i == 0:
                                    a_motion = _degree_to_semitone(ca) - _degree_to_semitone(prev_a)
                                    b_motion = _degree_to_semitone(cb) - _degree_to_semitone(prev_b)
                                else:
                                    a_motion = _degree_to_semitone(ca) - _degree_to_semitone(pa)
                                    b_motion = _degree_to_semitone(cb) - _degree_to_semitone(pb)

                                if a_motion == 0 or b_motion == 0:
                                    continue

                                same_dir = (a_motion > 0) == (b_motion > 0)
                                ic = _interval_class(ca, cb)

                                if same_dir and ic in PERFECT_INTERVALS:
                                    if i == 0:
                                        # First beat: check against pre-cadence
                                        ic_prev = _interval_class(prev_a, prev_b)
                                        if ic_prev in PERFECT_INTERVALS:
                                            # Both at perfect interval - forbid
                                            b_ca = model.NewBoolVar(f"cad_{name_a}{name_b}_{i}_{ca}")
                                            b_cb = model.NewBoolVar(f"cad_{name_a}{name_b}_{i}_{cb}")
                                            model.Add(curr_a_var == ca).OnlyEnforceIf(b_ca)
                                            model.Add(curr_a_var != ca).OnlyEnforceIf(b_ca.Not())
                                            model.Add(curr_b_var == cb).OnlyEnforceIf(b_cb)
                                            model.Add(curr_b_var != cb).OnlyEnforceIf(b_cb.Not())
                                            model.AddBoolOr([b_ca.Not(), b_cb.Not()])

    # H3: Consonance between V1 and V2 throughout
    for i in range(n_beats):
        for d1 in range(1, 8):
            for d2 in range(1, 8):
                ic = _interval_class(d1, d2)
                if ic in CONSONANCES:
                    continue
                # Dissonant - forbid this combination
                b1 = model.NewBoolVar(f"cons_v1_{i}_{d1}")
                b2 = model.NewBoolVar(f"cons_v2_{i}_{d2}")
                model.Add(v1_degs[i] == d1).OnlyEnforceIf(b1)
                model.Add(v1_degs[i] != d1).OnlyEnforceIf(b1.Not())
                model.Add(v2_degs[i] == d2).OnlyEnforceIf(b2)
                model.Add(v2_degs[i] != d2).OnlyEnforceIf(b2.Not())
                model.AddBoolOr([b1.Not(), b2.Not()])

    # === SOFT CONSTRAINTS ===
    penalties: list = []

    # S1: Prefer stepwise motion in all voices
    for degs, pre, name in [(v1_degs, v1_pre_deg, "v1"), (v2_degs, v2_pre_deg, "v2"), (bass_degs, bass_pre_deg, "bass")]:
        prev = pre
        for i, curr_var in enumerate(degs):
            for curr_d in range(1, 8):
                if i == 0:
                    motion = abs(_degree_to_semitone(curr_d) - _degree_to_semitone(prev))
                    if motion > 2:
                        b = model.NewBoolVar(f"step_{name}_{i}_{curr_d}")
                        model.Add(curr_var == curr_d).OnlyEnforceIf(b)
                        model.Add(curr_var != curr_d).OnlyEnforceIf(b.Not())
                        penalties.append(b * (15 if motion <= 4 else 40))

    # S2: Penultimate bass should approach root from below
    if n_beats >= 2:
        approach = wrap_degree(root - 1)
        for d in range(1, 8):
            if d == approach:
                continue
            b = model.NewBoolVar(f"bass_app_{d}")
            model.Add(bass_degs[-2] == d).OnlyEnforceIf(b)
            model.Add(bass_degs[-2] != d).OnlyEnforceIf(b.Not())
            penalties.append(b * 25)

    # === SOLVE ===
    if penalties:
        model.Minimize(cp_model.LinearExpr.Sum(penalties))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout_seconds

    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    return (
        [solver.Value(d) for d in v1_degs],
        [solver.Value(d) for d in v2_degs],
        [solver.Value(d) for d in bass_degs],
    )


def _apply_interleaved(
    treated_soprano: TimedMaterial,
    counter_subject: TimedMaterial,
    texture: TextureSpec,
    budget: Fraction,
    voice_count: int,
    tonal_target: str,
    bar_dur: Fraction,
) -> tuple[TimedMaterial, ...]:
    """Apply interleaved texture: invertible counterpoint.

    Uses CP-SAT optimization to find bass line and cadence that:
    - Avoid parallel 5ths/8ves with upper voices
    - Maintain consonance on strong beats
    - Prefer stepwise and contrary motion
    - Approach cadence properly

    Falls back to deterministic generation if solver fails.
    """
    from engine.expander_util import TONAL_ROOTS

    # Parse parameters
    swap_at_str = texture.parameters.get("swap_at", "1/2")
    swap_at_frac = Fraction(swap_at_str) if isinstance(swap_at_str, str) else Fraction(swap_at_str)
    swap_point = budget * swap_at_frac

    subj_pitches = list(treated_soprano.pitches)
    subj_durs = list(treated_soprano.durations)
    cs_pitches = list(counter_subject.pitches)
    cs_durs = list(counter_subject.durations)

    root: int = TONAL_ROOTS.get(tonal_target, 1)
    quarter = Fraction(1, 4)

    # Reserve last bar for cadence
    cadence_budget = bar_dur
    main_budget = budget - cadence_budget
    first_half_budget = swap_point
    second_half_budget = main_budget - first_half_budget
    cadence_start = main_budget

    # First half: V1 plays subject, V2 plays counter-subject
    v1_first = _sequential_repeat(subj_pitches, subj_durs, first_half_budget, transpose_step=0)
    v2_first = _sequential_repeat(cs_pitches, cs_durs, first_half_budget, transpose_step=0)

    # Second half (before cadence): swap material with sequential transposition
    v1_second = _sequential_repeat(cs_pitches, cs_durs, second_half_budget, transpose_step=-1)
    v2_second = _sequential_repeat(subj_pitches, subj_durs, second_half_budget, transpose_step=-1)

    # Build slices for V1 and V2 (for solver input)
    def material_to_slices(mat: TimedMaterial, start_offset: Fraction) -> list[tuple[Fraction, Fraction, int]]:
        """Convert TimedMaterial to (offset, duration, degree) tuples."""
        slices = []
        offset = start_offset
        for p, d in zip(mat.pitches, mat.durations):
            if isinstance(p, FloatingNote):
                slices.append((offset, d, p.degree))
            offset += d
        return slices

    v1_slices = material_to_slices(v1_first, Fraction(0))
    v1_slices.extend(material_to_slices(v1_second, first_half_budget))

    v2_slices = material_to_slices(v2_first, Fraction(0))
    v2_slices.extend(material_to_slices(v2_second, first_half_budget))

    # Get pre-cadence degrees for cadence solver
    v1_pre_deg = v1_slices[-1][2] if v1_slices else 1
    v2_pre_deg = v2_slices[-1][2] if v2_slices else 3

    # Generate bass positions (quarter-note grid for main section)
    bass_offsets = []
    pos = Fraction(0)
    while pos < main_budget:
        bass_offsets.append(pos)
        pos += quarter

    # === SOLVE FOR OPTIMAL BASS ===
    bass_degrees = _solve_interleaved_bass(
        v1_slices, v2_slices, bass_offsets, root, cadence_start
    )

    if bass_degrees is None:
        # Fallback to deterministic bass
        bass_degrees = _fallback_bass_degrees(len(bass_offsets), root)

    bass_pre_deg = bass_degrees[-1] if bass_degrees else root

    # === SOLVE FOR OPTIMAL CADENCE ===
    cadence_result = _solve_interleaved_cadence(
        v1_pre_deg, v2_pre_deg, bass_pre_deg, root, n_beats=4
    )

    if cadence_result:
        cad_v1_degs, cad_v2_degs, cad_bass_degs = cadence_result
    else:
        # Fallback cadence
        cad_v1_degs = [wrap_degree(root + 2), wrap_degree(root + 1), wrap_degree(root + 1), root]
        cad_v2_degs = [wrap_degree(root + 4), wrap_degree(root + 3), wrap_degree(root + 4), wrap_degree(root + 2)]
        cad_bass_degs = [root, wrap_degree(root - 1), wrap_degree(root + 1), root]

    # Build cadence pitches
    cad_v1_p = [FloatingNote(d) for d in cad_v1_degs]
    cad_v2_p = [FloatingNote(d) for d in cad_v2_degs]
    cad_bass_p = [FloatingNote(d) for d in cad_bass_degs]
    cad_durs = [quarter] * 4

    # Combine V1 and V2
    v1_pitches = list(v1_first.pitches) + list(v1_second.pitches) + cad_v1_p
    v1_durs = list(v1_first.durations) + list(v1_second.durations) + cad_durs
    voice1 = TimedMaterial(tuple(v1_pitches), tuple(v1_durs), budget)

    v2_pitches = list(v2_first.pitches) + list(v2_second.pitches) + cad_v2_p
    v2_durs = list(v2_first.durations) + list(v2_second.durations) + cad_durs
    voice2 = TimedMaterial(tuple(v2_pitches), tuple(v2_durs), budget)

    # Build bass from solved degrees
    bass_p = [FloatingNote(d) for d in bass_degrees] + cad_bass_p
    bass_d = [quarter] * len(bass_degrees) + cad_durs
    bass = TimedMaterial(tuple(bass_p), tuple(bass_d), budget)

    if voice_count == 2:
        return voice1, voice2
    else:
        return voice1, voice2, bass


def _fallback_bass_degrees(n: int, root: int) -> list[int]:
    """Generate fallback bass degrees when solver fails."""
    degrees = []
    for i in range(n):
        bar_idx = i // 4
        beat = i % 4
        if bar_idx % 2 == 0:
            # Ascending pattern
            degrees.append(wrap_degree(root + beat))
        else:
            # Descending pattern
            degrees.append(wrap_degree(root + 4 - beat))
    return degrees


def _sequential_repeat(
    pitches: list[Pitch],
    durations: list[Fraction],
    budget: Fraction,
    transpose_step: int,
) -> TimedMaterial:
    """Repeat material to budget with sequential transposition.

    Each complete repetition transposes by transpose_step degrees,
    creating baroque sequence effect.

    Args:
        pitches: Source pitches
        durations: Source durations
        budget: Target duration
        transpose_step: Degrees to transpose each repetition (0 = no transposition)
    """
    result_p: list[Pitch] = []
    result_d: list[Fraction] = []
    remaining = budget
    rep_count = 0
    idx = 0
    max_iter = 1000

    while remaining > Fraction(0) and idx < max_iter:
        src_idx = idx % len(pitches)
        p = pitches[src_idx]
        d = durations[src_idx]

        # Track repetition count for transposition
        if src_idx == 0 and idx > 0:
            rep_count += 1

        # Apply transposition
        if isinstance(p, FloatingNote) and transpose_step != 0:
            transposed_deg = wrap_degree(p.degree + (rep_count * transpose_step))
            p = FloatingNote(transposed_deg)

        use_d = min(d, remaining)
        result_p.append(p)
        result_d.append(use_d)
        remaining -= use_d
        idx += 1

    return TimedMaterial(tuple(result_p), tuple(result_d), budget)


def _generate_walking_bass(
    budget: Fraction,
    bar_dur: Fraction,
    root: int,
    tonal_target: str,
) -> TimedMaterial:
    """Generate baroque walking bass line.

    Creates quarter-note motion with:
    - Stepwise movement and occasional thirds
    - Harmonic rhythm following progression to tonal_target
    - V-I cadential formula in final bar
    - Octave leaps on bar downbeats for variety

    Args:
        budget: Total duration
        bar_dur: Duration of one bar
        root: Root degree of tonal target (1-7)
        tonal_target: Harmonic destination (I, V, vi, etc.)
    """
    bass_p: list[Pitch] = []
    bass_d: list[Fraction] = []

    quarter = Fraction(1, 4)
    remaining = budget
    beat_count = 0

    # Calculate total beats for position tracking
    total_beats = int(budget / quarter)
    cadence_beats = 4  # Reserve last bar (4 beats) for cadence

    while remaining > Fraction(0):
        is_cadence_zone = (total_beats - beat_count) <= cadence_beats

        if is_cadence_zone:
            # Cadential bar: quarter-note motion matching upper voices
            # Bass: root→step below→step above→target (e.g., 1→7→2→1 for I)
            cadence_beat = cadence_beats - (total_beats - beat_count)
            if cadence_beat == 0:
                bass_p.append(FloatingNote(wrap_degree(root)))  # start on target area
            elif cadence_beat == 1:
                bass_p.append(FloatingNote(wrap_degree(root - 1)))  # step below
            elif cadence_beat == 2:
                bass_p.append(FloatingNote(wrap_degree(root + 1)))  # step above
            else:
                bass_p.append(FloatingNote(wrap_degree(root)))  # arrive on target
            use_d = min(quarter, remaining)
            bass_d.append(use_d)
            remaining -= use_d
            beat_count += 1
            continue
        # Walking pattern based on position (non-cadential bars)
        use_d = min(quarter, remaining)
        bar_idx = beat_count // 4
        beat_in_bar = beat_count % 4
        bar_position = Fraction(bar_idx) / Fraction(max(1, (total_beats - cadence_beats) // 4))

        if bar_idx % 2 == 0:
            # Pattern A: ascending
            start_deg = _interpolate_degree(1, root, bar_position)
            offsets = [0, 1, 2, 1]
            bass_p.append(FloatingNote(wrap_degree(start_deg + offsets[beat_in_bar])))
        else:
            # Pattern B: descending
            start_deg = _interpolate_degree(5, root + 4, bar_position)
            offsets = [0, -1, -2, -1]
            bass_p.append(FloatingNote(wrap_degree(start_deg + offsets[beat_in_bar])))

        bass_d.append(use_d)
        remaining -= use_d
        beat_count += 1

    return TimedMaterial(tuple(bass_p), tuple(bass_d), budget)


def _interpolate_degree(start: int, end: int, position: Fraction) -> int:
    """Interpolate between two scale degrees based on position (0-1)."""
    # Normalize degrees to 1-7 range for interpolation
    start_norm = ((start - 1) % 7) + 1
    end_norm = ((end - 1) % 7) + 1

    # Linear interpolation
    diff = end_norm - start_norm
    result = start_norm + int(float(position) * diff)

    return wrap_degree(result)


def _apply_canon(
    treated_soprano: TimedMaterial,
    texture: TextureSpec,
    budget: Fraction,
    voice_count: int,
    tonal_target: str,
    bar_dur: Fraction,
) -> tuple[TimedMaterial, ...]:
    """Apply canon texture.

    Dux states material, comes imitates after delay with transformation.
    """
    from engine.expander_util import TONAL_ROOTS
    from shared.pitch import wrap_degree

    # Parse parameters
    offset_str = texture.parameters.get("offset", "1/2")
    offset = Fraction(offset_str) * bar_dur
    interval = texture.parameters.get("interval", -4)
    canon_type = texture.parameters.get("canon_type", "strict")

    # Dux: treated soprano repeated to budget
    dux = TimedMaterial.repeat_to_budget(
        list(treated_soprano.pitches), list(treated_soprano.durations), budget
    )

    # Comes: transform dux according to canon_type, then offset
    comes_pitches: list[Pitch] = []
    for p in treated_soprano.pitches:
        if isinstance(p, FloatingNote):
            if canon_type == "strict":
                # Transpose by interval
                comes_pitches.append(FloatingNote(wrap_degree(p.degree + interval)))
            elif canon_type == "inversion":
                # Invert around axis 4, then transpose
                inverted = wrap_degree(2 * 4 - p.degree)
                comes_pitches.append(FloatingNote(wrap_degree(inverted + interval)))
            elif canon_type == "retrograde":
                # Handle retrograde separately below
                comes_pitches.append(p)
            else:
                comes_pitches.append(FloatingNote(wrap_degree(p.degree + interval)))
        else:
            comes_pitches.append(p)

    comes_durs = list(treated_soprano.durations)
    if canon_type == "retrograde":
        comes_pitches = list(reversed(comes_pitches))
        comes_durs = list(reversed(comes_durs))
        # Apply interval transposition
        comes_pitches = [
            FloatingNote(wrap_degree(p.degree + interval)) if isinstance(p, FloatingNote) else p
            for p in comes_pitches
        ]
    elif canon_type == "augmentation":
        comes_durs = [d * 2 for d in comes_durs]
    elif canon_type == "diminution":
        comes_durs = [max(d // 2, Fraction(1, 16)) for d in comes_durs]

    # Add offset rest before comes
    c_p: list[Pitch] = [Rest()]
    c_d: list[Fraction] = [offset]
    c_remaining = budget - offset

    idx = 0
    max_iter = 1000
    while c_remaining > Fraction(0) and idx < max_iter:
        p = comes_pitches[idx % len(comes_pitches)]
        d = comes_durs[idx % len(comes_durs)]
        use_d = min(d, c_remaining)
        c_p.append(p)
        c_d.append(use_d)
        c_remaining -= use_d
        idx += 1
    comes = TimedMaterial(tuple(c_p), tuple(c_d), budget)

    # Bass: simple harmonic support
    root: int = TONAL_ROOTS.get(tonal_target, 1)
    bass = TimedMaterial.repeat_to_budget(
        [FloatingNote(root), FloatingNote(5)],
        [Fraction(1, 2), Fraction(1, 2)],
        budget
    )

    if voice_count == 2:
        return dux, comes
    else:
        return dux, comes, bass


def _apply_hocket(
    treated_soprano: TimedMaterial,
    counter_subject: TimedMaterial,
    texture: TextureSpec,
    budget: Fraction,
    voice_count: int,
) -> tuple[TimedMaterial, ...]:
    """Apply hocket texture: interlocking voices with gaps.

    Voices alternate, filling each other's rests.
    """
    # Split treated soprano into alternating segments
    sop_pitches = list(treated_soprano.pitches)
    sop_durs = list(treated_soprano.durations)

    v1_p: list[Pitch] = []
    v1_d: list[Fraction] = []
    v2_p: list[Pitch] = []
    v2_d: list[Fraction] = []

    for i, (p, d) in enumerate(zip(sop_pitches, sop_durs)):
        if i % 2 == 0:
            v1_p.append(p)
            v1_d.append(d)
            v2_p.append(Rest())
            v2_d.append(d)
        else:
            v1_p.append(Rest())
            v1_d.append(d)
            v2_p.append(p)
            v2_d.append(d)

    voice1 = TimedMaterial.repeat_to_budget(v1_p, v1_d, budget)
    voice2 = TimedMaterial.repeat_to_budget(v2_p, v2_d, budget)

    if voice_count == 2:
        return voice1, voice2
    else:
        # Bass from counter-subject
        bass = TimedMaterial.repeat_to_budget(
            list(counter_subject.pitches), list(counter_subject.durations), budget
        )
        return voice1, voice2, bass
