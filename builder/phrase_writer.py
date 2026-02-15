"""Phrase orchestrator: delegates soprano and bass generation to dedicated modules."""
from dataclasses import replace
from fractions import Fraction

from builder.bass_viterbi import generate_bass_viterbi
from builder.cadence_writer import write_cadence
from builder.galant.bass_writer import generate_bass_phrase
from builder.galant.harmony import build_harmonic_grid, HarmonicGrid
from builder.galant.soprano_writer import build_structural_soprano
from builder.imitation import (
    subject_to_voice_notes,
)
from builder.phrase_types import PhrasePlan, PhraseResult, make_tail_plan
from builder.soprano_viterbi import generate_soprano_viterbi
from builder.types import Note
from motifs.fugue_loader import LoadedFugue
from planner.schema_loader import get_schema
from planner.thematic import BeatRole
from shared.constants import TRACK_BASS, TRACK_SOPRANO
from shared.key import Key
from shared.music_math import parse_metre


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
            harmonic_grid=harmonic_grid,
        )
    return generate_bass_phrase(
        plan=plan,
        soprano_notes=soprano_notes,
        prior_bass=prior_bass,
    )


def _segment_into_entries(thematic_roles: tuple[BeatRole, ...]) -> list[dict]:
    """Segment BeatRoles into entries.

    An entry is a contiguous run of bars where each voice maintains the same role.
    Detects role changes by comparing voice roles between consecutive bars.

    Returns:
        List of entry dicts with:
        - first_bar: int (1-based)
        - bar_count: int
        - voice0_role: ThematicRole
        - voice1_role: ThematicRole
        - beat_role_v0: BeatRole | None (first beat of voice 0)
        - beat_role_v1: BeatRole | None (first beat of voice 1)
    """
    from planner.thematic import ThematicRole

    # Group by bar, extract first beat role for each voice
    bars: dict[int, dict[int, BeatRole]] = {}
    for role in thematic_roles:
        if role.bar not in bars:
            bars[role.bar] = {}
        # Collect only beat-0 roles (first beat of bar determines entry)
        if role.beat == Fraction(0):
            bars[role.bar][role.voice] = role

    # Sort bars
    sorted_bars: list[int] = sorted(bars.keys())

    # Segment into entries
    entries: list[dict] = []
    current_entry: dict | None = None

    for bar in sorted_bars:
        voice0_beat_role: BeatRole | None = bars[bar].get(0)
        voice1_beat_role: BeatRole | None = bars[bar].get(1)
        voice0_role: ThematicRole = voice0_beat_role.role if voice0_beat_role else ThematicRole.FREE
        voice1_role: ThematicRole = voice1_beat_role.role if voice1_beat_role else ThematicRole.FREE

        if current_entry is None:
            # Start first entry
            current_entry = {
                "first_bar": bar,
                "bar_count": 1,
                "voice0_role": voice0_role,
                "voice1_role": voice1_role,
                "beat_role_v0": voice0_beat_role,
                "beat_role_v1": voice1_beat_role,
            }
        elif (voice0_role != current_entry["voice0_role"] or
              voice1_role != current_entry["voice1_role"]):
            # Role pattern changed, close current entry and start new one
            entries.append(current_entry)
            current_entry = {
                "first_bar": bar,
                "bar_count": 1,
                "voice0_role": voice0_role,
                "voice1_role": voice1_role,
                "beat_role_v0": voice0_beat_role,
                "beat_role_v1": voice1_beat_role,
            }
        else:
            # Same role pattern, extend current entry
            current_entry["bar_count"] += 1

    # Close last entry
    if current_entry is not None:
        entries.append(current_entry)

    return entries


def _write_thematic(
    plan: PhrasePlan,
    fugue: LoadedFugue,
    prior_upper: tuple[Note, ...],
    prior_lower: tuple[Note, ...],
    next_phrase_entry_degree: int | None,
    next_phrase_entry_key: Key | None,
) -> PhraseResult:
    """Write phrase using thematic renderer (TD-3).

    Unified dispatcher for all thematic material: SUBJECT, ANSWER, CS, EPISODE, STRETTO.
    Segments phrase into entries, renders each entry's material within a time window,
    and generates FREE tail bars using galant order (structural soprano → bass → soprano).
    """
    from builder.thematic_renderer import render_thematic_beat, _render_episode_fragment
    from planner.thematic import ThematicRole
    from shared.tracer import get_tracer, _key_str

    assert plan.thematic_roles is not None, "thematic_roles must be populated"

    # Segment phrase into entries
    entries: list[dict] = _segment_into_entries(plan.thematic_roles)

    # Filter entries: skip all-FREE entries (will be handled by tail logic)
    material_entries: list[dict] = []
    for entry in entries:
        v0_role: ThematicRole = entry["voice0_role"]
        v1_role: ThematicRole = entry["voice1_role"]
        # Keep entry if either voice has material
        if (v0_role in (ThematicRole.SUBJECT, ThematicRole.ANSWER, ThematicRole.CS, ThematicRole.EPISODE, ThematicRole.STRETTO) or
            v1_role in (ThematicRole.SUBJECT, ThematicRole.ANSWER, ThematicRole.CS, ThematicRole.EPISODE, ThematicRole.STRETTO)):
            material_entries.append(entry)

    bar_length: Fraction = parse_metre(metre=plan.metre)[0]
    phrase_end: Fraction = plan.start_offset + plan.phrase_duration

    # Track accumulated notes per voice
    soprano_notes: tuple[Note, ...] = ()
    bass_notes: tuple[Note, ...] = ()

    # Render each entry
    for entry_idx, entry in enumerate(material_entries):
        entry_first_bar: int = entry["first_bar"]
        entry_bar_count: int = entry["bar_count"]
        voice0_role: ThematicRole = entry["voice0_role"]
        voice1_role: ThematicRole = entry["voice1_role"]
        beat_role_v0: BeatRole | None = entry["beat_role_v0"]
        beat_role_v1: BeatRole | None = entry["beat_role_v1"]

        # Compute entry start offset from phrase start
        phrase_first_bar: int = plan.thematic_roles[0].bar
        bars_from_phrase_start: int = entry_first_bar - phrase_first_bar
        entry_start_offset: Fraction = plan.start_offset + bars_from_phrase_start * bar_length

        # Compute next entry start (end of this entry's time window)
        is_last_entry: bool = entry_idx == len(material_entries) - 1
        if not is_last_entry:
            next_entry_first_bar: int = material_entries[entry_idx + 1]["first_bar"]
            next_entry_start_offset: Fraction = (
                plan.start_offset + (next_entry_first_bar - phrase_first_bar) * bar_length
            )
        else:
            # Last entry: time window extends to phrase end
            next_entry_start_offset = phrase_end

        # Render voice 0 (soprano)
        if voice0_role in (ThematicRole.SUBJECT, ThematicRole.ANSWER, ThematicRole.CS):
            assert beat_role_v0 is not None, f"No BeatRole for voice 0 at entry bar {entry_first_bar}"

            voice0_notes: tuple[Note, ...] | None = render_thematic_beat(
                role=beat_role_v0,
                fugue=fugue,
                start_offset=entry_start_offset,
                target_range=plan.upper_range,
                end_offset=next_entry_start_offset,
            )
            if voice0_notes:
                # Label first note
                lyric: str = {
                    ThematicRole.SUBJECT: "subject",
                    ThematicRole.ANSWER: "answer",
                    ThematicRole.CS: "cs",
                }[voice0_role]
                voice0_notes = (replace(voice0_notes[0], lyric=lyric),) + voice0_notes[1:]
                soprano_notes = soprano_notes + voice0_notes

                # Trace render
                tracer = get_tracer()
                note_pitches: list[int] = [n.pitch for n in voice0_notes]
                tracer.trace_thematic_render(
                    bar=entry_first_bar,
                    voice_name="U",
                    role_name=voice0_role.value.upper(),
                    key_str=_key_str(key=beat_role_v0.material_key),
                    note_count=len(voice0_notes),
                    low_pitch=min(note_pitches),
                    high_pitch=max(note_pitches),
                )
            else:
                # No notes rendered for this voice
                tracer = get_tracer()
                tracer.trace_thematic_render(
                    bar=entry_first_bar,
                    voice_name="U",
                    role_name=voice0_role.value.upper(),
                    key_str=_key_str(key=beat_role_v0.material_key),
                    note_count=0,
                    low_pitch=0,
                    high_pitch=0,
                )

        elif voice0_role == ThematicRole.EPISODE:
            # Render all episode fragments (one per bar with incrementing iteration)
            all_episode_notes: list[Note] = []
            for bar_offset in range(entry_bar_count):
                bar_num: int = entry_first_bar + bar_offset
                bar_start_offset: Fraction = entry_start_offset + Fraction(bar_offset)

                # Find BeatRole for this bar and voice 0
                bar_beat_role: BeatRole | None = None
                for role in plan.thematic_roles:
                    if role.bar == bar_num and role.voice == 0 and role.beat == Fraction(0):
                        bar_beat_role = role
                        break

                assert bar_beat_role is not None, (
                    f"No BeatRole for voice 0 EPISODE at bar {bar_num}"
                )

                # Render this bar's fragment
                fragment_notes: tuple[Note, ...] = _render_episode_fragment(
                    role=bar_beat_role,
                    fugue=fugue,
                    start_offset=bar_start_offset,
                    target_track=TRACK_SOPRANO,
                    target_range=plan.upper_range,
                )
                all_episode_notes.extend(fragment_notes)

            # Apply time window
            voice0_notes_windowed: list[Note] = []
            for n in all_episode_notes:
                if n.offset >= next_entry_start_offset:
                    break
                note_end: Fraction = n.offset + n.duration
                if note_end > next_entry_start_offset:
                    voice0_notes_windowed.append(replace(n, duration=next_entry_start_offset - n.offset))
                else:
                    voice0_notes_windowed.append(n)
            soprano_notes = soprano_notes + tuple(voice0_notes_windowed)

            # Trace render (only for first bar)
            if voice0_notes_windowed:
                tracer = get_tracer()
                note_pitches = [n.pitch for n in voice0_notes_windowed]
                tracer.trace_thematic_render(
                    bar=entry_first_bar,
                    voice_name="U",
                    role_name="EPISODE",
                    key_str=_key_str(key=beat_role_v0.material_key) if beat_role_v0 else "",
                    note_count=len(voice0_notes_windowed),
                    low_pitch=min(note_pitches),
                    high_pitch=max(note_pitches),
                )

        elif voice0_role == ThematicRole.STRETTO:
            # STRETTO: follower voice plays subject with delay (upper voice case)
            assert beat_role_v0 is not None, f"No BeatRole for voice 0 at entry bar {entry_first_bar}"
            assert beat_role_v0.material is not None, "STRETTO BeatRole missing material (delay)"

            # Parse delay from material field (string -> int)
            delay_beats: int = int(beat_role_v0.material)

            # Compute delay_offset: delay in beats × beat_unit
            bar_length: Fraction
            beat_unit: Fraction
            bar_length, beat_unit = parse_metre(metre=plan.metre)
            delay_offset: Fraction = Fraction(delay_beats) * beat_unit

            # Render subject at delayed start
            voice0_notes_stretto: tuple[Note, ...] = subject_to_voice_notes(
                fugue=fugue,
                start_offset=entry_start_offset + delay_offset,
                target_key=beat_role_v0.material_key,
                target_track=TRACK_SOPRANO,
                target_range=plan.upper_range,
            )

            # Apply time window: drop/truncate notes outside [entry_start_offset, next_entry_start_offset)
            voice0_notes_windowed: list[Note] = []
            for n in voice0_notes_stretto:
                if n.offset >= next_entry_start_offset:
                    break
                note_end: Fraction = n.offset + n.duration
                if note_end > next_entry_start_offset:
                    voice0_notes_windowed.append(replace(n, duration=next_entry_start_offset - n.offset))
                else:
                    voice0_notes_windowed.append(n)

            # Label first note
            if voice0_notes_windowed:
                voice0_notes_windowed[0] = replace(voice0_notes_windowed[0], lyric="stretto")
                soprano_notes = soprano_notes + tuple(voice0_notes_windowed)

                # Trace render
                tracer = get_tracer()
                note_pitches = [n.pitch for n in voice0_notes_windowed]
                tracer.trace_thematic_render(
                    bar=entry_first_bar,
                    voice_name="U",
                    role_name="STRETTO",
                    key_str=_key_str(key=beat_role_v0.material_key),
                    note_count=len(voice0_notes_windowed),
                    low_pitch=min(note_pitches),
                    high_pitch=max(note_pitches),
                )
            else:
                # No notes rendered (fully truncated)
                tracer = get_tracer()
                tracer.trace_thematic_render(
                    bar=entry_first_bar,
                    voice_name="U",
                    role_name="STRETTO",
                    key_str=_key_str(key=beat_role_v0.material_key),
                    note_count=0,
                    low_pitch=0,
                    high_pitch=0,
                )

        elif voice0_role == ThematicRole.FREE:
            # FREE voice within material entry
            tracer = get_tracer()
            tracer.trace_thematic_render(
                bar=entry_first_bar,
                voice_name="U",
                role_name="FREE",
                key_str="",
                note_count=0,
                low_pitch=0,
                high_pitch=0,
            )

        # Render voice 1 (bass)
        if voice1_role in (ThematicRole.SUBJECT, ThematicRole.ANSWER, ThematicRole.CS):
            assert beat_role_v1 is not None, f"No BeatRole for voice 1 at entry bar {entry_first_bar}"

            voice1_notes: tuple[Note, ...] | None = render_thematic_beat(
                role=beat_role_v1,
                fugue=fugue,
                start_offset=entry_start_offset,
                target_range=plan.lower_range,
                end_offset=next_entry_start_offset,
            )
            if voice1_notes:
                # Label first note
                lyric: str = {
                    ThematicRole.SUBJECT: "subject",
                    ThematicRole.ANSWER: "answer",
                    ThematicRole.CS: "cs",
                }[voice1_role]
                voice1_notes = (replace(voice1_notes[0], lyric=lyric),) + voice1_notes[1:]
                bass_notes = bass_notes + voice1_notes

                # Trace render
                tracer = get_tracer()
                note_pitches = [n.pitch for n in voice1_notes]
                tracer.trace_thematic_render(
                    bar=entry_first_bar,
                    voice_name="L",
                    role_name=voice1_role.value.upper(),
                    key_str=_key_str(key=beat_role_v1.material_key),
                    note_count=len(voice1_notes),
                    low_pitch=min(note_pitches),
                    high_pitch=max(note_pitches),
                )
            else:
                # No notes rendered for this voice
                tracer = get_tracer()
                tracer.trace_thematic_render(
                    bar=entry_first_bar,
                    voice_name="L",
                    role_name=voice1_role.value.upper(),
                    key_str=_key_str(key=beat_role_v1.material_key),
                    note_count=0,
                    low_pitch=0,
                    high_pitch=0,
                )

        elif voice1_role == ThematicRole.EPISODE:
            # Render all episode fragments (one per bar with incrementing iteration)
            all_episode_notes: list[Note] = []
            for bar_offset in range(entry_bar_count):
                bar_num: int = entry_first_bar + bar_offset
                bar_start_offset: Fraction = entry_start_offset + Fraction(bar_offset)

                # Find BeatRole for this bar and voice 1
                bar_beat_role: BeatRole | None = None
                for role in plan.thematic_roles:
                    if role.bar == bar_num and role.voice == 1 and role.beat == Fraction(0):
                        bar_beat_role = role
                        break

                assert bar_beat_role is not None, (
                    f"No BeatRole for voice 1 EPISODE at bar {bar_num}"
                )

                # Render this bar's fragment
                fragment_notes: tuple[Note, ...] = _render_episode_fragment(
                    role=bar_beat_role,
                    fugue=fugue,
                    start_offset=bar_start_offset,
                    target_track=TRACK_BASS,
                    target_range=plan.lower_range,
                )
                all_episode_notes.extend(fragment_notes)

            # Apply time window
            voice1_notes_windowed: list[Note] = []
            for n in all_episode_notes:
                if n.offset >= next_entry_start_offset:
                    break
                note_end: Fraction = n.offset + n.duration
                if note_end > next_entry_start_offset:
                    voice1_notes_windowed.append(replace(n, duration=next_entry_start_offset - n.offset))
                else:
                    voice1_notes_windowed.append(n)
            bass_notes = bass_notes + tuple(voice1_notes_windowed)

            # Trace render (only for first bar)
            if voice1_notes_windowed:
                tracer = get_tracer()
                note_pitches = [n.pitch for n in voice1_notes_windowed]
                tracer.trace_thematic_render(
                    bar=entry_first_bar,
                    voice_name="L",
                    role_name="EPISODE",
                    key_str=_key_str(key=beat_role_v1.material_key) if beat_role_v1 else "",
                    note_count=len(voice1_notes_windowed),
                    low_pitch=min(note_pitches),
                    high_pitch=max(note_pitches),
                )

        elif voice1_role == ThematicRole.STRETTO:
            # STRETTO: follower voice plays subject with delay
            assert beat_role_v1 is not None, f"No BeatRole for voice 1 at entry bar {entry_first_bar}"
            assert beat_role_v1.material is not None, "STRETTO BeatRole missing material (delay)"

            # Parse delay from material field (string -> int)
            delay_beats: int = int(beat_role_v1.material)

            # Compute delay_offset: delay in beats × beat_unit
            bar_length: Fraction
            beat_unit: Fraction
            bar_length, beat_unit = parse_metre(metre=plan.metre)
            delay_offset: Fraction = Fraction(delay_beats) * beat_unit

            # Render subject at delayed start
            voice1_notes_stretto: tuple[Note, ...] = subject_to_voice_notes(
                fugue=fugue,
                start_offset=entry_start_offset + delay_offset,
                target_key=beat_role_v1.material_key,
                target_track=TRACK_BASS,
                target_range=plan.lower_range,
            )

            # Apply time window: drop/truncate notes outside [entry_start_offset, next_entry_start_offset)
            voice1_notes_windowed: list[Note] = []
            for n in voice1_notes_stretto:
                if n.offset >= next_entry_start_offset:
                    break
                note_end: Fraction = n.offset + n.duration
                if note_end > next_entry_start_offset:
                    voice1_notes_windowed.append(replace(n, duration=next_entry_start_offset - n.offset))
                else:
                    voice1_notes_windowed.append(n)

            # Label first note
            if voice1_notes_windowed:
                voice1_notes_windowed[0] = replace(voice1_notes_windowed[0], lyric="stretto")
                bass_notes = bass_notes + tuple(voice1_notes_windowed)

                # Trace render
                tracer = get_tracer()
                note_pitches = [n.pitch for n in voice1_notes_windowed]
                tracer.trace_thematic_render(
                    bar=entry_first_bar,
                    voice_name="L",
                    role_name="STRETTO",
                    key_str=_key_str(key=beat_role_v1.material_key),
                    note_count=len(voice1_notes_windowed),
                    low_pitch=min(note_pitches),
                    high_pitch=max(note_pitches),
                )
            else:
                # No notes rendered (fully truncated)
                tracer = get_tracer()
                tracer.trace_thematic_render(
                    bar=entry_first_bar,
                    voice_name="L",
                    role_name="STRETTO",
                    key_str=_key_str(key=beat_role_v1.material_key),
                    note_count=0,
                    low_pitch=0,
                    high_pitch=0,
                )

        elif voice1_role == ThematicRole.FREE:
            # FREE voice within material entry
            tracer = get_tracer()
            tracer.trace_thematic_render(
                bar=entry_first_bar,
                voice_name="L",
                role_name="FREE",
                key_str="",
                note_count=0,
                low_pitch=0,
                high_pitch=0,
            )

    # Handle FREE tail bars after last material entry
    if material_entries:
        last_material_bar: int = material_entries[-1]["first_bar"] + material_entries[-1]["bar_count"] - 1
        phrase_first_bar: int = plan.thematic_roles[0].bar
        phrase_last_bar: int = plan.thematic_roles[-1].bar

        if last_material_bar < phrase_last_bar:
            # There are tail bars: generate Viterbi fill (galant order)
            tail_start_bar_absolute: int = last_material_bar + 1
            tail_start_bar: int = tail_start_bar_absolute - phrase_first_bar + 1
            bars_from_phrase_start: int = tail_start_bar_absolute - phrase_first_bar
            tail_start_offset: Fraction = plan.start_offset + bars_from_phrase_start * bar_length

            # Build tail plan
            tail_plan: PhrasePlan = make_tail_plan(
                plan=plan,
                tail_start_bar=tail_start_bar,
                tail_start_offset=tail_start_offset,
                prev_exit_upper=soprano_notes[-1].pitch if soprano_notes else plan.prev_exit_upper,
                prev_exit_lower=bass_notes[-1].pitch if bass_notes else plan.prev_exit_lower,
            )

            # Galant order: structural soprano → bass Viterbi → soprano Viterbi
            structural_tail: tuple[Note, ...] = build_structural_soprano(
                plan=tail_plan,
                prev_exit_midi=soprano_notes[-1].pitch if soprano_notes else plan.prev_exit_upper,
            )

            tail_bass: tuple[Note, ...] = generate_bass_viterbi(
                plan=tail_plan,
                soprano_notes=prior_upper + soprano_notes + structural_tail,
                prior_lower=bass_notes,
                harmonic_grid=None,
            )
            bass_notes = bass_notes + tail_bass

            tail_soprano: tuple[Note, ...]
            tail_soprano, _ = generate_soprano_viterbi(
                plan=tail_plan,
                bass_notes=bass_notes,
                prior_upper=soprano_notes,
                next_phrase_entry_degree=next_phrase_entry_degree,
                next_phrase_entry_key=next_phrase_entry_key,
                harmonic_grid=None,
            )
            soprano_notes = soprano_notes + tail_soprano

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
                     ThematicRole.CS, ThematicRole.EPISODE, ThematicRole.STRETTO)
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
) -> PhraseResult:
    """Write pedal phrase: held bass note + Viterbi soprano.

    Args:
        plan: PhrasePlan with thematic_roles containing PEDAL role
        prior_upper: Prior soprano notes
        prior_lower: Prior bass notes

    Returns:
        PhraseResult with held bass and Viterbi soprano
    """
    from planner.thematic import ThematicRole
    from shared.music_math import parse_metre

    assert plan.thematic_roles is not None, "Pedal phrase requires thematic_roles"

    # Find the PEDAL BeatRole (voice 1, beat 0 of first bar)
    pedal_beat_role: BeatRole | None = None
    for role in plan.thematic_roles:
        if role.role == ThematicRole.PEDAL and role.voice == 1 and role.beat == Fraction(0):
            pedal_beat_role = role
            break

    assert pedal_beat_role is not None, "No PEDAL BeatRole found in thematic_roles"
    assert pedal_beat_role.material is not None, "PEDAL BeatRole missing material (degree)"

    # Parse degree from material field
    pedal_degree: int = int(pedal_beat_role.material)

    # Compute MIDI pitch for pedal degree in octave 4 (middle octave)
    pedal_midi: int = plan.local_key.degree_to_midi(degree=pedal_degree, octave=4)

    # Octave-shift to fit within lower_range, preferring octave closest to lower_median
    while pedal_midi < plan.lower_range.low:
        pedal_midi += 12
    while pedal_midi - 12 >= plan.lower_range.low:
        if abs(pedal_midi - 12 - plan.lower_median) < abs(pedal_midi - plan.lower_median):
            pedal_midi -= 12
        else:
            break

    assert plan.lower_range.low <= pedal_midi <= plan.lower_range.high, (
        f"Pedal pitch {pedal_midi} (degree {pedal_degree}) outside lower range "
        f"[{plan.lower_range.low}, {plan.lower_range.high}]"
    )

    # Generate bass held notes: one per bar
    bar_length: Fraction = parse_metre(metre=plan.metre)[0]
    bass_notes: list[Note] = []
    for bar_offset in range(plan.bar_span):
        bass_notes.append(Note(
            offset=plan.start_offset + bar_offset * bar_length,
            pitch=pedal_midi,
            duration=bar_length,
            voice=TRACK_BASS,
        ))

    # Build a minimal pedal plan with structural degrees for soprano anchors
    # Provide tonic (degree 1) at start and end to give Viterbi solver boundary knots
    from builder.phrase_types import BeatPosition
    pedal_plan = replace(plan,
        degrees_upper=(1, 1),
        degrees_lower=(pedal_degree, pedal_degree),
        degree_positions=(
            BeatPosition(bar=1, beat=1),
            BeatPosition(bar=plan.bar_span, beat=1),
        ),
        degree_keys=(plan.local_key, plan.local_key),
    )

    # Generate soprano using Viterbi (no harmonic grid, scale-only mode)
    soprano_notes: tuple[Note, ...]
    soprano_notes, _ = generate_soprano_viterbi(
        plan=pedal_plan,
        bass_notes=tuple(bass_notes),
        prior_upper=prior_upper,
        next_phrase_entry_degree=None,
        next_phrase_entry_key=None,
        harmonic_grid=None,
    )

    # Trace pedal rendering
    from shared.tracer import get_tracer, _key_str
    tracer = get_tracer()
    first_bar: int = plan.thematic_roles[0].bar if plan.thematic_roles else plan.start_bar
    tracer.trace_thematic_render(
        bar=first_bar,
        voice_name="L",
        role_name="PEDAL",
        key_str=_key_str(key=plan.local_key),
        note_count=len(bass_notes),
        low_pitch=pedal_midi,
        high_pitch=pedal_midi,
    )
    tracer.trace_thematic_render(
        bar=first_bar,
        voice_name="U",
        role_name="FREE",
        key_str="",
        note_count=len(soprano_notes),
        low_pitch=min(n.pitch for n in soprano_notes) if soprano_notes else 0,
        high_pitch=max(n.pitch for n in soprano_notes) if soprano_notes else 0,
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
) -> PhraseResult:
    """Write cadential phrase using fixed templates."""
    soprano_notes: tuple[Note, ...]
    bass_notes: tuple[Note, ...]
    soprano_notes, bass_notes = write_cadence(
        schema_name=plan.schema_name,
        metre=plan.metre,
        local_key=plan.local_key,
        start_offset=plan.start_offset,
        prior_upper=prior_upper,
        prior_lower=prior_lower,
        upper_range=(plan.upper_range.low, plan.upper_range.high),
        lower_range=(plan.lower_range.low, plan.lower_range.high),
        upper_median=plan.upper_median,
        lower_median=plan.lower_median,
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
    fugue: LoadedFugue | None = None,
    is_final: bool = False,
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
        )

    # Path 1.5: Pedal
    if plan.thematic_roles is not None and _has_pedal(plan.thematic_roles):
        return _write_pedal(
            plan=plan,
            prior_upper=prior_upper,
            prior_lower=prior_lower,
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
