"""Soprano Viterbi surface generation (shared solver, used by galant and thematic paths)."""
import logging
from fractions import Fraction

from builder.figuration.rhythm_calc import compute_rhythmic_distribution
from builder.figuration.soprano import character_to_density
from builder.phrase_types import (
    PhrasePlan,
    phrase_bar_duration,
    phrase_bar_start,
    phrase_degree_offset,
    phrase_offset_to_bar,
)
from builder.rhythm_cells import select_cell
from builder.types import Note
from builder.voice_types import VoiceConfig
from builder.voice_writer import validate_voice, audit_voice
from shared.constants import MIN_SOPRANO_MIDI, TRACK_SOPRANO, TRACK_BASS
from shared.key import Key
from shared.music_math import parse_metre
from shared.pitch import degree_to_nearest_midi
from viterbi.generate import generate_voice
from viterbi.mtypes import ContourShape, ExistingVoice, Knot
from viterbi.scale import KeyInfo, triad_pcs as viterbi_triad_pcs

logger = logging.getLogger(__name__)


def place_structural_tones(
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


def generate_soprano_viterbi(
    plan: PhrasePlan,
    bass_notes: tuple[Note, ...],
    prior_upper: tuple[Note, ...] = (),
    next_phrase_entry_degree: int | None = None,
    next_phrase_entry_key: Key | None = None,
    harmonic_grid: "HarmonicGrid | None" = None,
    density_override: str | None = None,
    contour: ContourShape | None = None,
    avoid_onsets_by_bar: dict[int, frozenset[Fraction]] | None = None,
) -> tuple[tuple[Note, ...], tuple[str, ...]]:
    """Generate soprano notes using Viterbi pathfinding against finished bass.

    Args:
        density_override: Optional density level ("high", "medium", "low") that
            overrides character_to_density(plan.character) for rhythm grid.
            Used in B1 to reduce companion voice density alongside thematic material.

    Returns (notes, figure_names) where figure_names is empty (Viterbi doesn't
    use diminution figures).
    """
    # Step 1: Place structural tones and convert to Knots
    prev_exit_midi: int | None = prior_upper[-1].pitch if prior_upper else None
    structural_tones: list[tuple[Fraction, int, Key]] = place_structural_tones(
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
    density: str = density_override if density_override is not None else character_to_density(plan.character)
    grid_positions: list[tuple[Fraction, Fraction]] = []  # (onset, duration) pairs

    if avoid_onsets_by_bar is not None:
        # I5: Bar-by-bar rhythm via select_cell for rhythmic independence
        # Compute bar-relative structural soprano offsets (required_onsets)
        struct_offsets_by_bar: dict[int, set[Fraction]] = {}
        for st_offset, _, _ in structural_tones:
            bn: int = phrase_offset_to_bar(
                plan=plan, offset=st_offset, bar_length=bar_length,
            )
            bs: Fraction = phrase_bar_start(
                plan=plan, bar_num=bn, bar_length=bar_length,
            )
            struct_offsets_by_bar.setdefault(bn, set()).add(st_offset - bs)
        bar_struct_fsets: dict[int, frozenset[Fraction]] = {
            k: frozenset(v) for k, v in struct_offsets_by_bar.items()
        }

        prev_cell_name: str | None = None
        for bar_num in range(1, plan.bar_span + 1):
            bar_start: Fraction = phrase_bar_start(
                plan=plan, bar_num=bar_num, bar_length=bar_length,
            )
            bar_dur: Fraction = phrase_bar_duration(
                plan=plan, bar_num=bar_num, bar_length=bar_length,
            )
            # Anacrusis bar: single note for the partial duration
            if bar_dur < bar_length:
                grid_positions.append((bar_start, bar_dur))
                prev_cell_name = None
                continue

            cell = select_cell(
                genre=plan.rhythm_profile,
                metre=plan.metre,
                bar_index=bar_num - 1,
                avoid_onsets=avoid_onsets_by_bar.get(bar_num),
                prefer_density=density,
                avoid_name=prev_cell_name,
                required_onsets=bar_struct_fsets.get(bar_num),
            )
            note_offset: Fraction = bar_start
            for dur in cell.durations:
                grid_positions.append((note_offset, dur))
                note_offset += dur
            prev_cell_name = cell.name
    else:
        # Original path: compute_rhythmic_distribution per structural span
        for i in range(len(structural_tones)):
            span_start: Fraction = structural_tones[i][0]
            if i < len(structural_tones) - 1:
                span_end: Fraction = structural_tones[i + 1][0]
            else:
                span_end = plan.start_offset + plan.phrase_duration
            gap: Fraction = span_end - span_start
            note_count, note_duration = compute_rhythmic_distribution(gap=gap, density=density)
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

    # Step 3: Build bass ExistingVoice at each grid position
    beat_grid: list[float] = [float(onset) for onset, _ in grid_positions]
    bass_pitches_at_beat: dict[float, int] = {}
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
        bass_pitches_at_beat[float(onset)] = bass_pitch
        prev_bass_pitch = bass_pitch
    bass_voice: ExistingVoice = ExistingVoice(
        pitches_at_beat=bass_pitches_at_beat,
        is_above=False,
    )

    # Step 4: Build KeyInfo from plan.local_key
    tonic_pc: int = plan.local_key.degree_to_midi(degree=1, octave=0) % 12
    pitch_classes: frozenset[int] = (
        plan.local_key.cadential_pitch_class_set
        if plan.cadential_approach
        else plan.local_key.pitch_class_set
    )
    key_info: KeyInfo = KeyInfo(
        pitch_class_set=pitch_classes,
        tonic_pc=tonic_pc,
    )

    # Step 4b: Build chord grid from harmonic grid or fallback to H3
    chord_pcs_per_beat: list[frozenset[int]]
    if harmonic_grid is not None:
        # HRL-2: Use schema-annotated Roman numerals (primary path)
        chord_pcs_per_beat = harmonic_grid.to_beat_list(beat_grid)
    else:
        # H3 fallback: derive chord from surface bass (deprecated path)
        if plan.thematic_roles is None and contour is None:
            logger.warning("No harmonic grid for schematic phrase '%s'; falling back to surface inference", plan.schema_name)
        assert len(plan.degrees_lower) == len(plan.degree_positions), (
            f"degrees_lower ({len(plan.degrees_lower)}) and degree_positions "
            f"({len(plan.degree_positions)}) length mismatch"
        )
        bass_degree_offsets: list[tuple[Fraction, int, Key]] = []
        for i, degree in enumerate(plan.degrees_lower):
            pos = plan.degree_positions[i]
            offset: Fraction = phrase_degree_offset(
                plan=plan, pos=pos, bar_length=bar_length, beat_unit=beat_unit,
            )
            key_for_deg: Key = plan.degree_keys[i]
            bass_midi_for_chord: int = key_for_deg.degree_to_midi(
                degree=degree,
                octave=0,
            )
            bass_degree_offsets.append((offset, bass_midi_for_chord, key_for_deg))

        # Pre-build KeyInfo + fallback triad for each schema degree position
        degree_key_infos: list[KeyInfo] = []
        degree_triads: list[frozenset[int]] = []
        for _, bass_midi, deg_key in bass_degree_offsets:
            deg_pitch_classes: frozenset[int] = (
                deg_key.cadential_pitch_class_set
                if plan.cadential_approach
                else deg_key.pitch_class_set
            )
            deg_key_info: KeyInfo = KeyInfo(
                pitch_class_set=deg_pitch_classes,
                tonic_pc=deg_key.degree_to_midi(degree=1, octave=0) % 12,
            )
            degree_key_infos.append(deg_key_info)
            degree_triads.append(viterbi_triad_pcs(bass_midi=bass_midi, key=deg_key_info))

        # H3: derive chord from surface bass at each grid position.
        # If surface bass is diatonic in the active key, build a triad from it
        # (per-beat harmonic awareness). Otherwise fall back to the most recent
        # schema degree's triad (H2 behaviour).
        chord_pcs_per_beat = []
        for i, (grid_onset, _) in enumerate(grid_positions):
            # Find most recent schema degree index
            active_idx: int = 0
            for j in range(len(bass_degree_offsets) - 1, -1, -1):
                if bass_degree_offsets[j][0] <= grid_onset:
                    active_idx = j
                    break
            fallback_chord: frozenset[int] = degree_triads[active_idx] if degree_triads else frozenset()
            active_key: KeyInfo = degree_key_infos[active_idx] if degree_key_infos else key_info
            # Surface bass triad if diatonic, else schema degree fallback
            surface_bass_midi: int = bass_pitches_at_beat[beat_grid[i]]
            surface_bass_pc: int = surface_bass_midi % 12
            if surface_bass_pc in active_key.pitch_class_set:
                chord_pcs_per_beat.append(viterbi_triad_pcs(bass_midi=surface_bass_midi, key=active_key))
            else:
                chord_pcs_per_beat.append(fallback_chord)

    # Step 5: Generate voice via Viterbi
    notes_tuple = generate_voice(
        structural_knots=knots,
        rhythm_grid=grid_positions,
        existing_voices=[bass_voice],
        range_low=plan.upper_range.low,
        range_high=plan.upper_range.high,
        key=key_info,
        voice_id=TRACK_SOPRANO,
        beats_per_bar=float(bar_length),
        chord_pcs_per_beat=chord_pcs_per_beat,
        contour=contour,
    )

    # Step 6: Validate and audit
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
        notes=notes_tuple,
        config=voice_config,
        phrase_start=plan.start_offset,
        phrase_duration=plan.phrase_duration,
    )

    # Audit (counterpoint style, strict=False so violations are logged not asserted)
    structural_offsets: frozenset[Fraction] = frozenset(st[0] for st in structural_tones)
    prior_phrase_tail: Note | None = prior_upper[-1] if prior_upper else None
    violations = audit_voice(
        notes=notes_tuple,
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
    return notes_tuple, ()
