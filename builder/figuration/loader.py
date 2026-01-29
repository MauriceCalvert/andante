"""YAML loaders for figuration system.

Category A: Pure functions with defensive validation.
All loaders assert on invalid data per CLAUDE.md.
"""
from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml

from builder.figuration.types import CadentialFigure, Figure, RhythmTemplate
from shared.constants import FIGURATION_INTERVALS

# Data directory path
DATA_DIR: Path = Path(__file__).parent.parent.parent / "data" / "figuration"


def _parse_fraction(value: Any) -> Fraction:
    """Parse a value as a Fraction.

    Accepts: int, float, str like "1/4", or already a Fraction.
    """
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, float):
        return Fraction(value).limit_denominator(32)
    if isinstance(value, str):
        if "/" in value:
            parts = value.split("/")
            assert len(parts) == 2, f"Invalid fraction string: {value}"
            return Fraction(int(parts[0]), int(parts[1]))
        return Fraction(int(value))
    raise AssertionError(f"Cannot parse as Fraction: {value!r} (type {type(value).__name__})")


def load_diminutions(path: Path | None = None) -> dict[str, list[Figure]]:
    """Load diminution figures indexed by interval.

    Returns:
        Dict mapping interval name to list of Figure objects.
    """
    if path is None:
        path = DATA_DIR / "diminutions.yaml"

    assert path.exists(), f"Diminutions file not found: {path}"

    with open(path, "r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    assert isinstance(raw, dict), f"diminutions.yaml must be a dict, got {type(raw).__name__}"

    result: dict[str, list[Figure]] = {}

    for interval, figures_raw in raw.items():
        assert interval in FIGURATION_INTERVALS, \
            f"Unknown interval '{interval}'. Valid: {FIGURATION_INTERVALS}"
        assert isinstance(figures_raw, list), \
            f"Figures for interval '{interval}' must be a list, got {type(figures_raw).__name__}"

        figures: list[Figure] = []
        for fig_data in figures_raw:
            assert isinstance(fig_data, dict), \
                f"Each figure must be a dict, got {type(fig_data).__name__}"

            # Required fields
            required_fields = [
                "name", "degrees", "contour", "polarity", "arrival", "placement",
                "character", "harmonic_tension", "max_density", "cadential_safe",
                "repeatable", "requires_compensation", "compensation_direction",
                "is_compound", "minor_safe", "requires_leading_tone", "weight",
            ]
            for field in required_fields:
                assert field in fig_data, \
                    f"Figure in '{interval}' missing required field '{field}': {fig_data.get('name', '(unnamed)')}"

            figure = Figure(
                name=fig_data["name"],
                degrees=tuple(fig_data["degrees"]),
                contour=fig_data["contour"],
                polarity=fig_data["polarity"],
                arrival=fig_data["arrival"],
                placement=fig_data["placement"],
                character=fig_data["character"],
                harmonic_tension=fig_data["harmonic_tension"],
                max_density=fig_data["max_density"],
                cadential_safe=bool(fig_data["cadential_safe"]),
                repeatable=bool(fig_data["repeatable"]),
                requires_compensation=bool(fig_data["requires_compensation"]),
                compensation_direction=fig_data["compensation_direction"],
                is_compound=bool(fig_data["is_compound"]),
                minor_safe=bool(fig_data["minor_safe"]),
                requires_leading_tone=bool(fig_data["requires_leading_tone"]),
                weight=float(fig_data["weight"]),
                chainable=bool(fig_data.get("chainable", False)),
                chain_unit=fig_data.get("chain_unit"),
            )
            figures.append(figure)

        assert len(figures) > 0, f"Interval '{interval}' has no figures"
        result[interval] = figures

    # Verify all intervals have figures
    for interval in FIGURATION_INTERVALS:
        assert interval in result, f"Missing interval '{interval}' in diminutions.yaml"

    return result


def load_cadential(path: Path | None = None) -> dict[str, dict[str, list[CadentialFigure]]]:
    """Load cadential figures indexed by target degree and approach interval.

    Returns:
        Dict mapping target ("target_1", "target_5") to dict mapping
        approach interval to list of CadentialFigure objects.
    """
    if path is None:
        path = DATA_DIR / "cadential.yaml"

    assert path.exists(), f"Cadential file not found: {path}"

    with open(path, "r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    assert isinstance(raw, dict), f"cadential.yaml must be a dict, got {type(raw).__name__}"

    result: dict[str, dict[str, list[CadentialFigure]]] = {}

    valid_targets = ("target_1", "target_5")
    for target, approaches in raw.items():
        assert target in valid_targets, \
            f"Unknown cadential target '{target}'. Valid: {valid_targets}"
        assert isinstance(approaches, dict), \
            f"Approaches for target '{target}' must be a dict, got {type(approaches).__name__}"

        result[target] = {}

        for approach, figures_raw in approaches.items():
            assert isinstance(figures_raw, list), \
                f"Figures for {target}/{approach} must be a list, got {type(figures_raw).__name__}"

            figures: list[CadentialFigure] = []
            for fig_data in figures_raw:
                assert isinstance(fig_data, dict), \
                    f"Each cadential figure must be a dict, got {type(fig_data).__name__}"

                required_fields = ["name", "degrees", "contour", "trill_position", "hemiola"]
                for field in required_fields:
                    assert field in fig_data, \
                        f"Cadential figure in {target}/{approach} missing field '{field}'"

                figure = CadentialFigure(
                    name=fig_data["name"],
                    degrees=tuple(fig_data["degrees"]),
                    contour=fig_data["contour"],
                    trill_position=fig_data["trill_position"],
                    hemiola=bool(fig_data["hemiola"]),
                )
                figures.append(figure)

            assert len(figures) > 0, f"{target}/{approach} has no figures"
            result[target][approach] = figures

    # Verify both targets exist
    for target in valid_targets:
        assert target in result, f"Missing target '{target}' in cadential.yaml"

    return result


def load_rhythm_templates(path: Path | None = None) -> dict[tuple[int, str, bool], RhythmTemplate]:
    """Load rhythm templates indexed by (note_count, metre, overdotted).

    Returns:
        Dict mapping (note_count, metre, overdotted) to RhythmTemplate.
    """
    if path is None:
        path = DATA_DIR / "rhythm_templates.yaml"

    assert path.exists(), f"Rhythm templates file not found: {path}"

    with open(path, "r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    assert isinstance(raw, dict), f"rhythm_templates.yaml must be a dict, got {type(raw).__name__}"

    result: dict[tuple[int, str, bool], RhythmTemplate] = {}

    for metre, note_counts in raw.items():
        # Skip hemiola section for now (handled separately)
        if metre == "hemiola":
            continue

        assert isinstance(note_counts, dict), \
            f"Note counts for metre '{metre}' must be a dict, got {type(note_counts).__name__}"

        for note_count_str, variants in note_counts.items():
            note_count = int(note_count_str)
            assert isinstance(variants, dict), \
                f"Variants for {metre}/{note_count} must be a dict, got {type(variants).__name__}"

            for variant_name, variant_data in variants.items():
                assert isinstance(variant_data, dict), \
                    f"Variant data for {metre}/{note_count}/{variant_name} must be a dict"
                assert "durations" in variant_data, \
                    f"Variant {metre}/{note_count}/{variant_name} missing 'durations'"

                overdotted = variant_name == "overdotted"
                durations_raw = variant_data["durations"]
                assert isinstance(durations_raw, list), \
                    f"Durations must be a list, got {type(durations_raw).__name__}"

                durations = tuple(_parse_fraction(d) for d in durations_raw)
                assert len(durations) == note_count, \
                    f"Duration count {len(durations)} != note_count {note_count} for {metre}/{note_count}/{variant_name}"

                template = RhythmTemplate(
                    note_count=note_count,
                    metre=metre,
                    durations=durations,
                    overdotted=overdotted,
                )
                result[(note_count, metre, overdotted)] = template

    return result


def load_hemiola_templates(path: Path | None = None) -> dict[tuple[int, str], RhythmTemplate]:
    """Load hemiola-specific rhythm templates.

    Returns:
        Dict mapping (note_count, metre) to RhythmTemplate for hemiola contexts.
    """
    if path is None:
        path = DATA_DIR / "rhythm_templates.yaml"

    assert path.exists(), f"Rhythm templates file not found: {path}"

    with open(path, "r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    assert isinstance(raw, dict), f"rhythm_templates.yaml must be a dict, got {type(raw).__name__}"

    result: dict[tuple[int, str], RhythmTemplate] = {}

    if "hemiola" not in raw:
        return result

    hemiola_section = raw["hemiola"]
    assert isinstance(hemiola_section, dict), "hemiola section must be a dict"

    for metre, note_counts in hemiola_section.items():
        assert isinstance(note_counts, dict), \
            f"Hemiola note counts for metre '{metre}' must be a dict"

        for note_count_str, variants in note_counts.items():
            note_count = int(note_count_str)
            assert isinstance(variants, dict), \
                f"Hemiola variants for {metre}/{note_count} must be a dict"

            # Use standard variant for hemiola
            if "standard" in variants:
                variant_data = variants["standard"]
                assert "durations" in variant_data, \
                    f"Hemiola {metre}/{note_count}/standard missing 'durations'"

                durations_raw = variant_data["durations"]
                durations = tuple(_parse_fraction(d) for d in durations_raw)

                template = RhythmTemplate(
                    note_count=note_count,
                    metre=metre,
                    durations=durations,
                    overdotted=False,
                )
                result[(note_count, metre)] = template

    return result


def load_figuration_profiles(path: Path | None = None) -> dict[str, dict[str, list[str]]]:
    """Load figuration profiles mapping schema types to pattern sets.

    Returns:
        Dict mapping profile name to dict with 'interior' and 'cadential' pattern lists.
    """
    if path is None:
        path = DATA_DIR / "figuration_profiles.yaml"
    assert path.exists(), f"Figuration profiles file not found: {path}"
    with open(path, "r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)
    assert isinstance(raw, dict), f"figuration_profiles.yaml must be a dict, got {type(raw).__name__}"
    result: dict[str, dict[str, list[str]]] = {}
    for profile_name, profile_data in raw.items():
        assert isinstance(profile_data, dict), \
            f"Profile '{profile_name}' must be a dict, got {type(profile_data).__name__}"
        interior = profile_data.get("interior", [])
        cadential = profile_data.get("cadential", [])
        assert isinstance(interior, list), \
            f"Profile '{profile_name}' interior must be a list, got {type(interior).__name__}"
        assert isinstance(cadential, list), \
            f"Profile '{profile_name}' cadential must be a list, got {type(cadential).__name__}"
        result[profile_name] = {
            "interior": interior,
            "cadential": cadential,
        }
    return result


# Cache for loaded data
_diminutions_cache: dict[str, list[Figure]] | None = None
_cadential_cache: dict[str, dict[str, list[CadentialFigure]]] | None = None
_rhythm_templates_cache: dict[tuple[int, str, bool], RhythmTemplate] | None = None
_hemiola_templates_cache: dict[tuple[int, str], RhythmTemplate] | None = None
_figuration_profiles_cache: dict[str, dict[str, list[str]]] | None = None


def get_diminutions() -> dict[str, list[Figure]]:
    """Get cached diminution figures."""
    global _diminutions_cache
    if _diminutions_cache is None:
        _diminutions_cache = load_diminutions()
    return _diminutions_cache


def get_cadential() -> dict[str, dict[str, list[CadentialFigure]]]:
    """Get cached cadential figures."""
    global _cadential_cache
    if _cadential_cache is None:
        _cadential_cache = load_cadential()
    return _cadential_cache


def get_rhythm_templates() -> dict[tuple[int, str, bool], RhythmTemplate]:
    """Get cached rhythm templates."""
    global _rhythm_templates_cache
    if _rhythm_templates_cache is None:
        _rhythm_templates_cache = load_rhythm_templates()
    return _rhythm_templates_cache


def get_hemiola_templates() -> dict[tuple[int, str], RhythmTemplate]:
    """Get cached hemiola templates."""
    global _hemiola_templates_cache
    if _hemiola_templates_cache is None:
        _hemiola_templates_cache = load_hemiola_templates()
    return _hemiola_templates_cache


def get_figuration_profiles() -> dict[str, dict[str, list[str]]]:
    """Get cached figuration profiles."""
    global _figuration_profiles_cache
    if _figuration_profiles_cache is None:
        _figuration_profiles_cache = load_figuration_profiles()
    return _figuration_profiles_cache


def clear_cache() -> None:
    """Clear all cached data (useful for testing)."""
    global _diminutions_cache, _cadential_cache, _rhythm_templates_cache, _hemiola_templates_cache
    global _figuration_profiles_cache
    _diminutions_cache = None
    _cadential_cache = None
    _rhythm_templates_cache = None
    _hemiola_templates_cache = None
    _figuration_profiles_cache = None
