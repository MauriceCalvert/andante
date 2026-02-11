"""Soprano figuration helpers — public pitch realisation functions.

Provides utilities for converting figured diminutions to MIDI pitches with
voice-leading-aware octave selection.
"""
import logging

from builder.figuration.types import Figure
from shared.key import Key

logger: logging.Logger = logging.getLogger(__name__)


def character_to_density(character: str) -> str:
    """Map figure character to rhythmic density."""
    if character in ("ornate", "bold", "energetic"):
        return "high"
    if character == "expressive":
        return "medium"
    return "low"


def realise_pitches(
    figure: Figure,
    note_count: int,
    start_midi: int,
    end_midi: int,
    key: Key,
    midi_range: tuple[int, int],
) -> list[int]:
    """Convert figure degree offsets to MIDI pitches.

    Figure.degrees are diatonic offsets from the start pitch.
    The first note is always start_midi. Subsequent pitches use
    voice-leading-aware octave selection: all octave variants of the
    target pitch within midi_range are generated, and the one closest
    to the previous pitch is chosen.
    """
    degrees: tuple[int, ...] = fit_degrees_to_count(
        figure=figure, target_count=note_count,
    )
    pitches: list[int] = []
    prev_pitch: int = start_midi
    for i, deg_offset in enumerate(degrees):
        if i == 0:
            pitch: int = start_midi
        else:
            raw: int = key.diatonic_step(midi=start_midi, steps=deg_offset)
            pitch = nearest_in_range(
                target=raw,
                prev_pitch=prev_pitch,
                midi_range=midi_range,
            )
        prev_pitch = pitch
        pitches.append(pitch)
    return pitches


def fit_degrees_to_count(
    figure: Figure,
    target_count: int,
) -> tuple[int, ...]:
    """Adjust figure degrees to match target note count.

    - Exact match: return as-is.
    - Chainable: tile the chain unit.
    - Fewer notes: truncate or interpolate.
    - More notes: pad with linear steps.
    """
    if len(figure.degrees) == target_count:
        return figure.degrees

    # Chainable tiling
    if figure.chainable and figure.effective_chain_unit > 0:
        unit: tuple[int, ...] = figure.degrees[:figure.effective_chain_unit]
        tiles_needed: int = target_count // len(unit)
        remainder: int = target_count % len(unit)
        result: list[int] = []
        for _ in range(tiles_needed):
            result.extend(unit)
        if remainder > 0:
            result.extend(unit[:remainder])
        return tuple(result[:target_count])

    # Too many figure notes — truncate keeping first and last
    if len(figure.degrees) > target_count:
        if target_count <= 2:
            return (figure.degrees[0], figure.degrees[-1])[:target_count]
        # Keep first, evenly sample middle, keep last
        middle_count: int = target_count - 2
        step: float = (len(figure.degrees) - 2) / (middle_count + 1)
        indices: list[int] = [0]
        for i in range(1, middle_count + 1):
            indices.append(int(i * step))
        indices.append(len(figure.degrees) - 1)
        return tuple(figure.degrees[idx] for idx in indices[:target_count])

    # Too few figure notes — extend with neighbour-tone alternation
    result_list: list[int] = list(figure.degrees)
    last_deg: int = figure.degrees[-1]
    pad_count: int = target_count - len(figure.degrees)
    if pad_count > 4:
        logger.warning(
            "Figure '%s' padded by %d notes (degrees %d, target %d)",
            figure.name, pad_count, len(figure.degrees), target_count,
        )
    while len(result_list) < target_count:
        pad_idx: int = len(result_list) - len(figure.degrees)
        offset: int = [1, 0, -1, 0][pad_idx % 4]
        result_list.append(last_deg + offset)
    return tuple(result_list)


def nearest_in_range(
    target: int,
    prev_pitch: int,
    midi_range: tuple[int, int],
) -> int:
    """Pick the octave variant of target closest to prev_pitch, within range.

    Generates all octave transpositions of target that fall within
    midi_range, then returns the one with the smallest absolute
    interval to prev_pitch. If no variant is in range (degenerate),
    falls back to hard clamp.
    """
    candidates: list[int] = []
    # Start from lowest possible octave variant
    base: int = target % 12 + (midi_range[0] // 12) * 12
    if base < midi_range[0]:
        base += 12
    pitch: int = base
    while pitch <= midi_range[1]:
        candidates.append(pitch)
        pitch += 12
    if not candidates:
        # Degenerate: no octave variant in range, hard clamp
        return max(midi_range[0], min(target, midi_range[1]))
    # Pick closest to prev_pitch
    best: int = min(candidates, key=lambda p: abs(p - prev_pitch))
    return best
