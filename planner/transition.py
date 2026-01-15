"""Transition planning between macro-sections."""
from pathlib import Path

import yaml

from planner.plannertypes import EpisodeSpec, MacroSection

DATA_DIR = Path(__file__).parent.parent / "data"
RELATED_KEYS: set[tuple[str, str]] = {
    ("I", "V"), ("V", "I"), ("I", "IV"), ("IV", "I"),
    ("I", "vi"), ("vi", "I"), ("i", "III"), ("III", "i"),
    ("i", "v"), ("v", "i"), ("i", "iv"), ("iv", "i"),
}


def load_yaml(name: str) -> dict:
    """Load YAML file from data directory."""
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def keys_are_related(from_key: str, to_key: str) -> bool:
    """Check if two key areas are closely related."""
    if from_key == to_key:
        return True
    return (from_key, to_key) in RELATED_KEYS


def select_transition_type(from_section: MacroSection, to_section: MacroSection) -> str:
    """Select appropriate transition type based on key and character."""
    transitions: dict = load_yaml("transitions.yaml")
    from_key: str = from_section.key_area
    to_key: str = to_section.key_area
    from_char: str = from_section.character
    to_char: str = to_section.character
    related: bool = keys_are_related(from_key, to_key)
    contrast: bool = from_char != to_char
    if from_key == to_key:
        return "linking"
    if to_char in ("triumphant", "climax"):
        return "cadential"
    if contrast and not related:
        return "dramatic"
    if not related:
        return "chromatic" if from_char == "turbulent" else "sequential"
    return "pivot"


def generate_transition(from_section: MacroSection, to_section: MacroSection) -> EpisodeSpec:
    """Generate transition episode between two macro-sections."""
    transitions: dict = load_yaml("transitions.yaml")
    transition_type: str = select_transition_type(from_section, to_section)
    trans_def: dict = transitions[transition_type]
    bars: int = trans_def["bars"]
    return EpisodeSpec(type=transition_type, bars=bars, is_transition=True)


def needs_transition(from_section: MacroSection, to_section: MacroSection) -> bool:
    """Determine if sections need a transition between them."""
    if from_section.key_area != to_section.key_area:
        return True
    if from_section.character != to_section.character:
        return True
    return False
