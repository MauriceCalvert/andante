"""Bass Viterbi: walking-bass generation via Viterbi pathfinding against soprano."""
import logging
from fractions import Fraction

from builder.bass_writer import validate_bass_notes
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
from viterbi.corridors import build_corridors
from viterbi.mtypes import Knot, LeaderNote
from viterbi.pathfinder import find_path
from viterbi.scale import KeyInfo

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
) -> tuple[Note, ...]:
    """Generate walking bass via Viterbi pathfinding against soprano.

    Soprano is the leader; bass is the follower.  Structural bass knots
    (schema degrees) are pinned; between them the solver finds the
    optimal diatonic bass line minimising counterpoint cost.
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
    knots: list[Knot] = []
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
    if len(knots) == 0 or abs(float(phrase_end) - knots[-1].beat) > 1e-6:
        knots.append(Knot(beat=float(phrase_end), midi_pitch=final_midi))

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

    # ================================================================
    # Step 3 — Build leader notes (soprano at each grid position)
    # ================================================================
    leader_notes: list[LeaderNote] = []
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
        leader_notes.append(LeaderNote(beat=float(onset), midi_pitch=sp))
        prev_sop = sp

    # ================================================================
    # Step 4 — Build corridors with voice-crossing post-filter
    # ================================================================
    key_info: KeyInfo = KeyInfo(
        pitch_class_set=plan.local_key.pitch_class_set,
        tonic_pc=plan.local_key.degree_to_midi(degree=1, octave=0) % 12,
    )
    corridors = build_corridors(
        leader_notes=leader_notes,
        follower_low=plan.lower_range.low,
        follower_high=plan.lower_range.high,
        key=key_info,
        beats_per_bar=float(bar_length),
    )
    # L004: remove bass pitches above soprano (leader_pitch)
    for corridor in corridors:
        corridor.legal_pitches = [
            p for p in corridor.legal_pitches
            if p <= corridor.leader_pitch
        ]
        assert len(corridor.legal_pitches) > 0, (
            f"No legal bass pitch at beat {corridor.beat} below soprano "
            f"{corridor.leader_pitch} in range "
            f"[{plan.lower_range.low}, {plan.lower_range.high}]"
        )

    # ================================================================
    # Step 5 — Solve
    # ================================================================
    assert len(knots) >= 2, f"Need >= 2 bass knots, got {len(knots)}"
    assert abs(knots[0].beat - leader_notes[0].beat) < 1e-6, (
        f"First knot {knots[0].beat} != first leader {leader_notes[0].beat}"
    )
    assert abs(knots[-1].beat - leader_notes[-1].beat) < 1e-6, (
        f"Last knot {knots[-1].beat} != last leader {leader_notes[-1].beat}"
    )

    _beats, pitches, total_cost = find_path(
        corridors=corridors,
        knots=knots,
        final_pitch=knots[-1].midi_pitch,
        phrase_length=len(leader_notes),
        verbose=False,
        key=key_info,
        chord_pcs_at=None,
    )
    logger.debug(
        "bass_viterbi: phrase at %s, cost=%.2f, %d notes",
        plan.start_offset, total_cost, len(pitches),
    )

    # ================================================================
    # Step 6 — Convert solver output to Notes
    # ================================================================
    notes: list[Note] = []
    for (onset, dur), pitch in zip(grid_positions, pitches):
        # Negative duration = final endpoint marker; extend previous note
        if dur < 0:
            if notes:
                prev_note: Note = notes[-1]
                notes[-1] = Note(
                    offset=prev_note.offset,
                    pitch=prev_note.pitch,
                    duration=onset - prev_note.offset,
                    voice=TRACK_BASS,
                )
            continue
        notes.append(Note(
            offset=onset,
            pitch=pitch,
            duration=dur,
            voice=TRACK_BASS,
        ))

    # ================================================================
    # Step 7 — Validate
    # ================================================================
    validate_bass_notes(notes=notes, plan=plan, soprano_notes=soprano_notes)

    return tuple(notes)
