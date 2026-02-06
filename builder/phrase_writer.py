"""Phrase generation for soprano and bass.

Given a PhrasePlan, produces Notes for both voices. The soprano is generated
first, then the bass is fitted with inline counterpoint checking.
"""
from fractions import Fraction

from builder.cadence_writer import write_cadence
from builder.phrase_types import PhrasePlan, PhraseContext, PhraseResult
from builder.rhythm_cells import select_cell
from builder.types import Note
from shared.constants import (
    PERFECT_INTERVALS,
    STRONG_BEAT_DISSONANT,
    TRACK_SOPRANO,
    VALID_DURATIONS,
)
from shared.key import Key

VALID_DURATIONS_SET: frozenset[Fraction] = frozenset(VALID_DURATIONS)
MAX_MELODIC_INTERVAL: int = 12
LEAP_THRESHOLD: int = 4
STEP_THRESHOLD: int = 2
BASS_VOICE: int = 1
_BASS_TEXTURE: dict[str, str] = {
    "minuet": "pillar",
    "gavotte": "walking",
    "invention": "walking",
    "sarabande": "pillar",
    "bourree": "walking",
}


def _check_d007(
    notes: list[Note],
    metre: str,
    start_offset: Fraction,
) -> None:
    """Assert no repeated MIDI pitch across bar boundaries."""
    bar_length, _ = _parse_metre(metre=metre)
    for i in range(len(notes) - 1):
        note_a: Note = notes[i]
        note_b: Note = notes[i + 1]
        bar_a: int = int((note_a.offset - start_offset) // bar_length)
        bar_b: int = int((note_b.offset - start_offset) // bar_length)
        if bar_a != bar_b:
            assert note_a.pitch != note_b.pitch, (
                f"D007: repeated pitch {note_a.pitch} across bar boundary "
                f"at offset {note_b.offset}"
            )


def _check_leap_step(notes: list[Note]) -> None:
    """Assert leap-then-step rule (except final note)."""
    for i in range(len(notes) - 2):
        interval: int = abs(notes[i + 1].pitch - notes[i].pitch)
        if interval > LEAP_THRESHOLD:
            recovery: int = abs(notes[i + 2].pitch - notes[i + 1].pitch)
            assert recovery <= STEP_THRESHOLD, (
                f"Leap of {interval} at offset {notes[i].offset} not followed "
                f"by step (got {recovery})"
            )
            leap_dir: int = notes[i + 1].pitch - notes[i].pitch
            step_dir: int = notes[i + 2].pitch - notes[i + 1].pitch
            assert (leap_dir > 0) != (step_dir > 0) or step_dir == 0, (
                f"Leap at offset {notes[i].offset} not followed by contrary step"
            )


def _check_max_interval(notes: list[Note]) -> None:
    """Assert no melodic interval exceeds an octave."""
    for i in range(len(notes) - 1):
        interval: int = abs(notes[i + 1].pitch - notes[i].pitch)
        assert interval <= MAX_MELODIC_INTERVAL, (
            f"Melodic interval {interval} exceeds octave at offset {notes[i].offset}"
        )


def _degree_to_nearest_midi(
    degree: int,
    key: Key,
    target_midi: int,
    midi_range: tuple[int, int],
) -> int:
    """Place degree in nearest octave to target, within range."""
    candidates: list[int] = [
        key.degree_to_midi(degree=degree, octave=octave) for octave in range(2, 7)
    ]
    valid: list[int] = [
        m for m in candidates if midi_range[0] <= m <= midi_range[1]
    ]
    assert len(valid) > 0, (
        f"No valid octave for degree {degree} in range {midi_range}"
    )
    return min(valid, key=lambda m: abs(m - target_midi))


def _parse_metre(metre: str) -> tuple[Fraction, Fraction]:
    """Parse '3/4' to (bar_length, beat_unit)."""
    num, denom = metre.split("/")
    beats_per_bar: int = int(num)
    beat_value: int = int(denom)
    beat_unit: Fraction = Fraction(1, beat_value)
    bar_length: Fraction = beat_unit * beats_per_bar
    return bar_length, beat_unit


def _soprano_pitch_at_offset(
    soprano_notes: tuple[Note, ...],
    offset: Fraction,
) -> int | None:
    """Return soprano MIDI pitch sounding at given offset, or None."""
    for note in soprano_notes:
        if note.offset <= offset < note.offset + note.duration:
            return note.pitch
    return None


def _is_strong_beat(
    offset: Fraction,
    bar_length: Fraction,
    start_offset: Fraction,
) -> bool:
    """True if offset falls on beat 1 of any bar."""
    relative: Fraction = offset - start_offset
    return (relative % bar_length) == Fraction(0)


def _check_parallel_perfects(
    bass_pitch: int,
    soprano_pitch: int,
    prev_bass_pitch: int | None,
    prev_soprano_pitch: int | None,
) -> bool:
    """Return True if parallel perfect interval detected."""
    if prev_bass_pitch is None or prev_soprano_pitch is None:
        return False
    prev_ic: int = abs(prev_soprano_pitch - prev_bass_pitch) % 12
    curr_ic: int = abs(soprano_pitch - bass_pitch) % 12
    if prev_ic in PERFECT_INTERVALS and curr_ic == prev_ic:
        if prev_ic == curr_ic and prev_ic in {0, 7}:
            return True
    return False


def _find_consonant_alternative(
    target_degree: int,
    key: Key,
    soprano_pitch: int,
    bass_range: tuple[int, int],
    prev_bass_midi: int,
) -> int:
    """Find nearest consonant bass pitch for a given degree."""
    candidates: list[int] = [
        key.degree_to_midi(degree=target_degree, octave=octave) for octave in range(2, 7)
    ]
    valid: list[int] = [
        m for m in candidates if bass_range[0] <= m <= bass_range[1]
    ]
    if not valid:
        return min(candidates, key=lambda m: abs(m - prev_bass_midi))
    consonant: list[int] = [
        m for m in valid
        if abs(soprano_pitch - m) % 12 not in STRONG_BEAT_DISSONANT
    ]
    pool: list[int] = consonant if consonant else valid
    return min(pool, key=lambda m: abs(m - prev_bass_midi))


def _validate_soprano_notes(
    notes: list[Note],
    plan: PhrasePlan,
) -> None:
    """Validate all postconditions on soprano notes."""
    assert len(notes) >= 1, "No soprano notes generated"
    for note in notes:
        assert plan.upper_range.low <= note.pitch <= plan.upper_range.high, (
            f"Soprano pitch {note.pitch} outside range "
            f"[{plan.upper_range.low}, {plan.upper_range.high}]"
        )
        assert note.duration in VALID_DURATIONS_SET, (
            f"Duration {note.duration} not in VALID_DURATIONS"
        )
    sorted_notes: list[Note] = sorted(notes, key=lambda n: n.offset)
    assert notes == sorted_notes, "Soprano notes not sorted by offset"
    for i in range(len(notes) - 1):
        expected_next: Fraction = notes[i].offset + notes[i].duration
        assert expected_next == notes[i + 1].offset, (
            f"Gap or overlap in soprano at offset {notes[i].offset}"
        )
    total_dur: Fraction = sum((n.duration for n in notes), Fraction(0))
    assert total_dur == plan.phrase_duration, (
        f"Soprano durations sum to {total_dur}, expected {plan.phrase_duration}"
    )
    assert notes[0].offset == plan.start_offset, (
        f"Soprano first note at {notes[0].offset}, expected {plan.start_offset}"
    )
    _check_max_interval(notes=notes)
    _check_d007(notes=notes, metre=plan.metre, start_offset=plan.start_offset)
    _check_leap_step(notes=notes)


def _validate_bass_notes(
    notes: list[Note],
    plan: PhrasePlan,
    soprano_notes: tuple[Note, ...],
) -> None:
    """Validate all postconditions on bass notes."""
    assert len(notes) >= 1, "No bass notes generated"
    for note in notes:
        assert plan.lower_range.low <= note.pitch <= plan.lower_range.high, (
            f"Bass pitch {note.pitch} outside range "
            f"[{plan.lower_range.low}, {plan.lower_range.high}]"
        )
        assert note.duration in VALID_DURATIONS_SET, (
            f"Duration {note.duration} not in VALID_DURATIONS"
        )
    sorted_notes: list[Note] = sorted(notes, key=lambda n: n.offset)
    assert notes == sorted_notes, "Bass notes not sorted by offset"
    for i in range(len(notes) - 1):
        expected_next: Fraction = notes[i].offset + notes[i].duration
        assert expected_next == notes[i + 1].offset, (
            f"Gap or overlap in bass at offset {notes[i].offset}"
        )
    total_dur: Fraction = sum((n.duration for n in notes), Fraction(0))
    assert total_dur == plan.phrase_duration, (
        f"Bass durations sum to {total_dur}, expected {plan.phrase_duration}"
    )
    assert notes[0].offset == plan.start_offset, (
        f"Bass first note at {notes[0].offset}, expected {plan.start_offset}"
    )
    bar_length, _ = _parse_metre(metre=plan.metre)
    for note in notes:
        soprano_pitch: int | None = _soprano_pitch_at_offset(soprano_notes=soprano_notes, offset=note.offset)
        if soprano_pitch is not None:
            assert note.pitch <= soprano_pitch, (
                f"Voice overlap: bass {note.pitch} > soprano {soprano_pitch} "
                f"at offset {note.offset}"
            )


def generate_soprano_phrase(plan: PhrasePlan) -> tuple[Note, ...]:
    """Generate soprano notes for one phrase."""
    if plan.is_cadential:
        soprano_notes, _ = write_cadence(
            schema_name=plan.schema_name,
            metre=plan.metre,
            local_key=plan.local_key,
            start_offset=plan.start_offset,
            prev_upper_midi=plan.prev_exit_upper,
            prev_lower_midi=plan.prev_exit_lower,
            upper_range=(plan.upper_range.low, plan.upper_range.high),
            lower_range=(plan.lower_range.low, plan.lower_range.high),
            upper_median=plan.upper_median,
            lower_median=plan.lower_median,
        )
        return soprano_notes
    bar_length, beat_unit = _parse_metre(metre=plan.metre)
    structural_tones: list[tuple[Fraction, int]] = []
    prev_midi: int = (
        plan.prev_exit_upper if plan.prev_exit_upper is not None
        else plan.upper_median
    )
    for i, degree in enumerate(plan.degrees_upper):
        pos = plan.degree_positions[i]
        offset: Fraction = (
            plan.start_offset
            + (pos.bar - 1) * bar_length
            + (pos.beat - 1) * beat_unit
        )
        midi: int = _degree_to_nearest_midi(
            degree=degree,
            key=plan.local_key,
            target_midi=prev_midi,
            midi_range=(plan.upper_range.low, plan.upper_range.high),
        )
        structural_tones.append((offset, midi))
        prev_midi = midi
    structural_map: dict[Fraction, int] = dict(structural_tones)
    notes: list[Note] = []
    current_offset: Fraction = plan.start_offset
    current_midi: int = (
        plan.prev_exit_upper if plan.prev_exit_upper is not None
        else structural_tones[0][1] if structural_tones else plan.upper_median
    )
    prev_cell_name: str | None = None
    struct_idx: int = 0
    for bar_num in range(1, plan.bar_span + 1):
        bar_start: Fraction = plan.start_offset + (bar_num - 1) * bar_length
        is_final_bar: bool = bar_num == plan.bar_span
        prefer: str = "cadential" if is_final_bar else "plain"
        cell = select_cell(
            genre=plan.rhythm_profile,
            metre=plan.metre,
            bar_index=bar_num - 1,
            prefer_character=prefer,
            avoid_name=prev_cell_name,
        )
        prev_cell_name = cell.name
        note_offset: Fraction = bar_start
        for dur in cell.durations:
            if note_offset in structural_map:
                pitch: int = structural_map[note_offset]
                while struct_idx < len(structural_tones) - 1:
                    if structural_tones[struct_idx][0] <= note_offset:
                        struct_idx += 1
                    else:
                        break
            else:
                next_struct_offset: Fraction
                next_struct_midi: int
                if struct_idx < len(structural_tones):
                    next_struct_offset, next_struct_midi = structural_tones[struct_idx]
                else:
                    next_struct_offset = plan.start_offset + plan.phrase_duration
                    next_struct_midi = current_midi
                if next_struct_midi > current_midi:
                    pitch = plan.local_key.diatonic_step(midi=current_midi, steps=+1)
                elif next_struct_midi < current_midi:
                    pitch = plan.local_key.diatonic_step(midi=current_midi, steps=-1)
                else:
                    direction: int = +1 if (bar_num % 2 == 0) else -1
                    pitch = plan.local_key.diatonic_step(midi=current_midi, steps=direction)
            pitch = max(plan.upper_range.low, min(pitch, plan.upper_range.high))
            if notes:
                last_bar: int = int((notes[-1].offset - plan.start_offset) // bar_length)
                this_bar: int = int((note_offset - plan.start_offset) // bar_length)
                if last_bar != this_bar and pitch == notes[-1].pitch:
                    if pitch < plan.upper_range.high:
                        pitch = plan.local_key.diatonic_step(midi=pitch, steps=+1)
                    else:
                        pitch = plan.local_key.diatonic_step(midi=pitch, steps=-1)
                    pitch = max(plan.upper_range.low, min(pitch, plan.upper_range.high))
            notes.append(Note(
                offset=note_offset,
                pitch=pitch,
                duration=dur,
                voice=TRACK_SOPRANO,
            ))
            current_midi = pitch
            note_offset += dur
        current_offset = note_offset
    _validate_soprano_notes(notes=notes, plan=plan)
    return tuple(notes)


def generate_bass_phrase(
    plan: PhrasePlan,
    soprano_notes: tuple[Note, ...],
) -> tuple[Note, ...]:
    """Generate bass notes for one phrase, checked against soprano."""
    if plan.is_cadential:
        _, bass_notes = write_cadence(
            schema_name=plan.schema_name,
            metre=plan.metre,
            local_key=plan.local_key,
            start_offset=plan.start_offset,
            prev_upper_midi=plan.prev_exit_upper,
            prev_lower_midi=plan.prev_exit_lower,
            upper_range=(plan.upper_range.low, plan.upper_range.high),
            lower_range=(plan.lower_range.low, plan.lower_range.high),
            upper_median=plan.upper_median,
            lower_median=plan.lower_median,
        )
        return bass_notes
    bar_length, beat_unit = _parse_metre(metre=plan.metre)
    structural_tones: list[tuple[Fraction, int]] = []
    prev_midi: int = (
        plan.prev_exit_lower if plan.prev_exit_lower is not None
        else plan.lower_median
    )
    for i, degree in enumerate(plan.degrees_lower):
        pos = plan.degree_positions[i]
        offset: Fraction = (
            plan.start_offset
            + (pos.bar - 1) * bar_length
            + (pos.beat - 1) * beat_unit
        )
        soprano_at_offset: int | None = _soprano_pitch_at_offset(soprano_notes=soprano_notes, offset=offset)
        if soprano_at_offset is not None:
            midi: int = _find_consonant_alternative(
                target_degree=degree,
                key=plan.local_key,
                soprano_pitch=soprano_at_offset,
                bass_range=(plan.lower_range.low, plan.lower_range.high),
                prev_bass_midi=prev_midi,
            )
        else:
            midi = _degree_to_nearest_midi(
                degree=degree,
                key=plan.local_key,
                target_midi=prev_midi,
                midi_range=(plan.lower_range.low, plan.lower_range.high),
            )
        structural_tones.append((offset, midi))
        prev_midi = midi
    structural_map: dict[Fraction, int] = dict(structural_tones)
    texture: str = _BASS_TEXTURE.get(plan.rhythm_profile, "pillar")
    notes: list[Note] = []
    if texture == "pillar":
        for bar_num in range(1, plan.bar_span + 1):
            bar_start: Fraction = plan.start_offset + (bar_num - 1) * bar_length
            if bar_start in structural_map:
                pitch: int = structural_map[bar_start]
            elif notes:
                pitch = notes[-1].pitch
            else:
                pitch = structural_tones[0][1] if structural_tones else plan.lower_median
            pitch = max(plan.lower_range.low, min(pitch, plan.lower_range.high))
            notes.append(Note(
                offset=bar_start,
                pitch=pitch,
                duration=bar_length,
                voice=BASS_VOICE,
            ))
    else:
        current_midi = (
            plan.prev_exit_lower if plan.prev_exit_lower is not None
            else structural_tones[0][1] if structural_tones else plan.lower_median
        )
        struct_idx: int = 0
        prev_strong_bass: int | None = None
        prev_strong_soprano: int | None = None
        for bar_num in range(1, plan.bar_span + 1):
            bar_start: Fraction = plan.start_offset + (bar_num - 1) * bar_length
            is_final_bar: bool = bar_num == plan.bar_span
            prefer: str = "cadential" if is_final_bar else "plain"
            cell = select_cell(
                genre=plan.rhythm_profile,
                metre=plan.metre,
                bar_index=bar_num - 1,
                prefer_character=prefer,
                avoid_name=None,
            )
            note_offset: Fraction = bar_start
            for dur in cell.durations:
                if note_offset in structural_map:
                    pitch = structural_map[note_offset]
                    while struct_idx < len(structural_tones) - 1:
                        if structural_tones[struct_idx][0] <= note_offset:
                            struct_idx += 1
                        else:
                            break
                else:
                    next_struct_midi: int
                    if struct_idx < len(structural_tones):
                        _, next_struct_midi = structural_tones[struct_idx]
                    else:
                        next_struct_midi = current_midi
                    if next_struct_midi > current_midi:
                        pitch = plan.local_key.diatonic_step(midi=current_midi, steps=+1)
                    elif next_struct_midi < current_midi:
                        pitch = plan.local_key.diatonic_step(midi=current_midi, steps=-1)
                    else:
                        pitch = current_midi
                pitch = max(plan.lower_range.low, min(pitch, plan.lower_range.high))
                is_strong: bool = _is_strong_beat(offset=note_offset, bar_length=bar_length, start_offset=plan.start_offset)
                if is_strong:
                    soprano_pitch: int | None = _soprano_pitch_at_offset(soprano_notes=soprano_notes, offset=note_offset)
                    if soprano_pitch is not None:
                        ic: int = abs(soprano_pitch - pitch) % 12
                        if ic in STRONG_BEAT_DISSONANT:
                            pitch = plan.local_key.diatonic_step(midi=pitch, steps=+1)
                            pitch = max(plan.lower_range.low, min(pitch, plan.lower_range.high))
                            ic = abs(soprano_pitch - pitch) % 12
                            if ic in STRONG_BEAT_DISSONANT:
                                pitch = plan.local_key.diatonic_step(midi=pitch, steps=-2)
                                pitch = max(plan.lower_range.low, min(pitch, plan.lower_range.high))
                        if pitch > soprano_pitch:
                            pitch = plan.local_key.diatonic_step(midi=soprano_pitch, steps=-1)
                            pitch = max(plan.lower_range.low, min(pitch, plan.lower_range.high))
                        if _check_parallel_perfects(bass_pitch=pitch, soprano_pitch=soprano_pitch, prev_bass_pitch=prev_strong_bass, prev_soprano_pitch=prev_strong_soprano):
                            pitch = plan.local_key.diatonic_step(midi=pitch, steps=+1)
                            pitch = max(plan.lower_range.low, min(pitch, plan.lower_range.high))
                        prev_strong_bass = pitch
                        prev_strong_soprano = soprano_pitch
                notes.append(Note(
                    offset=note_offset,
                    pitch=pitch,
                    duration=dur,
                    voice=BASS_VOICE,
                ))
                current_midi = pitch
                note_offset += dur
    _validate_bass_notes(notes=notes, plan=plan, soprano_notes=soprano_notes)
    return tuple(notes)


def write_phrase(
    plan: PhrasePlan,
    context: PhraseContext | None = None,
) -> PhraseResult:
    """Write complete phrase (soprano + bass) and return result."""
    # TODO: use context for cross-phrase parallel checking
    if plan.is_cadential:
        soprano_notes, bass_notes = write_cadence(
            schema_name=plan.schema_name,
            metre=plan.metre,
            local_key=plan.local_key,
            start_offset=plan.start_offset,
            prev_upper_midi=plan.prev_exit_upper,
            prev_lower_midi=plan.prev_exit_lower,
            upper_range=(plan.upper_range.low, plan.upper_range.high),
            lower_range=(plan.lower_range.low, plan.lower_range.high),
            upper_median=plan.upper_median,
            lower_median=plan.lower_median,
        )
    else:
        soprano_notes = generate_soprano_phrase(plan=plan)
        bass_notes = generate_bass_phrase(plan=plan, soprano_notes=soprano_notes)
    return PhraseResult(
        upper_notes=soprano_notes,
        lower_notes=bass_notes,
        exit_upper=soprano_notes[-1].pitch,
        exit_lower=bass_notes[-1].pitch,
        schema_name=plan.schema_name,
    )
