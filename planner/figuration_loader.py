"""Load and query figuration patterns and profiles from YAML.

Category A: Pure functions, no I/O, no validation.

Figuration patterns are baroque melodic vocabulary from Quantz and CPE Bach.
Profiles group patterns by schema context (stepwise descent, ascending sequence, etc.).
Accompaniment patterns are bass figures for melody_accompaniment texture.
"""
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


DATA_DIR: Path = Path(__file__).parent.parent / "data"


@dataclass(frozen=True)
class FigurationPattern:
    """Single figuration pattern from figurations.yaml."""
    name: str
    description: str
    offset_from_target: tuple[int, ...]  # Scale degrees relative to target (0 = target)
    notes_per_beat: int  # Rhythmic density (2=eighths, 4=sixteenths)
    metric: str  # strong, weak, across, any
    function: str  # ornament, diminution, cadential, sequential
    approach: str  # step_above, step_below, leap_above, leap_below, repeated, any
    energy: str  # low, medium, high

    @property
    def pattern_length(self) -> int:
        """Number of notes in pattern."""
        return len(self.offset_from_target)

    @property
    def duration_beats(self) -> float:
        """Duration in beats (pattern_length / notes_per_beat)."""
        return self.pattern_length / self.notes_per_beat


@dataclass(frozen=True)
class FigurationProfile:
    """Profile grouping patterns for schema context."""
    name: str
    description: str
    interior: tuple[str, ...]  # Pattern names for interior connections
    cadential: tuple[str, ...]  # Pattern names for cadential connections


@dataclass(frozen=True)
class AccompanimentPattern:
    """Bass accompaniment pattern from accompaniments.yaml."""
    name: str
    description: str
    degrees: tuple[int, ...]  # Scale degrees (1=root, 3=third, 5=fifth, 8=octave)
    durations: tuple[Fraction, ...]  # Note durations as fractions of a bar
    per_bar: bool  # Whether pattern repeats each bar


def _load_yaml(name: str) -> dict[str, Any]:
    """Load YAML file from data directory."""
    path: Path = DATA_DIR / name
    assert path.exists(), f"YAML file not found: {path}"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _parse_pattern(name: str, data: dict[str, Any]) -> FigurationPattern:
    """Parse single pattern from YAML."""
    return FigurationPattern(
        name=name,
        description=data.get("description", ""),
        offset_from_target=tuple(data["offset_from_target"]),
        notes_per_beat=data.get("notes_per_beat", 4),
        metric=data.get("metric", "any"),
        function=data.get("function", "diminution"),
        approach=data.get("approach", "any"),
        energy=data.get("energy", "medium"),
    )


def _parse_profile(name: str, data: dict[str, Any]) -> FigurationProfile:
    """Parse single profile from YAML."""
    interior: list[str] = data.get("interior", [])
    cadential: list[str] = data.get("cadential", [])
    return FigurationProfile(
        name=name,
        description=data.get("description", ""),
        interior=tuple(interior),
        cadential=tuple(cadential),
    )


@lru_cache(maxsize=1)
def load_figurations() -> dict[str, FigurationPattern]:
    """Load all figuration patterns from data/figurations.yaml."""
    raw: dict[str, Any] = _load_yaml("figurations.yaml")
    patterns: dict[str, FigurationPattern] = {}
    for name, data in raw.items():
        if not isinstance(data, dict):
            continue
        if "offset_from_target" not in data:
            continue
        patterns[name] = _parse_pattern(name, data)
    return patterns


@lru_cache(maxsize=1)
def load_profiles() -> dict[str, FigurationProfile]:
    """Load all figuration profiles from data/figuration_profiles.yaml."""
    raw: dict[str, Any] = _load_yaml("figuration_profiles.yaml")
    profiles: dict[str, FigurationProfile] = {}
    for name, data in raw.items():
        if not isinstance(data, dict):
            continue
        if "interior" not in data and "cadential" not in data:
            continue
        profiles[name] = _parse_profile(name, data)
    return profiles


def get_pattern(name: str) -> FigurationPattern:
    """Get single pattern by name."""
    patterns: dict[str, FigurationPattern] = load_figurations()
    assert name in patterns, f"Unknown pattern: {name}. Available: {sorted(patterns.keys())}"
    return patterns[name]


def get_profile(name: str) -> FigurationProfile:
    """Get single profile by name."""
    profiles: dict[str, FigurationProfile] = load_profiles()
    assert name in profiles, f"Unknown profile: {name}. Available: {sorted(profiles.keys())}"
    return profiles[name]


def validate_profiles() -> list[str]:
    """Validate that all pattern names in profiles exist in figurations.

    Returns list of error messages (empty if valid).
    """
    patterns: dict[str, FigurationPattern] = load_figurations()
    profiles: dict[str, FigurationProfile] = load_profiles()
    errors: list[str] = []

    for profile_name, profile in profiles.items():
        for pattern_name in profile.interior:
            if pattern_name not in patterns:
                errors.append(f"Profile '{profile_name}' references unknown interior pattern '{pattern_name}'")
        for pattern_name in profile.cadential:
            if pattern_name not in patterns:
                errors.append(f"Profile '{profile_name}' references unknown cadential pattern '{pattern_name}'")

    return errors


def get_patterns_for_profile(
    profile_name: str,
    is_cadential: bool = False,
) -> list[FigurationPattern]:
    """Get patterns for a profile (interior or cadential)."""
    profile: FigurationProfile = get_profile(profile_name)
    patterns: dict[str, FigurationPattern] = load_figurations()

    pattern_names: tuple[str, ...] = profile.cadential if is_cadential else profile.interior
    return [patterns[name] for name in pattern_names if name in patterns]


def get_patterns_by_function(function: str) -> list[FigurationPattern]:
    """Get all patterns with given function (ornament, diminution, cadential, sequential)."""
    patterns: dict[str, FigurationPattern] = load_figurations()
    return [p for p in patterns.values() if p.function == function]


def get_patterns_by_direction(ascending: bool) -> list[FigurationPattern]:
    """Get patterns suitable for ascending or descending motion.

    Ascending patterns have negative offsets (approach from below).
    Descending patterns have positive offsets (approach from above).
    """
    patterns: dict[str, FigurationPattern] = load_figurations()
    result: list[FigurationPattern] = []

    for pattern in patterns.values():
        offsets: tuple[int, ...] = pattern.offset_from_target
        if len(offsets) < 2:
            continue
        # First offset indicates approach direction
        first_offset: int = offsets[0]
        if ascending and first_offset < 0:
            result.append(pattern)
        elif not ascending and first_offset > 0:
            result.append(pattern)

    return result


def _parse_accompaniment(name: str, data: dict[str, Any]) -> AccompanimentPattern:
    """Parse single accompaniment pattern from YAML."""
    raw_degrees: list[int] = data["degrees"]
    raw_durations: list[str | float] = data["durations"]

    # Parse durations - they may be strings like "1/4" or floats
    durations: list[Fraction] = []
    for d in raw_durations:
        if isinstance(d, str):
            if "/" in d:
                parts = d.split("/")
                durations.append(Fraction(int(parts[0]), int(parts[1])))
            else:
                durations.append(Fraction(d))
        else:
            # Float - convert to Fraction
            durations.append(Fraction(d).limit_denominator(16))

    return AccompanimentPattern(
        name=name,
        description=data.get("description", ""),
        degrees=tuple(raw_degrees),
        durations=tuple(durations),
        per_bar=data.get("per_bar", True),
    )


@lru_cache(maxsize=1)
def load_accompaniments() -> dict[str, AccompanimentPattern]:
    """Load all accompaniment patterns from data/accompaniments.yaml."""
    raw: dict[str, Any] = _load_yaml("accompaniments.yaml")
    patterns: dict[str, AccompanimentPattern] = {}
    for name, data in raw.items():
        if not isinstance(data, dict):
            continue
        if "degrees" not in data:
            continue
        patterns[name] = _parse_accompaniment(name, data)
    return patterns


def get_accompaniment(name: str) -> AccompanimentPattern:
    """Get single accompaniment pattern by name."""
    patterns: dict[str, AccompanimentPattern] = load_accompaniments()
    assert name in patterns, f"Unknown accompaniment: {name}. Available: {sorted(patterns.keys())}"
    return patterns[name]


def get_accompaniment_for_energy(energy: str) -> AccompanimentPattern:
    """Select accompaniment pattern based on energy level.

    Low energy: pedal, murky (simple, sustained)
    Medium energy: arpeggiated_down, basso_continuo (standard baroque)
    High energy: running, walking (more active)
    """
    patterns: dict[str, AccompanimentPattern] = load_accompaniments()

    energy_map: dict[str, list[str]] = {
        "low": ["pedal", "murky", "chaconne"],
        "medium": ["arpeggiated_down", "basso_continuo", "arpeggiated_up"],
        "high": ["running", "walking", "arpeggiated_down"],
    }

    candidates: list[str] = energy_map.get(energy, energy_map["medium"])
    for name in candidates:
        if name in patterns:
            return patterns[name]

    # Fallback to first available
    return next(iter(patterns.values()))
