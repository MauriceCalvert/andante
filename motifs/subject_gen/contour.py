"""Pitch contour analysis and classification."""


def _find_climax(pitches: list[int]) -> tuple[int, int, str]:
    """Find the climax: extreme pitch that is unique and followed by direction change."""
    n = len(pitches)
    hi_val = max(pitches)
    lo_val = min(pitches)
    hi_span = hi_val - pitches[0]
    lo_span = pitches[0] - lo_val
    if hi_span >= lo_span:
        candidates = [i for i in range(n) if pitches[i] == hi_val]
        direction = 'high'
    else:
        candidates = [i for i in range(n) if pitches[i] == lo_val]
        direction = 'low'
    if len(candidates) != 1:
        return (-1, 0, '')
    ci = candidates[0]
    if ci == 0 or ci == n - 1:
        return (-1, 0, '')
    if direction == 'high':
        if pitches[ci + 1] >= pitches[ci]:
            return (-1, 0, '')
    else:
        if pitches[ci + 1] <= pitches[ci]:
            return (-1, 0, '')
    return (ci, pitches[ci], direction)


def _find_high_climax(pitches: list[int]) -> tuple[int, int]:
    """Find unique high-point index and pitch, or (-1, 0) if none."""
    hi_val = max(pitches)
    candidates = [i for i in range(len(pitches)) if pitches[i] == hi_val]
    if len(candidates) != 1:
        return (-1, 0)
    ci = candidates[0]
    if ci == 0 or ci == len(pitches) - 1:
        return (-1, 0)
    if pitches[ci + 1] >= pitches[ci]:
        return (-1, 0)
    return (ci, hi_val)


def _find_low_climax(pitches: list[int]) -> tuple[int, int]:
    """Find unique low-point index and pitch, or (-1, 0) if none."""
    lo_val = min(pitches)
    candidates = [i for i in range(len(pitches)) if pitches[i] == lo_val]
    if len(candidates) != 1:
        return (-1, 0)
    ci = candidates[0]
    if ci == 0 or ci == len(pitches) - 1:
        return (-1, 0)
    if pitches[ci + 1] <= pitches[ci]:
        return (-1, 0)
    return (ci, lo_val)


def _opening_direction(pitches: list[int]) -> int:
    """Net direction of the first third of the melody: +1 up, -1 down, 0 flat."""
    third = max(2, len(pitches) // 3)
    net = pitches[third] - pitches[0]
    return 1 if net > 0 else (-1 if net < 0 else 0)


def _derive_shape_name(pitches: list[int]) -> str:
    """Derive shape from pitch contour using dominant climax and opening direction."""
    n = len(pitches)
    hi_ci, _ = _find_high_climax(pitches)
    lo_ci, _ = _find_low_climax(pitches)
    hi_span = max(pitches) - pitches[0]
    lo_span = pitches[0] - min(pitches)
    opens_up = _opening_direction(pitches) >= 0
    # Zigzag: both a valid high and low climax on opposite sides of start,
    # or dominant extreme with ending that reverses past origin.
    if hi_ci >= 0 and lo_ci >= 0 and hi_span > 0 and lo_span > 0:
        return 'zigzag'
    # Determine dominant extreme
    if hi_ci >= 0 and lo_ci >= 0:
        use_high = (hi_span > lo_span) or (hi_span == lo_span and hi_ci <= lo_ci)
    elif hi_ci >= 0:
        use_high = True
    elif lo_ci >= 0:
        use_high = False
    else:
        net = pitches[-1] - pitches[0]
        return 'ascending' if net > 0 else 'descending' if net < 0 else 'flat'
    # Arch/swoop must end at or below start (no cup at end).
    # Dip/valley must end at or above start (no cap at end).
    if use_high and pitches[-1] > pitches[0]:
        return 'zigzag'
    if not use_high and pitches[-1] < pitches[0]:
        return 'zigzag'
    if use_high:
        return 'arch' if opens_up else 'swoop'
    else:
        return 'dip' if not opens_up else 'valley'


def _derive_leap_info(ivs: tuple[int, ...]) -> tuple[int, str, str]:
    """Derive leap_size, leap_direction, tail_direction."""
    max_abs = 0
    max_iv = 0
    for iv in ivs:
        if abs(iv) > max_abs:
            max_abs = abs(iv)
            max_iv = iv
    second_half = ivs[len(ivs) // 2:]
    net = sum(second_half)
    return (
        max_abs,
        "up" if max_iv > 0 else "down",
        "down" if net < 0 else "up",
    )
