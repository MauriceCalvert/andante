"""Figure selection engine for soprano diminutions.

Deterministic selection of baroque figures from the diminution table,
indexed by interval between consecutive structural tones.
"""
from builder.figuration.loader import get_diminutions
from builder.figuration.types import Figure
from shared.key import Key


# Map diatonic step count to interval name (ascending/descending)
_STEP_TO_INTERVAL: dict[int, tuple[str, str]] = {
    0: ("unison", "unison"),
    1: ("step_up", "step_down"),
    2: ("third_up", "third_down"),
    3: ("fourth_up", "fourth_down"),
    4: ("fifth_up", "fifth_down"),
    5: ("sixth_up", "sixth_down"),
    6: ("sixth_down", "sixth_up"),   # 6 steps = inverted second
    7: ("octave_up", "octave_down"),
}


def classify_interval(from_midi: int, to_midi: int, key: Key) -> str:
    """Map a MIDI interval to a FIGURATION_INTERVALS key.

    Counts diatonic steps in the key's scale to classify the interval.
    Intervals larger than an octave are reduced to their compound equivalent.
    """
    if from_midi == to_midi:
        return "unison"

    ascending: bool = to_midi > from_midi

    # Count diatonic steps between the two pitches
    dp_from = key.midi_to_diatonic(midi=from_midi)
    dp_to = key.midi_to_diatonic(midi=to_midi)
    raw_steps: int = abs(dp_to.step - dp_from.step)

    # Reduce compound intervals (> octave) to simple
    diatonic_steps: int = raw_steps % 7 if raw_steps > 7 else raw_steps

    pair = _STEP_TO_INTERVAL.get(diatonic_steps)
    assert pair is not None, (
        f"Unmapped diatonic step count {diatonic_steps} "
        f"(from MIDI {from_midi} to {to_midi})"
    )
    return pair[0] if ascending else pair[1]


def select_figure(
    interval: str,
    note_count: int,
    character: str,
    position: str,
    is_minor: bool,
    bar_num: int,
    prev_figure_name: str | None = None,
) -> Figure:
    """Deterministic figure selection from diminution table.

    Args:
        interval: FIGURATION_INTERVALS key (e.g. "step_up", "third_down").
        note_count: Desired number of notes to fill the gap.
        character: "plain" | "expressive" | "energetic" | "ornate" | "bold".
        position: "passing" | "cadential" | "schema_arrival".
        is_minor: True if current key is minor.
        bar_num: Bar index for deterministic rotation (V001).
        prev_figure_name: Previous figure name to avoid immediate repetition.

    Returns:
        Selected Figure from the diminution table.
    """
    diminutions: dict[str, list[Figure]] = get_diminutions()
    pool: list[Figure] = diminutions[interval]
    assert len(pool) > 0, f"No figures for interval '{interval}'"

    # Filter by note count: exact match or chainable figures that divide evenly
    exact: list[Figure] = [f for f in pool if f.note_count == note_count]
    chainable: list[Figure] = [
        f for f in pool
        if f.chainable and f.effective_chain_unit > 0
        and note_count >= f.effective_chain_unit
        and note_count % f.effective_chain_unit == 0
    ]
    candidates: list[Figure] = exact or chainable

    # If no exact/chainable match, accept figures with fewer notes
    # (rhythm template will pad) — prefer closest note count
    if not candidates:
        by_distance: list[tuple[int, Figure]] = sorted(
            [(abs(f.note_count - note_count), f) for f in pool],
            key=lambda t: t[0],
        )
        candidates = [f for _, f in by_distance]

    # Filter: cadential safety
    if position == "cadential":
        safe: list[Figure] = [f for f in candidates if f.cadential_safe]
        if safe:
            candidates = safe

    # Filter: minor safety
    if is_minor:
        minor_ok: list[Figure] = [f for f in candidates if f.minor_safe]
        if minor_ok:
            candidates = minor_ok

    # Filter: character compatibility (soft — keep all if no match)
    char_match: list[Figure] = [
        f for f in candidates if f.character == character
    ]
    if char_match:
        candidates = char_match

    # Sort by weight descending for stable ordering
    candidates.sort(key=lambda f: (-f.weight, f.name))

    # Avoid immediate repetition of previous figure
    if prev_figure_name is not None and len(candidates) > 1:
        non_repeat: list[Figure] = [
            f for f in candidates if f.name != prev_figure_name
        ]
        if non_repeat:
            candidates = non_repeat

    # Deterministic rotation by bar_num (V001)
    return candidates[bar_num % len(candidates)]
