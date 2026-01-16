"""Hard constraint checks - REFUSES category."""
from fractions import Fraction

from engine.bob import vocabulary as vocab
from engine.bob.formatter import Issue, offset_to_bar_beat
from engine.engine_types import RealisedNote, RealisedPhrase
from engine.voice_checks import (
    Violation,
    VoiceViolation,
    check_parallel_fifths,
    check_parallel_octaves,
    detect_direct_perfect,
    detect_voice_overlap,
    validate_dissonance,
)

def _voice_names_for_count(voice_count: int) -> list[str]:
    """Get voice names appropriate for the voice count."""
    if voice_count == 2:
        return ["soprano", "bass"]
    elif voice_count == 3:
        return ["soprano", "alto", "bass"]
    elif voice_count == 4:
        return ["soprano", "alto", "tenor", "bass"]
    else:
        return [f"v{i}" for i in range(voice_count)]


def _voice_pair_name(upper_idx: int, lower_idx: int, voice_count: int) -> str:
    """Get voice pair name like 'soprano-bass'."""
    names = _voice_names_for_count(voice_count)
    return f"{names[upper_idx]}-{names[lower_idx]}"


def _notes_to_tuples(notes: tuple[RealisedNote, ...]) -> list[tuple[Fraction, int]]:
    """Convert RealisedNotes to (offset, pitch) tuples."""
    return [(n.offset, n.pitch) for n in notes]


def _violation_to_issue(
    v: Violation,
    bar_duration: Fraction,
    voices: str,
    message: str,
) -> Issue:
    """Convert Violation to Issue."""
    bar, beat = offset_to_bar_beat(v.offset, bar_duration)
    return Issue(
        category="REFUSES",
        bar=bar,
        beat=beat,
        voices=voices,
        message=message,
    )


def _voice_violation_to_issue(
    v: VoiceViolation,
    bar_duration: Fraction,
    voice_count: int,
    message: str,
) -> Issue:
    """Convert VoiceViolation to Issue."""
    bar, beat = offset_to_bar_beat(v.offset, bar_duration)
    voices = _voice_pair_name(v.upper_index, v.lower_index, voice_count)
    return Issue(
        category="REFUSES",
        bar=bar,
        beat=beat,
        voices=voices,
        message=message,
    )


def check_parallel_fifths_refuses(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
) -> list[Issue]:
    """Check for parallel fifths between outer voices."""
    issues: list[Issue] = []
    for phrase in phrases:
        soprano = _notes_to_tuples(phrase.soprano)
        bass = _notes_to_tuples(phrase.bass)
        for v in check_parallel_fifths(soprano, bass):
            issues.append(_violation_to_issue(
                v, bar_duration, "soprano-bass", vocab.PARALLEL_FIFTH
            ))
    return issues


def check_parallel_octaves_refuses(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
) -> list[Issue]:
    """Check for parallel octaves between outer voices."""
    issues: list[Issue] = []
    for phrase in phrases:
        soprano = _notes_to_tuples(phrase.soprano)
        bass = _notes_to_tuples(phrase.bass)
        for v in check_parallel_octaves(soprano, bass):
            issues.append(_violation_to_issue(
                v, bar_duration, "soprano-bass", vocab.PARALLEL_OCTAVE
            ))
    return issues


def check_parallel_unisons_refuses(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
) -> list[Issue]:
    """Check for parallel unisons between outer voices."""
    from shared.parallels import is_parallel_motion

    issues: list[Issue] = []
    for phrase in phrases:
        soprano = _notes_to_tuples(phrase.soprano)
        bass = _notes_to_tuples(phrase.bass)
        sop_by_off = {off: pitch for off, pitch in soprano}
        bass_by_off = {off: pitch for off, pitch in bass}
        common = sorted(set(sop_by_off.keys()) & set(bass_by_off.keys()))

        for i in range(1, len(common)):
            prev_off = common[i - 1]
            curr_off = common[i]
            if is_parallel_motion(
                sop_by_off[prev_off], bass_by_off[prev_off],
                sop_by_off[curr_off], bass_by_off[curr_off],
                0  # unison/octave
            ):
                # Check if it's truly unison (same pitch) not just octave
                if sop_by_off[prev_off] == bass_by_off[prev_off]:
                    bar, beat = offset_to_bar_beat(curr_off, bar_duration)
                    issues.append(Issue(
                        category="REFUSES",
                        bar=bar,
                        beat=beat,
                        voices="soprano-bass",
                        message=vocab.PARALLEL_UNISON,
                    ))
    return issues


def check_direct_perfect_refuses(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
) -> list[Issue]:
    """Check for direct fifths/octaves between outer voices."""
    issues: list[Issue] = []
    for phrase in phrases:
        soprano = _notes_to_tuples(phrase.soprano)
        bass = _notes_to_tuples(phrase.bass)
        for v in detect_direct_perfect(soprano, bass):
            msg = vocab.DIRECT_FIFTH if v.type == "direct_fifth" else vocab.DIRECT_OCTAVE
            issues.append(_violation_to_issue(v, bar_duration, "soprano-bass", msg))
    return issues


def check_dissonance_refuses(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
) -> list[Issue]:
    """Check for unprepared/unresolved dissonances."""
    issues: list[Issue] = []
    for phrase in phrases:
        soprano = _notes_to_tuples(phrase.soprano)
        bass = _notes_to_tuples(phrase.bass)
        for v in validate_dissonance(soprano, bass, bar_duration):
            if v.type == "dissonance_unprepared":
                msg = vocab.UNPREPARED
            elif v.type == "dissonance_unresolved":
                msg = vocab.UNRESOLVED
            elif v.type == "dissonance_resolved_up":
                msg = vocab.RESOLVED_UP
            else:
                continue
            issues.append(_violation_to_issue(v, bar_duration, "soprano-bass", msg))
    return issues


def check_voice_overlap_refuses(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
) -> list[Issue]:
    """Check for voice overlap."""
    issues: list[Issue] = []
    for phrase in phrases:
        voice_count = len(phrase.voices)
        voices_data = [
            _notes_to_tuples(tuple(v.notes)) for v in phrase.voices
        ]
        for v in detect_voice_overlap(voices_data):
            issues.append(_voice_violation_to_issue(
                v, bar_duration, voice_count, vocab.VOICE_OVERLAP
            ))
    return issues


def check_voice_crossing_refuses(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
    max_beats: Fraction = Fraction(1),
) -> list[Issue]:
    """Check for prolonged voice crossing (> max_beats)."""
    from engine.guards.spacing import check_spacing, SPACING_OUTER

    issues: list[Issue] = []
    for phrase in phrases:
        voice_count = len(phrase.voices)
        if voice_count < 2:
            continue
        soprano = _notes_to_tuples(phrase.soprano)
        bass = _notes_to_tuples(phrase.bass)

        # Track crossing duration
        crossing_start: Fraction | None = None
        prev_off: Fraction | None = None

        sop_by_off = {off: pitch for off, pitch in soprano}
        bass_by_off = {off: pitch for off, pitch in bass}
        common = sorted(set(sop_by_off.keys()) & set(bass_by_off.keys()))

        for off in common:
            is_crossing = sop_by_off[off] < bass_by_off[off]

            if is_crossing:
                if crossing_start is None:
                    crossing_start = off
            else:
                if crossing_start is not None and prev_off is not None:
                    duration = prev_off - crossing_start
                    if duration > max_beats:
                        bar, beat = offset_to_bar_beat(crossing_start, bar_duration)
                        issues.append(Issue(
                            category="REFUSES",
                            bar=bar,
                            beat=beat,
                            voices="soprano-bass",
                            message=vocab.VOICE_CROSSING,
                        ))
                crossing_start = None
            prev_off = off

        # Check final crossing
        if crossing_start is not None and prev_off is not None:
            duration = prev_off - crossing_start
            if duration > max_beats:
                bar, beat = offset_to_bar_beat(crossing_start, bar_duration)
                issues.append(Issue(
                    category="REFUSES",
                    bar=bar,
                    beat=beat,
                    voices="soprano-bass",
                    message=vocab.VOICE_CROSSING,
                ))

    return issues


def check_verbatim_repetition_refuses(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
    threshold: int = 3,
) -> list[Issue]:
    """Check for verbatim repetition (3+ consecutive identical bars).

    This catches the subject being repeated verbatim without variation.
    """
    issues: list[Issue] = []

    for phrase in phrases:
        voice_count = len(phrase.voices)
        for v_idx, voice in enumerate(phrase.voices):
            notes = _notes_to_tuples(tuple(voice.notes))

            # Group pitches by bar
            bars: dict[int, tuple[int, ...]] = {}
            for offset, pitch in notes:
                bar_num = int(offset // bar_duration)
                if bar_num not in bars:
                    bars[bar_num] = ()
                bars[bar_num] = bars[bar_num] + (pitch,)

            sorted_bars = sorted(bars.keys())
            if len(sorted_bars) < threshold + 1:
                continue

            # Find runs of identical consecutive bars
            run_start = 0
            for i in range(1, len(sorted_bars)):
                prev_bar = sorted_bars[i - 1]
                curr_bar = sorted_bars[i]
                is_consecutive = (curr_bar == prev_bar + 1)
                is_identical = (bars[curr_bar] == bars[sorted_bars[run_start]])

                if is_consecutive and is_identical:
                    continue
                else:
                    run_len = i - run_start
                    if run_len >= threshold:
                        bar, beat = offset_to_bar_beat(
                            Fraction(sorted_bars[run_start]) * bar_duration,
                            bar_duration,
                        )
                        voice_name = _voice_names_for_count(voice_count)[v_idx]
                        issues.append(Issue(
                            category="REFUSES",
                            bar=bar,
                            beat=beat,
                            voices=voice_name,
                            message=vocab.VERBATIM_REPETITION.format(bars=run_len + 1),
                        ))
                    run_start = i

            # Check final run
            run_len = len(sorted_bars) - run_start
            if run_len >= threshold:
                bar, beat = offset_to_bar_beat(
                    Fraction(sorted_bars[run_start]) * bar_duration,
                    bar_duration,
                )
                voice_name = _voice_names_for_count(voice_count)[v_idx]
                issues.append(Issue(
                    category="REFUSES",
                    bar=bar,
                    beat=beat,
                    voices=voice_name,
                    message=vocab.VERBATIM_REPETITION.format(bars=run_len + 1),
                ))

    return issues


def collect_refuses_non_guard(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
) -> list[Issue]:
    """Collect REFUSES issues that aren't covered by the guard system.

    These are Bob-specific checks like voice crossing duration and verbatim repetition.
    The guard system handles parallels, direct motion, and dissonance.
    """
    issues: list[Issue] = []
    issues.extend(check_voice_crossing_refuses(phrases, bar_duration))
    issues.extend(check_verbatim_repetition_refuses(phrases, bar_duration))
    return issues


def collect_refuses(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
) -> list[Issue]:
    """Collect all REFUSES issues (legacy, for when guard diagnostics not available)."""
    issues: list[Issue] = []
    issues.extend(check_parallel_fifths_refuses(phrases, bar_duration))
    issues.extend(check_parallel_octaves_refuses(phrases, bar_duration))
    issues.extend(check_parallel_unisons_refuses(phrases, bar_duration))
    issues.extend(check_direct_perfect_refuses(phrases, bar_duration))
    issues.extend(check_dissonance_refuses(phrases, bar_duration))
    issues.extend(check_voice_overlap_refuses(phrases, bar_duration))
    issues.extend(check_voice_crossing_refuses(phrases, bar_duration))
    issues.extend(check_verbatim_repetition_refuses(phrases, bar_duration))
    return issues
