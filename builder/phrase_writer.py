"""Phrase generation for soprano and bass.

Given a PhrasePlan, produces Notes for both voices. The soprano is generated
first, then the bass is fitted with inline counterpoint checking.
"""
from fractions import Fraction

from builder.cadence_writer import write_cadence
from builder.figuration.bass import get_bass_pattern, realise_bass_pattern
from builder.figuration.soprano import figurate_soprano_span
from builder.phrase_types import PhrasePlan, PhraseResult
from builder.rhythm_cells import select_cell
from builder.types import Note
from shared.constants import (
    LEAP_THRESHOLD,
    MAX_MELODIC_INTERVAL,
    PERFECT_INTERVALS,
    TRACK_BASS,
    SKIP_SEMITONES,
    STEP_SEMITONES,
    STRONG_BEAT_DISSONANT,
    TRACK_SOPRANO,
    UGLY_INTERVALS,
    VALID_DURATIONS_SET,
)
from shared.key import Key
from shared.music_math import parse_metre
from shared.pitch import degree_to_nearest_midi




def _deflect_neighbour(
    pitch: int,
    key: Key,
    midi_range: tuple[int, int],
    target_pitch: int,
) -> int:
    """Return a diatonic neighbour of pitch, preferring direction toward target."""
    if target_pitch >= pitch:
        first_dir, second_dir = +1, -1
    else:
        first_dir, second_dir = -1, +1
    candidate: int = key.diatonic_step(midi=pitch, steps=first_dir)
    if midi_range[0] <= candidate <= midi_range[1]:
        return candidate
    candidate = key.diatonic_step(midi=pitch, steps=second_dir)
    if midi_range[0] <= candidate <= midi_range[1]:
        return candidate
    return pitch


def _check_leap_step(
    notes: list[Note],
    structural_offsets: frozenset[Fraction] | None = None,
) -> None:
    """Assert leap-then-step rule (except final note and structural-to-structural)."""
    for i in range(len(notes) - 2):
        interval: int = abs(notes[i + 1].pitch - notes[i].pitch)
        if interval > LEAP_THRESHOLD:
            if structural_offsets is not None:
                recovery_forced: bool = (
                    notes[i + 1].offset in structural_offsets
                    and notes[i + 2].offset in structural_offsets
                )
                if recovery_forced:
                    continue
            recovery: int = abs(notes[i + 2].pitch - notes[i + 1].pitch)
            assert recovery <= STEP_SEMITONES, (
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
    prev_prev_bass_midi: int | None = None,
) -> int:
    """Find nearest bass pitch for a given degree, preferring consonance."""
    candidates: list[int] = [
        key.degree_to_midi(degree=target_degree, octave=octave) for octave in range(2, 7)
    ]
    valid: list[int] = [
        m for m in candidates if bass_range[0] <= m <= bass_range[1]
    ]
    assert len(valid) > 0, (
        f"No valid octave for degree {target_degree} in range {bass_range}"
    )
    # L004: soprano/bass crossing forbidden
    below: list[int] = [m for m in valid if m <= soprano_pitch]
    assert len(below) > 0, (
        f"No bass pitch for degree {target_degree} below soprano {soprano_pitch} "
        f"in range {bass_range}"
    )
    consonant: list[int] = [
        m for m in below
        if abs(soprano_pitch - m) % 12 not in STRONG_BEAT_DISSONANT
    ]
    pool: list[int] = consonant if consonant else below
    # Prefer candidates that don't form ugly melodic intervals
    non_ugly: list[int] = [
        m for m in pool
        if abs(m - prev_bass_midi) % 12 not in UGLY_INTERVALS
    ]
    if non_ugly:
        pool = non_ugly
    # Prefer candidates that don't create consecutive same-direction leaps
    if prev_prev_bass_midi is not None:
        prev_interval: int = prev_bass_midi - prev_prev_bass_midi
        if abs(prev_interval) > SKIP_SEMITONES:
            no_consec: list[int] = [
                m for m in pool
                if abs(m - prev_bass_midi) <= SKIP_SEMITONES
                or (m - prev_bass_midi > 0) != (prev_interval > 0)
            ]
            if no_consec:
                pool = no_consec
    return min(pool, key=lambda m: abs(m - prev_bass_midi))


def _validate_soprano_notes(
    notes: list[Note],
    plan: PhrasePlan,
    structural_offsets: frozenset[Fraction] | None = None,
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
    _check_leap_step(notes=notes, structural_offsets=structural_offsets)


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
    next_phrase_entry_degree: int | None = None,
    next_phrase_entry_key: Key | None = None,
) -> tuple[tuple[Note, ...], tuple[str, ...]]:
    """Generate soprano notes for one phrase.

    Returns (notes, figure_names) where figure_names lists the figuration
    patterns used for each span between structural tones.
    """
    assert not plan.is_cadential, (
        f"generate_soprano_phrase called with cadential plan '{plan.schema_name}'; "
        f"use write_phrase() which delegates to write_cadence()"
    )
    bar_length, beat_unit = parse_metre(metre=plan.metre)
    structural_tones: list[tuple[Fraction, int]] = []
    structural_keys: list[tuple[Fraction, Key]] = []
    prev_midi: int = (
        prev_exit_midi if prev_exit_midi is not None
        else plan.upper_median
    )
    actual_prev: int | None = prev_exit_midi
    prev_prev: int | None = None
    for i, degree in enumerate(plan.degrees_upper):
        pos = plan.degree_positions[i]
        offset: Fraction = (
            plan.start_offset
            + (pos.bar - 1) * bar_length
            + (pos.beat - 1) * beat_unit
        )
        key_for_degree: Key = plan.degree_keys[i] if plan.degree_keys is not None else plan.local_key
        midi: int = degree_to_nearest_midi(
            degree=degree,
            key=key_for_degree,
            target_midi=prev_midi,
            midi_range=(plan.upper_range.low, plan.upper_range.high),
            prev_midi=actual_prev,
            prev_prev_midi=prev_prev,
        )
        structural_tones.append((offset, midi))
        structural_keys.append((offset, key_for_degree))
        prev_prev = actual_prev
        actual_prev = midi
        prev_midi = midi
    structural_map: dict[Fraction, int] = dict(structural_tones)
    structural_key_map: dict[Fraction, Key] = dict(structural_keys)
    bar_structural_offsets: dict[int, frozenset[Fraction]] = {}
    for st_offset, _ in structural_tones:
        bar_num_for_st: int = int((st_offset - plan.start_offset) // bar_length) + 1
        bar_rel: Fraction = st_offset - plan.start_offset - (bar_num_for_st - 1) * bar_length
        bar_structural_offsets.setdefault(bar_num_for_st, set()).add(bar_rel)
    bar_structural_offsets = {k: frozenset(v) for k, v in bar_structural_offsets.items()}
    # Cross-phrase guard: compute next phrase's first soprano pitch
    next_entry_midi: int | None = None
    if (
        next_phrase_entry_degree is not None
        and next_phrase_entry_key is not None
        and len(structural_tones) > 0
    ):
        next_entry_midi = degree_to_nearest_midi(
            degree=next_phrase_entry_degree,
            key=next_phrase_entry_key,
            target_midi=structural_tones[-1][1],
            midi_range=(plan.upper_range.low, plan.upper_range.high),
        )
    # Pre-compute figured pitch sequence between each pair of structural tones.
    # This gives us a pool of pitches per span; the bar-by-bar rhythm cell loop
    # consumes them in order. This keeps the old rhythm cell variety (avoiding
    # lockstep) while replacing stepwise pitch fill with figured diminutions.
    phrase_end: Fraction = plan.start_offset + plan.phrase_duration
    end_midi_target: int = (
        next_entry_midi if next_entry_midi is not None
        else (structural_tones[-1][1] if structural_tones else plan.upper_median)
    )
    midi_range: tuple[int, int] = (plan.upper_range.low, plan.upper_range.high)
    is_minor: bool = plan.local_key.mode == "minor"
    # Build pitch pool from figuration spans
    figured_pitches: dict[int, list[int]] = {}  # span_idx -> pitch sequence
    collected_figure_names: list[str] = []
    prev_figure_name: str | None = None
    for si in range(len(structural_tones)):
        a_off, a_midi = structural_tones[si]
        a_key: Key = structural_keys[si][1]
        if si + 1 < len(structural_tones):
            b_off, b_midi = structural_tones[si + 1]
        else:
            b_off = phrase_end
            b_midi = end_midi_target
        if b_off <= a_off:
            continue
        bar_num_for_span: int = int((a_off - plan.start_offset) // bar_length) + 1
        is_final: bool = si == len(structural_tones) - 1
        position: str = "cadential" if is_final else "passing"
        span_notes, fig_name = figurate_soprano_span(
            start_offset=a_off,
            start_midi=a_midi,
            end_offset=b_off,
            end_midi=b_midi,
            key=a_key,
            metre=plan.metre,
            character="plain",
            position=position,
            is_minor=is_minor,
            bar_num=bar_num_for_span,
            midi_range=midi_range,
            prev_figure_name=prev_figure_name,
        )
        prev_figure_name = fig_name
        collected_figure_names.append(fig_name)
        # Store just the pitches (skip first — that's the structural tone itself)
        figured_pitches[si] = [p for _, p, _ in span_notes[1:]]
    # Now do the bar-by-bar rhythm cell loop (preserving old timing logic),
    # but use figured pitches instead of stepwise fill.
    notes: list[Note] = []
    current_offset: Fraction = plan.start_offset
    current_midi: int = (
        prev_exit_midi if prev_exit_midi is not None
        else structural_tones[0][1] if structural_tones else plan.upper_median
    )
    current_key: Key = structural_keys[0][1] if structural_keys else plan.local_key
    prev_cell_name: str | None = None
    struct_idx: int = 0
    recovery_direction: int = 0
    # Index into figured pitch pool for current span
    fig_pool_idx: int = 0
    fig_pool: list[int] = figured_pitches.get(0, [])
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
            required_onsets=bar_structural_offsets.get(bar_num),
        )
        prev_cell_name = cell.name
        note_offset: Fraction = bar_start
        for dur in cell.durations:
            if note_offset in structural_map:
                pitch: int = structural_map[note_offset]
                if note_offset in structural_key_map:
                    current_key = structural_key_map[note_offset]
                # Advance to next span's pool when we hit a structural tone
                while struct_idx < len(structural_tones):
                    if structural_tones[struct_idx][0] <= note_offset:
                        struct_idx += 1
                    else:
                        break
                # Reset figure pool for new span
                pool_key: int = struct_idx - 1 if struct_idx > 0 else 0
                fig_pool = figured_pitches.get(pool_key, [])
                fig_pool_idx = 0
                leap: int = abs(pitch - current_midi) if current_midi != plan.upper_median else 0
                if leap > LEAP_THRESHOLD:
                    recovery_direction = +1 if pitch < current_midi else -1
                else:
                    recovery_direction = 0
            else:
                # Use figured pitch if available, else fall back to old logic
                if recovery_direction != 0:
                    candidate_pitch: int = current_key.diatonic_step(midi=current_midi, steps=recovery_direction)
                    if plan.upper_range.low <= candidate_pitch <= plan.upper_range.high:
                        pitch = candidate_pitch
                    else:
                        pitch = current_midi
                    recovery_direction = 0
                elif fig_pool_idx < len(fig_pool):
                    target_pitch: int = fig_pool[fig_pool_idx]
                    fig_pool_idx += 1
                    # If figured pitch is within a step, use it directly.
                    # Otherwise, step toward it (preserving direction/shape
                    # while respecting leap-step constraint).
                    if abs(target_pitch - current_midi) <= STEP_SEMITONES:
                        pitch = target_pitch
                    else:
                        step_toward: int = +1 if target_pitch > current_midi else -1
                        pitch = current_key.diatonic_step(midi=current_midi, steps=step_toward)
                    # Ensure pitch stays in range
                    if pitch < plan.upper_range.low or pitch > plan.upper_range.high:
                        pitch = current_midi
                else:
                    # Fallback: step toward next structural tone (old logic)
                    next_struct_offset: Fraction
                    next_struct_midi: int
                    if struct_idx < len(structural_tones):
                        next_struct_offset, next_struct_midi = structural_tones[struct_idx]
                    else:
                        next_struct_offset = plan.start_offset + plan.phrase_duration
                        next_struct_midi = next_entry_midi if next_entry_midi is not None else current_midi
                    if next_struct_midi > current_midi:
                        direction = +1
                    elif next_struct_midi < current_midi:
                        direction = -1
                    else:
                        direction = +1 if (bar_num % 2 == 0) else -1
                    candidate_pitch = current_key.diatonic_step(midi=current_midi, steps=direction)
                    if plan.upper_range.low <= candidate_pitch <= plan.upper_range.high:
                        pitch = candidate_pitch
                    else:
                        alt_pitch: int = current_key.diatonic_step(midi=current_midi, steps=-direction)
                        if plan.upper_range.low <= alt_pitch <= plan.upper_range.high:
                            pitch = alt_pitch
                        else:
                            pitch = current_midi
            # D007: prevent cross-bar pitch repetition at bar entry
            is_bar_entry: bool = note_offset == bar_start and bar_num > 1
            if (
                is_bar_entry
                and pitch == current_midi
                and note_offset not in structural_map
            ):
                next_target: int = (
                    structural_tones[struct_idx][1]
                    if struct_idx < len(structural_tones)
                    else pitch + 1
                )
                pitch = _deflect_neighbour(
                    pitch=pitch,
                    key=current_key,
                    midi_range=(plan.upper_range.low, plan.upper_range.high),
                    target_pitch=next_target,
                )
            # D007: prevent cross-bar pitch repetition at bar exit
            next_bar_start: Fraction = bar_start + bar_length
            is_bar_exit: bool = note_offset + dur == next_bar_start
            if (
                is_bar_exit
                and bar_num < plan.bar_span
                and next_bar_start in structural_map
                and structural_map[next_bar_start] == pitch
                and note_offset not in structural_map
            ):
                next_target_exit: int = structural_map[next_bar_start]
                pitch = _deflect_neighbour(
                    pitch=pitch,
                    key=current_key,
                    midi_range=(plan.upper_range.low, plan.upper_range.high),
                    target_pitch=next_target_exit,
                )
            # Ugly-interval guard
            if note_offset not in structural_map:
                if struct_idx < len(structural_tones):
                    guard_target: int = structural_tones[struct_idx][1]
                elif next_entry_midi is not None:
                    guard_target = next_entry_midi
                else:
                    guard_target = pitch
                guard_interval: int = abs(pitch - guard_target)
                if guard_interval > STEP_SEMITONES and guard_interval % 12 in UGLY_INTERVALS:
                    toward: int = +1 if guard_target > pitch else -1
                    for try_dir in (toward, -toward):
                        alt: int = current_key.diatonic_step(midi=pitch, steps=try_dir)
                        if plan.upper_range.low <= alt <= plan.upper_range.high:
                            alt_interval: int = abs(alt - guard_target)
                            if alt_interval <= STEP_SEMITONES or alt_interval % 12 not in UGLY_INTERVALS:
                                pitch = alt
                                break
            # Range and leap guards
            assert plan.upper_range.low <= pitch <= plan.upper_range.high, (
                f"Soprano fill pitch {pitch} outside range "
                f"[{plan.upper_range.low}, {plan.upper_range.high}] "
                f"at offset {note_offset}, bar {bar_num}; "
                f"current_midi={current_midi}, recovery_direction={recovery_direction}"
            )
            notes.append(Note(
                offset=note_offset,
                pitch=pitch,
                duration=dur,
                voice=TRACK_SOPRANO,
            ))
            current_midi = pitch
            note_offset += dur
        current_offset = note_offset
    _validate_soprano_notes(
        notes=notes,
        plan=plan,
        structural_offsets=frozenset(structural_map.keys()),
    )
    return tuple(notes), tuple(collected_figure_names)


def generate_bass_phrase(
    plan: PhrasePlan,
    soprano_notes: tuple[Note, ...],
    prev_exit_midi: int | None = None,
    prev_prev_exit_midi: int | None = None,
) -> tuple[Note, ...]:
    """Generate bass notes for one phrase, checked against soprano."""
    assert not plan.is_cadential, (
        f"generate_bass_phrase called with cadential plan '{plan.schema_name}'; "
        f"use write_phrase() which delegates to write_cadence()"
    )
    bar_length, beat_unit = parse_metre(metre=plan.metre)
    structural_tones: list[tuple[Fraction, int]] = []
    structural_keys: list[tuple[Fraction, Key]] = []
    prev_midi: int = (
        prev_exit_midi if prev_exit_midi is not None
        else plan.lower_median
    )
    actual_prev: int | None = prev_exit_midi
    prev_prev: int | None = None
    for i, degree in enumerate(plan.degrees_lower):
        pos = plan.degree_positions[i]
        offset: Fraction = (
            plan.start_offset
            + (pos.bar - 1) * bar_length
            + (pos.beat - 1) * beat_unit
        )
        key_for_degree: Key = plan.degree_keys[i] if plan.degree_keys is not None else plan.local_key
        soprano_at_offset: int | None = _soprano_pitch_at_offset(soprano_notes=soprano_notes, offset=offset)
        if soprano_at_offset is not None:
            midi: int = _find_consonant_alternative(
                target_degree=degree,
                key=key_for_degree,
                soprano_pitch=soprano_at_offset,
                bass_range=(plan.lower_range.low, plan.lower_range.high),
                prev_bass_midi=prev_midi,
                prev_prev_bass_midi=prev_prev,
            )
        else:
            midi = degree_to_nearest_midi(
                degree=degree,
                key=key_for_degree,
                target_midi=prev_midi,
                midi_range=(plan.lower_range.low, plan.lower_range.high),
                prev_midi=actual_prev,
                prev_prev_midi=prev_prev,
            )
        structural_tones.append((offset, midi))
        structural_keys.append((offset, key_for_degree))
        prev_prev = actual_prev
        actual_prev = midi
        prev_midi = midi
    structural_map: dict[Fraction, int] = dict(structural_tones)
    structural_key_map: dict[Fraction, Key] = dict(structural_keys)
    bar_structural_offsets: dict[int, frozenset[Fraction]] = {}
    for st_offset, _ in structural_tones:
        bar_num_for_st: int = int((st_offset - plan.start_offset) // bar_length) + 1
        bar_rel: Fraction = st_offset - plan.start_offset - (bar_num_for_st - 1) * bar_length
        bar_structural_offsets.setdefault(bar_num_for_st, set()).add(bar_rel)
    bar_structural_offsets = {k: frozenset(v) for k, v in bar_structural_offsets.items()}
    # Pre-compute soprano onset offsets per bar (bar-relative) for
    # complementary rhythm selection — shared by both textures
    soprano_onsets_per_bar: dict[int, frozenset[Fraction]] = {}
    for sn in soprano_notes:
        s_bar: int = int((sn.offset - plan.start_offset) // bar_length) + 1
        s_rel: Fraction = sn.offset - plan.start_offset - (s_bar - 1) * bar_length
        soprano_onsets_per_bar.setdefault(s_bar, set()).add(s_rel)
    soprano_onsets_per_bar = {
        k: frozenset(v) for k, v in soprano_onsets_per_bar.items()
    }
    texture: str = plan.bass_texture
    # Walking patterns should use walking texture path for complementary rhythm
    use_pattern_bass: bool = (
        texture == "pillar"
        and plan.bass_pattern is not None
        and not plan.bass_pattern.startswith("continuo_walking")
    )
    notes: list[Note] = []
    if use_pattern_bass:
        # Patterned bass: use realise_bass_pattern for each bar
        pattern = get_bass_pattern(name=plan.bass_pattern)
        assert pattern is not None, (
            f"Bass pattern '{plan.bass_pattern}' not found"
        )
        prev_bp_pitch: int | None = prev_exit_midi
        prev_prev_bp: int | None = prev_prev_exit_midi
        # Soprano onset set for common-onset parallel checking
        soprano_onset_set: frozenset[Fraction] = frozenset(
            n.offset for n in soprano_notes
        )
        # Track last common onset (where both voices start a note)
        # for parallel-fifth detection matching fault checker logic
        prev_common_bass: int | None = None
        prev_common_sop: int | None = None
        # Map bar numbers to their first structural bass degree (for the bar's root)
        bar_degree_map: dict[int, int] = {}
        for i, degree in enumerate(plan.degrees_lower):
            pos = plan.degree_positions[i]
            if pos.bar not in bar_degree_map:
                bar_degree_map[pos.bar] = degree
        current_bass_degree: int = plan.degrees_lower[0] if plan.degrees_lower else 1
        # Count structural tones per bar for fallback logic
        bar_struct_count: dict[int, int] = {}
        for pos in plan.degree_positions:
            bar_struct_count[pos.bar] = bar_struct_count.get(pos.bar, 0) + 1
        for bar_num in range(1, plan.bar_span + 1):
            bar_start: Fraction = plan.start_offset + (bar_num - 1) * bar_length
            if bar_num in bar_degree_map:
                current_bass_degree = bar_degree_map[bar_num]
            key_for_bar: Key = plan.local_key
            # Use degree_keys if available for this bar's structural tone
            for i, pos in enumerate(plan.degree_positions):
                if pos.bar == bar_num and plan.degree_keys is not None:
                    key_for_bar = plan.degree_keys[i]
                    break
            # If bar has more structural tones than pattern beats,
            # fall back to structural tones directly
            n_struct_in_bar: int = bar_struct_count.get(bar_num, 0)
            if n_struct_in_bar > len(pattern.beats):
                # Emit structural tones as individual notes splitting the bar
                bar_structs: list[tuple[Fraction, int]] = [
                    (off, midi) for off, midi in structural_tones
                    if bar_start <= off < bar_start + bar_length
                ]
                bar_structs.sort(key=lambda x: x[0])
                for j, (st_off, st_midi) in enumerate(bar_structs):
                    # Duration: until next structural tone or bar end
                    if j + 1 < len(bar_structs):
                        st_dur: Fraction = bar_structs[j + 1][0] - st_off
                    else:
                        st_dur = bar_start + bar_length - st_off
                    sop_here_fb: int | None = _soprano_pitch_at_offset(
                        soprano_notes=soprano_notes, offset=st_off,
                    )
                    fb_pitch: int = st_midi
                    if sop_here_fb is not None and fb_pitch > sop_here_fb:
                        fb_pitch -= 12
                    notes.append(Note(
                        offset=st_off,
                        pitch=fb_pitch,
                        duration=st_dur,
                        voice=TRACK_BASS,
                    ))
                    if st_off in soprano_onset_set and sop_here_fb is not None:
                        prev_common_bass = fb_pitch
                        prev_common_sop = sop_here_fb
                    prev_prev_bp = prev_bp_pitch
                    prev_bp_pitch = fb_pitch
                continue
            pattern_notes = realise_bass_pattern(
                pattern=pattern,
                bass_degree=current_bass_degree,
                key=key_for_bar,
                bar_offset=bar_start,
                bar_duration=bar_length,
                bass_median=plan.lower_median,
                metre=plan.metre,
                prev_pitch=prev_bp_pitch,
                prev_prev_pitch=prev_prev_bp,
            )
            for p_offset, p_midi, p_dur in pattern_notes:
                # Override with structural pitch if this offset is a structural tone
                if p_offset in structural_map:
                    p_midi = structural_map[p_offset]
                # Voice crossing check
                sop_here: int | None = _soprano_pitch_at_offset(
                    soprano_notes=soprano_notes,
                    offset=p_offset,
                )
                pitch: int = p_midi
                # If bass above soprano, try octave below
                if sop_here is not None and pitch > sop_here:
                    pitch -= 12
                if pitch < plan.lower_range.low:
                    pitch = p_midi  # revert if out of range
                assert plan.lower_range.low <= pitch <= plan.lower_range.high, (
                    f"Pattern bass pitch {pitch} outside range "
                    f"[{plan.lower_range.low}, {plan.lower_range.high}] "
                    f"at offset {p_offset}, bar {bar_num}, "
                    f"pattern {plan.bass_pattern}"
                )
                assert sop_here is None or pitch <= sop_here, (
                    f"Pattern bass {pitch} > soprano {sop_here} "
                    f"at offset {p_offset}, bar {bar_num}"
                )
                # Check parallel perfects at common onsets (where both
                # voices start a note), matching fault checker logic
                is_common_onset: bool = (
                    sop_here is not None
                    and p_offset in soprano_onset_set
                )
                if (
                    is_common_onset
                    and prev_common_bass is not None
                    and prev_common_sop is not None
                    and _check_parallel_perfects(
                        bass_pitch=pitch,
                        soprano_pitch=sop_here,
                        prev_bass_pitch=prev_common_bass,
                        prev_soprano_pitch=prev_common_sop,
                    )
                ):
                    # For structural offsets: try octave shift
                    # For non-structural: try diatonic step
                    pp_candidates: list[int] = []
                    if p_offset in structural_map:
                        pp_candidates = [pitch - 12, pitch + 12]
                    else:
                        pp_candidates = [
                            key_for_bar.diatonic_step(midi=pitch, steps=-1),
                            key_for_bar.diatonic_step(midi=pitch, steps=+1),
                        ]
                    for alt_bp in pp_candidates:
                        if (
                            plan.lower_range.low <= alt_bp <= plan.lower_range.high
                            and (sop_here is None or alt_bp <= sop_here)
                            and not _check_parallel_perfects(
                                bass_pitch=alt_bp,
                                soprano_pitch=sop_here,
                                prev_bass_pitch=prev_common_bass,
                                prev_soprano_pitch=prev_common_sop,
                            )
                        ):
                            pitch = alt_bp
                            break
                # Check consecutive same-direction leaps
                if prev_prev_bp is not None and prev_bp_pitch is not None:
                    prev_leap: int = prev_bp_pitch - prev_prev_bp
                    curr_leap: int = pitch - prev_bp_pitch
                    if (
                        abs(prev_leap) > SKIP_SEMITONES
                        and abs(curr_leap) > SKIP_SEMITONES
                        and (prev_leap > 0) == (curr_leap > 0)
                    ):
                        # Try octave flip to reverse direction
                        flip: int = pitch + (12 if curr_leap < 0 else -12)
                        if (
                            plan.lower_range.low <= flip <= plan.lower_range.high
                            and (sop_here is None or flip <= sop_here)
                        ):
                            pitch = flip
                notes.append(Note(
                    offset=p_offset,
                    pitch=pitch,
                    duration=p_dur,
                    voice=TRACK_BASS,
                ))
                # Update common-onset tracking
                if is_common_onset:
                    prev_common_bass = pitch
                    prev_common_sop = sop_here
                prev_prev_bp = prev_bp_pitch
                prev_bp_pitch = pitch
    elif texture == "pillar":
        # Legacy pillar: no bass_pattern declared
        current_midi: int = (
            prev_exit_midi if prev_exit_midi is not None
            else structural_tones[0][1] if structural_tones else plan.lower_median
        )
        prev_cell_name: str | None = None
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
                required_onsets=bar_structural_offsets.get(bar_num),
                soprano_onsets=soprano_onsets_per_bar.get(bar_num),
            )
            prev_cell_name = cell.name
            note_offset: Fraction = bar_start
            for dur in cell.durations:
                if note_offset in structural_map:
                    pitch = structural_map[note_offset]
                else:
                    pitch = current_midi
                assert plan.lower_range.low <= pitch <= plan.lower_range.high, (
                    f"Pillar bass pitch {pitch} outside range "
                    f"[{plan.lower_range.low}, {plan.lower_range.high}] "
                    f"at offset {note_offset}, bar {bar_num}"
                )
                sop_here = _soprano_pitch_at_offset(
                    soprano_notes=soprano_notes,
                    offset=note_offset,
                )
                assert sop_here is None or pitch <= sop_here, (
                    f"Pillar bass {pitch} > soprano {sop_here} "
                    f"at offset {note_offset}, bar {bar_num}"
                )
                notes.append(Note(
                    offset=note_offset,
                    pitch=pitch,
                    duration=dur,
                    voice=TRACK_BASS,
                ))
                current_midi = pitch
                note_offset += dur
    else:
        current_midi = (
            prev_exit_midi if prev_exit_midi is not None
            else structural_tones[0][1] if structural_tones else plan.lower_median
        )
        current_key: Key = structural_keys[0][1] if structural_keys else plan.local_key
        struct_idx: int = 0
        prev_bass: int | None = None
        prev_soprano: int | None = None
        # Common-onset tracking for parallel-fifth detection
        walk_soprano_onsets: frozenset[Fraction] = frozenset(
            n.offset for n in soprano_notes
        )
        prev_common_bass_w: int | None = None
        prev_common_sop_w: int | None = None
        prev_cell_name: str | None = None
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
                required_onsets=bar_structural_offsets.get(bar_num),
                soprano_onsets=soprano_onsets_per_bar.get(bar_num),
            )
            prev_cell_name = cell.name
            note_offset: Fraction = bar_start
            for note_idx, dur in enumerate(cell.durations):
                # L004: look up soprano ceiling before computing bass pitch
                sop_here: int | None = _soprano_pitch_at_offset(
                    soprano_notes=soprano_notes,
                    offset=note_offset,
                )
                from_structural: bool = note_offset in structural_map
                if from_structural:
                    pitch = structural_map[note_offset]
                    if note_offset in structural_key_map:
                        current_key = structural_key_map[note_offset]
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
                    # Determine step direction, respecting soprano ceiling
                    if next_struct_midi > current_midi:
                        candidate: int = current_key.diatonic_step(midi=current_midi, steps=+1)
                        if sop_here is not None and candidate > sop_here:
                            candidate = current_key.diatonic_step(midi=current_midi, steps=-1)
                        pitch = candidate
                    elif next_struct_midi < current_midi:
                        pitch = current_key.diatonic_step(midi=current_midi, steps=-1)
                    else:
                        pitch = current_midi
                assert plan.lower_range.low <= pitch <= plan.lower_range.high, (
                    f"Walking bass pitch {pitch} outside range "
                    f"[{plan.lower_range.low}, {plan.lower_range.high}] "
                    f"at offset {note_offset}, bar {bar_num}; "
                    f"current_midi={current_midi}, from_structural={from_structural}"
                )
                assert sop_here is None or pitch <= sop_here, (
                    f"Bass {pitch} above soprano {sop_here} "
                    f"at offset {note_offset}, bar {bar_num}"
                )
                # Use cell accent_pattern instead of offset-based strong beat check
                is_accented: bool = cell.accent_pattern[note_idx]
                is_common_w: bool = (
                    sop_here is not None
                    and note_offset in walk_soprano_onsets
                )
                if is_accented and sop_here is not None and not from_structural:
                    pitch = _select_strong_beat_bass(
                        candidate=pitch,
                        soprano_pitch=sop_here,
                        key=current_key,
                        bass_range=(plan.lower_range.low, plan.lower_range.high),
                        prev_bass=prev_common_bass_w,
                        prev_soprano=prev_common_sop_w,
                    )
                # Check parallels at common onsets (matching fault checker)
                if (
                    is_common_w
                    and prev_common_bass_w is not None
                    and prev_common_sop_w is not None
                    and _check_parallel_perfects(
                        bass_pitch=pitch,
                        soprano_pitch=sop_here,
                        prev_bass_pitch=prev_common_bass_w,
                        prev_soprano_pitch=prev_common_sop_w,
                    )
                ):
                    # Try one step in opposite direction to break the parallel
                    alt: int = current_key.diatonic_step(midi=pitch, steps=-1)
                    if alt < plan.lower_range.low:
                        alt = current_key.diatonic_step(midi=pitch, steps=+1)
                    if (
                        plan.lower_range.low <= alt <= plan.lower_range.high
                        and (sop_here is None or alt <= sop_here)
                        and not _check_parallel_perfects(
                            bass_pitch=alt,
                            soprano_pitch=sop_here,
                            prev_bass_pitch=prev_common_bass_w,
                            prev_soprano_pitch=prev_common_sop_w,
                        )
                    ):
                        pitch = alt
                if sop_here is not None:
                    prev_bass = pitch
                    prev_soprano = sop_here
                if is_common_w:
                    prev_common_bass_w = pitch
                    prev_common_sop_w = sop_here
                notes.append(Note(
                    offset=note_offset,
                    pitch=pitch,
                    duration=dur,
                    voice=TRACK_BASS,
                ))
                current_midi = pitch
                note_offset += dur
    _validate_bass_notes(notes=notes, plan=plan, soprano_notes=soprano_notes)
    return tuple(notes)


def write_phrase(
    plan: PhrasePlan,
    prev_upper_midi: int | None = None,
    prev_lower_midi: int | None = None,
    prev_prev_lower_midi: int | None = None,
    next_phrase_entry_degree: int | None = None,
    next_phrase_entry_key: Key | None = None,
) -> PhraseResult:
    """Write complete phrase (soprano + bass) and return result."""
    soprano_figures: tuple[str, ...] = ()
    bass_pattern_name: str | None = None
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
        soprano_notes, soprano_figures = generate_soprano_phrase(
            plan=plan,
            prev_exit_midi=prev_upper_midi,
            next_phrase_entry_degree=next_phrase_entry_degree,
            next_phrase_entry_key=next_phrase_entry_key,
        )
        bass_notes = generate_bass_phrase(
            plan=plan,
            soprano_notes=soprano_notes,
            prev_exit_midi=prev_lower_midi,
            prev_prev_exit_midi=prev_prev_lower_midi,
        )
        bass_pattern_name = plan.bass_pattern
    return PhraseResult(
        upper_notes=soprano_notes,
        lower_notes=bass_notes,
        exit_upper=soprano_notes[-1].pitch,
        exit_lower=bass_notes[-1].pitch,
        schema_name=plan.schema_name,
        soprano_figures=soprano_figures,
        bass_pattern_name=bass_pattern_name,
    )
