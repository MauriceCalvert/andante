"""Fault detection for composed pieces.

Reports issues in Bob's vocabulary: plain English, note names, bar.beat locations.
Supports 1-4 voices.

Usage:
    from builder.faults import find_faults, print_faults
    faults = find_faults([soprano_notes, bass_notes], "4/4")
    print_faults(faults)

Fault Categories
================

    parallel_fifth      Consecutive perfect fifths by similar motion.

    parallel_octave     Consecutive perfect octaves by similar motion.

    parallel_unison     Consecutive unisons by similar motion.

    direct_fifth        Similar motion into perfect fifth with soprano leap.

    direct_octave       Similar motion into perfect octave with soprano leap.

    unprepared_dissonance   Dissonance on strong beat without preparation.

    unresolved_dissonance   Prepared dissonance not resolved by step.

    grotesque_leap      Melodic leap exceeding playable range (>19 semitones).

    consecutive_leaps   Two leaps (>4 semitones) in same direction.

    ugly_leap           Augmented or diminished melodic intervals.

    cross_relation      Same letter name chromatically altered between voices.

    tessitura_excursion Note beyond voice's range.

    voice_overlap       Voice moves to pitch just vacated by other voice.

    spacing_error       Adjacent voices more than two octaves apart.

    parallel_rhythm     Too many consecutive simultaneous attacks (lockstep motion).
"""
import logging
from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence

logger: logging.Logger = logging.getLogger(__name__)

from builder.types import Note
from shared.constants import (
    CONSONANT_INTERVALS_ABOVE_BASS,
    CROSS_RELATION_PAIRS,
    DIRECT_MOTION_LEAP_SEMITONES,
    GROTESQUE_LEAP_SEMITONES,
    MAX_PARALLEL_RHYTHM_ATTACKS,
    NOTE_NAMES_SHARP,
    SKIP_SEMITONES,
    STEP_SEMITONES,
    UGLY_INTERVALS,
    VOICE_NAME_TO_RANGE_IDX,
    VOICE_RANGES,
)



@dataclass(frozen=True)
class Fault:
    """Single fault report."""
    category: str
    bar_beat: str
    voices: tuple[int, ...]
    message: str


def _bar_duration(metre: str) -> Fraction:
    """Compute bar duration in whole notes."""
    num, den = map(int, metre.split("/"))
    return Fraction(num, den)


def _beat_duration(metre: str) -> Fraction:
    """Compute beat duration in whole notes."""
    _, den = map(int, metre.split("/"))
    return Fraction(1, den)


def _interval_semitones(pitch_a: int, pitch_b: int) -> int:
    """Signed interval in semitones."""
    return pitch_b - pitch_a


def _is_strong_beat(offset: Fraction, metre: str) -> bool:
    """Check if offset falls on a strong beat (beat 1 only)."""
    bar_dur: Fraction = _bar_duration(metre=metre)
    offset_in_bar: Fraction = offset % bar_dur
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
    bar_dur: Fraction = _bar_duration(metre=metre)
    beat_dur: Fraction = _beat_duration(metre=metre)
    bar: int = int(offset // bar_dur) + 1
    beat_offset: Fraction = offset % bar_dur
    beat: int = int(beat_offset // beat_dur) + 1
    return f"{bar}.{beat}"


def _parse_bar_beat(bar_beat: str) -> tuple[int, int]:
    """Parse bar.beat string to (bar, beat) tuple for numeric sorting."""
    parts: list[str] = bar_beat.split(".")
    return (int(parts[0]), int(parts[1]))


def _simple_interval(pitch_a: int, pitch_b: int) -> int:
    """Interval in semitones, reduced to single octave."""
    return abs(pitch_a - pitch_b) % 12


def _check_consecutive_leaps(
    voice_notes: Sequence[Note],
    voice_idx: int,
    metre: str,
    structural: frozenset[Fraction] = frozenset(),
) -> list[Fault]:
    """Check for two leaps in same direction."""
    faults: list[Fault] = []
    pitches: list[tuple[Fraction, int]] = [(n.offset, n.pitch) for n in voice_notes]
    for i in range(len(pitches) - 2):
        # Exempt when leap targets are structural (schema-mandated pitches)
        if pitches[i + 1][0] in structural and pitches[i + 2][0] in structural:
            continue
        int1: int = pitches[i + 1][1] - pitches[i][1]
        int2: int = pitches[i + 2][1] - pitches[i + 1][1]
        if abs(int1) > SKIP_SEMITONES and abs(int2) > SKIP_SEMITONES:
            if (int1 > 0) == (int2 > 0):
                loc: str = _offset_to_bar_beat(offset=pitches[i + 1][0], metre=metre)
                p1: str = _midi_to_name(midi=pitches[i][1])
                p2: str = _midi_to_name(midi=pitches[i + 1][1])
                p3: str = _midi_to_name(midi=pitches[i + 2][1])
                faults.append(Fault(
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
                if other_v == v_idx:
                    continue
                pair: tuple[int, int] = (min(pc, other_pc), max(pc, other_pc))
                if pair in CROSS_RELATION_PAIRS:
                    loc: str = _offset_to_bar_beat(offset=offsets[i + 1], metre=metre)
                    n1: str = _midi_to_name(midi=other_pitch)
                    n2: str = _midi_to_name(midi=pitch)
                    faults.append(Fault(
                        category="cross_relation",
                        bar_beat=loc,
                        voices=(other_v, v_idx),
                        message=f"Cross-relation: {n1} against {n2}",
                    ))
    return faults


def _check_direct_motion(
    voices: Sequence[Sequence[Note]],
    metre: str,
    voice_structural: Sequence[frozenset[Fraction]] = (),
) -> list[Fault]:
    """Check for direct fifths/octaves with soprano leap."""
    faults: list[Fault] = []
    if len(voices) < 2:
        return faults
    soprano: Sequence[Note] = voices[0]
    s_struct: frozenset[Fraction] = voice_structural[0] if voice_structural else frozenset()
    for other_idx in range(1, len(voices)):
        other: Sequence[Note] = voices[other_idx]
        o_struct: frozenset[Fraction] = voice_structural[other_idx] if voice_structural else frozenset()
        s_by_off: dict[Fraction, int] = {n.offset: n.pitch for n in soprano}
        o_by_off: dict[Fraction, int] = {n.offset: n.pitch for n in other}
        common: list[Fraction] = sorted(set(s_by_off.keys()) & set(o_by_off.keys()))
        for i in range(len(common) - 1):
            off1, off2 = common[i], common[i + 1]
            # Exempt when both voices at target offset are structural
            if off2 in s_struct and off2 in o_struct:
                continue
            s1, s2 = s_by_off[off1], s_by_off[off2]
            o1, o2 = o_by_off[off1], o_by_off[off2]
            motion: str = _motion_type(pitch_a_from=s1, pitch_a_to=s2, pitch_b_from=o1, pitch_b_to=o2)
            if motion != "similar":
                continue
            soprano_leap: int = abs(s2 - s1)
            if soprano_leap <= DIRECT_MOTION_LEAP_SEMITONES:
                continue
            interval: int = _simple_interval(pitch_a=s2, pitch_b=o2)
            if interval == 7:
                loc: str = _offset_to_bar_beat(offset=off2, metre=metre)
                faults.append(Fault(
                    category="direct_fifth",
                    bar_beat=loc,
                    voices=(0, other_idx),
                    message=f"Similar motion to fifth with soprano leap: "
                            f"{_midi_to_name(midi=s1)}-{_midi_to_name(midi=s2)}",
                ))
            if interval == 0:
                loc = _offset_to_bar_beat(offset=off2, metre=metre)
                faults.append(Fault(
                    category="direct_octave",
                    bar_beat=loc,
                    voices=(0, other_idx),
                    message=f"Similar motion to octave with soprano leap: "
                            f"{_midi_to_name(midi=s1)}-{_midi_to_name(midi=s2)}",
                ))
    return faults


def _check_dissonance(
    voices: Sequence[Sequence[Note]],
    metre: str,
    voice_structural: Sequence[frozenset[Fraction]] = (),
) -> list[Fault]:
    """Check for unprepared/unresolved dissonances on strong beats."""
    faults: list[Fault] = []
    if len(voices) < 2:
        return faults
    consonant: frozenset[int] = CONSONANT_INTERVALS_ABOVE_BASS
    soprano: Sequence[Note] = voices[0]
    bass: Sequence[Note] = voices[-1]
    s_struct: frozenset[Fraction] = voice_structural[0] if voice_structural else frozenset()
    b_struct: frozenset[Fraction] = voice_structural[-1] if voice_structural else frozenset()
    s_by_off: dict[Fraction, int] = {n.offset: n.pitch for n in soprano}
    b_by_off: dict[Fraction, int] = {n.offset: n.pitch for n in bass}
    common: list[Fraction] = sorted(set(s_by_off.keys()) & set(b_by_off.keys()))
    for i, off in enumerate(common):
        if not _is_strong_beat(offset=off, metre=metre):
            continue
        # Exempt when both voices are structural — planned dissonance
        if off in s_struct and off in b_struct:
            continue
        s_pitch: int = s_by_off[off]
        b_pitch: int = b_by_off[off]
        interval: int = _simple_interval(pitch_a=s_pitch, pitch_b=b_pitch)
        if interval in consonant:
            continue
        loc: str = _offset_to_bar_beat(offset=off, metre=metre)
        prepared: bool = False
        if i > 0:
            prev_off: Fraction = common[i - 1]
            if prev_off in s_by_off and s_by_off[prev_off] == s_pitch:
                prepared = True
        if not prepared:
            faults.append(Fault(
                category="unprepared_dissonance",
                bar_beat=loc,
                voices=(0, len(voices) - 1),
                message=f"Unprepared dissonance on strong beat: "
                        f"{_midi_to_name(midi=s_pitch)}/{_midi_to_name(midi=b_pitch)}",
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
                category="unresolved_dissonance",
                bar_beat=loc,
                voices=(0, len(voices) - 1),
                message=f"Dissonance not resolved by step: "
                        f"{_midi_to_name(midi=s_pitch)}/{_midi_to_name(midi=b_pitch)}",
            ))
    return faults


def _check_grotesque_leap(
    voice_notes: Sequence[Note],
    voice_idx: int,
    metre: str,
) -> list[Fault]:
    """Check for leaps exceeding playable range (>19 semitones)."""
    faults: list[Fault] = []
    for i in range(len(voice_notes) - 1):
        interval: int = abs(voice_notes[i + 1].pitch - voice_notes[i].pitch)
        if interval > GROTESQUE_LEAP_SEMITONES:
            loc: str = _offset_to_bar_beat(offset=voice_notes[i + 1].offset, metre=metre)
            n1: str = _midi_to_name(midi=voice_notes[i].pitch)
            n2: str = _midi_to_name(midi=voice_notes[i + 1].pitch)
            faults.append(Fault(
                category="grotesque_leap",
                bar_beat=loc,
                voices=(voice_idx,),
                message=f"Leap of {interval} semitones: {n1} to {n2}",
            ))
    return faults


def _check_spacing(
    voices: Sequence[Sequence[Note]],
    metre: str,
) -> list[Fault]:
    """Check for spacing errors between adjacent voices. Skip for 2-voice texture."""
    faults: list[Fault] = []
    if len(voices) <= 2:
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
                    category="spacing_error",
                    bar_beat=_offset_to_bar_beat(offset=off, metre=metre),
                    voices=(v_idx, v_idx + 1),
                    message=f"Voices more than two octaves apart: "
                            f"{_midi_to_name(midi=u_by_off[off])}/{_midi_to_name(midi=l_by_off[off])}",
                ))
    return faults


def _check_tessitura(
    voice_notes: Sequence[Note],
    voice_idx: int,
    metre: str,
    voice_count: int,
    actuator_ranges: dict[int, tuple[int, int]] | None = None,
) -> list[Fault]:
    """Check for notes outside voice range (one fault per bar).
    
    If actuator_ranges is provided, uses those ranges per voice index.
    Otherwise falls back to VOICE_RANGES from shared/constants.py.
    """
    faults: list[Fault] = []
    if actuator_ranges is not None:
        if voice_idx not in actuator_ranges:
            return faults
        low, high = actuator_ranges[voice_idx]
    elif voice_count == 2:
        ranges: dict[int, tuple[int, int]] = {
            0: VOICE_RANGES[0],  # Soprano
            1: VOICE_RANGES[3],  # Bass
        }
        if voice_idx not in ranges:
            return faults
        low, high = ranges[voice_idx]
    else:
        if voice_idx not in VOICE_RANGES:
            return faults
        low, high = VOICE_RANGES[voice_idx]
    bar_dur: Fraction = _bar_duration(metre=metre)
    bar_worst: dict[int, tuple[int, int, Fraction, str]] = {}
    for note in voice_notes:
        if note.pitch < low:
            beyond: int = low - note.pitch
            direction: str = "below"
        elif note.pitch > high:
            beyond = note.pitch - high
            direction = "above"
        else:
            continue
        bar: int = int(note.offset // bar_dur) + 1
        if bar not in bar_worst or beyond > bar_worst[bar][0]:
            bar_worst[bar] = (beyond, note.pitch, note.offset, direction)
    for bar in sorted(bar_worst.keys()):
        beyond, pitch, offset, direction = bar_worst[bar]
        faults.append(Fault(
            category="tessitura_excursion",
            bar_beat=_offset_to_bar_beat(offset=offset, metre=metre),
            voices=(voice_idx,),
            message=f"{_midi_to_name(midi=pitch)} is {beyond} semitones {direction} "
                    f"voice range ({_midi_to_name(midi=low)}-{_midi_to_name(midi=high)})",
        ))
    return faults


def _check_ugly_leaps(
    voice_notes: Sequence[Note],
    voice_idx: int,
    metre: str,
    structural: frozenset[Fraction] = frozenset(),
) -> list[Fault]:
    """Check for augmented or diminished intervals."""
    faults: list[Fault] = []
    ugly: frozenset[int] = UGLY_INTERVALS
    for i in range(len(voice_notes) - 1):
        # Exempt structural-to-structural leaps (schema-mandated)
        if voice_notes[i].offset in structural and voice_notes[i + 1].offset in structural:
            continue
        interval: int = abs(voice_notes[i + 1].pitch - voice_notes[i].pitch)
        simple: int = interval % 12
        if simple in ugly and interval > STEP_SEMITONES:
            loc: str = _offset_to_bar_beat(offset=voice_notes[i + 1].offset, metre=metre)
            n1: str = _midi_to_name(midi=voice_notes[i].pitch)
            n2: str = _midi_to_name(midi=voice_notes[i + 1].pitch)
            if simple == 6:
                name: str = "tritone"
            elif simple == 1:
                name = "minor ninth" if interval > 12 else "minor second"
            elif simple == 10:
                name = "minor seventh"
            else:
                name = "major seventh"
            faults.append(Fault(
                category="ugly_leap",
                bar_beat=loc,
                voices=(voice_idx,),
                message=f"Ugly leap ({name}): {n1} to {n2}",
            ))
    return faults


def _check_voice_overlap(
    voices: Sequence[Sequence[Note]],
    metre: str,
    voice_structural: Sequence[frozenset[Fraction]] = (),
) -> list[Fault]:
    """Check for voice moving to pitch just vacated by other voice."""
    faults: list[Fault] = []
    if len(voices) < 2:
        return faults
    for v_a in range(len(voices)):
        a_struct: frozenset[Fraction] = voice_structural[v_a] if voice_structural else frozenset()
        for v_b in range(len(voices)):
            if v_a == v_b:
                continue
            b_struct: frozenset[Fraction] = voice_structural[v_b] if voice_structural else frozenset()
            a_notes: list[Note] = sorted(voices[v_a], key=lambda n: n.offset)
            b_notes: list[Note] = sorted(voices[v_b], key=lambda n: n.offset)
            b_by_off: dict[Fraction, int] = {n.offset: n.pitch for n in b_notes}
            b_end_off: dict[Fraction, Fraction] = {n.offset: n.offset + n.duration for n in b_notes}
            for i in range(len(a_notes) - 1):
                curr_a: Note = a_notes[i]
                next_a: Note = a_notes[i + 1]
                # Exempt when either voice at relevant offset is structural
                # — overlap is unavoidable if schema mandates the pitch
                if next_a.offset in a_struct or curr_a.offset in b_struct:
                    continue
                if curr_a.offset in b_by_off:
                    b_pitch: int = b_by_off[curr_a.offset]
                    # Only flag if the other voice has actually released (vacated)
                    b_note_end: Fraction = b_end_off[curr_a.offset]
                    if b_note_end > next_a.offset:
                        continue  # note still sounding — unison, not vacated overlap
                    if next_a.pitch == b_pitch:
                        # If other voice re-attacks same pitch at next offset,
                        # pitch was not truly vacated — it is a unison
                        if next_a.offset in b_by_off and b_by_off[next_a.offset] == b_pitch:
                            continue
                        faults.append(Fault(
                            category="voice_overlap",
                            bar_beat=_offset_to_bar_beat(offset=next_a.offset, metre=metre),
                            voices=(v_a, v_b),
                            message=f"Voice {v_a} moves to {_midi_to_name(midi=next_a.pitch)} "
                                    f"just vacated by voice {v_b}",
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
                motion: str = _motion_type(pitch_a_from=a1, pitch_a_to=a2, pitch_b_from=b1, pitch_b_to=b2)
                if motion != "similar":
                    continue
                int1: int = _simple_interval(pitch_a=a1, pitch_b=b1)
                int2: int = _simple_interval(pitch_a=a2, pitch_b=b2)
                if int1 == int2 and int1 in {0, 7}:
                    loc: str = _offset_to_bar_beat(offset=off2, metre=metre)
                    if int1 == 0:
                        cat: str = "parallel_unison" if abs(a2 - b2) < 12 else "parallel_octave"
                    else:
                        cat = "parallel_fifth"
                    msg: str = (f"Parallel {cat.split('_')[1]}s: "
                                f"{_midi_to_name(midi=a1)}/{_midi_to_name(midi=b1)} to "
                                f"{_midi_to_name(midi=a2)}/{_midi_to_name(midi=b2)}")
                    faults.append(Fault(
                        category=cat,
                        bar_beat=loc,
                        voices=(v_a, v_b),
                        message=msg,
                    ))
    return faults


def _check_parallel_rhythm(
    voices: Sequence[Sequence[Note]],
    metre: str,
    phrase_offsets: Sequence[Fraction] = (),
) -> list[Fault]:
    """Check for too many consecutive simultaneous attacks (lockstep rhythm)."""
    faults: list[Fault] = []
    if len(voices) < 2:
        return faults
    phrase_breaks: frozenset[Fraction] = frozenset(phrase_offsets)
    offsets_per_voice: list[set[Fraction]] = [
        {n.offset for n in voice} for voice in voices
    ]
    all_offsets: list[Fraction] = sorted(
        set.union(*offsets_per_voice) if offsets_per_voice else set()
    )
    for v_a in range(len(voices)):
        for v_b in range(v_a + 1, len(voices)):
            run_start: Fraction | None = None
            run_length: int = 0
            for off in all_offsets:
                # Reset run at phrase boundaries — cadential lockstep
                # is idiomatic and must not bleed into adjacent phrases
                if off in phrase_breaks and run_length > 0:
                    if run_length > MAX_PARALLEL_RHYTHM_ATTACKS:
                        faults.append(Fault(
                            category="parallel_rhythm",
                            bar_beat=_offset_to_bar_beat(offset=run_start, metre=metre),
                            voices=(v_a, v_b),
                            message=f"{run_length} consecutive simultaneous attacks "
                                    f"(voices move in lockstep)",
                        ))
                    run_start = None
                    run_length = 0
                both_attack: bool = off in offsets_per_voice[v_a] and off in offsets_per_voice[v_b]
                if both_attack:
                    if run_start is None:
                        run_start = off
                        run_length = 1
                    else:
                        run_length += 1
                else:
                    if run_length > MAX_PARALLEL_RHYTHM_ATTACKS:
                        faults.append(Fault(
                            category="parallel_rhythm",
                            bar_beat=_offset_to_bar_beat(offset=run_start, metre=metre),
                            voices=(v_a, v_b),
                            message=f"{run_length} consecutive simultaneous attacks "
                                    f"(voices move in lockstep)",
                        ))
                    run_start = None
                    run_length = 0
            if run_length > MAX_PARALLEL_RHYTHM_ATTACKS:
                faults.append(Fault(
                    category="parallel_rhythm",
                    bar_beat=_offset_to_bar_beat(offset=run_start, metre=metre),
                    voices=(v_a, v_b),
                    message=f"{run_length} consecutive simultaneous attacks "
                            f"(voices move in lockstep)",
                ))
    return faults


def find_faults(
    voices: Sequence[Sequence[Note]],
    metre: str,
    actuator_ranges: dict[int, tuple[int, int]] | None = None,
    phrase_offsets: Sequence[Fraction] = (),
    voice_structural: Sequence[frozenset[Fraction]] = (),
) -> list[Fault]:
    """Find all faults in a multi-voice composition.
    
    Args:
        voices: Sequence of note sequences, one per voice (index 0 = upper).
        metre: Time signature string (e.g. "4/4").
        actuator_ranges: Optional dict mapping voice index to (low, high) MIDI range.
            If not provided, uses default VOICE_RANGES.
        phrase_offsets: Phrase start offsets for resetting parallel rhythm runs.
        voice_structural: Per-voice frozensets of structural (schema-mandated) offsets.
    """
    assert 1 <= len(voices) <= 4, f"Expected 1-4 voices, got {len(voices)}"
    assert "/" in metre, f"Invalid metre format: {metre}"
    voice_count: int = len(voices)
    faults: list[Fault] = []
    for v_idx, voice in enumerate(voices):
        v_struct: frozenset[Fraction] = voice_structural[v_idx] if v_idx < len(voice_structural) else frozenset()
        faults.extend(_check_consecutive_leaps(voice_notes=voice, voice_idx=v_idx, metre=metre, structural=v_struct))
        faults.extend(_check_grotesque_leap(voice_notes=voice, voice_idx=v_idx, metre=metre))
        faults.extend(_check_tessitura(voice_notes=voice, voice_idx=v_idx, metre=metre, voice_count=voice_count, actuator_ranges=actuator_ranges))
        if v_idx == 0:
            faults.extend(_check_ugly_leaps(voice_notes=voice, voice_idx=v_idx, metre=metre, structural=v_struct))
    faults.extend(_check_cross_relation(voices=voices, metre=metre))
    faults.extend(_check_direct_motion(voices=voices, metre=metre, voice_structural=voice_structural))
    faults.extend(_check_dissonance(voices=voices, metre=metre, voice_structural=voice_structural))
    faults.extend(_check_parallel_perfect(voices=voices, metre=metre))
    faults.extend(_check_parallel_rhythm(voices=voices, metre=metre, phrase_offsets=phrase_offsets))
    faults.extend(_check_spacing(voices=voices, metre=metre))
    faults.extend(_check_voice_overlap(voices=voices, metre=metre, voice_structural=voice_structural))
    faults.sort(key=lambda f: (_parse_bar_beat(bar_beat=f.bar_beat), f.category))
    return faults


def find_faults_from_composition(
    composition: "Composition",
    actuator_ranges: dict[str, tuple[int, int]] | None = None,
) -> list[Fault]:
    """Find faults from a Composition object.
    
    Args:
        composition: Composition with voices dict and metre.
        actuator_ranges: Optional dict mapping voice_id to (low, high) MIDI range.
    
    Returns:
        List of Fault objects sorted by bar_beat.
    """
    from builder.types import Composition
    voice_data: list[tuple[int, str, Sequence[Note]]] = []
    for name, notes in composition.voices.items():
        track: int = notes[0].voice if notes else 0
        voice_data.append((track, name, notes))
    voice_data.sort(key=lambda x: x[0])
    voices: list[Sequence[Note]] = [notes for _, _, notes in voice_data]
    ranges: dict[int, tuple[int, int]] = {}
    for i, (track, name, _) in enumerate(voice_data):
        if actuator_ranges is not None and name in actuator_ranges:
            ranges[i] = actuator_ranges[name]
        elif name in VOICE_NAME_TO_RANGE_IDX:
            range_idx: int = VOICE_NAME_TO_RANGE_IDX[name]
            ranges[i] = VOICE_RANGES[range_idx]
    # Build per-voice structural offsets in same order as voices list
    v_structural: list[frozenset[Fraction]] = []
    for _, name, _ in voice_data:
        v_structural.append(
            composition.structural_offsets.get(name, frozenset())
        )
    return find_faults(
        voices=voices,
        metre=composition.metre,
        actuator_ranges=ranges if ranges else None,
        phrase_offsets=composition.phrase_offsets,
        voice_structural=tuple(v_structural),
    )


def print_faults(faults: list[Fault]) -> None:
    """Log faults in readable format."""
    if not faults:
        logger.info("No faults found.")
        return
    logger.info("Found %d faults", len(faults))
    for fault in faults:
        voices_str: str = ",".join(str(v) for v in fault.voices)
        logger.info("[%s] v%s %s: %s", fault.bar_beat, voices_str, fault.category, fault.message)
