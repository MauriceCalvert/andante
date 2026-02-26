"""Contour enforcement for planned subjects.

Checks that the pitches in each segment (head, tail) follow the
specified contour direction.  Also checks that the head contains
the vocabulary's signature interval.
"""


def _segment_contour(pitches: tuple[int, ...]) -> str | None:
    """Classify the contour of a pitch segment.

    Returns one of: "ascending", "descending", "arch", "dip", or None
    if the segment is too short or flat.
    """
    n: int = len(pitches)
    if n < 2:
        return None
    first: int = pitches[0]
    last: int = pitches[-1]
    peak_idx: int = 0
    trough_idx: int = 0
    for i in range(n):
        if pitches[i] > pitches[peak_idx]:
            peak_idx = i
        if pitches[i] < pitches[trough_idx]:
            trough_idx = i
    # Net direction.
    if last > first:
        net: str = "up"
    elif last < first:
        net = "down"
    else:
        net = "flat"
    # Interior extrema.
    peak_interior: bool = 0 < peak_idx < n - 1
    trough_interior: bool = 0 < trough_idx < n - 1
    if peak_interior and not trough_interior:
        return "arch"
    if trough_interior and not peak_interior:
        return "dip"
    if net == "up":
        return "ascending"
    if net == "down":
        return "descending"
    return None


def contour_matches(
    pitches: tuple[int, ...],
    target: str,
) -> bool:
    """Check whether a pitch segment matches the target contour."""
    actual: str | None = _segment_contour(pitches=pitches)
    return actual == target


def has_signature_interval(
    pitches: tuple[int, ...],
    min_interval: int,
) -> bool:
    """Check that the segment contains at least one leap >= min_interval."""
    for i in range(len(pitches) - 1):
        if abs(pitches[i + 1] - pitches[i]) >= min_interval:
            return True
    return False


def check_plan_contours(
    all_pitches: tuple[int, ...],
    head_n: int,
    head_contour: str,
    tail_contour: str,
    signature_interval: int,
) -> bool:
    """Check that a complete pitch sequence satisfies the plan's contour requirements."""
    head_pitches: tuple[int, ...] = all_pitches[:head_n]
    tail_pitches: tuple[int, ...] = all_pitches[head_n:]
    if not contour_matches(pitches=head_pitches, target=head_contour):
        return False
    if not contour_matches(pitches=tail_pitches, target=tail_contour):
        return False
    if not has_signature_interval(pitches=head_pitches, min_interval=signature_interval):
        return False
    return True
