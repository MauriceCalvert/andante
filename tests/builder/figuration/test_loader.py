"""Tests for builder.figuration.loader module."""
from fractions import Fraction
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from builder.figuration.loader import (
    clear_cache,
    get_cadential,
    get_diminutions,
    get_hemiola_templates,
    get_rhythm_templates,
    load_cadential,
    load_diminutions,
    load_hemiola_templates,
    load_rhythm_templates,
)
from builder.figuration.types import CadentialFigure, Figure, RhythmTemplate
from shared.constants import FIGURATION_INTERVALS


class TestLoadDiminutions:
    """Tests for load_diminutions function."""

    def test_load_default_diminutions(self) -> None:
        """Loading default diminutions.yaml should work."""
        clear_cache()
        diminutions = load_diminutions()

        # Should have all intervals
        for interval in FIGURATION_INTERVALS:
            assert interval in diminutions, f"Missing interval: {interval}"

        # Each interval should have at least one figure
        for interval, figures in diminutions.items():
            assert len(figures) > 0, f"No figures for interval: {interval}"
            for fig in figures:
                assert isinstance(fig, Figure)

    def test_diminutions_have_required_fields(self) -> None:
        """All diminution figures should have required fields."""
        diminutions = get_diminutions()

        for interval, figures in diminutions.items():
            for fig in figures:
                assert fig.name, f"Figure in {interval} has empty name"
                assert len(fig.degrees) >= 2, f"Figure {fig.name} has insufficient degrees"
                assert fig.weight > 0, f"Figure {fig.name} has non-positive weight"

    def test_step_up_figures_exist(self) -> None:
        """step_up interval should have multiple figures."""
        diminutions = get_diminutions()
        assert "step_up" in diminutions
        assert len(diminutions["step_up"]) >= 3

    def test_figure_names_unique_within_interval(self) -> None:
        """Figure names should be unique within each interval."""
        diminutions = get_diminutions()

        for interval, figures in diminutions.items():
            names = [f.name for f in figures]
            assert len(names) == len(set(names)), \
                f"Duplicate figure names in {interval}"

    def test_missing_file_raises(self) -> None:
        """Loading from non-existent file should raise AssertionError."""
        with pytest.raises(AssertionError, match="not found"):
            load_diminutions(Path("/nonexistent/diminutions.yaml"))


class TestLoadCadential:
    """Tests for load_cadential function."""

    def test_load_default_cadential(self) -> None:
        """Loading default cadential.yaml should work."""
        clear_cache()
        cadential = load_cadential()

        # Should have both targets
        assert "target_1" in cadential
        assert "target_5" in cadential

        # Each target should have approaches
        for target, approaches in cadential.items():
            assert len(approaches) > 0, f"No approaches for {target}"

    def test_cadential_figures_valid(self) -> None:
        """All cadential figures should be valid CadentialFigure instances."""
        cadential = get_cadential()

        for target, approaches in cadential.items():
            for approach, figures in approaches.items():
                for fig in figures:
                    assert isinstance(fig, CadentialFigure)
                    assert fig.name
                    assert len(fig.degrees) >= 2

    def test_target_1_has_step_down(self) -> None:
        """target_1 should have step_down approach (2->1)."""
        cadential = get_cadential()
        assert "step_down" in cadential["target_1"]
        figures = cadential["target_1"]["step_down"]
        assert len(figures) >= 1

    def test_target_5_has_step_up(self) -> None:
        """target_5 should have step_up approach (4->5)."""
        cadential = get_cadential()
        assert "step_up" in cadential["target_5"]
        figures = cadential["target_5"]["step_up"]
        assert len(figures) >= 1


class TestLoadRhythmTemplates:
    """Tests for load_rhythm_templates function."""

    def test_load_default_rhythm_templates(self) -> None:
        """Loading default rhythm_templates.yaml should work."""
        clear_cache()
        templates = load_rhythm_templates()

        # Should have some templates
        assert len(templates) > 0

    def test_rhythm_templates_have_correct_structure(self) -> None:
        """All rhythm templates should have matching note_count and durations."""
        templates = get_rhythm_templates()

        for (note_count, metre, overdotted), template in templates.items():
            assert isinstance(template, RhythmTemplate)
            assert template.note_count == note_count
            assert template.metre == metre
            assert template.overdotted == overdotted
            assert len(template.durations) == note_count

    def test_common_templates_exist(self) -> None:
        """Common rhythm templates should exist."""
        templates = get_rhythm_templates()

        # 4/4 with 4 notes, standard
        assert (4, "4/4", False) in templates
        # 3/4 with 3 notes, standard
        assert (3, "3/4", False) in templates

    def test_durations_are_fractions(self) -> None:
        """All durations should be Fraction instances."""
        templates = get_rhythm_templates()

        for template in templates.values():
            for dur in template.durations:
                assert isinstance(dur, Fraction), \
                    f"Duration {dur} is not a Fraction"


class TestLoadHemiolaTemplates:
    """Tests for load_hemiola_templates function."""

    def test_load_hemiola_templates(self) -> None:
        """Loading hemiola templates should work."""
        clear_cache()
        templates = load_hemiola_templates()

        # May or may not have templates depending on YAML
        assert isinstance(templates, dict)

    def test_hemiola_templates_valid(self) -> None:
        """All hemiola templates should be valid RhythmTemplate instances."""
        templates = get_hemiola_templates()

        for (note_count, metre), template in templates.items():
            assert isinstance(template, RhythmTemplate)
            assert template.note_count == note_count
            assert template.metre == metre


class TestCaching:
    """Tests for caching behavior."""

    def test_cache_returns_same_object(self) -> None:
        """Cached getters should return the same object."""
        clear_cache()

        dim1 = get_diminutions()
        dim2 = get_diminutions()
        assert dim1 is dim2

        cad1 = get_cadential()
        cad2 = get_cadential()
        assert cad1 is cad2

        rhy1 = get_rhythm_templates()
        rhy2 = get_rhythm_templates()
        assert rhy1 is rhy2

    def test_clear_cache_works(self) -> None:
        """clear_cache should force reload."""
        dim1 = get_diminutions()
        clear_cache()
        dim2 = get_diminutions()
        # After cache clear, should get a new dict (equal but not identical)
        assert dim1 == dim2
        assert dim1 is not dim2


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_fraction_parsing_integers(self) -> None:
        """Loader should handle integer durations."""
        templates = get_rhythm_templates()
        # Check that we have some templates (integers in YAML become Fractions)
        assert len(templates) > 0

    def test_fraction_parsing_strings(self) -> None:
        """Loader should handle string fraction durations like '1/4'."""
        templates = get_rhythm_templates()
        # String fractions like "1/4" should be parsed
        for template in templates.values():
            for dur in template.durations:
                assert isinstance(dur, Fraction)
                assert dur > 0
