"""Thematic transformation utilities.

Extract interval patterns from subjects and countersubjects, and apply
baroque motivic transformations: inversion, retrograde, diminution,
augmentation, and transposition.

Depends only on shared.key, shared.pitch, shared.constants, and
motifs.head_generator.  No Viterbi, no Note objects, no phrase plans.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING

from motifs.head_generator import degrees_to_midi
from shared.constants import VALID_DURATIONS_SORTED, exact_fraction
from shared.key import Key
from shared.pitch import build_pitch_class_set, diatonic_step_count

if TYPE_CHECKING:
    from motifs.fragen import Cell


@dataclass(frozen=True)
class IntervalPattern:
    """Ordered interval pattern extracted from a melodic line.

    intervals: sequence of (signed_diatonic_step, duration) pairs, one per
        note after the first.  Positive step = ascending, negative = descending,
        0 = repeated note.  Duration is the target note's own duration.
    start_duration: duration of the first note (has no preceding interval).
    """
    intervals: tuple[tuple[int, Fraction], ...]
    start_duration: Fraction


@dataclass(frozen=True)
class TransformedCell:
    """One cell with one specific transformation applied."""
    cell_name: str
    source_family: str      # "subject" or "cs"
    transform_name: str     # "identity", "invert", "retrograde", "diminish", "augment"
    pattern: IntervalPattern
    total_duration: Fraction


@dataclass(frozen=True)
class CellCatalogue:
    """Pre-computed transformation catalogue for all motivic cells."""
    subject_cells: tuple[TransformedCell, ...]
    cs_cells: tuple[TransformedCell, ...]
    all_cells: tuple[TransformedCell, ...]


@dataclass(frozen=True)
class VerticalGenome:
    """Beat-by-beat vertical interval profile from the exposition.

    entries: tuple of (normalised_position, abs_diatonic_interval) pairs,
        sorted by position. Position is 0.0 at the start of the overlap,
        1.0 at the end. Interval is the absolute diatonic distance between
        the two voices (0 = unison, 1 = second, 2 = third, etc.).
    """
    entries: tuple[tuple[float, int], ...]


def augment(pattern: IntervalPattern) -> IntervalPattern:
    """Double every duration.  Intervals unchanged.

    Durations that double to a value outside VALID_DURATIONS are clamped
    to the nearest valid duration (L006).
    """
    new_start: Fraction = _nearest_valid_duration(dur=pattern.start_duration * 2)
    new_intervals: tuple[tuple[int, Fraction], ...] = tuple(
        (step, _nearest_valid_duration(dur=dur * 2))
        for step, dur in pattern.intervals
    )
    return IntervalPattern(intervals=new_intervals, start_duration=new_start)


def diminish(pattern: IntervalPattern) -> IntervalPattern:
    """Halve every duration.  Intervals unchanged.

    Durations that halve to a value outside VALID_DURATIONS are clamped
    to the nearest valid duration (L006).
    """
    new_start: Fraction = _nearest_valid_duration(dur=pattern.start_duration / 2)
    new_intervals: tuple[tuple[int, Fraction], ...] = tuple(
        (step, _nearest_valid_duration(dur=dur / 2))
        for step, dur in pattern.intervals
    )
    return IntervalPattern(intervals=new_intervals, start_duration=new_start)


def extract_interval_pattern(
    degrees: tuple[int, ...],
    durations: tuple[float, ...],
    tonic_midi: int,
    mode: str,
) -> IntervalPattern:
    """Extract ordered interval pattern from a melodic line.

    Args:
        degrees: Scale degree indices (0-indexed, as stored in LoadedSubject).
            Degree 0 = tonic at octave 0, degree 7 = tonic an octave higher, etc.
        durations: Note durations as floats (whole-note fractions).
        tonic_midi: MIDI pitch of the tonic note used for degree-to-MIDI mapping.
        mode: "major" or "minor".

    Returns:
        IntervalPattern with len(degrees)-1 signed diatonic intervals.
    """
    assert len(degrees) >= 2, (
        f"Need at least 2 notes to extract an interval pattern, got {len(degrees)}. "
        f"Ensure the subject/countersubject has at least 2 notes."
    )
    assert len(degrees) == len(durations), (
        f"degrees and durations must have the same length: "
        f"got {len(degrees)} degrees vs {len(durations)} durations. "
        f"Fix the fugue file so both sequences have equal length."
    )
    midi_pitches: tuple[int, ...] = degrees_to_midi(
        degrees=degrees, tonic_midi=tonic_midi, mode=mode,
    )
    tonic_pc: int = tonic_midi % 12
    pcs: frozenset[int] = build_pitch_class_set(tonic_pc=tonic_pc, mode=mode)
    frac_durations: tuple[Fraction, ...] = tuple(
        exact_fraction(value=d, label=f"duration[{i}]") for i, d in enumerate(durations)
    )
    intervals: list[tuple[int, Fraction]] = []
    for i in range(len(degrees) - 1):
        a: int = midi_pitches[i]
        b: int = midi_pitches[i + 1]
        direction: int = 1 if b > a else (-1 if b < a else 0)
        step_count: int = diatonic_step_count(pitch_a=a, pitch_b=b, pitch_class_set=pcs)
        signed_interval: int = direction * step_count
        intervals.append((signed_interval, frac_durations[i + 1]))
    return IntervalPattern(
        intervals=tuple(intervals),
        start_duration=frac_durations[0],
    )


def invert(pattern: IntervalPattern) -> IntervalPattern:
    """Negate every interval sign.  Durations unchanged.

    Diatonic inversion: (+2, 1/4) becomes (-2, 1/4).  This is standard
    baroque practice (diatonic, not tonal inversion).
    """
    new_intervals: tuple[tuple[int, Fraction], ...] = tuple(
        (-step, dur) for step, dur in pattern.intervals
    )
    return IntervalPattern(intervals=new_intervals, start_duration=pattern.start_duration)


def realise_pattern(
    pattern: IntervalPattern,
    start_degree: int,
    key: Key,
    octave: int,
) -> tuple[tuple[int, Fraction], ...]:
    """Realise an interval pattern as (midi_pitch, duration) pairs.

    Walks the diatonic scale from start_degree, applying each signed step
    in turn.  Stays diatonic throughout (no chromatic alterations).

    Args:
        pattern: Interval pattern to realise.
        start_degree: Starting scale degree (1-7, 1-indexed).
        key: Musical key for degree-to-MIDI conversion.
        octave: Octave number for the starting note (e.g. 4 for middle octave).

    Returns:
        Tuple of (midi_pitch, duration) pairs, one per note.
    """
    assert 1 <= start_degree <= 7, (
        f"start_degree must be 1-7, got {start_degree}. "
        f"Scale degrees are 1-indexed."
    )
    current_midi: int = key.degree_to_midi(degree=start_degree, octave=octave)
    result: list[tuple[int, Fraction]] = [(current_midi, pattern.start_duration)]
    for signed_step, duration in pattern.intervals:
        current_midi = key.diatonic_step(midi=current_midi, steps=signed_step)
        result.append((current_midi, duration))
    return tuple(result)


def retrograde(pattern: IntervalPattern) -> IntervalPattern:
    """Reverse the note sequence.

    Reversing note order negates every interval's direction.
    start_duration becomes the last note's original duration;
    the original start_duration becomes the last entry's duration.
    """
    all_durations: list[Fraction] = [pattern.start_duration] + [
        dur for _, dur in pattern.intervals
    ]
    rev_durations: list[Fraction] = list(reversed(all_durations))
    rev_steps: list[int] = [-(step) for step, _ in reversed(pattern.intervals)]
    new_intervals: tuple[tuple[int, Fraction], ...] = tuple(
        (step, dur) for step, dur in zip(rev_steps, rev_durations[1:])
    )
    return IntervalPattern(intervals=new_intervals, start_duration=rev_durations[0])


def transpose(pattern: IntervalPattern) -> IntervalPattern:
    """Identity transformation (no-op).

    Transposition is achieved at realisation time by choosing a different
    start_degree in realise_pattern.  This function exists for API
    completeness so all five transforms can be applied uniformly.
    """
    return pattern


def nearest_degree_for_midi(target_midi: int, key: Key) -> tuple[int, int]:
    """Return (degree, octave) whose key.degree_to_midi is closest to target_midi.

    Searches degrees 1-7 across octaves 3-6.
    """
    best_degree: int = 1
    best_octave: int = 4
    best_dist: int = 10000
    for octave in range(3, 7):
        for degree in range(1, 8):
            midi: int = key.degree_to_midi(degree=degree, octave=octave)
            dist: int = abs(midi - target_midi)
            if dist < best_dist:
                best_dist = dist
                best_degree = degree
                best_octave = octave
    return (best_degree, best_octave)


def build_thematic_knots(
    pattern: IntervalPattern,
    start_degree: int,
    key: Key,
    octave: int,
    start_offset: Fraction,
    range_low: int,
    range_high: int,
    max_offset: Fraction | None = None,
) -> "list[Knot]":
    """Realise pattern as a list of structural Knots.

    Walks the pattern from (start_degree, octave) in key.  Accumulates
    absolute offsets from start_offset.  Each realised pitch is
    range-checked: if outside [range_low, range_high] a single ±12 shift
    is attempted; if still out, the knot is skipped.

    Args:
        pattern: Interval pattern to realise.
        start_degree: Starting scale degree (1-7).
        key: Local musical key.
        octave: Starting octave number.
        start_offset: Absolute beat offset of the first knot.
        range_low: Minimum MIDI pitch (inclusive).
        range_high: Maximum MIDI pitch (inclusive).

    Returns:
        List of Knot objects at realised positions.
    """
    from viterbi.mtypes import Knot
    realised: tuple[tuple[int, Fraction], ...] = realise_pattern(
        pattern=pattern,
        start_degree=start_degree,
        key=key,
        octave=octave,
    )
    knots: list[Knot] = []
    offset: Fraction = start_offset
    for midi, duration in realised:
        # Stop producing knots at or past the phrase boundary
        if max_offset is not None and offset >= max_offset:
            break
        # Range check: try one octave shift if needed
        if midi < range_low:
            midi += 12
        elif midi > range_high:
            midi -= 12
        if range_low <= midi <= range_high:
            knots.append(Knot(beat=float(offset), midi_pitch=midi))
        offset += duration
    return knots


def cell_to_pattern(cell: Cell) -> IntervalPattern:
    """Convert a fragen Cell to an IntervalPattern.

    Cell.degrees are relative diatonic offsets (first note = 0).
    IntervalPattern.intervals are successive signed diatonic steps.
    """
    assert len(cell.degrees) >= 2, (
        f"Cell '{cell.name}' must have at least 2 degrees to convert to "
        f"IntervalPattern, got {len(cell.degrees)}. Fix the cell extraction."
    )
    assert len(cell.degrees) == len(cell.durations), (
        f"Cell '{cell.name}' degrees ({len(cell.degrees)}) and durations "
        f"({len(cell.durations)}) must have equal length. Fix the cell."
    )
    intervals: tuple[tuple[int, Fraction], ...] = tuple(
        (cell.degrees[i + 1] - cell.degrees[i], cell.durations[i + 1])
        for i in range(len(cell.degrees) - 1)
    )
    return IntervalPattern(intervals=intervals, start_duration=cell.durations[0])


def build_cell_catalogue(
    cells: list[Cell],
    bar_length: Fraction,
) -> CellCatalogue:
    """Build transformation catalogue from fragen cells.

    For each cell, computes its IntervalPattern and applies all five
    baroque transformations.  Transforms whose total_duration exceeds
    2 * bar_length are discarded (too long for a single free-run cell).
    """
    assert bar_length > Fraction(0), (
        f"bar_length must be positive, got {bar_length}. "
        f"Fix the metre string passed to build_cell_catalogue."
    )
    max_duration: Fraction = bar_length * 2
    subject_cells: list[TransformedCell] = []
    cs_cells: list[TransformedCell] = []

    for cell in cells:
        base_pattern: IntervalPattern = cell_to_pattern(cell)
        family: str = _source_family(cell.source)
        for transform_name, transformed in (
            ("identity", transpose(base_pattern)),
            ("invert", invert(base_pattern)),
            ("retrograde", retrograde(base_pattern)),
            ("diminish", diminish(base_pattern)),
            ("augment", augment(base_pattern)),
        ):
            total_dur: Fraction = _pattern_total_duration(transformed)
            if total_dur > max_duration:
                continue
            tc = TransformedCell(
                cell_name=cell.name,
                source_family=family,
                transform_name=transform_name,
                pattern=transformed,
                total_duration=total_dur,
            )
            if family == "cs":
                cs_cells.append(tc)
            else:
                subject_cells.append(tc)

    all_cells: tuple[TransformedCell, ...] = tuple(subject_cells) + tuple(cs_cells)
    return CellCatalogue(
        subject_cells=tuple(subject_cells),
        cs_cells=tuple(cs_cells),
        all_cells=all_cells,
    )


_ZONE_TRANSFORMS: dict[int, tuple[str, ...]] = {
    0: ("identity",),
    1: ("invert", "retrograde"),
    2: ("diminish",),
}


def sequence_cell_knots(
    catalogue: CellCatalogue,
    span_duration: Fraction,
    prefer_family: str,
    start_midi: int,
    key: Key,
    start_offset: Fraction,
    range_low: int,
    range_high: int,
    max_offset: Fraction,
    seed: int = 0,
) -> "list[Knot]":
    """Chain motivic cells end-to-end to fill span_duration.

    Selects cells from catalogue for pitch continuity and family alternation.
    Zone-based transform selection creates a phrase arc (stable → exploratory
    → intensified).

    Args:
        catalogue: Pre-computed cell transformation catalogue.
        span_duration: Total duration to fill.
        prefer_family: "subject" or "cs" — preferred motivic family.
        start_midi: MIDI pitch of the last note before this span.
        key: Local musical key.
        start_offset: Absolute beat offset of the first knot.
        range_low: Minimum MIDI pitch (inclusive).
        range_high: Maximum MIDI pitch (inclusive).
        max_offset: Absolute beat offset limit (knots at or past this are dropped).
        seed: Deterministic tie-break seed (use run_counter for companions, 100/200 for tails).

    Returns:
        List of Knot objects.
    """
    from viterbi.mtypes import Knot

    if not catalogue.all_cells:
        return []

    result: list[Knot] = []
    remaining: Fraction = span_duration
    current_midi: int = start_midi
    current_offset: Fraction = start_offset
    last_family: str = ""
    last_cell_name: str = ""
    iteration: int = 0

    while remaining > Fraction(0):
        if iteration > 50:
            break

        # a. Compute zone (0=opening, 1=middle, 2=cadential)
        raw_progress: Fraction = (current_offset - start_offset) / span_duration
        progress: float = float(max(Fraction(0), min(Fraction(1), raw_progress)))
        zone: int = 0 if progress < 0.25 else (2 if progress >= 0.75 else 1)

        # b. Build candidate pool: cells whose total_duration fits remaining
        pool: list[TransformedCell] = [
            tc for tc in catalogue.all_cells if tc.total_duration <= remaining
        ]

        # c. Pool empty — Viterbi fills the rest
        if not pool:
            break

        # d. Zone filter (soft preference: restore full pool if zone empties it)
        zone_filtered: list[TransformedCell] = [
            tc for tc in pool if tc.transform_name in _ZONE_TRANSFORMS[zone]
        ]
        if zone_filtered:
            pool = zone_filtered

        # e. Family alternation filter (soft: prefer other family)
        other_family_pool: list[TransformedCell] = [
            tc for tc in pool if tc.source_family != last_family
        ]
        if other_family_pool:
            pool = other_family_pool

        # f. Cell-name filter: avoid immediate literal repetition
        name_filtered: list[TransformedCell] = [
            tc for tc in pool if tc.cell_name != last_cell_name
        ]
        if name_filtered:
            pool = name_filtered

        # g. Score by pitch continuity: find nearest diatonic degree to current_midi,
        #    realise each candidate, measure distance of its first pitch from current_midi.
        start_degree: int
        start_octave: int
        start_degree, start_octave = nearest_degree_for_midi(target_midi=current_midi, key=key)

        def _score(
            tc: TransformedCell,
            _pool: list[TransformedCell] = pool,
            _sd: int = start_degree,
            _so: int = start_octave,
            _cm: int = current_midi,
            _pf: str = prefer_family,
            _seed: int = seed,
            _it: int = iteration,
        ) -> tuple[int, int, int]:
            realised: tuple[tuple[int, Fraction], ...] = realise_pattern(
                pattern=tc.pattern,
                start_degree=_sd,
                key=key,
                octave=_so,
            )
            pitch_dist: int = abs(realised[0][0] - _cm)
            family_match: int = 0 if tc.source_family == _pf else 1
            tiebreak: int = (_pool.index(tc) + _seed + _it) % max(1, len(_pool))
            return (pitch_dist, family_match, tiebreak)

        chosen: TransformedCell = min(pool, key=_score)

        # h. Build knots from the chosen cell
        chosen_degree: int
        chosen_octave: int
        chosen_degree, chosen_octave = nearest_degree_for_midi(target_midi=current_midi, key=key)
        new_knots: list[Knot] = build_thematic_knots(
            pattern=chosen.pattern,
            start_degree=chosen_degree,
            key=key,
            octave=chosen_octave,
            start_offset=current_offset,
            range_low=range_low,
            range_high=range_high,
            max_offset=max_offset,
        )
        result.extend(new_knots)

        # i. Update tracking
        if new_knots:
            current_midi = new_knots[-1].midi_pitch
        current_offset += chosen.total_duration
        remaining -= chosen.total_duration
        last_family = chosen.source_family
        last_cell_name = chosen.cell_name
        iteration += 1

    return result


def _pattern_total_duration(pattern: IntervalPattern) -> Fraction:
    """Sum of all note durations in an IntervalPattern."""
    return pattern.start_duration + sum(dur for _, dur in pattern.intervals)


def _source_family(source: str) -> str:
    """Classify a Cell source string as 'cs' or 'subject'."""
    if source.startswith("cs"):
        return "cs"
    return "subject"


def _nearest_valid_duration(dur: Fraction) -> Fraction:
    """Return the nearest duration in VALID_DURATIONS_SORTED to dur."""
    return min(VALID_DURATIONS_SORTED, key=lambda v: abs(v - dur))
