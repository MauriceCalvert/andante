"""Shared knot construction utilities used across builder and motifs modules.

Six public utilities extracted from cs_writer, hold_writer, soprano_viterbi,
bass_viterbi, and free_fill to eliminate duplicated logic and give each
call site a clean API.
"""
from fractions import Fraction

from builder.types import Note
from shared.constants import STRONG_BEAT_DISSONANT
from shared.key import Key
from viterbi.mtypes import Knot


# Semitone interval classes considered consonant for companion enrichment.
# m3=3, M3=4, m6=8, M6=9 (covers 3rds, 6ths, and their octave compounds).
_COMPANION_CONSONANT_INTERVALS: tuple[int, ...] = (3, 4, 8, 9)


def find_consonant_pitch(
    target_midi: int,
    reference_midi: int,
    range_low: int,
    range_high: int,
) -> int:
    """Find nearest pitch to target_midi that is consonant with reference_midi.

    Searches outward from target_midi within the target range. Falls back to
    range midpoint if nothing consonant is reachable (should not happen in
    practice).
    """
    for distance in range(13):
        for candidate in (target_midi + distance, target_midi - distance):
            if range_low <= candidate <= range_high:
                if abs(candidate - reference_midi) % 12 not in STRONG_BEAT_DISSONANT:
                    return candidate
    return (range_low + range_high) // 2


def sort_and_dedup_knots(knots: list[Knot]) -> list[Knot]:
    """Sort knots by beat and remove entries within 1e-6 of their predecessor."""
    knots.sort(key=lambda k: k.beat)
    return [k for i, k in enumerate(knots) if i == 0 or abs(k.beat - knots[i - 1].beat) > 1e-6]


def ensure_final_knot(
    knots: list[Knot],
    final_beat: float,
    final_midi: int,
) -> list[Knot]:
    """Append a knot at final_beat if none exists within 1e-6.

    Mutates the list and returns it.
    """
    if len(knots) == 0 or abs(final_beat - knots[-1].beat) > 1e-6:
        knots.append(Knot(beat=final_beat, midi_pitch=final_midi))
    return knots


def check_structural_tone_consonance(
    structural_tones: list[tuple[Fraction, int, Key]],
    bass_notes: tuple[Note, ...],
    midi_range: tuple[int, int],
) -> list[tuple[Fraction, int, Key]]:
    """Adjust structural tone octaves to avoid strong-beat vertical dissonances.

    For each tone, finds the bass note sounding at that offset (sustain lookup).
    If the vertical interval class is in STRONG_BEAT_DISSONANT, tries the
    nearest octave shift (up then down). Falls back to the original placement
    when no consonant octave exists within range.

    Args:
        structural_tones: List of (offset, midi, key) from place_structural_tones.
        bass_notes: Finished bass voice notes (sustain-aware lookup).
        midi_range: (low, high) soprano MIDI range for validity check.

    Returns:
        Adjusted list; same length and order as input.
    """
    result: list[tuple[Fraction, int, Key]] = []
    for offset, midi, key in structural_tones:
        bass_pitch: int | None = None
        for bn in bass_notes:
            if bn.offset <= offset < bn.offset + bn.duration:
                bass_pitch = bn.pitch
                break
        if bass_pitch is None or abs(midi - bass_pitch) % 12 not in STRONG_BEAT_DISSONANT:
            result.append((offset, midi, key))
            continue
        # Try octave shifts; accept first that clears the dissonance
        adjusted: int = midi
        for shift in (12, -12):
            candidate: int = midi + shift
            if midi_range[0] <= candidate <= midi_range[1]:
                if abs(candidate - bass_pitch) % 12 not in STRONG_BEAT_DISSONANT:
                    adjusted = candidate
                    break
        result.append((offset, adjusted, key))
    return result


def strong_beat_offsets(bar_length: Fraction, metre: str) -> frozenset[Fraction]:
    """Return strong-beat offsets within a bar for the given metre.

    4/4: downbeat and half-bar (beats 1, 3).
    6/8: downbeat and half-bar (beats 1, 4).
    All others: downbeat only.
    """
    parts: list[str] = metre.split("/")
    numerator: int = int(parts[0])

    if numerator in (4, 6):
        return frozenset({Fraction(0), bar_length / 2})
    return frozenset({Fraction(0)})


def enrich_companion_knots(
    existing_knots: list[Knot] | None,
    material_notes: tuple[Note, ...],
    run_start_offset: Fraction,
    run_end_offset: Fraction,
    bar_length: Fraction,
    companion_range_low: int,
    companion_range_high: int,
    companion_is_above: bool,
    seed_pitch: int | None = None,
) -> list[Knot] | None:
    """Supplement sparse companion knots with consonant pitches on strong beats.

    After thematic knots are built, adds one knot per strong beat where no
    thematic knot already exists.  Each new knot forms a consonant interval
    (3rd or 6th) with the material voice note sounding at that beat.

    Enrichment is additive: existing thematic knots are never removed or
    overridden.  If the resulting merged set is no larger than the input,
    the input is returned unchanged.

    Args:
        existing_knots: Thematic knots already computed (None = none yet).
        material_notes: Notes from the material voice (the voice with content).
        run_start_offset: Absolute offset where the FREE run starts.
        run_end_offset: Absolute offset where the FREE run ends (exclusive).
        bar_length: Length of one bar in whole-note fractions.
        companion_range_low: Minimum MIDI pitch for the companion voice.
        companion_range_high: Maximum MIDI pitch for the companion voice.
        companion_is_above: True when companion is soprano (above bass material).

    Returns:
        Merged, beat-sorted list of knots; or existing_knots when no gain.
    """
    assert companion_range_low <= companion_range_high, (
        f"companion_range_low ({companion_range_low}) must be <= "
        f"companion_range_high ({companion_range_high}).  Fix the range."
    )

    # Strong-beat stride: every half-bar in duple metre, every full bar in triple.
    is_triple: bool = bar_length.numerator % 3 == 0
    stride: Fraction = bar_length if is_triple else bar_length / 2

    # Enumerate strong-beat offsets within this run.
    strong_offsets: list[Fraction] = []
    cursor: Fraction = run_start_offset
    while cursor < run_end_offset:
        strong_offsets.append(cursor)
        cursor += stride

    if not strong_offsets:
        return existing_knots

    # Pre-index existing knot beats for proximity guard.
    existing_beats: list[float] = [k.beat for k in existing_knots] if existing_knots else []
    half_stride: float = float(stride / 2)

    # Reference pitch for "nearest to previous knot" scoring.
    companion_median: int = (companion_range_low + companion_range_high) // 2
    prev_pitch: int = seed_pitch if seed_pitch is not None else companion_median

    new_knots: list[Knot] = []
    for strong_offset in strong_offsets:
        strong_beat: float = float(strong_offset)

        # Skip if an existing thematic knot is close enough.
        if any(abs(eb - strong_beat) < half_stride for eb in existing_beats):
            continue

        # Find the material-voice note sounding at this offset.
        material_pitch: int | None = None
        for note in material_notes:
            if note.offset <= strong_offset < note.offset + note.duration:
                material_pitch = note.pitch
                break

        if material_pitch is None:
            continue

        # Pick the companion pitch nearest to prev_pitch that forms a
        # consonant interval with the material pitch, within range.
        best_pitch: int | None = None
        best_dist: int = 10000
        for midi in range(companion_range_low, companion_range_high + 1):
            interval_class: int = abs(midi - material_pitch) % 12
            if interval_class not in _COMPANION_CONSONANT_INTERVALS:
                continue
            dist: int = abs(midi - prev_pitch)
            if dist < best_dist:
                best_dist = dist
                best_pitch = midi

        if best_pitch is None:
            continue

        new_knots.append(Knot(beat=strong_beat, midi_pitch=best_pitch))
        prev_pitch = best_pitch

    if not new_knots:
        return existing_knots

    merged: list[Knot] = list(existing_knots) if existing_knots else []
    merged.extend(new_knots)
    merged.sort(key=lambda k: k.beat)

    # Guard: never return fewer knots than what was given.
    if existing_knots is not None and len(merged) < len(existing_knots):
        return existing_knots

    return merged
