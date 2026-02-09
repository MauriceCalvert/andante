"""Soprano phrase generation and validation."""
from fractions import Fraction

from builder.figuration.soprano import figurate_soprano_span
from builder.phrase_types import (
    PhrasePlan,
    phrase_bar_duration,
    phrase_bar_start,
    phrase_degree_offset,
    phrase_offset_to_bar,
)
from builder.rhythm_cells import select_cell
from builder.types import Note
from shared.constants import (
    LEAP_THRESHOLD,
    MAX_MELODIC_INTERVAL,
    MIN_SOPRANO_MIDI,
    STEP_SEMITONES,
    TRACK_SOPRANO,
    UGLY_INTERVALS,
    VALID_DURATIONS_SET,
)
from shared.key import Key
from shared.music_math import parse_metre
from shared.pitch import degree_to_nearest_midi


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


def generate_soprano_phrase(
    plan: PhrasePlan,
    prior_upper: tuple[Note, ...] = (),
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
    prev_exit_midi: int | None = prior_upper[-1].pitch if prior_upper else None
    bar_length, beat_unit = parse_metre(metre=plan.metre)
    structural_tones: list[tuple[Fraction, int]] = []
    structural_keys: list[tuple[Fraction, Key]] = []
    biased_upper_median: int = plan.upper_median + plan.registral_bias
    prev_midi: int = (
        prev_exit_midi if prev_exit_midi is not None
        else biased_upper_median
    )
    actual_prev: int | None = prev_exit_midi
    prev_prev: int | None = None
    for i, degree in enumerate(plan.degrees_upper):
        pos = plan.degree_positions[i]
        offset: Fraction = phrase_degree_offset(plan=plan, pos=pos, bar_length=bar_length, beat_unit=beat_unit)
        key_for_degree: Key = plan.degree_keys[i] if plan.degree_keys is not None else plan.local_key
        midi: int = degree_to_nearest_midi(
            degree=degree,
            key=key_for_degree,
            target_midi=prev_midi,
            midi_range=(plan.upper_range.low, plan.upper_range.high),
            prev_midi=actual_prev,
            prev_prev_midi=prev_prev,
        )
        # Soprano floor clamp: preserve degree, shift up by octave
        if midi < MIN_SOPRANO_MIDI:
            midi += 12
        structural_tones.append((offset, midi))
        structural_keys.append((offset, key_for_degree))
        prev_prev = actual_prev
        actual_prev = midi
        prev_midi = midi
    structural_map: dict[Fraction, int] = dict(structural_tones)
    structural_key_map: dict[Fraction, Key] = dict(structural_keys)
    bar_structural_offsets: dict[int, frozenset[Fraction]] = {}
    for st_offset, _ in structural_tones:
        bar_num_for_st: int = phrase_offset_to_bar(plan=plan, offset=st_offset, bar_length=bar_length)
        bar_rel: Fraction = st_offset - phrase_bar_start(plan=plan, bar_num=bar_num_for_st, bar_length=bar_length)
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
        else (structural_tones[-1][1] if structural_tones else biased_upper_median)
    )
    midi_range: tuple[int, int] = (plan.upper_range.low, plan.upper_range.high)
    is_minor: bool = (
        plan.degree_keys[0].mode == "minor"
        if plan.degree_keys is not None
        else plan.local_key.mode == "minor"
    )
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
        bar_num_for_span: int = phrase_offset_to_bar(plan=plan, offset=a_off, bar_length=bar_length)
        is_final: bool = si == len(structural_tones) - 1
        position: str = "cadential" if is_final else "passing"
        span_notes, fig_name = figurate_soprano_span(
            start_offset=a_off,
            start_midi=a_midi,
            end_offset=b_off,
            end_midi=b_midi,
            key=a_key,
            metre=plan.metre,
            character=plan.character,
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
        else structural_tones[0][1] if structural_tones else biased_upper_median
    )
    current_key: Key = structural_keys[0][1] if structural_keys else plan.local_key
    prev_cell_name: str | None = None
    struct_idx: int = 0
    recovery_direction: int = 0
    # Index into figured pitch pool for current span
    fig_pool_idx: int = 0
    fig_pool: list[int] = figured_pitches.get(0, [])
    for bar_num in range(1, plan.bar_span + 1):
        bar_start: Fraction = phrase_bar_start(plan=plan, bar_num=bar_num, bar_length=bar_length)
        bar_dur: Fraction = phrase_bar_duration(plan=plan, bar_num=bar_num, bar_length=bar_length)
        is_final_bar: bool = bar_num == plan.bar_span
        prefer: str = "cadential" if is_final_bar else "plain"
        cell_durations: tuple[Fraction, ...]
        cell_name: str | None
        if bar_dur < bar_length:
            # Anacrusis bar: simple single-note rhythm
            cell_durations = (bar_dur,)
            cell_name = None
        else:
            cell = select_cell(
                genre=plan.rhythm_profile,
                metre=plan.metre,
                bar_index=bar_num - 1,
                prefer_character=prefer,
                avoid_name=prev_cell_name,
                required_onsets=bar_structural_offsets.get(bar_num),
            )
            cell_durations = cell.durations
            cell_name = cell.name
        prev_cell_name = cell_name
        note_offset: Fraction = bar_start
        for dur in cell_durations:
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
                leap: int = abs(pitch - current_midi) if current_midi != biased_upper_median else 0
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
            next_bar_start: Fraction = bar_start + bar_dur
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
