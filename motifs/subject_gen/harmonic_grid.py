"""Harmonic grid data and lookup for baroque melody generation.

Pure data + lookup module providing harmonic context for the melody
generator.  No generation logic.  No dependencies on the existing
pitch pipeline.
"""
import logging

from shared.constants import MAJOR_SCALE, NATURAL_MINOR_SCALE

logger: logging.Logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# ── Harmonic rhythm thresholds (section 1.1) ────────────────────────────

FAST_THRESHOLD: float = 3.0
MEDIUM_THRESHOLD: float = 1.5

# ── Harmonic levels ─────────────────────────────────────────────────────

LEVEL_FAST: str = "fast"
LEVEL_MEDIUM: str = "medium"
LEVEL_SLOW: str = "slow"

_VALID_LEVELS: frozenset[str] = frozenset({LEVEL_FAST, LEVEL_MEDIUM, LEVEL_SLOW})

# ── Modes ───────────────────────────────────────────────────────────────

MODE_MAJOR: str = "major"
MODE_MINOR: str = "minor"

_VALID_MODES: frozenset[str] = frozenset({MODE_MAJOR, MODE_MINOR})

# ── Directions ──────────────────────────────────────────────────────────

DIR_ASCENDING: str = "ascending"
DIR_DESCENDING: str = "descending"

_VALID_DIRECTIONS: frozenset[str] = frozenset({DIR_ASCENDING, DIR_DESCENDING})

# ── Raisable degrees (0-based mod 7) ───────────────────────────────────
# Degrees 5 (6th step) and 6 (7th step) may be raised in minor mode.

RAISABLE_DEGREES: frozenset[int] = frozenset({5, 6})

# ── Octave constants ───────────────────────────────────────────────────

_DEGREES_PER_OCTAVE: int = 7
_SEMITONES_PER_OCTAVE: int = 12


# =============================================================================
# Stock progressions (sections 1.2-1.4)
# =============================================================================

# Major-mode Roman numerals.  For minor mode, apply minor_equivalent().

_PROGRESSIONS: dict[tuple[str, str], tuple[str, ...]] = {
    # Fast: 8 slots, one chord per beat (section 1.2)
    (LEVEL_FAST, "A"): ("I", "I", "I", "V", "V", "V", "V", "I"),
    (LEVEL_FAST, "B"): ("I", "I", "IV", "IV", "V", "V", "V", "I"),
    (LEVEL_FAST, "C"): ("I", "I", "ii", "ii", "V", "V", "V", "I"),
    (LEVEL_FAST, "D"): ("I", "I", "I", "I", "V", "V", "I", "I"),
    (LEVEL_FAST, "E"): ("I", "I", "IV", "V", "V", "V", "V", "I"),
    (LEVEL_FAST, "F"): ("I", "I", "I", "V", "V", "V", "I", "I"),
    # Medium: 4 slots, one chord per half-bar (section 1.3)
    (LEVEL_MEDIUM, "A"): ("I", "V", "V", "I"),
    (LEVEL_MEDIUM, "B"): ("I", "IV", "V", "I"),
    (LEVEL_MEDIUM, "C"): ("I", "ii", "V", "I"),
    (LEVEL_MEDIUM, "D"): ("I", "I", "V", "I"),
    # Slow: 2 slots, one chord per bar (section 1.4)
    (LEVEL_SLOW, "A"): ("I", "V"),
    (LEVEL_SLOW, "B"): ("I", "I"),
}

# Pre-compute per-level pattern tuples for get_progressions().
_tmp_by_level: dict[str, list[tuple[str, ...]]] = {}
for _key, _prog in _PROGRESSIONS.items():
    _tmp_by_level.setdefault(_key[0], []).append(_prog)

_PROGRESSIONS_BY_LEVEL: dict[str, tuple[tuple[str, ...], ...]] = {
    k: tuple(v) for k, v in _tmp_by_level.items()
}
del _tmp_by_level, _key, _prog


# =============================================================================
# Chord-tone sets (section 1.6)
# =============================================================================

# Keyed by (mode, chord_name), value is frozenset of 0-based scale
# degrees (mod 7).

_CHORD_TONES: dict[tuple[str, str], frozenset[int]] = {
    # Major mode
    (MODE_MAJOR, "I"): frozenset({0, 2, 4}),
    (MODE_MAJOR, "IV"): frozenset({0, 3, 5}),
    (MODE_MAJOR, "V"): frozenset({1, 4, 6}),
    (MODE_MAJOR, "ii"): frozenset({1, 3, 5}),
    # Minor mode
    (MODE_MINOR, "i"): frozenset({0, 2, 4}),
    (MODE_MINOR, "iv"): frozenset({0, 3, 5}),
    (MODE_MINOR, "V"): frozenset({1, 4, 6}),
    (MODE_MINOR, "iio"): frozenset({1, 3, 5}),
}

# Degrees requiring chromatic raising, keyed by (mode, chord).
# Only minor V: degree 6 is the raised 7th (leading tone).

_RAISED_CHORD_DEGREES: dict[tuple[str, str], frozenset[int]] = {
    (MODE_MINOR, "V"): frozenset({6}),
}


# =============================================================================
# Minor equivalents (section 1.5)
# =============================================================================

_MINOR_EQUIVALENTS: dict[str, str] = {
    "I": "i",
    "IV": "iv",
    "ii": "iio",
    "V": "V",
}


# =============================================================================
# Scale semitone tables
# =============================================================================

_SCALE_SEMITONES: dict[str, tuple[int, ...]] = {
    MODE_MAJOR: MAJOR_SCALE,
    MODE_MINOR: NATURAL_MINOR_SCALE,
}


# =============================================================================
# Public functions (alphabetical)
# =============================================================================

def chord_at_tick(
    progression: tuple[str, ...],
    tick_offset: int,
    bar_ticks: int,
    n_bars: int,
) -> str:
    """Return the active chord at the given tick offset within the progression."""
    assert len(progression) > 0, "progression must not be empty"
    assert tick_offset >= 0, (
        f"tick_offset must be >= 0, got {tick_offset}"
    )
    assert bar_ticks > 0, (
        f"bar_ticks must be > 0, got {bar_ticks}"
    )
    assert n_bars > 0, (
        f"n_bars must be > 0, got {n_bars}"
    )
    total_ticks: int = n_bars * bar_ticks
    assert tick_offset < total_ticks, (
        f"tick_offset ({tick_offset}) must be < total_ticks ({total_ticks})"
    )
    n_slots: int = len(progression)
    assert total_ticks % n_slots == 0, (
        f"total ticks ({total_ticks}) must divide evenly by "
        f"progression length ({n_slots})"
    )
    slot_width: int = total_ticks // n_slots
    slot_index: int = tick_offset // slot_width
    return progression[slot_index]


def chord_tones(
    mode: str,
    chord: str,
) -> frozenset[int]:
    """Return the set of 0-based scale degrees (mod 7) for the given chord."""
    lookup_key: tuple[str, str] = (mode, chord)
    assert lookup_key in _CHORD_TONES, (
        f"unknown (mode, chord) pair: ({mode!r}, {chord!r}). "
        f"Valid pairs: {sorted(_CHORD_TONES.keys())}"
    )
    return _CHORD_TONES[lookup_key]


def degree_to_semitone(
    degree: int,
    mode: str,
    raised: bool = False,
) -> int:
    """Convert a 0-based scale degree to semitone offset from tonic."""
    assert mode in _VALID_MODES, (
        f"mode must be one of {_VALID_MODES!r}, got {mode!r}"
    )
    deg_mod7: int = degree % _DEGREES_PER_OCTAVE
    octave: int = degree // _DEGREES_PER_OCTAVE
    if raised and mode == MODE_MINOR:
        assert deg_mod7 in RAISABLE_DEGREES, (
            f"raised=True only valid for degrees {RAISABLE_DEGREES} "
            f"(mod 7) in minor, got degree {degree} (mod 7 = {deg_mod7})"
        )
    scale: tuple[int, ...] = _SCALE_SEMITONES[mode]
    semitone: int = scale[deg_mod7] + (octave * _SEMITONES_PER_OCTAVE)
    if raised and mode == MODE_MINOR and deg_mod7 in RAISABLE_DEGREES:
        semitone += 1
    return semitone


def get_progressions(
    level: str,
) -> tuple[tuple[str, ...], ...]:
    """Return all stock progressions for the given harmonic level."""
    assert level in _VALID_LEVELS, (
        f"level must be one of {_VALID_LEVELS!r}, got {level!r}"
    )
    return _PROGRESSIONS_BY_LEVEL[level]


def is_cross_relation(
    degree_a: int,
    degree_b: int,
    raised_a: bool,
    raised_b: bool,
) -> bool:
    """Return True if two adjacent notes form a cross-relation."""
    if degree_a % _DEGREES_PER_OCTAVE != degree_b % _DEGREES_PER_OCTAVE:
        return False
    return raised_a != raised_b


def is_raised_chord_degree(
    mode: str,
    chord: str,
    degree: int,
) -> bool:
    """Return True if the given degree requires chromatic raising in this chord."""
    raised_set: frozenset[int] = _RAISED_CHORD_DEGREES.get(
        (mode, chord), frozenset()
    )
    return (degree % _DEGREES_PER_OCTAVE) in raised_set


def minor_equivalent(
    major_chord: str,
) -> str:
    """Return the minor-mode equivalent of a major-mode chord name."""
    assert major_chord in _MINOR_EQUIVALENTS, (
        f"unknown major chord {major_chord!r}. "
        f"Valid: {sorted(_MINOR_EQUIVALENTS.keys())}"
    )
    return _MINOR_EQUIVALENTS[major_chord]


def select_harmonic_level(
    cell_ticks: tuple[int, ...],
) -> str:
    """Select harmonic rhythm level based on mean tick value of the cell sequence."""
    assert len(cell_ticks) > 0, "cell_ticks must not be empty"
    mean_tick: float = sum(cell_ticks) / len(cell_ticks)
    if mean_tick >= FAST_THRESHOLD:
        return LEVEL_FAST
    if mean_tick >= MEDIUM_THRESHOLD:
        return LEVEL_MEDIUM
    return LEVEL_SLOW


def should_raise(
    degree_mod7: int,
    direction: str,
) -> bool:
    """Return True if the degree should use the raised form (minor mode only)."""
    assert direction in _VALID_DIRECTIONS, (
        f"direction must be one of {_VALID_DIRECTIONS!r}, got {direction!r}"
    )
    return direction == DIR_ASCENDING and degree_mod7 in RAISABLE_DEGREES
