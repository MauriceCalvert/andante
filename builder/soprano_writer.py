"""Soprano phrase generation and validation."""
import logging
from fractions import Fraction

from builder.figuration.rhythm_calc import compute_rhythmic_distribution
from builder.figuration.soprano import character_to_density
from builder.phrase_types import PhrasePlan, phrase_degree_offset
from builder.strategies.diminution import DiminutionFill
from builder.types import Note
from builder.voice_types import DiminutionMetadata, StructuralTone, VoiceConfig, WriteResult
from builder.voice_writer import validate_voice, audit_voice, write_voice
from shared.constants import MIN_SOPRANO_MIDI, TRACK_SOPRANO, TRACK_BASS, VALID_DURATIONS_SET
from shared.key import Key
from shared.music_math import parse_metre
from shared.pitch import degree_to_nearest_midi
from viterbi.mtypes import Knot, LeaderNote
from viterbi.pipeline import solve_phrase
from viterbi.scale import KeyInfo

logger = logging.getLogger(__name__)


def build_structural_soprano(
    plan: PhrasePlan,
    prev_exit_midi: int | None,
) -> tuple[Note, ...]:
    """Build structural soprano skeleton (held notes at schema arrival positions).

    Returns one Note per structural tone, each held until the next structural
    tone (or phrase end for the final tone). Bass writer checks against this
    coarse skeleton; Viterbi soprano generation replaces it with full surface.
    """
    structural_tones: list[tuple[Fraction, int, Key]] = _place_structural_tones(
        plan=plan, prev_exit_midi=prev_exit_midi,
    )
    bar_length, beat_unit = parse_metre(metre=plan.metre)
    notes: list[Note] = []
    for i, (offset, midi, key) in enumerate(structural_tones):
        # Duration: until next structural tone, or phrase end for final tone
        if i < len(structural_tones) - 1:
            next_offset: Fraction = structural_tones[i + 1][0]
            duration: Fraction = next_offset - offset
        else:
            phrase_end: Fraction = plan.start_offset + plan.phrase_duration
            duration = phrase_end - offset
        notes.append(Note(
            offset=offset,
            pitch=midi,
            duration=duration,
            voice=TRACK_SOPRANO,
        ))
    return tuple(notes)


def _place_structural_tones(
    plan: PhrasePlan,
    prev_exit_midi: int | None,
) -> list[tuple[Fraction, int, Key]]:
    """Place structural tones with octave selection and floor clamp.

    Returns list of (offset, midi, key) triples.
    """
    bar_length, beat_unit = parse_metre(metre=plan.metre)
    structural_tones: list[tuple[Fraction, int, Key]] = []
    biased_upper_median: int = plan.upper_median + plan.registral_bias
    prev_midi: int = (
        prev_exit_midi if prev_exit_midi is not None
        else biased_upper_median
    )
    actual_prev: int | None = prev_exit_midi
    prev_prev: int | None = None
    for i, degree in enumerate(plan.degrees_upper):
        pos = plan.degree_positions[i]
        offset: Fraction = phrase_degree_offset(
            plan=plan, pos=pos, bar_length=bar_length, beat_unit=beat_unit,
        )
        key_for_degree: Key = plan.degree_keys[i]
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
        structural_tones.append((offset, midi, key_for_degree))
        prev_prev = actual_prev
        actual_prev = midi
        prev_midi = midi
    return structural_tones


def generate_soprano_phrase(
    plan: PhrasePlan,
    prior_upper: tuple[Note, ...] = (),
    lower_notes: tuple[Note, ...] = (),
    next_phrase_entry_degree: int | None = None,
    next_phrase_entry_key: Key | None = None,
    recall_figure_name: str | None = None,
) -> tuple[tuple[Note, ...], tuple[str, ...]]:
    """Generate soprano notes for one phrase.

    Returns (notes, figure_names) where figure_names lists the figuration
    patterns used for each span between structural tones.
    """
    assert not plan.is_cadential, (
        f"generate_soprano_phrase called with cadential plan '{plan.schema_name}'; "
        f"use write_phrase() which delegates to write_cadence()"
    )

    # Step 1: Place structural tones
    prev_exit_midi: int | None = prior_upper[-1].pitch if prior_upper else None
    structural_tones: list[tuple[Fraction, int, Key]] = _place_structural_tones(
        plan=plan, prev_exit_midi=prev_exit_midi,
    )

    # Step 2: Compute phrase exit target
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

    # Convert structural tones to StructuralTone objects
    structural_tone_objects: tuple[StructuralTone, ...] = tuple(
        StructuralTone(offset=st[0], midi=st[1], key=st[2])
        for st in structural_tones
    )

    # Build VoiceConfig
    bar_length, beat_unit = parse_metre(metre=plan.metre)
    voice_config: VoiceConfig = VoiceConfig(
        voice_id=TRACK_SOPRANO,
        range_low=plan.upper_range.low,
        range_high=plan.upper_range.high,
        key=plan.local_key,
        metre=plan.metre,
        bar_length=bar_length,
        beat_unit=beat_unit,
        phrase_start=plan.start_offset,
        genre=plan.rhythm_profile,
        character=plan.character,
        is_minor=plan.degree_keys[0].mode == "minor",
        guard_tolerance=frozenset(),
        cadence_type=plan.cadence_type,
    )

    # Build other_voices dict
    other_voices: dict[int, tuple[Note, ...]] = {}
    if lower_notes:
        other_voices[TRACK_BASS] = lower_notes

    # Build strategy
    strategy: DiminutionFill = DiminutionFill(
        character=plan.character,
        recall_figure_name=recall_figure_name,
    )

    # Prior phrase tail for boundary checking
    prior_phrase_tail: Note | None = prior_upper[-1] if prior_upper else None

    # Call write_voice
    result: WriteResult = write_voice(
        structural_tones=structural_tone_objects,
        phrase_start=plan.start_offset,
        phrase_duration=plan.phrase_duration,
        fill_strategy=strategy,
        other_voices=other_voices,
        config=voice_config,
        next_entry_midi=next_entry_midi,
        prior_phrase_tail=prior_phrase_tail,
        strict_audit=False,
    )

    # Log any audit violations
    for violation in result.audit_violations:
        logger.warning("soprano audit: %s at offset %s", violation.detail, violation.offset)

    # Extract figure names from span metadata
    figure_names: list[str] = [
        m.figure_name
        for m in result.span_metadata
        if isinstance(m, DiminutionMetadata)
    ]

    return result.notes, tuple(figure_names)


def generate_soprano_viterbi(
    plan: PhrasePlan,
    bass_notes: tuple[Note, ...],
    prior_upper: tuple[Note, ...] = (),
    next_phrase_entry_degree: int | None = None,
    next_phrase_entry_key: Key | None = None,
) -> tuple[tuple[Note, ...], tuple[str, ...]]:
    """Generate soprano notes using Viterbi pathfinding against finished bass.

    Returns (notes, figure_names) where figure_names is empty (Viterbi doesn't
    use diminution figures).
    """
    # Step 1: Place structural tones and convert to Knots
    prev_exit_midi: int | None = prior_upper[-1].pitch if prior_upper else None
    structural_tones: list[tuple[Fraction, int, Key]] = _place_structural_tones(
        plan=plan, prev_exit_midi=prev_exit_midi,
    )
    knots: list[Knot] = [
        Knot(beat=float(offset), midi_pitch=midi)
        for offset, midi, _ in structural_tones
    ]

    # Compute final knot pitch: use next_phrase_entry if provided, else last structural tone
    final_offset: Fraction = plan.start_offset + plan.phrase_duration
    if next_phrase_entry_degree is not None and next_phrase_entry_key is not None:
        final_midi: int = degree_to_nearest_midi(
            degree=next_phrase_entry_degree,
            key=next_phrase_entry_key,
            target_midi=structural_tones[-1][1] if structural_tones else prev_exit_midi or plan.upper_median,
            midi_range=(plan.upper_range.low, plan.upper_range.high),
        )
    else:
        final_midi = structural_tones[-1][1] if structural_tones else prev_exit_midi or plan.upper_median

    # Add final knot at phrase_end (required by Viterbi solver)
    if len(knots) == 0 or abs(float(final_offset) - knots[-1].beat) > 1e-6:
        knots.append(Knot(beat=float(final_offset), midi_pitch=final_midi))

    # Step 2: Build rhythm grid (onset positions with durations)
    bar_length, beat_unit = parse_metre(metre=plan.metre)
    density: str = character_to_density(plan.character)
    grid_positions: list[tuple[Fraction, Fraction]] = []  # (onset, duration) pairs

    for i in range(len(structural_tones)):
        span_start: Fraction = structural_tones[i][0]
        if i < len(structural_tones) - 1:
            span_end: Fraction = structural_tones[i + 1][0]
        else:
            span_end = plan.start_offset + plan.phrase_duration
        gap: Fraction = span_end - span_start
        note_count, note_duration = compute_rhythmic_distribution(gap=gap, density=density)
        # Generate onset positions for this span
        for j in range(note_count):
            onset: Fraction = span_start + j * note_duration
            grid_positions.append((onset, note_duration))

    # Deduplicate positions (structural tones appear as both span end and span start)
    seen_onsets: set[Fraction] = set()
    unique_grid: list[tuple[Fraction, Fraction]] = []
    for onset, dur in grid_positions:
        if onset not in seen_onsets:
            unique_grid.append((onset, dur))
            seen_onsets.add(onset)
    grid_positions = sorted(unique_grid, key=lambda x: x[0])

    # The last knot must align with the last grid position (Viterbi requirement)
    # If last onset < phrase_end, add phrase_end as final grid position with marker duration
    if len(grid_positions) > 0:
        last_onset = grid_positions[-1][0]
        if abs(float(last_onset - final_offset)) > 1e-6:
            # Add phrase_end as final onset; use NEGATIVE duration as marker (will extend previous note)
            grid_positions.append((final_offset, Fraction(-1)))

    # Step 3: Extract leader surface (bass notes at each grid position)
    leader_notes: list[LeaderNote] = []
    prev_bass_pitch: int | None = None
    for onset, _ in grid_positions:
        # Find bass note sounding at this onset
        bass_pitch: int | None = None
        for bn in bass_notes:
            if bn.offset <= onset < bn.offset + bn.duration:
                bass_pitch = bn.pitch
                break
        # If no bass note at this position, sustain previous
        if bass_pitch is None:
            assert prev_bass_pitch is not None, (
                f"No bass note at grid position {onset} and no previous bass to sustain"
            )
            bass_pitch = prev_bass_pitch
        leader_notes.append(LeaderNote(beat=float(onset), midi_pitch=bass_pitch))
        prev_bass_pitch = bass_pitch

    # Step 4: Build KeyInfo from plan.local_key
    tonic_pc: int = plan.local_key.degree_to_midi(degree=1, octave=0) % 12
    key_info: KeyInfo = KeyInfo(
        pitch_class_set=plan.local_key.pitch_class_set,
        tonic_pc=tonic_pc,
    )

    # Step 5: Run Viterbi solver
    result = solve_phrase(
        leader_notes=leader_notes,
        follower_knots=knots,
        follower_low=plan.upper_range.low,
        follower_high=plan.upper_range.high,
        verbose=False,
        key=key_info,
    )

    # Step 6: Convert solver output to Notes
    notes: list[Note] = []
    for i, ((onset, dur), pitch) in enumerate(zip(grid_positions, result.pitches)):
        # Handle final marker (duration < 0): extend previous note instead of creating new one
        if dur < 0:
            # This is the final endpoint marker; extend the previous note to phrase_end
            if len(notes) > 0:
                prev_note = notes[-1]
                extended_dur: Fraction = onset - prev_note.offset
                notes[-1] = Note(
                    offset=prev_note.offset,
                    pitch=prev_note.pitch,
                    duration=extended_dur,
                    voice=TRACK_SOPRANO,
                )
            # Don't create a new note for the marker
            continue
        notes.append(Note(
            offset=onset,
            pitch=pitch,
            duration=dur,
            voice=TRACK_SOPRANO,
        ))

    # Step 7: Validate and audit
    # Build VoiceConfig (same pattern as generate_soprano_phrase)
    voice_config: VoiceConfig = VoiceConfig(
        voice_id=TRACK_SOPRANO,
        range_low=plan.upper_range.low,
        range_high=plan.upper_range.high,
        key=plan.local_key,
        metre=plan.metre,
        bar_length=bar_length,
        beat_unit=beat_unit,
        phrase_start=plan.start_offset,
        genre=plan.rhythm_profile,
        character=plan.character,
        is_minor=plan.degree_keys[0].mode == "minor" if plan.degree_keys else plan.local_key.mode == "minor",
        guard_tolerance=frozenset(),
        cadence_type=plan.cadence_type,
    )

    # Build other_voices dict
    other_voices: dict[int, tuple[Note, ...]] = {TRACK_BASS: bass_notes}

    # Validate (hard invariants)
    validate_voice(
        notes=tuple(notes),
        config=voice_config,
        phrase_start=plan.start_offset,
        phrase_duration=plan.phrase_duration,
    )

    # Audit (counterpoint style, strict=False so violations are logged not asserted)
    structural_offsets: frozenset[Fraction] = frozenset(st[0] for st in structural_tones)
    prior_phrase_tail: Note | None = prior_upper[-1] if prior_upper else None
    violations = audit_voice(
        notes=tuple(notes),
        other_voices=other_voices,
        structural_offsets=structural_offsets,
        config=voice_config,
        prior_phrase_tail=prior_phrase_tail,
        strict=False,
    )

    # Log violations
    for v in violations:
        logger.warning("viterbi soprano audit: %s at offset %s", v.detail, v.offset)

    # Return (notes, empty figure_names)
    return tuple(notes), ()
