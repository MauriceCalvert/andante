"""Fault detection for composed pieces.

Reports issues in Bob's vocabulary: plain English, note names, bar.beat locations.
Supports 1-4 voices.

Usage:
    from builder.faults import find_faults, print_faults
    faults = find_faults([soprano_notes, bass_notes], "4/4")
    print_faults(faults)

Fault Categories
================

ERRORS (Bob refuses to play - hard counterpoint violations):

    parallel_fifth      Consecutive perfect fifths by similar motion.
                        Example: C4/F3 -> D4/G3 (both P5, both voices ascend)

    parallel_octave     Consecutive perfect octaves by similar motion.
                        Example: C4/C3 -> D4/D3 (both P8, both voices ascend)

    parallel_unison     Consecutive unisons by similar motion.
                        Example: C4/C4 -> D4/D4 (both voices on same pitch)

    direct_fifth        Similar motion into perfect fifth with soprano leap.
                        Soprano leaps (>2 semitones) while both voices move
                        same direction into a P5. Steps are permitted.

    direct_octave       Similar motion into perfect octave with soprano leap.
                        Same as direct_fifth but arriving at P8/unison.

    unprepared_dissonance   Dissonance on strong beat without preparation.
                            Strong beats: beat 1 in all metres, beat 3 in 4/4.
                            Dissonant intervals: m2, M2, P4, tritone, m7, M7.
                            Preparation: dissonant note must sound in same
                            voice on immediately preceding beat.

    unresolved_dissonance   Prepared dissonance not resolved by step.
                            Resolution: suspended voice must move by 1-2
                            semitones on the following beat.

WARNINGS (Bob complains but plays - voice-leading problems):

    ugly_leap           Augmented or diminished melodic intervals.
                        Includes: tritone (6), minor 9th (13), major 7th (11),
                        minor 7th (10) when larger than a step.

    consecutive_leaps   Two leaps (>4 semitones) in same direction.
                        Creates awkward melodic outline. Example: C4-G4-D5.

    unreversed_leap     Leap not followed by contrary stepwise motion.
                        Good practice: large leap should reverse by step.
                        Example: C4-G4-A4 (leap up, step up = bad)

    tessitura_excursion Note beyond voice's comfortable range.
                        Each voice has a median pitch and 7-semitone span.
                        Notes beyond span trigger warnings with distance.

    voice_crossing      Lower voice sounds above upper voice (persistent).
                        Brief crossings are acceptable; 4+ consecutive
                        crossings trigger warning.

    voice_overlap       Voice moves to pitch just vacated by other voice.
                        Example: Soprano on G4, bass moves to G4 as soprano
                        leaves. Creates momentary voice identity confusion.

    cross_relation      Chromatic contradiction between voices.
                        Example: F# in soprano against F natural in bass
                        on adjacent beats. Creates harmonic "false relation".

    spacing_error       Adjacent voices more than two octaves apart.
                        Standard spacing: upper voices within octave,
                        bass may be further. >24 semitones triggers warning.

INFO (stylistic observations - not errors):

    parallel_rhythm     Both voices in identical rhythm (homorhythm).
                        More than 2 consecutive bars with same rhythm
                        pattern in all voices. Reduces independence.

    parallel_thirds     Extended parallel thirds (>4 consecutive).
                        Acceptable but monotonous. Variety preferred.

    parallel_sixths     Extended parallel sixths (>4 consecutive).
                        Same as parallel_thirds.

    melodic_repetition  Literal bar repetition in same voice.
                        Bar N+1 has identical pitches to bar N.

    sequence_overuse    Pattern repeated more than twice in sequence.
                        Rule of Three: sequences lose effect after 2 reps.

    monotonous_contour  Excessive stepwise motion without leaps.
                        6+ consecutive steps in any direction.
                        Melody becomes scale-like, lacks character.

    excessive_leaps     Leap ratio exceeds 40% of melodic intervals.
                        Too disjunct; melody becomes fragmented.

    weak_cadence        Final notes don't form proper cadence.
                        Expects unison, fifth, or octave at end.

    missing_contrary_motion
                        8+ consecutive moves without contrary motion.
                        Voices should interact; extended parallel/similar
                        motion reduces independence.

Tessitura Defaults (MIDI pitch medians):
    1 voice:  soprano=70 (Bb4)
    2 voices: soprano=70, bass=48 (C3)
    3 voices: soprano=70, alto=60 (C4), bass=48
    4 voices: soprano=70, alto=60, tenor=54 (F#3), bass=48

Output Format:
    [SEVERITY] bar.beat vN,M category: message
    Example: [ERROR] 3.2 v0,1 parallel_fifth: Parallel fifths: G4/C4 to A4/D4
"""
from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence

from builder.types import Note
from shared.constants import (
    DEFAULT_TESSITURA_MEDIANS,
    NOTE_NAMES_SHARP,
    TESSITURA_COMFORTABLE_SPAN,
)


@dataclass(frozen=True)
class Fault:
    """Single fault report."""
    severity: str
    category: str
    bar_beat: str
    voices: tuple[int, ...]
    message: str
STEP_MAX: int = 2
SKIP_MAX: int = 4
LEAP_MAX: int = 7
CONSECUTIVE_IMPERFECT_LIMIT: int = 4
CONSECUTIVE_SAME_DIRECTION_LIMIT: int = 6
HOMORHYTHM_BAR_LIMIT: int = 2
SEQUENCE_REPEAT_LIMIT: int = 2


def _bar_duration(metre: str) -> Fraction:
    """Compute bar duration in whole notes."""
    num, den = map(int, metre.split("/"))
    return Fraction(num, den)


def _beat_duration(metre: str) -> Fraction:
    """Compute beat duration in whole notes."""
    _, den = map(int, metre.split("/"))
    return Fraction(1, den)


def _extract_bar_pitches(
    notes: Sequence[Note],
    bar: int,
    metre: str,
) -> list[int]:
    """Extract pitches from a specific bar."""
    bar_dur: Fraction = _bar_duration(metre)
    bar_start: Fraction = (bar - 1) * bar_dur
    bar_end: Fraction = bar * bar_dur
    return [n.pitch for n in notes if bar_start <= n.offset < bar_end]


def _extract_bar_rhythm(
    notes: Sequence[Note],
    bar: int,
    metre: str,
) -> tuple[Fraction, ...]:
    """Extract rhythm pattern (durations) from a specific bar."""
    bar_dur: Fraction = _bar_duration(metre)
    bar_start: Fraction = (bar - 1) * bar_dur
    bar_end: Fraction = bar * bar_dur
    return tuple(n.duration for n in notes if bar_start <= n.offset < bar_end)


def _get_bar_count(notes: Sequence[Note], metre: str) -> int:
    """Compute total bar count from notes."""
    if not notes:
        return 0
    max_end: Fraction = max(n.offset + n.duration for n in notes)
    bar_dur: Fraction = _bar_duration(metre)
    return int((max_end + bar_dur - Fraction(1, 1000)) // bar_dur)


def _interval_semitones(pitch_a: int, pitch_b: int) -> int:
    """Signed interval in semitones."""
    return pitch_b - pitch_a


def _is_strong_beat(offset: Fraction, metre: str) -> bool:
    """Check if offset falls on a strong beat."""
    num, _ = map(int, metre.split("/"))
    bar_dur: Fraction = _bar_duration(metre)
    beat_dur: Fraction = _beat_duration(metre)
    offset_in_bar: Fraction = offset % bar_dur
    if num == 4:
        return offset_in_bar in {Fraction(0), beat_dur * 2}
    return offset_in_bar == Fraction(0)


def _midi_to_name(midi: int) -> str:
    """Convert MIDI pitch to note name."""
    octave: int = (midi // 12) - 1
    pc: int = midi % 12
    return f"{NOTE_NAMES_SHARP[pc]}{octave}"


def _motion_type(
    pitch_a_from: int,
    pitch_a_to: int,
    pitch_b_from: int,
    pitch_b_to: int,
) -> str:
    """Classify motion between two voice pairs."""
    motion_a: int = pitch_a_to - pitch_a_from
    motion_b: int = pitch_b_to - pitch_b_from
    if motion_a == 0 and motion_b == 0:
        return "static"
    if motion_a == 0 or motion_b == 0:
        return "oblique"
    if (motion_a > 0) == (motion_b > 0):
        return "similar"
    return "contrary"


def _offset_to_bar_beat(offset: Fraction, metre: str) -> str:
    """Convert offset to bar.beat string."""
    bar_dur: Fraction = _bar_duration(metre)
    beat_dur: Fraction = _beat_duration(metre)
    bar: int = int(offset // bar_dur) + 1
    beat_offset: Fraction = offset % bar_dur
    beat: int = int(beat_offset // beat_dur) + 1
    return f"{bar}.{beat}"


def _simple_interval(pitch_a: int, pitch_b: int) -> int:
    """Interval in semitones, reduced to single octave."""
    return abs(pitch_a - pitch_b) % 12


def _check_consecutive_leaps(
    voice_notes: Sequence[Note],
    voice_idx: int,
    metre: str,
) -> list[Fault]:
    """Check for two leaps in same direction."""
    faults: list[Fault] = []
    pitches: list[tuple[Fraction, int]] = [(n.offset, n.pitch) for n in voice_notes]
    for i in range(len(pitches) - 2):
        int1: int = pitches[i + 1][1] - pitches[i][1]
        int2: int = pitches[i + 2][1] - pitches[i + 1][1]
        if abs(int1) > SKIP_MAX and abs(int2) > SKIP_MAX:
            if (int1 > 0) == (int2 > 0):
                loc: str = _offset_to_bar_beat(pitches[i + 1][0], metre)
                p1: str = _midi_to_name(pitches[i][1])
                p2: str = _midi_to_name(pitches[i + 1][1])
                p3: str = _midi_to_name(pitches[i + 2][1])
                faults.append(Fault(
                    severity="warning",
                    category="consecutive_leaps",
                    bar_beat=loc,
                    voices=(voice_idx,),
                    message=f"Two leaps same direction: {p1}-{p2}-{p3}",
                ))
    return faults


def _check_cross_relation(
    voices: Sequence[Sequence[Note]],
    metre: str,
) -> list[Fault]:
    """Check for chromatic contradiction between voices."""
    faults: list[Fault] = []
    all_notes: list[tuple[Fraction, int, int]] = []
    for v_idx, voice in enumerate(voices):
        for note in voice:
            all_notes.append((note.offset, note.pitch, v_idx))
    all_notes.sort(key=lambda x: x[0])
    by_offset: dict[Fraction, list[tuple[int, int]]] = {}
    for offset, pitch, v_idx in all_notes:
        if offset not in by_offset:
            by_offset[offset] = []
        by_offset[offset].append((pitch, v_idx))
    offsets: list[Fraction] = sorted(by_offset.keys())
    for i in range(len(offsets) - 1):
        curr_pcs: dict[int, tuple[int, int]] = {}
        for pitch, v_idx in by_offset[offsets[i]]:
            pc: int = pitch % 12
            curr_pcs[pc] = (pitch, v_idx)
        for pitch, v_idx in by_offset[offsets[i + 1]]:
            pc: int = pitch % 12
            for other_pc, (other_pitch, other_v) in curr_pcs.items():
                if other_v != v_idx and abs(pc - other_pc) == 1:
                    if (pc in {1, 3, 6, 8, 10} or other_pc in {1, 3, 6, 8, 10}):
                        loc: str = _offset_to_bar_beat(offsets[i + 1], metre)
                        n1: str = _midi_to_name(other_pitch)
                        n2: str = _midi_to_name(pitch)
                        faults.append(Fault(
                            severity="warning",
                            category="cross_relation",
                            bar_beat=loc,
                            voices=(other_v, v_idx),
                            message=f"Chromatic clash: {n1} against {n2}",
                        ))
    return faults


def _check_direct_motion(
    voices: Sequence[Sequence[Note]],
    metre: str,
) -> list[Fault]:
    """Check for direct fifths/octaves with soprano leap."""
    faults: list[Fault] = []
    if len(voices) < 2:
        return faults
    soprano: Sequence[Note] = voices[0]
    for other_idx in range(1, len(voices)):
        other: Sequence[Note] = voices[other_idx]
        s_by_off: dict[Fraction, int] = {n.offset: n.pitch for n in soprano}
        o_by_off: dict[Fraction, int] = {n.offset: n.pitch for n in other}
        common: list[Fraction] = sorted(set(s_by_off.keys()) & set(o_by_off.keys()))
        for i in range(len(common) - 1):
            off1, off2 = common[i], common[i + 1]
            s1, s2 = s_by_off[off1], s_by_off[off2]
            o1, o2 = o_by_off[off1], o_by_off[off2]
            motion: str = _motion_type(s1, s2, o1, o2)
            if motion != "similar":
                continue
            soprano_leap: int = abs(s2 - s1)
            if soprano_leap <= STEP_MAX:
                continue
            interval: int = _simple_interval(s2, o2)
            if interval == 7:
                loc: str = _offset_to_bar_beat(off2, metre)
                faults.append(Fault(
                    severity="error",
                    category="direct_fifth",
                    bar_beat=loc,
                    voices=(0, other_idx),
                    message=f"Similar motion to fifth with soprano leap: "
                            f"{_midi_to_name(s1)}-{_midi_to_name(s2)}",
                ))
            if interval == 0:
                loc = _offset_to_bar_beat(off2, metre)
                faults.append(Fault(
                    severity="error",
                    category="direct_octave",
                    bar_beat=loc,
                    voices=(0, other_idx),
                    message=f"Similar motion to octave with soprano leap: "
                            f"{_midi_to_name(s1)}-{_midi_to_name(s2)}",
                ))
    return faults


def _check_dissonance(
    voices: Sequence[Sequence[Note]],
    metre: str,
) -> list[Fault]:
    """Check for unprepared/unresolved dissonances on strong beats."""
    faults: list[Fault] = []
    if len(voices) < 2:
        return faults
    consonant: frozenset[int] = frozenset({0, 3, 4, 7, 8, 9})
    soprano: Sequence[Note] = voices[0]
    bass: Sequence[Note] = voices[-1]
    s_by_off: dict[Fraction, int] = {n.offset: n.pitch for n in soprano}
    b_by_off: dict[Fraction, int] = {n.offset: n.pitch for n in bass}
    common: list[Fraction] = sorted(set(s_by_off.keys()) & set(b_by_off.keys()))
    for i, off in enumerate(common):
        if not _is_strong_beat(off, metre):
            continue
        s_pitch: int = s_by_off[off]
        b_pitch: int = b_by_off[off]
        interval: int = _simple_interval(s_pitch, b_pitch)
        if interval in consonant:
            continue
        loc: str = _offset_to_bar_beat(off, metre)
        prepared: bool = False
        if i > 0:
            prev_off: Fraction = common[i - 1]
            if prev_off in s_by_off and s_by_off[prev_off] == s_pitch:
                prepared = True
        if not prepared:
            faults.append(Fault(
                severity="error",
                category="unprepared_dissonance",
                bar_beat=loc,
                voices=(0, len(voices) - 1),
                message=f"Unprepared dissonance on strong beat: "
                        f"{_midi_to_name(s_pitch)}/{_midi_to_name(b_pitch)}",
            ))
            continue
        resolved: bool = False
        if i < len(common) - 1:
            next_off: Fraction = common[i + 1]
            if next_off in s_by_off:
                step: int = abs(s_by_off[next_off] - s_pitch)
                if step in {1, 2}:
                    resolved = True
        if not resolved:
            faults.append(Fault(
                severity="error",
                category="unresolved_dissonance",
                bar_beat=loc,
                voices=(0, len(voices) - 1),
                message=f"Dissonance not resolved by step: "
                        f"{_midi_to_name(s_pitch)}/{_midi_to_name(b_pitch)}",
            ))
    return faults


def _check_excessive_leaps(
    voice_notes: Sequence[Note],
    voice_idx: int,
    metre: str,
) -> list[Fault]:
    """Check if leap ratio is too high."""
    faults: list[Fault] = []
    if len(voice_notes) < 10:
        return faults
    leap_count: int = 0
    for i in range(len(voice_notes) - 1):
        interval: int = abs(voice_notes[i + 1].pitch - voice_notes[i].pitch)
        if interval > SKIP_MAX:
            leap_count += 1
    ratio: float = leap_count / (len(voice_notes) - 1)
    if ratio > 0.4:
        faults.append(Fault(
            severity="info",
            category="excessive_leaps",
            bar_beat="1.1",
            voices=(voice_idx,),
            message=f"Leap ratio {ratio:.0%} exceeds 40% threshold",
        ))
    return faults


def _check_melodic_repetition(
    voice_notes: Sequence[Note],
    voice_idx: int,
    metre: str,
) -> list[Fault]:
    """Check for literal bar repetition."""
    faults: list[Fault] = []
    bar_count: int = _get_bar_count(voice_notes, metre)
    for bar in range(1, bar_count):
        pitches_curr: list[int] = _extract_bar_pitches(voice_notes, bar, metre)
        pitches_next: list[int] = _extract_bar_pitches(voice_notes, bar + 1, metre)
        if pitches_curr and pitches_curr == pitches_next:
            faults.append(Fault(
                severity="info",
                category="melodic_repetition",
                bar_beat=f"{bar + 1}.1",
                voices=(voice_idx,),
                message=f"Bar {bar + 1} repeats bar {bar} literally",
            ))
    return faults


def _check_missing_contrary(
    voices: Sequence[Sequence[Note]],
    metre: str,
) -> list[Fault]:
    """Check for extended passage without contrary motion."""
    faults: list[Fault] = []
    if len(voices) < 2:
        return faults
    soprano: Sequence[Note] = voices[0]
    bass: Sequence[Note] = voices[-1]
    s_by_off: dict[Fraction, int] = {n.offset: n.pitch for n in soprano}
    b_by_off: dict[Fraction, int] = {n.offset: n.pitch for n in bass}
    common: list[Fraction] = sorted(set(s_by_off.keys()) & set(b_by_off.keys()))
    no_contrary_count: int = 0
    max_no_contrary: int = 0
    worst_loc: Fraction = Fraction(0)
    for i in range(len(common) - 1):
        off1, off2 = common[i], common[i + 1]
        motion: str = _motion_type(
            s_by_off[off1], s_by_off[off2],
            b_by_off[off1], b_by_off[off2],
        )
        if motion == "contrary":
            no_contrary_count = 0
        else:
            no_contrary_count += 1
            if no_contrary_count > max_no_contrary:
                max_no_contrary = no_contrary_count
                worst_loc = off2
    if max_no_contrary >= 8:
        faults.append(Fault(
            severity="info",
            category="missing_contrary_motion",
            bar_beat=_offset_to_bar_beat(worst_loc, metre),
            voices=(0, len(voices) - 1),
            message=f"{max_no_contrary} consecutive moves without contrary motion",
        ))
    return faults


def _check_monotonous_contour(
    voice_notes: Sequence[Note],
    voice_idx: int,
    metre: str,
) -> list[Fault]:
    """Check for excessive stepwise motion without leaps."""
    faults: list[Fault] = []
    consecutive_steps: int = 0
    max_steps: int = 0
    worst_offset: Fraction = Fraction(0)
    for i in range(len(voice_notes) - 1):
        interval: int = abs(voice_notes[i + 1].pitch - voice_notes[i].pitch)
        if interval <= STEP_MAX:
            consecutive_steps += 1
            if consecutive_steps > max_steps:
                max_steps = consecutive_steps
                worst_offset = voice_notes[i + 1].offset
        else:
            consecutive_steps = 0
    if max_steps >= CONSECUTIVE_SAME_DIRECTION_LIMIT:
        faults.append(Fault(
            severity="info",
            category="monotonous_contour",
            bar_beat=_offset_to_bar_beat(worst_offset, metre),
            voices=(voice_idx,),
            message=f"{max_steps} consecutive stepwise moves without a leap",
        ))
    return faults


def _check_parallel_imperfect(
    voices: Sequence[Sequence[Note]],
    metre: str,
) -> list[Fault]:
    """Check for extended parallel thirds or sixths."""
    faults: list[Fault] = []
    if len(voices) < 2:
        return faults
    thirds: frozenset[int] = frozenset({3, 4})
    sixths: frozenset[int] = frozenset({8, 9})
    for v_a in range(len(voices)):
        for v_b in range(v_a + 1, len(voices)):
            a_by_off: dict[Fraction, int] = {n.offset: n.pitch for n in voices[v_a]}
            b_by_off: dict[Fraction, int] = {n.offset: n.pitch for n in voices[v_b]}
            common: list[Fraction] = sorted(set(a_by_off.keys()) & set(b_by_off.keys()))
            third_run: int = 0
            sixth_run: int = 0
            third_start: Fraction = Fraction(0)
            sixth_start: Fraction = Fraction(0)
            for off in common:
                interval: int = _simple_interval(a_by_off[off], b_by_off[off])
                if interval in thirds:
                    if third_run == 0:
                        third_start = off
                    third_run += 1
                else:
                    if third_run > CONSECUTIVE_IMPERFECT_LIMIT:
                        faults.append(Fault(
                            severity="info",
                            category="parallel_thirds",
                            bar_beat=_offset_to_bar_beat(third_start, metre),
                            voices=(v_a, v_b),
                            message=f"{third_run} consecutive parallel thirds",
                        ))
                    third_run = 0
                if interval in sixths:
                    if sixth_run == 0:
                        sixth_start = off
                    sixth_run += 1
                else:
                    if sixth_run > CONSECUTIVE_IMPERFECT_LIMIT:
                        faults.append(Fault(
                            severity="info",
                            category="parallel_sixths",
                            bar_beat=_offset_to_bar_beat(sixth_start, metre),
                            voices=(v_a, v_b),
                            message=f"{sixth_run} consecutive parallel sixths",
                        ))
                    sixth_run = 0
            if third_run > CONSECUTIVE_IMPERFECT_LIMIT:
                faults.append(Fault(
                    severity="info",
                    category="parallel_thirds",
                    bar_beat=_offset_to_bar_beat(third_start, metre),
                    voices=(v_a, v_b),
                    message=f"{third_run} consecutive parallel thirds",
                ))
            if sixth_run > CONSECUTIVE_IMPERFECT_LIMIT:
                faults.append(Fault(
                    severity="info",
                    category="parallel_sixths",
                    bar_beat=_offset_to_bar_beat(sixth_start, metre),
                    voices=(v_a, v_b),
                    message=f"{sixth_run} consecutive parallel sixths",
                ))
    return faults


def _check_parallel_perfect(
    voices: Sequence[Sequence[Note]],
    metre: str,
) -> list[Fault]:
    """Check for parallel fifths, octaves, unisons."""
    faults: list[Fault] = []
    if len(voices) < 2:
        return faults
    for v_a in range(len(voices)):
        for v_b in range(v_a + 1, len(voices)):
            a_by_off: dict[Fraction, int] = {n.offset: n.pitch for n in voices[v_a]}
            b_by_off: dict[Fraction, int] = {n.offset: n.pitch for n in voices[v_b]}
            common: list[Fraction] = sorted(set(a_by_off.keys()) & set(b_by_off.keys()))
            for i in range(len(common) - 1):
                off1, off2 = common[i], common[i + 1]
                a1, a2 = a_by_off[off1], a_by_off[off2]
                b1, b2 = b_by_off[off1], b_by_off[off2]
                motion: str = _motion_type(a1, a2, b1, b2)
                if motion not in {"similar", "parallel"}:
                    continue
                if motion == "parallel" and a1 == a2 and b1 == b2:
                    continue
                int1: int = _simple_interval(a1, b1)
                int2: int = _simple_interval(a2, b2)
                if int1 == int2 and int1 in {0, 7}:
                    loc: str = _offset_to_bar_beat(off2, metre)
                    if int1 == 0:
                        cat: str = "parallel_unison" if abs(a2 - b2) < 12 else "parallel_octave"
                    else:
                        cat = "parallel_fifth"
                    faults.append(Fault(
                        severity="error",
                        category=cat,
                        bar_beat=loc,
                        voices=(v_a, v_b),
                        message=f"Parallel {cat.split('_')[1]}s: "
                                f"{_midi_to_name(a1)}/{_midi_to_name(b1)} to "
                                f"{_midi_to_name(a2)}/{_midi_to_name(b2)}",
                    ))
    return faults


def _check_parallel_rhythm(
    voices: Sequence[Sequence[Note]],
    metre: str,
) -> list[Fault]:
    """Check for homorhythmic passages."""
    faults: list[Fault] = []
    if len(voices) < 2:
        return faults
    bar_count: int = max(_get_bar_count(v, metre) for v in voices if v)
    homorhythm_run: int = 0
    run_start: int = 1
    for bar in range(1, bar_count + 1):
        rhythms: list[tuple[Fraction, ...]] = [
            _extract_bar_rhythm(v, bar, metre) for v in voices
        ]
        all_same: bool = len(set(rhythms)) == 1 and rhythms[0]
        if all_same:
            if homorhythm_run == 0:
                run_start = bar
            homorhythm_run += 1
        else:
            if homorhythm_run > HOMORHYTHM_BAR_LIMIT:
                faults.append(Fault(
                    severity="info",
                    category="parallel_rhythm",
                    bar_beat=f"{run_start}.1",
                    voices=tuple(range(len(voices))),
                    message=f"Homorhythmic texture for {homorhythm_run} bars",
                ))
            homorhythm_run = 0
    if homorhythm_run > HOMORHYTHM_BAR_LIMIT:
        faults.append(Fault(
            severity="info",
            category="parallel_rhythm",
            bar_beat=f"{run_start}.1",
            voices=tuple(range(len(voices))),
            message=f"Homorhythmic texture for {homorhythm_run} bars",
        ))
    return faults


def _check_sequence_overuse(
    voice_notes: Sequence[Note],
    voice_idx: int,
    metre: str,
) -> list[Fault]:
    """Check for pattern repeated more than twice in sequence."""
    faults: list[Fault] = []
    if len(voice_notes) < 6:
        return faults
    intervals: list[int] = [
        voice_notes[i + 1].pitch - voice_notes[i].pitch
        for i in range(len(voice_notes) - 1)
    ]
    for pattern_len in range(2, min(6, len(intervals) // 2)):
        for start in range(len(intervals) - pattern_len * 3 + 1):
            pattern: list[int] = intervals[start:start + pattern_len]
            reps: int = 1
            pos: int = start + pattern_len
            while pos + pattern_len <= len(intervals):
                next_seg: list[int] = intervals[pos:pos + pattern_len]
                if next_seg == pattern:
                    reps += 1
                    pos += pattern_len
                else:
                    break
            if reps > SEQUENCE_REPEAT_LIMIT:
                loc: str = _offset_to_bar_beat(voice_notes[start].offset, metre)
                faults.append(Fault(
                    severity="info",
                    category="sequence_overuse",
                    bar_beat=loc,
                    voices=(voice_idx,),
                    message=f"Pattern of {pattern_len} intervals repeated {reps} times",
                ))
                break
    return faults


def _check_spacing(
    voices: Sequence[Sequence[Note]],
    metre: str,
) -> list[Fault]:
    """Check for spacing errors between adjacent voices."""
    faults: list[Fault] = []
    if len(voices) < 2:
        return faults
    for v_idx in range(len(voices) - 1):
        upper: Sequence[Note] = voices[v_idx]
        lower: Sequence[Note] = voices[v_idx + 1]
        u_by_off: dict[Fraction, int] = {n.offset: n.pitch for n in upper}
        l_by_off: dict[Fraction, int] = {n.offset: n.pitch for n in lower}
        common: list[Fraction] = sorted(set(u_by_off.keys()) & set(l_by_off.keys()))
        for off in common:
            gap: int = u_by_off[off] - l_by_off[off]
            if gap > 24:
                faults.append(Fault(
                    severity="warning",
                    category="spacing_error",
                    bar_beat=_offset_to_bar_beat(off, metre),
                    voices=(v_idx, v_idx + 1),
                    message=f"Voices more than two octaves apart: "
                            f"{_midi_to_name(u_by_off[off])}/{_midi_to_name(l_by_off[off])}",
                ))
    return faults


def _check_tessitura(
    voice_notes: Sequence[Note],
    voice_idx: int,
    metre: str,
    median: int,
) -> list[Fault]:
    """Check for notes outside comfortable tessitura (one fault per bar)."""
    faults: list[Fault] = []
    bar_dur: Fraction = _bar_duration(metre)
    bar_worst: dict[int, tuple[int, int, Fraction]] = {}
    for note in voice_notes:
        deviation: int = abs(note.pitch - median)
        if deviation > TESSITURA_COMFORTABLE_SPAN:
            bar: int = int(note.offset // bar_dur) + 1
            beyond: int = deviation - TESSITURA_COMFORTABLE_SPAN
            if bar not in bar_worst or beyond > bar_worst[bar][0]:
                bar_worst[bar] = (beyond, note.pitch, note.offset)
    for bar in sorted(bar_worst.keys()):
        beyond, pitch, offset = bar_worst[bar]
        faults.append(Fault(
            severity="warning",
            category="tessitura_excursion",
            bar_beat=_offset_to_bar_beat(offset, metre),
            voices=(voice_idx,),
            message=f"{_midi_to_name(pitch)} is {beyond} semitones beyond "
                    f"comfortable range (median {_midi_to_name(median)})",
        ))
    return faults


def _check_ugly_leaps(
    voice_notes: Sequence[Note],
    voice_idx: int,
    metre: str,
) -> list[Fault]:
    """Check for augmented or diminished intervals."""
    faults: list[Fault] = []
    ugly: frozenset[int] = frozenset({1, 6, 10, 11})
    for i in range(len(voice_notes) - 1):
        interval: int = abs(voice_notes[i + 1].pitch - voice_notes[i].pitch)
        simple: int = interval % 12
        if simple in ugly and interval > STEP_MAX:
            loc: str = _offset_to_bar_beat(voice_notes[i + 1].offset, metre)
            n1: str = _midi_to_name(voice_notes[i].pitch)
            n2: str = _midi_to_name(voice_notes[i + 1].pitch)
            if simple == 6:
                name: str = "tritone"
            elif simple == 1:
                name = "augmented octave" if interval > 12 else "minor ninth"
            elif simple == 10:
                name = "minor seventh"
            else:
                name = "major seventh"
            faults.append(Fault(
                severity="warning",
                category="ugly_leap",
                bar_beat=loc,
                voices=(voice_idx,),
                message=f"Ugly leap ({name}): {n1} to {n2}",
            ))
    return faults


def _check_unreversed_leap(
    voice_notes: Sequence[Note],
    voice_idx: int,
    metre: str,
) -> list[Fault]:
    """Check for leaps not followed by contrary step."""
    faults: list[Fault] = []
    for i in range(len(voice_notes) - 2):
        int1: int = voice_notes[i + 1].pitch - voice_notes[i].pitch
        int2: int = voice_notes[i + 2].pitch - voice_notes[i + 1].pitch
        if abs(int1) <= SKIP_MAX:
            continue
        contrary: bool = (int1 > 0) != (int2 > 0)
        is_step: bool = abs(int2) <= STEP_MAX
        if not (contrary and is_step):
            loc: str = _offset_to_bar_beat(voice_notes[i + 1].offset, metre)
            n1: str = _midi_to_name(voice_notes[i].pitch)
            n2: str = _midi_to_name(voice_notes[i + 1].pitch)
            n3: str = _midi_to_name(voice_notes[i + 2].pitch)
            faults.append(Fault(
                severity="warning",
                category="unreversed_leap",
                bar_beat=loc,
                voices=(voice_idx,),
                message=f"Leap not recovered: {n1}-{n2}-{n3}",
            ))
    return faults


def _check_voice_crossing(
    voices: Sequence[Sequence[Note]],
    metre: str,
) -> list[Fault]:
    """Check for persistent voice crossing."""
    faults: list[Fault] = []
    if len(voices) < 2:
        return faults
    for v_upper in range(len(voices) - 1):
        v_lower: int = v_upper + 1
        upper: Sequence[Note] = voices[v_upper]
        lower: Sequence[Note] = voices[v_lower]
        u_by_off: dict[Fraction, int] = {n.offset: n.pitch for n in upper}
        l_by_off: dict[Fraction, int] = {n.offset: n.pitch for n in lower}
        common: list[Fraction] = sorted(set(u_by_off.keys()) & set(l_by_off.keys()))
        crossing_run: int = 0
        run_start: Fraction = Fraction(0)
        for off in common:
            if l_by_off[off] > u_by_off[off]:
                if crossing_run == 0:
                    run_start = off
                crossing_run += 1
            else:
                if crossing_run >= 4:
                    faults.append(Fault(
                        severity="warning",
                        category="voice_crossing",
                        bar_beat=_offset_to_bar_beat(run_start, metre),
                        voices=(v_upper, v_lower),
                        message=f"Voices crossed for {crossing_run} consecutive notes",
                    ))
                crossing_run = 0
        if crossing_run >= 4:
            faults.append(Fault(
                severity="warning",
                category="voice_crossing",
                bar_beat=_offset_to_bar_beat(run_start, metre),
                voices=(v_upper, v_lower),
                message=f"Voices crossed for {crossing_run} consecutive notes",
            ))
    return faults


def _check_voice_overlap(
    voices: Sequence[Sequence[Note]],
    metre: str,
) -> list[Fault]:
    """Check for voice moving to pitch just vacated by other voice."""
    faults: list[Fault] = []
    if len(voices) < 2:
        return faults
    for v_a in range(len(voices)):
        for v_b in range(len(voices)):
            if v_a == v_b:
                continue
            a_notes: list[Note] = sorted(voices[v_a], key=lambda n: n.offset)
            b_notes: list[Note] = sorted(voices[v_b], key=lambda n: n.offset)
            b_by_off: dict[Fraction, int] = {n.offset: n.pitch for n in b_notes}
            for i in range(len(a_notes) - 1):
                curr_a: Note = a_notes[i]
                next_a: Note = a_notes[i + 1]
                if curr_a.offset in b_by_off:
                    b_pitch: int = b_by_off[curr_a.offset]
                    if next_a.pitch == b_pitch:
                        faults.append(Fault(
                            severity="warning",
                            category="voice_overlap",
                            bar_beat=_offset_to_bar_beat(next_a.offset, metre),
                            voices=(v_a, v_b),
                            message=f"Voice {v_a} moves to {_midi_to_name(next_a.pitch)} "
                                    f"just vacated by voice {v_b}",
                        ))
    return faults


def _check_weak_cadence(
    voices: Sequence[Sequence[Note]],
    metre: str,
) -> list[Fault]:
    """Check if final notes form a proper cadence."""
    faults: list[Fault] = []
    if len(voices) < 2:
        return faults
    soprano: Sequence[Note] = voices[0]
    bass: Sequence[Note] = voices[-1]
    if not soprano or not bass:
        return faults
    final_s: Note = max(soprano, key=lambda n: n.offset)
    final_b: Note = max(bass, key=lambda n: n.offset)
    interval: int = _simple_interval(final_s.pitch, final_b.pitch)
    if interval not in {0, 7}:
        faults.append(Fault(
            severity="info",
            category="weak_cadence",
            bar_beat=_offset_to_bar_beat(final_s.offset, metre),
            voices=(0, len(voices) - 1),
            message=f"Final interval is {interval} semitones, not unison/octave/fifth",
        ))
    return faults


def _default_medians_for_voice_count(voice_count: int) -> dict[int, int]:
    """Return appropriate tessitura medians for given voice count."""
    if voice_count == 1:
        return {0: 70}
    if voice_count == 2:
        return {0: 70, 1: 48}
    if voice_count == 3:
        return {0: 70, 1: 60, 2: 48}
    return {0: 70, 1: 60, 2: 54, 3: 48}


def find_faults(
    voices: Sequence[Sequence[Note]],
    metre: str,
    tessitura_medians: dict[int, int] | None = None,
) -> list[Fault]:
    """Find all faults in a multi-voice composition."""
    assert 1 <= len(voices) <= 4, f"Expected 1-4 voices, got {len(voices)}"
    assert "/" in metre, f"Invalid metre format: {metre}"
    medians: dict[int, int] = tessitura_medians or _default_medians_for_voice_count(len(voices))
    faults: list[Fault] = []
    for v_idx, voice in enumerate(voices):
        median: int = medians.get(v_idx, medians.get(0, 70))
        faults.extend(_check_consecutive_leaps(voice, v_idx, metre))
        faults.extend(_check_excessive_leaps(voice, v_idx, metre))
        faults.extend(_check_melodic_repetition(voice, v_idx, metre))
        faults.extend(_check_monotonous_contour(voice, v_idx, metre))
        faults.extend(_check_sequence_overuse(voice, v_idx, metre))
        faults.extend(_check_tessitura(voice, v_idx, metre, median))
        faults.extend(_check_ugly_leaps(voice, v_idx, metre))
        faults.extend(_check_unreversed_leap(voice, v_idx, metre))
    faults.extend(_check_cross_relation(voices, metre))
    faults.extend(_check_direct_motion(voices, metre))
    faults.extend(_check_dissonance(voices, metre))
    faults.extend(_check_missing_contrary(voices, metre))
    faults.extend(_check_parallel_imperfect(voices, metre))
    faults.extend(_check_parallel_perfect(voices, metre))
    faults.extend(_check_parallel_rhythm(voices, metre))
    faults.extend(_check_spacing(voices, metre))
    faults.extend(_check_voice_crossing(voices, metre))
    faults.extend(_check_voice_overlap(voices, metre))
    faults.extend(_check_weak_cadence(voices, metre))
    faults.sort(key=lambda f: (
        {"error": 0, "warning": 1, "info": 2}[f.severity],
        f.bar_beat,
        f.category,
    ))
    return faults


def print_faults(faults: list[Fault]) -> None:
    """Print faults in readable format."""
    if not faults:
        print("No faults found.")
        return
    errors: list[Fault] = [f for f in faults if f.severity == "error"]
    warnings: list[Fault] = [f for f in faults if f.severity == "warning"]
    infos: list[Fault] = [f for f in faults if f.severity == "info"]
    print(f"Found {len(faults)} faults: {len(errors)} errors, "
          f"{len(warnings)} warnings, {len(infos)} info")
    print()
    for fault in faults:
        sev: str = fault.severity.upper()
        voices_str: str = ",".join(str(v) for v in fault.voices)
        print(f"[{sev}] {fault.bar_beat} v{voices_str} {fault.category}: {fault.message}")
