"""Realisation: Turn anchors into notes.

Category A: Pure functions, no I/O, no validation.

Canonical design: Anchors store degrees + key. MIDI conversion happens here.
Each anchor becomes a note; duration extends to next anchor.

Layer 6.5 (Figuration) can be enabled to produce baroque melodic patterns
instead of simple block-chord output.
"""
from fractions import Fraction
from typing import Sequence

from builder.types import (
    Anchor, AffectConfig, FormConfig, GenreConfig, KeyConfig,
    Note, NoteFile, TreatmentAssignment,
)
from shared.constants import DEFAULT_TESSITURA_MEDIANS
from shared.pitch import select_octave


def _get_treatment_for_bar(
    bar: int,
    assignments: Sequence[TreatmentAssignment] | None,
) -> str | None:
    """Look up treatment name for a given bar number."""
    if assignments is None:
        return None
    for assignment in assignments:
        if assignment.start_bar <= bar <= assignment.end_bar:
            return assignment.treatment
    return None


def _build_stacked_lyric(
    schema: str | None,
    treatment: str | None,
    figure: str | None,
) -> str:
    """Build stacked lyric from schema, treatment, and figure name.
    
    Format: schema/treatment/figure (omitting empty parts).
    Only includes parts that are present and non-empty.
    """
    parts: list[str] = []
    if schema:
        parts.append(schema)
    if treatment:
        parts.append(treatment)
    if figure:
        parts.append(figure)
    return "/".join(parts)


def _realise(
    anchors: Sequence[Anchor],
    treatment_assignments: Sequence[TreatmentAssignment] | None,
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
    prev_treatment: str | None = None
    for i, anchor in enumerate(sorted_anchors):
        offset: Fraction = _bar_beat_to_offset(anchor.bar_beat, beats_per_bar)
        if i < len(sorted_anchors) - 1:
            next_offset: Fraction = _bar_beat_to_offset(sorted_anchors[i + 1].bar_beat, beats_per_bar)
            duration: Fraction = next_offset - offset
        else:
            duration = end_offset - offset
        s_midi: int = select_octave(
            anchor.local_key, anchor.soprano_degree, soprano_median, prev_soprano,
        )
        b_midi: int = select_octave(
            anchor.local_key, anchor.bass_degree, bass_median, prev_bass,
        )
        prev_soprano = s_midi
        prev_bass = b_midi
        bar: int = int(anchor.bar_beat.split(".")[0])
        treatment: str | None = _get_treatment_for_bar(bar, treatment_assignments)
        schema_part: str | None = anchor.schema if anchor.stage == 1 else None
        treatment_part: str | None = treatment if treatment != prev_treatment else None
        prev_treatment = treatment
        lyric: str = _build_stacked_lyric(schema_part, treatment_part, None)
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
    )


def _anchor_sort_key(anchor: Anchor) -> tuple[float, int]:
    """Sort key for anchors: by time, then by soprano degree."""
    parts: list[str] = anchor.bar_beat.split(".")
    bar: int = int(parts[0])
    beat: float = float(parts[1]) if len(parts) > 1 else 1.0
    return (bar + beat / 10.0, anchor.soprano_degree)


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


def realise_with_figuration(
    anchors: Sequence[Anchor],
    treatment_assignments: Sequence[TreatmentAssignment] | None,
    key_config: KeyConfig,
    affect_config: AffectConfig,
    genre_config: GenreConfig,
    form_config: FormConfig,
    total_bars: int,
    seed: int = 42,
) -> NoteFile:
    """Convert anchors to notes using baroque figuration patterns.

    This function uses the Layer 6.5 figuration system to produce
    idiomatic melodic motion instead of simple whole-note output.
    Soprano uses melodic figures; bass uses accompaniment patterns.

    Args:
        anchors: Schema arrivals with degrees
        treatment_assignments: Voice role assignments (optional)
        key_config: Key configuration
        affect_config: Affect configuration
        genre_config: Genre configuration
        form_config: Form configuration
        total_bars: Total bars in piece
        seed: RNG seed for deterministic output

    Returns:
        NoteFile with figured soprano and bass.
    """
    from builder.figuration.figurate import figurate
    if not anchors:
        return NoteFile(soprano=(), bass=(), metre=genre_config.metre, tempo=72)
    key = anchors[0].local_key
    density = affect_config.density
    character = "plain"
    if density == "high":
        character = "energetic"
    elif density == "medium":
        character = "expressive"
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
    prev_treatment: str | None = None
    for i, figured_bar in enumerate(figured_bars):
        if i >= len(sorted_anchors):
            break
        anchor = sorted_anchors[i]
        bar: int = int(anchor.bar_beat.split(".")[0])
        bar_offset: Fraction = _bar_beat_to_offset(anchor.bar_beat, beats_per_bar)
        current_offset = bar_offset
        treatment: str | None = _get_treatment_for_bar(bar, treatment_assignments)
        for j, (degree, duration) in enumerate(zip(figured_bar.degrees, figured_bar.durations)):
            s_midi: int = select_octave(
                anchor.local_key, degree, soprano_median,
                prev_pitch=None if j == 0 and prev_soprano is None else prev_soprano,
            )
            prev_soprano = s_midi
            if current_offset == bar_offset:
                schema_part: str | None = anchor.schema if anchor.stage == 1 else None
                treatment_part: str | None = treatment if treatment != prev_treatment else None
                prev_treatment = treatment
                figure_part: str | None = figured_bar.figure_name
                lyric = _build_stacked_lyric(schema_part, treatment_part, figure_part)
            else:
                lyric = ""
            soprano_notes.append(Note(
                offset=current_offset,
                pitch=s_midi,
                duration=duration,
                voice=0,
                lyric=lyric,
            ))
            current_offset += duration
    if sorted_anchors:
        final_anchor = sorted_anchors[-1]
        final_offset: Fraction = _bar_beat_to_offset(final_anchor.bar_beat, beats_per_bar)
        final_duration: Fraction = end_offset - final_offset
        if final_duration > 0:
            s_midi = select_octave(
                final_anchor.local_key, final_anchor.soprano_degree, soprano_median, prev_soprano,
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
                current_offset += dur
        if sorted_anchors:
            final_anchor = sorted_anchors[-1]
            final_offset_bass: Fraction = _bar_beat_to_offset(final_anchor.bar_beat, beats_per_bar)
            final_duration_bass: Fraction = end_offset - final_offset_bass
            if final_duration_bass > 0:
                b_midi = select_octave(
                    final_anchor.local_key, final_anchor.bass_degree, bass_median, prev_bass,
                )
                bass_notes.append(Note(
                    offset=final_offset_bass,
                    pitch=b_midi,
                    duration=final_duration_bass,
                    voice=3,
                    lyric="",
                ))
    else:
        from builder.figuration.bass import get_bass_pattern, realise_bass_pattern
        bass_pattern = get_bass_pattern(genre_config.bass_pattern)
        assert bass_pattern is not None, f"Bass pattern '{genre_config.bass_pattern}' not found"
        prev_bass: int | None = None
        for i, anchor in enumerate(sorted_anchors):
            offset: Fraction = _bar_beat_to_offset(anchor.bar_beat, beats_per_bar)
            if i < len(sorted_anchors) - 1:
                next_offset: Fraction = _bar_beat_to_offset(sorted_anchors[i + 1].bar_beat, beats_per_bar)
                duration: Fraction = next_offset - offset
            else:
                duration = end_offset - offset
            metre_matches = bass_pattern.metre == genre_config.metre or bass_pattern.metre == "any"
            if metre_matches and duration >= bar_duration:
                pattern_notes = realise_bass_pattern(
                    pattern=bass_pattern,
                    bass_degree=anchor.bass_degree,
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
                    prev_bass = midi_pitch
            else:
                b_midi: int = select_octave(
                    anchor.local_key, anchor.bass_degree, bass_median, prev_bass,
                )
                prev_bass = b_midi
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
    )
