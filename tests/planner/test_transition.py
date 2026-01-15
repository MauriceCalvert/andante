"""Tests for planner.transition.

Category A tests: Transition planning between macro-sections.
Tests import only:
- planner.transition (module under test)
- planner.types (shared types)
- stdlib

Note: Uses YAML data files for transition definitions.
"""
import pytest

from planner.transition import (
    RELATED_KEYS,
    generate_transition,
    keys_are_related,
    load_yaml,
    needs_transition,
    select_transition_type,
)
from planner.plannertypes import EpisodeSpec, MacroSection


def make_section(
    label: str = "A",
    character: str = "expressive",
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


class TestLoadYaml:
    """Test load_yaml function."""

    def test_loads_transitions(self) -> None:
        """Transitions data loads successfully."""
        data: dict = load_yaml("transitions.yaml")
        assert "cadential" in data
        assert "pivot" in data
        assert "linking" in data

    def test_transition_has_bars(self) -> None:
        """Each transition type has bars field."""
        data: dict = load_yaml("transitions.yaml")
        for name, trans in data.items():
            assert "bars" in trans, f"Transition {name} missing 'bars'"
            assert isinstance(trans["bars"], int)


class TestRelatedKeys:
    """Test RELATED_KEYS constant."""

    def test_contains_tonic_dominant(self) -> None:
        """I and V are related (dominant relationship)."""
        assert ("I", "V") in RELATED_KEYS
        assert ("V", "I") in RELATED_KEYS

    def test_contains_tonic_subdominant(self) -> None:
        """I and IV are related (subdominant relationship)."""
        assert ("I", "IV") in RELATED_KEYS
        assert ("IV", "I") in RELATED_KEYS

    def test_contains_relative_minor(self) -> None:
        """I and vi are related (relative minor)."""
        assert ("I", "vi") in RELATED_KEYS
        assert ("vi", "I") in RELATED_KEYS

    def test_minor_mode_relationships(self) -> None:
        """Minor mode key relationships are included."""
        assert ("i", "III") in RELATED_KEYS  # Relative major
        assert ("i", "v") in RELATED_KEYS    # Minor dominant
        assert ("i", "iv") in RELATED_KEYS   # Minor subdominant


class TestKeysAreRelated:
    """Test keys_are_related function."""

    def test_same_key_is_related(self) -> None:
        """Same key is always related to itself."""
        assert keys_are_related("I", "I") is True
        assert keys_are_related("V", "V") is True
        assert keys_are_related("vi", "vi") is True

    def test_tonic_dominant_related(self) -> None:
        """Tonic and dominant are related."""
        assert keys_are_related("I", "V") is True
        assert keys_are_related("V", "I") is True

    def test_distant_keys_not_related(self) -> None:
        """Distant keys are not related."""
        assert keys_are_related("I", "iii") is False
        assert keys_are_related("I", "ii") is False

    def test_cross_mode_not_related(self) -> None:
        """Major I and minor i not in RELATED_KEYS (different modes)."""
        # Note: This tests the set as defined, not music theory
        assert ("I", "i") not in RELATED_KEYS


class TestSelectTransitionType:
    """Test select_transition_type function."""

    def test_same_key_uses_linking(self) -> None:
        """Same key area uses linking transition."""
        from_sec: MacroSection = make_section(key_area="I", character="expressive")
        to_sec: MacroSection = make_section(key_area="I", character="dramatic")
        result: str = select_transition_type(from_sec, to_sec)
        assert result == "linking"

    def test_to_climax_uses_cadential(self) -> None:
        """Transition to climax section uses cadential."""
        from_sec: MacroSection = make_section(key_area="I", character="expressive")
        to_sec: MacroSection = make_section(key_area="V", character="climax")
        result: str = select_transition_type(from_sec, to_sec)
        assert result == "cadential"

    def test_to_triumphant_uses_cadential(self) -> None:
        """Transition to triumphant section uses cadential (when keys differ)."""
        from_sec: MacroSection = make_section(key_area="I")
        to_sec: MacroSection = make_section(key_area="V", character="triumphant")
        result: str = select_transition_type(from_sec, to_sec)
        assert result == "cadential"

    def test_same_key_triumphant_uses_linking(self) -> None:
        """Same key to triumphant uses linking (key check precedes character check)."""
        from_sec: MacroSection = make_section(key_area="I")
        to_sec: MacroSection = make_section(key_area="I", character="triumphant")
        result: str = select_transition_type(from_sec, to_sec)
        assert result == "linking"

    def test_contrast_unrelated_uses_dramatic(self) -> None:
        """Contrasting characters with unrelated keys use dramatic."""
        from_sec: MacroSection = make_section(key_area="I", character="expressive")
        to_sec: MacroSection = make_section(key_area="iii", character="turbulent")  # Unrelated key
        result: str = select_transition_type(from_sec, to_sec)
        assert result == "dramatic"

    def test_turbulent_unrelated_uses_chromatic(self) -> None:
        """Turbulent to unrelated key uses chromatic."""
        from_sec: MacroSection = make_section(key_area="I", character="turbulent")
        to_sec: MacroSection = make_section(key_area="iii", character="turbulent")  # Same char, unrelated
        result: str = select_transition_type(from_sec, to_sec)
        assert result == "chromatic"

    def test_non_turbulent_unrelated_uses_sequential(self) -> None:
        """Non-turbulent to unrelated key uses sequential."""
        from_sec: MacroSection = make_section(key_area="I", character="expressive")
        to_sec: MacroSection = make_section(key_area="iii", character="expressive")  # Same char, unrelated
        result: str = select_transition_type(from_sec, to_sec)
        assert result == "sequential"

    def test_related_keys_use_pivot(self) -> None:
        """Related keys with different characters use pivot."""
        from_sec: MacroSection = make_section(key_area="I", character="expressive")
        to_sec: MacroSection = make_section(key_area="V", character="dramatic")  # Related, different char
        result: str = select_transition_type(from_sec, to_sec)
        assert result == "pivot"


class TestGenerateTransition:
    """Test generate_transition function."""

    def test_returns_episode_spec(self) -> None:
        """generate_transition returns EpisodeSpec."""
        from_sec: MacroSection = make_section(key_area="I")
        to_sec: MacroSection = make_section(key_area="V")
        result: EpisodeSpec = generate_transition(from_sec, to_sec)
        assert isinstance(result, EpisodeSpec)

    def test_is_transition_flag_set(self) -> None:
        """Transition episodes have is_transition=True."""
        from_sec: MacroSection = make_section(key_area="I")
        to_sec: MacroSection = make_section(key_area="V")
        result: EpisodeSpec = generate_transition(from_sec, to_sec)
        assert result.is_transition is True

    def test_type_matches_selection(self) -> None:
        """Episode type matches selected transition type."""
        from_sec: MacroSection = make_section(key_area="I", character="expressive")
        to_sec: MacroSection = make_section(key_area="I", character="dramatic")
        result: EpisodeSpec = generate_transition(from_sec, to_sec)
        # Same key uses linking
        assert result.type == "linking"

    def test_bars_from_transitions_yaml(self) -> None:
        """Bars come from transitions.yaml definition."""
        data: dict = load_yaml("transitions.yaml")
        from_sec: MacroSection = make_section(key_area="I")
        to_sec: MacroSection = make_section(key_area="I", character="different")
        result: EpisodeSpec = generate_transition(from_sec, to_sec)
        expected_bars: int = data["linking"]["bars"]
        assert result.bars == expected_bars

    def test_cadential_transition_bars(self) -> None:
        """Cadential transition has correct bars."""
        data: dict = load_yaml("transitions.yaml")
        from_sec: MacroSection = make_section(key_area="I")
        to_sec: MacroSection = make_section(key_area="V", character="climax")
        result: EpisodeSpec = generate_transition(from_sec, to_sec)
        assert result.type == "cadential"
        assert result.bars == data["cadential"]["bars"]


class TestNeedsTransition:
    """Test needs_transition function."""

    def test_different_key_needs_transition(self) -> None:
        """Different key areas need transition."""
        from_sec: MacroSection = make_section(key_area="I")
        to_sec: MacroSection = make_section(key_area="V")
        assert needs_transition(from_sec, to_sec) is True

    def test_different_character_needs_transition(self) -> None:
        """Different characters need transition."""
        from_sec: MacroSection = make_section(character="expressive")
        to_sec: MacroSection = make_section(character="turbulent")
        assert needs_transition(from_sec, to_sec) is True

    def test_same_key_and_character_no_transition(self) -> None:
        """Same key and character don't need transition."""
        from_sec: MacroSection = make_section(key_area="I", character="expressive")
        to_sec: MacroSection = make_section(key_area="I", character="expressive")
        assert needs_transition(from_sec, to_sec) is False

    def test_same_key_different_character_needs_transition(self) -> None:
        """Same key but different character needs transition."""
        from_sec: MacroSection = make_section(key_area="I", character="expressive")
        to_sec: MacroSection = make_section(key_area="I", character="turbulent")
        assert needs_transition(from_sec, to_sec) is True

    def test_different_key_same_character_needs_transition(self) -> None:
        """Different key but same character needs transition."""
        from_sec: MacroSection = make_section(key_area="I", character="expressive")
        to_sec: MacroSection = make_section(key_area="V", character="expressive")
        assert needs_transition(from_sec, to_sec) is True
