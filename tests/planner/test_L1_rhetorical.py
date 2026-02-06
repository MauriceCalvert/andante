"""L1 Rhetorical layer contract tests."""
from fractions import Fraction
from builder.types import GenreConfig
from planner.rhetorical import layer_1_rhetorical
from shared.constants import VALID_DURATIONS_SET


def test_tempo_matches_genre_spec(genre_config: GenreConfig) -> None:
    """L1-01: tempo exactly matches genre YAML specification."""
    _, _, tempo = layer_1_rhetorical(genre_config=genre_config)
    assert isinstance(tempo, int)
    assert tempo == genre_config.tempo, (
        f"Genre '{genre_config.name}': L1 returned tempo {tempo}, "
        f"expected {genre_config.tempo} from genre spec"
    )


def test_rhythmic_unit_in_valid_durations(genre_config: GenreConfig) -> None:
    """L1-02: rhythmic_unit is a valid duration from VALID_DURATIONS."""
    _, rhythm_vocab, _ = layer_1_rhetorical(genre_config=genre_config)
    assert "rhythmic_unit" in rhythm_vocab, "rhythm_vocab missing 'rhythmic_unit' key"
    unit: Fraction = Fraction(rhythm_vocab["rhythmic_unit"])
    assert unit in VALID_DURATIONS_SET, (
        f"Genre '{genre_config.name}': rhythmic_unit {unit} "
        f"not in VALID_DURATIONS"
    )


def test_rhythmic_unit_matches_genre_spec(genre_config: GenreConfig) -> None:
    """L1-03: rhythmic_unit matches genre YAML specification."""
    _, rhythm_vocab, _ = layer_1_rhetorical(genre_config=genre_config)
    expected: Fraction = Fraction(genre_config.rhythmic_unit)
    actual: Fraction = Fraction(rhythm_vocab["rhythmic_unit"])
    assert actual == expected, (
        f"Genre '{genre_config.name}': L1 returned rhythmic_unit {actual}, "
        f"expected {expected} from genre spec"
    )


def test_trajectory_length(genre_config: GenreConfig) -> None:
    """L1-04: trajectory length == section count."""
    trajectory, _, _ = layer_1_rhetorical(genre_config=genre_config)
    assert len(trajectory) == len(genre_config.sections)


def test_trajectory_matches_sections(genre_config: GenreConfig) -> None:
    """L1-05: trajectory entries match section names from genre spec."""
    trajectory, _, _ = layer_1_rhetorical(genre_config=genre_config)
    section_names: list[str] = [s["name"] for s in genre_config.sections]
    assert trajectory == section_names, (
        f"Genre '{genre_config.name}': trajectory {trajectory} "
        f"does not match sections {section_names}"
    )
