"""Frame resolver: Brief -> Frame."""
from fractions import Fraction
from pathlib import Path

import yaml

from planner.plannertypes import Brief, Frame

DATA_DIR = Path(__file__).parent.parent / "data"


def load_yaml(name: str) -> dict:
    """Load YAML file from data directory."""
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_upbeat(value: int | str) -> Fraction:
    """Parse upbeat value from YAML (0, '1/4', '1/2')."""
    if isinstance(value, int):
        return Fraction(value)
    return Fraction(value)


def resolve_frame(brief: Brief) -> Frame:
    """Resolve Frame from Brief using data files."""
    affects_data: dict = load_yaml(name="rhetoric/affects.yaml")
    affects: dict = affects_data.get("affects", {})
    key_characters: dict = affects_data.get("key_characters", {})
    genre_data: dict = load_yaml(name=f"genres/{brief.genre}.yaml")
    assert brief.affect in affects, f"Unknown affect: {brief.affect}"
    affect_def: dict = affects[brief.affect]
    mode: str = affect_def["mode"]
    tempo: str = affect_def["tempo"]
    key_character: str = affect_def["key_character"]
    assert key_character in key_characters, f"Unknown key_character: {key_character}"
    candidates: list[str] = sorted(key_characters[key_character])
    key: str = candidates[0]
    metre: str = genre_data["metre"]
    voices: int = genre_data["voices"]
    upbeat: Fraction = parse_upbeat(value=genre_data.get("upbeat", 0))
    form: str = genre_data.get("form", "through_composed")
    return Frame(key=key, mode=mode, metre=metre, tempo=tempo, voices=voices, upbeat=upbeat, form=form)
