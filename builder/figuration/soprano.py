"""Soprano figuration — fill gaps between structural tones with diminutions.

Given two anchor (offset, midi) pairs, selects a figure from the diminution
table, pairs it with a rhythm template, and realises concrete (offset, midi,
duration) note tuples.
"""
import logging
from fractions import Fraction

from builder.figuration.loader import get_rhythm_templates, select_rhythm_template
from builder.figuration.rhythm_calc import compute_rhythmic_distribution
from builder.figuration.selection import classify_interval, select_figure
from builder.figuration.types import Figure, RhythmTemplate
from shared.constants import VALID_DURATIONS_SET
from shared.key import Key
from shared.music_math import parse_metre

logger: logging.Logger = logging.getLogger(__name__)


def figurate_soprano_span(
    start_offset: Fraction,
    start_midi: int,
    end_offset: Fraction,
    end_midi: int,
    key: Key,
    metre: str,
    character: str,
    position: str,
    is_minor: bool,
    bar_num: int,
    midi_range: tuple[int, int],
    prev_figure_name: str | None = None,
    recall_figure_name: str | None = None,
) -> tuple[list[tuple[Fraction, int, Fraction]], str]:
    """Fill gap between two structural tones with a figured diminution.

    The first note always starts at start_offset with start_midi.
    The last note's pitch approaches end_midi but need not equal it —
    the next structural tone handles arrival.

    Args:
        start_offset: Absolute offset of the first anchor (whole notes).
        start_midi: MIDI pitch of the first anchor.
        end_offset: Absolute offset of the next anchor (whole notes).
        end_midi: MIDI pitch of the next anchor.
        key: Current musical key.
        metre: Time signature string (e.g. "3/4").
        character: Desired character ("plain", "expressive", etc.).
        position: "passing" | "cadential" | "schema_arrival".
        is_minor: True if current key is minor.
        bar_num: Bar index for deterministic variation (V001).
        midi_range: (low, high) MIDI bounds for soprano.
        prev_figure_name: Previous figure name to avoid repetition.
        recall_figure_name: If set, prefer this figure for motivic recall.

    Returns:
        (notes, figure_name) where notes is [(offset, midi, duration), ...].
    """
    gap: Fraction = end_offset - start_offset
    assert gap > 0, (
        f"figurate_soprano_span: non-positive gap {gap} "
        f"from offset {start_offset} to {end_offset}"
    )

    # Classify the melodic interval
    interval: str = classify_interval(
        from_midi=start_midi, to_midi=end_midi, key=key,
    )

    # Determine note count from gap + density
    density: str = _character_to_density(character=character)
    note_count, _equal_dur = compute_rhythmic_distribution(
        gap=gap, density=density,
    )

    # Get rhythm durations — may adjust note_count for valid durations
    durations: tuple[Fraction, ...] = _get_durations(
        note_count=note_count,
        gap=gap,
        metre=metre,
        character=character,
        position=position,
        bar_num=bar_num,
    )
    # Durations are authoritative for actual note count
    actual_count: int = len(durations)

    # Select figure based on actual note count
    figure: Figure = select_figure(
        interval=interval,
        note_count=actual_count,
        character=character,
        position=position,
        is_minor=is_minor,
        bar_num=bar_num,
        prev_figure_name=prev_figure_name,
        recall_figure_name=recall_figure_name,
    )

    # Realise figure degrees as MIDI pitches
    pitches: list[int] = _realise_pitches(
        figure=figure,
        note_count=actual_count,
        start_midi=start_midi,
        end_midi=end_midi,
        key=key,
        midi_range=midi_range,
    )

    # Build output notes
    assert len(pitches) == len(durations), (
        f"Pitch count {len(pitches)} != duration count {len(durations)}"
    )
    notes: list[tuple[Fraction, int, Fraction]] = []
    offset: Fraction = start_offset
    for pitch, dur in zip(pitches, durations):
        notes.append((offset, pitch, dur))
        offset += dur

    return notes, figure.name


def _character_to_density(character: str) -> str:
    """Map figure character to rhythmic density."""
    if character in ("ornate", "bold", "energetic"):
        return "high"
    if character == "expressive":
        return "medium"
    return "low"


def _get_durations(
    note_count: int,
    gap: Fraction,
    metre: str,
    character: str,
    position: str,
    bar_num: int,
) -> tuple[Fraction, ...]:
    """Get duration sequence for the figuration.

    Uses rhythm templates only when the gap is a full bar (so scaling
    by beat_unit preserves valid durations). For sub-bar gaps, uses
    equal subdivision from compute_rhythmic_distribution.
    """
    bar_length, beat_unit = parse_metre(metre=metre)

    # Only use templates for full-bar gaps where scaling is clean
    if gap == bar_length:
        templates: dict[tuple[int, str], list[RhythmTemplate]] = get_rhythm_templates()
        counts_to_try: list[int] = [note_count]
        for try_count in counts_to_try:
            template_key: tuple[int, str] = (try_count, metre)
            if template_key not in templates:
                continue
            template_list: list[RhythmTemplate] = templates[template_key]
            template: RhythmTemplate = select_rhythm_template(
                templates=template_list,
                character=character,
                position=position,
                bar_num=bar_num,
            )
            # Template durations are in beats — multiply by beat_unit
            scaled: tuple[Fraction, ...] = tuple(
                d * beat_unit for d in template.durations
            )
            # Verify all are valid durations
            if all(d in VALID_DURATIONS_SET for d in scaled):
                return scaled

    # Fall back to equal subdivision via compute_rhythmic_distribution
    _, unit_dur = compute_rhythmic_distribution(gap=gap, density="medium")
    count: int = int(gap / unit_dur) if unit_dur > 0 else note_count
    if count < 1:
        count = 1
    actual_dur: Fraction = gap / count
    return tuple(actual_dur for _ in range(count))


def _realise_pitches(
    figure: Figure,
    note_count: int,
    start_midi: int,
    end_midi: int,
    key: Key,
    midi_range: tuple[int, int],
) -> list[int]:
    """Convert figure degree offsets to MIDI pitches.

    Figure.degrees are diatonic offsets from the start pitch.
    The first note is always start_midi.
    """
    # Get the figure's degree sequence, adjusted to target note_count
    degrees: tuple[int, ...] = _fit_degrees_to_count(
        figure=figure, target_count=note_count,
    )

    pitches: list[int] = []
    for i, deg_offset in enumerate(degrees):
        if i == 0:
            pitch: int = start_midi
        else:
            pitch = key.diatonic_step(midi=start_midi, steps=deg_offset)
            pitch = _clamp_to_range(pitch=pitch, midi_range=midi_range)
        pitches.append(pitch)

    return pitches


def _fit_degrees_to_count(
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


def _clamp_to_range(pitch: int, midi_range: tuple[int, int]) -> int:
    """Clamp a pitch to the allowed MIDI range, using octave transposition."""
    while pitch < midi_range[0] and pitch + 12 <= midi_range[1]:
        pitch += 12
    while pitch > midi_range[1] and pitch - 12 >= midi_range[0]:
        pitch -= 12
    # Final clamp if still out
    if pitch < midi_range[0]:
        pitch = midi_range[0]
    if pitch > midi_range[1]:
        pitch = midi_range[1]
    return pitch
