"""Phrase orchestrator: delegates soprano and bass generation to dedicated modules."""
import logging
from dataclasses import replace
from fractions import Fraction

from builder.bass_viterbi import BassOptions, generate_bass_viterbi
from builder.cadence_writer import write_cadence, write_thematic_cadence
from builder.galant.bass_writer import generate_bass_phrase
from builder.galant.harmony import build_harmonic_grid, HarmonicGrid
from builder.galant.soprano_writer import build_structural_soprano
from builder.figuration.rhythm_calc import compute_rhythmic_distribution
from builder.phrase_types import BeatPosition, PhrasePlan, PhraseResult, make_tail_plan, make_free_companion_plan
from builder.voice_types import VoiceBias
from builder.soprano_viterbi import SopranoOptions, generate_soprano_viterbi
from builder.types import Note
from motifs.fragen import (
    Fragment,
    FragenProvider,
    VOICE_BASS as FRAGEN_BASS,
    VOICE_SOPRANO as FRAGEN_SOPRANO,
    realise_to_notes,
)
from motifs.subject_loader import SubjectTriple, ThematicBias
from planner.schema_loader import get_schema
from planner.thematic import BeatRole
from shared.constants import TRACK_BASS, TRACK_SOPRANO
from shared.key import Key
from shared.music_math import parse_metre
from shared.pitch import degree_to_nearest_midi
from shared.tracer import get_tracer, _key_str
from shared.voice_types import Range
from viterbi.scale import KeyInfo, triad_pcs as viterbi_triad_pcs

_log: logging.Logger = logging.getLogger(__name__)

# Implied harmonic progression above dominant pedal (2 bars, 4/4).
# Each entry: (bar_offset 0-based, beat_offset 0-based, chord_root_degree).
# bar_offset 0 = bar 1; beat_offset 0 = beat 1, 2 = beat 3 (half-bar divisions).
_PEDAL_HARMONY_2BAR_4_4: tuple[tuple[int, int, int], ...] = (
    (0, 0, 1),  # bar 1 beat 1: I   — consonant frame
    (0, 2, 4),  # bar 1 beat 3: IV  — mild tension
    (1, 0, 7),  # bar 2 beat 1: viio — leading tone, max tension
    (1, 2, 1),  # bar 2 beat 3: I   — pre-cadential approach
)


def _is_walking(plan: PhrasePlan) -> bool:
    """True if plan uses walking bass texture (Viterbi path)."""
    return (
        plan.bass_texture == "walking"
        or (plan.bass_pattern is not None
            and plan.bass_pattern.startswith("continuo_walking"))
    )


def _bass_for_plan(
    plan: PhrasePlan,
    soprano_notes: tuple[Note, ...],
    prior_bass: tuple[Note, ...],
    harmonic_grid: HarmonicGrid | None = None,
) -> tuple[Note, ...]:
    """Dispatch bass generation: Viterbi for walking, greedy otherwise."""
    if _is_walking(plan=plan):
        return generate_bass_viterbi(
            plan=plan,
            soprano_notes=soprano_notes,
            prior_lower=prior_bass,
            options=BassOptions(harmonic_grid=harmonic_grid),
        )
    return generate_bass_phrase(
        plan=plan,
        soprano_notes=soprano_notes,
        prior_bass=prior_bass,
    )



def _segment_into_entries(thematic_roles: tuple[BeatRole, ...]) -> list[dict]:
    """Segment BeatRoles into entries (beat-aware).

    An entry is a contiguous run where each voice maintains the same role.
    Detects role changes at any beat, not just bar boundaries.
    If a bar has a mid-bar role change, it is split into multiple sub-entries.

    Returns:
        List of entry dicts with:
        - first_bar: int (1-based)
        - bar_count: int (may be 0 for mid-bar sub-entries within a single bar)
        - start_beat_offset: Fraction (beat offset within first_bar, 0 for bar-aligned)
        - voice0_role: ThematicRole
        - voice1_role: ThematicRole
        - beat_role_v0: BeatRole | None (first beat of voice 0)
        - beat_role_v1: BeatRole | None (first beat of voice 1)
    """
    from planner.thematic import ThematicRole

    # Group by (bar, beat), collect roles for each voice
    bar_beat_roles: dict[int, dict[Fraction, dict[int, BeatRole]]] = {}
    for role in thematic_roles:
        if role.bar not in bar_beat_roles:
            bar_beat_roles[role.bar] = {}
        if role.beat not in bar_beat_roles[role.bar]:
            bar_beat_roles[role.bar][role.beat] = {}
        bar_beat_roles[role.bar][role.beat][role.voice] = role

    # Sort bars
    sorted_bars: list[int] = sorted(bar_beat_roles.keys())

    # Build entries with beat-awareness
    entries: list[dict] = []
    current_entry: dict | None = None
    consumed_bars: set[int] = set()  # Track bars already unified into entries

    for bar in sorted_bars:
        # Skip bars already consumed by hold-exchange continuation
        if bar in consumed_bars:
            continue

        # Get all beats in this bar, sorted
        beats_in_bar: list[Fraction] = sorted(bar_beat_roles[bar].keys())

        for beat in beats_in_bar:
            voice0_beat_role: BeatRole | None = bar_beat_roles[bar][beat].get(0)
            voice1_beat_role: BeatRole | None = bar_beat_roles[bar][beat].get(1)
            voice0_role: ThematicRole = voice0_beat_role.role if voice0_beat_role else ThematicRole.FREE
            voice1_role: ThematicRole = voice1_beat_role.role if voice1_beat_role else ThematicRole.FREE

            if current_entry is None:
                # Start first entry
                current_entry = {
                    "first_bar": bar,
                    "bar_count": 1,
                    "start_beat_offset": beat,
                    "voice0_role": voice0_role,
                    "voice1_role": voice1_role,
                    "beat_role_v0": voice0_beat_role,
                    "beat_role_v1": voice1_beat_role,
                }
            elif (voice0_role != current_entry["voice0_role"] or
                  voice1_role != current_entry["voice1_role"]):
                # Check if this is hold-exchange continuation (HOLD↔FREE swap)
                is_hold_exchange_continuation: bool = (
                    {current_entry["voice0_role"], current_entry["voice1_role"]} == {ThematicRole.HOLD, ThematicRole.FREE} and
                    {voice0_role, voice1_role} == {ThematicRole.HOLD, ThematicRole.FREE} and
                    beat == Fraction(0)  # Must be bar-aligned
                )

                if is_hold_exchange_continuation:
                    # Hold-exchange: voices swap HOLD↔FREE, keep entry unified
                    current_entry["bar_count"] += 1
                    consumed_bars.add(bar)  # Mark this bar as consumed
                    break  # Skip remaining beats in this bar
                else:
                    # Role pattern changed, close current entry and start new one
                    entries.append(current_entry)
                    current_entry = {
                        "first_bar": bar,
                        "bar_count": 1 if beat == Fraction(0) else 0,
                        "start_beat_offset": beat,
                        "voice0_role": voice0_role,
                        "voice1_role": voice1_role,
                        "beat_role_v0": voice0_beat_role,
                        "beat_role_v1": voice1_beat_role,
                    }
            elif bar > current_entry["first_bar"] + current_entry["bar_count"] - 1:
                # New bar with same role pattern, extend bar_count
                current_entry["bar_count"] += 1

    # Close last entry
    if current_entry is not None:
        entries.append(current_entry)

    return entries


def _assert_within_entry(
    new_notes: tuple[Note, ...],
    voice_name: str,
    window_start: Fraction,
    window_end: Fraction,
    entry_first_bar: int,
) -> None:
    """Assert every note starts within the entry's time window."""
    for n in new_notes:
        assert window_start <= n.offset < window_end, (
            f"{voice_name} note outside entry window: offset={float(n.offset)} "
            f"window=[{float(window_start)}, {float(window_end)}) "
            f"creator={n.creator!r} pitch={n.pitch} bar={entry_first_bar}"
        )


def _write_thematic(
    plan: PhrasePlan,
    fugue: SubjectTriple,
    prior_upper: tuple[Note, ...],
    prior_lower: tuple[Note, ...],
    next_phrase_entry_degree: int | None,
    next_phrase_entry_key: Key | None,
    fragen_provider: FragenProvider | None,
) -> PhraseResult:
    """Write phrase using thematic renderer (TD-3 + R1 refactor).

    Voice-agnostic rendering via entry_renderer, hold_writer, free_fill modules.
    """
    from builder.entry_renderer import EntryTimeSpan, render_entry_voice
    from builder.free_fill import fill_free_bars
    from builder.hold_writer import render_hold_entry
    from planner.thematic import ThematicRole

    assert plan.thematic_roles is not None, "thematic_roles must be populated"
    bias: ThematicBias = fugue.thematic_bias()

    # Segment phrase into entries
    entries: list[dict] = _segment_into_entries(plan.thematic_roles)

    # Filter entries: skip all-FREE entries (will be handled by tail logic)
    material_entries: list[dict] = []
    for entry in entries:
        v0_role: ThematicRole = entry["voice0_role"]
        v1_role: ThematicRole = entry["voice1_role"]
        # Keep entry if either voice has material
        if (v0_role in (ThematicRole.SUBJECT, ThematicRole.ANSWER, ThematicRole.CS, ThematicRole.EPISODE, ThematicRole.STRETTO, ThematicRole.HOLD) or
            v1_role in (ThematicRole.SUBJECT, ThematicRole.ANSWER, ThematicRole.CS, ThematicRole.EPISODE, ThematicRole.STRETTO, ThematicRole.HOLD)):
            material_entries.append(entry)

    bar_length: Fraction
    beat_unit: Fraction
    bar_length, beat_unit = parse_metre(metre=plan.metre)
    phrase_end: Fraction = plan.start_offset + plan.phrase_duration

    # Track accumulated notes per voice
    soprano_notes: tuple[Note, ...] = ()
    bass_notes: tuple[Note, ...] = ()

    # Compute phrase_first_bar once for offset calculations
    phrase_first_bar: int = plan.thematic_roles[0].bar

    # Render each entry
    for entry_idx, entry in enumerate(material_entries):
        entry_first_bar: int = entry["first_bar"]
        entry_bar_count: int = entry["bar_count"]
        entry_start_beat: Fraction = entry["start_beat_offset"]
        voice0_role: ThematicRole = entry["voice0_role"]
        voice1_role: ThematicRole = entry["voice1_role"]
        beat_role_v0: BeatRole | None = entry["beat_role_v0"]
        beat_role_v1: BeatRole | None = entry["beat_role_v1"]

        # Compute entry start offset from phrase start (beat-aware)
        bars_from_phrase_start: int = entry_first_bar - phrase_first_bar
        entry_start_offset: Fraction = plan.start_offset + bars_from_phrase_start * bar_length + entry_start_beat

        # Compute next entry start (end of this entry's time window)
        is_last_entry: bool = entry_idx == len(material_entries) - 1
        if not is_last_entry:
            next_entry: dict = material_entries[entry_idx + 1]
            next_entry_first_bar: int = next_entry["first_bar"]
            next_entry_start_beat: Fraction = next_entry["start_beat_offset"]
            next_entry_start_offset: Fraction = (
                plan.start_offset + (next_entry_first_bar - phrase_first_bar) * bar_length + next_entry_start_beat
            )
        else:
            # Last entry: time window extends to phrase end
            next_entry_start_offset = phrase_end

        # HOLD: both voices handled together (returns accumulated tuples)
        if voice0_role == ThematicRole.HOLD or voice1_role == ThematicRole.HOLD:
            _hold_prev_sop: int = len(soprano_notes)
            _hold_prev_bas: int = len(bass_notes)
            soprano_notes, bass_notes = render_hold_entry(
                entry_first_bar=entry_first_bar,
                entry_bar_count=entry_bar_count,
                entry_start_offset=entry_start_offset,
                voice0_role=voice0_role,
                voice1_role=voice1_role,
                beat_role_v0=beat_role_v0,
                beat_role_v1=beat_role_v1,
                fugue=fugue,
                bar_length=bar_length,
                beat_unit=beat_unit,
                plan=plan,
                soprano_notes=soprano_notes,
                bass_notes=bass_notes,
            )
            _assert_within_entry(soprano_notes[_hold_prev_sop:], "soprano", entry_start_offset, next_entry_start_offset, entry_first_bar)
            _assert_within_entry(bass_notes[_hold_prev_bas:], "bass", entry_start_offset, next_entry_start_offset, entry_first_bar)
            continue

        # EPISODE: both voices rendered together via fragen
        if voice0_role == ThematicRole.EPISODE and voice1_role == ThematicRole.EPISODE:
            # Determine leader voice from BeatRole.material ("head" = leader)
            assert beat_role_v0 is not None, f"No BeatRole for voice 0 EPISODE at bar {entry_first_bar}"
            assert beat_role_v1 is not None, f"No BeatRole for voice 1 EPISODE at bar {entry_first_bar}"
            lead_voice_idx: int = 0 if beat_role_v0.material == "head" else 1
            leader_fragen: int = FRAGEN_SOPRANO if lead_voice_idx == 0 else FRAGEN_BASS

            # Step direction from fragment_iteration sign
            first_bar_role: BeatRole = beat_role_v0 if lead_voice_idx == 0 else beat_role_v1
            step: int = 1 if first_bar_role.fragment_iteration > 0 else -1

            # Select fragment via provider
            selected: Fragment | None = None
            if fragen_provider is not None:
                selected = fragen_provider.get_fragment(
                    leader_voice=leader_fragen,
                    step=step,
                )

            if selected is not None:
                episode_key: Key = beat_role_v0.material_key
                episode_notes: list[Note] | None = realise_to_notes(
                    fragment=selected,
                    n_bars=entry_bar_count,
                    step=step,
                    bar_length=bar_length,
                    key=episode_key,
                    start_offset=entry_start_offset,
                    prior_upper_pitch=soprano_notes[-1].pitch if soprano_notes else None,
                    prior_lower_pitch=bass_notes[-1].pitch if bass_notes else None,
                )
            else:
                episode_notes = None

            if episode_notes is not None:
                # Partition into soprano and bass
                ep_soprano: list[Note] = [n for n in episode_notes if n.voice == TRACK_SOPRANO]
                ep_bass: list[Note] = [n for n in episode_notes if n.voice == TRACK_BASS]

                # Label first notes
                if ep_soprano:
                    ep_soprano[0] = replace(ep_soprano[0], lyric="episode")
                if ep_bass:
                    ep_bass[0] = replace(ep_bass[0], lyric="episode")

                _ep_sop: tuple[Note, ...] = tuple(ep_soprano)
                _ep_bas: tuple[Note, ...] = tuple(ep_bass)
                soprano_notes = soprano_notes + _ep_sop
                bass_notes = bass_notes + _ep_bas
                _assert_within_entry(_ep_sop, "soprano", entry_start_offset, next_entry_start_offset, entry_first_bar)
                _assert_within_entry(_ep_bas, "bass", entry_start_offset, next_entry_start_offset, entry_first_bar)

                # Trace both voices
                tracer = get_tracer()
                if ep_soprano:
                    sp: list[int] = [n.pitch for n in ep_soprano]
                    tracer.trace_thematic_render(
                        bar=entry_first_bar,
                        voice_name="U",
                        role_name="EPISODE",
                        key_str=_key_str(key=episode_key),
                        note_count=len(ep_soprano),
                        low_pitch=min(sp),
                        high_pitch=max(sp),
                    )
                if ep_bass:
                    bp: list[int] = [n.pitch for n in ep_bass]
                    tracer.trace_thematic_render(
                        bar=entry_first_bar,
                        voice_name="L",
                        role_name="EPISODE",
                        key_str=_key_str(key=episode_key),
                        note_count=len(ep_bass),
                        low_pitch=min(bp),
                        high_pitch=max(bp),
                    )
                continue

            # Fragen fallback: realise_to_notes returned None
            _log.warning(
                "Fragen fallback at bar %d: realise_to_notes returned None, "
                "falling through to per-voice episode rendering",
                entry_first_bar,
            )
            # Fall through to per-voice rendering below

        # PEDAL: voice-1 specific, no duplication — keep inline
        if voice1_role == ThematicRole.PEDAL:
            assert beat_role_v1 is not None, f"No BeatRole for voice 1 PEDAL at entry bar {entry_first_bar}"
            assert beat_role_v1.material is not None, "PEDAL BeatRole missing material (degree)"

            # Build sub-plan for this entry's bars
            start_bar_relative: int = entry_first_bar - phrase_first_bar + 1
            pedal_plan: PhrasePlan = make_free_companion_plan(
                plan=plan,
                start_bar_relative=start_bar_relative,
                bar_count=entry_bar_count,
                start_offset=entry_start_offset,
                prev_exit_upper=soprano_notes[-1].pitch if soprano_notes else plan.prev_exit_upper,
                prev_exit_lower=bass_notes[-1].pitch if bass_notes else plan.prev_exit_lower,
            )

            # Generate bass Viterbi with density_override="low"
            pedal_bass_bias: VoiceBias = VoiceBias(
                degree_affinity=bias.degree_affinity,
                interval_affinity=bias.subject_interval_affinity,
            )
            pedal_bass: tuple[Note, ...] = generate_bass_viterbi(
                plan=pedal_plan,
                soprano_notes=soprano_notes,
                prior_lower=bass_notes,
                options=BassOptions(density_override="low", bias=pedal_bass_bias),
            )

            # Label first note
            if pedal_bass:
                pedal_bass = (replace(pedal_bass[0], lyric="pedal"),) + pedal_bass[1:]
                bass_notes = bass_notes + pedal_bass
                _assert_within_entry(pedal_bass, "bass", entry_start_offset, next_entry_start_offset, entry_first_bar)

                # Trace render
                tracer = get_tracer()
                note_pitches = [n.pitch for n in pedal_bass]
                tracer.trace_thematic_render(
                    bar=entry_first_bar,
                    voice_name="L",
                    role_name="PEDAL",
                    key_str=_key_str(key=beat_role_v1.material_key),
                    note_count=len(pedal_bass),
                    low_pitch=min(note_pitches),
                    high_pitch=max(note_pitches),
                )

            # Render voice 0 if it has material
            if voice0_role != ThematicRole.FREE:
                voice0_notes = render_entry_voice(
                    role=voice0_role,
                    beat_role=beat_role_v0,
                    fugue=fugue,
                    time_span=EntryTimeSpan(
                        start_offset=entry_start_offset,
                        end_offset=next_entry_start_offset,
                        first_bar=entry_first_bar,
                        bar_count=entry_bar_count,
                    ),
                    target_track=TRACK_SOPRANO,
                    target_range=plan.upper_range,
                    voice_name="U",
                    plan=plan,
                )
                soprano_notes = soprano_notes + voice0_notes
                _v0_window_start: Fraction = (
                    entry_start_offset + beat_role_v0.render_offset
                    if voice0_role == ThematicRole.ANSWER and beat_role_v0 is not None
                    else entry_start_offset
                )
                _assert_within_entry(voice0_notes, "soprano", _v0_window_start, next_entry_start_offset, entry_first_bar)
            continue

        # CP2: CS + companion — render companion first, then Viterbi CS
        _COMPANION_ROLES = {ThematicRole.SUBJECT, ThematicRole.ANSWER, ThematicRole.STRETTO}
        cs_idx: int | None = None
        comp_idx: int | None = None

        if voice0_role == ThematicRole.CS and voice1_role in _COMPANION_ROLES:
            cs_idx, comp_idx = 0, 1
        elif voice1_role == ThematicRole.CS and voice0_role in _COMPANION_ROLES:
            cs_idx, comp_idx = 1, 0

        if cs_idx is not None:
            assert comp_idx is not None
            # Unpack companion params
            comp_role: ThematicRole = voice0_role if comp_idx == 0 else voice1_role
            comp_beat: BeatRole | None = beat_role_v0 if comp_idx == 0 else beat_role_v1
            comp_track: int = TRACK_SOPRANO if comp_idx == 0 else TRACK_BASS
            comp_range: Range = plan.upper_range if comp_idx == 0 else plan.lower_range
            comp_vname: str = "U" if comp_idx == 0 else "L"

            companion_entry_notes: tuple[Note, ...] = render_entry_voice(
                role=comp_role,
                beat_role=comp_beat,
                fugue=fugue,
                time_span=EntryTimeSpan(
                    start_offset=entry_start_offset,
                    end_offset=next_entry_start_offset,
                    first_bar=entry_first_bar,
                    bar_count=entry_bar_count,
                ),
                target_track=comp_track,
                target_range=comp_range,
                voice_name=comp_vname,
                plan=plan,
            )
            _comp_window_start: Fraction = (
                entry_start_offset + comp_beat.render_offset
                if comp_role == ThematicRole.ANSWER and comp_beat is not None
                else entry_start_offset
            )
            if comp_idx == 0:
                soprano_notes = soprano_notes + companion_entry_notes
                _assert_within_entry(companion_entry_notes, "soprano", _comp_window_start, next_entry_start_offset, entry_first_bar)
            else:
                bass_notes = bass_notes + companion_entry_notes
                _assert_within_entry(companion_entry_notes, "bass", _comp_window_start, next_entry_start_offset, entry_first_bar)

            # CS via Viterbi if companion has notes, else fallback stamp-in
            cs_beat: BeatRole | None = beat_role_v0 if cs_idx == 0 else beat_role_v1
            cs_track: int = TRACK_SOPRANO if cs_idx == 0 else TRACK_BASS
            cs_range: Range = plan.upper_range if cs_idx == 0 else plan.lower_range
            cs_vname: str = "U" if cs_idx == 0 else "L"
            cs_index: int = (
                int(cs_beat.material)
                if cs_beat is not None
                and cs_beat.material is not None
                and cs_beat.material.isdigit()
                else 0
            )

            if companion_entry_notes:
                from builder.cs_writer import CSTarget, generate_cs_viterbi

                assert cs_beat is not None, f"No BeatRole for CS at entry bar {entry_first_bar}"
                cs_entry_notes: tuple[Note, ...] = generate_cs_viterbi(
                    fugue=fugue,
                    companion_notes=companion_entry_notes,
                    companion_is_above=(comp_idx == 0),
                    start_offset=entry_start_offset,
                    end_offset=next_entry_start_offset,
                    target=CSTarget(
                        key=cs_beat.material_key,
                        track=cs_track,
                        voice_range=cs_range,
                    ),
                    metre=plan.metre,
                    local_key=plan.local_key,
                    cadential_approach=plan.cadential_approach,
                    cs_index=cs_index,
                )
            else:
                # Fallback: stamp-in CS via render_entry_voice (silent companion)
                cs_entry_notes = render_entry_voice(
                    role=ThematicRole.CS,
                    beat_role=cs_beat,
                    fugue=fugue,
                    time_span=EntryTimeSpan(
                        start_offset=entry_start_offset,
                        end_offset=next_entry_start_offset,
                        first_bar=entry_first_bar,
                        bar_count=entry_bar_count,
                    ),
                    target_track=cs_track,
                    target_range=cs_range,
                    voice_name=cs_vname,
                    plan=plan,
                )

            # Trace CS render (role_name includes cs_index for verification)
            if cs_entry_notes:
                tracer = get_tracer()
                cs_pitches: list[int] = [n.pitch for n in cs_entry_notes]
                tracer.trace_thematic_render(
                    bar=entry_first_bar,
                    voice_name=cs_vname,
                    role_name=f"CS[{cs_index}]",
                    key_str=_key_str(key=cs_beat.material_key) if cs_beat else "",
                    note_count=len(cs_entry_notes),
                    low_pitch=min(cs_pitches),
                    high_pitch=max(cs_pitches),
                )

            if cs_idx == 0:
                soprano_notes = soprano_notes + cs_entry_notes
                _assert_within_entry(cs_entry_notes, "soprano", entry_start_offset, next_entry_start_offset, entry_first_bar)
            else:
                bass_notes = bass_notes + cs_entry_notes
                _assert_within_entry(cs_entry_notes, "bass", entry_start_offset, next_entry_start_offset, entry_first_bar)
            continue

        # All other roles: voice-agnostic loop
        for voice_idx, (role, beat_role) in enumerate((
            (voice0_role, beat_role_v0),
            (voice1_role, beat_role_v1),
        )):
            if role == ThematicRole.FREE:
                continue

            track = TRACK_SOPRANO if voice_idx == 0 else TRACK_BASS
            vrange = plan.upper_range if voice_idx == 0 else plan.lower_range
            vname = "U" if voice_idx == 0 else "L"

            notes = render_entry_voice(
                role=role,
                beat_role=beat_role,
                fugue=fugue,
                time_span=EntryTimeSpan(
                    start_offset=entry_start_offset,
                    end_offset=next_entry_start_offset,
                    first_bar=entry_first_bar,
                    bar_count=entry_bar_count,
                ),
                target_track=track,
                target_range=vrange,
                voice_name=vname,
                plan=plan,
            )
            _gen_window_start: Fraction = (
                entry_start_offset + beat_role.render_offset
                if role == ThematicRole.ANSWER and beat_role is not None
                else entry_start_offset
            )
            if voice_idx == 0:
                soprano_notes = soprano_notes + notes
                _assert_within_entry(notes, "soprano", _gen_window_start, next_entry_start_offset, entry_first_bar)
            else:
                bass_notes = bass_notes + notes
                _assert_within_entry(notes, "bass", _gen_window_start, next_entry_start_offset, entry_first_bar)

    # Fill FREE bars (companion + tail)
    soprano_notes, bass_notes = fill_free_bars(
        plan=plan,
        material_entries=material_entries,
        soprano_notes=soprano_notes,
        bass_notes=bass_notes,
        prior_upper=prior_upper,
        prior_lower=prior_lower,
        next_phrase_entry_degree=next_phrase_entry_degree,
        next_phrase_entry_key=next_phrase_entry_key,
        bar_length=bar_length,
        bias=bias,
    )

    # Return phrase result
    return PhraseResult(
        upper_notes=soprano_notes,
        lower_notes=bass_notes,
        exit_upper=soprano_notes[-1].pitch if soprano_notes else plan.prev_exit_upper or 60,
        exit_lower=bass_notes[-1].pitch if bass_notes else plan.prev_exit_lower or 48,
        schema_name=plan.schema_name,
        soprano_figures=(),
        bass_pattern_name=None,
    )


def _write_schematic(
    plan: PhrasePlan,
    prior_upper: tuple[Note, ...],
    prior_lower: tuple[Note, ...],
    next_phrase_entry_degree: int | None,
    next_phrase_entry_key: Key | None,
    is_final: bool,
) -> PhraseResult:
    """Write schematic phrase using galant order (structural soprano → bass → soprano).

    For non-thematic, non-cadential phrases. Builds structural soprano from schema degrees,
    generates bass (Viterbi or pattern), then Viterbi soprano with diminution.
    """
    # Build harmonic grid from schema annotations (HRL-2)
    schema = get_schema(name=plan.schema_name)
    harmonic_grid: HarmonicGrid | None = None
    if schema.harmony is not None:
        harmonic_grid = build_harmonic_grid(
            plan=plan,
            schema_harmony=schema.harmony,
        )

    prev_exit_upper: int | None = prior_upper[-1].pitch if prior_upper else None
    structural_soprano: tuple[Note, ...] = build_structural_soprano(
        plan=plan,
        prev_exit_midi=prev_exit_upper,
    )
    bass_notes: tuple[Note, ...] = _bass_for_plan(
        plan=plan,
        soprano_notes=prior_upper + structural_soprano,
        prior_bass=prior_lower,
        harmonic_grid=harmonic_grid,
    )
    soprano_notes: tuple[Note, ...]
    soprano_figures: tuple[str, ...]
    soprano_notes, soprano_figures = generate_soprano_viterbi(
        plan=plan,
        bass_notes=bass_notes,
        prior_upper=prior_upper,
        next_phrase_entry_degree=next_phrase_entry_degree,
        next_phrase_entry_key=next_phrase_entry_key,
        harmonic_grid=harmonic_grid,
    )
    bass_pattern_name: str | None = plan.bass_pattern

    return PhraseResult(
        upper_notes=soprano_notes,
        lower_notes=bass_notes,
        exit_upper=soprano_notes[-1].pitch,
        exit_lower=bass_notes[-1].pitch,
        schema_name=plan.schema_name,
        soprano_figures=soprano_figures,
        bass_pattern_name=bass_pattern_name,
    )


def _has_material(thematic_roles: tuple[BeatRole, ...]) -> bool:
    """Check if thematic_roles contains any non-FREE material."""
    from planner.thematic import ThematicRole
    return any(
        role.role in (ThematicRole.SUBJECT, ThematicRole.ANSWER,
                     ThematicRole.CS, ThematicRole.EPISODE, ThematicRole.STRETTO, ThematicRole.HOLD)
        for role in thematic_roles
    )


def _has_pedal(thematic_roles: tuple[BeatRole, ...]) -> bool:
    """Check if thematic_roles contains a PEDAL role."""
    from planner.thematic import ThematicRole
    return any(r.role == ThematicRole.PEDAL for r in thematic_roles)


def _write_pedal(
    plan: PhrasePlan,
    prior_upper: tuple[Note, ...],
    prior_lower: tuple[Note, ...],
    next_phrase_entry_degree: int | None = None,
    next_phrase_entry_key: Key | None = None,
    fugue: SubjectTriple | None = None,
) -> PhraseResult:
    """Write pedal phrase: held bass + cup-contour soprano via Viterbi."""
    from planner.thematic import ThematicRole
    from viterbi.mtypes import ContourShape, Knot
    assert plan.thematic_roles is not None, "Pedal phrase requires thematic_roles"
    bias: ThematicBias | None = fugue.thematic_bias() if fugue is not None else None
    # Find the PEDAL BeatRole (voice 1, beat 0 of first bar)
    pedal_beat_role: BeatRole | None = None
    for role in plan.thematic_roles:
        if role.role == ThematicRole.PEDAL and role.voice == 1 and role.beat == Fraction(0):
            pedal_beat_role = role
            break
    assert pedal_beat_role is not None, "No PEDAL BeatRole found in thematic_roles"
    assert pedal_beat_role.material is not None, "PEDAL BeatRole missing material (degree)"
    pedal_degree: int = int(pedal_beat_role.material)
    # Place pedal bass pitch
    pedal_midi: int = plan.local_key.degree_to_midi(degree=pedal_degree, octave=4)
    while pedal_midi < plan.lower_range.low:
        pedal_midi += 12
    while pedal_midi - 12 >= plan.lower_range.low:
        if abs(pedal_midi - 12 - plan.lower_median) < abs(pedal_midi - plan.lower_median):
            pedal_midi -= 12
        else:
            break
    assert plan.lower_range.low <= pedal_midi <= plan.lower_range.high, (
        f"Pedal pitch {pedal_midi} outside lower range "
        f"[{plan.lower_range.low}, {plan.lower_range.high}]"
    )
    # Generate bass held notes: one semibreve per bar
    bar_length: Fraction
    beat_unit: Fraction
    bar_length, beat_unit = parse_metre(metre=plan.metre)
    bass_notes: list[Note] = []
    for bar_offset in range(plan.bar_span):
        bass_notes.append(Note(
            offset=plan.start_offset + bar_offset * bar_length,
            pitch=pedal_midi,
            duration=bar_length,
            voice=TRACK_BASS,
            creator="pedal",
        ))
    # Build sub-plan for soprano generation.
    # Use degree 5 (dominant) as the initial structural tone — consonant
    # with the pedal bass and placed near range ceiling for clear descent.
    PEDAL_SOPRANO_START_DEGREE: int = 5
    start_knot_midi: int = plan.local_key.degree_to_midi(
        degree=PEDAL_SOPRANO_START_DEGREE,
        octave=5,
    )
    while start_knot_midi > plan.upper_range.high:
        start_knot_midi -= 12
    while start_knot_midi + 12 <= plan.upper_range.high:
        start_knot_midi += 12
    start_bar_relative: int = 1
    pedal_plan: PhrasePlan = make_free_companion_plan(
        plan=plan,
        start_bar_relative=start_bar_relative,
        bar_count=plan.bar_span,
        start_offset=plan.start_offset,
        prev_exit_upper=start_knot_midi,
        prev_exit_lower=bass_notes[-1].pitch if bass_notes else plan.prev_exit_lower,
    )
    # Bias registral_bias high so place_structural_tones targets the upper octave.
    PEDAL_REGISTRAL_BIAS: int = 9  # push biased_upper_median near A5
    # Build harmonic knots and chord grid for 2-bar 4/4 pedals (PED-1).
    # For other bar spans or metres, fall back to single-knot behaviour.
    chord_pcs_per_beat: list[frozenset[int]] | None = None
    pedal_knot_spec: tuple[tuple[int, float], ...] | None = None
    if plan.bar_span == 2 and plan.metre == "4/4":
        # Four structural knots at strong beats imply a directed harmonic arc
        # (I → IV → viio → I) over the static bass pedal.
        # Knot degrees and their progress within the 2-bar span.
        # Progress 0.0 = bar 1 beat 1, 0.25 = bar 1 beat 3, etc.
        pedal_knot_spec = (
            (5, 0.00),   # I   (5th above pedal — consonant)
            (4, 0.25),   # IV  (4th above pedal — mild tension)
            (7, 0.50),   # viio (leading tone — maximum tension)
            (1, 0.75),   # I   (pre-cadential resolution)
        )
        # Build chord PCS for each of the 4 harmony steps.
        # Bar 1 steps use natural PCS; bar 2 steps use cadential PCS
        # (raises degree 7 to leading tone in minor keys).
        tonic_pc: int = plan.local_key.degree_to_midi(degree=1, octave=0) % 12
        bar1_key_info: KeyInfo = KeyInfo(
            pitch_class_set=plan.local_key.pitch_class_set,
            tonic_pc=tonic_pc,
        )
        bar2_key_info: KeyInfo = KeyInfo(
            pitch_class_set=plan.local_key.cadential_pitch_class_set,
            tonic_pc=tonic_pc,
        )
        step_chords: list[frozenset[int]] = []
        for bar_off, _beat_off, chord_root_deg in _PEDAL_HARMONY_2BAR_4_4:
            use_cadential: bool = bar_off >= 1
            step_key: KeyInfo = bar2_key_info if use_cadential else bar1_key_info
            root_pc: int = plan.local_key.degree_to_midi(degree=chord_root_deg, octave=0) % 12
            # Bar 2 viio in minor: natural degree 7 is flat; raise to leading tone.
            if use_cadential and chord_root_deg == 7 and plan.local_key.mode == "minor":
                raised_pc: int = (root_pc + 1) % 12
                if raised_pc in step_key.pitch_class_set:
                    root_pc = raised_pc
            assert root_pc in step_key.pitch_class_set, (
                f"Chord root pc {root_pc} (degree {chord_root_deg}, bar {bar_off + 1}) "
                f"not in step PCS {step_key.pitch_class_set}; "
                f"fix _PEDAL_HARMONY_2BAR_4_4 or key handling for {plan.local_key}"
            )
            step_chords.append(viterbi_triad_pcs(bass_midi=root_pc, key=step_key))
        # Expand to grid resolution: each half-bar span gets notes_per_span slots.
        # Final marker entry (duration = -1) inherits last chord.
        notes_per_span: int
        _note_dur: Fraction
        notes_per_span, _note_dur = compute_rhythmic_distribution(
            gap=bar_length / 2,
            density="high",
        )
        chord_pcs_per_beat = []
        for chord_pcs in step_chords:
            chord_pcs_per_beat.extend([chord_pcs] * notes_per_span)
        chord_pcs_per_beat.append(step_chords[-1])  # final marker position
    else:
        _log.warning(
            "Pedal writer: bar_span=%d metre=%s is not 2-bar 4/4; "
            "falling back to single-knot behaviour (no harmonic direction)",
            plan.bar_span, plan.metre,
        )
        pedal_plan = replace(
            pedal_plan,
            degrees_upper=(PEDAL_SOPRANO_START_DEGREE,),
            registral_bias=PEDAL_REGISTRAL_BIAS,
        )
    # Cup contour: start high, descend to nadir at ~55%, ascend to cadential
    # handoff.  Units are scale degrees relative to range midpoint.
    # With harmonic knots providing direction, contour values are reduced
    # (knots do the structural work; contour only supplements shape).
    PEDAL_CONTOUR_START: float = 3.0   # slightly lower — knots do the work now
    PEDAL_CONTOUR_NADIR: float = -2.0  # shallower — knots prevent aimlessness
    PEDAL_CONTOUR_NADIR_POS: float = 0.45  # nadir before halfway — steep descent
    PEDAL_CONTOUR_END_DEFAULT: float = 2.0  # fallback if no next-phrase info
    PEDAL_CONTOUR_WEIGHT: float = 3.0  # reduced — knots and chords provide constraint
    # Compute contour end from next phrase's entry pitch when available.
    # This connects the pedal ascent to the cadence's first soprano note.
    contour_end: float
    if next_phrase_entry_degree is not None and next_phrase_entry_key is not None:
        next_entry_midi: int = degree_to_nearest_midi(
            degree=next_phrase_entry_degree,
            key=next_phrase_entry_key,
            target_midi=start_knot_midi,
            midi_range=(plan.upper_range.low, plan.upper_range.high),
        )
        range_mid: int = (plan.upper_range.low + plan.upper_range.high) // 2
        pc_count: int = len(plan.local_key.pitch_class_set)
        avg_step: float = 12.0 / max(pc_count, 1)
        contour_end = (next_entry_midi - range_mid) / avg_step
    else:
        contour_end = PEDAL_CONTOUR_END_DEFAULT
    pedal_contour: ContourShape = ContourShape(
        start=PEDAL_CONTOUR_START,
        apex=PEDAL_CONTOUR_NADIR,
        apex_pos=PEDAL_CONTOUR_NADIR_POS,
        end=contour_end,
        weight=PEDAL_CONTOUR_WEIGHT,
    )
    soprano_notes: tuple[Note, ...]
    soprano_figures: tuple[str, ...]
    # Pass empty prior_upper so place_structural_tones uses
    # pedal_plan.prev_exit_upper (our high bias) instead of the
    # actual prior phrase exit which may be low.
    # Pre-compute contour-aware structural knots for 2-bar 4/4 pedal.
    # Each knot's octave follows the cup contour rather than uniformly
    # targeting the ceiling — prevents 7th leaps at the nadir.
    pedal_structural_knots: list[Knot] | None = None
    if pedal_knot_spec is not None:
        range_mid: int = (plan.upper_range.low + plan.upper_range.high) // 2
        pc_count: int = len(plan.local_key.pitch_class_set)
        avg_step: float = 12.0 / max(pc_count, 1)
        pedal_structural_knots = []
        for knot_degree, knot_progress in pedal_knot_spec:
            # Interpolate cup contour at this progress position
            if knot_progress <= PEDAL_CONTOUR_NADIR_POS:
                contour_frac: float = knot_progress / PEDAL_CONTOUR_NADIR_POS
                contour_val: float = PEDAL_CONTOUR_START + contour_frac * (PEDAL_CONTOUR_NADIR - PEDAL_CONTOUR_START)
            else:
                contour_frac = (knot_progress - PEDAL_CONTOUR_NADIR_POS) / (1.0 - PEDAL_CONTOUR_NADIR_POS)
                contour_val = PEDAL_CONTOUR_NADIR + contour_frac * (contour_end - PEDAL_CONTOUR_NADIR)
            target_midi: int = round(range_mid + contour_val * avg_step)
            knot_midi: int = degree_to_nearest_midi(
                degree=knot_degree,
                key=plan.local_key,
                target_midi=target_midi,
                midi_range=(plan.upper_range.low, plan.upper_range.high),
            )
            knot_offset: float = float(plan.start_offset) + knot_progress * float(pedal_plan.phrase_duration)
            pedal_structural_knots.append(Knot(beat=knot_offset, midi_pitch=knot_midi))
    pedal_sop_bias: VoiceBias | None = VoiceBias(
        degree_affinity=bias.degree_affinity if bias else None,
        interval_affinity=bias.subject_interval_affinity if bias else None,
        structural_knots=pedal_structural_knots,
    ) if bias is not None else (
        VoiceBias(structural_knots=pedal_structural_knots)
        if pedal_structural_knots else None
    )
    soprano_notes, soprano_figures = generate_soprano_viterbi(
        plan=pedal_plan,
        bass_notes=tuple(bass_notes),
        prior_upper=(),
        next_phrase_entry_degree=next_phrase_entry_degree,
        next_phrase_entry_key=next_phrase_entry_key,
        options=SopranoOptions(
            density_override="high",
            contour=pedal_contour,
            chord_pcs_per_beat=chord_pcs_per_beat,
            bias=pedal_sop_bias,
        ),
    )
    # Trace
    first_bar: int = plan.thematic_roles[0].bar if plan.thematic_roles else plan.start_bar
    tracer = get_tracer()
    tracer.trace_thematic_render(
        bar=first_bar,
        voice_name="L",
        role_name="PEDAL",
        key_str=_key_str(key=plan.local_key),
        note_count=len(bass_notes),
        low_pitch=pedal_midi,
        high_pitch=pedal_midi,
    )
    if soprano_notes:
        sop_pitches: list[int] = [n.pitch for n in soprano_notes]
        tracer.trace_thematic_render(
            bar=first_bar,
            voice_name="U",
            role_name="PEDAL_SOP",
            key_str="",
            note_count=len(soprano_notes),
            low_pitch=min(sop_pitches),
            high_pitch=max(sop_pitches),
        )
    return PhraseResult(
        upper_notes=soprano_notes,
        lower_notes=tuple(bass_notes),
        exit_upper=soprano_notes[-1].pitch if soprano_notes else plan.prev_exit_upper or 60,
        exit_lower=bass_notes[-1].pitch if bass_notes else plan.prev_exit_lower or 48,
        schema_name=plan.schema_name,
        soprano_figures=(),
        bass_pattern_name=None,
    )


def _write_cadential(
    plan: PhrasePlan,
    prior_upper: tuple[Note, ...],
    prior_lower: tuple[Note, ...],
    is_final: bool,
    fugue: SubjectTriple | None = None,
) -> PhraseResult:
    """Write cadential phrase using fixed templates or thematic fragments."""
    soprano_notes: tuple[Note, ...]
    bass_notes: tuple[Note, ...]

    # Use thematic cadence for cadenza_composta 4/4 when fugue is available
    if fugue is not None and plan.schema_name == "cadenza_composta" and plan.metre == "4/4":
        soprano_notes, bass_notes = write_thematic_cadence(
            schema_name=plan.schema_name,
            metre=plan.metre,
            local_key=plan.local_key,
            start_offset=plan.start_offset,
            prior_upper=prior_upper,
            prior_lower=prior_lower,
            upper_range=(plan.upper_range.low, plan.upper_range.high),
            lower_range=(plan.lower_range.low, plan.lower_range.high),
            fugue=fugue,
            is_final=is_final,
        )
    else:
        soprano_notes, bass_notes = write_cadence(
            schema_name=plan.schema_name,
            metre=plan.metre,
            local_key=plan.local_key,
            start_offset=plan.start_offset,
            prior_upper=prior_upper,
            prior_lower=prior_lower,
            upper_range=(plan.upper_range.low, plan.upper_range.high),
            lower_range=(plan.lower_range.low, plan.lower_range.high),
            is_final=is_final,
        )
    return PhraseResult(
        upper_notes=soprano_notes,
        lower_notes=bass_notes,
        exit_upper=soprano_notes[-1].pitch,
        exit_lower=bass_notes[-1].pitch,
        schema_name=plan.schema_name,
        soprano_figures=(),
        bass_pattern_name=None,
    )


def write_phrase(
    plan: PhrasePlan,
    prior_upper: tuple[Note, ...] = (),
    prior_lower: tuple[Note, ...] = (),
    next_phrase_entry_degree: int | None = None,
    next_phrase_entry_key: Key | None = None,
    recall_figure_name: str | None = None,
    fugue: SubjectTriple | None = None,
    is_final: bool = False,
    fragen_provider: FragenProvider | None = None,
) -> PhraseResult:
    """Write complete phrase (soprano + bass) and return result.

    Three-way dispatcher (TD-3):
    - Cadential: fixed templates from cadence writer
    - Thematic: subject/answer/CS/episode/stretto from thematic renderer
    - Schematic: galant order (structural soprano → bass → soprano)
    """
    # Path 1: Cadential
    if plan.is_cadential:
        return _write_cadential(
            plan=plan,
            prior_upper=prior_upper,
            prior_lower=prior_lower,
            is_final=is_final,
            fugue=fugue,
        )

    # Path 1.5: Pedal
    if plan.thematic_roles is not None and _has_pedal(plan.thematic_roles):
        return _write_pedal(
            plan=plan,
            prior_upper=prior_upper,
            prior_lower=prior_lower,
            next_phrase_entry_degree=next_phrase_entry_degree,
            next_phrase_entry_key=next_phrase_entry_key,
            fugue=fugue,
        )

    # Path 2: Thematic
    if plan.thematic_roles is not None and _has_material(plan.thematic_roles):
        assert fugue is not None, "Thematic phrase requires fugue data"
        return _write_thematic(
            plan=plan,
            fugue=fugue,
            prior_upper=prior_upper,
            prior_lower=prior_lower,
            next_phrase_entry_degree=next_phrase_entry_degree,
            next_phrase_entry_key=next_phrase_entry_key,
            fragen_provider=fragen_provider,
        )

    # Path 3: Schematic (galant)
    return _write_schematic(
        plan=plan,
        prior_upper=prior_upper,
        prior_lower=prior_lower,
        next_phrase_entry_degree=next_phrase_entry_degree,
        next_phrase_entry_key=next_phrase_entry_key,
        is_final=is_final,
    )
