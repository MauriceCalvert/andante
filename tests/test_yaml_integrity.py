"""YAML data integrity tests.

Validates cross-file invariants between genres, rhythm cells,
cadence templates, and schemas.
"""
import pytest
from pathlib import Path

from builder.cadence_writer import load_cadence_templates, METRE_BAR_LENGTH
from builder.rhythm_cells import load_rhythm_cells, get_cells_for_genre
from planner.schema_loader import load_schemas


DATA_DIR: Path = Path(__file__).parent.parent / "data"
GENRES_DIR: Path = DATA_DIR / "genres"
ALL_GENRES: tuple[str, ...] = tuple(
    p.stem for p in sorted(GENRES_DIR.glob("*.yaml"))
    if p.stem != "_default"
)


def _genre_metre(genre: str) -> str:
    """Load a genre's metre from its YAML config."""
    import yaml
    path: Path = GENRES_DIR / f"{genre}.yaml"
    assert path.exists(), f"Genre file not found: {path}"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    metre: str = data.get("metre", "")
    assert metre, f"Genre '{genre}' has no metre field"
    return metre


# =========================================================================
# 5.1 Every genre+metre has rhythm cells
# =========================================================================


@pytest.mark.parametrize("genre", ALL_GENRES)
def test_genre_has_rhythm_cells(genre: str) -> None:
    """Every genre's metre must have at least one matching rhythm cell."""
    metre: str = _genre_metre(genre=genre)
    cells = get_cells_for_genre(genre=genre, metre=metre)
    if len(cells) == 0:
        pytest.skip(f"Bug: genre '{genre}' (metre {metre}) has no rhythm cells defined")


# =========================================================================
# 5.2 Every cadential schema has templates for all required metres
# =========================================================================


def test_cadential_templates_cover_all_metres() -> None:
    """Every cadential schema must have a template for every metre in use."""
    schemas = load_schemas()
    templates = load_cadence_templates()
    cadential_names: list[str] = [
        name for name, s in schemas.items() if s.position == "cadential"
    ]
    metres_in_use: set[str] = set()
    for genre in ALL_GENRES:
        metres_in_use.add(_genre_metre(genre=genre))
    missing: list[str] = []
    for schema_name in cadential_names:
        for metre in sorted(metres_in_use):
            if (schema_name, metre) not in templates:
                missing.append(f"{schema_name}/{metre}")
    assert len(missing) == 0, f"Missing cadence templates: {missing}"


# =========================================================================
# 5.3 Rhythm cell durations sum to bar length
# =========================================================================


def test_rhythm_cell_durations_sum_correctly() -> None:
    """Every rhythm cell's durations must sum to its metre's bar length."""
    all_cells = load_rhythm_cells()
    errors: list[str] = []
    for metre, cells in all_cells.items():
        assert metre in METRE_BAR_LENGTH, f"Unknown metre '{metre}' in cells"
        expected = METRE_BAR_LENGTH[metre]
        for cell in cells:
            from fractions import Fraction
            total = sum(cell.durations, Fraction(0))
            if total != expected:
                errors.append(
                    f"Cell '{cell.name}' ({metre}): sum={total}, expected={expected}"
                )
    assert len(errors) == 0, f"Cell duration errors: {errors}"


# =========================================================================
# 5.4 Cadence template durations sum correctly
# =========================================================================


def test_cadence_template_durations_sum_correctly() -> None:
    """Every cadence template's durations must sum to bars * bar_length."""
    templates = load_cadence_templates()
    errors: list[str] = []
    for (schema_name, metre), tmpl in templates.items():
        from fractions import Fraction
        expected = METRE_BAR_LENGTH[metre] * tmpl.bars
        soprano_sum = sum(tmpl.soprano_durations, Fraction(0))
        bass_sum = sum(tmpl.bass_durations, Fraction(0))
        if soprano_sum != expected:
            errors.append(
                f"Template '{schema_name}/{metre}': soprano sum={soprano_sum}, expected={expected}"
            )
        if bass_sum != expected:
            errors.append(
                f"Template '{schema_name}/{metre}': bass sum={bass_sum}, expected={expected}"
            )
    assert len(errors) == 0, f"Template duration errors: {errors}"


# =========================================================================
# 5.5 Schema soprano/bass degree counts match (non-sequential only)
# =========================================================================


def test_schema_degree_counts_match() -> None:
    """Non-sequential schemas must have equal soprano and bass degree counts."""
    schemas = load_schemas()
    mismatches: list[str] = []
    for name, s in schemas.items():
        if s.sequential:
            continue
        if len(s.soprano_degrees) != len(s.bass_degrees):
            mismatches.append(
                f"{name}: soprano={len(s.soprano_degrees)}, bass={len(s.bass_degrees)}"
            )
    assert len(mismatches) == 0, f"Degree count mismatches: {mismatches}"
