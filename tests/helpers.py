"""Helper functions for contract tests."""
from fractions import Fraction
from typing import Any
from shared.key import Key


def bar_of(
    offset: Fraction,
    metre: str,
    upbeat: Fraction,
) -> int:
    """Convert absolute offset to 1-based bar number."""
    bar_length, _ = parse_metre(metre=metre)
    bar: int = int((offset + upbeat) / bar_length) + 1
    assert bar >= 1, f"bar_of computed invalid bar {bar} for offset {offset}"
    return bar


def beat_of(
    offset: Fraction,
    metre: str,
    upbeat: Fraction,
) -> int:
    """Convert absolute offset to 1-based beat within bar."""
    bar_length, beat_unit = parse_metre(metre=metre)
    within_bar: Fraction = (offset + upbeat) % bar_length
    beat: int = int(within_bar / beat_unit) + 1
    assert beat >= 1, f"beat_of computed invalid beat {beat} for offset {offset}"
    return beat


def check_no_parallel(
    upper: tuple[Any, ...],
    lower: tuple[Any, ...],
    metre: str,
    forbidden_ic: frozenset[int],
) -> list[str]:
    """Check for parallel motion to forbidden intervals on strong beats."""
    upper_dict: dict[Fraction, int] = notes_at_offsets(notes=upper)
    lower_dict: dict[Fraction, int] = notes_at_offsets(notes=lower)
    common_offsets: set[Fraction] = set(upper_dict.keys()) & set(lower_dict.keys())
    strong_offsets: list[Fraction] = sorted(
        off for off in common_offsets if is_strong_beat(offset=off, metre=metre)
    )
    violations: list[str] = []
    for i in range(len(strong_offsets) - 1):
        off_a: Fraction = strong_offsets[i]
        off_b: Fraction = strong_offsets[i + 1]
        ic_a: int = interval_class(a=upper_dict[off_a], b=lower_dict[off_a])
        ic_b: int = interval_class(a=upper_dict[off_b], b=lower_dict[off_b])
        if ic_a in forbidden_ic and ic_b in forbidden_ic and ic_a == ic_b:
            violations.append(f"parallel {ic_a} at offsets {off_a} and {off_b}")
    return violations


def check_no_voice_overlap(
    upper: tuple[Any, ...],
    lower: tuple[Any, ...],
) -> list[str]:
    """Check for voice overlap where upper pitch is below lower pitch."""
    upper_dict: dict[Fraction, int] = notes_at_offsets(notes=upper)
    lower_dict: dict[Fraction, int] = notes_at_offsets(notes=lower)
    common_offsets: set[Fraction] = set(upper_dict.keys()) & set(lower_dict.keys())
    violations: list[str] = []
    for off in sorted(common_offsets):
        if upper_dict[off] < lower_dict[off]:
            violations.append(
                f"voice overlap at offset {off}: upper {upper_dict[off]} < lower {lower_dict[off]}"
            )
    return violations


def degree_at(
    midi: int,
    key: Key,
) -> int:
    """Convert MIDI pitch to scale degree 1-7."""
    pc: int = midi % 12
    tonic_pc: int = key.tonic_pc
    interval: int = (pc - tonic_pc) % 12
    scale: tuple[int, ...] = key.scale
    for idx, semitones in enumerate(scale):
        if semitones == interval:
            degree: int = idx + 1
            assert 1 <= degree <= 7, f"degree_at computed invalid degree {degree}"
            return degree
    assert False, f"MIDI {midi} (pc={pc}) not in scale of key {key.tonic} {key.mode}"


def interval_class(
    a: int,
    b: int,
) -> int:
    """Compute interval class (0-11) between two MIDI pitches."""
    return abs(a - b) % 12


def is_strong_beat(
    offset: Fraction,
    metre: str,
) -> bool:
    """Return True if offset falls on beat 1 of a bar."""
    bar_length, _ = parse_metre(metre=metre)
    return offset % bar_length == Fraction(0)


def notes_at_offsets(
    notes: tuple[Any, ...],
) -> dict[Fraction, int]:
    """Build dict mapping offset to MIDI pitch."""
    return {n.offset: n.pitch for n in notes}


def parse_metre(
    metre: str,
) -> tuple[Fraction, Fraction]:
    """Parse metre string to (bar_length, beat_unit)."""
    parts: list[str] = metre.split("/")
    assert len(parts) == 2, f"Invalid metre format: {metre}"
    numerator: int = int(parts[0])
    denominator: int = int(parts[1])
    bar_length: Fraction = Fraction(numerator, denominator)
    beat_unit: Fraction = Fraction(1, denominator)
    return bar_length, beat_unit
