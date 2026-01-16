"""Main diagnostic checker - Bob's entry point."""
from fractions import Fraction

from engine.bob import vocabulary as vocab
from engine.bob.complains import collect_complains
from engine.bob.formatter import Issue, Report, offset_to_bar_beat
from engine.bob.notes import collect_notes
from engine.bob.refuses import collect_refuses_non_guard
from engine.engine_types import ExpandedPhrase, RealisedPhrase
from engine.guards.registry import Diagnostic
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


# Map guard IDs to Bob vocabulary
_GUARD_TO_VOCAB: dict[str, str] = {
    "tex_001": vocab.PARALLEL_FIFTH,
    "tex_002": vocab.PARALLEL_OCTAVE,
    "vl_001": vocab.DIRECT_FIFTH,
    "vl_002": vocab.DIRECT_OCTAVE,
    "diss_001": vocab.UNPREPARED,
    "diss_002": vocab.UNRESOLVED,
    "diss_003": vocab.RESOLVED_UP,
}


def _diagnostic_to_issue(d: Diagnostic, bar_duration: Fraction) -> Issue | None:
    """Convert guard Diagnostic to Bob Issue.

    Returns None if the diagnostic shouldn't be shown as a REFUSES issue.
    """
    msg = _GUARD_TO_VOCAB.get(d.guard_id)
    if msg is None:
        return None  # Not a REFUSES-level issue

    # Only blockers become REFUSES
    if d.severity != "blocker":
        return None

    if d.offset is None:
        return None

    bar, beat = offset_to_bar_beat(d.offset, bar_duration)
    # Extract voice info from location (e.g., "phrase 1 voices 0-1")
    voices = "soprano-bass"
    if "voices" in d.location:
        parts = d.location.split("voices ")
        if len(parts) > 1:
            voice_nums = parts[1].split("-")
            if len(voice_nums) == 2:
                # Could map to voice names, but soprano-bass is usually correct for 2-voice
                pass

    return Issue(
        category="REFUSES",
        bar=bar,
        beat=beat,
        voices=voices,
        message=msg,
    )


def diagnose(
    phrases: list[RealisedPhrase],
    bar_duration: Fraction | None = None,
    metre: str = "4/4",
    key: Key | None = None,
    guard_diagnostics: list[Diagnostic] | None = None,
) -> Report:
    """Run all diagnostic checks on realised phrases.

    Args:
        phrases: List of RealisedPhrase objects to check
        bar_duration: Duration of one bar in quarter notes (derived from metre if None)
        metre: Time signature string like "4/4" or "3/4"
        key: Key object for tonic detection (defaults to C major)
        guard_diagnostics: Pre-computed guard diagnostics (uses guard system's
            Bach-practical filtering). If None, Bob runs its own checks.

    Returns:
        Report containing all issues found
    """
    if bar_duration is None:
        bar_duration = _parse_metre(metre)

    tonic_pc = _key_to_tonic_pc(key) if key else 0

    issues: list[Issue] = []

    # Hard constraints (REFUSES)
    if guard_diagnostics is not None:
        # Use guard system's diagnostics (already Bach-practical filtered)
        for d in guard_diagnostics:
            issue = _diagnostic_to_issue(d, bar_duration)
            if issue is not None:
                issues.append(issue)
        # Add non-guard REFUSES checks (voice crossing, verbatim repetition)
        issues.extend(collect_refuses_non_guard(phrases, bar_duration))
    else:
        # Fall back to Bob's own checks (no Bach-practical filtering)
        from engine.bob.refuses import collect_refuses
        issues.extend(collect_refuses(phrases, bar_duration))

    # Soft constraints (COMPLAINS)
    issues.extend(collect_complains(phrases, bar_duration))

    # Observations (NOTES)
    issues.extend(collect_notes(phrases, bar_duration, tonic_pc))

    # Sort by bar, then beat
    issues.sort(key=lambda i: (i.bar, i.beat))

    return Report(issues=issues)
