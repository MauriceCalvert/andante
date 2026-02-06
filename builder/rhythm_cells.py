"""Rhythm cell vocabulary loader.

Loads genre-specific rhythm cells from YAML. Each cell fills exactly
one bar and is tagged with genre names and character.
"""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml

from shared.constants import VALID_DURATIONS

DATA_DIR: Path = Path(__file__).parent.parent / "data"
VALID_DURATIONS_SET: frozenset[Fraction] = frozenset(VALID_DURATIONS)
METRE_BAR_LENGTH: dict[str, Fraction] = {
    "3/4": Fraction(3, 4),
    "4/4": Fraction(1),
}


@dataclass(frozen=True)
class RhythmCell:
    """One bar's rhythm pattern."""
    name: str
    metre: str
    durations: tuple[Fraction, ...]
    character: str
    genre_tags: frozenset[str]


_cache: dict[str, list[RhythmCell]] | None = None


def _parse_fraction(s: str) -> Fraction:
    """Parse fraction string like '1/4' or '1' to Fraction."""
    if "/" in s:
        num, denom = s.split("/")
        return Fraction(int(num), int(denom))
    return Fraction(int(s))


def _validate_cell(
    name: str,
    metre: str,
    durations: tuple[Fraction, ...],
    genre_tags: frozenset[str],
) -> None:
    """Validate cell invariants."""
    assert metre in METRE_BAR_LENGTH, f"Cell '{name}': unknown metre '{metre}'"
    expected_length: Fraction = METRE_BAR_LENGTH[metre]
    actual_length: Fraction = sum(durations, Fraction(0))
    assert actual_length == expected_length, (
        f"Cell '{name}': durations sum to {actual_length}, expected {expected_length}"
    )
    for dur in durations:
        assert dur in VALID_DURATIONS_SET, (
            f"Cell '{name}': duration {dur} not in VALID_DURATIONS"
        )
    assert len(genre_tags) > 0, f"Cell '{name}': must have at least one genre_tag"


def get_cells_for_genre(
    genre: str,
    metre: str,
) -> list[RhythmCell]:
    """Return cells matching genre and metre, sorted by character."""
    all_cells: dict[str, list[RhythmCell]] = load_rhythm_cells()
    cells_for_metre: list[RhythmCell] = all_cells.get(metre, [])
    matching: list[RhythmCell] = [
        c for c in cells_for_metre if genre in c.genre_tags
    ]
    return sorted(matching, key=lambda c: c.character)


def load_rhythm_cells() -> dict[str, list[RhythmCell]]:
    """Load cells, keyed by metre. Cached."""
    global _cache
    if _cache is not None:
        return _cache
    path: Path = DATA_DIR / "rhythm_cells" / "cells.yaml"
    assert path.exists(), f"Rhythm cells file not found: {path}"
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)
    result: dict[str, list[RhythmCell]] = {}
    for name, data in raw.items():
        metre: str = data["metre"]
        durations: tuple[Fraction, ...] = tuple(
            _parse_fraction(s=d) for d in data["durations"]
        )
        character: str = data["character"]
        genre_tags: frozenset[str] = frozenset(data["genre_tags"])
        _validate_cell(name=name, metre=metre, durations=durations, genre_tags=genre_tags)
        cell: RhythmCell = RhythmCell(
            name=name,
            metre=metre,
            durations=durations,
            character=character,
            genre_tags=genre_tags,
        )
        result.setdefault(metre, []).append(cell)
    _cache = result
    return result


def select_cell(
    genre: str,
    metre: str,
    bar_index: int,
    prefer_character: str = "plain",
    avoid_name: str | None = None,
) -> RhythmCell:
    """Select a rhythm cell for one bar. Deterministic (A005)."""
    candidates: list[RhythmCell] = get_cells_for_genre(genre=genre, metre=metre)
    assert len(candidates) > 0, (
        f"No rhythm cells for genre '{genre}' in metre '{metre}'"
    )
    preferred: list[RhythmCell] = [
        c for c in candidates if c.character == prefer_character
    ]
    pool: list[RhythmCell] = preferred if preferred else candidates
    if avoid_name is not None and len(pool) > 1:
        pool = [c for c in pool if c.name != avoid_name] or pool
    return pool[bar_index % len(pool)]
