"""Phrase position classification."""
from typing import Literal


PHRASE_ZONE = Literal["opening", "middle", "cadential"]


def phrase_zone(
    phrase_bar: int,
    total_bars: int,
) -> PHRASE_ZONE:
    """Classify bar position within a phrase.

    Returns "opening", "middle", or "cadential" based on proportional position.
    phrase_bar is 1-based.
    """
    assert phrase_bar >= 1, f"phrase_bar must be >= 1, got {phrase_bar}"
    assert total_bars >= 1, f"total_bars must be >= 1, got {total_bars}"

    # Defensive: handle invalid total_bars
    if total_bars <= 0:
        return "opening"

    # Single bar phrase
    if total_bars == 1:
        return "cadential"

    # Two bar phrase
    if total_bars == 2:
        return "opening" if phrase_bar == 1 else "cadential"

    # Multi-bar phrase: opening = first 25%, cadential = last 25%, middle = rest
    opening_end: int = max(1, int(total_bars * 0.25))
    cadential_start: int = int(total_bars * 0.75) + 1

    if phrase_bar <= opening_end:
        return "opening"
    elif phrase_bar >= cadential_start:
        return "cadential"
    else:
        return "middle"
