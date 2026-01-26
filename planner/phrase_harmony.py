"""Phrase harmony generator: bar-level chord progression for phrases."""
from pathlib import Path

import yaml

DATA_DIR = Path(__file__).parent.parent / "data"

# Pre-progression patterns to reach common targets (circle of fifths based)
# Each key is the target chord, value is a list of chords leading to it
PROGRESSIONS_TO: dict[str, list[str]] = {
    "I": ["IV", "ii", "vi", "I"],
    "V": ["I", "ii", "IV", "V"],
    "IV": ["I", "vi", "ii", "IV"],
    "vi": ["I", "IV", "ii", "vi"],
    "ii": ["I", "vi", "IV", "ii"],
    "iii": ["I", "vi", "ii", "iii"],
    "III": ["I", "VI", "II", "III"],  # for minor
}


def _load_cadence_formulas() -> dict[str, list[str]]:
    """Load cadence Roman numeral formulas from cadences.yaml."""
    path = DATA_DIR / "cadences" / "cadences.yaml"
    assert path.exists(), f"Missing cadences.yaml at {path}"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "cadences.yaml must be a dict"
    assert "roman_numerals" in data, "cadences.yaml must have 'roman_numerals' section"
    return data["roman_numerals"]


def _get_lead_in(bars_needed: int, target: str, prev_end: str) -> list[str]:
    """Generate lead-in progression to reach target chord."""
    if bars_needed <= 0:
        return []
    progression = PROGRESSIONS_TO.get(target, [prev_end, target])
    if bars_needed == 1:
        return [progression[-2] if len(progression) >= 2 else prev_end]
    result: list[str] = []
    idx = 0
    while len(result) < bars_needed:
        result.append(progression[idx % len(progression)])
        idx += 1
    return result[:bars_needed]


def generate_phrase_harmony(
    bars: int,
    tonal_target: str,
    cadence: str | None,
    prev_end: str = "I",
) -> tuple[str, ...]:
    """Generate bar-level harmony for a phrase.

    Args:
        bars: Number of bars in the phrase
        tonal_target: Target chord (Roman numeral) for phrase end
        cadence: Cadence type (authentic, half, etc.) or None
        prev_end: Final chord of previous phrase

    Returns:
        Tuple of Roman numerals, one per bar
    """
    assert bars > 0, f"bars must be positive: {bars}"
    formulas = _load_cadence_formulas()
    cadence_key = cadence if cadence else "null"
    assert cadence_key in formulas, f"Unknown cadence type: {cadence_key}"
    cadence_chords: list[str] = formulas[cadence_key]
    if not cadence_chords:
        return tuple([tonal_target] * bars)
    cadence_len = len(cadence_chords)
    if cadence_len >= bars:
        return tuple(cadence_chords[-bars:])
    lead_in_bars = bars - cadence_len
    first_cadence_chord = cadence_chords[0]
    lead_in = _get_lead_in(lead_in_bars, first_cadence_chord, prev_end)
    return tuple(lead_in + cadence_chords)
