"""L1 Rhetorical layer contract tests."""
from fractions import Fraction
from builder.types import GenreConfig
from planner.rhetorical import layer_1_rhetorical


def test_tempo_positive(genre_config: GenreConfig) -> None:
    """L1-01: tempo is int > 0."""
    _, _, tempo = layer_1_rhetorical(genre_config=genre_config)
    assert isinstance(tempo, int)
    assert tempo > 0


def test_tempo_plausible_range(genre_config: GenreConfig) -> None:
    """L1-02: tempo within 40..200."""
    _, _, tempo = layer_1_rhetorical(genre_config=genre_config)
    assert 40 <= tempo <= 200, f"Tempo {tempo} outside plausible range"


def test_rhythm_vocab_nonempty(genre_config: GenreConfig) -> None:
    """L1-03: rhythm_vocab is non-empty dict."""
    _, rhythm_vocab, _ = layer_1_rhetorical(genre_config=genre_config)
    assert isinstance(rhythm_vocab, dict)
    assert len(rhythm_vocab) > 0


def test_rhythmic_unit_valid_fraction(genre_config: GenreConfig) -> None:
    """L1-04: rhythmic_unit parseable as Fraction."""
    _, rhythm_vocab, _ = layer_1_rhetorical(genre_config=genre_config)
    assert "rhythmic_unit" in rhythm_vocab
    unit: Fraction = Fraction(rhythm_vocab["rhythmic_unit"])
    assert unit > 0


def test_trajectory_length(genre_config: GenreConfig) -> None:
    """L1-05: trajectory length == section count."""
    trajectory, _, _ = layer_1_rhetorical(genre_config=genre_config)
    assert len(trajectory) == len(genre_config.sections)


def test_trajectory_matches_sections(genre_config: GenreConfig) -> None:
    """L1-06: every trajectory entry matches section name."""
    trajectory, _, _ = layer_1_rhetorical(genre_config=genre_config)
    section_names: list[str] = [s["name"] for s in genre_config.sections]
    assert trajectory == section_names
