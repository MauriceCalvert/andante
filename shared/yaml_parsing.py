"""Shared YAML field parsers for schema and config loading.

Single source of truth (L017) for parsing signed degrees and key areas
from YAML data files.
"""
import re


def parse_signed_degree(raw: str | int | float, *, is_first: bool) -> tuple[int, str | None]:
    """Parse a signed degree string into (degree, direction).

    Format:
        First degree: unsigned (starting point), direction=None
        Subsequent: -N = down to N, N = same, +N = up to N

    Args:
        raw: Degree value as string ("+2", "-7", "1") or number.
        is_first: True if this is the first degree (no direction).

    Returns:
        (degree, direction) where degree is 1-7 and direction is up/down/same/None.
    """
    if isinstance(raw, (int, float)):
        degree = int(abs(raw))
        direction = None if is_first else "same"
        return degree, direction
    raw_str = str(raw).strip()
    if not raw_str:
        return 1, None
    if raw_str.startswith("+"):
        degree_str = raw_str[1:]
        direction = None if is_first else "up"
    elif raw_str.startswith("-"):
        degree_str = raw_str[1:]
        direction = None if is_first else "down"
    else:
        degree_str = raw_str
        direction = None if is_first else "same"
    degree = int(float(degree_str))
    return degree, direction


def parse_signed_degrees(raw_list: list) -> tuple[tuple[int, ...], tuple[str | None, ...]]:
    """Parse a list of signed degrees into degrees and directions.

    Args:
        raw_list: List of signed degree values.

    Returns:
        (degrees, directions) tuples.
    """
    degrees: list[int] = []
    directions: list[str | None] = []
    for i, raw in enumerate(raw_list):
        degree, direction = parse_signed_degree(raw, is_first=(i == 0))
        degrees.append(degree)
        directions.append(direction)
    return tuple(degrees), tuple(directions)


def parse_typical_keys(raw: str | None) -> tuple[str, ...] | None:
    """Parse typical_keys string into tuple of key areas.

    Examples:
        "IV -> V (-> vi)" -> ("IV", "V", "vi")
        "ii -> I" -> ("ii", "I")
        None -> None
    """
    if raw is None:
        return None
    pattern = r'[iIvV]+|[iI]{1,3}|[vV]{1,3}'
    matches: list[str] = re.findall(pattern, raw)
    if not matches:
        return None
    return tuple(matches)
