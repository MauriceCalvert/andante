"""Main diagnostic checker - Bob's entry point."""
from fractions import Fraction

from engine.bob.complains import collect_complains
from engine.bob.formatter import Issue, Report
from engine.bob.notes import collect_notes
from engine.bob.refuses import collect_refuses
from engine.engine_types import RealisedPhrase
from engine.key import Key


def _parse_metre(metre: str) -> Fraction:
    """Parse metre string to bar duration in quarter notes."""
    parts = metre.split("/")
    if len(parts) != 2:
        return Fraction(4)  # Default 4/4
    num, denom = int(parts[0]), int(parts[1])
    # Bar duration in quarter notes: num * (4 / denom)
    return Fraction(num * 4, denom)


def _key_to_tonic_pc(key: Key) -> int:
    """Get tonic pitch class (0-11) from Key."""
    # Map note names to pitch class
    name_to_pc = {
        "c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11,
    }
    name = key.tonic.lower().rstrip("#b")
    pc = name_to_pc.get(name, 0)
    if "#" in key.tonic.lower():
        pc = (pc + 1) % 12
    elif "b" in key.tonic.lower() and name != "b":
        pc = (pc - 1) % 12
    return pc


def diagnose(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction | None = None,
    metre: str = "4/4",
    key: Key | None = None,
) -> Report:
    """Run all diagnostic checks on realised phrases.

    Args:
        phrases: List of RealisedPhrase objects to check
        bar_duration: Duration of one bar in quarter notes (derived from metre if None)
        metre: Time signature string like "4/4" or "3/4"
        key: Key object for tonic detection (defaults to C major)

    Returns:
        Report containing all issues found
    """
    if bar_duration is None:
        bar_duration = _parse_metre(metre)

    tonic_pc = _key_to_tonic_pc(key) if key else 0

    issues: list[Issue] = []

    # Hard constraints (REFUSES)
    issues.extend(collect_refuses(phrases, bar_duration))

    # Soft constraints (COMPLAINS)
    issues.extend(collect_complains(phrases, bar_duration))

    # Observations (NOTES)
    issues.extend(collect_notes(phrases, bar_duration, tonic_pc))

    # Sort by bar, then beat
    issues.sort(key=lambda i: (i.bar, i.beat))

    return Report(issues=issues)
