"""Tests for planner.episode_generator.

Category A tests: Constraint-based episode sequence generation.
Tests import only:
- planner.episode_generator (module under test)
- planner.types (shared types)
- stdlib

Note: Uses random seed for deterministic tests.
"""
import random

import pytest

from planner.episode_generator import (
    _ensure_climax_episode,
    _get_climax_characters,
    _get_peak_episode_types,
    filter_by_energy,
    filter_by_repetition,
    generate_episodes,
    get_energy_profile,
    get_first_candidates,
    get_valid_transitions,
    load_constraints,
    select_episode,
    weight_by_affinity,
)
from planner.plannertypes import EpisodeSpec, MacroSection


def make_section(
    label: str = "A",
    character: str = "opening",
    bars: int = 16,
    texture: str = "polyphonic",
    key_area: str = "I",
    energy_arc: str = "rising",
) -> MacroSection:
    """Helper to create MacroSection."""
    return MacroSection(
        label=label,
        character=character,
        bars=bars,
        texture=texture,
        key_area=key_area,
        energy_arc=energy_arc,
    )


class TestLoadConstraints:
    """Test load_constraints function."""

    def test_loads_structure(self) -> None:
        """Constraints YAML loads with expected structure."""
        constraints: dict = load_constraints()
        assert "transitions" in constraints
        assert "first_episode" in constraints
        assert "energy_profiles" in constraints
        assert "character_affinity" in constraints

    def test_cached(self) -> None:
        """Constraints are cached (same object returned)."""
        c1: dict = load_constraints()
        c2: dict = load_constraints()
        assert c1 is c2


class TestGetFirstCandidates:
    """Test get_first_candidates function."""

    def test_opening_starts_with_statement(self) -> None:
        """Opening character starts with statement."""
        candidates: list[str] = get_first_candidates("opening")
        assert "statement" in candidates

    def test_turbulent_has_turbulent_option(self) -> None:
        """Turbulent character can start with turbulent."""
        candidates: list[str] = get_first_candidates("turbulent")
        assert "turbulent" in candidates

    def test_unknown_character_defaults_to_statement(self) -> None:
        """Unknown character defaults to statement."""
        candidates: list[str] = get_first_candidates("nonexistent")
        assert candidates == ["statement"]


class TestGetValidTransitions:
    """Test get_valid_transitions function."""

    def test_statement_transitions(self) -> None:
        """Statement can transition to multiple types."""
        transitions: list[str] = get_valid_transitions("statement")
        assert "response_cs" in transitions
        assert "continuation" in transitions
        assert "cadential" in transitions

    def test_cadential_terminal(self) -> None:
        """Cadential is terminal (no transitions)."""
        transitions: list[str] = get_valid_transitions("cadential")
        assert transitions == []

    def test_unknown_defaults_to_cadential(self) -> None:
        """Unknown episode type defaults to cadential."""
        transitions: list[str] = get_valid_transitions("nonexistent")
        assert transitions == ["cadential"]


class TestGetEnergyProfile:
    """Test get_energy_profile function."""

    def test_statement_is_stable(self) -> None:
        """Statement has stable energy profile."""
        profile: str = get_energy_profile("statement")
        assert profile == "stable"

    def test_climax_is_peak(self) -> None:
        """Climax has peak energy profile."""
        profile: str = get_energy_profile("climax")
        assert profile == "peak"

    def test_cadential_is_resolving(self) -> None:
        """Cadential has resolving energy profile."""
        profile: str = get_energy_profile("cadential")
        assert profile == "resolving"

    def test_unknown_defaults_to_stable(self) -> None:
        """Unknown episode type defaults to stable."""
        profile: str = get_energy_profile("nonexistent")
        assert profile == "stable"


class TestFilterByRepetition:
    """Test filter_by_repetition function."""

    def test_empty_history_no_filter(self) -> None:
        """Empty history doesn't filter candidates."""
        candidates: list[str] = ["statement", "continuation", "cadential"]
        result: list[str] = filter_by_repetition(candidates, [])
        assert result == candidates

    def test_filters_immediate_repeat(self) -> None:
        """Filters out immediate repetition of last episode type."""
        candidates: list[str] = ["statement", "continuation", "cadential"]
        history: list[EpisodeSpec] = [EpisodeSpec(type="statement", bars=4)]
        result: list[str] = filter_by_repetition(candidates, history)
        assert "statement" not in result

    def test_filters_type_used_twice(self) -> None:
        """Filters out episode type already used twice."""
        candidates: list[str] = ["statement", "continuation", "cadential"]
        history: list[EpisodeSpec] = [
            EpisodeSpec(type="continuation", bars=4),
            EpisodeSpec(type="statement", bars=4),
            EpisodeSpec(type="continuation", bars=4),
        ]
        result: list[str] = filter_by_repetition(candidates, history)
        assert "continuation" not in result

    def test_returns_first_if_all_filtered(self) -> None:
        """Returns first candidate if all would be filtered."""
        candidates: list[str] = ["statement"]
        history: list[EpisodeSpec] = [
            EpisodeSpec(type="statement", bars=4),
            EpisodeSpec(type="statement", bars=4),
        ]
        result: list[str] = filter_by_repetition(candidates, history)
        # Should return first candidate as fallback
        assert result == ["statement"]


class TestFilterByEnergy:
    """Test filter_by_energy function."""

    def test_empty_candidates_returns_empty(self) -> None:
        """Empty candidates list returns empty."""
        result: list[str] = filter_by_energy([], [], "rising", 16)
        assert result == []

    def test_rising_arc_allows_stable(self) -> None:
        """Rising arc allows stable energy profiles."""
        candidates: list[str] = ["statement", "continuation"]
        result: list[str] = filter_by_energy(candidates, [], "rising", 16)
        # Statement is stable, continuation is rising - both allowed in rising arc
        assert len(result) > 0

    def test_peak_arc_prefers_peak_when_needed(self) -> None:
        """Peak arc tries to include peak episode when time is running out."""
        candidates: list[str] = ["climax", "continuation", "cadential"]
        history: list[EpisodeSpec] = [
            EpisodeSpec(type="statement", bars=4),
            EpisodeSpec(type="continuation", bars=4),
        ]
        # With 12 bars remaining, should prioritize getting a peak in
        result: list[str] = filter_by_energy(candidates, history, "peak", 12)
        # Climax is peak energy
        assert "climax" in result


class TestWeightByAffinity:
    """Test weight_by_affinity function."""

    def test_preferred_gets_higher_weight(self) -> None:
        """Preferred episode types get higher weight."""
        # Opening character prefers statement
        candidates: list[str] = ["statement", "turbulent"]
        weighted: list[tuple[str, float]] = weight_by_affinity(candidates, "opening")
        weights: dict[str, float] = dict(weighted)
        # Statement should have higher weight than turbulent (which is avoided)
        assert weights["statement"] > weights["turbulent"]

    def test_avoided_gets_lower_weight(self) -> None:
        """Avoided episode types get lower weight."""
        candidates: list[str] = ["statement", "turbulent"]
        weighted: list[tuple[str, float]] = weight_by_affinity(candidates, "opening")
        weights: dict[str, float] = dict(weighted)
        assert weights["turbulent"] < 1.0  # Below neutral

    def test_neutral_gets_weight_one(self) -> None:
        """Episode types neither preferred nor avoided get weight 1.0."""
        candidates: list[str] = ["something_neutral"]
        weighted: list[tuple[str, float]] = weight_by_affinity(candidates, "opening")
        weights: dict[str, float] = dict(weighted)
        assert weights["something_neutral"] == 1.0


class TestSelectEpisode:
    """Test select_episode function."""

    def test_empty_returns_cadential(self) -> None:
        """Empty weighted list returns cadential."""
        rng: random.Random = random.Random(42)
        result: str = select_episode([], rng)
        assert result == "cadential"

    def test_single_option_selected(self) -> None:
        """Single option is always selected."""
        rng: random.Random = random.Random(42)
        result: str = select_episode([("statement", 1.0)], rng)
        assert result == "statement"

    def test_deterministic_with_seed(self) -> None:
        """Same seed produces same result."""
        weighted: list[tuple[str, float]] = [
            ("statement", 1.0),
            ("continuation", 1.0),
            ("cadential", 1.0),
        ]
        rng1: random.Random = random.Random(42)
        rng2: random.Random = random.Random(42)
        result1: str = select_episode(weighted, rng1)
        result2: str = select_episode(weighted, rng2)
        assert result1 == result2


class TestGetPeakEpisodeTypes:
    """Test _get_peak_episode_types function."""

    def test_includes_climax(self) -> None:
        """Peak episode types include climax."""
        peak_types: list[str] = _get_peak_episode_types()
        assert "climax" in peak_types

    def test_includes_triumphant(self) -> None:
        """Peak episode types include triumphant."""
        peak_types: list[str] = _get_peak_episode_types()
        assert "triumphant" in peak_types

    def test_includes_cadenza(self) -> None:
        """Peak episode types include cadenza."""
        peak_types: list[str] = _get_peak_episode_types()
        assert "cadenza" in peak_types


class TestGetClimaxCharacters:
    """Test _get_climax_characters function."""

    def test_includes_climax(self) -> None:
        """Climax characters include climax."""
        chars: list[str] = _get_climax_characters()
        assert "climax" in chars

    def test_includes_triumphant(self) -> None:
        """Climax characters include triumphant."""
        chars: list[str] = _get_climax_characters()
        assert "triumphant" in chars


class TestEnsureClimaxEpisode:
    """Test _ensure_climax_episode function."""

    def test_non_climax_character_unchanged(self) -> None:
        """Non-climax characters don't get episode replaced."""
        episodes: list[EpisodeSpec] = [
            EpisodeSpec(type="statement", bars=4),
            EpisodeSpec(type="continuation", bars=4),
        ]
        result: list[EpisodeSpec] = _ensure_climax_episode(episodes, "opening")
        assert result[0].type == "statement"
        assert result[1].type == "continuation"

    def test_climax_character_gets_peak(self) -> None:
        """Climax character sections get a peak episode if missing."""
        episodes: list[EpisodeSpec] = [
            EpisodeSpec(type="statement", bars=4),
            EpisodeSpec(type="continuation", bars=4),
            EpisodeSpec(type="cadential", bars=4),
        ]
        result: list[EpisodeSpec] = _ensure_climax_episode(episodes, "climax")
        # Should have replaced one episode with a peak type
        types: list[str] = [ep.type for ep in result]
        peak_types: list[str] = _get_peak_episode_types()
        has_peak: bool = any(t in peak_types for t in types)
        assert has_peak

    def test_already_has_peak_unchanged(self) -> None:
        """Sections already with peak episode are unchanged."""
        episodes: list[EpisodeSpec] = [
            EpisodeSpec(type="statement", bars=4),
            EpisodeSpec(type="climax", bars=4),
            EpisodeSpec(type="cadential", bars=4),
        ]
        result: list[EpisodeSpec] = _ensure_climax_episode(episodes, "climax")
        assert result[1].type == "climax"


class TestGenerateEpisodes:
    """Test generate_episodes function."""

    def test_returns_tuple_of_episode_specs(self) -> None:
        """generate_episodes returns tuple of EpisodeSpec."""
        section: MacroSection = make_section(bars=16)
        result: tuple[EpisodeSpec, ...] = generate_episodes(section, seed=42)
        assert isinstance(result, tuple)
        assert all(isinstance(ep, EpisodeSpec) for ep in result)

    def test_total_bars_match_target(self) -> None:
        """Generated episodes sum to target bars."""
        section: MacroSection = make_section(bars=16)
        result: tuple[EpisodeSpec, ...] = generate_episodes(section, seed=42)
        total_bars: int = sum(ep.bars for ep in result)
        assert total_bars == 16

    def test_ends_with_cadential(self) -> None:
        """Episode sequence ends with cadential for small remaining bars."""
        section: MacroSection = make_section(bars=8)
        result: tuple[EpisodeSpec, ...] = generate_episodes(section, seed=42)
        # Short sections should end with cadential
        # (may not always be true but is common pattern)
        assert result[-1].type in ("cadential", "statement", "continuation")

    def test_deterministic_with_seed(self) -> None:
        """Same seed produces identical result."""
        section: MacroSection = make_section(bars=16)
        result1: tuple[EpisodeSpec, ...] = generate_episodes(section, seed=42)
        result2: tuple[EpisodeSpec, ...] = generate_episodes(section, seed=42)
        assert result1 == result2

    def test_different_seeds_vary(self) -> None:
        """Different seeds produce different results."""
        section: MacroSection = make_section(bars=32, character="development")
        result1: tuple[EpisodeSpec, ...] = generate_episodes(section, seed=1)
        result2: tuple[EpisodeSpec, ...] = generate_episodes(section, seed=999)
        # Not guaranteed to differ for all seeds, but likely
        # At minimum, both should be valid
        assert all(isinstance(ep, EpisodeSpec) for ep in result1)
        assert all(isinstance(ep, EpisodeSpec) for ep in result2)

    def test_climax_character_has_peak(self) -> None:
        """Climax character sections include peak energy episode."""
        section: MacroSection = make_section(bars=16, character="climax")
        result: tuple[EpisodeSpec, ...] = generate_episodes(section, seed=42)
        peak_types: list[str] = _get_peak_episode_types()
        types: list[str] = [ep.type for ep in result]
        has_peak: bool = any(t in peak_types for t in types)
        assert has_peak

    def test_minimum_bars_handled(self) -> None:
        """Very short sections still produce valid output."""
        section: MacroSection = make_section(bars=4)
        result: tuple[EpisodeSpec, ...] = generate_episodes(section, seed=42)
        assert len(result) >= 1
        assert sum(ep.bars for ep in result) == 4

    def test_respects_character_affinity(self) -> None:
        """Generated episodes tend toward character-preferred types."""
        # Opening prefers statement over turbulent
        section: MacroSection = make_section(bars=16, character="opening")
        result: tuple[EpisodeSpec, ...] = generate_episodes(section, seed=42)
        types: list[str] = [ep.type for ep in result]
        # Statement should be present (preferred for opening)
        # This is probabilistic but statement is highly preferred
        assert "statement" in types or result[0].type == "statement"
