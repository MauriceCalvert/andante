"""Bass phrase generation and validation."""
from dataclasses import replace
from fractions import Fraction

from builder.figuration.bass import get_bass_pattern, realise_bass_pattern
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
    MAX_BASS_LEAP,
    PERFECT_INTERVALS,
    SKIP_SEMITONES,
    STRONG_BEAT_DISSONANT,
    TRACK_BASS,
    UGLY_INTERVALS,
    VALID_DURATIONS_SET,
)
from shared.counterpoint import prevent_cross_relation
from shared.key import Key
from shared.music_math import parse_metre
from shared.pitch import degree_to_nearest_midi


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


def _prevent_bass_leap(
    pitch: int,
    prev_pitch: int | None,
    bass_range: tuple[int, int],
    soprano_pitch: int | None,
) -> int:
    """Select a closer octave if leap from prev_pitch exceeds MAX_BASS_LEAP.

    Part of the generation/selection flow (D010: generators prevent).
    """
    if prev_pitch is None or abs(pitch - prev_pitch) <= MAX_BASS_LEAP:
        return pitch
    alts: list[int] = [pitch + 12, pitch - 12]
    valid: list[int] = [
        a for a in alts
        if bass_range[0] <= a <= bass_range[1]
        and (soprano_pitch is None or a <= soprano_pitch)
    ]
    if not valid:
        return pitch
    best: int = min(valid, key=lambda m: abs(m - prev_pitch))
    if abs(best - prev_pitch) < abs(pitch - prev_pitch):
        return best
    return pitch


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


def _last_common_onset_pair(
    soprano_notes: tuple[Note, ...],
    prior_bass: tuple[Note, ...],
    phrase_start: Fraction,
) -> tuple[int | None, int | None]:
    """Find last common-onset soprano/bass pitches from prior phrases.

    Only considers onsets strictly before phrase_start.
    Returns (soprano_pitch, bass_pitch) or (None, None).
    """
    prior_soprano_by_off: dict[Fraction, int] = {
        n.offset: n.pitch for n in soprano_notes if n.offset < phrase_start
    }
    prior_bass_by_off: dict[Fraction, int] = {n.offset: n.pitch for n in prior_bass}
    common: list[Fraction] = sorted(
        set(prior_soprano_by_off.keys()) & set(prior_bass_by_off.keys())
    )
    if not common:
        return None, None
    last: Fraction = common[-1]
    return prior_soprano_by_off[last], prior_bass_by_off[last]


def _soprano_pitch_at_offset(
    soprano_notes: tuple[Note, ...],
    offset: Fraction,
) -> int | None:
    """Return soprano MIDI pitch sounding at given offset, or None."""
    for note in soprano_notes:
        if note.offset <= offset < note.offset + note.duration:
            return note.pitch
    return None


def validate_bass_notes(
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


def generate_bass_phrase(
    plan: PhrasePlan,
    soprano_notes: tuple[Note, ...],
    prior_bass: tuple[Note, ...] = (),
) -> tuple[Note, ...]:
    """Generate bass notes for one phrase, checked against soprano."""
    assert not plan.is_cadential, (
        f"generate_bass_phrase called with cadential plan '{plan.schema_name}'; "
        f"use write_phrase() which delegates to write_cadence()"
    )
    prev_exit_midi: int | None = prior_bass[-1].pitch if prior_bass else None
    prev_prev_exit_midi: int | None = prior_bass[-2].pitch if len(prior_bass) >= 2 else None
    # Boundary tracking: last common-onset pair from prior phrases
    boundary_sop, boundary_bass = _last_common_onset_pair(
        soprano_notes=soprano_notes,
        prior_bass=prior_bass,
        phrase_start=plan.start_offset,
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
        offset: Fraction = phrase_degree_offset(plan=plan, pos=pos, bar_length=bar_length, beat_unit=beat_unit)
        key_for_degree: Key = plan.degree_keys[i]
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
        # Cross-relation prevention for structural tones
        midi = prevent_cross_relation(
            pitch=midi,
            other_notes=soprano_notes,
            offset=offset,
            beat_unit=beat_unit,
            key=key_for_degree,
            pitch_range=(plan.lower_range.low, plan.lower_range.high),
            ceiling=soprano_at_offset,
        )
        structural_tones.append((offset, midi))
        structural_keys.append((offset, key_for_degree))
        prev_prev = actual_prev
        actual_prev = midi
        prev_midi = midi
    structural_map: dict[Fraction, int] = {off: midi for off, midi in structural_tones}
    structural_key_map: dict[Fraction, Key] = {off: key for off, key in structural_keys}
    bar_structural_offsets: dict[int, frozenset[Fraction]] = {}
    for st_offset, _ in structural_tones:
        bar_num_for_st: int = phrase_offset_to_bar(plan=plan, offset=st_offset, bar_length=bar_length)
        bar_rel: Fraction = st_offset - phrase_bar_start(plan=plan, bar_num=bar_num_for_st, bar_length=bar_length)
        bar_structural_offsets.setdefault(bar_num_for_st, set()).add(bar_rel)
    bar_structural_offsets = {k: frozenset(v) for k, v in bar_structural_offsets.items()}
    # Pre-compute soprano onset offsets per bar (bar-relative) for
    # complementary rhythm selection — shared by both textures
    soprano_onsets_per_bar: dict[int, frozenset[Fraction]] = {}
    for sn in soprano_notes:
        s_bar: int = phrase_offset_to_bar(plan=plan, offset=sn.offset, bar_length=bar_length)
        s_rel: Fraction = sn.offset - phrase_bar_start(plan=plan, bar_num=s_bar, bar_length=bar_length)
        soprano_onsets_per_bar.setdefault(s_bar, set()).add(s_rel)
    soprano_onsets_per_bar = {
        k: frozenset(v) for k, v in soprano_onsets_per_bar.items()
    }
    texture: str = plan.bass_texture
    # Walking patterns should use walking texture path for complementary rhythm
    continuo_walking: bool = (
        plan.bass_pattern is not None
        and plan.bass_pattern.startswith("continuo_walking")
    )
    use_pattern_bass: bool = (
        texture == "pillar"
        and plan.bass_pattern is not None
        and not continuo_walking
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
        # for parallel-fifth detection matching fault checker logic.
        # Initialize from boundary to catch cross-phrase parallels.
        prev_common_bass: int | None = boundary_bass
        prev_common_sop: int | None = boundary_sop
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
            bar_start: Fraction = phrase_bar_start(plan=plan, bar_num=bar_num, bar_length=bar_length)
            bar_dur: Fraction = phrase_bar_duration(plan=plan, bar_num=bar_num, bar_length=bar_length)
            if bar_num in bar_degree_map:
                current_bass_degree = bar_degree_map[bar_num]
            key_for_bar: Key = plan.local_key
            # Use degree_keys if available for this bar's structural tone
            for i, pos in enumerate(plan.degree_positions):
                if pos.bar == bar_num:
                    key_for_bar = plan.degree_keys[i]
                    break
            # Anacrusis bar: emit structural tone with bar_dur, skip pattern
            if bar_dur < bar_length:
                st_pitch: int = structural_tones[0][1] if structural_tones else plan.lower_median
                sop_here_ac: int | None = _soprano_pitch_at_offset(
                    soprano_notes=soprano_notes, offset=bar_start,
                )
                if sop_here_ac is not None and st_pitch > sop_here_ac:
                    st_pitch -= 12
                st_pitch = prevent_cross_relation(
                    pitch=st_pitch,
                    other_notes=soprano_notes,
                    offset=bar_start,
                    beat_unit=beat_unit,
                    key=key_for_bar,
                    pitch_range=(plan.lower_range.low, plan.lower_range.high),
                    ceiling=sop_here_ac,
                )
                notes.append(Note(
                    offset=bar_start,
                    pitch=st_pitch,
                    duration=bar_dur,
                    voice=TRACK_BASS,
                ))
                if bar_start in soprano_onset_set and sop_here_ac is not None:
                    prev_common_bass = st_pitch
                    prev_common_sop = sop_here_ac
                prev_prev_bp = prev_bp_pitch
                prev_bp_pitch = st_pitch
                continue
            # If bar has more structural tones than pattern beats,
            # fall back to structural tones directly
            n_struct_in_bar: int = bar_struct_count.get(bar_num, 0)
            if n_struct_in_bar > len(pattern.beats):
                # Emit structural tones as individual notes splitting the bar
                bar_structs: list[tuple[Fraction, int]] = [
                    (off, midi) for off, midi in structural_tones
                    if bar_start <= off < bar_start + bar_dur
                ]
                bar_structs.sort(key=lambda x: x[0])
                for j, (st_off, st_midi) in enumerate(bar_structs):
                    # Duration: until next structural tone or bar end
                    if j + 1 < len(bar_structs):
                        st_dur: Fraction = bar_structs[j + 1][0] - st_off
                    else:
                        st_dur = bar_start + bar_dur - st_off
                    sop_here_fb: int | None = _soprano_pitch_at_offset(
                        soprano_notes=soprano_notes, offset=st_off,
                    )
                    fb_pitch: int = st_midi
                    if sop_here_fb is not None and fb_pitch > sop_here_fb:
                        fb_pitch -= 12
                    fb_pitch = _prevent_bass_leap(
                        pitch=fb_pitch,
                        prev_pitch=prev_bp_pitch,
                        bass_range=(plan.lower_range.low, plan.lower_range.high),
                        soprano_pitch=sop_here_fb,
                    )
                    fb_pitch = prevent_cross_relation(
                        pitch=fb_pitch,
                        other_notes=soprano_notes,
                        offset=st_off,
                        beat_unit=beat_unit,
                        key=key_for_bar,
                        pitch_range=(plan.lower_range.low, plan.lower_range.high),
                        ceiling=sop_here_fb,
                    )
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
                    # Structural offsets: octave shift (preserves degree).
                    # Non-structural: diatonic step.
                    if p_offset in structural_map:
                        pp_candidates: list[int] = [pitch - 12, pitch + 12]
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
                pitch = _prevent_bass_leap(
                    pitch=pitch,
                    prev_pitch=prev_bp_pitch,
                    bass_range=(plan.lower_range.low, plan.lower_range.high),
                    soprano_pitch=sop_here,
                )
                pitch = prevent_cross_relation(
                    pitch=pitch,
                    other_notes=soprano_notes,
                    offset=p_offset,
                    beat_unit=beat_unit,
                    key=key_for_bar,
                    pitch_range=(plan.lower_range.low, plan.lower_range.high),
                    ceiling=sop_here,
                )
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
    elif texture == "pillar" and not continuo_walking:
        # Legacy pillar: no bass_pattern declared
        current_midi: int = (
            prev_exit_midi if prev_exit_midi is not None
            else structural_tones[0][1] if structural_tones else plan.lower_median
        )
        prev_cell_name: str | None = None
        for bar_num in range(1, plan.bar_span + 1):
            bar_start: Fraction = phrase_bar_start(plan=plan, bar_num=bar_num, bar_length=bar_length)
            bar_dur: Fraction = phrase_bar_duration(plan=plan, bar_num=bar_num, bar_length=bar_length)
            is_final_bar: bool = bar_num == plan.bar_span
            prefer: str = "cadential" if is_final_bar else "plain"
            cell_durations: tuple[Fraction, ...]
            cell_name_p: str | None
            if bar_dur < bar_length:
                cell_durations = (bar_dur,)
                cell_name_p = None
            else:
                cell = select_cell(
                    genre=plan.rhythm_profile,
                    metre=plan.metre,
                    bar_index=bar_num - 1,
                    prefer_character=prefer,
                    avoid_name=prev_cell_name,
                    required_onsets=bar_structural_offsets.get(bar_num),
                    avoid_onsets=soprano_onsets_per_bar.get(bar_num),
                )
                cell_durations = cell.durations
                cell_name_p = cell.name
            prev_cell_name = cell_name_p
            note_offset: Fraction = bar_start
            for dur in cell_durations:
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
                # Boundary parallel-perfect prevention for first note
                if (
                    len(notes) == 0
                    and boundary_bass is not None
                    and boundary_sop is not None
                    and sop_here is not None
                    and _check_parallel_perfects(
                        bass_pitch=pitch,
                        soprano_pitch=sop_here,
                        prev_bass_pitch=boundary_bass,
                        prev_soprano_pitch=boundary_sop,
                    )
                ):
                    for step_dir in (-1, +1):
                        alt: int = plan.local_key.diatonic_step(
                            midi=pitch, steps=step_dir,
                        )
                        if (
                            plan.lower_range.low <= alt <= plan.lower_range.high
                            and alt <= sop_here
                            and abs(sop_here - alt) % 12 not in STRONG_BEAT_DISSONANT
                            and not _check_parallel_perfects(
                                bass_pitch=alt,
                                soprano_pitch=sop_here,
                                prev_bass_pitch=boundary_bass,
                                prev_soprano_pitch=boundary_sop,
                            )
                        ):
                            pitch = alt
                            break
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
        # Common-onset tracking for parallel-fifth detection.
        # Initialize from boundary to catch cross-phrase parallels.
        walk_soprano_onsets: frozenset[Fraction] = frozenset(
            n.offset for n in soprano_notes
        )
        prev_common_bass_w: int | None = boundary_bass
        prev_common_sop_w: int | None = boundary_sop
        prev_cell_name: str | None = None
        walk_direction: int = +1
        if len(structural_tones) >= 2:
            walk_direction = +1 if structural_tones[1][1] >= structural_tones[0][1] else -1
        last_struct_midi: int = current_midi
        last_structural_offset: Fraction = (
            structural_tones[-1][0] if structural_tones else Fraction(-1)
        )
        for bar_num in range(1, plan.bar_span + 1):
            bar_start: Fraction = phrase_bar_start(plan=plan, bar_num=bar_num, bar_length=bar_length)
            bar_dur: Fraction = phrase_bar_duration(plan=plan, bar_num=bar_num, bar_length=bar_length)
            is_final_bar: bool = bar_num == plan.bar_span
            prefer: str = "cadential" if is_final_bar else "plain"
            cell_durations_w: tuple[Fraction, ...]
            cell_accents_w: tuple[bool, ...]
            cell_name_w: str | None
            if bar_dur < bar_length:
                cell_durations_w = (bar_dur,)
                cell_accents_w = (True,)
                cell_name_w = None
            else:
                cell = select_cell(
                    genre=plan.rhythm_profile,
                    metre=plan.metre,
                    bar_index=bar_num - 1,
                    prefer_character=prefer,
                    avoid_name=prev_cell_name,
                    required_onsets=bar_structural_offsets.get(bar_num),
                    avoid_onsets=soprano_onsets_per_bar.get(bar_num),
                )
                cell_durations_w = cell.durations
                cell_accents_w = cell.accent_pattern
                cell_name_w = cell.name
            prev_cell_name = cell_name_w
            note_offset: Fraction = bar_start
            for note_idx, dur in enumerate(cell_durations_w):
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
                    last_struct_midi = pitch
                    # Re-derive walk_direction from soprano trajectory
                    # (contrary motion preference)
                    sop_at_struct: int | None = sop_here
                    next_sop_at_struct: int | None = None
                    if struct_idx < len(structural_tones):
                        next_sop_at_struct = _soprano_pitch_at_offset(
                            soprano_notes=soprano_notes,
                            offset=structural_tones[struct_idx][0],
                        )
                    if sop_at_struct is not None and next_sop_at_struct is not None:
                        sop_motion: int = next_sop_at_struct - sop_at_struct
                        if sop_motion > 0:
                            walk_direction = -1
                        elif sop_motion < 0:
                            walk_direction = +1
                        else:
                            # Soprano static: derive from bass structural
                            if struct_idx < len(structural_tones):
                                bass_target_dir: int = structural_tones[struct_idx][1] - pitch
                                if bass_target_dir > 0:
                                    walk_direction = +1
                                elif bass_target_dir < 0:
                                    walk_direction = -1
                                else:
                                    # Equal structural tones: move away,
                                    # creating neighbour-tone arc
                                    walk_direction = -walk_direction if walk_direction != 0 else +1
                    elif struct_idx < len(structural_tones):
                        bass_target_dir = structural_tones[struct_idx][1] - pitch
                        if bass_target_dir > 0:
                            walk_direction = +1
                        elif bass_target_dir < 0:
                            walk_direction = -1
                        else:
                            walk_direction = -walk_direction if walk_direction != 0 else +1
                else:
                    # Walking bass: approach before structural tones
                    # Chromatic approach ONLY at cadential arrivals;
                    # all other arrivals use diatonic stepping.
                    is_approach: bool = (note_offset + dur) in structural_map
                    if is_approach:
                        upcoming_midi: int = structural_map[note_offset + dur]
                        upcoming_offset: Fraction = note_offset + dur
                        # Chromatic approach only when approaching the
                        # LAST structural tone of a cadential phrase
                        is_cadential_approach: bool = (
                            upcoming_offset == last_structural_offset
                            and plan.cadence_type is not None
                        )
                        if is_cadential_approach:
                            # Chromatic semitone into the cadence target
                            if walk_direction >= 0:
                                pitch = upcoming_midi - 1
                            else:
                                pitch = upcoming_midi + 1
                            # Avoid repeated note
                            if pitch == current_midi:
                                pitch = (
                                    upcoming_midi + 1
                                    if walk_direction >= 0
                                    else upcoming_midi - 1
                                )
                            # Cross-relation guard: if chromatic pitch
                            # is out of key, check soprano within +-1
                            # beat for the diatonic form
                            approach_pc: int = pitch % 12
                            if approach_pc not in current_key.pitch_class_set:
                                diatonic_pc: int = -1
                                for cand_pc in [
                                    (approach_pc - 1) % 12,
                                    (approach_pc + 1) % 12,
                                ]:
                                    if cand_pc in current_key.pitch_class_set:
                                        diatonic_pc = cand_pc
                                        break
                                if diatonic_pc >= 0:
                                    for sop_note in soprano_notes:
                                        if abs(sop_note.offset - note_offset) <= beat_unit:
                                            if sop_note.pitch % 12 == diatonic_pc:
                                                # Cross-relation: fall
                                                # back to diatonic
                                                if upcoming_midi > current_midi:
                                                    pitch = current_key.diatonic_step(
                                                        midi=current_midi, steps=+1,
                                                    )
                                                elif upcoming_midi < current_midi:
                                                    pitch = current_key.diatonic_step(
                                                        midi=current_midi, steps=-1,
                                                    )
                                                else:
                                                    pitch = current_key.diatonic_step(
                                                        midi=current_midi,
                                                        steps=walk_direction,
                                                    )
                                                break
                            # Fallback if out of range or above soprano
                            if (
                                pitch < plan.lower_range.low
                                or pitch > plan.lower_range.high
                                or (sop_here is not None and pitch > sop_here)
                            ):
                                if upcoming_midi > current_midi:
                                    pitch = current_key.diatonic_step(
                                        midi=current_midi, steps=+1,
                                    )
                                elif upcoming_midi < current_midi:
                                    pitch = current_key.diatonic_step(
                                        midi=current_midi, steps=-1,
                                    )
                                else:
                                    pitch = current_key.diatonic_step(
                                        midi=current_midi,
                                        steps=walk_direction,
                                    )
                            # Last resort: avoid same pitch as target
                            if pitch == upcoming_midi:
                                away_dir: int = (
                                    -1 if upcoming_midi >= current_midi
                                    else +1
                                )
                                away_pitch: int = current_key.diatonic_step(
                                    midi=current_midi, steps=away_dir,
                                )
                                if (
                                    plan.lower_range.low <= away_pitch <= plan.lower_range.high
                                    and (sop_here is None or away_pitch <= sop_here)
                                ):
                                    pitch = away_pitch
                        else:
                            # Non-cadential approach: diatonic step
                            # toward the upcoming structural tone
                            if upcoming_midi > current_midi:
                                pitch = current_key.diatonic_step(
                                    midi=current_midi, steps=+1,
                                )
                            elif upcoming_midi < current_midi:
                                pitch = current_key.diatonic_step(
                                    midi=current_midi, steps=-1,
                                )
                            else:
                                pitch = current_key.diatonic_step(
                                    midi=current_midi,
                                    steps=walk_direction,
                                )
                            # Avoid same pitch as target on arrival
                            if pitch == upcoming_midi:
                                away_dir = (
                                    -1 if upcoming_midi >= current_midi
                                    else +1
                                )
                                away_pitch = current_key.diatonic_step(
                                    midi=current_midi, steps=away_dir,
                                )
                                if (
                                    plan.lower_range.low <= away_pitch <= plan.lower_range.high
                                    and (sop_here is None or away_pitch <= sop_here)
                                ):
                                    pitch = away_pitch
                            # Range/soprano fallback
                            if (
                                pitch < plan.lower_range.low
                                or pitch > plan.lower_range.high
                                or (sop_here is not None and pitch > sop_here)
                            ):
                                pitch = current_midi
                    else:
                        # Range guard: reverse within 2 semitones of boundary
                        if current_midi - plan.lower_range.low < 2:
                            walk_direction = +1
                        elif plan.lower_range.high - current_midi < 2:
                            walk_direction = -1
                        # Safety-net: reverse if >7 semitones from last
                        # structural tone (prevents wandering beyond easy
                        # stepwise return — a proxy, not a musical rule)
                        elif abs(current_midi - last_struct_midi) > 7:
                            walk_direction = (
                                +1 if last_struct_midi > current_midi
                                else -1
                            )
                        pitch = current_key.diatonic_step(
                            midi=current_midi, steps=walk_direction,
                        )
                    # Soprano ceiling
                    if sop_here is not None and pitch > sop_here:
                        pitch = current_key.diatonic_step(
                            midi=current_midi, steps=-1,
                        )
                        walk_direction = -1
                    # Range fallback
                    if (
                        pitch < plan.lower_range.low
                        or pitch > plan.lower_range.high
                    ):
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
                is_accented: bool = cell_accents_w[note_idx]
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
                    # Structural tones: octave shift (preserves degree).
                    # Non-structural: diatonic step ±1, ±2, then octave.
                    if from_structural:
                        pp_candidates: list[int] = [pitch - 12, pitch + 12]
                    else:
                        pp_candidates = [
                            current_key.diatonic_step(midi=pitch, steps=-1),
                            current_key.diatonic_step(midi=pitch, steps=+1),
                            current_key.diatonic_step(midi=pitch, steps=-2),
                            current_key.diatonic_step(midi=pitch, steps=+2),
                            pitch - 12,
                            pitch + 12,
                        ]
                    for alt_pp in pp_candidates:
                        if (
                            plan.lower_range.low <= alt_pp <= plan.lower_range.high
                            and (sop_here is None or alt_pp <= sop_here)
                            and not _check_parallel_perfects(
                                bass_pitch=alt_pp,
                                soprano_pitch=sop_here,
                                prev_bass_pitch=prev_common_bass_w,
                                prev_soprano_pitch=prev_common_sop_w,
                            )
                        ):
                            pitch = alt_pp
                            break
                # Lookahead check: prevent parallel octaves with next soprano note
                # even if not a common onset (11b fix)
                if sop_here is not None and prev_bass is not None and prev_soprano is not None:
                    next_sop_off: Fraction = note_offset + dur
                    next_sop_pitch: int | None = _soprano_pitch_at_offset(
                        soprano_notes=soprano_notes,
                        offset=next_sop_off,
                    )
                    if (
                        next_sop_pitch is not None
                        and _check_parallel_perfects(
                            bass_pitch=pitch,
                            soprano_pitch=next_sop_pitch,
                            prev_bass_pitch=prev_bass,
                            prev_soprano_pitch=prev_soprano,
                        )
                    ):
                        # Try alternatives: ±1, ±2, octave
                        lookahead_candidates: list[int] = [
                            current_key.diatonic_step(midi=pitch, steps=-1),
                            current_key.diatonic_step(midi=pitch, steps=+1),
                            current_key.diatonic_step(midi=pitch, steps=-2),
                            current_key.diatonic_step(midi=pitch, steps=+2),
                            pitch - 12,
                            pitch + 12,
                        ]
                        for alt_la in lookahead_candidates:
                            if (
                                plan.lower_range.low <= alt_la <= plan.lower_range.high
                                and (sop_here is None or alt_la <= sop_here)
                                and not _check_parallel_perfects(
                                    bass_pitch=alt_la,
                                    soprano_pitch=next_sop_pitch,
                                    prev_bass_pitch=prev_bass,
                                    prev_soprano_pitch=prev_soprano,
                                )
                            ):
                                pitch = alt_la
                                break
                # Cross-relation prevention (D010: generators prevent)
                pitch = prevent_cross_relation(
                    pitch=pitch,
                    other_notes=soprano_notes,
                    offset=note_offset,
                    beat_unit=beat_unit,
                    key=current_key,
                    pitch_range=(plan.lower_range.low, plan.lower_range.high),
                    ceiling=sop_here,
                )
                pitch = _prevent_bass_leap(
                    pitch=pitch,
                    prev_pitch=current_midi if notes else None,
                    bass_range=(plan.lower_range.low, plan.lower_range.high),
                    soprano_pitch=sop_here,
                )
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
    validate_bass_notes(notes=notes, plan=plan, soprano_notes=soprano_notes)
    return tuple(replace(n, generated_by="galant_bass") for n in notes)
