"""100% coverage tests for engine.schema.

Tests import only:
- engine.schema (module under test)
- shared (pitch, timed_material)
- stdlib

Schema module implements partimento-style harmonic schemas - bass patterns that
imply harmonic progressions. Schemas are loaded from schemas.yaml.
"""
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote

from engine.schema import (
    SCHEMAS,
    Schema,
    apply_schema,
    get_schema_names,
    load_schema,
    schema_for_context,
)


class TestSchemasConstant:
    """Test SCHEMAS data loaded from YAML."""

    def test_schemas_is_dict(self) -> None:
        """SCHEMAS is a dictionary."""
        assert isinstance(SCHEMAS, dict)

    def test_contains_romanesca(self) -> None:
        """SCHEMAS contains romanesca."""
        assert "romanesca" in SCHEMAS

    def test_contains_rule_of_octave_asc(self) -> None:
        """SCHEMAS contains rule_of_octave_asc."""
        assert "rule_of_octave_asc" in SCHEMAS

    def test_contains_rule_of_octave_desc(self) -> None:
        """SCHEMAS contains rule_of_octave_desc."""
        assert "rule_of_octave_desc" in SCHEMAS

    def test_contains_monte(self) -> None:
        """SCHEMAS contains monte."""
        assert "monte" in SCHEMAS

    def test_contains_fonte(self) -> None:
        """SCHEMAS contains fonte."""
        assert "fonte" in SCHEMAS

    def test_contains_prinner(self) -> None:
        """SCHEMAS contains prinner."""
        assert "prinner" in SCHEMAS

    def test_each_schema_has_bass_degrees(self) -> None:
        """Each schema has bass_degrees."""
        for name, data in SCHEMAS.items():
            assert "bass_degrees" in data, f"Schema {name} missing bass_degrees"

    def test_each_schema_has_soprano_degrees(self) -> None:
        """Each schema has soprano_degrees."""
        for name, data in SCHEMAS.items():
            assert "soprano_degrees" in data, f"Schema {name} missing soprano_degrees"

    def test_each_schema_has_durations(self) -> None:
        """Each schema has durations."""
        for name, data in SCHEMAS.items():
            assert "durations" in data, f"Schema {name} missing durations"

    def test_each_schema_has_bars(self) -> None:
        """Each schema has bars."""
        for name, data in SCHEMAS.items():
            assert "bars" in data, f"Schema {name} missing bars"


class TestSchemaDataclass:
    """Test Schema dataclass."""

    def test_schema_is_frozen(self) -> None:
        """Schema is immutable (frozen)."""
        schema: Schema = Schema(
            name="test",
            bass_degrees=(1, 2, 3),
            soprano_degrees=(3, 4, 5),
            durations=(Fraction(1, 2), Fraction(1, 2), Fraction(1, 2)),
            bars=2,
            cadence_approach=False,
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            schema.name = "changed"  # type: ignore

    def test_schema_fields(self) -> None:
        """Schema has expected fields."""
        schema: Schema = Schema(
            name="test",
            bass_degrees=(1, 5, 1),
            soprano_degrees=(3, 7, 3),
            durations=(Fraction(1, 2), Fraction(1, 4), Fraction(1, 4)),
            bars=1,
            cadence_approach=True,
        )
        assert schema.name == "test"
        assert schema.bass_degrees == (1, 5, 1)
        assert schema.soprano_degrees == (3, 7, 3)
        assert schema.durations == (Fraction(1, 2), Fraction(1, 4), Fraction(1, 4))
        assert schema.bars == 1
        assert schema.cadence_approach is True


class TestLoadSchema:
    """Test load_schema function."""

    def test_load_romanesca(self) -> None:
        """Load romanesca schema."""
        schema: Schema = load_schema("romanesca")
        assert schema.name == "romanesca"
        assert len(schema.bass_degrees) == 8
        assert len(schema.soprano_degrees) == 8
        assert len(schema.durations) == 8
        assert schema.bars == 4

    def test_romanesca_bass_degrees(self) -> None:
        """Romanesca has descending bass: 1-7-6-5-4-3-2-1."""
        schema: Schema = load_schema("romanesca")
        assert schema.bass_degrees == (1, 7, 6, 5, 4, 3, 2, 1)

    def test_romanesca_soprano_degrees(self) -> None:
        """Romanesca soprano has 5-5-3-3-1-1-7-1 pattern."""
        schema: Schema = load_schema("romanesca")
        assert schema.soprano_degrees == (5, 5, 3, 3, 1, 1, 7, 1)

    def test_romanesca_durations(self) -> None:
        """Romanesca uses half notes."""
        schema: Schema = load_schema("romanesca")
        assert all(d == Fraction(1, 2) for d in schema.durations)

    def test_load_monte(self) -> None:
        """Load monte schema."""
        schema: Schema = load_schema("monte")
        assert schema.name == "monte"
        assert schema.bass_degrees == (5, 1, 6, 2, 7, 3)
        assert schema.bars == 3

    def test_load_fonte(self) -> None:
        """Load fonte schema."""
        schema: Schema = load_schema("fonte")
        assert schema.name == "fonte"
        assert schema.bass_degrees == (5, 1, 4, 7, 3, 6)
        assert schema.bars == 3

    def test_load_prinner(self) -> None:
        """Load prinner schema."""
        schema: Schema = load_schema("prinner")
        assert schema.name == "prinner"
        assert schema.bass_degrees == (6, 5, 4, 3)
        assert schema.cadence_approach is True

    def test_cadence_approach_default_false(self) -> None:
        """cadence_approach defaults to False."""
        schema: Schema = load_schema("romanesca")
        assert schema.cadence_approach is False

    def test_unknown_schema_asserts(self) -> None:
        """Unknown schema name raises AssertionError."""
        with pytest.raises(AssertionError, match="Unknown schema"):
            load_schema("nonexistent_schema_xyz")


class TestApplySchema:
    """Test apply_schema function."""

    def test_returns_tuple_of_timed_materials(self) -> None:
        """Returns tuple of (soprano, bass) TimedMaterial."""
        from shared.timed_material import TimedMaterial
        soprano, bass = apply_schema("romanesca", Fraction(4))
        assert isinstance(soprano, TimedMaterial)
        assert isinstance(bass, TimedMaterial)

    def test_budget_preserved_soprano(self) -> None:
        """Soprano budget matches requested budget."""
        soprano, _ = apply_schema("romanesca", Fraction(4))
        assert soprano.budget == Fraction(4)

    def test_budget_preserved_bass(self) -> None:
        """Bass budget matches requested budget."""
        _, bass = apply_schema("romanesca", Fraction(4))
        assert bass.budget == Fraction(4)

    def test_durations_sum_to_budget(self) -> None:
        """Durations sum to budget for both voices."""
        soprano, bass = apply_schema("romanesca", Fraction(4))
        assert sum(soprano.durations) == Fraction(4)
        assert sum(bass.durations) == Fraction(4)

    def test_pitch_counts_match(self) -> None:
        """Soprano and bass have same number of pitches."""
        soprano, bass = apply_schema("monte", Fraction(3))
        assert len(soprano.pitches) == len(bass.pitches)

    def test_all_pitches_are_floating_notes(self) -> None:
        """All pitches are FloatingNote instances."""
        soprano, bass = apply_schema("fonte", Fraction(3))
        for p in soprano.pitches:
            assert isinstance(p, FloatingNote)
        for p in bass.pitches:
            assert isinstance(p, FloatingNote)

    def test_degrees_in_valid_range(self) -> None:
        """All degrees are in valid 1-7 range."""
        soprano, bass = apply_schema("romanesca", Fraction(8))
        for p in soprano.pitches:
            assert 1 <= p.degree <= 7
        for p in bass.pitches:
            assert 1 <= p.degree <= 7

    def test_start_degree_transposes(self) -> None:
        """start_degree transposes the schema."""
        sop1, bass1 = apply_schema("prinner", Fraction(2), start_degree=1)
        sop5, bass5 = apply_schema("prinner", Fraction(2), start_degree=5)
        # Degrees should be offset by 4 (5-1)
        d1_bass: list[int] = [p.degree for p in bass1.pitches]
        d5_bass: list[int] = [p.degree for p in bass5.pitches]
        # Not equal due to transposition
        assert d1_bass != d5_bass

    def test_partial_budget_truncates(self) -> None:
        """Budget smaller than schema duration truncates."""
        soprano, bass = apply_schema("romanesca", Fraction(1))
        # romanesca is 4 bars with 1/2 durations = 8 notes
        # 1 bar budget can fit 2 half notes
        assert sum(soprano.durations) == Fraction(1)
        assert len(soprano.pitches) == 2

    def test_budget_larger_than_schema_repeats(self) -> None:
        """Budget larger than schema repeats the pattern."""
        soprano, bass = apply_schema("prinner", Fraction(4))
        # prinner is 2 bars, budget=4 should repeat twice
        # Each repetition has 4 notes (half notes)
        assert len(soprano.pitches) == 8

    def test_repeated_schema_cycles_degrees(self) -> None:
        """Repeated schema transposes each cycle (ascending sequence)."""
        soprano, bass = apply_schema("prinner", Fraction(4), start_degree=1)
        # First cycle and second cycle should differ
        first_half: list[int] = [p.degree for p in bass.pitches[:4]]
        second_half: list[int] = [p.degree for p in bass.pitches[4:]]
        # Second cycle is transposed up by 1 degree
        assert first_half != second_half


class TestGetSchemaNames:
    """Test get_schema_names function."""

    def test_returns_list(self) -> None:
        """Returns a list."""
        names: list[str] = get_schema_names()
        assert isinstance(names, list)

    def test_contains_all_schemas(self) -> None:
        """Contains all defined schemas."""
        names: list[str] = get_schema_names()
        expected: set[str] = {"romanesca", "rule_of_octave_asc", "rule_of_octave_desc",
                             "monte", "fonte", "prinner"}
        assert expected.issubset(set(names))

    def test_count_matches_schemas(self) -> None:
        """Count matches SCHEMAS dict."""
        names: list[str] = get_schema_names()
        assert len(names) == len(SCHEMAS)


class TestSchemaForContext:
    """Test schema_for_context function."""

    def test_cadence_approach_returns_prinner(self) -> None:
        """Cadence approach returns prinner."""
        result: str | None = schema_for_context("statement", "I", is_cadence_approach=True)
        assert result == "prinner"

    def test_turbulent_episode_returns_fonte(self) -> None:
        """Turbulent episode returns fonte."""
        result: str | None = schema_for_context("turbulent", "I", is_cadence_approach=False)
        assert result == "fonte"

    def test_intensification_episode_returns_monte(self) -> None:
        """Intensification episode returns monte."""
        result: str | None = schema_for_context("intensification", "I", is_cadence_approach=False)
        assert result == "monte"

    def test_dominant_target_returns_rule_of_octave_asc(self) -> None:
        """Target V returns rule_of_octave_asc."""
        result: str | None = schema_for_context("statement", "V", is_cadence_approach=False)
        assert result == "rule_of_octave_asc"

    def test_minor_dominant_target_returns_rule_of_octave_asc(self) -> None:
        """Target v returns rule_of_octave_asc."""
        result: str | None = schema_for_context("statement", "v", is_cadence_approach=False)
        assert result == "rule_of_octave_asc"

    def test_subdominant_target_returns_romanesca(self) -> None:
        """Target IV returns romanesca."""
        result: str | None = schema_for_context("statement", "IV", is_cadence_approach=False)
        assert result == "romanesca"

    def test_minor_subdominant_target_returns_romanesca(self) -> None:
        """Target iv returns romanesca."""
        result: str | None = schema_for_context("statement", "iv", is_cadence_approach=False)
        assert result == "romanesca"

    def test_no_match_returns_none(self) -> None:
        """No matching context returns None."""
        result: str | None = schema_for_context("statement", "I", is_cadence_approach=False)
        assert result is None

    def test_none_episode_returns_none(self) -> None:
        """None episode type returns None (unless other conditions match)."""
        result: str | None = schema_for_context(None, "I", is_cadence_approach=False)
        assert result is None

    def test_cadence_approach_takes_priority(self) -> None:
        """Cadence approach takes priority over episode type."""
        # Even with turbulent episode, cadence approach should return prinner
        result: str | None = schema_for_context("turbulent", "V", is_cadence_approach=True)
        assert result == "prinner"


class TestIntegration:
    """Integration tests for schema module."""

    def test_all_schemas_can_be_applied(self) -> None:
        """All defined schemas can be applied."""
        for name in get_schema_names():
            soprano, bass = apply_schema(name, Fraction(4))
            assert sum(soprano.durations) == Fraction(4)
            assert sum(bass.durations) == Fraction(4)

    def test_context_to_application_workflow(self) -> None:
        """Complete workflow from context to applied schema."""
        # Get schema for cadence approach
        schema_name: str | None = schema_for_context("statement", "I", is_cadence_approach=True)
        assert schema_name == "prinner"
        # Apply the schema
        soprano, bass = apply_schema(schema_name, Fraction(2))
        assert soprano.budget == Fraction(2)
        assert bass.budget == Fraction(2)

    def test_romanesca_musical_correctness(self) -> None:
        """Romanesca produces musically correct degrees.

        Domain knowledge: Romanesca is a descending bass pattern 1-7-6-5-4-3-2-1
        with characteristic 5-5-3-3-1-1-7-1 soprano.
        """
        soprano, bass = apply_schema("romanesca", Fraction(4))
        bass_degrees: list[int] = [p.degree for p in bass.pitches]
        soprano_degrees: list[int] = [p.degree for p in soprano.pitches]
        assert bass_degrees == [1, 7, 6, 5, 4, 3, 2, 1]
        assert soprano_degrees == [5, 5, 3, 3, 1, 1, 7, 1]

    def test_prinner_musical_correctness(self) -> None:
        """Prinner produces musically correct cadence approach.

        Domain knowledge: Prinner is 6-5-4-3 bass with 4-3-2-1 soprano,
        a standard cadence preparation.
        """
        soprano, bass = apply_schema("prinner", Fraction(2))
        bass_degrees: list[int] = [p.degree for p in bass.pitches]
        soprano_degrees: list[int] = [p.degree for p in soprano.pitches]
        assert bass_degrees == [6, 5, 4, 3]
        assert soprano_degrees == [4, 3, 2, 1]

    def test_monte_musical_correctness(self) -> None:
        """Monte produces ascending fifths sequence.

        Domain knowledge: Monte is an ascending sequence pattern
        5-1-6-2-7-3 bass that rises by step.
        """
        schema: Schema = load_schema("monte")
        assert schema.bass_degrees == (5, 1, 6, 2, 7, 3)
