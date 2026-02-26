"""Pitch generation engine for baroque fugue subjects.

Replaces head_enumerator + cpsat_generator + validator.
Produces list[_ScoredPitch] matching the existing interface.

Algorithm (baroque_melody.md section 7):
  1. Select harmonic rhythm level from cell tick means
  2. Iterate stock progressions for that level
  3. Build C/P grid from cell patterns + boundary rule
  4. Enumerate C-slot skeletons (chord tones, pruned)
  5. Fill P-slots deterministically (stepwise, melodic minor)
  6. Validate complete sequences
  7. Classify contour and return as _ScoredPitch
"""
import logging
from dataclasses import dataclass

from motifs.subject_gen.constants import (
    ALLOWED_FINALS,
    DEGREES_PER_OCTAVE,
    MAX_FILL_LEAP,
    MAX_LARGE_LEAPS,
    MAX_PITCH_FREQ,
    MAX_SAME_SIGN_RUN,
    MIN_STEP_FRACTION,
    PITCH_HI,
    PITCH_LO,
    RANGE_HI,
    RANGE_LO,
)
from motifs.subject_gen.contour import _derive_shape_name
from motifs.subject_gen.harmonic_grid import (
    DIR_ASCENDING,
    DIR_DESCENDING,
    MODE_MINOR,
    RAISABLE_DEGREES,
    chord_at_tick,
    chord_tones,
    degree_to_semitone,
    get_progressions,
    is_cross_relation,
    is_raised_chord_degree,
    minor_equivalent,
    select_harmonic_level,
    should_raise,
)
from motifs.subject_gen.models import _ScoredPitch
from motifs.subject_gen.rhythm_cells import Cell
from shared.pitch import degrees_to_intervals

logger: logging.Logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Maximum diatonic interval between adjacent C-slots (a 5th = 4 steps).
MAX_CSLOT_INTERVAL: int = 4

# Maximum direct leap between adjacent C-slots with no P-slot between them.
MAX_DIRECT_LEAP: int = 2

# Tritone in semitones.
_TRITONE_SEMITONES: int = 6

# =============================================================================
# C/P pattern table (A001: data, not if-chains)
# =============================================================================

CP_PATTERNS: dict[str, tuple[str, ...]] = {
    "longa": ("C",),
    "pyrrhic": ("P", "P"),
    "iamb": ("P", "C"),
    "spondee": ("C", "C"),
    "trochee": ("C", "P"),
    "dotted": ("C", "P"),
    "snap": ("P", "C"),
    "tribrach": ("P", "P", "P"),
    "dactyl": ("C", "P", "P"),
    "amphibrach": ("P", "C", "P"),
    "anapaest": ("P", "P", "C"),
    "tirata": ("P", "P", "P", "P"),
}


# =============================================================================
# Data structures
# =============================================================================

@dataclass(frozen=True)
class NoteSlot:
    """Per-note grid entry with harmonic context."""

    index: int          # position in note sequence
    slot_type: str      # "C" or "P"
    chord: str          # active chord name (e.g. "I", "V", "iv")
    tick_offset: int    # ticks from bar 0


# =============================================================================
# Functions (alphabetical)
# =============================================================================

def _apply_melodic_minor(
    pitches: list[int | None],
    grid: tuple[NoteSlot, ...],
) -> None:
    """Placeholder for melodic minor raising.

    Raising is a chromatic alteration that does not change the diatonic
    degree value.  The raised flag is computed on-the-fly during
    validation by _is_raised_at, based on fill direction context.
    """


def _build_cp_grid(
    cell_sequence: tuple[Cell, ...],
    progression: tuple[str, ...],
    bar_ticks: int,
    n_bars: int,
) -> tuple[NoteSlot, ...]:
    """Assign C/P type, active chord, and tick offset to each note position.

    Applies boundary rule: first and last notes forced to C.
    """
    assert len(cell_sequence) > 0, "cell_sequence must not be empty"

    # Flatten cell patterns into slot types.
    raw_types: list[str] = []
    for cell in cell_sequence:
        pattern: tuple[str, ...] = CP_PATTERNS[cell.name]
        assert len(pattern) == cell.notes, (
            f"CP pattern length {len(pattern)} != cell notes {cell.notes} "
            f"for cell {cell.name!r}"
        )
        raw_types.extend(pattern)

    # Flatten tick durations.
    all_ticks: list[int] = []
    for cell in cell_sequence:
        all_ticks.extend(cell.ticks)

    assert len(raw_types) == len(all_ticks), (
        f"slot count {len(raw_types)} != tick count {len(all_ticks)}"
    )

    n_notes: int = len(raw_types)
    assert n_notes >= 2, f"need at least 2 notes, got {n_notes}"

    # Boundary rule: first and last forced to C.
    slot_types: list[str] = list(raw_types)
    slot_types[0] = "C"
    slot_types[-1] = "C"

    # Compute cumulative tick offsets.
    tick_offsets: list[int] = [0] * n_notes
    running: int = 0
    for i in range(n_notes):
        tick_offsets[i] = running
        running += all_ticks[i]

    # Build NoteSlot for each position.
    slots: list[NoteSlot] = []
    for i in range(n_notes):
        chord: str = chord_at_tick(
            progression=progression,
            tick_offset=tick_offsets[i],
            bar_ticks=bar_ticks,
            n_bars=n_bars,
        )
        slots.append(NoteSlot(
            index=i,
            slot_type=slot_types[i],
            chord=chord,
            tick_offset=tick_offsets[i],
        ))

    return tuple(slots)


def _classify_and_wrap(
    pitches: tuple[int, ...],
) -> _ScoredPitch:
    """Compute intervals, classify shape, wrap as _ScoredPitch."""
    ivs: tuple[int, ...] = degrees_to_intervals(degrees=pitches)
    shape: str = _derive_shape_name(list(pitches))
    return _ScoredPitch(
        score=0.0,
        ivs=ivs,
        degrees=pitches,
        shape=shape,
    )


def _enumerate_skeletons(
    grid: tuple[NoteSlot, ...],
    mode: str,
) -> list[tuple[int, ...]]:
    """Enumerate valid C-slot pitch combinations with early pruning.

    Returns list of tuples, each containing one pitch per C-slot.
    """
    c_slots: list[NoteSlot] = [s for s in grid if s.slot_type == "C"]
    n_c: int = len(c_slots)
    assert n_c >= 2, f"need at least 2 C-slots, got {n_c}"

    # Pre-compute valid pitches per C-slot.
    choices_per_slot: list[tuple[int, ...]] = []
    for slot in c_slots:
        pitches: tuple[int, ...] = _expand_chord_tones_in_range(
            mode=mode,
            chord=slot.chord,
        )
        choices_per_slot.append(pitches)

    results: list[tuple[int, ...]] = []
    partial: list[int] = []

    # Count P-slots between each adjacent C-slot pair.
    c_positions: list[int] = [s.index for s in grid if s.slot_type == "C"]
    p_counts_between: list[int] = []
    for i in range(n_c - 1):
        pos_a: int = c_positions[i]
        pos_b: int = c_positions[i + 1]
        p_cnt: int = pos_b - pos_a - 1
        p_counts_between.append(p_cnt)

    # Max gap per adjacent C-slot pair.  When p_count == 0 the two
    # C-slots are adjacent and the leap must be small.  Otherwise the
    # P-slots fill stepwise toward the target; any residual becomes a
    # leap at the C-slot boundary, capped at MAX_FILL_LEAP.
    max_gap_per_pair: list[int] = []
    for p_cnt in p_counts_between:
        if p_cnt == 0:
            max_gap_per_pair.append(MAX_DIRECT_LEAP)
        else:
            max_gap_per_pair.append(min(MAX_CSLOT_INTERVAL, p_cnt + MAX_FILL_LEAP))

    # Track pitch frequency in the skeleton to prune early.
    skeleton_freq: dict[int, int] = {}

    def _recurse(depth: int, running_min: int, running_max: int) -> None:
        if depth == n_c:
            # Range check.
            total_range: int = running_max - running_min
            if total_range < RANGE_LO:
                return
            if total_range > RANGE_HI:
                return
            results.append(tuple(partial))
            return

        for pitch in choices_per_slot[depth]:
            # Terminal degree constraints.
            deg_mod7: int = pitch % DEGREES_PER_OCTAVE
            if depth == 0 and deg_mod7 not in ALLOWED_FINALS:
                continue
            if depth == n_c - 1 and deg_mod7 not in ALLOWED_FINALS:
                continue

            # Skeleton-level pitch frequency: if this pitch already
            # appears MAX_PITCH_FREQ times in the skeleton, the filled
            # sequence will exceed the limit.
            if skeleton_freq.get(pitch, 0) >= MAX_PITCH_FREQ:
                continue

            # Adjacent C-slot interval constraint (tightened by P-count).
            if depth > 0:
                prev: int = partial[-1]
                interval: int = abs(pitch - prev)
                if interval > max_gap_per_pair[depth - 1]:
                    continue
                # Same-pitch rule:
                # - 0 P-slots between: ban (no neighbour figure possible)
                # - 1 P-slot: allow (neighbour figure, 2 occurrences)
                # - 2+ P-slots: ban (fill creates 3+ occurrences,
                #   exceeding MAX_PITCH_FREQ)
                if pitch == prev:
                    p_between: int = p_counts_between[depth - 1]
                    if p_between != 1:
                        continue

            new_min: int = min(running_min, pitch)
            new_max: int = max(running_max, pitch)

            # Early range pruning: if already too wide, skip.
            if new_max - new_min > RANGE_HI:
                continue

            partial.append(pitch)
            skeleton_freq[pitch] = skeleton_freq.get(pitch, 0) + 1
            _recurse(
                depth=depth + 1,
                running_min=new_min,
                running_max=new_max,
            )
            partial.pop()
            skeleton_freq[pitch] -= 1
            if skeleton_freq[pitch] == 0:
                del skeleton_freq[pitch]

    _recurse(depth=0, running_min=PITCH_HI, running_max=PITCH_LO)
    return results


def _expand_chord_tones_in_range(
    mode: str,
    chord: str,
) -> tuple[int, ...]:
    """Return all pitches (diatonic degree integers) within PITCH_LO..PITCH_HI
    that are chord tones for the given chord in the given mode."""
    base_degrees: frozenset[int] = chord_tones(mode=mode, chord=chord)
    result: list[int] = []
    for base_deg in base_degrees:
        for octave in range(-2, 3):
            pitch: int = octave * DEGREES_PER_OCTAVE + base_deg
            if PITCH_LO <= pitch <= PITCH_HI:
                result.append(pitch)
    result.sort()
    return tuple(result)


def _fill_p_slots(
    grid: tuple[NoteSlot, ...],
    skeleton: tuple[int, ...],
    mode: str,
) -> tuple[int, ...] | None:
    """Fill P-slots between C-slot anchors with stepwise motion.

    Returns the complete pitch sequence (one pitch per grid slot),
    or None if the skeleton cannot be filled (gap too large).
    """
    n_notes: int = len(grid)
    pitches: list[int | None] = [None] * n_notes

    # Place C-slot pitches from skeleton.
    c_idx: int = 0
    for i in range(n_notes):
        if grid[i].slot_type == "C":
            pitches[i] = skeleton[c_idx]
            c_idx += 1

    # Identify runs of P-slots between C-slot anchors.
    c_positions: list[int] = [i for i in range(n_notes) if grid[i].slot_type == "C"]

    for seg in range(len(c_positions) - 1):
        lo_pos: int = c_positions[seg]
        hi_pos: int = c_positions[seg + 1]
        p_count: int = hi_pos - lo_pos - 1
        anchor_lo_pitch: int = pitches[lo_pos]  # type: ignore[assignment]
        anchor_hi_pitch: int = pitches[hi_pos]  # type: ignore[assignment]
        gap: int = anchor_hi_pitch - anchor_lo_pitch

        if p_count == 0:
            # Adjacent C-slots, no P between them.
            if abs(gap) > MAX_DIRECT_LEAP:
                return None
            continue

        abs_gap: int = abs(gap)

        if abs_gap >= p_count:
            # Stepwise fill toward target; any residual is a leap at
            # the C-slot boundary.
            residual: int = abs_gap - p_count
            if residual > MAX_FILL_LEAP:
                return None
            step: int = 1 if gap > 0 else -1
            for j in range(1, p_count + 1):
                pitches[lo_pos + j] = anchor_lo_pitch + j * step
        else:
            # Surplus P-slots: need neighbour-tone detour.
            filled: list[int] | None = _fill_with_detour(
                anchor_start=anchor_lo_pitch,
                anchor_end=anchor_hi_pitch,
                p_count=p_count,
                grid=grid,
                start_pos=lo_pos,
                mode=mode,
            )
            if filled is None:
                return None
            for j in range(p_count):
                pitches[lo_pos + 1 + j] = filled[j]

    # Apply melodic minor raising for P-slots in minor mode.
    if mode == MODE_MINOR:
        _apply_melodic_minor(pitches=pitches, grid=grid)

    # Safety: all slots must be filled.
    assert all(p is not None for p in pitches), (
        "unfilled slots remain after P-slot fill"
    )
    return tuple(pitches)  # type: ignore[arg-type]


def _fill_with_detour(
    anchor_start: int,
    anchor_end: int,
    p_count: int,
    grid: tuple[NoteSlot, ...],
    start_pos: int,
    mode: str,
) -> list[int] | None:
    """Fill P-slots with a neighbour-tone detour when surplus notes exist.

    Proxy rule: prefer upper neighbour for notes on even tick offsets,
    lower on odd.
    """
    gap: int = anchor_end - anchor_start
    abs_gap: int = abs(gap)

    if gap == 0:
        # Same pitch, all P-slots must form neighbour figure(s).
        if p_count == 1:
            tick: int = grid[start_pos + 1].tick_offset
            direction: int = 1 if tick % 2 == 0 else -1
            return [anchor_start + direction]
        # Larger same-pitch gaps: alternating neighbour/return.
        result: list[int] = []
        for j in range(p_count):
            tick_j: int = grid[start_pos + 1 + j].tick_offset
            nb: int = 1 if tick_j % 2 == 0 else -1
            if j % 2 == 0:
                result.append(anchor_start + nb)
            else:
                result.append(anchor_start)
        return result

    # Non-zero gap with surplus.
    main_dir: int = 1 if gap > 0 else -1
    path: list[int] = []
    current_pitch: int = anchor_start
    steps_remaining: int = abs_gap
    slots_remaining: int = p_count
    detour_budget: int = p_count - abs_gap

    for j in range(p_count):
        slots_remaining -= 1

        if detour_budget > 0 and steps_remaining <= slots_remaining:
            # Insert detour: step based on tick parity.
            tick_k: int = grid[start_pos + 1 + j].tick_offset
            nb_direction: int = 1 if tick_k % 2 == 0 else -1
            current_pitch = current_pitch + nb_direction
            path.append(current_pitch)
            detour_budget -= 1
        else:
            # Normal step toward anchor_end.
            current_pitch = current_pitch + main_dir
            path.append(current_pitch)
            steps_remaining -= 1

    # Verify we arrived close to anchor_end.
    if abs(path[-1] - anchor_end) > 1:
        return None

    return path


def _is_raised_at(
    pitches: tuple[int, ...],
    idx: int,
    grid: tuple[NoteSlot, ...],
    mode: str,
) -> bool:
    """Determine if the pitch at idx should use the raised form.

    In minor mode:
    - C-slot under chord V with degree mod 7 in {5, 6}: raised.
    - P-slot ascending through degrees 5 or 6: raised (melodic minor).
    - Otherwise: natural.
    """
    if mode != MODE_MINOR:
        return False

    deg_mod7: int = pitches[idx] % DEGREES_PER_OCTAVE
    if deg_mod7 not in RAISABLE_DEGREES:
        return False

    slot: NoteSlot = grid[idx]

    # C-slot: only raised if chord requires it.
    if slot.slot_type == "C":
        return is_raised_chord_degree(
            mode=mode,
            chord=slot.chord,
            degree=pitches[idx],
        )

    # P-slot: determine direction from surrounding C-slot anchors.
    prev_c: int | None = None
    next_c: int | None = None
    for j in range(idx - 1, -1, -1):
        if grid[j].slot_type == "C":
            prev_c = j
            break
    for j in range(idx + 1, len(grid)):
        if grid[j].slot_type == "C":
            next_c = j
            break

    if prev_c is None or next_c is None:
        return False

    direction: str = DIR_ASCENDING if pitches[next_c] > pitches[prev_c] else DIR_DESCENDING
    return should_raise(degree_mod7=deg_mod7, direction=direction)


def _sign(x: int) -> int:
    """Return -1, 0, or 1."""
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def _validate_sequence(
    pitches: tuple[int, ...],
    grid: tuple[NoteSlot, ...],
    mode: str,
) -> bool:
    """Apply all validation checks from baroque_melody.md section 6.

    Returns True if the sequence passes all checks.
    """
    n: int = len(pitches)
    assert n == len(grid), (
        f"pitches length {n} != grid length {len(grid)}"
    )

    # 6.1 Range.
    pitch_range: int = max(pitches) - min(pitches)
    if pitch_range < RANGE_LO:
        return False
    if pitch_range > RANGE_HI:
        return False

    # 6.4 Terminal degrees.
    if pitches[0] % DEGREES_PER_OCTAVE not in ALLOWED_FINALS:
        return False
    if pitches[-1] % DEGREES_PER_OCTAVE not in ALLOWED_FINALS:
        return False
    # 6.4b No consecutive repeated pitches anywhere.
    for i in range(n - 1):
        if pitches[i] == pitches[i + 1]:
            return False

    # 6.5 Repeated pitches: no exact pitch > MAX_PITCH_FREQ times.
    freq: dict[int, int] = {}
    for p in pitches:
        freq[p] = freq.get(p, 0) + 1
        if freq[p] > MAX_PITCH_FREQ:
            return False

    # 6.6 Monotonic runs.
    if n > 1:
        same_dir_count: int = 1
        for i in range(2, n):
            prev_dir: int = _sign(pitches[i - 1] - pitches[i - 2])
            curr_dir: int = _sign(pitches[i] - pitches[i - 1])
            if curr_dir != 0 and curr_dir == prev_dir:
                same_dir_count += 1
                if same_dir_count > MAX_SAME_SIGN_RUN:
                    return False
            else:
                same_dir_count = 1

    # 6.7 Large leap limit.
    intervals: tuple[int, ...] = tuple(
        pitches[i + 1] - pitches[i] for i in range(n - 1)
    )
    large_leap_count: int = sum(1 for iv in intervals if abs(iv) >= 4)
    if large_leap_count > MAX_LARGE_LEAPS:
        return False
    # 6.8 Step fraction: most motion should be stepwise (up to thirds).
    step_count: int = sum(1 for iv in intervals if abs(iv) <= 2)
    if n > 1 and step_count / (n - 1) < MIN_STEP_FRACTION:
        return False
    # 6.2 Forbidden intervals (tritone between adjacent notes).
    for i in range(n - 1):
        raised_a: bool = _is_raised_at(
            pitches=pitches, idx=i, grid=grid, mode=mode,
        )
        raised_b: bool = _is_raised_at(
            pitches=pitches, idx=i + 1, grid=grid, mode=mode,
        )
        semi_a: int = degree_to_semitone(
            degree=pitches[i], mode=mode, raised=raised_a,
        )
        semi_b: int = degree_to_semitone(
            degree=pitches[i + 1], mode=mode, raised=raised_b,
        )
        interval_semi: int = abs(semi_b - semi_a)
        if interval_semi == _TRITONE_SEMITONES:
            return False

    # 6.3 Cross-relations at chord boundaries.
    for i in range(n - 1):
        if grid[i].chord != grid[i + 1].chord:
            raised_a = _is_raised_at(
                pitches=pitches, idx=i, grid=grid, mode=mode,
            )
            raised_b = _is_raised_at(
                pitches=pitches, idx=i + 1, grid=grid, mode=mode,
            )
            if is_cross_relation(
                degree_a=pitches[i],
                degree_b=pitches[i + 1],
                raised_a=raised_a,
                raised_b=raised_b,
            ):
                return False

    return True


def generate_pitched_subjects(
    cell_sequence: tuple[Cell, ...],
    mode: str,
    tonic_midi: int,
    n_bars: int,
    bar_ticks: int,
) -> list[_ScoredPitch]:
    """Generate pitched subject candidates from a cell sequence.

    Steps 1-7 of the baroque melody generation algorithm.
    """
    assert len(cell_sequence) > 0, "cell_sequence must not be empty"
    assert mode in ("major", "minor"), f"mode must be 'major' or 'minor', got {mode!r}"
    assert n_bars > 0, f"n_bars must be > 0, got {n_bars}"
    assert bar_ticks > 0, f"bar_ticks must be > 0, got {bar_ticks}"

    # Step 1: Determine harmonic rhythm level.
    all_ticks: list[int] = []
    for cell in cell_sequence:
        all_ticks.extend(cell.ticks)
    level: str = select_harmonic_level(cell_ticks=tuple(all_ticks))

    # Step 2: Get progressions for this level.
    progressions: tuple[tuple[str, ...], ...] = get_progressions(level=level)

    results: list[_ScoredPitch] = []
    seen_degrees: set[tuple[int, ...]] = set()

    for raw_prog in progressions:
        # Apply minor equivalents if needed.
        if mode == MODE_MINOR:
            prog: tuple[str, ...] = tuple(
                minor_equivalent(major_chord=ch) for ch in raw_prog
            )
        else:
            prog = raw_prog

        # Step 3: Build C/P grid.
        grid: tuple[NoteSlot, ...] = _build_cp_grid(
            cell_sequence=cell_sequence,
            progression=prog,
            bar_ticks=bar_ticks,
            n_bars=n_bars,
        )

        # Step 4: Enumerate C-slot skeletons.
        skeletons: list[tuple[int, ...]] = _enumerate_skeletons(
            grid=grid,
            mode=mode,
        )

        for skeleton in skeletons:
            # Step 5: Fill P-slots.
            filled: tuple[int, ...] | None = _fill_p_slots(
                grid=grid,
                skeleton=skeleton,
                mode=mode,
            )
            if filled is None:
                continue

            # Step 6: Validate.
            if not _validate_sequence(
                pitches=filled,
                grid=grid,
                mode=mode,
            ):
                continue

            # Deduplicate.
            if filled in seen_degrees:
                continue
            seen_degrees.add(filled)

            # Step 7: Classify and wrap.
            results.append(_classify_and_wrap(pitches=filled))

    logger.info(
        "generate_pitched_subjects: mode=%s level=%s progressions=%d "
        "results=%d",
        mode, level, len(progressions), len(results),
    )
    return results
