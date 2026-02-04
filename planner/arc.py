"""Arc planner: tension curve management across piece."""
from pathlib import Path

import yaml

from planner.plannertypes import Brief, MacroForm, TensionCurve, TensionPoint

DATA_DIR = Path(__file__).parent.parent / "data"
TENSION_TO_ENERGY: dict[str, str] = {
    "low": "low",
    "moderate": "moderate",
    "high": "rising",
    "peak": "peak",
    "falling": "falling",
}


def load_yaml(name: str) -> dict:
    """Load YAML file from data directory."""
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def select_tension_curve(brief: Brief) -> str:
    """Select tension curve template based on affect."""
    affect_to_curve: dict[str, str] = {
        "maestoso": "arch",
        "giocoso": "cumulative",
        "dolore": "dramatic",
        "grazioso": "calm",
        "furioso": "episodic",
    }
    return affect_to_curve.get(brief.affect, "arch")


def build_tension_curve(brief: Brief, macro_form: MacroForm | None = None) -> TensionCurve:
    """Build tension curve from template."""
    curves: dict = load_yaml(name="rhetoric/tension_curves.yaml")
    curve_name: str = select_tension_curve(brief=brief)
    assert curve_name in curves, f"Unknown tension curve: {curve_name}"
    curve_def: dict = curves[curve_name]
    raw_points: list[list[float]] = curve_def["points"]
    points: list[TensionPoint] = []
    max_level: float = 0.0
    max_position: float = 0.5
    for pos, level in raw_points:
        points.append(TensionPoint(position=pos, level=level))
        if level > max_level:
            max_level = level
            max_position = pos
    return TensionCurve(
        points=tuple(points),
        climax_position=max_position,
        climax_level=max_level,
    )


def get_tension_at_position(curve: TensionCurve, position: float) -> float:
    """Interpolate tension level at given position."""
    if position <= 0.0:
        return curve.points[0].level
    if position >= 1.0:
        return curve.points[-1].level
    prev: TensionPoint = curve.points[0]
    for point in curve.points[1:]:
        if point.position >= position:
            ratio: float = (position - prev.position) / (point.position - prev.position)
            return prev.level + ratio * (point.level - prev.level)
        prev = point
    return curve.points[-1].level


def tension_to_energy(level: float) -> str:
    """Convert tension level to energy name."""
    if level < 0.25:
        return "low"
    if level < 0.45:
        return "moderate"
    if level < 0.7:
        return "rising"
    if level < 0.85:
        return "peak"
    return "peak"


def get_energy_for_bar(curve: TensionCurve, bar: int, total_bars: int) -> str:
    """Get energy level for a specific bar."""
    position: float = bar / total_bars if total_bars > 0 else 0.0
    level: float = get_tension_at_position(curve=curve, position=position)
    return tension_to_energy(level=level)
