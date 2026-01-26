"""Realisation: Turn anchors directly into notes.

Category A: Pure functions, no I/O, no validation.

Canonical design: Anchors are the source of truth.
Each anchor becomes a note; duration extends to next anchor.
No slot expansion, no merging.
"""
from fractions import Fraction
from typing import Sequence

from builder.types import (
    Anchor, AffectConfig, FormConfig, GenreConfig, KeyConfig,
    Note, NoteFile, TreatmentAssignment,
)


def realise(
    anchors: Sequence[Anchor],
    treatment_assignments: Sequence[TreatmentAssignment] | None,
    key_config: KeyConfig,
    affect_config: AffectConfig,
    genre_config: GenreConfig,
    form_config: FormConfig,
) -> NoteFile:
    """Convert anchors directly to notes.

    Each anchor produces one soprano note and one bass note.
    Duration extends from this anchor to the next.

    Args:
        anchors: Anchors from L4 metric layer
        treatment_assignments: Unused, kept for interface compatibility
        key_config: Key configuration (unused, kept for interface)
        affect_config: Affect configuration (for tempo modifier)
        genre_config: Genre configuration (for tempo range, metre)
        form_config: Form configuration (unused, kept for interface)

    Returns:
        NoteFile with soprano and bass notes
    """
    soprano_notes: list[Note] = []
    bass_notes: list[Note] = []
    sorted_anchors: list[Anchor] = sorted(anchors, key=_anchor_sort_key)
    total_bars: int = form_config.minimum_bars
    beats_per_bar: int = _get_beats_per_bar(genre_config.metre)
    end_offset: Fraction = Fraction(total_bars * beats_per_bar, 4)
    for i, anchor in enumerate(sorted_anchors):
        offset: Fraction = _bar_beat_to_offset(anchor.bar_beat, beats_per_bar)
        if i < len(sorted_anchors) - 1:
            next_offset: Fraction = _bar_beat_to_offset(sorted_anchors[i + 1].bar_beat, beats_per_bar)
            duration: Fraction = next_offset - offset
        else:
            duration = end_offset - offset
        if anchor.stage == 1:
            lyric: str = anchor.schema
        else:
            lyric = ""
        soprano_notes.append(Note(
            offset=offset,
            pitch=anchor.soprano_midi,
            duration=duration,
            voice=0,
            lyric=lyric,
        ))
        bass_notes.append(Note(
            offset=offset,
            pitch=anchor.bass_midi,
            duration=duration,
            voice=3,
            lyric="",
        ))
    tempo_range: list[int] = genre_config.rhythmic_vocabulary.get("tempo_range", [72, 88])
    tempo_base: int = (tempo_range[0] + tempo_range[1]) // 2
    tempo: int = tempo_base + affect_config.tempo_modifier
    return NoteFile(
        soprano=tuple(soprano_notes),
        bass=tuple(bass_notes),
        metre=genre_config.metre,
        tempo=tempo,
    )


def _anchor_sort_key(anchor: Anchor) -> tuple[float, int]:
    """Sort key for anchors: by time, then by soprano pitch."""
    parts: list[str] = anchor.bar_beat.split(".")
    bar: int = int(parts[0])
    beat: float = float(parts[1]) if len(parts) > 1 else 1.0
    return (bar + beat / 10.0, anchor.soprano_midi)


def _get_beats_per_bar(metre: str) -> int:
    """Extract beats per bar from metre string."""
    num_str: str = metre.split("/")[0]
    return int(num_str)


def _bar_beat_to_offset(bar_beat: str, beats_per_bar: int) -> Fraction:
    """Convert bar.beat string to Fraction offset in whole notes.
    
    One beat = one crotchet = 1/4 whole note, regardless of metre.
    """
    parts: list[str] = bar_beat.split(".")
    bar: int = int(parts[0])
    beat: float = float(parts[1]) if len(parts) > 1 else 1.0
    offset_in_beats: Fraction = Fraction(bar - 1) * beats_per_bar + Fraction(beat) - 1
    return offset_in_beats / 4
