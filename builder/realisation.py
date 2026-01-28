"""Realisation: Turn anchors into notes.

Category A: Pure functions, no I/O, no validation.

Canonical design: Anchors store degrees + key. MIDI conversion happens here.
Each anchor becomes a note; duration extends to next anchor.

Layer 6.5 (Figuration) can be enabled to produce baroque melodic patterns
instead of simple block-chord output.
"""
from fractions import Fraction
from typing import Sequence

from builder.config_loader import get_expansion_for_function, load_expansions
from builder.types import (
    Anchor, AffectConfig, FormConfig, GenreConfig, KeyConfig,
    Note, NoteFile, PassageAssignment, VoiceExpansionConfig,
)
from shared.constants import DEFAULT_TESSITURA_MEDIANS
from shared.pitch import select_octave
from shared.tracer import get_tracer


def _get_function_for_bar(
    bar: int,
    assignments: Sequence[PassageAssignment] | None,
) -> str | None:
    """Look up passage function for a given bar number."""
    if assignments is None:
        return None
    for assignment in assignments:
        if assignment.start_bar <= bar <= assignment.end_bar:
            return assignment.function
    return None


def _get_expansion_for_bar(
    bar: int,
    assignments: Sequence[PassageAssignment] | None,
    genre_config: GenreConfig,
    expansions: dict[str, VoiceExpansionConfig],
) -> VoiceExpansionConfig:
    """Get voice expansion config for a given bar."""
    function: str | None = _get_function_for_bar(bar, assignments)
    if function is None:
        function = "episode"
    return get_expansion_for_function(
        function=function,
        function_map=genre_config.function_map,
        expansions=expansions,
    )


def _build_stacked_lyric(
    section: str | None,
    schema: str | None,
    function: str | None,
    figure: str | None,
) -> str:
    """Build stacked lyric from section, schema, passage function, and figure name."""
    parts: list[str] = []
    if section:
        parts.append(section)
    if schema:
        parts.append(schema)
    if function:
        parts.append(function)
    if figure:
        parts.append(figure)
    return "/".join(parts)


def _realise(
    anchors: Sequence[Anchor],
    passage_assignments: Sequence[PassageAssignment] | None,
    key_config: KeyConfig,
    affect_config: AffectConfig,
    genre_config: GenreConfig,
    form_config: FormConfig,
    total_bars: int,
) -> NoteFile:
    """Convert anchors to notes with gravitational voice leading."""
    soprano_notes: list[Note] = []
    bass_notes: list[Note] = []
    sorted_anchors: list[Anchor] = sorted(anchors, key=_anchor_sort_key)
    beats_per_bar: int = _get_beats_per_bar(genre_config.metre)
    end_offset: Fraction = Fraction(total_bars * beats_per_bar, 4)
    soprano_median: int = DEFAULT_TESSITURA_MEDIANS[0]
    bass_median: int = DEFAULT_TESSITURA_MEDIANS[3]
    prev_soprano: int | None = None
    prev_bass: int | None = None
    prev_function: str | None = None
    prev_section: str | None = None
    for i, anchor in enumerate(sorted_anchors):
        offset: Fraction = _bar_beat_to_offset(anchor.bar_beat, beats_per_bar)
        if i < len(sorted_anchors) - 1:
            next_offset: Fraction = _bar_beat_to_offset(sorted_anchors[i + 1].bar_beat, beats_per_bar)
            duration: Fraction = next_offset - offset
        else:
            duration = end_offset - offset
        s_midi: int = select_octave(
            anchor.local_key, anchor.upper_degree, soprano_median, prev_soprano,
        )
        b_midi: int = select_octave(
            anchor.local_key, anchor.lower_degree, bass_median, prev_bass,
        )
        prev_soprano = s_midi
        prev_bass = b_midi
        bar: int = int(anchor.bar_beat.split(".")[0])
        function: str | None = _get_function_for_bar(bar, passage_assignments)
        schema_part: str | None = anchor.schema if anchor.stage == 1 else None
        function_part: str | None = function if function != prev_function else None
        section_part: str | None = anchor.section if anchor.section != prev_section else None
        prev_function = function
        prev_section = anchor.section
        lyric: str = _build_stacked_lyric(section_part, schema_part, function_part, None)
        soprano_notes.append(Note(
            offset=offset,
            pitch=s_midi,
            duration=duration,
            voice=0,
            lyric=lyric,
        ))
        bass_notes.append(Note(
            offset=offset,
            pitch=b_midi,
            duration=duration,
            voice=3,
            lyric="",
        ))
    tempo: int = genre_config.tempo + affect_config.tempo_modifier
    return NoteFile(
        soprano=tuple(soprano_notes),
        bass=tuple(bass_notes),
        metre=genre_config.metre,
        tempo=tempo,
        upbeat=genre_config.upbeat,
    )


def _anchor_sort_key(anchor: Anchor) -> tuple[float, int]:
    """Sort key for anchors: by time, then by upper degree."""
    parts: list[str] = anchor.bar_beat.split(".")
    bar: int = int(parts[0])
    beat: float = float(parts[1]) if len(parts) > 1 else 1.0
    return (bar + beat / 10.0, anchor.upper_degree)


def _get_beats_per_bar(metre: str) -> int:
    """Extract beats per bar from metre string."""
    num_str: str = metre.split("/")[0]
    return int(num_str)


def _bar_beat_to_offset(bar_beat: str, beats_per_bar: int) -> Fraction:
    """Convert bar.beat string to Fraction offset in whole notes."""
    parts: list[str] = bar_beat.split(".")
    bar: int = int(parts[0])
    beat: float = float(parts[1]) if len(parts) > 1 else 1.0
    offset_in_beats: Fraction = Fraction(bar - 1) * beats_per_bar + Fraction(beat) - 1
    return offset_in_beats / 4


def _shift_notes_by_upbeat(notes: list[Note], upbeat: Fraction) -> list[Note]:
    """Shift all note offsets forward by the upbeat amount."""
    if upbeat == 0:
        return notes
    return [
        Note(
            offset=note.offset + upbeat,
            pitch=note.pitch,
            duration=note.duration,
            voice=note.voice,
            lyric=note.lyric,
        )
        for note in notes
    ]


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
    )
    soprano_notes: list[Note] = []
    bass_notes: list[Note] = []
    sorted_anchors: list[Anchor] = sorted(anchors, key=_anchor_sort_key)
    beats_per_bar: int = _get_beats_per_bar(genre_config.metre)
    soprano_median: int = DEFAULT_TESSITURA_MEDIANS[0]
    bass_median: int = DEFAULT_TESSITURA_MEDIANS[3]
    end_offset: Fraction = Fraction(total_bars * beats_per_bar, 4)
    prev_soprano: int | None = None
    prev_function: str | None = None
    prev_expansion_name: str | None = None
    prev_section: str | None = None
    for i, figured_bar in enumerate(figured_bars):
        if i >= len(sorted_anchors):
            break
        anchor = sorted_anchors[i]
        bar: int = int(anchor.bar_beat.split(".")[0])
        bar_offset: Fraction = _bar_beat_to_offset(anchor.bar_beat, beats_per_bar)
        current_offset = bar_offset
        function: str | None = _get_function_for_bar(bar, passage_assignments)
        expansion: VoiceExpansionConfig = _get_expansion_for_bar(
            bar=bar,
            assignments=passage_assignments,
            genre_config=genre_config,
            expansions=expansions,
        )
        expansion_name: str = expansion.name
        tracer.figure_selection(bar, figured_bar.figure_name or "none", density)
        tracer.expansion(bar, function or "none", expansion_name)
        for j, (degree, duration) in enumerate(zip(figured_bar.degrees, figured_bar.durations)):
            s_midi: int = select_octave(
                anchor.local_key, degree, soprano_median,
                prev_pitch=None if j == 0 and prev_soprano is None else prev_soprano,
            )
            prev_soprano = s_midi
            if current_offset == bar_offset:
                schema_part: str | None = anchor.schema if anchor.stage == 1 else None
                function_part: str | None = function if function != prev_function else None
                exp_part: str | None = expansion_name if expansion_name != prev_expansion_name else None
                section_part: str | None = anchor.section if anchor.section != prev_section else None
                prev_function = function
                prev_expansion_name = expansion_name
                prev_section = anchor.section
                figure_part: str | None = figured_bar.figure_name
                lyric = _build_stacked_lyric(section_part, schema_part, function_part, figure_part)
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
        final_offset: Fraction = _bar_beat_to_offset(final_anchor.bar_beat, beats_per_bar)
        final_duration: Fraction = end_offset - final_offset
        if final_duration > 0:
            s_midi = select_octave(
                final_anchor.local_key, final_anchor.upper_degree, soprano_median, prev_soprano,
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
        bass_figured_bars = figurate(
            anchors=anchors,
            key=key,
            metre=genre_config.metre,
            seed=seed + 1000,
            density=density,
            affect_character=character,
            voice="bass",
        )
        prev_bass: int | None = None
        for i, figured_bar in enumerate(bass_figured_bars):
            if i >= len(sorted_anchors):
                break
            anchor = sorted_anchors[i]
            bar_offset: Fraction = _bar_beat_to_offset(anchor.bar_beat, beats_per_bar)
            current_offset = bar_offset
            for j, (degree, dur) in enumerate(zip(figured_bar.degrees, figured_bar.durations)):
                b_midi: int = select_octave(
                    anchor.local_key, degree, bass_median,
                    prev_pitch=None if j == 0 and prev_bass is None else prev_bass,
                )
                prev_bass = b_midi
                bass_notes.append(Note(
                    offset=current_offset,
                    pitch=b_midi,
                    duration=dur,
                    voice=3,
                    lyric="",
                ))
                tracer.note_output("bass", current_offset, b_midi, dur)
                current_offset += dur
        if sorted_anchors:
            final_anchor = sorted_anchors[-1]
            final_offset_bass: Fraction = _bar_beat_to_offset(final_anchor.bar_beat, beats_per_bar)
            final_duration_bass: Fraction = end_offset - final_offset_bass
            if final_duration_bass > 0:
                b_midi = select_octave(
                    final_anchor.local_key, final_anchor.lower_degree, bass_median, prev_bass,
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
            offset: Fraction = _bar_beat_to_offset(anchor.bar_beat, beats_per_bar)
            if i < len(sorted_anchors) - 1:
                next_offset: Fraction = _bar_beat_to_offset(sorted_anchors[i + 1].bar_beat, beats_per_bar)
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
            offset: Fraction = _bar_beat_to_offset(anchor.bar_beat, beats_per_bar)
            if i < len(sorted_anchors) - 1:
                next_offset: Fraction = _bar_beat_to_offset(sorted_anchors[i + 1].bar_beat, beats_per_bar)
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
    if tempo_override is not None:
        tempo = tempo_override
    else:
        tempo = genre_config.tempo + affect_config.tempo_modifier
    return NoteFile(
        soprano=tuple(soprano_notes),
        bass=tuple(bass_notes),
        metre=genre_config.metre,
        tempo=tempo,
        upbeat=genre_config.upbeat,
    )
