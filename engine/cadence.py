"""Cadence formulas for phrase endings."""
from fractions import Fraction
from pathlib import Path

import yaml

from shared.pitch import FloatingNote, Pitch, wrap_degree
from shared.timed_material import TimedMaterial
from shared.voice_role import VoiceRole, get_roles_for_voice_count

DATA_DIR = Path(__file__).parent.parent / "data"

# Roman numeral to degree offset (I=0, V=+4, IV=-1, etc.)
TONAL_OFFSET: dict[str, int] = {
    "I": 0,
    "V": 4,
    "IV": -1,
    "vi": 5,
    "ii": 1,
    "iii": 2,
}

def load_cadences() -> dict:
    """Load all cadence formulas from YAML."""
    with open(DATA_DIR / "cadences.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _is_internal_cadence(formula: dict) -> bool:
    """Check if formula is internal (has top/bottom) vs final (has approach/resolution)."""
    return "top" in formula and "approach" not in formula


def get_internal_cadence_formulas() -> dict[str, tuple[tuple[Pitch, ...], tuple[Pitch, ...]]]:
    """Get internal cadence formulas as (top_degrees, bottom_degrees)."""
    cadences: dict = load_cadences()
    formulas: dict[str, tuple[tuple[Pitch, ...], tuple[Pitch, ...]]] = {}
    for name, formula in cadences.items():
        if not _is_internal_cadence(formula):
            continue
        top: tuple[Pitch, ...] = tuple(FloatingNote(d) for d in formula["top"])
        bottom: tuple[Pitch, ...] = tuple(FloatingNote(d) for d in formula["bottom"])
        formulas[name] = (top, bottom)
    return formulas


def get_internal_cadence_all_voices() -> dict[str, dict[str, tuple[Pitch, ...]]]:
    """Get internal cadence formulas with all voices by role (top, inner_1, inner_2, bottom)."""
    cadences: dict = load_cadences()
    formulas: dict[str, dict[str, tuple[Pitch, ...]]] = {}
    for name, formula in cadences.items():
        if not _is_internal_cadence(formula):
            continue
        voices: dict[str, tuple[Pitch, ...]] = {}
        for role in ["top", "inner_1", "inner_2", "bottom"]:
            if role in formula:
                voices[role] = tuple(FloatingNote(d) for d in formula[role])
        formulas[name] = voices
    return formulas


CADENCE_FORMULAS: dict[str, tuple[tuple[Pitch, ...], tuple[Pitch, ...]]] = get_internal_cadence_formulas()
CADENCE_FORMULAS_FULL: dict[str, dict[str, tuple[Pitch, ...]]] = get_internal_cadence_all_voices()


def offset_pitch(pitch: Pitch, offset: int) -> Pitch:
    """Offset a pitch by scale degrees."""
    assert isinstance(pitch, FloatingNote)
    return FloatingNote(wrap_degree(pitch.degree + offset))


def get_cadence_material(
    cadence_type: str,
    budget: Fraction,
    tonal_target: str = "I",
) -> tuple[TimedMaterial, TimedMaterial]:
    """Get top and bottom voice material for cadence, offset by tonal target."""
    if cadence_type not in CADENCE_FORMULAS:
        raise ValueError(f"Unknown cadence type: {cadence_type}")
    offset: int = TONAL_OFFSET.get(tonal_target, 0)
    top_base, bottom_base = CADENCE_FORMULAS[cadence_type]
    top_pitches: tuple[Pitch, ...] = tuple(offset_pitch(p, offset) for p in top_base)
    bottom_pitches: tuple[Pitch, ...] = tuple(offset_pitch(p, offset) for p in bottom_base)
    note_dur: Fraction = budget / 2
    durations: tuple[Fraction, ...] = (note_dur, note_dur)
    top: TimedMaterial = TimedMaterial(top_pitches, durations, budget)
    bottom: TimedMaterial = TimedMaterial(bottom_pitches, durations, budget)
    return (top, bottom)


def get_cadence_material_full(
    cadence_type: str,
    budget: Fraction,
    tonal_target: str = "I",
    voice_count: int = 4,
) -> dict[str, TimedMaterial]:
    """Get material for all voices in a cadence.

    Returns dict with keys by VoiceRole value: 'top', 'inner_1', 'inner_2', 'bottom'.
    Only includes roles applicable for the voice_count.
    """
    if cadence_type not in CADENCE_FORMULAS_FULL:
        raise ValueError(f"Unknown cadence type: {cadence_type}")
    offset: int = TONAL_OFFSET.get(tonal_target, 0)
    formula: dict[str, tuple[Pitch, ...]] = CADENCE_FORMULAS_FULL[cadence_type]
    note_dur: Fraction = budget / 2
    durations: tuple[Fraction, ...] = (note_dur, note_dur)
    result: dict[str, TimedMaterial] = {}
    # Get applicable roles for this voice count
    roles = get_roles_for_voice_count(voice_count)
    for role in roles:
        role_key = role.value  # "top", "inner_1", etc.
        if role_key in formula:
            pitches: tuple[Pitch, ...] = tuple(offset_pitch(p, offset) for p in formula[role_key])
            result[role_key] = TimedMaterial(pitches, durations, budget)
    return result


def load_final_cadences() -> dict:
    """Load final cadence formulas from YAML (those with approach/resolution)."""
    cadences: dict = load_cadences()
    return {name: formula for name, formula in cadences.items() if "approach" in formula}


def parse_fraction(s: str) -> Fraction:
    """Parse fraction string like '1/2' or '3/4'."""
    if "/" in s:
        num, den = s.split("/")
        return Fraction(int(num), int(den))
    return Fraction(int(s))


def apply_final_cadence(
    top_pitches: tuple[Pitch, ...],
    top_durations: tuple[Fraction, ...],
    bottom_pitches: tuple[Pitch, ...],
    bottom_durations: tuple[Fraction, ...],
    bar_dur: Fraction,
    phrase_budget: Fraction,
    tonal_target: str = "I",
    cadence_type: str = "decorated",
) -> tuple[tuple[Pitch, ...], tuple[Fraction, ...], tuple[Pitch, ...], tuple[Fraction, ...]]:
    """Replace final bars with cadential approach + resolution.

    Takes completed phrase material, drops bars to make room for cadence,
    then appends approach + resolution from final_cadences.yaml.

    Returns (top_pitches, top_durations, bottom_pitches, bottom_durations).
    """
    cadences: dict = load_final_cadences()
    if cadence_type not in cadences:
        raise ValueError(f"Unknown final cadence type: {cadence_type}")
    formula: dict = cadences[cadence_type]
    approach_dur: Fraction = sum(parse_fraction(d) for d in formula["approach"]["durations"]) * bar_dur
    resolution_dur: Fraction = sum(parse_fraction(d) for d in formula["resolution"]["durations"]) * bar_dur
    cadence_total: Fraction = approach_dur + resolution_dur
    offset: int = TONAL_OFFSET.get(tonal_target, 0)
    top_dur_total: Fraction = sum(top_durations)
    bottom_dur_total: Fraction = sum(bottom_durations)
    top_cut: Fraction = phrase_budget - cadence_total
    bottom_cut: Fraction = phrase_budget - cadence_total
    assert top_cut >= 0, f"Cadence {cadence_total} exceeds phrase budget {phrase_budget}"
    new_top_pitches: list[Pitch] = []
    new_top_durations: list[Fraction] = []
    accumulated: Fraction = Fraction(0)
    for p, d in zip(top_pitches, top_durations):
        if accumulated >= top_cut:
            break
        if accumulated + d > top_cut:
            new_top_durations.append(top_cut - accumulated)
            new_top_pitches.append(p)
            break
        new_top_pitches.append(p)
        new_top_durations.append(d)
        accumulated += d
    new_bottom_pitches: list[Pitch] = []
    new_bottom_durations: list[Fraction] = []
    accumulated = Fraction(0)
    for p, d in zip(bottom_pitches, bottom_durations):
        if accumulated >= bottom_cut:
            break
        if accumulated + d > bottom_cut:
            new_bottom_durations.append(bottom_cut - accumulated)
            new_bottom_pitches.append(p)
            break
        new_bottom_pitches.append(p)
        new_bottom_durations.append(d)
        accumulated += d
    approach: dict = formula["approach"]
    for deg, dur_str in zip(approach["top"], approach["durations"]):
        new_top_pitches.append(FloatingNote(wrap_degree(deg + offset)))
        new_top_durations.append(parse_fraction(dur_str) * bar_dur)
    for deg, dur_str in zip(approach["bottom"], approach["durations"]):
        new_bottom_pitches.append(FloatingNote(wrap_degree(deg + offset)))
        new_bottom_durations.append(parse_fraction(dur_str) * bar_dur)
    resolution: dict = formula["resolution"]
    for deg, dur_str in zip(resolution["top"], resolution["durations"]):
        new_top_pitches.append(FloatingNote(wrap_degree(deg + offset)))
        new_top_durations.append(parse_fraction(dur_str) * bar_dur)
    for deg, dur_str in zip(resolution["bottom"], resolution["durations"]):
        new_bottom_pitches.append(FloatingNote(wrap_degree(deg + offset)))
        new_bottom_durations.append(parse_fraction(dur_str) * bar_dur)
    result_top_dur: Fraction = sum(new_top_durations, Fraction(0))
    result_bottom_dur: Fraction = sum(new_bottom_durations, Fraction(0))
    assert result_top_dur == phrase_budget, (
        f"Top voice duration {result_top_dur} != phrase budget {phrase_budget}")
    assert result_bottom_dur == phrase_budget, (
        f"Bottom voice duration {result_bottom_dur} != phrase budget {phrase_budget}")
    return (
        tuple(new_top_pitches),
        tuple(new_top_durations),
        tuple(new_bottom_pitches),
        tuple(new_bottom_durations),
    )
