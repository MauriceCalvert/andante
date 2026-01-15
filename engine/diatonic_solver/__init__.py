"""Unified diatonic inner voice solver.

This is the canonical inner voice solver for the andante pipeline. All
operations are in degree space (1-7). No MIDI conversion occurs within
this module.

Public API:
    solve_inner_voices() - Main entry point for inner voice generation
    add_inner_voices() - Adapter for ExpandedPhrase integration
"""
from fractions import Fraction
from typing import Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from engine.engine_types import ExpandedPhrase
    from engine.key import Key

from engine.diatonic_solver.core import (
    DiatonicPitch,
    DiatonicSlice,
    VoiceConstraints,
    extract_degrees_from_voice,
    build_slices_from_voices,
    get_voice_constraints,
)
from engine.diatonic_solver.constraints import get_chord_tones
from engine.diatonic_solver.strategies import solve_cpsat, solve_greedy
from engine.voice_material import ExpandedVoices, VoiceMaterial
from shared.pitch import FloatingNote, Pitch, Rest, is_rest


Strategy = Literal["cpsat", "greedy"]


def solve_inner_voices(
    soprano: VoiceMaterial,
    bass: VoiceMaterial,
    voice_count: int,
    texture: str = "homophonic",
    strategy: Strategy = "cpsat",
    thematic: dict[int, VoiceMaterial] | None = None,
    metre: str = "4/4",
    timeout: float = 5.0,
) -> ExpandedVoices:
    """Solve inner voice pitches using specified strategy.

    All inputs/outputs are FloatingNote (diatonic). No MIDI conversion
    occurs within this function.

    Args:
        soprano: VoiceMaterial with soprano pitches (FloatingNote)
        bass: VoiceMaterial with bass pitches (FloatingNote)
        voice_count: Total number of voices (e.g., 4 for SATB)
        texture: "polyphonic" or "homophonic"
        strategy: "cpsat" (global optimal) or "greedy" (fast)
        thematic: Optional dict mapping voice_idx to VoiceMaterial for thematic targets
        metre: Time signature string for beat strength calculation
        timeout: CP-SAT solver time limit (only used for cpsat strategy)

    Returns:
        ExpandedVoices with all voices including solved inner voices.
    """
    inner_count = voice_count - 2
    if inner_count <= 0:
        # No inner voices to solve
        return ExpandedVoices(voices=[soprano, bass])

    # Extract degree events from outer voices
    soprano_events = extract_degrees_from_voice(
        tuple(soprano.pitches), tuple(soprano.durations)
    )
    bass_events = extract_degrees_from_voice(
        tuple(bass.pitches), tuple(bass.durations)
    )

    # Build slice sequence
    slices = build_slices_from_voices(soprano_events, bass_events, voice_count)

    if not slices:
        # No slices to solve (e.g., all rests)
        return _build_rest_inner_voices(soprano, bass, voice_count)

    # Calculate beat strength
    is_strong_beat = _calculate_beat_strength(slices, metre)

    # Build thematic targets if polyphonic
    thematic_targets: dict[tuple[int, int], int] | None = None
    if texture == "polyphonic" and thematic:
        thematic_targets = _build_thematic_targets(slices, thematic, voice_count)

    # Solve using selected strategy
    if strategy == "cpsat":
        solved_slices = solve_cpsat(
            slices, voice_count, is_strong_beat, thematic_targets, timeout
        )
        if solved_slices is None:
            # CP-SAT failed - fall back to greedy
            print("  CP-SAT infeasible, falling back to greedy")
            solved_slices = solve_greedy(slices, voice_count, is_strong_beat, thematic_targets)
    else:
        solved_slices = solve_greedy(slices, voice_count, is_strong_beat, thematic_targets)

    # Convert solved slices back to ExpandedVoices
    return _build_voices_from_slices(solved_slices, soprano, bass, voice_count)


def _calculate_beat_strength(slices: list[DiatonicSlice], metre: str) -> dict[int, bool]:
    """Calculate whether each slice is on a strong beat."""
    bar_dur = Fraction(1)  # Default 4/4
    if metre == "3/4":
        bar_dur = Fraction(3, 4)
    elif metre == "6/8":
        bar_dur = Fraction(3, 4)
    elif metre == "2/4":
        bar_dur = Fraction(1, 2)

    result: dict[int, bool] = {}
    for si, slice_data in enumerate(slices):
        beat_in_bar = slice_data.offset % bar_dur
        # Strong beats: downbeat and middle of bar
        is_strong = beat_in_bar == Fraction(0) or beat_in_bar == bar_dur / 2
        result[si] = is_strong

    return result


def _build_thematic_targets(
    slices: list[DiatonicSlice],
    thematic: dict[int, VoiceMaterial],
    voice_count: int,
) -> dict[tuple[int, int], int]:
    """Build thematic target mapping from voice materials."""
    targets: dict[tuple[int, int], int] = {}

    for voice_idx, material in thematic.items():
        if voice_idx < 1 or voice_idx >= voice_count - 1:
            continue  # Only inner voices

        # Build offset -> degree map for this voice
        offset = Fraction(0)
        for p, d in zip(material.pitches, material.durations):
            if isinstance(p, FloatingNote):
                # Find matching slice
                for si, slice_data in enumerate(slices):
                    if slice_data.offset == offset:
                        targets[(si, voice_idx)] = p.degree
                        break
            offset += d

    return targets


def _build_rest_inner_voices(
    soprano: VoiceMaterial,
    bass: VoiceMaterial,
    voice_count: int,
) -> ExpandedVoices:
    """Build ExpandedVoices with resting inner voices."""
    budget = soprano.budget
    materials: list[VoiceMaterial] = [soprano]

    for vi in range(1, voice_count - 1):
        materials.append(VoiceMaterial(
            voice_index=vi,
            pitches=[Rest()],
            durations=[budget],
        ))

    materials.append(bass)
    return ExpandedVoices(voices=materials)


def _build_voices_from_slices(
    solved_slices: list[DiatonicSlice],
    soprano: VoiceMaterial,
    bass: VoiceMaterial,
    voice_count: int,
) -> ExpandedVoices:
    """Convert solved slices back to ExpandedVoices with FloatingNote pitches."""
    inner_count = voice_count - 2
    budget = soprano.budget

    # Build inner voice materials from slices
    inner_pitches: list[list[Pitch]] = [[] for _ in range(inner_count)]
    inner_durations: list[list[Fraction]] = [[] for _ in range(inner_count)]

    # Handle gap before first slice
    if solved_slices and solved_slices[0].offset > Fraction(0):
        rest_dur = solved_slices[0].offset
        for vi in range(inner_count):
            inner_pitches[vi].append(Rest())
            inner_durations[vi].append(rest_dur)

    # Convert each slice
    for si, slice_data in enumerate(solved_slices):
        # Calculate duration until next slice or end
        if si < len(solved_slices) - 1:
            dur = solved_slices[si + 1].offset - slice_data.offset
        else:
            dur = budget - slice_data.offset

        if dur <= Fraction(0):
            continue

        # Extract inner voice pitches
        for inner_idx in range(inner_count):
            voice_idx = inner_idx + 1  # Skip soprano at index 0
            pitch_data = slice_data.pitches[voice_idx]

            if pitch_data is None:
                inner_pitches[inner_idx].append(Rest())
            else:
                inner_pitches[inner_idx].append(FloatingNote(pitch_data.degree))

            inner_durations[inner_idx].append(dur)

    # Build final voice materials
    materials: list[VoiceMaterial] = []

    # Soprano (index 0)
    materials.append(VoiceMaterial(
        voice_index=0,
        pitches=list(soprano.pitches),
        durations=list(soprano.durations),
    ))

    # Inner voices
    for vi in range(inner_count):
        materials.append(VoiceMaterial(
            voice_index=vi + 1,
            pitches=inner_pitches[vi],
            durations=inner_durations[vi],
        ))

    # Bass (index voice_count - 1)
    materials.append(VoiceMaterial(
        voice_index=voice_count - 1,
        pitches=list(bass.pitches),
        durations=list(bass.durations),
    ))

    return ExpandedVoices(voices=materials)


def add_inner_voices(
    phrase: "ExpandedPhrase",
    key: "Key",
    texture: str,
    voice_count: int,
    metre: str,
    subject_pitches: tuple[Pitch, ...] | None = None,
    subject_durations: tuple[Fraction, ...] | None = None,
    cs_pitches: tuple[Pitch, ...] | None = None,
    cs_durations: tuple[Fraction, ...] | None = None,
    timeout: float = 5.0,
) -> "ExpandedPhrase":
    """Add inner voices to an ExpandedPhrase using diatonic solver.

    This is the adapter function for integration with expander.py.
    All operations are in degree space (FloatingNote).

    Args:
        phrase: ExpandedPhrase with soprano and bass voices
        key: Musical key (used only for validation, not MIDI conversion)
        texture: "polyphonic" or "homophonic"
        voice_count: Target number of voices
        metre: Time signature string
        subject_pitches: Optional subject pitches for thematic matching
        subject_durations: Optional subject durations
        cs_pitches: Optional counter-subject pitches
        cs_durations: Optional counter-subject durations
        timeout: CP-SAT solver time limit

    Returns:
        ExpandedPhrase with all voices including solved inner voices.
    """
    # Avoid circular import
    from engine.engine_types import ExpandedPhrase as EP

    inner_count = voice_count - 2
    if inner_count <= 0:
        return phrase

    soprano = phrase.voices.soprano
    bass = phrase.voices.bass

    # Build thematic material for polyphonic texture
    thematic: dict[int, VoiceMaterial] | None = None
    if texture == "polyphonic":
        thematic = {}
        # Alto (voice 1) gets counter-subject if available
        if cs_pitches and cs_durations:
            thematic[1] = VoiceMaterial(
                voice_index=1,
                pitches=list(cs_pitches),
                durations=list(cs_durations),
            )
        # Tenor (voice 2) gets subject if 4+ voices
        if voice_count > 3 and subject_pitches and subject_durations:
            thematic[2] = VoiceMaterial(
                voice_index=2,
                pitches=list(subject_pitches),
                durations=list(subject_durations),
            )

    # Solve inner voices
    solved_voices = solve_inner_voices(
        soprano=soprano,
        bass=bass,
        voice_count=voice_count,
        texture=texture,
        strategy="cpsat",
        thematic=thematic,
        metre=metre,
        timeout=timeout,
    )

    # Build new ExpandedPhrase with solved voices
    return EP(
        index=phrase.index,
        bars=phrase.bars,
        voices=solved_voices,
        cadence=phrase.cadence,
        tonal_target=phrase.tonal_target,
        is_climax=phrase.is_climax,
        articulation=phrase.articulation,
        gesture=phrase.gesture,
        energy=phrase.energy,
        surprise=phrase.surprise,
        texture=phrase.texture,
        episode_type=phrase.episode_type,
        treatment=phrase.treatment,
    )


__all__ = [
    "solve_inner_voices",
    "add_inner_voices",
    "DiatonicPitch",
    "DiatonicSlice",
    "VoiceConstraints",
    "Strategy",
]
