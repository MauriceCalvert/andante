"""Harmonic context inference from outer voices.

Infers chord from soprano and bass pitches, generates chord tone candidates
for inner voice filling. Core of the slice solver's candidate generation.
"""
from dataclasses import dataclass
from typing import Tuple

from engine.key import Key
from shared.pitch import FloatingNote, MidiPitch, Pitch, is_rest


@dataclass(frozen=True)
class HarmonicContext:
    """Harmonic context inferred from outer voices at a vertical slice."""
    root_pc: int
    chord_tones: Tuple[int, ...]
    scale: Tuple[int, ...]
    bass_degree: int

    def is_chord_tone(self, pc: int) -> bool:
        """Check if pitch class is a chord tone."""
        return pc in self.chord_tones


def degree_to_pc(degree: int, key: Key) -> int:
    """Convert scale degree (1-7) to pitch class (0-11)."""
    assert 1 <= degree <= 7, f"Degree must be 1-7, got {degree}"
    scale: Tuple[int, ...] = key.scale
    semitones: int = scale[degree - 1]
    return (key.tonic_pc + semitones) % 12


def pc_to_degree(pc: int, key: Key) -> int | None:
    """Convert pitch class (0-11) to scale degree (1-7), or None if chromatic.

    Maps a pitch class to its scale degree in the given key.
    Returns None if the pitch class is not in the scale (chromatic note).
    """
    for degree in range(1, 8):
        if degree_to_pc(degree, key) == pc:
            return degree
    return None


def infer_chord_from_bass(bass_degree: int, key: Key) -> Tuple[int, ...]:
    """Infer triad chord tones from bass degree.

    Assumes root position triad built on bass. Returns pitch classes.
    In baroque practice, bass usually indicates chord root.
    """
    assert 1 <= bass_degree <= 7, f"Bass degree must be 1-7, got {bass_degree}"
    root_pc: int = degree_to_pc(bass_degree, key)
    third_degree: int = ((bass_degree - 1 + 2) % 7) + 1
    fifth_degree: int = ((bass_degree - 1 + 4) % 7) + 1
    third_pc: int = degree_to_pc(third_degree, key)
    fifth_pc: int = degree_to_pc(fifth_degree, key)
    return (root_pc, third_pc, fifth_pc)


def infer_harmony_from_outer(
    soprano_pitch: Pitch,
    bass_pitch: Pitch,
    key: Key,
) -> HarmonicContext:
    """Infer harmonic context from soprano and bass pitches.

    Bass pitch determines chord root (baroque figured bass convention).
    Soprano pitch confirms membership (should be chord tone in good voicing).
    Accepts FloatingNote or MidiPitch.
    """
    assert not is_rest(soprano_pitch), "Soprano cannot be rest"
    assert not is_rest(bass_pitch), "Bass cannot be rest"
    # Extract bass degree from pitch type
    if isinstance(bass_pitch, FloatingNote):
        bass_norm = bass_pitch.degree
    elif isinstance(bass_pitch, MidiPitch):
        bass_pc: int = bass_pitch.midi % 12
        degree: int | None = pc_to_degree(bass_pc, key)
        if degree is None:
            # Chromatic note: default to degree 1 (tonic) as fallback
            bass_norm = 1
        else:
            bass_norm = degree
    else:
        raise TypeError(f"Unexpected bass pitch type: {type(bass_pitch)}")
    chord_tones: Tuple[int, ...] = infer_chord_from_bass(bass_norm, key)
    return HarmonicContext(
        root_pc=chord_tones[0],
        chord_tones=chord_tones,
        scale=key.scale,
        bass_degree=bass_norm,
    )


def generate_chord_tone_candidates(
    context: HarmonicContext,
    voice_low: int,
    voice_high: int,
    key: Key,
) -> Tuple[int, ...]:
    """Generate all chord tones within voice range as MIDI pitches."""
    assert voice_low < voice_high, f"Invalid range: {voice_low}-{voice_high}"
    candidates: list[int] = []
    for pc in context.chord_tones:
        midi: int = pc
        while midi < voice_low:
            midi += 12
        while midi <= voice_high:
            candidates.append(midi)
            midi += 12
    return tuple(sorted(candidates))


def generate_scale_candidates(
    context: HarmonicContext,
    voice_low: int,
    voice_high: int,
    key: Key,
) -> Tuple[int, ...]:
    """Generate all scale degrees within voice range as MIDI pitches.

    Used as fallback when no chord tones fit constraints.
    """
    assert voice_low < voice_high, f"Invalid range: {voice_low}-{voice_high}"
    candidates: list[int] = []
    for semitone in context.scale:
        pc: int = (key.tonic_pc + semitone) % 12
        midi: int = pc
        while midi < voice_low:
            midi += 12
        while midi <= voice_high:
            candidates.append(midi)
            midi += 12
    return tuple(sorted(candidates))
