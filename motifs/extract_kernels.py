"""extract_kernels — Paired-kernel extraction from fugue subject/CS overlap.

Extracts two-voice PairedKernels from the concurrent exposition material
(CS against Answer), sliced at shared note-onset boundaries. Vertical
consonance is inherited from the original counterpoint; it is not checked
here — the caller (EpisodeKernelSource) is responsible for the consonance
check after diatonic transposition.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from fractions import Fraction

from motifs.subject_loader import SubjectTriple
from shared.constants import exact_fraction
from shared.music_math import parse_metre

_log: logging.Logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_KERNEL_MAX_NOTES: int = 4   # cap: longer fragments sound like subject quotations
_KERNEL_MIN_NOTES: int = 2   # minimum for a recognisable gesture

# ---------------------------------------------------------------------------
# Data type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PairedKernel:
    """Two-voice motivic kernel for sequential episode generation.

    Both voices are derived from the concurrent exposition material;
    vertical consonance is pre-guaranteed by the original counterpoint.
    Degrees are normalised so upper_degrees[0] == 0.
    """
    name: str                              # e.g. "cs_ans[1/4:1/2]"
    upper_degrees: tuple[int, ...]         # relative (first upper = 0)
    upper_durations: tuple[Fraction, ...]
    lower_degrees: tuple[int, ...]         # relative to same base as upper
    lower_durations: tuple[Fraction, ...]
    total_duration: Fraction               # shared-onset to shared-onset span
    source: str                            # "cs_ans", "ans_cs", "subj_cs", etc.


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_paired_kernels(fugue: SubjectTriple) -> list[PairedKernel]:
    """Extract paired kernels from the CS/Answer exposition overlap.

    Returns a deduplicated list of PairedKernels including inversions and
    sub-pairs (first-2, last-2 notes of the longer voice).  Returns an empty
    list if the subject/CS rhythms produce no shared onsets with 2+ notes per
    voice in any slice.
    """
    cs_degrees: tuple[int, ...] = fugue.countersubject.degrees
    cs_durations: tuple[Fraction, ...] = tuple(
        exact_fraction(value=d, label="cs duration")
        for d in fugue.countersubject.durations
    )
    ans_degrees: tuple[int, ...] = fugue.answer.degrees
    ans_durations: tuple[Fraction, ...] = tuple(
        exact_fraction(value=d, label="answer duration")
        for d in fugue.answer.durations
    )
    subj_degrees: tuple[int, ...] = fugue.subject.degrees
    subj_durations: tuple[Fraction, ...] = tuple(
        exact_fraction(value=d, label="subject duration")
        for d in fugue.subject.durations
    )

    pairings: list[tuple[
        str,
        tuple[int, ...], tuple[Fraction, ...],
        tuple[int, ...], tuple[Fraction, ...],
    ]] = [
        ("cs_ans",  cs_degrees,   cs_durations,  ans_degrees,  ans_durations),
        ("ans_cs",  ans_degrees,  ans_durations, cs_degrees,   cs_durations),
    ]
    if fugue.subject.degrees != fugue.answer.degrees:
        pairings.append(
            ("subj_cs", subj_degrees, subj_durations, cs_degrees, cs_durations)
        )

    raw: list[PairedKernel] = []
    for source, u_deg, u_dur, l_deg, l_dur in pairings:
        slices = _extract_slices(
            upper_degrees=u_deg,
            upper_durations=u_dur,
            lower_degrees=l_deg,
            lower_durations=l_dur,
            source=source,
        )
        raw.extend(slices)

    print(f"[EPI-6] extract: {len(raw)} raw slices from {len(pairings)} pairings")

    sub_pairs: list[PairedKernel] = []
    for pk in raw:
        sub_pairs.extend(_extract_sub_pairs(pk=pk))

    inverted: list[PairedKernel] = [
        _invert_paired_kernel(pk=pk) for pk in raw + sub_pairs
    ]

    result = _dedup_paired_kernels(kernels=raw + sub_pairs + inverted)
    print(f"[EPI-6] extract: {len(result)} total after dedup")
    return result


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_onsets(durations: tuple[Fraction, ...]) -> list[Fraction]:
    """Build note-onset list from a duration sequence (cumulative sums from 0)."""
    onsets: list[Fraction] = []
    cumulative: Fraction = Fraction(0)
    for dur in durations:
        onsets.append(cumulative)
        cumulative += dur
    return onsets


def _extract_slices(
    upper_degrees: tuple[int, ...],
    upper_durations: tuple[Fraction, ...],
    lower_degrees: tuple[int, ...],
    lower_durations: tuple[Fraction, ...],
    source: str,
) -> list[PairedKernel]:
    """Slice both voices at union of all onsets and return valid PairedKernels."""
    upper_onsets: list[Fraction] = _build_onsets(upper_durations)
    lower_onsets: list[Fraction] = _build_onsets(lower_durations)
    upper_total: Fraction = sum(upper_durations, Fraction(0))
    lower_total: Fraction = sum(lower_durations, Fraction(0))
    shorter_total: Fraction = min(upper_total, lower_total)
    # Union of all onsets from both voices, plus boundaries.
    all_onsets: set[Fraction] = set(upper_onsets) | set(lower_onsets)
    all_onsets.add(Fraction(0))
    all_onsets.add(shorter_total)
    boundary_sorted: list[Fraction] = sorted(
        t for t in all_onsets if Fraction(0) <= t <= shorter_total
    )
    kernels: list[PairedKernel] = []
    for i in range(len(boundary_sorted) - 1):
        for j in range(i + 1, len(boundary_sorted)):
            t_start: Fraction = boundary_sorted[i]
            t_end: Fraction = boundary_sorted[j]
            if t_end <= t_start:
                continue
            u_slice_deg, u_slice_dur = _voice_slice(
                degrees=upper_degrees,
                durations=upper_durations,
                onsets=upper_onsets,
                t_start=t_start,
                t_end=t_end,
            )
            l_slice_deg, l_slice_dur = _voice_slice(
                degrees=lower_degrees,
                durations=lower_durations,
                onsets=lower_onsets,
                t_start=t_start,
                t_end=t_end,
            )
            u_count: int = len(u_slice_deg)
            l_count: int = len(l_slice_deg)
            longer_count: int = max(u_count, l_count)
            # At least one voice must have 2+ notes; other may have 1.
            if longer_count < _KERNEL_MIN_NOTES:
                continue
            if u_count < 1 or l_count < 1:
                continue
            if longer_count > _KERNEL_MAX_NOTES:
                continue
            # Normalise: shift all degrees so upper_degrees[0] == 0.
            base: int = u_slice_deg[0]
            norm_upper: tuple[int, ...] = tuple(d - base for d in u_slice_deg)
            norm_lower: tuple[int, ...] = tuple(d - base for d in l_slice_deg)
            total_dur: Fraction = t_end - t_start
            tag: str = f"{source}[{t_start}:{t_end}]"
            kernels.append(PairedKernel(
                name=tag,
                upper_degrees=norm_upper,
                upper_durations=tuple(u_slice_dur),
                lower_degrees=norm_lower,
                lower_durations=tuple(l_slice_dur),
                total_duration=total_dur,
                source=source,
            ))
    if not kernels:
        n_windows: int = len(boundary_sorted) * (len(boundary_sorted) - 1) // 2
        print(
            f"[EPI-6] _extract_slices({source}): 0 kernels from "
            f"{len(boundary_sorted)} boundaries ({n_windows} windows). "
            f"min={_KERNEL_MIN_NOTES}, max={_KERNEL_MAX_NOTES}, "
            f"upper_durs={upper_durations[:6]}, lower_durs={lower_durations[:6]}"
        )
    return kernels


def _voice_slice(
    degrees: tuple[int, ...],
    durations: tuple[Fraction, ...],
    onsets: list[Fraction],
    t_start: Fraction,
    t_end: Fraction,
) -> tuple[tuple[int, ...], tuple[Fraction, ...]]:
    """Collect notes whose onset is in [t_start, t_end), truncating at t_end."""
    out_deg: list[int] = []
    out_dur: list[Fraction] = []
    for deg, dur, onset in zip(degrees, durations, onsets):
        if onset < t_start or onset >= t_end:
            continue
        effective_dur: Fraction = min(dur, t_end - onset)
        out_deg.append(deg)
        out_dur.append(effective_dur)
    return tuple(out_deg), tuple(out_dur)


def _extract_sub_pairs(pk: PairedKernel) -> list[PairedKernel]:
    """Extract first-2 and last-2 note sub-pairs for fragmentation use.

    Only produced when the longer voice has 3+ notes.
    """
    upper_len: int = len(pk.upper_degrees)
    lower_len: int = len(pk.lower_degrees)
    longer_voice_len: int = max(upper_len, lower_len)
    if longer_voice_len < 3:
        return []

    # Use the longer voice's duration sequence for span computation.
    longer_durs: tuple[Fraction, ...] = (
        pk.upper_durations if upper_len >= lower_len else pk.lower_durations
    )

    sub_pairs: list[PairedKernel] = []

    # First-2: time span of the first 2 notes in the longer voice.
    first2_end: Fraction = longer_durs[0] + longer_durs[1]
    sp1 = _truncate_pk(pk=pk, span_start=Fraction(0), span_end=first2_end, suffix="_f2")
    if sp1 is not None:
        sub_pairs.append(sp1)

    # Last-2: from onset of (n-2)th note to end of the longer voice.
    last2_start: Fraction = sum(longer_durs[:-2], Fraction(0))
    sp2 = _truncate_pk(pk=pk, span_start=last2_start, span_end=pk.total_duration, suffix="_l2")
    if sp2 is not None:
        sub_pairs.append(sp2)

    return sub_pairs


def _truncate_pk(
    pk: PairedKernel,
    span_start: Fraction,
    span_end: Fraction,
    suffix: str,
) -> PairedKernel | None:
    """Truncate both voices of a PairedKernel to [span_start, span_end)."""
    u_onsets: list[Fraction] = _build_onsets(pk.upper_durations)
    l_onsets: list[Fraction] = _build_onsets(pk.lower_durations)

    u_deg, u_dur = _voice_slice(
        degrees=pk.upper_degrees,
        durations=pk.upper_durations,
        onsets=u_onsets,
        t_start=span_start,
        t_end=span_end,
    )
    l_deg, l_dur = _voice_slice(
        degrees=pk.lower_degrees,
        durations=pk.lower_durations,
        onsets=l_onsets,
        t_start=span_start,
        t_end=span_end,
    )

    if max(len(u_deg), len(l_deg)) < _KERNEL_MIN_NOTES:
        return None
    if len(u_deg) < 1 or len(l_deg) < 1:
        return None
    if max(len(u_deg), len(l_deg)) > _KERNEL_MAX_NOTES:
        return None

    total: Fraction = span_end - span_start
    # Re-normalise so upper_degrees[0] == 0.
    base: int = u_deg[0] if u_deg else 0
    return PairedKernel(
        name=pk.name + suffix,
        upper_degrees=tuple(d - base for d in u_deg),
        upper_durations=u_dur,
        lower_degrees=tuple(d - base for d in l_deg),
        lower_durations=l_dur,
        total_duration=total,
        source=pk.source + suffix,
    )


def _invert_paired_kernel(pk: PairedKernel) -> PairedKernel:
    """Produce an inverted copy: negate all degrees, re-normalise."""
    raw_upper: tuple[int, ...] = tuple(-d for d in pk.upper_degrees)
    raw_lower: tuple[int, ...] = tuple(-d for d in pk.lower_degrees)
    base: int = raw_upper[0]
    return PairedKernel(
        name=pk.name + "_inv",
        upper_degrees=tuple(d - base for d in raw_upper),
        upper_durations=pk.upper_durations,
        lower_degrees=tuple(d - base for d in raw_lower),
        lower_durations=pk.lower_durations,
        total_duration=pk.total_duration,
        source=pk.source + "_inv",
    )


def _dedup_paired_kernels(kernels: list[PairedKernel]) -> list[PairedKernel]:
    """Remove kernels with identical (upper_degrees, upper_durations, lower_degrees, lower_durations)."""
    seen: set[tuple] = set()
    result: list[PairedKernel] = []
    for pk in kernels:
        key: tuple = (pk.upper_degrees, pk.upper_durations, pk.lower_degrees, pk.lower_durations)
        if key not in seen:
            seen.add(key)
            result.append(pk)
    return result
