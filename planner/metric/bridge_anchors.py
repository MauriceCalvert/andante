"""Bridge anchor generation for uncovered bars."""
from builder.types import Anchor
from planner.metric.distribution import get_final_strong_beat
from shared.key import Key

DEFAULT_SOPRANO_DEGREE: int = 1
DEFAULT_BASS_DEGREE: int = 1
DOMINANT_SOPRANO_DEGREE: int = 2
DOMINANT_BASS_DEGREE: int = 5


def generate_bridge_anchors(
    total_bars: int,
    covered_bars: set[int],
    existing_anchors: list[Anchor],
    key: Key,
    metre: str,
) -> list[Anchor]:
    """Generate bridge anchors for uncovered bars."""
    uncovered: list[int] = [b for b in range(1, total_bars + 1) if b not in covered_bars]
    if not uncovered:
        return []
    anchor_by_bar: dict[int, Anchor] = _build_anchor_lookup(existing_anchors)
    final_beat: int = get_final_strong_beat(metre)
    anchors: list[Anchor] = []
    for bar in uncovered:
        s_deg, b_deg, local_key = _interpolate_degrees(
            bar, total_bars, anchor_by_bar, key,
        )
        anchors.append(Anchor(
            bar_beat=f"{bar}.1",
            soprano_degree=s_deg,
            bass_degree=b_deg,
            local_key=local_key,
            schema="bridge",
            stage=1,
        ))
        if bar < total_bars:
            anchors.append(Anchor(
                bar_beat=f"{bar}.{final_beat}",
                soprano_degree=s_deg,
                bass_degree=b_deg,
                local_key=local_key,
                schema="bridge",
                stage=2,
            ))
    return anchors


def _build_anchor_lookup(anchors: list[Anchor]) -> dict[int, Anchor]:
    """Build lookup from bar number to first anchor in that bar."""
    anchor_by_bar: dict[int, Anchor] = {}
    for anchor in anchors:
        bar: int = int(anchor.bar_beat.split(".")[0])
        if bar not in anchor_by_bar:
            anchor_by_bar[bar] = anchor
    return anchor_by_bar


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


def _interpolate_degrees(
    bar: int,
    total_bars: int,
    anchor_by_bar: dict[int, Anchor],
    home_key: Key,
) -> tuple[int, int, Key]:
    """Interpolate soprano and bass degrees for uncovered bar."""
    prev_bar, next_bar = _find_neighbours(bar, total_bars, anchor_by_bar)
    if prev_bar is not None and next_bar is not None:
        return _linear_interpolate_degrees(bar, prev_bar, next_bar, anchor_by_bar)
    if prev_bar is not None:
        return _extrapolate_forward(bar, total_bars, anchor_by_bar[prev_bar], home_key)
    if next_bar is not None:
        anchor: Anchor = anchor_by_bar[next_bar]
        return anchor.soprano_degree, anchor.bass_degree, anchor.local_key
    return DEFAULT_SOPRANO_DEGREE, DEFAULT_BASS_DEGREE, home_key


def _linear_interpolate_degrees(
    bar: int,
    prev_bar: int,
    next_bar: int,
    anchor_by_bar: dict[int, Anchor],
) -> tuple[int, int, Key]:
    """Linear interpolation between two anchors in degree space."""
    prev_anchor: Anchor = anchor_by_bar[prev_bar]
    next_anchor: Anchor = anchor_by_bar[next_bar]
    t: float = (bar - prev_bar) / (next_bar - prev_bar)
    s_deg: int = _interpolate_degree(prev_anchor.soprano_degree, next_anchor.soprano_degree, t)
    b_deg: int = _interpolate_degree(prev_anchor.bass_degree, next_anchor.bass_degree, t)
    local_key: Key = prev_anchor.local_key if t < 0.5 else next_anchor.local_key
    return s_deg, b_deg, local_key


def _interpolate_degree(
    start_deg: int,
    end_deg: int,
    t: float,
) -> int:
    """Interpolate between two degrees (1-7), taking shortest path."""
    diff: int = end_deg - start_deg
    if abs(diff) > 3:
        if diff > 0:
            diff -= 7
        else:
            diff += 7
    result: int = round(start_deg + t * diff)
    return ((result - 1) % 7) + 1


def _extrapolate_forward(
    bar: int,
    total_bars: int,
    prev_anchor: Anchor,
    home_key: Key,
) -> tuple[int, int, Key]:
    """Extrapolate forward from previous anchor."""
    bars_to_end: int = total_bars - bar
    if bars_to_end <= 2:
        return DOMINANT_SOPRANO_DEGREE, DOMINANT_BASS_DEGREE, home_key
    return prev_anchor.soprano_degree, prev_anchor.bass_degree, prev_anchor.local_key
