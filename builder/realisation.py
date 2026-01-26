"""Realisation: Turn anchors into notes.

Category A: Pure functions, no I/O, no validation.

Canonical design: Anchors store degrees + key. MIDI conversion happens here.
Each anchor becomes a note; duration extends to next anchor.
"""
from fractions import Fraction
from typing import Sequence

from builder.types import (
    Anchor, AffectConfig, FormConfig, GenreConfig, KeyConfig,
    Note, NoteFile, TreatmentAssignment,
)

DRIFT_THRESHOLD: int = 12


def realise(
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
    soprano_median: int = genre_config.tessitura.get("soprano", 70)
    bass_median: int = genre_config.tessitura.get("bass", 48)
    prev_soprano: int = soprano_median
    prev_bass: int = bass_median
    for i, anchor in enumerate(sorted_anchors):
        offset: Fraction = _bar_beat_to_offset(anchor.bar_beat, beats_per_bar)
        if i < len(sorted_anchors) - 1:
            next_offset: Fraction = _bar_beat_to_offset(sorted_anchors[i + 1].bar_beat, beats_per_bar)
            duration: Fraction = next_offset - offset
        else:
            duration = end_offset - offset
        s_midi: int = _gravitational_pitch(
            anchor.local_key, anchor.soprano_degree, prev_soprano, soprano_median,
        )
        b_midi: int = _gravitational_pitch(
            anchor.local_key, anchor.bass_degree, prev_bass, bass_median,
        )
        prev_soprano = s_midi
        prev_bass = b_midi
        lyric: str = anchor.schema if anchor.stage == 1 else ""
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


def _gravitational_pitch(
    key: "Key",
    degree: int,
    prev_pitch: int,
    median: int,
) -> int:
    """Find pitch of given degree using gravitational voice leading."""
    from shared.key import Key
    candidates: list[int] = []
    for octave in range(1, 8):
        midi: int = key.degree_to_midi(degree, octave=octave)
        candidates.append(midi)
    candidates.sort(key=lambda m: abs(m - prev_pitch))
    nearest: int = candidates[0]
    nearest_drift: int = abs(nearest - median)
    if nearest_drift <= DRIFT_THRESHOLD:
        return nearest
    candidates.sort(key=lambda m: abs(m - median))
    for alt in candidates:
        if alt != nearest:
            return alt
    return nearest
