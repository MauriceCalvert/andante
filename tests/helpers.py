"""Helper functions for contract tests."""
from fractions import Fraction
from pathlib import Path
from typing import Any
from shared.key import Key

DATA_DIR: Path = Path(__file__).parent.parent / "data"


def get_phrase_genres() -> tuple[str, ...]:
    """Return genres that have rhythm cells for their metre."""
    from builder.config_loader import load_configs
    from builder.rhythm_cells import get_cells_for_genre
    result: list[str] = []
    for path in sorted((DATA_DIR / "genres").glob("*.yaml")):
        if path.stem == "_default":
            continue
        genre: str = path.stem
        try:
            config = load_configs(genre=genre, key="c_major", affect="Zierlich")
            gc = config["genre"]
            cells = get_cells_for_genre(genre=genre, metre=gc.metre)
            if len(cells) > 0:
                result.append(genre)
        except Exception:
            continue
    return tuple(result)


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


def _notes_by_offset(
    notes: tuple[Any, ...],
) -> dict[Fraction, list[int]]:
    """Build dict mapping offset to list of MIDI pitches (handles duplicates)."""
    result: dict[Fraction, list[int]] = {}
    for n in notes:
        result.setdefault(n.offset, []).append(n.pitch)
    return result


def check_no_parallel(
    upper: tuple[Any, ...],
    lower: tuple[Any, ...],
    metre: str,
    forbidden_ic: frozenset[int],
) -> list[str]:
    """Check for parallel motion to forbidden intervals on strong beats."""
    upper_by_off: dict[Fraction, list[int]] = _notes_by_offset(notes=upper)
    lower_by_off: dict[Fraction, list[int]] = _notes_by_offset(notes=lower)
    common_offsets: set[Fraction] = set(upper_by_off.keys()) & set(lower_by_off.keys())
    strong_offsets: list[Fraction] = sorted(
        off for off in common_offsets if is_strong_beat(offset=off, metre=metre)
    )
    violations: list[str] = []
    for i in range(len(strong_offsets) - 1):
        off_a: Fraction = strong_offsets[i]
        off_b: Fraction = strong_offsets[i + 1]
        for up_a in upper_by_off[off_a]:
            for lo_a in lower_by_off[off_a]:
                ic_a: int = interval_class(a=up_a, b=lo_a)
                if ic_a not in forbidden_ic:
                    continue
                for up_b in upper_by_off[off_b]:
                    for lo_b in lower_by_off[off_b]:
                        ic_b: int = interval_class(a=up_b, b=lo_b)
                        if ic_b == ic_a:
                            violations.append(
                                f"parallel {ic_a} at offsets {off_a} and {off_b}"
                            )
    return violations


def check_no_voice_overlap(
    upper: tuple[Any, ...],
    lower: tuple[Any, ...],
) -> list[str]:
    """Check for voice overlap where upper pitch is below lower pitch."""
    upper_by_off: dict[Fraction, list[int]] = _notes_by_offset(notes=upper)
    lower_by_off: dict[Fraction, list[int]] = _notes_by_offset(notes=lower)
    common_offsets: set[Fraction] = set(upper_by_off.keys()) & set(lower_by_off.keys())
    violations: list[str] = []
    for off in sorted(common_offsets):
        for up in upper_by_off[off]:
            for lo in lower_by_off[off]:
                if up < lo:
                    violations.append(
                        f"voice overlap at offset {off}: upper {up} < lower {lo}"
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
    """Build dict mapping offset to MIDI pitch.

    If duplicate offsets exist (phrase boundary overlap), the last note wins.
    Callers requiring all notes at an offset should iterate directly.
    """
    result: dict[Fraction, int] = {}
    for n in notes:
        if n.offset in result:
            import logging
            logging.getLogger(__name__).debug(
                "Duplicate offset %s: pitch %d replaced by %d",
                n.offset, result[n.offset], n.pitch,
            )
        result[n.offset] = n.pitch
    return result


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
