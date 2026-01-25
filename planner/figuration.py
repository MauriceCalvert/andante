"""Layer 6.5: Figuration as ornamented stepwise lines.

Category A: Pure functions, no I/O, no validation.

Model:
    1. Generate stepwise path from anchor A to anchor B
    2. Distribute available slots among path notes
    3. Ornament each note to fill its slots

Ornaments decorate scale degrees, not fill gaps.
"""
from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence

from builder.types import Anchor, TreatmentAssignment
from shared.key import Key


SLOTS_PER_BAR: int = 16
SEMIQUAVER: Fraction = Fraction(1, 16)


def stepwise_path(
    start: int,
    target: int,
    key: Key,
    floor: int = 30,
    ceiling: int = 88,
) -> list[int]:
    """Generate stepwise diatonic path from start to target (inclusive).

    Clamps pitches to stay within floor/ceiling.
    """
    # Clamp start and target to range
    start = max(floor, min(ceiling, start))
    target = max(floor, min(ceiling, target))

    if start == target:
        return [start]
    path: list[int] = [start]
    current: int = start
    step: int = 1 if target > start else -1
    while current != target:
        current = key.diatonic_step(current, step)
        # Clamp to range
        current = max(floor, min(ceiling, current))
        path.append(current)
        if len(path) > 20:
            break
        # Stop if we hit the boundary and can't progress
        if (step > 0 and current >= ceiling) or (step < 0 and current <= floor):
            break
    return path


def distribute_slots(path_length: int, total_slots: int) -> list[int]:
    """Distribute slots among path notes, more to earlier notes."""
    if path_length == 0:
        return []
    if path_length == 1:
        return [total_slots]
    base: int = total_slots // path_length
    remainder: int = total_slots % path_length
    slots: list[int] = [base] * path_length
    for i in range(remainder):
        slots[i] += 1
    return slots


def ornament_note(
    pitch: int,
    slots: int,
    key: Key,
    is_final: bool = False,
    floor: int = 30,
    ceiling: int = 88,
) -> list[int]:
    """Ornament a single pitch to fill given number of slots.

    Ornaments stay within floor/ceiling to avoid range violations.
    """
    if slots <= 0:
        return []
    if slots == 1:
        return [pitch]

    # Compute neighbor tones, clamped to range
    lower_raw: int = key.diatonic_step(pitch, -1)
    upper_raw: int = key.diatonic_step(pitch, 1)
    lower: int = lower_raw if lower_raw >= floor else pitch
    upper: int = upper_raw if upper_raw <= ceiling else pitch

    if slots == 2:
        if is_final:
            return [pitch, pitch]
        return [pitch, lower]
    if slots == 3:
        return [pitch, lower, pitch]
    if slots == 4:
        return [upper, pitch, lower, pitch]

    result: list[int] = []
    remaining: int = slots
    while remaining >= 4:
        result.extend([upper, pitch, lower, pitch])
        remaining -= 4
    if remaining == 3:
        result.extend([pitch, lower, pitch])
    elif remaining == 2:
        result.extend([pitch, lower])
    elif remaining == 1:
        result.append(pitch)
    return result


def figurate_connection(
    start: int,
    target: int,
    slots: int,
    key: Key,
    floor: int = 30,
    ceiling: int = 88,
) -> list[int]:
    """Generate ornamented stepwise line from start to target."""
    path: list[int] = stepwise_path(start, target, key, floor, ceiling)
    slot_distribution: list[int] = distribute_slots(len(path), slots)
    result: list[int] = []
    for i, (pitch, note_slots) in enumerate(zip(path, slot_distribution)):
        is_final: bool = (i == len(path) - 1)
        ornamented: list[int] = ornament_note(pitch, note_slots, key, is_final, floor, ceiling)
        result.extend(ornamented)
    return result


def _bar_beat_to_slot(bar_beat: str) -> int:
    """Convert bar.beat string to slot index."""
    parts: list[str] = bar_beat.split(".")
    bar: int = int(parts[0])
    beat: float = float(parts[1]) if len(parts) > 1 else 1.0
    slot_in_bar: int = int((beat - 1) * 4)
    return (bar - 1) * SLOTS_PER_BAR + slot_in_bar


def apply_figuration_to_voice(
    anchors: Sequence[Anchor],
    key: Key,
    voice: str,
) -> tuple[tuple[int, ...], tuple[Fraction, ...]]:
    """Apply figuration to fill gaps between anchors for one voice."""
    if len(anchors) < 2:
        if len(anchors) == 1:
            pitch: int = anchors[0].soprano_midi if voice == "soprano" else anchors[0].bass_midi
            return (pitch,), (Fraction(1, 4),)
        return (), ()

    # Voice-specific range limits
    floor: int = 30 if voice == "bass" else 52
    ceiling: int = 66 if voice == "bass" else 88

    all_pitches: list[int] = []
    for i in range(len(anchors) - 1):
        anchor_a: Anchor = anchors[i]
        anchor_b: Anchor = anchors[i + 1]
        slot_a: int = _bar_beat_to_slot(anchor_a.bar_beat)
        slot_b: int = _bar_beat_to_slot(anchor_b.bar_beat)
        slots: int = slot_b - slot_a
        if slots <= 0:
            slots = 1
        start: int = anchor_a.soprano_midi if voice == "soprano" else anchor_a.bass_midi
        target: int = anchor_b.soprano_midi if voice == "soprano" else anchor_b.bass_midi
        pitches: list[int] = figurate_connection(start, target, slots, key, floor, ceiling)
        all_pitches.extend(pitches)
    final: Anchor = anchors[-1]
    final_pitch: int = final.soprano_midi if voice == "soprano" else final.bass_midi
    all_pitches.append(final_pitch)
    all_durations: tuple[Fraction, ...] = tuple(SEMIQUAVER for _ in all_pitches)
    return tuple(all_pitches), all_durations


def layer_6_5_figuration(
    anchors: Sequence[Anchor],
    key: Key,
    schema_profiles: dict[str, str],
    energy: str,
    pitch_class_set: frozenset[int],
    registers: dict[str, tuple[int, int]],
    metre: str,
    treatment_assignments: Sequence[TreatmentAssignment] | None = None,
) -> tuple[tuple[int, ...], tuple[Fraction, ...], tuple[int, ...], tuple[Fraction, ...]]:
    """Execute Layer 6.5: Figuration as ornamented stepwise lines."""
    if not anchors:
        return (), (), (), ()
    soprano_pitches, soprano_durations = apply_figuration_to_voice(anchors, key, "soprano")
    bass_pitches, bass_durations = apply_figuration_to_voice(anchors, key, "bass")
    return soprano_pitches, soprano_durations, bass_pitches, bass_durations
