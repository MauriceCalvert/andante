"""Parse brief YAML and merge with genre template.

Loads brief files, parses them into Brief objects, loads the corresponding
genre template, and applies any user overrides via deep merge.
"""
from fractions import Fraction
from pathlib import Path

import yaml

from planner.genre_loader import load_genre
from planner.plannertypes import (
    Brief,
    CadenceTemplate,
    GenreSection,
    GenreTemplate,
    Motif,
    SubjectConstraints,
    TreatmentSpec,
)


def parse_brief(path: Path) -> tuple[Brief, GenreTemplate]:
    """Parse brief file and load its genre.

    Args:
        path: Path to .brief or .yaml file

    Returns:
        (brief, genre_template) - genre may have overrides applied

    Raises:
        AssertionError: If brief file not found or missing required fields
    """
    assert path.exists(), f"Brief file not found: {path}"

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    brief = _parse_brief_data(data, path)
    genre = load_genre(brief.genre)

    # Apply overrides if present
    if brief.overrides:
        genre = _apply_overrides(genre, brief.overrides)

    return brief, genre


def _parse_brief_data(data: dict, path: Path) -> Brief:
    """Parse brief section of YAML."""
    assert "brief" in data, f"Missing 'brief' section in {path}"
    b = data["brief"]

    _require_brief_field(b, "affect", path)
    _require_brief_field(b, "genre", path)
    _require_brief_field(b, "forces", path)
    _require_brief_field(b, "bars", path)

    frame = data.get("frame", {})

    # Parse subject if present (top-level or under material)
    subject = None
    if "subject" in data:
        subject = _parse_subject(data["subject"], path)
    elif "material" in data and "subject" in data["material"]:
        # Legacy format: material.subject
        subject = _parse_subject(data["material"]["subject"], path)

    return Brief(
        affect=b["affect"],
        genre=b["genre"],
        forces=b["forces"],
        bars=b["bars"],
        key=frame.get("key"),
        mode=frame.get("mode"),
        metre=frame.get("metre"),
        tempo=frame.get("tempo"),
        subject=subject,
        overrides=data.get("overrides"),
        # Legacy fields
        virtuosic=b.get("virtuosic", False),
        motif_source=b.get("motif_source"),
    )


def _parse_subject(data: dict, path: Path) -> Motif:
    """Parse subject into Motif.

    Supports:
    - Inline degrees/durations
    - File reference (file: path/to/subject.note)
    """
    if "file" in data:
        return _load_subject_file(data["file"], path)

    assert "degrees" in data or "pitches" in data, (
        f"Subject in {path} must have 'degrees', 'pitches', or 'file'"
    )

    durations = None
    if "durations" in data:
        durations = tuple(_parse_fraction(d) for d in data["durations"])

    # Calculate bars from durations if not specified
    bars = data.get("bars")
    if bars is None and durations:
        total = sum(durations)
        bars = int(total)  # Rough estimate

    degrees = tuple(data["degrees"]) if "degrees" in data else None
    pitches = tuple(data["pitches"]) if "pitches" in data else None

    return Motif(
        durations=durations or (),
        bars=bars or 1,
        degrees=degrees,
        pitches=pitches,
        source_key=data.get("source_key"),
    )


def _load_subject_file(file_path: str, brief_path: Path) -> Motif:
    """Load subject from .note or .subject file.

    Resolution order:
    1. Absolute path (used as-is)
    2. Relative to brief file directory
    3. Relative to project root (andante/)
    """
    if Path(file_path).is_absolute():
        full_path = Path(file_path)
    else:
        # Try relative to brief directory first
        full_path = brief_path.parent / file_path
        if not full_path.exists():
            # Try relative to project root (andante/)
            project_root = Path(__file__).parent.parent
            full_path = project_root / file_path

    assert full_path.exists(), f"Subject file not found: {file_path} (referenced from {brief_path})"

    with open(full_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Subject files use same format as inline
    return _parse_subject(data, full_path)


def _apply_overrides(genre: GenreTemplate, overrides: dict) -> GenreTemplate:
    """Apply brief overrides to genre template.

    Supports deep merge for all GenreTemplate fields.
    """
    # Start with existing values
    schema_prefs = dict(genre.schema_preferences)
    cadence_template = genre.cadence_template
    sections = genre.sections
    subject_constraints = genre.subject_constraints
    treatments = genre.treatments

    # Override schema_preferences
    if "schema_preferences" in overrides:
        for position, schemas in overrides["schema_preferences"].items():
            schema_prefs[position] = schemas

    # Override cadence_template
    if "cadence_template" in overrides:
        ct = overrides["cadence_template"]
        cadence_template = CadenceTemplate(
            density=ct.get("density", cadence_template.density),
            first_cadence_bar=ct.get("first_cadence_bar", cadence_template.first_cadence_bar),
            first_cadence_type=ct.get("first_cadence_type", cadence_template.first_cadence_type),
            section_end_type=ct.get("section_end_type", cadence_template.section_end_type),
            final_type=ct.get("final_type", cadence_template.final_type),
        )

    # Override sections (replace entirely if provided)
    if "sections" in overrides:
        sections = tuple(
            GenreSection(
                label=s["label"],
                key_area=s["key_area"],
                proportion=s["proportion"],
                end_cadence=s["end_cadence"],
            )
            for s in overrides["sections"]
        )

    # Override subject_constraints
    if "subject_constraints" in overrides:
        sc = overrides["subject_constraints"]
        subject_constraints = SubjectConstraints(
            min_notes=sc.get("min_notes", subject_constraints.min_notes),
            max_notes=sc.get("max_notes", subject_constraints.max_notes),
            max_bars=sc.get("max_bars", subject_constraints.max_bars),
            require_invertible=sc.get("require_invertible", subject_constraints.require_invertible),
            require_answerable=sc.get("require_answerable", subject_constraints.require_answerable),
            first_degree=tuple(sc.get("first_degree", subject_constraints.first_degree)),
            last_degree=tuple(sc.get("last_degree", subject_constraints.last_degree)),
        )

    # Override treatments
    if "treatments" in overrides:
        t = overrides["treatments"]
        treatments = TreatmentSpec(
            required=tuple(t.get("required", treatments.required)),
            optional=tuple(t.get("optional", treatments.optional)),
            opening=t.get("opening", treatments.opening),
            answer=t.get("answer", treatments.answer),
        )

    return GenreTemplate(
        name=genre.name,
        voices=overrides.get("voices", genre.voices),
        metre=overrides.get("metre", genre.metre),
        texture=overrides.get("texture", genre.texture),
        schema_preferences=schema_prefs,
        cadence_template=cadence_template,
        sections=sections,
        subject_constraints=subject_constraints,
        treatments=treatments,
    )


def _parse_fraction(value: str | int | float | Fraction) -> Fraction:
    """Parse duration to Fraction."""
    if isinstance(value, Fraction):
        return value
    if isinstance(value, str) and "/" in value:
        num, den = value.split("/")
        return Fraction(int(num), int(den))
    return Fraction(value)


def _require_brief_field(data: dict, field: str, path: Path) -> None:
    """Assert field exists with helpful error message."""
    assert field in data, f"Missing required field 'brief.{field}' in {path}"
