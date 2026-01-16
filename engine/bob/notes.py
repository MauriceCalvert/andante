"""Perceptual observations - NOTES category."""
from fractions import Fraction

from engine.bob import vocabulary as vocab
from engine.bob.formatter import Issue, offset_to_bar_beat
from engine.engine_types import RealisedNote, RealisedPhrase
from engine.voice_checks import DISSONANT_INTERVALS

VOICE_NAMES = ["soprano", "alto", "tenor", "bass"]


def _notes_to_tuples(notes: tuple[RealisedNote, ...]) -> list[tuple[Fraction, int]]:
    """Convert RealisedNotes to (offset, pitch) tuples."""
    return [(n.offset, n.pitch) for n in notes]


def check_resolves_nicely(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
) -> list[Issue]:
    """Detect nicely resolved dissonances."""
    issues: list[Issue] = []

    for phrase in phrases:
        soprano = _notes_to_tuples(phrase.soprano)
        bass = _notes_to_tuples(phrase.bass)

        sop_by_off = {off: pitch for off, pitch in soprano}
        bass_by_off = {off: pitch for off, pitch in bass}
        common = sorted(set(sop_by_off.keys()) & set(bass_by_off.keys()))

        for i in range(len(common) - 1):
            curr_off = common[i]
            next_off = common[i + 1]

            curr_sop = sop_by_off[curr_off]
            curr_bass = bass_by_off[curr_off]
            next_sop = sop_by_off[next_off]
            next_bass = bass_by_off[next_off]

            curr_interval = abs(curr_sop - curr_bass) % 12
            next_interval = abs(next_sop - next_bass) % 12

            # Dissonance resolving to consonance by step down
            if (curr_interval in DISSONANT_INTERVALS and
                    next_interval not in DISSONANT_INTERVALS):
                soprano_motion = next_sop - curr_sop
                if -3 <= soprano_motion < 0:  # Step down
                    bar, beat = offset_to_bar_beat(next_off, bar_duration)
                    issues.append(Issue(
                        category="NOTES",
                        bar=bar,
                        beat=beat,
                        voices="",
                        message=vocab.RESOLVES_NICELY,
                    ))

    return issues


def check_feels_conclusive(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
    tonic_pc: int,
) -> list[Issue]:
    """Detect conclusive endings (authentic cadence on tonic)."""
    issues: list[Issue] = []

    if not phrases:
        return issues

    # Check last phrase
    last_phrase = phrases[-1]
    soprano = _notes_to_tuples(last_phrase.soprano)
    bass = _notes_to_tuples(last_phrase.bass)

    if len(soprano) < 2 or len(bass) < 2:
        return issues

    soprano.sort(key=lambda x: x[0])
    bass.sort(key=lambda x: x[0])

    # Get final two notes
    final_sop_off, final_sop = soprano[-1]
    penult_sop_off, penult_sop = soprano[-2]
    final_bass_off, final_bass = bass[-1]
    penult_bass_off, penult_bass = bass[-2]

    # Authentic cadence: V-I in bass, soprano ends on tonic
    dominant_pc = (tonic_pc + 7) % 12
    final_bass_pc = final_bass % 12
    penult_bass_pc = penult_bass % 12
    final_sop_pc = final_sop % 12

    if (penult_bass_pc == dominant_pc and
            final_bass_pc == tonic_pc and
            final_sop_pc == tonic_pc):
        bar, beat = offset_to_bar_beat(final_sop_off, bar_duration)
        issues.append(Issue(
            category="NOTES",
            bar=bar,
            beat=beat,
            voices="",
            message=vocab.FEELS_CONCLUSIVE,
        ))

    return issues


def check_feels_half_stop(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
    tonic_pc: int,
) -> list[Issue]:
    """Detect half cadences (ending on V)."""
    issues: list[Issue] = []

    for phrase in phrases:
        bass = _notes_to_tuples(phrase.bass)
        if not bass:
            continue

        bass.sort(key=lambda x: x[0])
        final_off, final_pitch = bass[-1]

        dominant_pc = (tonic_pc + 7) % 12
        if final_pitch % 12 == dominant_pc:
            # Check it's not the very last phrase (that would be unusual)
            if phrase != phrases[-1]:
                bar, beat = offset_to_bar_beat(final_off, bar_duration)
                issues.append(Issue(
                    category="NOTES",
                    bar=bar,
                    beat=beat,
                    voices="",
                    message=vocab.FEELS_HALF_STOP,
                ))

    return issues


def check_same_pattern(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
) -> list[Issue]:
    """Detect sequences (same pattern transposed)."""
    issues: list[Issue] = []

    # Compare consecutive phrases for transposed patterns
    for i in range(1, len(phrases)):
        prev_phrase = phrases[i - 1]
        curr_phrase = phrases[i]

        prev_soprano = [n.pitch for n in prev_phrase.soprano]
        curr_soprano = [n.pitch for n in curr_phrase.soprano]

        if len(prev_soprano) != len(curr_soprano) or len(prev_soprano) < 3:
            continue

        # Check if intervals match (transposed)
        prev_intervals = [prev_soprano[j + 1] - prev_soprano[j]
                         for j in range(len(prev_soprano) - 1)]
        curr_intervals = [curr_soprano[j + 1] - curr_soprano[j]
                         for j in range(len(curr_soprano) - 1)]

        if prev_intervals == curr_intervals:
            # Same pattern - determine direction
            transposition = curr_soprano[0] - prev_soprano[0]
            if transposition == 0:
                continue  # Identical, not sequence

            direction = "higher" if transposition > 0 else "lower"
            source_bar = int(prev_phrase.soprano[0].offset // bar_duration) + 1

            bar, beat = offset_to_bar_beat(curr_phrase.soprano[0].offset, bar_duration)
            msg = vocab.SAME_PATTERN.format(source_bar=source_bar, direction=direction)
            issues.append(Issue(
                category="NOTES",
                bar=bar,
                beat=beat,
                voices="soprano",
                message=msg,
            ))

    return issues


def check_reaches_peak(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
) -> list[Issue]:
    """Detect climax (highest soprano note)."""
    issues: list[Issue] = []

    # Find global highest soprano note
    all_soprano: list[RealisedNote] = []
    for phrase in phrases:
        all_soprano.extend(phrase.soprano)

    if not all_soprano:
        return issues

    max_pitch = max(n.pitch for n in all_soprano)
    peak_notes = [n for n in all_soprano if n.pitch == max_pitch]

    # Report the first occurrence of the peak
    if peak_notes:
        peak = min(peak_notes, key=lambda n: n.offset)
        bar, beat = offset_to_bar_beat(peak.offset, bar_duration)
        issues.append(Issue(
            category="NOTES",
            bar=bar,
            beat=beat,
            voices="soprano",
            message=vocab.REACHES_PEAK,
        ))

    return issues


def collect_notes(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
    tonic_pc: int,
) -> list[Issue]:
    """Collect all NOTES observations."""
    issues: list[Issue] = []
    issues.extend(check_resolves_nicely(phrases, bar_duration))
    issues.extend(check_feels_conclusive(phrases, bar_duration, tonic_pc))
    issues.extend(check_feels_half_stop(phrases, bar_duration, tonic_pc))
    issues.extend(check_same_pattern(phrases, bar_duration))
    issues.extend(check_reaches_peak(phrases, bar_duration))
    return issues
