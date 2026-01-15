"""Macro-form planner: Brief + Frame -> MacroForm for extended pieces."""
from pathlib import Path

import yaml

from planner.plannertypes import Brief, Frame, MacroForm, MacroSection

DATA_DIR = Path(__file__).parent.parent / "data"


def load_yaml(name: str) -> dict:
    """Load YAML file from data directory."""
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def select_macro_arc(brief: Brief, frame: Frame) -> str:
    """Select macro-arc template based on affect and mode."""
    arc_selection: dict = load_yaml("arc_selection.yaml")
    genre_arcs: dict | None = arc_selection.get(brief.genre)
    assert genre_arcs is not None, f"No arc selection for genre: {brief.genre}"
    arc: str | None = genre_arcs.get(brief.affect)
    assert arc is not None, f"No arc for affect {brief.affect} in genre {brief.genre}"
    return arc


def estimate_transition_bars(arc_sections: list[dict]) -> int:
    """Estimate bars needed for transitions between sections."""
    transitions: int = 0
    for i in range(1, len(arc_sections)):
        prev: dict = arc_sections[i - 1]
        curr: dict = arc_sections[i]
        if prev["key_area"] != curr["key_area"] or prev["character"] != curr["character"]:
            transitions += 2
    return transitions


def scale_section_bars(
    arc_sections: list[dict], template_total: int, target_bars: int
) -> list[int]:
    """Scale section bars proportionally to target, reserving space for transitions."""
    transition_reserve: int = estimate_transition_bars(arc_sections)
    available_bars: int = target_bars - transition_reserve
    scale: float = available_bars / template_total
    scaled: list[int] = []
    for sec in arc_sections:
        raw: float = sec["bars"] * scale
        bars: int = max(4, round(raw / 4) * 4)
        scaled.append(bars)
    total: int = sum(scaled)
    if total != available_bars:
        diff: int = available_bars - total
        largest_idx: int = max(range(len(scaled)), key=lambda i: scaled[i])
        scaled[largest_idx] = max(4, scaled[largest_idx] + diff)
    return scaled


def build_macro_form(brief: Brief, frame: Frame) -> MacroForm:
    """Build MacroForm from arc template, scaling to brief.bars."""
    arc_name: str = select_macro_arc(brief, frame)
    arcs: dict = load_yaml("fantasia_arcs.yaml")
    assert arc_name in arcs, f"Unknown fantasia arc: {arc_name}"
    arc_def: dict = arcs[arc_name]
    template_total: int = arc_def["total_bars"]
    target_bars: int = brief.bars
    scaled_bars: list[int] = scale_section_bars(
        arc_def["sections"], template_total, target_bars
    )
    sections: list[MacroSection] = []
    for i, sec in enumerate(arc_def["sections"]):
        section: MacroSection = MacroSection(
            label=sec["label"],
            character=sec["character"],
            bars=scaled_bars[i],
            texture=sec["texture"],
            key_area=sec["key_area"],
            energy_arc=sec["energy_arc"],
        )
        sections.append(section)
    return MacroForm(
        sections=tuple(sections),
        climax_section=arc_def["climax_section"],
        total_bars=target_bars,
    )


def uses_macro_form(brief: Brief) -> bool:
    """Check if genre uses macro-form planning."""
    genre_data: dict = load_yaml(f"genres/{brief.genre}.yaml")
    return genre_data.get("uses_macro_form", False)
