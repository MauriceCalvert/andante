"""L2 Tonal layer contract tests."""
import pytest
from builder.config_loader import load_configs
from builder.types import GenreConfig, TonalPlan
from planner.tonal import layer_2_tonal
from shared.constants import TONAL_CADENCE_TYPES, VALID_KEY_AREAS
from tests.conftest import AFFECTS, GENRES


@pytest.fixture(params=[(g, a) for g in GENRES for a in AFFECTS], ids=lambda p: f"{p[0]}-{p[1]}")
def tonal_result(request: pytest.FixtureRequest) -> tuple[TonalPlan, GenreConfig]:
    """Run L2 for each genre x affect combination."""
    genre, affect = request.param
    config = load_configs(genre=genre, key="c_major", affect=affect)
    plan: TonalPlan = layer_2_tonal(
        affect_config=config["affect"],
        genre_config=config["genre"],
        seed=42,
    )
    return plan, config["genre"]


def test_output_type(tonal_result: tuple[TonalPlan, GenreConfig]) -> None:
    """L2-01: output is TonalPlan."""
    plan, _ = tonal_result
    assert isinstance(plan, TonalPlan)


def test_section_count(tonal_result: tuple[TonalPlan, GenreConfig]) -> None:
    """L2-02: section count matches genre."""
    plan, genre_config = tonal_result
    assert len(plan.sections) == len(genre_config.sections)


def test_section_names_match(tonal_result: tuple[TonalPlan, GenreConfig]) -> None:
    """L2-03: section names match genre section names."""
    plan, genre_config = tonal_result
    genre_names: list[str] = [s["name"] for s in genre_config.sections]
    plan_names: list[str] = [s.name for s in plan.sections]
    assert plan_names == genre_names


def test_key_areas_valid(tonal_result: tuple[TonalPlan, GenreConfig]) -> None:
    """L2-04: every key_area is in VALID_KEY_AREAS."""
    plan, _ = tonal_result
    for s in plan.sections:
        assert s.key_area in VALID_KEY_AREAS, f"Invalid key_area '{s.key_area}' in section {s.name}"


def test_cadence_types_valid(tonal_result: tuple[TonalPlan, GenreConfig]) -> None:
    """L2-05: every cadence_type is valid."""
    plan, _ = tonal_result
    for s in plan.sections:
        assert s.cadence_type in TONAL_CADENCE_TYPES, f"Invalid cadence '{s.cadence_type}' in {s.name}"


def test_final_cadence_authentic(tonal_result: tuple[TonalPlan, GenreConfig]) -> None:
    """L2-06: final section cadence is authentic."""
    plan, _ = tonal_result
    assert plan.sections[-1].cadence_type == "authentic"


def test_first_key_tonic(tonal_result: tuple[TonalPlan, GenreConfig]) -> None:
    """L2-07: first section key_area is I for 3+ sections, V/III for binary."""
    plan, genre_config = tonal_result
    if len(genre_config.sections) == 2:
        # Binary forms: section A destination is dominant (V) or relative major (III)
        assert plan.sections[0].key_area in ("V", "III"), (
            f"Binary section A should target V or III, got '{plan.sections[0].key_area}'"
        )
    else:
        assert plan.sections[0].key_area == "I"


def test_final_key_tonic(tonal_result: tuple[TonalPlan, GenreConfig]) -> None:
    """L2-08: final section key_area is I (tonic)."""
    plan, _ = tonal_result
    assert plan.sections[-1].key_area == "I"


def test_no_consecutive_nontonic(tonal_result: tuple[TonalPlan, GenreConfig]) -> None:
    """L2-09: no two consecutive identical non-tonic key areas."""
    plan, _ = tonal_result
    areas: list[str] = [s.key_area for s in plan.sections]
    for i in range(len(areas) - 1):
        if areas[i] != "I":
            assert areas[i] != areas[i + 1], f"Consecutive non-tonic '{areas[i]}' at sections {i},{i+1}"


def test_no_consecutive_half_cadences(tonal_result: tuple[TonalPlan, GenreConfig]) -> None:
    """L2-10: no two consecutive half cadences."""
    plan, _ = tonal_result
    cadences: list[str] = [s.cadence_type for s in plan.sections]
    for i in range(len(cadences) - 1):
        if cadences[i] == "half":
            assert cadences[i + 1] != "half", f"Consecutive half cadences at sections {i},{i+1}"


def test_interior_authentic_limit(tonal_result: tuple[TonalPlan, GenreConfig]) -> None:
    """L2-11: at most one interior authentic cadence."""
    plan, _ = tonal_result
    interior = plan.sections[:-1]
    auth_count: int = sum(1 for s in interior if s.cadence_type == "authentic")
    assert auth_count <= 1, f"{auth_count} interior authentic cadences"


def test_density_valid(tonal_result: tuple[TonalPlan, GenreConfig]) -> None:
    """L2-12: density is valid."""
    plan, _ = tonal_result
    assert plan.density in {"low", "medium", "high"}


def test_modality_valid(tonal_result: tuple[TonalPlan, GenreConfig]) -> None:
    """L2-13: modality is valid."""
    plan, _ = tonal_result
    assert plan.modality in {"diatonic", "chromatic"}
