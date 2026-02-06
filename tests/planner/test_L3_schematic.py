"""L3 Schematic layer contract tests."""
import pytest
from typing import Any
from builder.config_loader import load_configs
from builder.types import GenreConfig, SchemaChain
from planner.schematic import layer_3_schematic
from planner.tonal import layer_2_tonal
from shared.constants import TONAL_CADENCE_TYPES
from tests.conftest import GENRES


def _section_ranges(boundaries: list[int]) -> list[tuple[int, int]]:
    """Return list of (start_idx, end_idx) for each section."""
    ranges: list[tuple[int, int]] = []
    prev: int = 0
    for b in boundaries:
        ranges.append((prev, b))
        prev = b
    return ranges


@pytest.fixture(params=GENRES)
def schema_result(request: pytest.FixtureRequest) -> tuple[SchemaChain, GenreConfig, dict[str, Any]]:
    """Run L2+L3 for each genre, return (chain, genre_config, schemas)."""
    genre: str = request.param
    config = load_configs(genre=genre, key="c_major", affect="Zierlich")
    tonal_plan = layer_2_tonal(
        affect_config=config["affect"],
        genre_config=config["genre"],
        seed=42,
    )
    chain: SchemaChain = layer_3_schematic(
        tonal_plan=tonal_plan,
        genre_config=config["genre"],
        form_config=config["form"],
        schemas=config["schemas"],
        seed=43,
    )
    return chain, config["genre"], config["schemas"]


def test_output_type(schema_result: tuple[SchemaChain, GenreConfig, dict[str, Any]]) -> None:
    """L3-01: output is SchemaChain."""
    chain, _, _ = schema_result
    assert isinstance(chain, SchemaChain)


def test_chain_nonempty(schema_result: tuple[SchemaChain, GenreConfig, dict[str, Any]]) -> None:
    """L3-02: chain.schemas is non-empty."""
    chain, _, _ = schema_result
    assert len(chain.schemas) >= 1


def test_all_schemas_in_catalogue(schema_result: tuple[SchemaChain, GenreConfig, dict[str, Any]]) -> None:
    """L3-03: every schema name exists in catalogue."""
    chain, _, schemas = schema_result
    for name in chain.schemas:
        assert name in schemas, f"Schema '{name}' not in catalogue"


def test_boundary_count(schema_result: tuple[SchemaChain, GenreConfig, dict[str, Any]]) -> None:
    """L3-04: section_boundaries count matches genre section count."""
    chain, genre_config, _ = schema_result
    assert len(chain.section_boundaries) == len(genre_config.sections)


def test_boundaries_monotonic(schema_result: tuple[SchemaChain, GenreConfig, dict[str, Any]]) -> None:
    """L3-05: section boundaries are strictly increasing."""
    chain, _, _ = schema_result
    for i in range(len(chain.section_boundaries) - 1):
        assert chain.section_boundaries[i] < chain.section_boundaries[i + 1], (
            f"Boundary {i} ({chain.section_boundaries[i]}) not less than "
            f"boundary {i+1} ({chain.section_boundaries[i + 1]})"
        )


def test_boundaries_tile_chain(schema_result: tuple[SchemaChain, GenreConfig, dict[str, Any]]) -> None:
    """L3-06: final boundary equals schema count."""
    chain, _, _ = schema_result
    assert chain.section_boundaries[-1] == len(chain.schemas)


def test_first_section_nonempty(schema_result: tuple[SchemaChain, GenreConfig, dict[str, Any]]) -> None:
    """L3-07: first section has at least one schema."""
    chain, _, _ = schema_result
    assert chain.section_boundaries[0] >= 1


def test_key_areas_length(schema_result: tuple[SchemaChain, GenreConfig, dict[str, Any]]) -> None:
    """L3-08: key_areas length matches schemas length."""
    chain, _, _ = schema_result
    assert len(chain.key_areas) == len(chain.schemas)


def test_cadences_length(schema_result: tuple[SchemaChain, GenreConfig, dict[str, Any]]) -> None:
    """L3-09: cadences length matches schemas length."""
    chain, _, _ = schema_result
    assert len(chain.cadences) == len(chain.schemas)


def test_no_adjacent_repetition(schema_result: tuple[SchemaChain, GenreConfig, dict[str, Any]]) -> None:
    """L3-10: no two adjacent schemas are the same."""
    chain, _, _ = schema_result
    for i in range(len(chain.schemas) - 1):
        assert chain.schemas[i] != chain.schemas[i + 1], (
            f"Adjacent repetition at indices {i},{i+1}: '{chain.schemas[i]}'"
        )


def test_cadence_entries_valid(schema_result: tuple[SchemaChain, GenreConfig, dict[str, Any]]) -> None:
    """L3-13: every cadence is None or in TONAL_CADENCE_TYPES."""
    chain, _, _ = schema_result
    for i, cadence in enumerate(chain.cadences):
        assert cadence is None or cadence in TONAL_CADENCE_TYPES, (
            f"Invalid cadence '{cadence}' at index {i}"
        )


def test_one_cadence_per_section(schema_result: tuple[SchemaChain, GenreConfig, dict[str, Any]]) -> None:
    """L3-14: each section has exactly one cadence at its last schema."""
    chain, _, _ = schema_result
    ranges: list[tuple[int, int]] = _section_ranges(chain.section_boundaries)
    for section_idx, (start, end) in enumerate(ranges):
        section_cadences = chain.cadences[start:end]
        non_none = [c for c in section_cadences if c is not None]
        assert len(non_none) == 1, (
            f"Section {section_idx} has {len(non_none)} cadences, expected 1"
        )
        assert section_cadences[-1] is not None, (
            f"Section {section_idx} cadence not at last schema position"
        )
