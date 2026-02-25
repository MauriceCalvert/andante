"""Hold-exchange renderer: generates hold-exchange sections (B9).

One voice holds a whole note while the other runs in consonant counterpoint via Viterbi.
"""
from fractions import Fraction

from builder.types import Note
from motifs.fragment_catalogue import extract_sixteenth_cell
from motifs.fugue_loader import LoadedFugue
from motifs.head_generator import degrees_to_midi
from planner.thematic import BeatRole, ThematicRole
from shared.constants import TRACK_BASS, TRACK_SOPRANO, STRONG_BEAT_DISSONANT
from shared.key import Key
from shared.tracer import get_tracer, _key_str
from shared.voice_types import Range
from viterbi.generate import generate_voice
from viterbi.mtypes import ExistingVoice, Knot
from viterbi.scale import KeyInfo


def _find_consonant_near(
    target_midi: int,
    held_pitch: int,
    range_low: int,
    range_high: int,
) -> int:
    """Find nearest pitch to target_midi consonant with held_pitch, within range.

    Searches outward ±1..±12. Falls back to range midpoint.
    """
    for distance in range(13):
        for candidate in (target_midi + distance, target_midi - distance):
            if range_low <= candidate <= range_high:
                if abs(candidate - held_pitch) % 12 not in STRONG_BEAT_DISSONANT:
                    return candidate
    return (range_low + range_high) // 2


def _generate_running_voice_bar(
    held_pitch: int,
    held_is_above: bool,
    running_track: int,
    running_range: Range,
    bar_start_offset: Fraction,
    bar_length: Fraction,
    beat_unit: Fraction,
    rhythm_durations: tuple[Fraction, ...],
    local_key: Key,
    prior_running_notes: tuple[Note, ...],
    prior_held_notes: tuple[Note, ...],
    cell_degrees: tuple[int, ...] = (),
    cell_iteration: int = 0,
    material_key: Key | None = None,
    subject_mode: str = "major",
) -> tuple[Note, ...]:
    """Generate one bar of running-voice notes against a held pitch.

    Voice-agnostic. Uses Viterbi to find consonant counterpoint against the held note.
    When cell_degrees is provided, builds structural knots from a descending
    diatonic sequence of the subject cell, giving the running voice motivic identity.
    """
    # Build rhythm grid: onset + duration for each note
    rhythm_grid: list[tuple[Fraction, Fraction]] = []
    cumulative: Fraction = Fraction(0)
    for dur in rhythm_durations:
        rhythm_grid.append((bar_start_offset + cumulative, dur))
        cumulative += dur

    # Add final marker for Viterbi alignment (duration -1 means "extend previous note")
    bar_end_offset: Fraction = bar_start_offset + bar_length
    rhythm_grid.append((bar_end_offset, Fraction(-1)))

    # Build ExistingVoice from held pitch (one pitch at every onset)
    held_pitches_at_beat: dict[float, int] = {}
    for onset, _ in rhythm_grid:
        held_pitches_at_beat[float(onset)] = held_pitch
    held_voice: ExistingVoice = ExistingVoice(
        pitches_at_beat=held_pitches_at_beat,
        is_above=held_is_above,
    )

    # Build KeyInfo from local_key
    key_info: KeyInfo = KeyInfo(
        pitch_class_set=local_key.pitch_class_set,
        tonic_pc=local_key.degree_to_midi(degree=1, octave=0) % 12,
    )

    running_median: int = (running_range.low + running_range.high) // 2

    # -----------------------------------------------------------
    # Build structural knots from subject cell (descending sequence)
    # -----------------------------------------------------------
    if len(cell_degrees) > 0 and material_key is not None:
        cell_duration: Fraction = sum(rhythm_durations[:len(cell_degrees)])
        iterations: int = int(bar_length / cell_duration) if cell_duration > 0 else 0
        tonic_midi: int = 60 + material_key.tonic_pc

        # Compute a single octave shift from the first cell degree so all
        # knots share the same transposition — preserves descending intervals.
        iters: int = max(iterations, 1)
        first_step: int = cell_iteration * iters
        first_degree: int = cell_degrees[0] - first_step
        first_raw: int = degrees_to_midi(
            degrees=(first_degree,),
            tonic_midi=tonic_midi,
            mode=subject_mode,
        )[0]
        # Anchor: prefer prior running pitch, else range median
        anchor: int = prior_running_notes[-1].pitch if prior_running_notes else running_median
        common_shift: int = round((anchor - first_raw) / 12) * 12

        structural_knots: list[Knot] = []
        for r in range(iters):
            step_count: int = cell_iteration * iters + r
            transposed_degree: int = cell_degrees[0] - step_count

            raw_midi: int = degrees_to_midi(
                degrees=(transposed_degree,),
                tonic_midi=tonic_midi,
                mode=subject_mode,
            )[0]

            shifted: int = raw_midi + common_shift
            # Clamp to running range
            shifted = max(running_range.low, min(running_range.high, shifted))

            # Consonance-check against held pitch
            adjusted: int = _find_consonant_near(
                target_midi=shifted,
                held_pitch=held_pitch,
                range_low=running_range.low,
                range_high=running_range.high,
            )

            onset_beat: Fraction = bar_start_offset + r * cell_duration
            structural_knots.append(
                Knot(beat=float(onset_beat), midi_pitch=adjusted)
            )

        # End-of-bar knot: derive from last cell repetition's last degree
        last_r: int = iters - 1
        end_step: int = cell_iteration * iters + last_r
        end_degree: int = cell_degrees[-1] - end_step
        end_raw: int = degrees_to_midi(
            degrees=(end_degree,),
            tonic_midi=tonic_midi,
            mode=subject_mode,
        )[0]
        end_shifted: int = end_raw + common_shift
        end_shifted = max(running_range.low, min(running_range.high, end_shifted))
        end_adjusted: int = _find_consonant_near(
            target_midi=end_shifted,
            held_pitch=held_pitch,
            range_low=running_range.low,
            range_high=running_range.high,
        )
        structural_knots.append(
            Knot(beat=float(bar_end_offset), midi_pitch=end_adjusted)
        )
    else:
        # Fallback: original two-knot behaviour
        consonant_pitches: list[int] = [
            p for p in range(running_range.low, running_range.high + 1)
            if abs(p - held_pitch) % 12 not in STRONG_BEAT_DISSONANT
        ]
        assert len(consonant_pitches) > 0, "No consonant pitches in running voice range"

        candidate_start: int = prior_running_notes[-1].pitch if prior_running_notes else running_median
        if abs(candidate_start - held_pitch) % 12 in STRONG_BEAT_DISSONANT:
            start_pitch: int = min(consonant_pitches, key=lambda p: abs(p - candidate_start))
        else:
            start_pitch = candidate_start

        if abs(running_median - held_pitch) % 12 in STRONG_BEAT_DISSONANT:
            end_pitch: int = min(consonant_pitches, key=lambda p: abs(p - running_median))
        else:
            end_pitch = running_median

        structural_knots = [
            Knot(beat=float(bar_start_offset), midi_pitch=start_pitch),
            Knot(beat=float(bar_end_offset), midi_pitch=end_pitch),
        ]

    # Call generate_voice
    running_notes: tuple[Note, ...] = generate_voice(
        structural_knots=structural_knots,
        rhythm_grid=rhythm_grid,
        existing_voices=[held_voice],
        range_low=running_range.low,
        range_high=running_range.high,
        key=key_info,
        voice_id=running_track,
        beats_per_bar=float(bar_length),
        chord_pcs_per_beat=None,
    )

    return running_notes


def render_hold_entry(
    entry_first_bar: int,
    entry_bar_count: int,
    entry_start_offset: Fraction,
    voice0_role: ThematicRole,
    voice1_role: ThematicRole,
    beat_role_v0: BeatRole | None,
    beat_role_v1: BeatRole | None,
    fugue: LoadedFugue,
    bar_length: Fraction,
    beat_unit: Fraction,
    plan: "PhrasePlan",
    soprano_notes: tuple[Note, ...],
    bass_notes: tuple[Note, ...],
) -> tuple[tuple[Note, ...], tuple[Note, ...]]:
    """Render a HOLD entry: one voice holds, other runs bar-by-bar (B9).

    Args:
        entry_first_bar: First bar of this entry (1-based)
        entry_bar_count: Number of bars in this entry
        entry_start_offset: Absolute offset where this entry starts
        voice0_role: ThematicRole for voice 0
        voice1_role: ThematicRole for voice 1
        beat_role_v0: BeatRole for voice 0
        beat_role_v1: BeatRole for voice 1
        fugue: LoadedFugue for rhythm extraction
        bar_length: Length of one bar
        beat_unit: Beat unit for metre
        plan: PhrasePlan for ranges and keys
        soprano_notes: Accumulated soprano notes so far
        bass_notes: Accumulated bass notes so far

    Returns:
        Tuple of (soprano_notes, bass_notes) with HOLD entry added
    """
    soprano_holds: bool = voice0_role == ThematicRole.HOLD
    bass_holds: bool = voice1_role == ThematicRole.HOLD
    hold_beat_role: BeatRole | None = beat_role_v0 if soprano_holds else beat_role_v1

    assert hold_beat_role is not None, f"No BeatRole for hold voice at entry bar {entry_first_bar}"

    # Extract sixteenth cell from subject tail for rhythm
    sixteenth_cell = extract_sixteenth_cell(fugue=fugue, bar_length=bar_length)

    # Validate cell divides evenly into bar_length, else use regular semiquaver grid
    cell_total_duration: Fraction = sum(sixteenth_cell.durations) if sixteenth_cell.durations else Fraction(0)
    if cell_total_duration > 0 and bar_length % cell_total_duration == 0:
        # Repeat cell to fill entire bar
        iterations: int = int(bar_length / cell_total_duration)
        rhythm_durations: tuple[Fraction, ...] = sixteenth_cell.durations * iterations
    else:
        # Fallback: regular semiquaver grid for 4/4
        rhythm_durations = (Fraction(1, 16),) * 16

    # Validate rhythm fills exactly one bar
    assert sum(rhythm_durations) == bar_length, (
        f"Rhythm durations sum to {sum(rhythm_durations)}, expected {bar_length}"
    )

    # Cell data for subject-derived knots
    cell_degrees: tuple[int, ...] = sixteenth_cell.degrees
    subject_mode: str = fugue.subject.mode

    # Track running voice notes per bar for held-pitch exchange
    last_bar_running_notes: tuple[Note, ...] = ()

    # Generate bar-by-bar: held voice (whole note) + running voice (Viterbi)
    for bar_offset in range(entry_bar_count):
        bar_start_offset: Fraction = entry_start_offset + Fraction(bar_offset) * bar_length

        # Determine which voice holds in THIS bar (alternates)
        sop_holds_this_bar: bool = (bar_offset % 2 == 0 and soprano_holds) or (bar_offset % 2 == 1 and bass_holds)
        bass_holds_this_bar: bool = (bar_offset % 2 == 0 and bass_holds) or (bar_offset % 2 == 1 and soprano_holds)

        if bass_holds_this_bar:
            # Bass holds: pick held pitch
            if bar_offset == 0:
                # Bar 0: use previous pitch (existing logic)
                prev_bass_pitch: int = bass_notes[-1].pitch if bass_notes else plan.prev_exit_lower or plan.lower_median
            else:
                # Exchange bar: use last running voice's final pitch
                assert len(last_bar_running_notes) > 0, (
                    f"No running notes from previous bar at hold bar_offset={bar_offset}"
                )
                prev_bass_pitch = last_bar_running_notes[-1].pitch
                # Ensure consonance with running range median
                if abs(prev_bass_pitch - ((plan.upper_range.low + plan.upper_range.high) // 2)) % 12 in STRONG_BEAT_DISSONANT:
                    prev_bass_pitch = _find_consonant_near(
                        target_midi=prev_bass_pitch,
                        held_pitch=(plan.upper_range.low + plan.upper_range.high) // 2,
                        range_low=plan.lower_range.low,
                        range_high=plan.lower_range.high,
                    )

            bass_note: Note = Note(
                offset=bar_start_offset,
                pitch=prev_bass_pitch,
                duration=bar_length,
                voice=TRACK_BASS,
                lyric="hold" if bar_offset == 0 else "",
                creator="hold",
            )
            bass_notes = bass_notes + (bass_note,)

            # Soprano runs: generate via Viterbi against held bass
            sop_notes: tuple[Note, ...] = _generate_running_voice_bar(
                held_pitch=prev_bass_pitch,
                held_is_above=False,
                running_track=TRACK_SOPRANO,
                running_range=plan.upper_range,
                bar_start_offset=bar_start_offset,
                bar_length=bar_length,
                beat_unit=beat_unit,
                rhythm_durations=rhythm_durations,
                local_key=hold_beat_role.material_key,
                prior_running_notes=soprano_notes,
                prior_held_notes=bass_notes,
                cell_degrees=cell_degrees,
                cell_iteration=bar_offset,
                material_key=hold_beat_role.material_key,
                subject_mode=subject_mode,
            )
            soprano_notes = soprano_notes + sop_notes
            last_bar_running_notes = sop_notes
        else:
            # Soprano holds: pick held pitch
            if bar_offset == 0:
                # Bar 0: use previous pitch (existing logic)
                prev_sop_pitch: int = soprano_notes[-1].pitch if soprano_notes else plan.prev_exit_upper or plan.upper_median
            else:
                # Exchange bar: use last running voice's final pitch
                assert len(last_bar_running_notes) > 0, (
                    f"No running notes from previous bar at hold bar_offset={bar_offset}"
                )
                prev_sop_pitch = last_bar_running_notes[-1].pitch
                # Ensure consonance with running range median
                if abs(prev_sop_pitch - ((plan.lower_range.low + plan.lower_range.high) // 2)) % 12 in STRONG_BEAT_DISSONANT:
                    prev_sop_pitch = _find_consonant_near(
                        target_midi=prev_sop_pitch,
                        held_pitch=(plan.lower_range.low + plan.lower_range.high) // 2,
                        range_low=plan.upper_range.low,
                        range_high=plan.upper_range.high,
                    )

            sop_note: Note = Note(
                offset=bar_start_offset,
                pitch=prev_sop_pitch,
                duration=bar_length,
                voice=TRACK_SOPRANO,
                lyric="hold" if bar_offset == 0 else "",
                creator="hold",
            )
            soprano_notes = soprano_notes + (sop_note,)

            # Bass runs: generate via Viterbi against held soprano
            bass_result: tuple[Note, ...] = _generate_running_voice_bar(
                held_pitch=prev_sop_pitch,
                held_is_above=True,
                running_track=TRACK_BASS,
                running_range=plan.lower_range,
                bar_start_offset=bar_start_offset,
                bar_length=bar_length,
                beat_unit=beat_unit,
                rhythm_durations=rhythm_durations,
                local_key=hold_beat_role.material_key,
                prior_running_notes=bass_notes,
                prior_held_notes=soprano_notes,
                cell_degrees=cell_degrees,
                cell_iteration=bar_offset,
                material_key=hold_beat_role.material_key,
                subject_mode=subject_mode,
            )
            bass_notes = bass_notes + bass_result
            last_bar_running_notes = bass_result

    # Trace first bar only
    if soprano_notes or bass_notes:
        tracer = get_tracer()
        if soprano_holds:
            hold_voice_notes = [n for n in soprano_notes if n.offset >= entry_start_offset and n.offset < entry_start_offset + bar_length]
            run_voice_notes = [n for n in bass_notes if n.offset >= entry_start_offset and n.offset < entry_start_offset + bar_length]
            if hold_voice_notes:
                note_pitches = [n.pitch for n in hold_voice_notes]
                tracer.trace_thematic_render(
                    bar=entry_first_bar,
                    voice_name="U",
                    role_name="HOLD",
                    key_str=_key_str(key=hold_beat_role.material_key),
                    note_count=len(hold_voice_notes),
                    low_pitch=min(note_pitches),
                    high_pitch=max(note_pitches),
                )
            if run_voice_notes:
                note_pitches = [n.pitch for n in run_voice_notes]
                tracer.trace_thematic_render(
                    bar=entry_first_bar,
                    voice_name="L",
                    role_name="FREE",
                    key_str=_key_str(key=hold_beat_role.material_key),
                    note_count=len(run_voice_notes),
                    low_pitch=min(note_pitches),
                    high_pitch=max(note_pitches),
                )
        else:
            hold_voice_notes = [n for n in bass_notes if n.offset >= entry_start_offset and n.offset < entry_start_offset + bar_length]
            run_voice_notes = [n for n in soprano_notes if n.offset >= entry_start_offset and n.offset < entry_start_offset + bar_length]
            if hold_voice_notes:
                note_pitches = [n.pitch for n in hold_voice_notes]
                tracer.trace_thematic_render(
                    bar=entry_first_bar,
                    voice_name="L",
                    role_name="HOLD",
                    key_str=_key_str(key=hold_beat_role.material_key),
                    note_count=len(hold_voice_notes),
                    low_pitch=min(note_pitches),
                    high_pitch=max(note_pitches),
                )
            if run_voice_notes:
                note_pitches = [n.pitch for n in run_voice_notes]
                tracer.trace_thematic_render(
                    bar=entry_first_bar,
                    voice_name="U",
                    role_name="FREE",
                    key_str=_key_str(key=hold_beat_role.material_key),
                    note_count=len(run_voice_notes),
                    low_pitch=min(note_pitches),
                    high_pitch=max(note_pitches),
                )

    return (soprano_notes, bass_notes)
