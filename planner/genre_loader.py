"""Load genre templates from YAML with fallback merge logic.

Provides centralised genre template loading that deep-merges genre-specific
YAML over _default.yaml to ensure all fields are always present.

Two APIs:
- load_genre_template(genre) -> dict: Raw merged dict for simple field access
- load_genre(genre) -> GenreTemplate: Typed dataclass for structured access
"""
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from planner.plannertypes import (
    CadenceTemplate,
    GenreSection,
    GenreTemplate,
    SubjectConstraints,
    TreatmentSpec,
)


logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "genres"
DEFAULT_FILE = DATA_DIR / "_default.yaml"
_CACHE: dict[str, GenreTemplate] = {}


# =============================================================================
# Deep Merge Utilities
# =============================================================================


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge override dict over base dict.

    - Dicts: recursive merge
    - Lists: override replaces (no concatenation)
    - Scalars: override replaces

    Args:
        base: Base dictionary (typically defaults)
        override: Override dictionary (typically genre-specific)

    Returns:
        New merged dictionary (does not mutate inputs)
    """
    result: dict[str, Any] = {}

    # Start with all base keys
    for key, base_value in base.items():
        if key in override:
            override_value = override[key]
            # Both are dicts: recursive merge
            if isinstance(base_value, dict) and isinstance(override_value, dict):
                result[key] = _deep_merge(base_value, override_value)
            else:
                # Lists or scalars: override replaces
                result[key] = override_value
        else:
            result[key] = base_value

    # Add keys only in override
    for key, override_value in override.items():
        if key not in base:
            result[key] = override_value

    return result


@lru_cache(maxsize=1)
def _load_default_template() -> dict[str, Any]:
    """Load _default.yaml (cached).

    Returns:
        Default template dict

    Raises:
        AssertionError: If _default.yaml does not exist
    """
    assert DEFAULT_FILE.exists(), f"Default genre template not found: {DEFAULT_FILE}"
    with open(DEFAULT_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert data is not None, f"Default genre template is empty: {DEFAULT_FILE}"
    return data


def _load_genre_file(genre: str) -> dict[str, Any] | None:
    """Load genre-specific YAML file if it exists.

    Args:
        genre: Genre name (e.g., 'invention', 'minuet')

    Returns:
        Genre data dict, or None if file does not exist
    """
    path = DATA_DIR / f"{genre}.yaml"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if data else None


def load_genre_template(genre: str) -> dict[str, Any]:
    """Load genre template with fallback to defaults.

    Priority:
    1. Load _default.yaml first
    2. If genre-specific file exists, deep merge it over defaults
    3. If not, log warning and return defaults

    Args:
        genre: Genre name (e.g., 'invention', 'minuet')

    Returns:
        Complete genre template dict with all fields guaranteed
    """
    defaults = _load_default_template()

    genre_data = _load_genre_file(genre)
    if genre_data is None:
        logger.warning(
            "Genre file not found for '%s', using default template", genre
        )
        return defaults.copy()

    return _deep_merge(defaults, genre_data)


# =============================================================================
# Typed API (GenreTemplate dataclass)
# =============================================================================


def load_genre(name: str) -> GenreTemplate:
    """Load genre template by name with fallback merge.

    Uses load_genre_template to get merged dict, then parses to typed object.

    Args:
        name: Genre name (e.g., "invention", "minuet")

    Returns:
        GenreTemplate with all fields populated

    Raises:
        AssertionError: If _default.yaml missing or corrupted
    """
    if name in _CACHE:
        return _CACHE[name]

    data = load_genre_template(name)
    template = _parse_genre(data, name)
    _CACHE[name] = template
    return template


def clear_cache() -> None:
    """Clear all caches. Used in tests."""
    _CACHE.clear()
    _load_default_template.cache_clear()


def _parse_genre(data: dict, name: str) -> GenreTemplate:
    """Parse genre dict into GenreTemplate."""
    _require_field(data, "name", name)
    _require_field(data, "voices", name)
    _require_field(data, "metre", name)
    _require_field(data, "texture", name)
    _require_field(data, "schema_preferences", name)
    _require_field(data, "cadence_template", name)
    _require_field(data, "sections", name)
    _require_field(data, "subject_constraints", name)
    _require_field(data, "treatments", name)

    return GenreTemplate(
        name=data["name"],
        voices=data["voices"],
        metre=data["metre"],
        texture=data["texture"],
        schema_preferences=data["schema_preferences"],
        cadence_template=_parse_cadence_template(data["cadence_template"], name),
        sections=tuple(_parse_section(s, name, i) for i, s in enumerate(data["sections"])),
        subject_constraints=_parse_constraints(data["subject_constraints"], name),
        treatments=_parse_treatments(data["treatments"], name),
    )


def _parse_cadence_template(data: dict, genre: str) -> CadenceTemplate:
    """Parse cadence template."""
    ctx = f"{genre}.cadence_template"
    _require_field(data, "density", ctx)
    _require_field(data, "first_cadence_bar", ctx)
    _require_field(data, "first_cadence_type", ctx)
    _require_field(data, "section_end_type", ctx)
    _require_field(data, "final_type", ctx)

    return CadenceTemplate(
        density=data["density"],
        first_cadence_bar=data["first_cadence_bar"],
        first_cadence_type=data["first_cadence_type"],
        section_end_type=data["section_end_type"],
        final_type=data["final_type"],
    )


def _parse_section(data: dict, genre: str, index: int) -> GenreSection:
    """Parse genre section."""
    ctx = f"{genre}.sections[{index}]"
    _require_field(data, "label", ctx)
    _require_field(data, "key_area", ctx)
    _require_field(data, "proportion", ctx)
    _require_field(data, "end_cadence", ctx)

    return GenreSection(
        label=data["label"],
        key_area=data["key_area"],
        proportion=data["proportion"],
        end_cadence=data["end_cadence"],
    )


def _parse_constraints(data: dict, genre: str) -> SubjectConstraints:
    """Parse subject constraints."""
    ctx = f"{genre}.subject_constraints"
    _require_field(data, "min_notes", ctx)
    _require_field(data, "max_notes", ctx)
    _require_field(data, "max_bars", ctx)
    _require_field(data, "require_invertible", ctx)
    _require_field(data, "require_answerable", ctx)
    _require_field(data, "first_degree", ctx)
    _require_field(data, "last_degree", ctx)

    return SubjectConstraints(
        min_notes=data["min_notes"],
        max_notes=data["max_notes"],
        max_bars=data["max_bars"],
        require_invertible=data["require_invertible"],
        require_answerable=data["require_answerable"],
        first_degree=tuple(data["first_degree"]),
        last_degree=tuple(data["last_degree"]),
    )


def _parse_treatments(data: dict, genre: str) -> TreatmentSpec:
    """Parse treatment specification."""
    ctx = f"{genre}.treatments"
    _require_field(data, "required", ctx)
    _require_field(data, "opening", ctx)
    _require_field(data, "answer", ctx)

    return TreatmentSpec(
        required=tuple(data["required"]),
        optional=tuple(data.get("optional", [])),
        opening=data["opening"],
        answer=data["answer"],
    )


def _require_field(data: dict, field: str, context: str) -> None:
    """Assert field exists with helpful error message."""
    assert field in data, f"Missing required field '{field}' in {context}. Add it to the YAML file."
