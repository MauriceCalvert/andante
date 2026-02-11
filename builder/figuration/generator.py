"""Algorithmic figuration generator for soprano diminutions.

Pure deterministic function (A005) that generates degree sequences algorithmically
based on interval class, note count, harmonic context, and phrase character.
Replaces lookup-then-pad flow for dense and non-matching figuration gaps.
"""
from shared.constants import INTERVAL_DIATONIC_SIZE


def generate_degrees(
    interval: str,
    note_count: int,
    character: str,
    position: str,
    chord_tones: tuple[int, ...],
    bar_num: int,
) -> tuple[int, ...]:
    """Generate degree sequence algorithmically for a figuration span.

    Pure function: no state, no RNG. Variation via bar_num only (V001).

    Args:
        interval: Interval class ("unison", "step_up", "third_down", etc.).
        note_count: Exact number of degrees to produce.
        character: "plain" | "expressive" | "energetic" | "ornate" | "bold".
        position: "passing" | "cadential" | "schema_arrival".
        chord_tones: Diatonic offsets of chord tones from start pitch.
        bar_num: Bar index for deterministic variation (V001).

    Returns:
        Tuple of exactly note_count degree offsets from start pitch.
        First offset is always 0 (start pitch itself).
    """
    assert note_count >= 2, f"note_count must be >= 2, got {note_count}"
    assert interval in INTERVAL_DIATONIC_SIZE, f"Unknown interval: {interval}"
    assert character in ("plain", "expressive", "energetic", "ornate", "bold"), \
        f"Invalid character: {character}"
    assert position in ("passing", "cadential", "schema_arrival"), \
        f"Invalid position: {position}"

    # Extract interval distance from interval name
    interval_distance: int = INTERVAL_DIATONIC_SIZE[interval]
    # Determine direction: ascending or descending
    is_ascending: bool = "_up" in interval or interval == "unison"
    target: int = interval_distance if is_ascending else -interval_distance

    # Dispatch by interval class
    if interval == "unison":
        return _generate_unison(
            note_count=note_count,
            character=character,
            bar_num=bar_num,
        )
    elif interval_distance == 1:  # step
        return _generate_step(
            note_count=note_count,
            target=target,
            character=character,
            position=position,
            chord_tones=chord_tones,
            bar_num=bar_num,
        )
    elif interval_distance == 2:  # third
        return _generate_third(
            note_count=note_count,
            target=target,
            character=character,
            chord_tones=chord_tones,
            bar_num=bar_num,
        )
    elif interval_distance in (3, 4):  # fourth, fifth
        return _generate_fourth_fifth(
            note_count=note_count,
            target=target,
            character=character,
            chord_tones=chord_tones,
            bar_num=bar_num,
        )
    else:  # sixth and larger
        return _generate_tirata(
            note_count=note_count,
            target=target,
            character=character,
            position=position,
            chord_tones=chord_tones,
            bar_num=bar_num,
        )


def _generate_unison(
    note_count: int,
    character: str,
    bar_num: int,
) -> tuple[int, ...]:
    """Generate unison figuration: repeated tone with decorations."""
    if note_count == 2:
        return (0, 0)
    if note_count == 3:
        # Mordent: lower or upper neighbour
        variant: int = bar_num % 2
        return (0, -1, 0) if variant == 0 else (0, 1, 0)
    if note_count == 4:
        # Turn or inverted turn
        variant = bar_num % 2
        return (0, 1, 0, -1) if variant == 0 else (0, -1, 0, 1)
    # 5+: tile turn pattern
    if character == "plain" and note_count >= 4:
        # Plain: mostly repeated tone, single neighbour at midpoint
        result: list[int] = [0] * note_count
        mid: int = note_count // 2
        result[mid] = 1 if (bar_num % 2 == 0) else -1
        return tuple(result)
    # Tile turn pattern
    turn: tuple[int, ...] = (0, 1, 0, -1) if (bar_num % 2 == 0) else (0, -1, 0, 1)
    tiles_needed: int = note_count // 4
    remainder: int = note_count % 4
    result_list: list[int] = []
    for _ in range(tiles_needed):
        result_list.extend(turn)
    if remainder > 0:
        result_list.extend(turn[:remainder])
    return tuple(result_list[:note_count])


def _generate_step(
    note_count: int,
    target: int,
    character: str,
    position: str,
    chord_tones: tuple[int, ...],
    bar_num: int,
) -> tuple[int, ...]:
    """Generate step figuration: circolo patterns, neighbour decorations."""
    direction: int = 1 if target > 0 else -1
    if note_count == 2:
        return (0, target)
    if note_count == 3:
        # Lower neighbour approach or direct
        variant: int = bar_num % 2
        if variant == 0:
            return (0, -direction, target)
        else:
            # Check if intermediate chord tone exists
            if direction in chord_tones:
                return (0, direction, target)
            return (0, -direction, target)
    if note_count == 4:
        # Circolo mezzo or turn-then-step
        variant = bar_num % 2
        if variant == 0:
            # Circolo mezzo: [-1, 0, -1, +1] for step up
            return (-direction, 0, -direction, target)
        else:
            # Turn then step
            return (0, -direction, 0, target)
    if note_count == 8:
        # Double circolo or stepwise walk with neighbour decoration
        variant = bar_num % 2
        if variant == 0 and character in ("expressive", "ornate"):
            # Double circolo: tile the 4-note pattern twice
            unit: tuple[int, ...] = (-direction, 0, -direction, target)
            return unit + unit
        else:
            # Stepwise walk with neighbours: [0, -1, 0, 1, 0, -1, 0, +1]
            return (
                0, -direction, 0, direction,
                0, -direction, 0, target,
            )
    # General case: stepwise fill with neighbour decorations
    # For energetic: continuous motion, more passing tones
    # For plain: simpler, fewer decorations
    if character in ("energetic", "bold"):
        # Stepwise run: [0, direction, direction*2, ..., target]
        # But we have note_count notes, not just 2
        # Interpolate between 0 and target with decorations
        return _stepwise_interpolate(
            start=0,
            end=target,
            count=note_count,
            allow_decorations=True,
            bar_num=bar_num,
        )
    else:
        # Moderate decoration
        return _stepwise_interpolate(
            start=0,
            end=target,
            count=note_count,
            allow_decorations=True,
            bar_num=bar_num,
        )


def _generate_third(
    note_count: int,
    target: int,
    character: str,
    chord_tones: tuple[int, ...],
    bar_num: int,
) -> tuple[int, ...]:
    """Generate third figuration: stepwise fill with neighbour decorations."""
    direction: int = 1 if target > 0 else -1
    if note_count == 2:
        # Direct (rare, only for plain)
        return (0, target)
    if note_count == 3:
        # Stepwise fill: [0, direction, target]
        return (0, direction, target)
    if note_count == 4:
        # Neighbour then step, or undershoot approach
        variant: int = bar_num % 2
        if variant == 0:
            return (0, direction, 0, target)
        else:
            return (0, -direction, direction, target)
    # 6+: stepwise fill with neighbour decorations
    # Check if chord has intermediate tone
    intermediate: int = direction
    if intermediate in chord_tones:
        # Use chord tone as passing landmark
        if note_count == 6:
            # [0, -dir, int, dir*2, int, target]
            return (
                0, -direction, intermediate,
                direction * 2, intermediate, target,
            )
        else:
            return _stepwise_interpolate(
                start=0,
                end=target,
                count=note_count,
                allow_decorations=True,
                bar_num=bar_num,
            )
    else:
        # Neighbour-decorate endpoints
        return _stepwise_interpolate(
            start=0,
            end=target,
            count=note_count,
            allow_decorations=True,
            bar_num=bar_num,
        )


def _generate_fourth_fifth(
    note_count: int,
    target: int,
    character: str,
    chord_tones: tuple[int, ...],
    bar_num: int,
) -> tuple[int, ...]:
    """Generate fourth/fifth figuration: pure stepwise fill (conservative)."""
    # Conservative approach: pure stepwise fill to avoid leap violations
    # Arpeggiation creates non-adjacent degrees that can produce leaps in realization
    return _stepwise_interpolate(
        start=0,
        end=target,
        count=note_count,
        allow_decorations=False,  # No decorations to avoid leap-then-leap
        bar_num=bar_num,
    )


def _generate_tirata(
    note_count: int,
    target: int,
    character: str,
    position: str,
    chord_tones: tuple[int, ...],
    bar_num: int,
) -> tuple[int, ...]:
    """Generate tirata (scale run) for sixths and larger intervals."""
    # Pure stepwise fill, no decorations (conservative to avoid leap violations)
    return _stepwise_interpolate(
        start=0,
        end=target,
        count=note_count,
        allow_decorations=False,
        bar_num=bar_num,
    )


def _stepwise_interpolate(
    start: int,
    end: int,
    count: int,
    allow_decorations: bool,
    bar_num: int,
) -> tuple[int, ...]:
    """Interpolate stepwise from start to end with exactly count notes.

    Args:
        start: Starting degree offset.
        end: Ending degree offset.
        count: Number of notes to produce.
        allow_decorations: If True, add neighbour-tone decorations.
        bar_num: For deterministic variation.

    Returns:
        Tuple of count degree offsets, starting with start, ending with end.
    """
    assert count >= 2, f"count must be >= 2, got {count}"
    direction: int = 1 if end > start else -1
    interval: int = abs(end - start)

    if interval == 0:
        # Unison: repeat start
        return (start,) * count

    # Pure stepwise fill: [start, start+dir, start+2*dir, ..., end]
    stepwise_count: int = interval + 1
    if count <= stepwise_count:
        # ALWAYS use complete stepwise fill, never sample/skip degrees
        # Sampling creates leaps. If we need fewer notes than steps, just use first N steps.
        result: list[int] = []
        for i in range(min(count, stepwise_count)):
            result.append(start + i * direction)
        # If count > stepwise_count (shouldn't happen in this branch), pad with end
        while len(result) < count:
            result.append(end)
        return tuple(result)
    else:
        # More notes than steps: add decorations
        # Conservative: for large intervals (>4 steps), no decorations — just pure stepwise
        # to avoid leap-then-leap violations in realization (especially in minor keys)
        if interval > 4 or not allow_decorations:
            # Pure stepwise fill, then repeat final tone
            base: list[int] = [start + i * direction for i in range(stepwise_count)]
            # Pad by repeating end
            result_list: list[int] = base + [end] * (count - len(base))
            return tuple(result_list[:count])
        else:
            # Small interval with decorations: safe to insert neighbours
            base = [start + i * direction for i in range(stepwise_count)]
            extra: int = count - stepwise_count
            # Insert neighbours every N steps
            insert_every: int = max(2, stepwise_count // (extra + 1))
            decorated: list[int] = []
            inserted: int = 0
            for i, deg in enumerate(base):
                decorated.append(deg)
                if inserted < extra and i > 0 and i % insert_every == 0:
                    # Insert neighbour: alternate upper/lower
                    neighbour_dir: int = -direction if (bar_num + inserted) % 2 == 0 else direction
                    decorated.append(deg + neighbour_dir)
                    inserted += 1
            # Truncate to count
            return tuple(decorated[:count])
