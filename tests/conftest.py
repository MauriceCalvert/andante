"""Shared fixtures for contract tests.

All contract tests for L1-L5 and L7 are parametrised over GENRES.
L2 tests additionally parametrised over AFFECTS.
"""
import pytest
from pathlib import Path
from typing import Any
from builder.config_loader import load_configs
from builder.types import AffectConfig, FormConfig, GenreConfig, KeyConfig


@pytest.fixture(autouse=True, scope="session")
def _validate_yaml_data() -> None:
    """Gate all tests on YAML validation. Skips if data unchanged."""
    from scripts.yaml_validator import validate_all
    result = validate_all()
    if not result.valid:
        lines = [f"YAML validation failed ({len(result.errors)} errors):"]
        for e in result.errors:
            lines.append(f"  {e}")
        pytest.fail("\n".join(lines))
    # for p in result.orphaned:
    #     print(f"  INFO: orphaned YAML file: {p}")


DATA_DIR: Path = Path(__file__).parent.parent / "data"

GENRES: tuple[str, ...] = tuple(
    sorted(
        p.stem for p in (DATA_DIR / "genres").glob("*.yaml")
        if p.stem != "_default"
    )
)

AFFECTS: tuple[str, ...] = ("Zierlich", "Zaertlichkeit", "Freudigkeit", "Dolore")

KEYS: tuple[str, ...] = ("c_major", "a_minor")


@pytest.fixture(params=GENRES)
def genre_name(request: pytest.FixtureRequest) -> str:
    """Parametrised genre name."""
    return request.param


@pytest.fixture(params=AFFECTS)
def affect_name(request: pytest.FixtureRequest) -> str:
    """Parametrised affect name."""
    return request.param


@pytest.fixture(params=KEYS)
def key_name(request: pytest.FixtureRequest) -> str:
    """Parametrised key name."""
    return request.param


@pytest.fixture
def configs(genre_name: str) -> dict[str, Any]:
    """Load all configs for a genre. Uses default key c_major."""
    return load_configs(genre=genre_name, key="c_major", affect="Zierlich")


@pytest.fixture
def genre_config(configs: dict[str, Any]) -> GenreConfig:
    """GenreConfig for current genre."""
    return configs["genre"]


@pytest.fixture
def affect_config(configs: dict[str, Any]) -> AffectConfig:
    """AffectConfig for current genre."""
    return configs["affect"]


@pytest.fixture
def form_config(configs: dict[str, Any]) -> FormConfig:
    """FormConfig for current genre."""
    return configs["form"]


@pytest.fixture
def key_config(configs: dict[str, Any]) -> KeyConfig:
    """KeyConfig for current genre."""
    return configs["key"]


@pytest.fixture
def schemas(configs: dict[str, Any]) -> dict[str, Any]:
    """Schema catalogue for current genre."""
    return configs["schemas"]
