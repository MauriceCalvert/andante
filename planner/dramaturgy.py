"""Dramaturgy: Mattheson key-character mappings.

Maps affects to historically appropriate keys per Mattheson's
Der vollkommene Capellmeister (baroque_theory.md section 8.1).
"""
from typing import Dict, Tuple


# Mattheson Key Characteristics (baroque_theory.md section 8.1)
MATTHESON_KEYS: Dict[str, str] = {
    "C": "pure_innocent",
    "D": "sharp_martial",
    "E": "piercing_sorrowful",
    "F": "tender_calm",
    "G": "persuading_brilliant",
    "A": "affecting_radiant",
    "Bb": "magnificent",
    "Eb": "serious",
    "c": "sweet_sad",
    "d": "devout_grand",
    "e": "pensive_profound",
    "g": "serious_magnificent",
    "a": "tender_plaintive",
    "f": "obscure_plaintive",
    "b": "harsh_plaintive",
}

# Affect to Mattheson key mapping (baroque_theory.md section 8.1 Affektenlehre)
AFFECT_TO_KEYS: Dict[str, Tuple[str, ...]] = {
    # Major affects (German)
    "Freudigkeit": ("G", "A", "D"),
    "Majestaet": ("D", "Bb", "Eb"),
    "Zaertlichkeit": ("F", "C", "A"),
    "Verwunderung": ("A", "G", "E"),
    "Entschlossenheit": ("D", "G", "C"),
    # Minor affects (German)
    "Sehnsucht": ("e", "a", "d"),
    "Klage": ("a", "c", "g"),
    "Zorn": ("g", "d", "c"),
    "Dolore": ("a", "c", "e"),
    # English equivalents
    "joyful": ("G", "A", "D"),
    "majestic": ("D", "Bb", "Eb"),
    "tender": ("F", "C", "A"),
    "default": ("D", "G", "C"),
    "resolute": ("D", "G", "C"),
    "wondering": ("A", "G", "E"),
    "yearning": ("e", "a", "d"),
    "lamenting": ("a", "c", "g"),
    "angry": ("g", "d", "c"),
    "sorrowful": ("a", "c", "e"),
}

# Fallback by mode + character
KEY_SUGGESTIONS: Dict[str, Tuple[str, ...]] = {
    "bright_major": ("G", "A", "D"),
    "dark_major": ("Eb", "Bb", "E"),
    "bright_minor": ("e", "a", "d"),
    "dark_minor": ("c", "g", "f"),
}


def get_suggested_key(affect: str, preference: int = 0) -> str:
    """Get a suggested key for the affect per Mattheson's Affektenlehre."""
    if affect in AFFECT_TO_KEYS:
        suggestions: Tuple[str, ...] = AFFECT_TO_KEYS[affect]
        if preference < len(suggestions):
            return suggestions[preference]
        return suggestions[0]
    # Fall back to bright_major
    suggestions = KEY_SUGGESTIONS.get("bright_major", ("C",))
    if preference < len(suggestions):
        return suggestions[preference]
    return suggestions[0] if suggestions else "C"
