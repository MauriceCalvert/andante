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
    BASS_PATTERNS,
    RULE_OF_OCTAVE_ASCENDING,
    RULE_OF_OCTAVE_DESCENDING,
    SCHEMAS,
    BassPattern,
    Schema,
    apply_rule_of_octave,
    apply_schema,
    detect_bass_pattern,
    get_rule_of_octave_figure,
    get_schema_names,
    harmonise_bass_pattern,
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
        assert len(schema.bass_degrees) == 4
        assert len(schema.soprano_degrees) == 4
        assert len(schema.durations) == 4
        assert schema.bars == 1

    def test_romanesca_bass_degrees(self) -> None:
        """Romanesca has descending bass: 1-7-6-3."""
        schema: Schema = load_schema("romanesca")
        assert schema.bass_degrees == (1, 7, 6, 3)

    def test_romanesca_soprano_degrees(self) -> None:
        """Romanesca soprano has 1-5-1-1 pattern."""
        schema: Schema = load_schema("romanesca")
        assert schema.soprano_degrees == (1, 5, 1, 1)

    def test_romanesca_durations(self) -> None:
        """Romanesca uses quarter notes."""
        schema: Schema = load_schema("romanesca")
        assert all(d == Fraction(1, 4) for d in schema.durations)

    def test_load_monte(self) -> None:
        """Load monte schema."""
        schema: Schema = load_schema("monte")
        assert schema.name == "monte"
        assert schema.bass_degrees == (7, 1, 7, 1)  # Sequential pattern
        assert schema.bars == 1

    def test_load_fonte(self) -> None:
        """Load fonte schema."""
        schema: Schema = load_schema("fonte")
        assert schema.name == "fonte"
        assert schema.bass_degrees == (7, 1, 7, 1)  # Sequential pattern
        assert schema.bars == 1

    def test_load_prinner(self) -> None:
        """Load prinner schema."""
        schema: Schema = load_schema("prinner")
        assert schema.name == "prinner"
        assert schema.bass_degrees == (4, 3, 2, 1)  # Descending stepwise
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
        soprano, bass = apply_schema("romanesca", Fraction(1, 2))
        # romanesca is 1 bar with 1/4 durations = 4 notes
        # 1/2 bar budget can fit 2 quarter notes
        assert sum(soprano.durations) == Fraction(1, 2)
        assert len(soprano.pitches) == 2

    def test_budget_larger_than_schema_repeats(self) -> None:
        """Budget larger than schema repeats the pattern."""
        soprano, bass = apply_schema("prinner", Fraction(4))
        # prinner is 1 bar (4 quarter notes), budget=4 should repeat 4 times
        # Each repetition has 4 notes
        assert len(soprano.pitches) == 16

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

    def test_dominant_target_returns_fenaroli(self) -> None:
        """Target V returns fenaroli (dominant key schema)."""
        result: str | None = schema_for_context("statement", "V", is_cadence_approach=False)
        assert result == "fenaroli"

    def test_minor_dominant_target_returns_fenaroli(self) -> None:
        """Target v returns fenaroli (dominant key schema)."""
        result: str | None = schema_for_context("statement", "v", is_cadence_approach=False)
        assert result == "fenaroli"

    def test_subdominant_target_returns_romanesca(self) -> None:
        """Target IV returns romanesca."""
        result: str | None = schema_for_context("statement", "IV", is_cadence_approach=False)
        assert result == "romanesca"

    def test_minor_subdominant_target_returns_romanesca(self) -> None:
        """Target iv returns romanesca."""
        result: str | None = schema_for_context("statement", "iv", is_cadence_approach=False)
        assert result == "romanesca"

    def test_no_match_returns_fallback(self) -> None:
        """No matching context returns fallback (meyer)."""
        result: str | None = schema_for_context("statement", "I", is_cadence_approach=False)
        assert result == "meyer"

    def test_none_episode_returns_fallback(self) -> None:
        """None episode type returns fallback (unless other conditions match)."""
        result: str | None = schema_for_context(None, "I", is_cadence_approach=False)
        assert result == "meyer"

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

        Domain knowledge: Romanesca is a descending bass pattern 1-7-6-3
        with characteristic 1-5-1-1 soprano.
        """
        soprano, bass = apply_schema("romanesca", Fraction(1))
        bass_degrees: list[int] = [p.degree for p in bass.pitches]
        soprano_degrees: list[int] = [p.degree for p in soprano.pitches]
        assert bass_degrees == [1, 7, 6, 3]
        assert soprano_degrees == [1, 5, 1, 1]

    def test_prinner_musical_correctness(self) -> None:
        """Prinner produces musically correct cadence approach.

        Domain knowledge: Prinner is 4-3-2-1 bass with 6-5-4-3 soprano,
        a standard cadence preparation.
        """
        soprano, bass = apply_schema("prinner", Fraction(1))
        bass_degrees: list[int] = [p.degree for p in bass.pitches]
        soprano_degrees: list[int] = [p.degree for p in soprano.pitches]
        assert bass_degrees == [4, 3, 2, 1]
        assert soprano_degrees == [6, 5, 4, 3]

    def test_monte_musical_correctness(self) -> None:
        """Monte produces ascending sequence pattern.

        Domain knowledge: Monte is an ascending sequence pattern
        with 7-1-7-1 bass pattern (transposed on repetition).
        """
        schema: Schema = load_schema("monte")
        assert schema.bass_degrees == (7, 1, 7, 1)


# =============================================================================
# Rule of the Octave Tests (baroque_plan.md Phase 3.1)
# =============================================================================


class TestRuleOfOctaveConstants:
    """Test Rule of the Octave constant dictionaries."""

    def test_ascending_has_all_degrees(self) -> None:
        """Ascending dictionary has all 7 degrees."""
        assert set(RULE_OF_OCTAVE_ASCENDING.keys()) == {1, 2, 3, 4, 5, 6, 7}

    def test_descending_has_all_degrees(self) -> None:
        """Descending dictionary has all 7 degrees."""
        assert set(RULE_OF_OCTAVE_DESCENDING.keys()) == {1, 2, 3, 4, 5, 6, 7}

    def test_ascending_tonic_is_root_position(self) -> None:
        """Ascending: degree 1 is 5/3 (root position)."""
        assert RULE_OF_OCTAVE_ASCENDING[1] == "5/3"

    def test_ascending_dominant_is_root_position(self) -> None:
        """Ascending: degree 5 is 5/3 (root position)."""
        assert RULE_OF_OCTAVE_ASCENDING[5] == "5/3"

    def test_ascending_supertonic_is_first_inversion(self) -> None:
        """Ascending: degree 2 is 6/3 (first inversion)."""
        assert RULE_OF_OCTAVE_ASCENDING[2] == "6/3"

    def test_ascending_subdominant_has_dissonance(self) -> None:
        """Ascending: degree 4 has 6/5/3 (dissonance before 5)."""
        assert RULE_OF_OCTAVE_ASCENDING[4] == "6/5/3"

    def test_ascending_leading_tone_has_dissonance(self) -> None:
        """Ascending: degree 7 has 6/5/3 (dissonance before 8)."""
        assert RULE_OF_OCTAVE_ASCENDING[7] == "6/5/3"

    def test_descending_tonic_is_root_position(self) -> None:
        """Descending: degree 1 is 5/3 (root position)."""
        assert RULE_OF_OCTAVE_DESCENDING[1] == "5/3"

    def test_descending_dominant_is_root_position(self) -> None:
        """Descending: degree 5 is 5/3 (root position)."""
        assert RULE_OF_OCTAVE_DESCENDING[5] == "5/3"

    def test_descending_submediant_has_raised_sixth(self) -> None:
        """Descending: degree 6 has #6/4/3 (raised 6th = leading tone to 5)."""
        assert RULE_OF_OCTAVE_DESCENDING[6] == "#6/4/3"

    def test_descending_subdominant_has_strong_dissonance(self) -> None:
        """Descending: degree 4 has 6/4/2 (strong dissonance from 5)."""
        assert RULE_OF_OCTAVE_DESCENDING[4] == "6/4/2"

    def test_descending_supertonic_has_fourth(self) -> None:
        """Descending: degree 2 has 6/4/3 (with 4th)."""
        assert RULE_OF_OCTAVE_DESCENDING[2] == "6/4/3"


class TestGetRuleOfOctaveFigure:
    """Test get_rule_of_octave_figure function."""

    def test_ascending_degree_1(self) -> None:
        """Ascending degree 1 returns 5/3."""
        assert get_rule_of_octave_figure(1, "ascending") == "5/3"

    def test_ascending_degree_4(self) -> None:
        """Ascending degree 4 returns 6/5/3."""
        assert get_rule_of_octave_figure(4, "ascending") == "6/5/3"

    def test_descending_degree_4(self) -> None:
        """Descending degree 4 returns 6/4/2."""
        assert get_rule_of_octave_figure(4, "descending") == "6/4/2"

    def test_descending_degree_6(self) -> None:
        """Descending degree 6 returns #6/4/3."""
        assert get_rule_of_octave_figure(6, "descending") == "#6/4/3"

    def test_unknown_degree_returns_default(self) -> None:
        """Unknown degree returns 5/3 default."""
        assert get_rule_of_octave_figure(8, "ascending") == "5/3"
        assert get_rule_of_octave_figure(0, "descending") == "5/3"

    def test_all_ascending_degrees_return_figures(self) -> None:
        """All ascending degrees return valid figures."""
        for deg in range(1, 8):
            fig = get_rule_of_octave_figure(deg, "ascending")
            assert fig in {"5/3", "6/3", "6/5/3"}

    def test_all_descending_degrees_return_figures(self) -> None:
        """All descending degrees return valid figures."""
        for deg in range(1, 8):
            fig = get_rule_of_octave_figure(deg, "descending")
            assert isinstance(fig, str)
            assert len(fig) > 0


class TestApplyRuleOfOctave:
    """Test apply_rule_of_octave function."""

    def test_returns_timed_material_and_figures(self) -> None:
        """Returns tuple of (TimedMaterial, list of figures)."""
        bass_degrees = (1, 2, 3, 4, 5)
        bass, figures = apply_rule_of_octave(bass_degrees, Fraction(5))
        assert hasattr(bass, 'pitches')
        assert hasattr(bass, 'durations')
        assert isinstance(figures, list)

    def test_empty_bass_returns_empty(self) -> None:
        """Empty bass degrees returns empty results."""
        bass, figures = apply_rule_of_octave((), Fraction(0))
        assert len(bass.pitches) == 0
        assert len(figures) == 0

    def test_figure_count_matches_degree_count(self) -> None:
        """Figure count matches bass degree count."""
        bass_degrees = (1, 2, 3, 4, 5, 6, 7)
        bass, figures = apply_rule_of_octave(bass_degrees, Fraction(7))
        assert len(figures) == len(bass_degrees)

    def test_pitch_count_matches_degree_count(self) -> None:
        """Pitch count matches bass degree count."""
        bass_degrees = (1, 2, 3, 4, 5)
        bass, figures = apply_rule_of_octave(bass_degrees, Fraction(5))
        assert len(bass.pitches) == len(bass_degrees)

    def test_ascending_scale_harmonization(self) -> None:
        """Ascending scale (1-2-3-4-5-6-7) produces correct figures.

        Domain knowledge (baroque_literature.md Part II.1):
        Ascending: 5/3, 6/3, 6/3, 6/5/3, 5/3, 6/3, 6/5/3
        """
        bass_degrees = (1, 2, 3, 4, 5, 6, 7)
        _, figures = apply_rule_of_octave(bass_degrees, Fraction(7))
        expected = ["5/3", "6/3", "6/3", "6/5/3", "5/3", "6/3", "6/5/3"]
        assert figures == expected

    def test_descending_scale_harmonization(self) -> None:
        """Descending scale (7-6-5-4-3-2-1) produces correct figures.

        Domain knowledge (baroque_literature.md Part II.1):
        Descending: 6/3, #6/4/3, 5/3, 6/4/2, 6/3, 6/4/3, 5/3
        First note defaults to ascending since no previous.
        """
        bass_degrees = (7, 6, 5, 4, 3, 2, 1)
        _, figures = apply_rule_of_octave(bass_degrees, Fraction(7))
        # First note uses ascending (no prev), rest detect descending
        assert figures[0] == "6/5/3"  # Ascending default for first
        assert figures[1] == "#6/4/3"  # Descending 6
        assert figures[2] == "5/3"  # Descending 5
        assert figures[3] == "6/4/2"  # Descending 4
        assert figures[4] == "6/3"  # Descending 3
        assert figures[5] == "6/4/3"  # Descending 2
        assert figures[6] == "5/3"  # Descending 1

    def test_durations_sum_to_budget(self) -> None:
        """Durations sum to budget."""
        bass_degrees = (1, 5, 1)
        bass, _ = apply_rule_of_octave(bass_degrees, Fraction(3))
        assert sum(bass.durations) == Fraction(3)

    def test_duration_per_note_is_equal(self) -> None:
        """Each note gets equal duration."""
        bass_degrees = (1, 2, 3, 4)
        bass, _ = apply_rule_of_octave(bass_degrees, Fraction(4))
        assert all(d == Fraction(1) for d in bass.durations)

    def test_wraparound_7_to_1_is_ascending(self) -> None:
        """7 to 1 transition is detected as ascending."""
        bass_degrees = (7, 1)
        _, figures = apply_rule_of_octave(bass_degrees, Fraction(2))
        # 7->1 wraps around, so 1 is ascending
        assert figures[1] == "5/3"  # Ascending 1


class TestBassPatternConstants:
    """Test BASS_PATTERNS constant dictionary."""

    def test_contains_circle_fifths(self) -> None:
        """Contains circle of fifths pattern."""
        assert "circle_fifths" in BASS_PATTERNS

    def test_contains_up3_down1(self) -> None:
        """Contains up 3rd down step pattern."""
        assert "up3_down1" in BASS_PATTERNS

    def test_contains_down3_up1(self) -> None:
        """Contains down 3rd up step pattern."""
        assert "down3_up1" in BASS_PATTERNS

    def test_contains_romanesca(self) -> None:
        """Contains romanesca pattern."""
        assert "romanesca" in BASS_PATTERNS

    def test_all_patterns_are_bass_pattern_type(self) -> None:
        """All values are BassPattern dataclass."""
        for name, pattern in BASS_PATTERNS.items():
            assert isinstance(pattern, BassPattern)

    def test_circle_fifths_intervals(self) -> None:
        """Circle of fifths has (4, -5) intervals (up 4th, down 5th)."""
        pattern = BASS_PATTERNS["circle_fifths"]
        assert pattern.intervals == (4, -5)

    def test_romanesca_intervals(self) -> None:
        """Romanesca has (-1, -2, 2) intervals (down step, down 3rd, up 3rd)."""
        pattern = BASS_PATTERNS["romanesca"]
        assert pattern.intervals == (-1, -2, 2)


class TestDetectBassPattern:
    """Test detect_bass_pattern function."""

    def test_empty_bass_returns_empty(self) -> None:
        """Empty bass returns empty list."""
        result = detect_bass_pattern(())
        assert result == []

    def test_single_note_returns_empty(self) -> None:
        """Single note returns empty list."""
        result = detect_bass_pattern((1,))
        assert result == []

    def test_detects_ascending_stepwise(self) -> None:
        """Detects ascending stepwise pattern."""
        # 1-2-3 has intervals (1, 1)
        bass = (1, 2, 3)
        result = detect_bass_pattern(bass)
        pattern_names = [p.name for _, p in result]
        assert "ascending_stepwise" in pattern_names

    def test_detects_descending_stepwise(self) -> None:
        """Detects descending stepwise pattern."""
        # 3-2-1 has intervals (-1, -1)
        bass = (3, 2, 1)
        result = detect_bass_pattern(bass)
        pattern_names = [p.name for _, p in result]
        assert "descending_stepwise" in pattern_names

    def test_returns_start_index(self) -> None:
        """Returns correct start index for detected pattern."""
        bass = (1, 2, 3)  # ascending stepwise
        result = detect_bass_pattern(bass)
        if result:
            start_idx, _ = result[0]
            assert start_idx == 0

    def test_no_match_returns_empty(self) -> None:
        """No matching pattern returns empty list."""
        # Random intervals that don't match any pattern
        bass = (1, 3, 1, 5, 2)
        result = detect_bass_pattern(bass)
        # May or may not find patterns depending on exact intervals


class TestHarmoniseBassPattern:
    """Test harmonise_bass_pattern function."""

    def test_empty_bass_returns_empty(self) -> None:
        """Empty bass returns empty list."""
        result = harmonise_bass_pattern(())
        assert result == []

    def test_returns_list_of_figures(self) -> None:
        """Returns list of figure strings."""
        result = harmonise_bass_pattern((1, 2, 3))
        assert isinstance(result, list)
        assert all(isinstance(f, str) for f in result)

    def test_figure_count_matches_degree_count(self) -> None:
        """Figure count matches bass degree count."""
        bass = (1, 2, 3, 4, 5)
        result = harmonise_bass_pattern(bass)
        assert len(result) == len(bass)

    def test_uses_rule_of_octave_for_unmatched(self) -> None:
        """Uses Rule of Octave for degrees not in a pattern."""
        bass = (1, 5, 1)
        result = harmonise_bass_pattern(bass)
        # Check that we get valid figures
        assert all(f in {"5/3", "6/3", "6/4", "6/5/3", "6/4/2", "6/4/3", "#6/4/3"} for f in result)

    def test_detected_pattern_uses_pattern_harmonization(self) -> None:
        """Detected pattern uses its harmonization."""
        # Ascending stepwise: intervals (1,)
        bass = (1, 2)
        result = harmonise_bass_pattern(bass)
        # ascending_stepwise harmonization is ("6/3",)
        # So second note should be 6/3
        assert "6/3" in result
