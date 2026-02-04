"""Layer 6: Rhythmic.

Category A: Pure functions, no I/O, no validation.
Input: Anchors + treatments + density + metre
Output: Active slots and durations per voice

Determines which slots are active for each voice based on passage
assignments. Lead voice gets dense filling, accompaniment gets sparse.
"""
from fractions import Fraction

from builder.types import Anchor, RhythmPlan


# Density rates for subject voice (proportion of slots to fill)
DENSITY_RATES: dict[str, float] = {
    "high": 0.75,
    "medium": 0.50,
    "sparse": 0.25,
}

# Accompaniment voice fills fewer slots than subject
ACCOMPANIMENT_RATES: dict[str, float] = {
    "high": 0.50,
    "medium": 0.35,
    "sparse": 0.20,
}

# Duration assignments by density
ANCHOR_DURATION: Fraction = Fraction(1, 8)
SUBJECT_DURATION: Fraction = Fraction(1, 16)
ACCOMPANIMENT_DURATIONS: dict[str, Fraction] = {
    "high": Fraction(1, 8),
    "medium": Fraction(1, 4),
    "sparse": Fraction(1, 2),
}


def _bar_beat_to_slot(bar_beat: str, slots_per_bar: int) -> int:
    """Convert bar.beat string to absolute slot index.

    Args:
        bar_beat: String like "1.0", "3.5" (1-indexed bar, beat as fraction of bar)
        slots_per_bar: Number of slots per bar (16 for 4/4 at 1/16 resolution)

    Returns:
        0-indexed absolute slot number
    """
    parts = bar_beat.split(".")
    bar = int(parts[0])
    beat_frac = Fraction(parts[1]) if len(parts) > 1 else Fraction(0)
    # Convert 1-indexed bar to 0-indexed
    bar_offset = (bar - 1) * slots_per_bar
    # beat_frac is in whole notes, convert to slots
    beat_slots = int(beat_frac * slots_per_bar)
    return bar_offset + beat_slots


def _get_phrase_boundaries(
    treatments: list[dict],
    slots_per_bar: int,
) -> set[int]:
    """Get slot indices at phrase boundaries.

    Phrase boundaries are first and last slot of each treatment span.
    """
    boundaries: set[int] = set()
    for t in treatments:
        bars = t["bars"]
        start_bar, end_bar = bars[0], bars[1]
        # First slot of phrase
        boundaries.add((start_bar - 1) * slots_per_bar)
        # Last slot of phrase (end_bar is inclusive, last slot)
        boundaries.add(end_bar * slots_per_bar - 1)
    return boundaries


def _select_slots_for_voice(
    bar_start: int,
    bar_end: int,
    is_lead_voice: bool,
    density: str,
    slots_per_bar: int,
    anchor_slots: frozenset[int],
    phrase_boundary_slots: set[int],
) -> tuple[set[int], dict[int, Fraction]]:
    """Select active slots for a voice within a bar range.

    Args:
        bar_start: 1-indexed start bar (inclusive)
        bar_end: 1-indexed end bar (inclusive)
        is_lead_voice: True if this voice leads (carries subject material)
        density: "high", "medium", or "sparse"
        slots_per_bar: Slots per bar
        anchor_slots: Set of anchor slot indices (always active)
        phrase_boundary_slots: Set of phrase boundary slots (always active)

    Returns:
        Tuple of (active_slots set, slot_durations dict)
    """
    active: set[int] = set()
    durations: dict[int, Fraction] = {}

    rate = DENSITY_RATES[density] if is_lead_voice else ACCOMPANIMENT_RATES[density]
    dur = SUBJECT_DURATION if is_lead_voice else ACCOMPANIMENT_DURATIONS[density]

    total_slots = (bar_end - bar_start + 1) * slots_per_bar
    start_slot = (bar_start - 1) * slots_per_bar
    end_slot = bar_end * slots_per_bar

    # Distribute slots evenly across the span
    slots_to_fill = int(total_slots * rate)
    assert slots_to_fill > 0, f"No slots to fill: rate={rate}, total={total_slots}"

    # Spacing between active slots
    spacing = max(1, total_slots // slots_to_fill)

    for i in range(start_slot, end_slot, spacing):
        if len(active) >= slots_to_fill:
            break
        active.add(i)
        durations[i] = dur

    # Always include anchor slots within range
    for slot in anchor_slots:
        if start_slot <= slot < end_slot:
            active.add(slot)
            durations[slot] = ANCHOR_DURATION

    # Always include phrase boundary slots within range
    for slot in phrase_boundary_slots:
        if start_slot <= slot < end_slot:
            active.add(slot)
            if slot not in durations:
                durations[slot] = dur

    return active, durations


def layer_6_rhythmic(
    anchors: list[Anchor],
    treatments: list[dict],
    density: str,
    total_bars: int,
    metre: str = "4/4",
) -> RhythmPlan:
    """Execute Layer 6: Generate rhythm plan.

    Args:
        anchors: Schema anchors from L4 (arrival constraints)
        treatments: Passage sequence with {bars: [start, end], lead_voice: 0|1|None}
        density: "high", "medium", or "sparse"
        total_bars: Total bars in piece
        metre: Time signature (default "4/4")

    Returns:
        RhythmPlan with active slots and durations per voice
    """
    assert density in DENSITY_RATES, f"Invalid density: {density}"
    assert treatments, "Empty treatment sequence"
    assert total_bars > 0, f"Invalid total_bars: {total_bars}"

    # Parse metre to get slots per bar (1/16 resolution)
    num, denom = map(int, metre.split("/"))
    slots_per_bar = num * 4  # 4 sixteenths per quarter note

    # Convert anchors to slot indices
    anchor_slots: frozenset[int] = frozenset(
        _bar_beat_to_slot(bar_beat=a.bar_beat, slots_per_bar=slots_per_bar) for a in anchors
    )

    # Get phrase boundary slots
    phrase_boundaries = _get_phrase_boundaries(treatments=treatments, slots_per_bar=slots_per_bar)

    soprano_active: set[int] = set()
    bass_active: set[int] = set()
    soprano_durations: dict[int, Fraction] = {}
    bass_durations: dict[int, Fraction] = {}

    for t in treatments:
        bars = t["bars"]
        start_bar, end_bar = bars[0], bars[1]
        lead_voice = t.get("lead_voice")  # 0=upper, 1=lower, None=equal
        # When lead_voice is None (episode/cadential), NEITHER voice leads
        # Both get accompaniment (sparse) treatment for voice independence
        is_soprano_lead = lead_voice == 0
        is_bass_lead = lead_voice == 1
        s_slots, s_durs = _select_slots_for_voice(
            bar_start=start_bar, bar_end=end_bar,
            is_lead_voice=is_soprano_lead,
            density=density,
            slots_per_bar=slots_per_bar,
            anchor_slots=anchor_slots,
            phrase_boundary_slots=phrase_boundaries,
        )
        soprano_active.update(s_slots)
        soprano_durations.update(s_durs)
        b_slots, b_durs = _select_slots_for_voice(
            bar_start=start_bar, bar_end=end_bar,
            is_lead_voice=is_bass_lead,
            density=density,
            slots_per_bar=slots_per_bar,
            anchor_slots=anchor_slots,
            phrase_boundary_slots=phrase_boundaries,
        )
        bass_active.update(b_slots)
        bass_durations.update(b_durs)

    return RhythmPlan(
        soprano_active=frozenset(soprano_active),
        bass_active=frozenset(bass_active),
        soprano_durations=soprano_durations,
        bass_durations=bass_durations,
    )
