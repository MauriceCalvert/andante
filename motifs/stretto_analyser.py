"""Stretto analyser: discover valid stretto offsets for a fugue subject.

A stretto entry is the subject overlapping with a time-shifted copy of
itself (or its tonal answer). For each candidate offset, the analyser
checks whether the overlapping region produces acceptable two-voice
counterpoint: consonant on strong beats, no parallel 5ths/octaves.

The analyser does not modify the subject. It discovers which offsets
work and stores them as metadata.
"""
from dataclasses import dataclass
from fractions import Fraction
from typing import Tuple

from motifs.subject_generator import GeneratedSubject
from motifs.answer_generator import GeneratedAnswer


# Intervals mod 7 that are consonant (invertible: no 5ths)
STRONG_BEAT_CONSONANCES: frozenset[int] = frozenset({0, 2, 5})  # unison, 3rd, 6th
WEAK_BEAT_CONSONANCES: frozenset[int] = frozenset({0, 1, 2, 4, 5, 6})  # all but tritone
# Maximum dissonance count on weak beats before rejecting
MAX_WEAK_DISSONANCES: int = 1


@dataclass(frozen=True)
class StrettoOffset:
    """A valid stretto entry point."""
    offset: float           # Offset in whole-note units
    offset_beats: float     # Offset in beat units (quarter notes in 4/4)
    overlap_notes: int      # Number of simultaneous note-pairs checked
    all_consonant: bool     # True if every overlap point is consonant
    voice: str              # "subject" or "answer" — what the follower plays


@dataclass(frozen=True)
class StrettoAnalysis:
    """Result of stretto analysis for a subject."""
    valid_offsets: Tuple[StrettoOffset, ...]


def _build_timeline(
    degrees: tuple[int, ...],
    durations: tuple[float, ...],
) -> list[tuple[Fraction, int]]:
    """Build a (onset_time, degree) timeline from degrees and durations."""
    timeline: list[tuple[Fraction, int]] = []
    offset = Fraction(0)
    for deg, dur in zip(degrees, durations):
        timeline.append((offset, deg))
        offset += Fraction(dur).limit_denominator(64)
    return timeline


def _degree_at_time(
    timeline: list[tuple[Fraction, int]],
    t: Fraction,
    total_dur: Fraction,
) -> int | None:
    """Return the sounding degree at time t, or None if outside range."""
    if t < Fraction(0) or t >= total_dur:
        return None
    result: int | None = None
    for onset, deg in timeline:
        if onset > t:
            break
        result = deg
    return result


def _is_strong_beat(
    t: Fraction,
    metre: tuple[int, int],
) -> bool:
    """Check if time t falls on a strong beat."""
    beat_dur = Fraction(1, metre[1])
    bar_dur = Fraction(metre[0], metre[1])
    beat_in_bar = int((t % bar_dur) / beat_dur)
    if metre[0] == 4:
        return beat_in_bar in (0, 2)
    if metre[0] == 3:
        return beat_in_bar == 0
    if metre[0] == 2:
        return beat_in_bar == 0
    if metre[0] == 6:
        return beat_in_bar in (0, 3)
    return beat_in_bar == 0


def _check_overlap(
    leader_timeline: list[tuple[Fraction, int]],
    follower_timeline: list[tuple[Fraction, int]],
    leader_dur: Fraction,
    follower_dur: Fraction,
    offset: Fraction,
    metre: tuple[int, int],
    min_duration: Fraction,
) -> tuple[bool, int, bool]:
    """Check counterpoint validity of follower entering at offset.

    Returns (valid, overlap_note_count, all_consonant).
    """
    # Follower starts at `offset`, runs to `offset + follower_dur`
    # Leader starts at 0, runs to `leader_dur`
    overlap_start = offset
    overlap_end = min(leader_dur, offset + follower_dur)
    if overlap_end <= overlap_start:
        return False, 0, False
    # Collect all onset times in the overlap region from both voices
    check_times: set[Fraction] = set()
    for onset, _ in leader_timeline:
        if overlap_start <= onset < overlap_end:
            check_times.add(onset)
    for onset, _ in follower_timeline:
        shifted = onset + offset
        if overlap_start <= shifted < overlap_end:
            check_times.add(shifted)
    if len(check_times) < 2:
        return False, 0, False
    sorted_times = sorted(check_times)
    weak_dissonance_count = 0
    all_consonant = True
    prev_interval_mod7: int | None = None
    prev_leader_dir: int | None = None
    for t in sorted_times:
        leader_deg = _degree_at_time(leader_timeline, t, leader_dur)
        follower_deg = _degree_at_time(follower_timeline, t - offset, follower_dur)
        if leader_deg is None or follower_deg is None:
            continue
        interval_mod7 = abs(leader_deg - follower_deg) % 7
        strong = _is_strong_beat(t, metre)
        if strong:
            if interval_mod7 not in STRONG_BEAT_CONSONANCES:
                return False, 0, False
        else:
            if interval_mod7 not in WEAK_BEAT_CONSONANCES:
                return False, 0, False
            if interval_mod7 not in STRONG_BEAT_CONSONANCES:
                all_consonant = False
                weak_dissonance_count += 1
                if weak_dissonance_count > MAX_WEAK_DISSONANCES:
                    return False, 0, False
        # Check parallel 5ths/octaves with previous interval
        if prev_interval_mod7 is not None:
            if interval_mod7 == prev_interval_mod7 and interval_mod7 in (0, 4):
                return False, 0, False
        prev_interval_mod7 = interval_mod7
    return True, len(sorted_times), all_consonant


def count_self_stretto(
    degrees: tuple[int, ...],
    durations: tuple[float, ...],
    metre: tuple[int, int] = (4, 4),
) -> int:
    """Count valid self-stretto offsets for a degree/duration sequence."""
    frac_durs = tuple(Fraction(d).limit_denominator(64) for d in durations)
    total_dur = sum(frac_durs)
    timeline = _build_timeline(degrees, durations)
    min_dur = min(frac_durs)
    assert min_dur > Fraction(0), "Zero-duration note"
    count = 0
    offset = min_dur
    while offset < total_dur:
        valid, overlap_count, _ = _check_overlap(
            leader_timeline=timeline,
            follower_timeline=timeline,
            leader_dur=total_dur,
            follower_dur=total_dur,
            offset=offset,
            metre=metre,
            min_duration=min_dur,
        )
        if valid and overlap_count >= 3:
            count += 1
        offset += min_dur
    return count


def analyse_stretto(
    subject: GeneratedSubject,
    answer: GeneratedAnswer | None = None,
    metre: tuple[int, int] = (4, 4),
) -> StrettoAnalysis:
    """Discover valid stretto offsets for subject (and optionally answer).

    Tests the subject against itself, and if answer is provided, the
    subject against the answer as follower. Offsets are quantised to
    the smallest note duration in the subject.
    """
    subj_durations = tuple(Fraction(d).limit_denominator(64) for d in subject.durations)
    subj_total = sum(subj_durations)
    subj_timeline = _build_timeline(subject.scale_indices, subject.durations)
    # Quantisation grid: smallest note in the subject
    min_dur = min(subj_durations)
    assert min_dur > Fraction(0), "Zero-duration note in subject"
    beat_dur = Fraction(1, metre[1])
    results: list[StrettoOffset] = []
    # Test subject against itself at each offset
    offset = min_dur
    while offset < subj_total:
        valid, overlap_count, all_consonant = _check_overlap(
            leader_timeline=subj_timeline,
            follower_timeline=subj_timeline,
            leader_dur=subj_total,
            follower_dur=subj_total,
            offset=offset,
            metre=metre,
            min_duration=min_dur,
        )
        if valid and overlap_count >= 3:
            results.append(StrettoOffset(
                offset=float(offset),
                offset_beats=float(offset / beat_dur),
                overlap_notes=overlap_count,
                all_consonant=all_consonant,
                voice="subject",
            ))
        offset += min_dur
    # Test subject (leader) against answer (follower)
    if answer is not None:
        ans_durations = tuple(Fraction(d).limit_denominator(64) for d in answer.durations)
        ans_total = sum(ans_durations)
        ans_timeline = _build_timeline(answer.scale_indices, answer.durations)
        offset = min_dur
        while offset < subj_total:
            valid, overlap_count, all_consonant = _check_overlap(
                leader_timeline=subj_timeline,
                follower_timeline=ans_timeline,
                leader_dur=subj_total,
                follower_dur=ans_total,
                offset=offset,
                metre=metre,
                min_duration=min_dur,
            )
            if valid and overlap_count >= 3:
                results.append(StrettoOffset(
                    offset=float(offset),
                    offset_beats=float(offset / beat_dur),
                    overlap_notes=overlap_count,
                    all_consonant=all_consonant,
                    voice="answer",
                ))
            offset += min_dur
    return StrettoAnalysis(valid_offsets=tuple(results))
