"""Phrase generation for soprano and bass.

Given a PhrasePlan, produces Notes for both voices. The soprano is generated
first, then the bass is fitted with inline counterpoint checking.
"""
from fractions import Fraction

from builder.cadence_writer import write_cadence
from builder.phrase_types import PhrasePlan, PhraseResult
from builder.rhythm_cells import select_cell
from builder.types import Note
from shared.constants import (
    PERFECT_INTERVALS,
    PHRASE_VOICE_BASS,
    STRONG_BEAT_DISSONANT,
    TRACK_SOPRANO,
    VALID_DURATIONS,
)
from shared.key import Key

VALID_DURATIONS_SET: frozenset[Fraction] = frozenset(VALID_DURATIONS)
MAX_MELODIC_INTERVAL: int = 12
LEAP_THRESHOLD: int = 4
STEP_THRESHOLD: int = 2
_BASS_TEXTURE: dict[str, str] = {
    "minuet": "pillar",
    "gavotte": "walking",
    "invention": "walking",
    "sarabande": "pillar",
    "bourree": "walking",
}



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


def _check_parallel_perfects(
    bass_pitch: int,
    soprano_pitch: int,
    prev_bass_pitch: int | None,
    prev_soprano_pitch: int | None,
) -> bool:
    """Return True if parallel perfect interval by similar motion detected."""
    if prev_bass_pitch is None or prev_soprano_pitch is None:
        return False
    prev_ic: int = abs(prev_soprano_pitch - prev_bass_pitch) % 12
    curr_ic: int = abs(soprano_pitch - bass_pitch) % 12
    if prev_ic not in PERFECT_INTERVALS or curr_ic != prev_ic:
        return False
    soprano_motion: int = soprano_pitch - prev_soprano_pitch
    bass_motion: int = bass_pitch - prev_bass_pitch
    if soprano_motion == 0 or bass_motion == 0:
        return False
    same_direction: bool = (soprano_motion > 0) == (bass_motion > 0)
    return same_direction


def _select_strong_beat_bass(
    candidate: int,
    soprano_pitch: int,
    key: Key,
    bass_range: tuple[int, int],
    prev_bass: int | None,
    prev_soprano: int | None,
) -> int:
    """Select a valid bass pitch for a strong beat from candidates."""
    # Build candidates: diatonic neighbours within +-4 steps of candidate
    pitches: list[int] = [candidate]
    for step in range(1, 5):
        pitches.append(key.diatonic_step(midi=candidate, steps=-step))
        pitches.append(key.diatonic_step(midi=candidate, steps=+step))
    # Hard constraints: in range, not crossing soprano
    valid: list[int] = [
        p for p in pitches
        if bass_range[0] <= p <= bass_range[1] and p <= soprano_pitch
    ]
    assert len(valid) > 0, (
        f"No valid strong-beat bass near {candidate} below soprano {soprano_pitch} "
        f"in range {bass_range}"
    )
    # Prefer consonant with soprano
    consonant: list[int] = [
        p for p in valid
        if abs(soprano_pitch - p) % 12 not in STRONG_BEAT_DISSONANT
    ]
    pool: list[int] = consonant if consonant else valid
    # Exclude parallel perfects
    if prev_bass is not None and prev_soprano is not None:
        no_parallel: list[int] = [
            p for p in pool
            if not _check_parallel_perfects(
                bass_pitch=p,
                soprano_pitch=soprano_pitch,
                prev_bass_pitch=prev_bass,
                prev_soprano_pitch=prev_soprano,
            )
        ]
        pool = no_parallel if no_parallel else pool
    # Pick nearest to candidate
    return min(pool, key=lambda p: abs(p - candidate))


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
    assert len(valid) > 0, (
        f"No valid octave for degree {target_degree} in range {bass_range}"
    )
    # L004: soprano/bass crossing forbidden — exclude pitches above soprano
    below: list[int] = [m for m in valid if m <= soprano_pitch]
    assert len(below) > 0, (
        f"No bass pitch for degree {target_degree} below soprano {soprano_pitch} "
        f"in range {bass_range}"
    )
    pool_base: list[int] = below
    consonant: list[int] = [
        m for m in pool_base
        if abs(soprano_pitch - m) % 12 not in STRONG_BEAT_DISSONANT
    ]
    pool: list[int] = consonant if consonant else pool_base
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
    # L004: soprano/bass crossing forbidden
    for note in notes:
        soprano_pitch: int | None = _soprano_pitch_at_offset(
            soprano_notes=soprano_notes,
            offset=note.offset,
        )
        if soprano_pitch is not None:
            assert note.pitch <= soprano_pitch, (
                f"Voice overlap: bass {note.pitch} > soprano {soprano_pitch} "
                f"at offset {note.offset}"
            )


def generate_soprano_phrase(
    plan: PhrasePlan,
    prev_exit_midi: int | None = None,
) -> tuple[Note, ...]:
    """Generate soprano notes for one phrase."""
    assert not plan.is_cadential, (
        f"generate_soprano_phrase called with cadential plan '{plan.schema_name}'; "
        f"use write_phrase() which delegates to write_cadence()"
    )
    bar_length, beat_unit = _parse_metre(metre=plan.metre)
    structural_tones: list[tuple[Fraction, int]] = []
    prev_midi: int = (
        prev_exit_midi if prev_exit_midi is not None
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
        prev_exit_midi if prev_exit_midi is not None
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
    prev_exit_midi: int | None = None,
) -> tuple[Note, ...]:
    """Generate bass notes for one phrase, checked against soprano."""
    assert not plan.is_cadential, (
        f"generate_bass_phrase called with cadential plan '{plan.schema_name}'; "
        f"use write_phrase() which delegates to write_cadence()"
    )
    bar_length, beat_unit = _parse_metre(metre=plan.metre)
    structural_tones: list[tuple[Fraction, int]] = []
    prev_midi: int = (
        prev_exit_midi if prev_exit_midi is not None
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
            # L004: soprano/bass crossing forbidden
            sop_here: int | None = _soprano_pitch_at_offset(
                soprano_notes=soprano_notes,
                offset=bar_start,
            )
            assert sop_here is None or pitch <= sop_here, (
                f"Pillar bass {pitch} > soprano {sop_here} at offset {bar_start}"
            )
            notes.append(Note(
                offset=bar_start,
                pitch=pitch,
                duration=bar_length,
                voice=PHRASE_VOICE_BASS,
            ))
    else:
        current_midi = (
            prev_exit_midi if prev_exit_midi is not None
            else structural_tones[0][1] if structural_tones else plan.lower_median
        )
        struct_idx: int = 0
        prev_bass: int | None = None
        prev_soprano: int | None = None
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
            for note_idx, dur in enumerate(cell.durations):
                from_structural: bool = note_offset in structural_map
                if from_structural:
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
                # L004: soprano/bass crossing forbidden — soprano is hard ceiling
                sop_here: int | None = _soprano_pitch_at_offset(
                    soprano_notes=soprano_notes,
                    offset=note_offset,
                )
                if sop_here is not None and pitch > sop_here:
                    # Step down from soprano instead of stepping toward target
                    pitch = plan.local_key.diatonic_step(midi=sop_here, steps=-1)
                    pitch = max(plan.lower_range.low, pitch)
                    assert pitch <= sop_here, (
                        f"Bass {pitch} still above soprano {sop_here} "
                        f"at offset {note_offset} after correction"
                    )
                # Use cell accent_pattern instead of offset-based strong beat check
                is_accented: bool = cell.accent_pattern[note_idx]
                if is_accented and sop_here is not None and not from_structural:
                    pitch = _select_strong_beat_bass(
                        candidate=pitch,
                        soprano_pitch=sop_here,
                        key=plan.local_key,
                        bass_range=(plan.lower_range.low, plan.lower_range.high),
                        prev_bass=prev_bass,
                        prev_soprano=prev_soprano,
                    )
                # Check parallels at every beat, not just strong beats
                if sop_here is not None and _check_parallel_perfects(
                    bass_pitch=pitch,
                    soprano_pitch=sop_here,
                    prev_bass_pitch=prev_bass,
                    prev_soprano_pitch=prev_soprano,
                ):
                    # Try one step in opposite direction to break the parallel
                    alt: int = plan.local_key.diatonic_step(midi=pitch, steps=-1)
                    if alt < plan.lower_range.low:
                        alt = plan.local_key.diatonic_step(midi=pitch, steps=+1)
                    if (
                        plan.lower_range.low <= alt <= plan.lower_range.high
                        and (sop_here is None or alt <= sop_here)
                        and not _check_parallel_perfects(
                            bass_pitch=alt,
                            soprano_pitch=sop_here,
                            prev_bass_pitch=prev_bass,
                            prev_soprano_pitch=prev_soprano,
                        )
                    ):
                        pitch = alt
                if sop_here is not None:
                    prev_bass = pitch
                    prev_soprano = sop_here
                notes.append(Note(
                    offset=note_offset,
                    pitch=pitch,
                    duration=dur,
                    voice=PHRASE_VOICE_BASS,
                ))
                current_midi = pitch
                note_offset += dur
    _validate_bass_notes(notes=notes, plan=plan, soprano_notes=soprano_notes)
    return tuple(notes)


def write_phrase(
    plan: PhrasePlan,
    prev_upper_midi: int | None = None,
    prev_lower_midi: int | None = None,
) -> PhraseResult:
    """Write complete phrase (soprano + bass) and return result."""
    if plan.is_cadential:
        soprano_notes, bass_notes = write_cadence(
            schema_name=plan.schema_name,
            metre=plan.metre,
            local_key=plan.local_key,
            start_offset=plan.start_offset,
            prev_upper_midi=prev_upper_midi,
            prev_lower_midi=prev_lower_midi,
            upper_range=(plan.upper_range.low, plan.upper_range.high),
            lower_range=(plan.lower_range.low, plan.lower_range.high),
            upper_median=plan.upper_median,
            lower_median=plan.lower_median,
        )
    else:
        soprano_notes = generate_soprano_phrase(plan=plan, prev_exit_midi=prev_upper_midi)
        bass_notes = generate_bass_phrase(plan=plan, soprano_notes=soprano_notes, prev_exit_midi=prev_lower_midi)
    return PhraseResult(
        upper_notes=soprano_notes,
        lower_notes=bass_notes,
        exit_upper=soprano_notes[-1].pitch,
        exit_lower=bass_notes[-1].pitch,
        schema_name=plan.schema_name,
    )
