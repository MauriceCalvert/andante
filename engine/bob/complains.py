"""Soft constraint checks - COMPLAINS category."""
from fractions import Fraction

from engine.bob import vocabulary as vocab
from engine.bob.formatter import Issue, offset_to_bar_beat
from engine.engine_types import RealisedNote, RealisedPhrase
from engine.voice_checks import (
    MelodicPenalty,
    check_bar_duplication,
    check_consecutive_leaps,
    check_endless_trill,
    check_forbidden_intervals,
    check_leap_compensation,
    check_sequence_duplication,
    check_tritone_outline,
)
from engine.guards.spacing import (
    SPACING_ADJACENT_UPPER,
    SPACING_OUTER,
    check_spacing,
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


def _notes_to_tuples(notes: tuple[RealisedNote, ...]) -> list[tuple[Fraction, int]]:
    """Convert RealisedNotes to (offset, pitch) tuples."""
    return [(n.offset, n.pitch) for n in notes]


def _voice_name(idx: int, voice_count: int) -> str:
    """Get voice name."""
    names = _voice_names_for_count(voice_count)
    return names[idx] if idx < len(names) else f"v{idx}"


def _voice_pair_name(upper_idx: int, lower_idx: int, voice_count: int) -> str:
    """Get voice pair name."""
    return f"{_voice_name(upper_idx, voice_count)}-{_voice_name(lower_idx, voice_count)}"


def check_leap_compensation_complains(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
) -> list[Issue]:
    """Check for uncompensated leaps."""
    issues: list[Issue] = []
    for phrase in phrases:
        voice_count = len(phrase.voices)
        for v_idx, voice in enumerate(phrase.voices):
            melody = _notes_to_tuples(tuple(voice.notes))
            if len(melody) < 3:
                continue

            sorted_melody = sorted(melody, key=lambda x: x[0])
            for i in range(len(sorted_melody) - 2):
                off1, p1 = sorted_melody[i]
                off2, p2 = sorted_melody[i + 1]
                off3, p3 = sorted_melody[i + 2]

                interval1 = p2 - p1
                interval2 = p3 - p2

                if abs(interval1) <= 2:
                    continue

                is_step = abs(interval2) <= 2
                is_contrary = (interval1 > 0) != (interval2 > 0) and interval2 != 0

                if not (is_step and is_contrary):
                    bar, beat = offset_to_bar_beat(off2, bar_duration)
                    direction = "up" if interval1 > 0 else "down"
                    msg = vocab.LEAP_UNCOMP.format(direction=direction, semitones=abs(interval1))
                    issues.append(Issue(
                        category="COMPLAINS",
                        bar=bar,
                        beat=beat,
                        voices=_voice_name(v_idx, voice_count),
                        message=msg,
                    ))
    return issues


def check_consecutive_leaps_complains(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
) -> list[Issue]:
    """Check for consecutive leaps in same direction."""
    issues: list[Issue] = []
    for phrase in phrases:
        voice_count = len(phrase.voices)
        for v_idx, voice in enumerate(phrase.voices):
            melody = _notes_to_tuples(tuple(voice.notes))
            for p in check_consecutive_leaps(melody):
                bar, beat = offset_to_bar_beat(p.offset, bar_duration)
                issues.append(Issue(
                    category="COMPLAINS",
                    bar=bar,
                    beat=beat,
                    voices=_voice_name(v_idx, voice_count),
                    message=vocab.CONSECUTIVE_LEAPS,
                ))
    return issues


def check_tritone_outline_complains(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
) -> list[Issue]:
    """Check for tritone outlines."""
    issues: list[Issue] = []
    for phrase in phrases:
        voice_count = len(phrase.voices)
        for v_idx, voice in enumerate(phrase.voices):
            melody = _notes_to_tuples(tuple(voice.notes))
            for p in check_tritone_outline(melody):
                bar, beat = offset_to_bar_beat(p.offset, bar_duration)
                issues.append(Issue(
                    category="COMPLAINS",
                    bar=bar,
                    beat=beat,
                    voices=_voice_name(v_idx, voice_count),
                    message=vocab.TRITONE_OUTLINE,
                ))
    return issues


def check_forbidden_intervals_complains(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
) -> list[Issue]:
    """Check for forbidden melodic intervals."""
    issues: list[Issue] = []
    for phrase in phrases:
        voice_count = len(phrase.voices)
        for v_idx, voice in enumerate(phrase.voices):
            notes = sorted(voice.notes, key=lambda n: n.offset)
            if len(notes) < 2:
                continue

            for i in range(len(notes) - 1):
                n1, n2 = notes[i], notes[i + 1]
                interval = abs(n2.pitch - n1.pitch)
                bar, beat = offset_to_bar_beat(n2.offset, bar_duration)

                # Tritone (augmented fourth) = 6 semitones
                if interval == 6:
                    issues.append(Issue(
                        category="COMPLAINS",
                        bar=bar,
                        beat=beat,
                        voices=_voice_name(v_idx, voice_count),
                        message=vocab.AUGMENTED_INTERVAL.format(semitones=6),
                    ))
                # Seventh (minor=10, major=11 semitones)
                elif interval in (10, 11):
                    issues.append(Issue(
                        category="COMPLAINS",
                        bar=bar,
                        beat=beat,
                        voices=_voice_name(v_idx, voice_count),
                        message=vocab.SEVENTH_LEAP.format(semitones=interval),
                    ))
                # Beyond octave (> 12 semitones)
                elif interval > 12:
                    issues.append(Issue(
                        category="COMPLAINS",
                        bar=bar,
                        beat=beat,
                        voices=_voice_name(v_idx, voice_count),
                        message=vocab.BEYOND_OCTAVE.format(semitones=interval),
                    ))
    return issues


def check_spacing_complains(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
) -> list[Issue]:
    """Check for spacing violations."""
    issues: list[Issue] = []
    for phrase in phrases:
        voice_count = len(phrase.voices)
        if voice_count < 2:
            continue

        # Check adjacent upper voices
        for i in range(voice_count - 2):
            upper = _notes_to_tuples(tuple(phrase.voices[i].notes))
            lower = _notes_to_tuples(tuple(phrase.voices[i + 1].notes))
            for v in check_spacing(upper, lower, i, i + 1, SPACING_ADJACENT_UPPER):
                if v.type == "spacing_too_wide":
                    bar, beat = offset_to_bar_beat(v.offset, bar_duration)
                    interval = v.upper_pitch - v.lower_pitch
                    msg = vocab.SPACING_WIDE_UPPER.format(semitones=interval)
                    issues.append(Issue(
                        category="COMPLAINS",
                        bar=bar,
                        beat=beat,
                        voices=_voice_pair_name(v.upper_index, v.lower_index, voice_count),
                        message=msg,
                    ))

        # Check outer voices
        soprano = _notes_to_tuples(phrase.soprano)
        bass = _notes_to_tuples(phrase.bass)
        for v in check_spacing(soprano, bass, 0, voice_count - 1, SPACING_OUTER):
            if v.type == "spacing_too_wide":
                bar, beat = offset_to_bar_beat(v.offset, bar_duration)
                interval = v.upper_pitch - v.lower_pitch
                msg = vocab.SPACING_WIDE_OUTER.format(semitones=interval)
                issues.append(Issue(
                    category="COMPLAINS",
                    bar=bar,
                    beat=beat,
                    voices="soprano-bass",
                    message=msg,
                ))
    return issues


def check_monotonous_rhythm_complains(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
    threshold_bars: int = 4,
) -> list[Issue]:
    """Check for monotonous rhythm (same duration pattern repeated)."""
    issues: list[Issue] = []

    for phrase in phrases:
        voice_count = len(phrase.voices)
        for v_idx, voice in enumerate(phrase.voices):
            notes = list(voice.notes)
            if not notes:
                continue

            # Group durations by bar
            bars_durations: dict[int, tuple[Fraction, ...]] = {}
            for note in notes:
                bar_num = int(note.offset // bar_duration)
                if bar_num not in bars_durations:
                    bars_durations[bar_num] = ()
                bars_durations[bar_num] = bars_durations[bar_num] + (note.duration,)

            # Find consecutive identical rhythm bars
            sorted_bars = sorted(bars_durations.keys())
            if len(sorted_bars) < threshold_bars:
                continue

            run_start = 0
            for i in range(1, len(sorted_bars)):
                if (sorted_bars[i] == sorted_bars[i - 1] + 1 and
                        bars_durations[sorted_bars[i]] == bars_durations[sorted_bars[i - 1]]):
                    continue
                else:
                    run_len = i - run_start
                    if run_len >= threshold_bars:
                        start_bar = sorted_bars[run_start] + 1
                        end_bar = sorted_bars[i - 1] + 1
                        msg = vocab.MONOTONOUS_RHYTHM.format(bars=run_len)
                        issues.append(Issue(
                            category="COMPLAINS",
                            bar=start_bar,
                            beat=1.0,
                            voices=_voice_name(v_idx, voice_count),
                            message=msg,
                            end_bar=end_bar,
                        ))
                    run_start = i

            # Check final run
            run_len = len(sorted_bars) - run_start
            if run_len >= threshold_bars:
                start_bar = sorted_bars[run_start] + 1
                end_bar = sorted_bars[-1] + 1
                msg = vocab.MONOTONOUS_RHYTHM.format(bars=run_len)
                issues.append(Issue(
                    category="COMPLAINS",
                    bar=start_bar,
                    beat=1.0,
                    voices=_voice_name(v_idx, voice_count),
                    message=msg,
                    end_bar=end_bar,
                ))

    return issues


def check_static_voice_complains(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
    threshold_beats: int = 4,
) -> list[Issue]:
    """Check for static voice (same pitch for too long)."""
    issues: list[Issue] = []

    for phrase in phrases:
        voice_count = len(phrase.voices)
        for v_idx, voice in enumerate(phrase.voices):
            notes = sorted(voice.notes, key=lambda n: n.offset)
            if len(notes) < 2:
                continue

            run_start = 0
            for i in range(1, len(notes)):
                if notes[i].pitch == notes[run_start].pitch:
                    continue
                else:
                    total_dur = sum(
                        float(notes[j].duration) for j in range(run_start, i)
                    )
                    if total_dur >= threshold_beats:
                        bar, beat = offset_to_bar_beat(notes[run_start].offset, bar_duration)
                        msg = vocab.STATIC_VOICE.format(beats=int(total_dur))
                        issues.append(Issue(
                            category="COMPLAINS",
                            bar=bar,
                            beat=beat,
                            voices=_voice_name(v_idx, voice_count),
                            message=msg,
                        ))
                    run_start = i

            # Check final run
            total_dur = sum(
                float(notes[j].duration) for j in range(run_start, len(notes))
            )
            if total_dur >= threshold_beats:
                bar, beat = offset_to_bar_beat(notes[run_start].offset, bar_duration)
                msg = vocab.STATIC_VOICE.format(beats=int(total_dur))
                issues.append(Issue(
                    category="COMPLAINS",
                    bar=bar,
                    beat=beat,
                    voices=_voice_name(v_idx, voice_count),
                    message=msg,
                ))

    return issues


def check_static_harmony_complains(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
    threshold_bars: int = 4,
) -> list[Issue]:
    """Check for static harmony (same bass pitch class for too many bars)."""
    issues: list[Issue] = []

    # Collect all bass notes across phrases
    all_bass: list[RealisedNote] = []
    for phrase in phrases:
        all_bass.extend(phrase.bass)
    all_bass.sort(key=lambda n: n.offset)

    if not all_bass:
        return issues

    # Group by bar and get pitch class
    bar_pc: dict[int, int] = {}
    for note in all_bass:
        bar_num = int(note.offset // bar_duration)
        if bar_num not in bar_pc:
            bar_pc[bar_num] = note.pitch % 12

    sorted_bars = sorted(bar_pc.keys())
    if len(sorted_bars) < threshold_bars:
        return issues

    run_start = 0
    for i in range(1, len(sorted_bars)):
        if (sorted_bars[i] == sorted_bars[i - 1] + 1 and
                bar_pc[sorted_bars[i]] == bar_pc[sorted_bars[run_start]]):
            continue
        else:
            run_len = i - run_start
            if run_len >= threshold_bars:
                start_bar = sorted_bars[run_start] + 1
                end_bar = sorted_bars[i - 1] + 1
                msg = vocab.STATIC_HARMONY.format(bars=run_len)
                issues.append(Issue(
                    category="COMPLAINS",
                    bar=start_bar,
                    beat=1.0,
                    voices="",
                    message=msg,
                    end_bar=end_bar,
                ))
            run_start = i

    # Check final run
    run_len = len(sorted_bars) - run_start
    if run_len >= threshold_bars:
        start_bar = sorted_bars[run_start] + 1
        end_bar = sorted_bars[-1] + 1
        msg = vocab.STATIC_HARMONY.format(bars=run_len)
        issues.append(Issue(
            category="COMPLAINS",
            bar=start_bar,
            beat=1.0,
            voices="",
            message=msg,
            end_bar=end_bar,
        ))

    return issues


def check_endless_alternation_complains(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
) -> list[Issue]:
    """Check for endless trill/alternation."""
    issues: list[Issue] = []
    for phrase in phrases:
        voice_count = len(phrase.voices)
        for v_idx, voice in enumerate(phrase.voices):
            melody = _notes_to_tuples(tuple(voice.notes))
            for v in check_endless_trill(melody):
                bar, beat = offset_to_bar_beat(v.offset, bar_duration)
                issues.append(Issue(
                    category="COMPLAINS",
                    bar=bar,
                    beat=beat,
                    voices=_voice_name(v_idx, voice_count),
                    message=vocab.ENDLESS_ALTERNATION,
                ))
    return issues


def check_bar_duplication_complains(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
) -> list[Issue]:
    """Check for identical consecutive bars."""
    issues: list[Issue] = []
    for phrase in phrases:
        voice_count = len(phrase.voices)
        for v_idx, voice in enumerate(phrase.voices):
            melody = _notes_to_tuples(tuple(voice.notes))
            for v in check_bar_duplication(melody, bar_duration):
                bar, beat = offset_to_bar_beat(v.offset, bar_duration)
                issues.append(Issue(
                    category="COMPLAINS",
                    bar=bar,
                    beat=beat,
                    voices=_voice_name(v_idx, voice_count),
                    message=vocab.BAR_DUPLICATION,
                ))
    return issues


def check_sequence_duplication_complains(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
) -> list[Issue]:
    """Check for overly long repeated sequences."""
    issues: list[Issue] = []
    for phrase in phrases:
        voice_count = len(phrase.voices)
        for v_idx, voice in enumerate(phrase.voices):
            melody = _notes_to_tuples(tuple(voice.notes))
            for v in check_sequence_duplication(melody):
                bar, beat = offset_to_bar_beat(v.offset, bar_duration)
                issues.append(Issue(
                    category="COMPLAINS",
                    bar=bar,
                    beat=beat,
                    voices=_voice_name(v_idx, voice_count),
                    message=vocab.SEQUENCE_TOO_LONG,
                ))
    return issues


def collect_complains(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction,
) -> list[Issue]:
    """Collect all COMPLAINS issues."""
    issues: list[Issue] = []
    issues.extend(check_leap_compensation_complains(phrases, bar_duration))
    issues.extend(check_consecutive_leaps_complains(phrases, bar_duration))
    issues.extend(check_tritone_outline_complains(phrases, bar_duration))
    issues.extend(check_forbidden_intervals_complains(phrases, bar_duration))
    issues.extend(check_spacing_complains(phrases, bar_duration))
    issues.extend(check_monotonous_rhythm_complains(phrases, bar_duration))
    issues.extend(check_static_voice_complains(phrases, bar_duration))
    issues.extend(check_static_harmony_complains(phrases, bar_duration))
    issues.extend(check_endless_alternation_complains(phrases, bar_duration))
    issues.extend(check_bar_duplication_complains(phrases, bar_duration))
    issues.extend(check_sequence_duplication_complains(phrases, bar_duration))
    return issues
