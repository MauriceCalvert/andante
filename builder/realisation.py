"""Realisation: Turn anchors into notes.

Category A: Pure functions, no I/O, no validation.

Canonical design: Anchors store degrees + key. MIDI conversion happens here.
Each anchor becomes a note; duration extends to next anchor.

Layer 6.5 (Figuration) can be enabled to produce baroque melodic patterns
instead of simple block-chord output.

Rhythm complementarity: When one voice leads a passage, the other voice
staggers its onsets by one subdivision to avoid parallel rhythm.
"""
from fractions import Fraction
from typing import Sequence

from builder.config_loader import load_expansions
from builder.realisation_bass import adjust_downbeat_consonance
from builder.realisation_util import (
    anchor_sort_key,
    bar_beat_to_offset,
    build_stacked_lyric,
    get_bass_articulation,
    get_beats_per_bar,
    get_expansion_for_bar,
    get_function_for_bar,
    get_lead_voice_for_bar,
    get_passage_end_offset,
)
from builder.types import (
    Anchor, AffectConfig, FormConfig, GenreConfig, KeyConfig,
    Note, NoteFile, PassageAssignment, VoiceExpansionConfig,
)
from shared.constants import (
    DEFAULT_TESSITURA_MEDIANS,
    STACCATO_DURATION_THRESHOLD,
    VOICE_RANGES,
)
from shared.pitch import select_octave
from shared.tracer import get_tracer


def _infer_direction(from_degree: int, to_degree: int) -> str:
    """Infer voice-leading direction from consecutive degrees.

    Uses shortest path: if interval is 1-3 steps, go that way.
    If 4-6 steps, go the opposite way (shorter path wrapping).

    Args:
        from_degree: Starting degree (1-7)
        to_degree: Target degree (1-7)

    Returns:
        "up", "down", or "same"
    """
    if from_degree == to_degree:
        return "same"
    diff = to_degree - from_degree
    # Normalize to -3..+3 range (shortest path)
    if diff > 3:
        diff -= 7  # e.g., 1→6 = +5 → -2 (down)
    elif diff < -3:
        diff += 7  # e.g., 6→1 = -5 → +2 (up)
    return "up" if diff > 0 else "down"


SCHEMA_STAGE_COUNTS: dict[str, int] = {
    "prinner": 4,
    "romanesca": 6,
    "fonte": 2,
    "monte": 2,
    "cadenza_semplice": 3,
    "cadenza_composta": 4,
}

SCHEMAS_NEEDING_SUSTAINED_FINAL: frozenset[str] = frozenset({"prinner", "romanesca"})


def _is_schema_final_stage(schema: str | None, stage: int) -> bool:
    """Check if this is the final stage of a schema that needs sustained bass."""
    if schema is None:
        return False
    if schema not in SCHEMAS_NEEDING_SUSTAINED_FINAL:
        return False
    total_stages = SCHEMA_STAGE_COUNTS.get(schema)
    if total_stages is None:
        return False
    return stage == total_stages


def realise_with_figuration(
    anchors: Sequence[Anchor],
    passage_assignments: Sequence[PassageAssignment] | None,
    key_config: KeyConfig,
    affect_config: AffectConfig,
    genre_config: GenreConfig,
    form_config: FormConfig,
    total_bars: int,
    seed: int = 42,
    tempo_override: int | None = None,
) -> NoteFile:
    """Convert anchors to notes using baroque figuration patterns."""
    from builder.figuration.figurate import figurate
    from builder.figuration.bass import get_bass_pattern, realise_bass_pattern
    tracer = get_tracer()
    expansions: dict[str, VoiceExpansionConfig] = load_expansions()
    if not anchors:
        return NoteFile(soprano=(), bass=(), metre=genre_config.metre, tempo=72, upbeat=genre_config.upbeat)
    key = anchors[0].local_key
    density = affect_config.density
    character = "plain"
    if density == "high":
        character = "energetic"
    elif density == "medium":
        character = "expressive"
    tracer.L6("Figuration", density=density, character=character, anchor_count=len(anchors))
    figured_bars = figurate(
        anchors=anchors,
        key=key,
        metre=genre_config.metre,
        seed=seed,
        density=density,
        affect_character=character,
        passage_assignments=passage_assignments,
    )
    soprano_notes: list[Note] = []
    bass_notes: list[Note] = []
    sorted_anchors: list[Anchor] = sorted(anchors, key=anchor_sort_key)
    beats_per_bar: int = get_beats_per_bar(genre_config.metre)
    soprano_median: int = DEFAULT_TESSITURA_MEDIANS[0]
    bass_median: int = DEFAULT_TESSITURA_MEDIANS[3]
    end_offset: Fraction = Fraction(total_bars * beats_per_bar, 4)
    prev_soprano: int | None = None
    prev_soprano_degree: int | None = None  # Track degree for cross-bar direction
    prev_function: str | None = None
    prev_expansion_name: str | None = None
    prev_section: str | None = None
    beat_value: Fraction = Fraction(1, int(genre_config.metre.split("/")[1]))
    anchor_idx: int = 0
    for figured_bar in figured_bars:
        bar: int = figured_bar.bar
        # Anacrusis (bar 0) uses negative offset
        if bar == 0:
            current_offset = -sum(figured_bar.durations)
            first_bar_offset = current_offset
            anchor_for_key = sorted_anchors[0] if sorted_anchors else None
        else:
            if anchor_idx >= len(sorted_anchors):
                break
            anchor_for_key = sorted_anchors[anchor_idx]
            bar_offset: Fraction = bar_beat_to_offset(anchor_for_key.bar_beat, beats_per_bar)
            # Use start_beat from figured bar (computed during figuration)
            current_offset = bar_offset + (figured_bar.start_beat - 1) * beat_value
            first_bar_offset = current_offset
            anchor_idx += 1
        assert anchor_for_key is not None, "No anchor for soprano note"
        function: str | None = get_function_for_bar(bar, passage_assignments)
        expansion: VoiceExpansionConfig = get_expansion_for_bar(
            bar=bar,
            assignments=passage_assignments,
            genre_config=genre_config,
            expansions=expansions,
        )
        expansion_name: str = expansion.name
        tracer.figure_selection(bar, figured_bar.figure_name or "none", density)
        tracer.expansion(bar, function or "none", expansion_name)
        degrees = figured_bar.degrees
        for j, (degree, duration) in enumerate(zip(degrees, figured_bar.durations)):
            # Infer direction from previous degree
            if j == 0 and prev_soprano is None:
                direction = None  # Very first note - use median
            elif j > 0:
                direction = _infer_direction(degrees[j - 1], degree)
            elif prev_soprano_degree is not None:
                # First note of bar, have previous bar's last degree
                direction = _infer_direction(prev_soprano_degree, degree)
            else:
                direction = None
            s_midi: int = select_octave(
                anchor_for_key.local_key, degree, soprano_median,
                prev_pitch=None if j == 0 and prev_soprano is None else prev_soprano,
                direction=direction,
                voice_range=VOICE_RANGES[0],
            )
            prev_soprano = s_midi
            prev_soprano_degree = degree  # Track for next iteration
            if current_offset == first_bar_offset:
                schema_part: str | None = anchor_for_key.schema if anchor_for_key.stage == 1 else None
                function_part: str | None = function if function != prev_function else None
                exp_part: str | None = expansion_name if expansion_name != prev_expansion_name else None
                section_part: str | None = anchor_for_key.section if anchor_for_key.section != prev_section else None
                prev_function = function
                prev_expansion_name = expansion_name
                prev_section = anchor_for_key.section
                figure_part: str | None = figured_bar.figure_name
                lyric = build_stacked_lyric(section_part, schema_part, function_part, figure_part)
                if exp_part and lyric:
                    lyric = f"{lyric}[{exp_part}]"
                elif exp_part:
                    lyric = f"[{exp_part}]"
            else:
                lyric = ""
            soprano_notes.append(Note(
                offset=current_offset,
                pitch=s_midi,
                duration=duration,
                voice=0,
                lyric=lyric,
            ))
            tracer.note_output("soprano", current_offset, s_midi, duration)
            current_offset += duration
    if sorted_anchors:
        final_anchor = sorted_anchors[-1]
        final_offset: Fraction = bar_beat_to_offset(final_anchor.bar_beat, beats_per_bar)
        final_duration: Fraction = end_offset - final_offset
        if final_duration > 0:
            s_midi = select_octave(
                final_anchor.local_key, final_anchor.upper_degree, soprano_median, prev_soprano,
                voice_range=VOICE_RANGES[0],
            )
            soprano_notes.append(Note(
                offset=final_offset,
                pitch=s_midi,
                duration=final_duration,
                voice=0,
                lyric="",
            ))
    bar_duration = Fraction(beats_per_bar, 4)
    if genre_config.bass_treatment == "contrapuntal":
        from builder.figuration.bass_figurate import figurate_bass
        bass_figured_bars = figurate_bass(
            anchors=anchors,
            metre=genre_config.metre,
            seed=seed + 1000,
            density=density,
            passage_assignments=passage_assignments,
        )
        prev_bass: int | None = None
        prev_bass_degree: int | None = None  # Track degree for cross-bar direction
        bar_duration: Fraction = Fraction(beats_per_bar, 4)
        bass_beat_value: Fraction = Fraction(1, int(genre_config.metre.split("/")[1]))
        anchor_idx: int = 0
        for figured_bar in bass_figured_bars:
            bar: int = figured_bar.bar
            # Anacrusis (bar 0) uses negative offset
            if bar == 0:
                current_offset = -sum(figured_bar.durations)
                anchor_for_key = sorted_anchors[0] if sorted_anchors else None
            else:
                if anchor_idx >= len(sorted_anchors):
                    break
                anchor_for_key = sorted_anchors[anchor_idx]
                bar_offset: Fraction = bar_beat_to_offset(anchor_for_key.bar_beat, beats_per_bar)
                # Use start_beat from figured bar (computed during figuration)
                current_offset = bar_offset + (figured_bar.start_beat - 1) * bass_beat_value
                anchor_idx += 1
            assert anchor_for_key is not None, "No anchor for bass note"
            short_note_count: int = sum(
                1 for d in figured_bar.durations if d <= STACCATO_DURATION_THRESHOLD
            )
            is_run: bool = short_note_count >= 3
            passage_end: Fraction | None = get_passage_end_offset(
                bar, passage_assignments, beats_per_bar,
            )
            bass_degrees = figured_bar.degrees
            for j, (degree, dur) in enumerate(zip(bass_degrees, figured_bar.durations)):
                # Infer direction from previous degree
                if j == 0 and prev_bass is None:
                    direction = None  # Very first note - use median
                elif j > 0:
                    direction = _infer_direction(bass_degrees[j - 1], degree)
                elif prev_bass_degree is not None:
                    # First note of bar, have previous bar's last degree
                    direction = _infer_direction(prev_bass_degree, degree)
                else:
                    direction = None
                b_midi: int = select_octave(
                    anchor_for_key.local_key, degree, bass_median,
                    prev_pitch=None if j == 0 and prev_bass is None else prev_bass,
                    direction=direction,
                    voice_range=VOICE_RANGES[3],
                )
                prev_bass = b_midi
                prev_bass_degree = degree  # Track for next iteration
                # Truncate duration at passage boundary to avoid overlap
                note_dur = dur
                if passage_end is not None and current_offset >= 0:
                    max_duration = passage_end - current_offset
                    if max_duration > 0 and note_dur > max_duration:
                        note_dur = max_duration
                articulation: str = get_bass_articulation(note_dur, is_run)
                bass_notes.append(Note(
                    offset=current_offset,
                    pitch=b_midi,
                    duration=note_dur,
                    voice=3,
                    lyric=articulation,
                ))
                tracer.note_output("bass", current_offset, b_midi, note_dur)
                current_offset += dur  # Advance by original dur for next note timing
        if sorted_anchors:
            final_anchor = sorted_anchors[-1]
            final_offset_bass: Fraction = bar_beat_to_offset(final_anchor.bar_beat, beats_per_bar)
            final_duration_bass: Fraction = end_offset - final_offset_bass
            if final_duration_bass > 0:
                b_midi = select_octave(
                    final_anchor.local_key, final_anchor.lower_degree, bass_median, prev_bass,
                    voice_range=VOICE_RANGES[3],
                )
                bass_notes.append(Note(
                    offset=final_offset_bass,
                    pitch=b_midi,
                    duration=final_duration_bass,
                    voice=3,
                    lyric="",
                ))
    elif genre_config.bass_mode == "schema":
        from builder.figuration.bass import get_rhythm_pattern, realise_bass_schema
        rhythm_pattern = get_rhythm_pattern(genre_config.bass_pattern)
        assert rhythm_pattern is not None, f"Rhythm pattern '{genre_config.bass_pattern}' not found"
        sustained_pattern = get_rhythm_pattern("sustained")
        prev_bass: int | None = None
        for i, anchor in enumerate(sorted_anchors):
            offset: Fraction = bar_beat_to_offset(anchor.bar_beat, beats_per_bar)
            if i < len(sorted_anchors) - 1:
                next_offset: Fraction = bar_beat_to_offset(sorted_anchors[i + 1].bar_beat, beats_per_bar)
                duration: Fraction = next_offset - offset
                next_degree: int | None = sorted_anchors[i + 1].lower_degree
            else:
                duration = end_offset - offset
                next_degree = None
            pattern = rhythm_pattern
            if _is_schema_final_stage(anchor.schema, anchor.stage):
                if sustained_pattern is not None:
                    pattern = sustained_pattern
            bar: int = int(anchor.bar_beat.split(".")[0])
            tracer.bass_pattern(bar, pattern.name, anchor.lower_degree)
            metre_matches = pattern.metre == genre_config.metre or pattern.metre == "any"
            if metre_matches and duration >= bar_duration:
                pattern_notes = realise_bass_schema(
                    pattern=pattern,
                    current_degree=anchor.lower_degree,
                    next_degree=next_degree,
                    key=anchor.local_key,
                    bar_offset=offset,
                    bar_duration=bar_duration,
                    bass_median=bass_median,
                    prev_pitch=prev_bass,
                )
                for note_offset, midi_pitch, note_duration in pattern_notes:
                    bass_notes.append(Note(
                        offset=note_offset,
                        pitch=midi_pitch,
                        duration=note_duration,
                        voice=3,
                        lyric="",
                    ))
                    tracer.note_output("bass", note_offset, midi_pitch, note_duration)
                    prev_bass = midi_pitch
            else:
                b_midi: int = select_octave(
                    anchor.local_key, anchor.lower_degree, bass_median, prev_bass,
                    voice_range=VOICE_RANGES[3],
                )
                prev_bass = b_midi
                bass_notes.append(Note(
                    offset=offset,
                    pitch=b_midi,
                    duration=duration,
                    voice=3,
                    lyric="",
                ))
    else:
        default_pattern = get_bass_pattern(genre_config.bass_pattern)
        assert default_pattern is not None, f"Bass pattern '{genre_config.bass_pattern}' not found"
        cadence_pattern = get_bass_pattern("continuo_sustained")
        prev_bass: int | None = None
        prev_prev_bass: int | None = None
        for i, anchor in enumerate(sorted_anchors):
            offset: Fraction = bar_beat_to_offset(anchor.bar_beat, beats_per_bar)
            if i < len(sorted_anchors) - 1:
                next_offset: Fraction = bar_beat_to_offset(sorted_anchors[i + 1].bar_beat, beats_per_bar)
                duration: Fraction = next_offset - offset
            else:
                duration = end_offset - offset
            bass_pattern = default_pattern
            if _is_schema_final_stage(anchor.schema, anchor.stage):
                if cadence_pattern is not None:
                    bass_pattern = cadence_pattern
            bar: int = int(anchor.bar_beat.split(".")[0])
            tracer.bass_pattern(bar, bass_pattern.name, anchor.lower_degree)
            metre_matches = bass_pattern.metre == genre_config.metre or bass_pattern.metre == "any"
            if metre_matches and duration >= bar_duration:
                pattern_notes = realise_bass_pattern(
                    pattern=bass_pattern,
                    bass_degree=anchor.lower_degree,
                    key=anchor.local_key,
                    bar_offset=offset,
                    bar_duration=bar_duration,
                    bass_median=bass_median,
                    prev_pitch=prev_bass,
                    prev_prev_pitch=prev_prev_bass,
                )
                for note_offset, midi_pitch, note_duration in pattern_notes:
                    bass_notes.append(Note(
                        offset=note_offset,
                        pitch=midi_pitch,
                        duration=note_duration,
                        voice=3,
                        lyric="",
                    ))
                    tracer.note_output("bass", note_offset, midi_pitch, note_duration)
                    prev_prev_bass = prev_bass
                    prev_bass = midi_pitch
            else:
                b_midi: int = select_octave(
                    anchor.local_key, anchor.lower_degree, bass_median, prev_bass,
                    voice_range=VOICE_RANGES[3],
                )
                prev_prev_bass = prev_bass
                prev_bass = b_midi
                bass_notes.append(Note(
                    offset=offset,
                    pitch=b_midi,
                    duration=duration,
                    voice=3,
                    lyric="",
                ))
    # Adjust bass at downbeats to ensure consonance with soprano
    if bass_notes and soprano_notes:
        bass_notes = adjust_downbeat_consonance(
            soprano_notes=soprano_notes,
            bass_notes=bass_notes,
            beats_per_bar=beats_per_bar,
            total_bars=total_bars,
            bass_range=VOICE_RANGES[3],
        )

    if tempo_override is not None:
        tempo = tempo_override
    else:
        tempo = genre_config.tempo + affect_config.tempo_modifier

    # Shift all offsets to eliminate negative values
    min_offset = Fraction(0)
    for note in soprano_notes:
        if note.offset < min_offset:
            min_offset = note.offset
    for note in bass_notes:
        if note.offset < min_offset:
            min_offset = note.offset
    if min_offset < 0:
        shift = -min_offset  # Convert negative to positive shift
        soprano_notes = [
            Note(
                offset=n.offset + shift,
                pitch=n.pitch,
                duration=n.duration,
                voice=n.voice,
                lyric=n.lyric,
            )
            for n in soprano_notes
        ]
        bass_notes = [
            Note(
                offset=n.offset + shift,
                pitch=n.pitch,
                duration=n.duration,
                voice=n.voice,
                lyric=n.lyric,
            )
            for n in bass_notes
        ]

    return NoteFile(
        soprano=tuple(soprano_notes),
        bass=tuple(bass_notes),
        metre=genre_config.metre,
        tempo=tempo,
        upbeat=genre_config.upbeat,
    )
