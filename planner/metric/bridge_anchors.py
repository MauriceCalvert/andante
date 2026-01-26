"""Bridge anchor generation for uncovered bars."""
from builder.types import Anchor
from planner.metric.distribution import get_final_strong_beat
from planner.metric.pitch import compute_base_octave, degree_to_midi, snap_to_key
from shared.key import Key


def generate_bridge_anchors(
    total_bars: int,
    covered_bars: set[int],
    existing_anchors: list[Anchor],
    key: Key,
    soprano_median: int,
    bass_median: int,
    metre: str,
) -> list[Anchor]:
    """Generate bridge anchors for uncovered bars."""
    uncovered: list[int] = [b for b in range(1, total_bars + 1) if b not in covered_bars]
    if not uncovered:
        return []
    anchor_by_bar: dict[int, Anchor] = _build_anchor_lookup(existing_anchors)
    defaults: _DefaultPitches = _compute_defaults(key, soprano_median, bass_median)
    final_beat: int = get_final_strong_beat(metre)
    anchors: list[Anchor] = []
    for bar in uncovered:
        s_midi, b_midi = _interpolate_pitches(
            bar, total_bars, anchor_by_bar, defaults, key,
        )
        anchors.append(Anchor(
            bar_beat=f"{bar}.1",
            soprano_midi=s_midi,
            bass_midi=b_midi,
            schema="bridge",
            stage=1,
        ))
        if bar < total_bars:
            anchors.append(Anchor(
                bar_beat=f"{bar}.{final_beat}",
                soprano_midi=s_midi,
                bass_midi=b_midi,
                schema="bridge",
                stage=2,
            ))
    return anchors


class _DefaultPitches:
    """Default pitches for bridge interpolation."""
    
    def __init__(
        self,
        tonic_soprano: int,
        tonic_bass: int,
        dominant_soprano: int,
        dominant_bass: int,
    ) -> None:
        self.tonic_soprano: int = tonic_soprano
        self.tonic_bass: int = tonic_bass
        self.dominant_soprano: int = dominant_soprano
        self.dominant_bass: int = dominant_bass


def _build_anchor_lookup(anchors: list[Anchor]) -> dict[int, Anchor]:
    """Build lookup from bar number to first anchor in that bar."""
    anchor_by_bar: dict[int, Anchor] = {}
    for anchor in anchors:
        bar: int = int(anchor.bar_beat.split(".")[0])
        if bar not in anchor_by_bar:
            anchor_by_bar[bar] = anchor
    return anchor_by_bar


def _compute_defaults(
    key: Key,
    soprano_median: int,
    bass_median: int,
) -> _DefaultPitches:
    """Compute default tonic and dominant pitches."""
    s_octave: int = compute_base_octave(key, 1, soprano_median)
    b_octave: int = compute_base_octave(key, 1, bass_median)
    return _DefaultPitches(
        tonic_soprano=degree_to_midi(key, 1, s_octave),
        tonic_bass=degree_to_midi(key, 1, b_octave),
        dominant_soprano=degree_to_midi(key, 2, s_octave),
        dominant_bass=degree_to_midi(key, 5, b_octave),
    )


def _find_neighbours(
    bar: int,
    total_bars: int,
    anchor_by_bar: dict[int, Anchor],
) -> tuple[int | None, int | None]:
    """Find previous and next bars with anchors."""
    prev_bar: int | None = None
    next_bar: int | None = None
    for b in range(bar - 1, 0, -1):
        if b in anchor_by_bar:
            prev_bar = b
            break
    for b in range(bar + 1, total_bars + 1):
        if b in anchor_by_bar:
            next_bar = b
            break
    return prev_bar, next_bar


def _interpolate_pitches(
    bar: int,
    total_bars: int,
    anchor_by_bar: dict[int, Anchor],
    defaults: _DefaultPitches,
    key: Key,
) -> tuple[int, int]:
    """Interpolate soprano and bass pitches for uncovered bar."""
    prev_bar, next_bar = _find_neighbours(bar, total_bars, anchor_by_bar)
    if prev_bar is not None and next_bar is not None:
        return _linear_interpolate(bar, prev_bar, next_bar, anchor_by_bar, key)
    if prev_bar is not None:
        return _extrapolate_forward(bar, total_bars, anchor_by_bar[prev_bar], defaults)
    if next_bar is not None:
        anchor: Anchor = anchor_by_bar[next_bar]
        return anchor.soprano_midi, anchor.bass_midi
    return defaults.tonic_soprano, defaults.tonic_bass


def _linear_interpolate(
    bar: int,
    prev_bar: int,
    next_bar: int,
    anchor_by_bar: dict[int, Anchor],
    key: Key,
) -> tuple[int, int]:
    """Linear interpolation between two anchors."""
    prev_anchor: Anchor = anchor_by_bar[prev_bar]
    next_anchor: Anchor = anchor_by_bar[next_bar]
    t: float = (bar - prev_bar) / (next_bar - prev_bar)
    s_midi: int = int(prev_anchor.soprano_midi + t * (next_anchor.soprano_midi - prev_anchor.soprano_midi))
    b_midi: int = int(prev_anchor.bass_midi + t * (next_anchor.bass_midi - prev_anchor.bass_midi))
    return snap_to_key(s_midi, key), snap_to_key(b_midi, key)


def _extrapolate_forward(
    bar: int,
    total_bars: int,
    prev_anchor: Anchor,
    defaults: _DefaultPitches,
) -> tuple[int, int]:
    """Extrapolate forward from previous anchor."""
    bars_to_end: int = total_bars - bar
    if bars_to_end <= 2:
        return defaults.dominant_soprano, defaults.dominant_bass
    return prev_anchor.soprano_midi, prev_anchor.bass_midi
