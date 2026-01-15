"""Tests for planner.arc.

Category B tests: Tension curve management across piece.
Tests import only:
- planner.arc (module under test)
- planner.types (shared types)
- stdlib

Note: Uses YAML data files for tension curve definitions.
"""
import pytest

from planner.arc import (
    TENSION_TO_ENERGY,
    build_tension_curve,
    get_energy_for_bar,
    get_tension_at_position,
    load_yaml,
    select_tension_curve,
    tension_to_energy,
)
from planner.plannertypes import Brief, MacroForm, TensionCurve, TensionPoint


def make_brief(affect: str = "maestoso") -> Brief:
    """Create Brief with specified affect."""
    return Brief(affect=affect, genre="fugue", forces="keyboard", bars=32)


class TestLoadYaml:
    """Test load_yaml function."""

    def test_loads_tension_curves(self) -> None:
        """Tension curves data loads successfully."""
        data: dict = load_yaml("tension_curves.yaml")
        assert "arch" in data
        assert "dramatic" in data
        assert "calm" in data

    def test_curve_has_points(self) -> None:
        """Each curve has points field."""
        data: dict = load_yaml("tension_curves.yaml")
        for name, curve in data.items():
            assert "points" in curve, f"Curve {name} missing 'points'"


class TestTensionToEnergyMapping:
    """Test TENSION_TO_ENERGY constant."""

    def test_has_expected_levels(self) -> None:
        """Mapping includes expected tension levels."""
        assert "low" in TENSION_TO_ENERGY
        assert "moderate" in TENSION_TO_ENERGY
        assert "high" in TENSION_TO_ENERGY
        assert "peak" in TENSION_TO_ENERGY
        assert "falling" in TENSION_TO_ENERGY


class TestSelectTensionCurve:
    """Test select_tension_curve function."""

    def test_maestoso_uses_arch(self) -> None:
        """Maestoso affect uses arch tension curve."""
        brief: Brief = make_brief("maestoso")
        result: str = select_tension_curve(brief)
        assert result == "arch"

    def test_giocoso_uses_cumulative(self) -> None:
        """Giocoso affect uses cumulative tension curve."""
        brief: Brief = make_brief("giocoso")
        result: str = select_tension_curve(brief)
        assert result == "cumulative"

    def test_dolore_uses_dramatic(self) -> None:
        """Dolore affect uses dramatic tension curve."""
        brief: Brief = make_brief("dolore")
        result: str = select_tension_curve(brief)
        assert result == "dramatic"

    def test_grazioso_uses_calm(self) -> None:
        """Grazioso affect uses calm tension curve."""
        brief: Brief = make_brief("grazioso")
        result: str = select_tension_curve(brief)
        assert result == "calm"

    def test_furioso_uses_episodic(self) -> None:
        """Furioso affect uses episodic tension curve."""
        brief: Brief = make_brief("furioso")
        result: str = select_tension_curve(brief)
        assert result == "episodic"

    def test_unknown_affect_defaults_to_arch(self) -> None:
        """Unknown affect defaults to arch."""
        brief: Brief = Brief(affect="unknown", genre="fugue", forces="keyboard", bars=32)
        result: str = select_tension_curve(brief)
        assert result == "arch"


class TestBuildTensionCurve:
    """Test build_tension_curve function."""

    def test_returns_tension_curve(self) -> None:
        """build_tension_curve returns TensionCurve object."""
        brief: Brief = make_brief("maestoso")
        result: TensionCurve = build_tension_curve(brief)
        assert isinstance(result, TensionCurve)

    def test_has_points(self) -> None:
        """TensionCurve has points tuple."""
        brief: Brief = make_brief("maestoso")
        result: TensionCurve = build_tension_curve(brief)
        assert len(result.points) > 0
        assert all(isinstance(p, TensionPoint) for p in result.points)

    def test_points_start_at_zero(self) -> None:
        """First point is at position 0.0."""
        brief: Brief = make_brief("maestoso")
        result: TensionCurve = build_tension_curve(brief)
        assert result.points[0].position == 0.0

    def test_points_end_at_one(self) -> None:
        """Last point is at position 1.0."""
        brief: Brief = make_brief("maestoso")
        result: TensionCurve = build_tension_curve(brief)
        assert result.points[-1].position == 1.0

    def test_climax_position_identified(self) -> None:
        """Climax position matches maximum tension point."""
        brief: Brief = make_brief("maestoso")
        result: TensionCurve = build_tension_curve(brief)
        max_level: float = max(p.level for p in result.points)
        assert result.climax_level == max_level
        # Climax position should be where max occurs
        assert any(p.position == result.climax_position and p.level == max_level for p in result.points)

    def test_dramatic_curve_shape(self) -> None:
        """Dramatic curve starts high (per YAML definition)."""
        brief: Brief = make_brief("dolore")  # Uses dramatic
        result: TensionCurve = build_tension_curve(brief)
        # Dramatic starts at 0.7 tension
        assert result.points[0].level >= 0.6


class TestGetTensionAtPosition:
    """Test get_tension_at_position function."""

    def test_at_start(self) -> None:
        """Position 0.0 returns first point's level."""
        points: tuple[TensionPoint, ...] = (
            TensionPoint(position=0.0, level=0.3),
            TensionPoint(position=1.0, level=0.5),
        )
        curve: TensionCurve = TensionCurve(points=points, climax_position=1.0, climax_level=0.5)
        result: float = get_tension_at_position(curve, 0.0)
        assert result == 0.3

    def test_at_end(self) -> None:
        """Position 1.0 returns last point's level."""
        points: tuple[TensionPoint, ...] = (
            TensionPoint(position=0.0, level=0.3),
            TensionPoint(position=1.0, level=0.5),
        )
        curve: TensionCurve = TensionCurve(points=points, climax_position=1.0, climax_level=0.5)
        result: float = get_tension_at_position(curve, 1.0)
        assert result == 0.5

    def test_interpolates_middle(self) -> None:
        """Position between points is linearly interpolated."""
        points: tuple[TensionPoint, ...] = (
            TensionPoint(position=0.0, level=0.0),
            TensionPoint(position=1.0, level=1.0),
        )
        curve: TensionCurve = TensionCurve(points=points, climax_position=1.0, climax_level=1.0)
        result: float = get_tension_at_position(curve, 0.5)
        assert result == 0.5

    def test_interpolates_complex(self) -> None:
        """Complex curve interpolates correctly."""
        points: tuple[TensionPoint, ...] = (
            TensionPoint(position=0.0, level=0.2),
            TensionPoint(position=0.5, level=0.8),
            TensionPoint(position=1.0, level=0.4),
        )
        curve: TensionCurve = TensionCurve(points=points, climax_position=0.5, climax_level=0.8)
        # At 0.25: midway between 0.2 and 0.8 = 0.5
        result: float = get_tension_at_position(curve, 0.25)
        assert result == pytest.approx(0.5, abs=0.01)

    def test_before_start_clamps(self) -> None:
        """Position < 0 returns first point's level."""
        points: tuple[TensionPoint, ...] = (
            TensionPoint(position=0.0, level=0.3),
            TensionPoint(position=1.0, level=0.5),
        )
        curve: TensionCurve = TensionCurve(points=points, climax_position=1.0, climax_level=0.5)
        result: float = get_tension_at_position(curve, -0.5)
        assert result == 0.3

    def test_after_end_clamps(self) -> None:
        """Position > 1 returns last point's level."""
        points: tuple[TensionPoint, ...] = (
            TensionPoint(position=0.0, level=0.3),
            TensionPoint(position=1.0, level=0.5),
        )
        curve: TensionCurve = TensionCurve(points=points, climax_position=1.0, climax_level=0.5)
        result: float = get_tension_at_position(curve, 1.5)
        assert result == 0.5


class TestTensionToEnergy:
    """Test tension_to_energy function."""

    def test_low_tension(self) -> None:
        """Low tension levels return 'low'."""
        assert tension_to_energy(0.1) == "low"
        assert tension_to_energy(0.2) == "low"

    def test_moderate_tension(self) -> None:
        """Moderate tension levels return 'moderate'."""
        assert tension_to_energy(0.3) == "moderate"
        assert tension_to_energy(0.4) == "moderate"

    def test_rising_tension(self) -> None:
        """Rising tension levels return 'rising'."""
        assert tension_to_energy(0.5) == "rising"
        assert tension_to_energy(0.6) == "rising"

    def test_peak_tension(self) -> None:
        """Peak tension levels return 'peak'."""
        assert tension_to_energy(0.75) == "peak"
        assert tension_to_energy(0.9) == "peak"


class TestGetEnergyForBar:
    """Test get_energy_for_bar function."""

    def test_first_bar(self) -> None:
        """First bar (0) returns energy at position 0."""
        points: tuple[TensionPoint, ...] = (
            TensionPoint(position=0.0, level=0.2),  # low
            TensionPoint(position=1.0, level=0.9),  # peak
        )
        curve: TensionCurve = TensionCurve(points=points, climax_position=1.0, climax_level=0.9)
        result: str = get_energy_for_bar(curve, 0, 32)
        assert result == "low"

    def test_last_bar(self) -> None:
        """Last bar returns energy at end of curve."""
        points: tuple[TensionPoint, ...] = (
            TensionPoint(position=0.0, level=0.2),
            TensionPoint(position=1.0, level=0.9),  # peak
        )
        curve: TensionCurve = TensionCurve(points=points, climax_position=1.0, climax_level=0.9)
        result: str = get_energy_for_bar(curve, 32, 32)
        assert result == "peak"

    def test_middle_bar(self) -> None:
        """Middle bar returns interpolated energy."""
        points: tuple[TensionPoint, ...] = (
            TensionPoint(position=0.0, level=0.2),
            TensionPoint(position=1.0, level=0.8),
        )
        curve: TensionCurve = TensionCurve(points=points, climax_position=1.0, climax_level=0.8)
        # Bar 16 of 32 = position 0.5 = tension 0.5 = "rising"
        result: str = get_energy_for_bar(curve, 16, 32)
        assert result == "rising"

    def test_zero_total_bars(self) -> None:
        """Zero total bars returns energy at position 0."""
        points: tuple[TensionPoint, ...] = (
            TensionPoint(position=0.0, level=0.2),
            TensionPoint(position=1.0, level=0.9),
        )
        curve: TensionCurve = TensionCurve(points=points, climax_position=1.0, climax_level=0.9)
        result: str = get_energy_for_bar(curve, 0, 0)
        assert result == "low"


class TestIntegration:
    """Integration tests for arc module."""

    def test_full_curve_workflow(self) -> None:
        """Complete workflow from Brief to energy levels."""
        brief: Brief = make_brief("maestoso")
        curve: TensionCurve = build_tension_curve(brief)
        # Get energy at various positions
        energies: list[str] = []
        for bar in range(0, 32, 8):
            energy: str = get_energy_for_bar(curve, bar, 32)
            energies.append(energy)
        # Should have variety across the piece
        assert len(set(energies)) >= 2  # At least 2 different energy levels
