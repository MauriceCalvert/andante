"""Rhythm cell vocabulary loader.

Loads genre-specific rhythm cells from YAML. Each cell fills exactly
one bar and is tagged with genre names and character.
"""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml

from shared.constants import METRE_BAR_LENGTH, STRONG_BEAT_OFFSETS, VALID_DURATIONS_SET
from shared.music_math import parse_fraction

DATA_DIR: Path = Path(__file__).parent.parent / "data"


@dataclass(frozen=True)
class RhythmCell:
    """One bar's rhythm pattern."""
    name: str
    metre: str
    durations: tuple[Fraction, ...]
    character: str
    genre_tags: frozenset[str]
    accent_pattern: tuple[bool, ...]


_cache: dict[str, list[RhythmCell]] | None = None


def _compute_accent_pattern(
    durations: tuple[Fraction, ...],
    metre: str,
) -> tuple[bool, ...]:
    """Derive accent pattern from note onsets and metre strong beats."""
    strong_offsets: tuple[Fraction, ...] = STRONG_BEAT_OFFSETS.get(metre, (Fraction(0),))
    accents: list[bool] = []
    offset: Fraction = Fraction(0)
    for dur in durations:
        accents.append(offset in strong_offsets)
        offset += dur
    return tuple(accents)


def _parse_accent_pattern(
    raw: list[bool] | None,
    durations: tuple[Fraction, ...],
    metre: str,
    name: str,
) -> tuple[bool, ...]:
    """Parse explicit accent_pattern from YAML or compute default."""
    if raw is not None:
        assert len(raw) == len(durations), (
            f"Cell '{name}': accent_pattern length {len(raw)} "
            f"!= durations length {len(durations)}"
        )
        return tuple(raw)
    return _compute_accent_pattern(durations=durations, metre=metre)


def _validate_cell(
    name: str,
    metre: str,
    durations: tuple[Fraction, ...],
    genre_tags: frozenset[str],
    accent_pattern: tuple[bool, ...],
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
    assert len(accent_pattern) == len(durations), (
        f"Cell '{name}': accent_pattern length {len(accent_pattern)} "
        f"!= durations length {len(durations)}"
    )


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
            parse_fraction(s=d) for d in data["durations"]
        )
        character: str = data["character"]
        genre_tags: frozenset[str] = frozenset(data["genre_tags"])
        accent_pattern: tuple[bool, ...] = _parse_accent_pattern(
            raw=data.get("accent_pattern"),
            durations=durations,
            metre=metre,
            name=name,
        )
        _validate_cell(name=name, metre=metre, durations=durations, genre_tags=genre_tags, accent_pattern=accent_pattern)
        cell: RhythmCell = RhythmCell(
            name=name,
            metre=metre,
            durations=durations,
            character=character,
            genre_tags=genre_tags,
            accent_pattern=accent_pattern,
        )
        result.setdefault(metre, []).append(cell)
    _cache = result
    return result


def _cell_onsets(cell: RhythmCell) -> frozenset[Fraction]:
    """Return bar-relative onset offsets for a cell."""
    offsets: list[Fraction] = []
    pos: Fraction = Fraction(0)
    for dur in cell.durations:
        offsets.append(pos)
        pos += dur
    return frozenset(offsets)


def select_cell(
    genre: str,
    metre: str,
    bar_index: int,
    prefer_character: str = "plain",
    avoid_name: str | None = None,
    required_onsets: frozenset[Fraction] | None = None,
) -> RhythmCell:
    """Select a rhythm cell for one bar. Deterministic (A005)."""
    candidates: list[RhythmCell] = get_cells_for_genre(genre=genre, metre=metre)
    assert len(candidates) > 0, (
        f"No rhythm cells for genre '{genre}' in metre '{metre}'"
    )
    if required_onsets is not None:
        candidates = [
            c for c in candidates
            if required_onsets.issubset(_cell_onsets(cell=c))
        ]
        assert len(candidates) > 0, (
            f"No rhythm cells for genre '{genre}' in metre '{metre}' "
            f"with onsets at {sorted(required_onsets)}"
        )
    preferred: list[RhythmCell] = [
        c for c in candidates if c.character == prefer_character
    ]
    pool: list[RhythmCell] = preferred if preferred else candidates
    if avoid_name is not None and len(pool) > 1:
        pool = [c for c in pool if c.name != avoid_name] or pool
    return pool[bar_index % len(pool)]
