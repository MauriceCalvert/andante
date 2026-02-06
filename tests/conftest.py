"""Shared fixtures for contract tests.

All contract tests for L1-L5 and L7 are parametrised over GENRES.
L2 tests additionally parametrised over AFFECTS.
"""
import pytest
from typing import Any
from builder.config_loader import load_configs


GENRES: tuple[str, ...] = ("bourree", "gavotte", "invention", "minuet", "sarabande")

AFFECTS: tuple[str, ...] = ("Zierlich", "Zaertlichkeit", "Freudigkeit", "Dolore")


@pytest.fixture(params=GENRES)
def genre_name(request: pytest.FixtureRequest) -> str:
    """Parametrised genre name."""
    return request.param


@pytest.fixture(params=AFFECTS)
def affect_name(request: pytest.FixtureRequest) -> str:
    """Parametrised affect name."""
    return request.param


@pytest.fixture
def configs(genre_name: str) -> dict[str, Any]:
    """Load all configs for a genre. Uses default key c_major."""
    return load_configs(genre=genre_name, key="c_major", affect="Zierlich")


@pytest.fixture
def genre_config(configs: dict[str, Any]) -> Any:
    """GenreConfig for current genre."""
    return configs["genre"]


@pytest.fixture
def affect_config(configs: dict[str, Any]) -> Any:
    """AffectConfig for current genre."""
    return configs["affect"]


@pytest.fixture
def form_config(configs: dict[str, Any]) -> Any:
    """FormConfig for current genre."""
    return configs["form"]


@pytest.fixture
def key_config(configs: dict[str, Any]) -> Any:
    """KeyConfig for current genre."""
    return configs["key"]


@pytest.fixture
def schemas(configs: dict[str, Any]) -> Any:
    """Schema catalogue for current genre."""
    return configs["schemas"]
