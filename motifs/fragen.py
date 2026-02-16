"""FRAGEN — Fragment Episode Generator.

Extracts motivic cells from fugue subjects and builds two-voice episode
textures by pairing leader and follower cells with consonance checking.
Realises fragments as sequenced note events for MIDI output.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from typing import NamedTuple

from builder.types import Note as BuilderNote
from motifs.fragment_catalogue import extract_head, extract_tail
from motifs.fugue_loader import LoadedFugue
from motifs.head_generator import degrees_to_midi
from shared.constants import (
    CONSONANT_INTERVALS_ABOVE_BASS,
    CROSS_RELATION_PAIRS,
    PERFECT_INTERVALS,
    STEP_SEMITONES,
    STRONG_BEAT_OFFSETS,
    TRACK_BASS,
    TRACK_SOPRANO,
    VOICE_RANGES,
)
from shared.key import Key

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

VOICE_BASS: int = 1
VOICE_SOPRANO: int = 0

# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

_FOLLOWER_OFFSETS: tuple[Fraction, ...] = (
    Fraction(0),
    Fraction(1, 8),
    Fraction(1, 4),
)
_HOLD_CONSONANCE: float = 1.0
_MAX_BOUNDARY_LEAP: int = 3         # max degree steps at cell join
_MAX_NONTERMINAL_FINAL: Fraction = Fraction(3, 16)  # longest final note in a non-terminal cell
_MAX_CHAIN_CELLS: int = 3           # max cells per bar in a chain
_MAX_CHAINS: int = 500              # cap on chain enumeration
_MAX_SCORED_CHAINS: int = 200       # keep top N chains after boundary scoring
_MIN_CELL_NOTES: int = 2            # sub-sequence minimum length
_MIN_CHAIN_CELL_DUR: Fraction = Fraction(1, 8)  # shortest cell in a chain
_MIN_CONSONANCE: float = 0.8
_MIN_HOLD_CELL_FRAC: int = 4       # cell must fill >= 1/4 bar for hold
_MIN_HOLD_SEPARATION: int = 5      # semitones between held and running voice
_MIN_RANGE_MARGIN: int = 3         # semitones from range edge to qualify for proximity selection
_MIN_VOICE_SEPARATION: int = 5     # semitones: bass must not approach soprano
_REF_UPPER_BASE: int = 7           # reference upper start for consonance check
_METRE_FROM_BAR_LENGTH: dict[Fraction, str] = {
    Fraction(1): "4/4",
    Fraction(3, 4): "3/4",
}
_RHYTHMIC_CONTRAST: int = 2        # min ratio of avg note durations
_SEPARATION_RANGE: range = range(5, 15)  # degree separation upper minus lower
_START_SEARCH: range = range(-3, 16)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class Note(NamedTuple):
    """Single note event in a realised episode."""
    offset: Fraction
    degree: int
    duration: Fraction
    voice: int


@dataclass(frozen=True)
class Cell:
    """Motivic cell: contiguous sub-sequence of subject or its inversion."""
    name: str
    degrees: tuple[int, ...]
    durations: tuple[Fraction, ...]
    total_duration: Fraction
    source: str


@dataclass(frozen=True)
class Fragment:
    """Two-voice episode texture, unique under transposition."""
    upper: Cell
    lower: Cell
    leader_voice: int
    separation: int
    offset: Fraction


# ---------------------------------------------------------------------------
# Cell extraction (alphabetical: public then private)
# ---------------------------------------------------------------------------


def extract_cells(
    fugue: LoadedFugue,
    bar_length: Fraction,
) -> list[Cell]:
    """Extract motivic cells as contiguous sub-sequences from subject material."""
    head = extract_head(fugue=fugue, bar_length=bar_length)
    tail = extract_tail(fugue=fugue, bar_length=bar_length)
    raw: list[Cell] = []
    sources: list[tuple[str, tuple[int, ...], tuple]] = [
        ("head", head.degrees, head.durations),
        ("tail", tail.degrees, tail.durations),
        ("answer", fugue.answer.degrees, fugue.answer.durations),
        ("cs", fugue.countersubject.degrees, fugue.countersubject.durations),
    ]
    for source, degrees, durs_raw in sources:
        durs: tuple[Fraction, ...] = tuple(
            Fraction(d).limit_denominator(64) for d in durs_raw
        )
        raw.extend(_subsequence_cells(
            degrees=degrees,
            durations=durs,
            source=source,
        ))
    inverted: list[Cell] = [_invert(c) for c in raw]
    return _dedup_cells(raw + inverted)


def _dedup_cells(cells: list[Cell]) -> list[Cell]:
    """Remove cells with identical (degrees, durations)."""
    seen: set[tuple[tuple[int, ...], tuple[Fraction, ...]]] = set()
    result: list[Cell] = []
    for c in cells:
        key = (c.degrees, c.durations)
        if key not in seen:
            seen.add(key)
            result.append(c)
    return result


def _invert(cell: Cell) -> Cell:
    """Diatonic inversion around first degree."""
    inv_source: str = cell.source + "_inv"
    return Cell(
        name=cell.name.replace(cell.source, inv_source),
        degrees=tuple(-d for d in cell.degrees),
        durations=cell.durations,
        total_duration=cell.total_duration,
        source=inv_source,
    )


def _subsequence_cells(
    degrees: tuple[int, ...],
    durations: tuple[Fraction, ...],
    source: str,
) -> list[Cell]:
    """Extract every contiguous sub-sequence of 2+ notes."""
    n: int = len(degrees)
    cells: list[Cell] = []
    for start in range(n):
        for end in range(start + _MIN_CELL_NOTES, n + 1):
            sub_deg: tuple[int, ...] = degrees[start:end]
            sub_dur: tuple[Fraction, ...] = durations[start:end]
            base: int = sub_deg[0]
            relative: tuple[int, ...] = tuple(d - base for d in sub_deg)
            total: Fraction = sum(sub_dur)
            if end - start == n and start == 0:
                tag: str = source
            else:
                tag = f"{source}[{start}:{end}]"
            cells.append(Cell(
                name=tag,
                degrees=relative,
                durations=sub_dur,
                total_duration=total,
                source=source,
            ))
    return cells


# ---------------------------------------------------------------------------
# Chain building
# ---------------------------------------------------------------------------


def build_chains(
    cells: list[Cell],
    bar_length: Fraction,
) -> list[Cell]:
    """Assemble sub-bar cells into bar-filling chains."""
    eligible: list[Cell] = [
        c for c in cells
        if c.total_duration >= _MIN_CHAIN_CELL_DUR
        and c.total_duration <= bar_length
    ]
    eligible.sort(key=lambda c: c.total_duration, reverse=True)
    combos: list[list[Cell]] = []
    _find_chain_combos(
        cells=eligible,
        remaining=bar_length,
        current=[],
        results=combos,
    )
    raw: list[Cell] = []
    penalties: list[int] = []
    for combo in combos:
        if len(combo) == 1:
            raw.append(combo[0])
            penalties.append(0)
        else:
            raw.append(_chain_to_cell(combo))
            penalties.append(_chain_boundary_penalty(combo))
    # Sort by ascending penalty, keep top _MAX_SCORED_CHAINS
    sorted_pairs: list[tuple[int, Cell]] = sorted(
        zip(penalties, raw), key=lambda p: p[0],
    )
    capped: list[Cell] = [c for _, c in sorted_pairs[:_MAX_SCORED_CHAINS]]
    return _dedup_chains(capped)


def _contour(degrees: tuple[int, ...]) -> int:
    """Net contour direction: -1 descending, 0 flat, +1 ascending."""
    net: int = degrees[-1] - degrees[0]
    if net > 0:
        return 1
    if net < 0:
        return -1
    return 0


def _dedup_chains(cells: list[Cell]) -> list[Cell]:
    """Dedup chains by rhythm profile + contour direction (spec 2c)."""
    seen: set[tuple[tuple[Fraction, ...], int]] = set()
    result: list[Cell] = []
    for c in cells:
        key: tuple = (c.durations, _contour(c.degrees))
        if key not in seen:
            seen.add(key)
            result.append(c)
    return result


def _chain_boundary_penalty(chain: list[Cell]) -> int:
    """Penalise boundary leaps and non-terminal cells with long final notes."""
    penalty: int = 0
    for i in range(len(chain) - 1):
        last_deg: int = chain[i].degrees[-1]
        first_deg: int = chain[i + 1].degrees[0]
        if abs(last_deg - first_deg) > _MAX_BOUNDARY_LEAP:
            penalty += 1
        # Stall penalty: closing gesture used mid-chain
        if chain[i].durations[-1] > _MAX_NONTERMINAL_FINAL:
            penalty += 10
    return penalty


def _chain_to_cell(chain: list[Cell]) -> Cell:
    """Convert a sequence of cells into a single composite cell."""
    assert len(chain) >= 2, "Chain must have at least 2 cells"
    degrees: list[int] = []
    durations: list[Fraction] = []
    for i, cell in enumerate(chain):
        offset: int = degrees[-1] if i > 0 else 0
        for deg in cell.degrees:
            degrees.append(offset + deg)
        durations.extend(cell.durations)
    base: int = degrees[0]
    normalised: tuple[int, ...] = tuple(d - base for d in degrees)
    names: str = "+".join(c.name for c in chain)
    return Cell(
        name=f"chain({names})",
        degrees=normalised,
        durations=tuple(durations),
        total_duration=sum(durations),
        source="chain",
    )


def _find_chain_combos(
    cells: list[Cell],
    remaining: Fraction,
    current: list[Cell],
    results: list[list[Cell]],
) -> None:
    """Recursively find cell sequences summing to bar_length."""
    if remaining == Fraction(0):
        results.append(list(current))
        return
    if len(current) >= _MAX_CHAIN_CELLS:
        return
    if len(results) >= _MAX_CHAINS:
        return
    for cell in cells:
        if cell.total_duration > remaining:
            continue
        current.append(cell)
        _find_chain_combos(
            cells=cells,
            remaining=remaining - cell.total_duration,
            current=current,
            results=results,
        )
        current.pop()
        if len(results) >= _MAX_CHAINS:
            return


# ---------------------------------------------------------------------------
# Consonance checking
# ---------------------------------------------------------------------------


def _avg_duration(cell: Cell) -> Fraction:
    """Average note duration of a cell."""
    return cell.total_duration / len(cell.degrees)


def _degree_at(
    cell: Cell,
    t: Fraction,
) -> int:
    """Return the degree sounding at time t within a cell."""
    onset: Fraction = Fraction(0)
    result: int = cell.degrees[0]
    for deg, dur in zip(cell.degrees, cell.durations):
        if onset > t:
            break
        result = deg
        onset += dur
    return result


def _consonance_score(
    upper: Cell,
    lower: Cell,
    separation: int,
    offset: Fraction,
    bar_length: Fraction,
    tonic_midi: int,
    mode: str,
) -> float:
    """Check consonance at crotchet grid with parallel-perfect and cross-relation rejection.

    Returns consonance_rate (consonant strong beats / total strong beats),
    or 0.0 if voices cross, parallel perfects, or cross-relations detected.
    """
    upper_base: int = _REF_UPPER_BASE
    lower_base: int = upper_base - separation
    model_dur: Fraction = max(
        upper.total_duration,
        lower.total_duration + offset,
    )
    # Crotchet grid: bar_length / 4 gives one check per crotchet beat
    beat_unit: Fraction = bar_length / 4
    assert beat_unit > 0, f"beat_unit must be positive, got bar_length={bar_length}"

    # Determine strong beat offsets within a bar
    metre: str = _METRE_FROM_BAR_LENGTH.get(bar_length, "4/4")
    strong_offsets: tuple[Fraction, ...] = STRONG_BEAT_OFFSETS.get(
        metre, (Fraction(0),),
    )

    # Collect all check points and their pitches
    check_points: list[tuple[Fraction, int, int, bool]] = []  # (t, u_midi, l_midi, is_strong)
    t: Fraction = Fraction(0)
    while t < model_dur:
        follower_t: Fraction = t - offset
        if follower_t < Fraction(0) or follower_t >= lower.total_duration:
            t += beat_unit
            continue
        u_deg: int = upper_base + _degree_at(cell=upper, t=t)
        l_deg: int = lower_base + _degree_at(cell=lower, t=follower_t)
        u_midi: int = degrees_to_midi((u_deg,), tonic_midi, mode)[0]
        l_midi: int = degrees_to_midi((l_deg,), tonic_midi, mode)[0]

        # Voice crossing / approach check
        if u_midi - l_midi < _MIN_VOICE_SEPARATION:
            return 0.0

        # Determine if this is a strong beat (offset within bar)
        bar_offset: Fraction = t % bar_length
        is_strong: bool = bar_offset in strong_offsets

        check_points.append((t, u_midi, l_midi, is_strong))
        t += beat_unit

    if not check_points:
        return 0.0

    # Cross-relation check: within each check point and between consecutive
    for i, (_, u_midi, l_midi, _) in enumerate(check_points):
        u_pc: int = u_midi % 12
        l_pc: int = l_midi % 12
        pair: tuple[int, int] = (min(u_pc, l_pc), max(u_pc, l_pc))
        if pair in CROSS_RELATION_PAIRS:
            return 0.0
        # Check cross-relation between this and previous check point
        if i > 0:
            _, prev_u, prev_l, _ = check_points[i - 1]
            for cur, prev in ((u_pc, prev_l % 12), (l_pc, prev_u % 12)):
                xr: tuple[int, int] = (min(cur, prev), max(cur, prev))
                if xr in CROSS_RELATION_PAIRS:
                    return 0.0

    # Parallel perfect check: consecutive strong beats
    prev_strong: tuple[int, int] | None = None
    for _, u_midi, l_midi, is_strong in check_points:
        if not is_strong:
            continue
        iv: int = (u_midi - l_midi) % 12
        if prev_strong is not None:
            prev_iv: int = (prev_strong[0] - prev_strong[1]) % 12
            if iv == prev_iv and iv in PERFECT_INTERVALS:
                # Check similar motion (both voices moved same direction)
                u_motion: int = u_midi - prev_strong[0]
                l_motion: int = l_midi - prev_strong[1]
                if u_motion != 0 and l_motion != 0:
                    if (u_motion > 0) == (l_motion > 0):
                        return 0.0
        prev_strong = (u_midi, l_midi)

    # Consonance scoring on strong beats with weak-beat passing-tone tolerance
    consonant: int = 0
    total_strong: int = 0
    for i, (_, u_midi, l_midi, is_strong) in enumerate(check_points):
        iv = (u_midi - l_midi) % 12
        if is_strong:
            total_strong += 1
            if iv in CONSONANT_INTERVALS_ABOVE_BASS:
                consonant += 1
        else:
            # Weak beat: tolerate dissonance only if step-approached and step-left
            if iv not in CONSONANT_INTERVALS_ABOVE_BASS:
                # Check both voices for passing-tone condition
                passed: bool = False
                if i > 0 and i < len(check_points) - 1:
                    _, prev_u, prev_l, _ = check_points[i - 1]
                    _, next_u, next_l, _ = check_points[i + 1]
                    # Upper voice dissonant — check step approach/leave
                    u_approach: int = abs(u_midi - prev_u)
                    u_leave: int = abs(next_u - u_midi)
                    # Lower voice dissonant — check step approach/leave
                    l_approach: int = abs(l_midi - prev_l)
                    l_leave: int = abs(next_l - l_midi)
                    # At least one voice must be passing through by step
                    if ((u_approach <= STEP_SEMITONES and u_leave <= STEP_SEMITONES) or
                            (l_approach <= STEP_SEMITONES and l_leave <= STEP_SEMITONES)):
                        passed = True
                if not passed:
                    # Unprepared weak-beat dissonance — count against strong-beat score
                    total_strong += 1

    if total_strong == 0:
        return 0.0
    return consonant / total_strong


# ---------------------------------------------------------------------------
# Fragment building
# ---------------------------------------------------------------------------


def build_fragments(
    cells: list[Cell],
    tonic_midi: int,
    mode: str,
    bar_length: Fraction,
) -> list[Fragment]:
    """Build consonant two-voice episode textures from cell pairs."""
    fragments: list[Fragment] = []
    for leader, follower in product(cells, repeat=2):
        if leader is follower:
            continue
        leader_avg: Fraction = _avg_duration(leader)
        follower_avg: Fraction = _avg_duration(follower)
        if follower_avg < _RHYTHMIC_CONTRAST * leader_avg:
            continue
        for voice in (VOICE_SOPRANO, VOICE_BASS):
            upper: Cell = leader if voice == VOICE_SOPRANO else follower
            lower: Cell = follower if voice == VOICE_SOPRANO else leader
            for offset in _FOLLOWER_OFFSETS:
                if voice == VOICE_SOPRANO:
                    if upper.total_duration < lower.total_duration + offset:
                        continue
                else:
                    if lower.total_duration + offset < upper.total_duration:
                        continue
                for sep in _SEPARATION_RANGE:
                    rate: float = _consonance_score(
                        upper=upper,
                        lower=lower,
                        separation=sep,
                        offset=offset,
                        bar_length=bar_length,
                        tonic_midi=tonic_midi,
                        mode=mode,
                    )
                    if rate < _MIN_CONSONANCE:
                        continue
                    fragments.append(Fragment(
                        upper=upper,
                        lower=lower,
                        leader_voice=voice,
                        separation=sep,
                        offset=offset,
                    ))
                    break  # first valid separation for this combo
    return fragments


def build_hold_fragments(
    cells: list[Cell],
    tonic_midi: int,
    mode: str,
    bar_length: Fraction,
) -> list[Fragment]:
    """Build hold-exchange textures: running cell over single held note."""
    fragments: list[Fragment] = []
    min_dur: Fraction = bar_length / _MIN_HOLD_CELL_FRAC
    for cell in cells:
        if cell.total_duration < min_dur:
            continue
        hold: Cell = Cell(
            name="hold",
            degrees=(0,),
            durations=(cell.total_duration,),
            total_duration=cell.total_duration,
            source="hold",
        )
        for voice in (VOICE_SOPRANO, VOICE_BASS):
            upper: Cell = cell if voice == VOICE_SOPRANO else hold
            lower: Cell = hold if voice == VOICE_SOPRANO else cell
            for sep in _SEPARATION_RANGE:
                rate: float = _consonance_score(
                    upper=upper,
                    lower=lower,
                    separation=sep,
                    offset=Fraction(0),
                    bar_length=bar_length,
                    tonic_midi=tonic_midi,
                    mode=mode,
                )
                if rate < _HOLD_CONSONANCE:
                    continue
                u_midi: int = degrees_to_midi(
                    (_REF_UPPER_BASE,), tonic_midi, mode,
                )[0]
                l_midi: int = degrees_to_midi(
                    (_REF_UPPER_BASE - sep,), tonic_midi, mode,
                )[0]
                if u_midi - l_midi < _MIN_HOLD_SEPARATION:
                    continue
                fragments.append(Fragment(
                    upper=upper,
                    lower=lower,
                    leader_voice=voice,
                    separation=sep,
                    offset=Fraction(0),
                ))
                break  # first valid separation for this combo
    return fragments


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def dedup_fragments(fragments: list[Fragment]) -> list[Fragment]:
    """Remove duplicates: quantised leader rhythm + leader voice (spec 4b)."""
    seen: set[tuple] = set()
    unique: list[Fragment] = []
    for f in fragments:
        leader: Cell = (
            f.upper if f.leader_voice == VOICE_SOPRANO else f.lower
        )
        key: tuple = (
            _rhythm_class(leader.durations),
            f.leader_voice,
        )
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def _rhythm_class(durations: tuple[Fraction, ...]) -> tuple[int, ...]:
    """Quantise durations to density bins for perceptual dedup."""
    result: list[int] = []
    for d in durations:
        if d <= Fraction(1, 16):
            result.append(1)
        elif d <= Fraction(1, 8):
            result.append(2)
        elif d <= Fraction(1, 4):
            result.append(3)
        else:
            result.append(4)
    return tuple(result)


def _intervals(degrees: tuple[int, ...]) -> tuple[int, ...]:
    """Successive interval differences; transposition-invariant."""
    return tuple(degrees[i + 1] - degrees[i] for i in range(len(degrees) - 1))


# ---------------------------------------------------------------------------
# Realisation
# ---------------------------------------------------------------------------


def realise(
    fragment: Fragment,
    n_bars: int,
    step: int,
    bar_length: Fraction,
    tonic_midi: int,
    mode: str,
    prefer_upper_pitch: int | None = None,
    prefer_lower_pitch: int | None = None,
) -> list[Note] | None:
    """Realise a fragment as sequenced note events over n_bars.

    Returns None if no start degree keeps both voices in range.
    Optional prefer_upper/lower_pitch: MIDI pitches to prefer for smooth connection.
    """
    target_dur: Fraction = bar_length * n_bars
    model_dur: Fraction = max(
        fragment.upper.total_duration,
        fragment.lower.total_duration + fragment.offset,
    )
    assert model_dur > 0, "Model duration must be positive"
    iterations: int = max(1, math.ceil(target_dur / model_dur))
    start: int | None = _find_start(
        fragment=fragment,
        step=step,
        iterations=iterations,
        tonic_midi=tonic_midi,
        mode=mode,
        prefer_upper_pitch=prefer_upper_pitch,
        prefer_lower_pitch=prefer_lower_pitch,
    )
    if start is None:
        return None
    return _emit_notes(
        fragment=fragment,
        start=start,
        step=step,
        iterations=iterations,
        model_dur=model_dur,
        target_dur=target_dur,
        tonic_midi=tonic_midi,
        mode=mode,
    )


def validate_realisation(
    notes: list[Note],
    tonic_midi: int,
    mode: str,
    bar_length: Fraction,
) -> bool:
    """Validate realised notes: voice crossing, consonance, parallel perfects, cross-relations."""
    soprano: list[tuple[Fraction, int, Fraction]] = [
        (n.offset, degrees_to_midi((n.degree,), tonic_midi, mode)[0], n.duration)
        for n in notes if n.voice == VOICE_SOPRANO
    ]
    bass: list[tuple[Fraction, int, Fraction]] = [
        (n.offset, degrees_to_midi((n.degree,), tonic_midi, mode)[0], n.duration)
        for n in notes if n.voice == VOICE_BASS
    ]
    # Voice crossing check at every onset
    all_onsets: list[Fraction] = sorted({n.offset for n in notes})
    for t in all_onsets:
        s: int | None = _pitch_at(soprano, t)
        b: int | None = _pitch_at(bass, t)
        if s is None or b is None:
            continue
        if s - b < _MIN_VOICE_SEPARATION:
            return False

    # Crotchet grid checks
    beat_unit: Fraction = bar_length / 4
    metre: str = _METRE_FROM_BAR_LENGTH.get(bar_length, "4/4")
    strong_offsets: tuple[Fraction, ...] = STRONG_BEAT_OFFSETS.get(
        metre, (Fraction(0),),
    )
    max_t: Fraction = max(n.offset + n.duration for n in notes)

    # Collect check points
    check_points: list[tuple[Fraction, int, int, bool]] = []
    t_beat: Fraction = Fraction(0)
    while t_beat < max_t:
        s = _pitch_at(soprano, t_beat)
        b = _pitch_at(bass, t_beat)
        if s is not None and b is not None:
            bar_offset: Fraction = t_beat % bar_length
            is_strong: bool = bar_offset in strong_offsets
            check_points.append((t_beat, s, b, is_strong))
        t_beat += beat_unit

    if not check_points:
        return False

    # Cross-relation check
    for i, (_, s_midi, b_midi, _) in enumerate(check_points):
        s_pc: int = s_midi % 12
        b_pc: int = b_midi % 12
        pair: tuple[int, int] = (min(s_pc, b_pc), max(s_pc, b_pc))
        if pair in CROSS_RELATION_PAIRS:
            return False
        if i > 0:
            _, prev_s, prev_b, _ = check_points[i - 1]
            for cur, prev in ((s_pc, prev_b % 12), (b_pc, prev_s % 12)):
                xr: tuple[int, int] = (min(cur, prev), max(cur, prev))
                if xr in CROSS_RELATION_PAIRS:
                    return False

    # Parallel perfect check on consecutive strong beats
    prev_strong: tuple[int, int] | None = None
    for _, s_midi, b_midi, is_strong in check_points:
        if not is_strong:
            continue
        iv: int = (s_midi - b_midi) % 12
        if prev_strong is not None:
            prev_iv: int = (prev_strong[0] - prev_strong[1]) % 12
            if iv == prev_iv and iv in PERFECT_INTERVALS:
                s_motion: int = s_midi - prev_strong[0]
                b_motion: int = b_midi - prev_strong[1]
                if s_motion != 0 and b_motion != 0:
                    if (s_motion > 0) == (b_motion > 0):
                        return False
        prev_strong = (s_midi, b_midi)

    # Consonance scoring with weak-beat passing-tone tolerance
    consonant: int = 0
    total_strong: int = 0
    for i, (_, s_midi, b_midi, is_strong) in enumerate(check_points):
        iv = (s_midi - b_midi) % 12
        if is_strong:
            total_strong += 1
            if iv in CONSONANT_INTERVALS_ABOVE_BASS:
                consonant += 1
        else:
            if iv not in CONSONANT_INTERVALS_ABOVE_BASS:
                passed: bool = False
                if i > 0 and i < len(check_points) - 1:
                    _, prev_s, prev_b, _ = check_points[i - 1]
                    _, next_s, next_b, _ = check_points[i + 1]
                    s_approach: int = abs(s_midi - prev_s)
                    s_leave: int = abs(next_s - s_midi)
                    b_approach: int = abs(b_midi - prev_b)
                    b_leave: int = abs(next_b - b_midi)
                    if ((s_approach <= STEP_SEMITONES and s_leave <= STEP_SEMITONES) or
                            (b_approach <= STEP_SEMITONES and b_leave <= STEP_SEMITONES)):
                        passed = True
                if not passed:
                    total_strong += 1

    if total_strong == 0:
        return False
    return (consonant / total_strong) >= _MIN_CONSONANCE


def _emit_notes(
    fragment: Fragment,
    start: int,
    step: int,
    iterations: int,
    model_dur: Fraction,
    target_dur: Fraction,
    tonic_midi: int,
    mode: str,
) -> list[Note]:
    """Generate note events for all iterations, truncated to target_dur.

    After generation, fills inter-iteration gaps per voice by extending
    the last note before the gap (4c).
    """
    notes: list[Note] = []
    for k in range(iterations):
        t_base: Fraction = model_dur * k
        transpose: int = step * k
        _emit_voice_notes(
            notes=notes,
            cell=fragment.upper,
            base_degree=start + transpose,
            time_base=t_base,
            time_offset=Fraction(0),
            target_dur=target_dur,
            voice=VOICE_SOPRANO,
        )
        _emit_voice_notes(
            notes=notes,
            cell=fragment.lower,
            base_degree=start - fragment.separation + transpose,
            time_base=t_base,
            time_offset=fragment.offset,
            target_dur=target_dur,
            voice=VOICE_BASS,
        )

    # Gap-fill per voice (4c)
    for voice in (VOICE_SOPRANO, VOICE_BASS):
        voice_indices = [i for i, n in enumerate(notes) if n.voice == voice]
        voice_indices.sort(key=lambda i: notes[i].offset)
        for j in range(len(voice_indices) - 1):
            curr_idx = voice_indices[j]
            next_idx = voice_indices[j + 1]
            curr = notes[curr_idx]
            nxt = notes[next_idx]
            gap = nxt.offset - (curr.offset + curr.duration)
            if gap > Fraction(0):
                notes[curr_idx] = Note(
                    offset=curr.offset,
                    degree=curr.degree,
                    duration=curr.duration + gap,
                    voice=curr.voice,
                )

    return notes


def _emit_voice_notes(
    notes: list[Note],
    cell: Cell,
    base_degree: int,
    time_base: Fraction,
    time_offset: Fraction,
    target_dur: Fraction,
    voice: int,
) -> None:
    """Append note events for one voice in one iteration."""
    onset: Fraction = Fraction(0)
    for deg, dur in zip(cell.degrees, cell.durations):
        abs_t: Fraction = time_base + time_offset + onset
        if abs_t >= target_dur:
            break
        actual_dur: Fraction = min(dur, target_dur - abs_t)
        notes.append(Note(
            offset=abs_t,
            degree=base_degree + deg,
            duration=actual_dur,
            voice=voice,
        ))
        onset += dur


def _pitch_at(
    voice_notes: list[tuple[Fraction, int, Fraction]],
    t: Fraction,
) -> int | None:
    """Return MIDI pitch sounding at time t, or None."""
    result: int | None = None
    for onset, pitch, dur in voice_notes:
        if onset <= t < onset + dur:
            result = pitch
    return result


def _find_start(
    fragment: Fragment,
    step: int,
    iterations: int,
    tonic_midi: int,
    mode: str,
    prefer_upper_pitch: int | None = None,
    prefer_lower_pitch: int | None = None,
) -> int | None:
    """Find start degree with proximity-first selection and cross-relation rejection.

    When prefer_upper/lower_pitch are given:
    - Rejects candidates that create cross-relations with prior material
    - Among candidates with margin >= _MIN_RANGE_MARGIN, picks smallest proximity
    - Falls back to largest margin if no candidate meets threshold

    When no preferred pitches: picks largest margin (legacy behavior).
    """
    s_lo, s_hi = VOICE_RANGES[0]
    b_lo, b_hi = VOICE_RANGES[3]

    # Collect valid candidates with their margin and proximity
    candidates: list[tuple[int, int, int]] = []  # (candidate_deg, margin, proximity)

    for candidate in _START_SEARCH:
        ok: bool = True
        margin: int = 999

        # First notes for cross-relation checking
        first_upper_midi: int = degrees_to_midi(
            (candidate + fragment.upper.degrees[0],), tonic_midi, mode,
        )[0]
        first_lower_midi: int = degrees_to_midi(
            (candidate - fragment.separation + fragment.lower.degrees[0],),
            tonic_midi, mode,
        )[0]

        # Cross-relation rejection (4b)
        if prefer_upper_pitch is not None:
            for first, prior in (
                (first_upper_midi, prefer_upper_pitch),
                (first_lower_midi, prefer_upper_pitch),
            ):
                pair = (min(first % 12, prior % 12), max(first % 12, prior % 12))
                if pair in CROSS_RELATION_PAIRS:
                    ok = False
        if prefer_lower_pitch is not None and ok:
            for first, prior in (
                (first_lower_midi, prefer_lower_pitch),
                (first_upper_midi, prefer_lower_pitch),
            ):
                pair = (min(first % 12, prior % 12), max(first % 12, prior % 12))
                if pair in CROSS_RELATION_PAIRS:
                    ok = False

        if not ok:
            continue

        # Range check across all iterations
        for k in range(iterations):
            transpose: int = step * k
            for deg in fragment.upper.degrees:
                m: int = degrees_to_midi(
                    (candidate + deg + transpose,), tonic_midi, mode,
                )[0]
                if m < s_lo or m > s_hi:
                    ok = False
                    break
                margin = min(margin, m - s_lo, s_hi - m)
            if not ok:
                break
            for deg in fragment.lower.degrees:
                m = degrees_to_midi(
                    (candidate - fragment.separation + deg + transpose,),
                    tonic_midi,
                    mode,
                )[0]
                if m < b_lo or m > b_hi:
                    ok = False
                    break
                margin = min(margin, m - b_lo, b_hi - m)
            if not ok:
                break

        if not ok:
            continue

        # Compute proximity to preferred pitches
        proximity: int = 0
        if prefer_upper_pitch is not None:
            proximity += abs(first_upper_midi - prefer_upper_pitch)
        if prefer_lower_pitch is not None:
            proximity += abs(first_lower_midi - prefer_lower_pitch)

        candidates.append((candidate, margin, proximity))

    if not candidates:
        return None

    # Selection (4a): proximity-first if prefer_*_pitch given
    has_preferred: bool = prefer_upper_pitch is not None or prefer_lower_pitch is not None

    if has_preferred:
        # Among candidates with margin >= threshold, pick smallest proximity
        qualified: list[tuple[int, int, int]] = [
            (c, m, p) for c, m, p in candidates if m >= _MIN_RANGE_MARGIN
        ]
        if qualified:
            # Pick smallest proximity among qualified
            return min(qualified, key=lambda t: t[2])[0]
        else:
            # No candidate meets threshold: fall back to largest margin
            return max(candidates, key=lambda t: t[1])[0]
    else:
        # No preferred pitches: pick largest margin (legacy)
        return max(candidates, key=lambda t: t[1])[0]


# ---------------------------------------------------------------------------
# Fragment provider (stateful per-composition instance)
# ---------------------------------------------------------------------------


def _fragment_signature(frag: Fragment) -> tuple[tuple[int, ...], Fraction, int]:
    """Extract distinguishing features for diversity comparison.

    Returns tuple of:
    - interval_sequence: full melodic contour (all intervals, not just first)
    - offset: rhythmic offset between leader and follower
    - separation: degree separation between voices

    Fragments with different signatures sound perceptually distinct.
    Using full interval sequence ensures each unique melodic shape
    gets a unique signature.
    """
    leader_cell: Cell = frag.upper if frag.leader_voice == VOICE_SOPRANO else frag.lower
    degrees: tuple[int, ...] = leader_cell.degrees

    # Compute full interval sequence (complete melodic fingerprint)
    intervals: tuple[int, ...] = tuple(
        degrees[i + 1] - degrees[i]
        for i in range(len(degrees) - 1)
    )

    return (intervals, frag.offset, frag.separation)


class FragenProvider:
    """Stateful episode fragment provider.

    Created once per composition. Tracks which fragments have been used
    to ensure variety across episodes.

    Selection prioritizes perceptual diversity: fragments with novel
    signatures (melodic shape, rhythm, texture) are preferred over
    any previously-used patterns, even if use counts are equal.
    Never repeats a signature until all available signatures are exhausted.
    """

    def __init__(self, fugue: LoadedFugue, bar_length: Fraction):
        # Build catalogue once
        cells = extract_cells(fugue=fugue, bar_length=bar_length)
        chains = build_chains(cells=cells, bar_length=bar_length)
        fragments = build_fragments(
            cells=chains,
            tonic_midi=fugue.tonic_midi,
            mode=fugue.subject.mode,
            bar_length=bar_length,
        )
        self._catalogue: list[Fragment] = dedup_fragments(fragments=fragments)
        self._used_indices: set[int] = set()
        self._use_count: dict[int, int] = {}  # index -> times used
        self._history: list[Fragment] = []    # chronological order for diversity

    @property
    def catalogue_size(self) -> int:
        return len(self._catalogue)

    def get_fragment(
        self,
        leader_voice: int,
        step: int,
    ) -> Fragment | None:
        """Select a fragment, preferring perceptually diverse ones.

        Selection priority:
        1. Unused fragment matching leader_voice with novel signature
        2. Unused fragment matching leader_voice (any signature)
        3. Used fragment matching leader_voice with novel signature
        4. Least-used fragment matching leader_voice
        5. Unused fragment with any leader (if no match)
        6. None (if catalogue is empty)
        """
        if not self._catalogue:
            return None

        # Find candidates matching leader_voice
        matching: list[tuple[int, Fragment]] = [
            (i, f) for i, f in enumerate(self._catalogue)
            if f.leader_voice == leader_voice
        ]

        if not matching:
            # No match: try any unused fragment
            for i, f in enumerate(self._catalogue):
                if i not in self._used_indices:
                    self._mark_used(i, f)
                    return f
            # All used: return first
            i = 0
            self._mark_used(i, self._catalogue[i])
            return self._catalogue[i]

        # Build signature set from entire composition history
        all_used_sigs: set[tuple[tuple[int, ...], Fraction, int]] = {
            _fragment_signature(h) for h in self._history
        }

        # Partition candidates: unused vs used
        unused: list[tuple[int, Fragment]] = [(i, f) for i, f in matching if i not in self._used_indices]
        used: list[tuple[int, Fragment]] = [(i, f) for i, f in matching if i in self._used_indices]

        # 1. Prefer unused with novel signature (never used before in this composition)
        if unused:
            novel_unused = [(i, f) for i, f in unused if _fragment_signature(f) not in all_used_sigs]
            if novel_unused:
                i, f = novel_unused[0]
                self._mark_used(i, f)
                return f
            # 2. Fall back to any unused (signature was seen before, but this fragment wasn't)
            i, f = unused[0]
            self._mark_used(i, f)
            return f

        # 3. All matching have been used: prefer novel signature
        novel_used = [(i, f) for i, f in used if _fragment_signature(f) not in all_used_sigs]
        if novel_used:
            i, f = novel_used[0]
            self._mark_used(i, f)
            return f

        # 4. All signatures recently used: pick least-used
        least_used_idx: int = min(
            (i for i, _ in used),
            key=lambda idx: self._use_count.get(idx, 0),
        )
        self._mark_used(least_used_idx, self._catalogue[least_used_idx])
        return self._catalogue[least_used_idx]

    def _mark_used(self, index: int, fragment: Fragment) -> None:
        """Mark fragment as used and append to history."""
        self._used_indices.add(index)
        self._use_count[index] = self._use_count.get(index, 0) + 1
        self._history.append(fragment)


# ---------------------------------------------------------------------------
# Pipeline adapter
# ---------------------------------------------------------------------------


def realise_to_notes(
    fragment: Fragment,
    n_bars: int,
    step: int,
    bar_length: Fraction,
    key: Key,
    start_offset: Fraction,
    prior_upper_pitch: int | None,
    prior_lower_pitch: int | None,
) -> list[BuilderNote] | None:
    """Realise a fragment and convert to builder.types.Note for pipeline consumption.

    Returns None if no valid start degree is found.
    """
    fragen_notes: list[Note] | None = realise(
        fragment=fragment,
        n_bars=n_bars,
        step=step,
        bar_length=bar_length,
        tonic_midi=key.tonic_pc + 60,
        mode=key.mode,
        prefer_upper_pitch=prior_upper_pitch,
        prefer_lower_pitch=prior_lower_pitch,
    )
    if fragen_notes is None:
        return None
    tonic_midi: int = key.tonic_pc + 60
    result: list[BuilderNote] = []
    for fn in fragen_notes:
        midi_pitch: int = degrees_to_midi(
            (fn.degree,), tonic_midi, key.mode,
        )[0]
        track: int = TRACK_SOPRANO if fn.voice == VOICE_SOPRANO else TRACK_BASS
        result.append(BuilderNote(
            offset=fn.offset + start_offset,
            pitch=midi_pitch,
            duration=fn.duration,
            voice=track,
        ))
    return result
