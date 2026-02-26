"""Bass Viterbi: walking-bass generation via Viterbi pathfinding against soprano."""
import logging
from fractions import Fraction

from builder.knot_builder import ensure_final_knot, sort_and_dedup_knots
from builder.galant.bass_writer import validate_bass_notes
from builder.voice_types import VoiceBias
from builder.phrase_types import (
    PhrasePlan,
    phrase_bar_duration,
    phrase_bar_start,
    phrase_degree_offset,
    phrase_offset_to_bar,
)
from builder.rhythm_cells import select_cell
from builder.types import Note
from shared.constants import STRONG_BEAT_DISSONANT, TRACK_BASS
from shared.music_math import parse_metre
from shared.pitch import degree_to_nearest_midi
from viterbi.generate import generate_voice
from viterbi.mtypes import ExistingVoice, Knot
from viterbi.scale import KeyInfo, triad_pcs as viterbi_triad_pcs

logger = logging.getLogger(__name__)


def _soprano_at(
    soprano_notes: tuple[Note, ...],
    offset: Fraction,
) -> int | None:
    """Return soprano MIDI pitch sounding at offset (sustain lookup)."""
    for note in soprano_notes:
        if note.offset <= offset < note.offset + note.duration:
            return note.pitch
    return None


def generate_bass_viterbi(
    plan: PhrasePlan,
    soprano_notes: tuple[Note, ...],
    prior_lower: tuple[Note, ...] = (),
    harmonic_grid: "HarmonicGrid | None" = None,
    density_override: str | None = None,
    bias: VoiceBias | None = None,
) -> tuple[Note, ...]:
    """Generate walking bass via Viterbi pathfinding against soprano.

    Soprano is the leader; bass is the follower.  Structural bass knots
    (schema degrees) are pinned; between them the solver finds the
    optimal diatonic bass line minimising counterpoint cost.

    Args:
        density_override: Optional density level ("high", "medium", "low") that
            biases rhythm cell selection toward appropriate note counts.
            Used in B1 to reduce companion voice density alongside thematic material.
    """
    assert not plan.is_cadential, (
        f"generate_bass_viterbi called with cadential plan '{plan.schema_name}'"
    )

    bar_length: Fraction
    beat_unit: Fraction
    bar_length, beat_unit = parse_metre(metre=plan.metre)
    prev_exit_midi: int | None = prior_lower[-1].pitch if prior_lower else None
    phrase_end: Fraction = plan.start_offset + plan.phrase_duration

    # ================================================================
    # Step 1 — Place structural bass knots
    # ================================================================
    knots: list[Knot]
    structural_knots_override: list[Knot] | None = bias.structural_knots if bias else None
    if structural_knots_override is not None:
        knots = list(structural_knots_override)
    else:
        knots = []
        prev_midi: int = prev_exit_midi if prev_exit_midi is not None else plan.lower_median

        for i, degree in enumerate(plan.degrees_lower):
            pos = plan.degree_positions[i]
            offset: Fraction = phrase_degree_offset(
                plan=plan, pos=pos, bar_length=bar_length, beat_unit=beat_unit,
            )
            key_for_degree = plan.degree_keys[i]
            bass_midi: int = degree_to_nearest_midi(
                degree=degree,
                key=key_for_degree,
                target_midi=prev_midi,
                midi_range=(plan.lower_range.low, plan.lower_range.high),
            )

            # Consonance check against soprano at this offset
            sop_at: int | None = _soprano_at(
                soprano_notes=soprano_notes, offset=offset,
            )
            if sop_at is not None:
                if abs(bass_midi - sop_at) % 12 in STRONG_BEAT_DISSONANT:
                    alternatives: list[int] = [
                        alt for alt in (bass_midi - 12, bass_midi + 12)
                        if (plan.lower_range.low <= alt <= plan.lower_range.high
                            and alt <= sop_at
                            and abs(alt - sop_at) % 12 not in STRONG_BEAT_DISSONANT)
                    ]
                    if alternatives:
                        bass_midi = min(alternatives, key=lambda m: abs(m - prev_midi))
                # L004: bass must not cross soprano
                if bass_midi > sop_at:
                    alt_low: int = bass_midi - 12
                    if plan.lower_range.low <= alt_low:
                        bass_midi = alt_low

            knots.append(Knot(beat=float(offset), midi_pitch=bass_midi))
            prev_midi = bass_midi

    # Final knot at phrase_end (same pattern as soprano Viterbi)
    final_midi: int = knots[-1].midi_pitch if knots else plan.lower_median
    ensure_final_knot(knots, float(phrase_end), final_midi)

    # ================================================================
    # Step 2 — Build rhythm grid via select_cell (bar-by-bar)
    # ================================================================

    # Bar-relative structural offsets → required_onsets for select_cell
    struct_offsets_by_bar: dict[int, set[Fraction]] = {}
    for i in range(len(plan.degrees_lower)):
        pos = plan.degree_positions[i]
        off: Fraction = phrase_degree_offset(
            plan=plan, pos=pos, bar_length=bar_length, beat_unit=beat_unit,
        )
        bn: int = phrase_offset_to_bar(
            plan=plan, offset=off, bar_length=bar_length,
        )
        bs: Fraction = phrase_bar_start(
            plan=plan, bar_num=bn, bar_length=bar_length,
        )
        struct_offsets_by_bar.setdefault(bn, set()).add(off - bs)
    bar_struct_fsets: dict[int, frozenset[Fraction]] = {
        k: frozenset(v) for k, v in struct_offsets_by_bar.items()
    }

    # Bar-relative soprano onsets → avoid_onsets for complementary rhythm
    sop_onsets_by_bar: dict[int, set[Fraction]] = {}
    for sn in soprano_notes:
        if plan.start_offset <= sn.offset < phrase_end:
            sb: int = phrase_offset_to_bar(
                plan=plan, offset=sn.offset, bar_length=bar_length,
            )
            ss: Fraction = phrase_bar_start(
                plan=plan, bar_num=sb, bar_length=bar_length,
            )
            sop_onsets_by_bar.setdefault(sb, set()).add(sn.offset - ss)
    sop_onset_fsets: dict[int, frozenset[Fraction]] = {
        k: frozenset(v) for k, v in sop_onsets_by_bar.items()
    }

    grid_positions: list[tuple[Fraction, Fraction]] = []  # (onset, duration)
    prev_cell_name: str | None = None

    for bar_num in range(1, plan.bar_span + 1):
        bar_start: Fraction = phrase_bar_start(
            plan=plan, bar_num=bar_num, bar_length=bar_length,
        )
        bar_dur: Fraction = phrase_bar_duration(
            plan=plan, bar_num=bar_num, bar_length=bar_length,
        )
        is_final: bool = bar_num == plan.bar_span
        prefer: str = "cadential" if is_final else "plain"

        # Anacrusis bar: single note for the partial duration
        if bar_dur < bar_length:
            grid_positions.append((bar_start, bar_dur))
            prev_cell_name = None
            continue

        cell = select_cell(
            genre=plan.rhythm_profile,
            metre=plan.metre,
            bar_index=bar_num - 1,
            prefer_character=prefer,
            avoid_name=prev_cell_name,
            required_onsets=bar_struct_fsets.get(bar_num),
            avoid_onsets=sop_onset_fsets.get(bar_num),
            prefer_density=density_override,
        )
        note_offset: Fraction = bar_start
        for dur in cell.durations:
            grid_positions.append((note_offset, dur))
            note_offset += dur
        prev_cell_name = cell.name

    assert len(grid_positions) > 0, "Empty rhythm grid for bass Viterbi"

    # Final marker so last knot aligns with last grid position
    if abs(float(grid_positions[-1][0] - phrase_end)) > 1e-6:
        grid_positions.append((phrase_end, Fraction(-1)))

    # Ensure first knot aligns with first grid position
    first_beat: float = float(grid_positions[0][0])
    if abs(knots[0].beat - first_beat) > 1e-6:
        start_midi: int = prev_exit_midi if prev_exit_midi is not None else plan.lower_median
        knots.insert(0, Knot(beat=first_beat, midi_pitch=start_midi))
    # Sort by beat and deduplicate (thematic overrides + alignment knots may overlap)
    knots = sort_and_dedup_knots(knots)

    # ================================================================
    # Step 3 — Build soprano ExistingVoice at each grid position
    # ================================================================
    beat_grid: list[float] = [float(onset) for onset, _ in grid_positions]
    soprano_pitches_at_beat: dict[float, int] = {}
    prev_sop: int | None = None
    for onset, _ in grid_positions:
        sp: int | None = _soprano_at(
            soprano_notes=soprano_notes, offset=onset,
        )
        if sp is None:
            assert prev_sop is not None, (
                f"No soprano at bass grid offset {onset} and no previous to sustain"
            )
            sp = prev_sop
        soprano_pitches_at_beat[float(onset)] = sp
        prev_sop = sp
    soprano_voice: ExistingVoice = ExistingVoice(
        pitches_at_beat=soprano_pitches_at_beat,
        is_above=True,
    )

    # ================================================================
    # Step 4 — Generate voice via Viterbi
    # ================================================================
    pitch_classes: frozenset[int] = (
        plan.local_key.cadential_pitch_class_set
        if plan.cadential_approach
        else plan.local_key.pitch_class_set
    )
    key_info: KeyInfo = KeyInfo(
        pitch_class_set=pitch_classes,
        tonic_pc=plan.local_key.degree_to_midi(degree=1, octave=0) % 12,
    )

    # HRL-2: Build chord awareness from harmonic grid or surface soprano
    chord_pcs: list[frozenset[int]] | None = None
    if harmonic_grid is not None:
        chord_pcs = harmonic_grid.to_beat_list(beat_grid)
    else:
        # Surface inference: derive triads from soprano pitches at each
        # grid position.  Root-position assumption — imprecise when the
        # soprano is on the 3rd or 5th of the actual chord, but still
        # constrains toward consonant intervals.  Skip non-diatonic
        # soprano pitches (chromatic approach tones, raised leading
        # tones) to avoid triad_pcs assertion failure.
        chord_pcs = []
        for beat_f in beat_grid:
            sop_midi: int = soprano_pitches_at_beat[beat_f]
            sop_pc: int = sop_midi % 12
            if sop_pc in key_info.pitch_class_set:
                chord_pcs.append(viterbi_triad_pcs(
                    bass_midi=sop_midi,
                    key=key_info,
                ))
            else:
                chord_pcs.append(frozenset())

    notes_tuple = generate_voice(
        structural_knots=knots,
        rhythm_grid=grid_positions,
        existing_voices=[soprano_voice],
        range_low=plan.lower_range.low,
        range_high=plan.lower_range.high,
        key=key_info,
        voice_id=TRACK_BASS,
        beats_per_bar=float(bar_length),
        chord_pcs_per_beat=chord_pcs,
        degree_affinity=bias.degree_affinity if bias else None,
        interval_affinity=bias.interval_affinity if bias else None,
        genome_entries=bias.vertical_genome.entries if bias and bias.vertical_genome else None,
    )

    # ================================================================
    # Step 5 — Validate
    # ================================================================
    validate_bass_notes(notes=list(notes_tuple), plan=plan, soprano_notes=soprano_notes)

    return notes_tuple
