"""Bass handlers - generate bass from phrase harmony."""
from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml

from builder.transform import Notes, notes_to_dicts
from builder.tree import Node, yaml_to_tree
from shared.constants import DIATONIC_DEFAULTS, TONAL_ROOTS

BUILDER_DATA_DIR: Path = Path(__file__).parent.parent / "data"


def _load_bass_patterns() -> dict[str, Any]:
    """Load bass patterns from YAML."""
    path: Path = BUILDER_DATA_DIR / "bass_patterns.yaml"
    assert path.exists(), f"Missing bass_patterns.yaml at {path}"
    with open(path, encoding="utf-8") as f:
        data: Any = yaml.safe_load(f)
    assert data is not None, "bass_patterns.yaml is empty"
    return data


BASS_PATTERNS: dict[str, Any] = _load_bass_patterns()


def generate_bass_for_bar(node: Node) -> Node:
    """Generate bass notes for one bar from harmony.

    Args:
        node: The 'notes' node for a bass voice

    Returns:
        New notes node with bass pitches
    """
    voice: Node = node.parent
    assert voice is not None, "notes node must have parent voice"
    harmony: tuple[str, ...] | None = _get_harmony(node)
    if harmony is None:
        return node
    metre: str = _get_metre(node)
    bar_duration: Fraction = _parse_metre(metre)
    bar_idx: int = _get_bar_index(node)
    if bar_idx >= len(harmony):
        return node
    chord: str = harmony[bar_idx]
    bar_notes: Notes = generate_harmonic_bass(chord, bar_duration, metre)
    final: Notes = _to_diatonic(bar_notes, "bass")
    notes_data: list[dict[str, Any]] = notes_to_dicts(final)
    return yaml_to_tree(notes_data, key="notes", parent=voice)


def generate_harmonic_bass(chord: str, bar_duration: Fraction, metre: str) -> Notes:
    """Generate harmonic bass pattern for one bar from YAML patterns."""
    root: int = roman_to_degree(chord)
    harmonic: dict[str, Any] = BASS_PATTERNS["harmonic"]
    metres: dict[str, Any] = harmonic["metres"]
    if metre not in metres:
        return Notes((root,), (bar_duration,))
    pattern: dict[str, Any] = metres[metre]
    intervals: list[int] = pattern["intervals"]
    dur_strs: list[str] = pattern["durations"]
    pitches: tuple[int, ...] = tuple(
        ((root - 1 + interval) % 7) + 1 for interval in intervals
    )
    durations: tuple[Fraction, ...] = tuple(Fraction(d) for d in dur_strs)
    return Notes(pitches, durations)


def roman_to_degree(roman: str) -> int:
    """Convert Roman numeral to scale degree (1-7)."""
    assert roman in TONAL_ROOTS, f"Unknown Roman numeral: '{roman}'. Valid: {sorted(TONAL_ROOTS.keys())}"
    return TONAL_ROOTS[roman]


def _get_bar_index(node: Node) -> int:
    """Get bar index from ancestor bar node."""
    bar: Node | None = node.find_ancestor(lambda n: "bar_index" in n)
    assert bar is not None, "Cannot find bar ancestor with bar_index"
    return bar["bar_index"].value


def _get_harmony(node: Node) -> tuple[str, ...] | None:
    """Get harmony from ancestor phrase node."""
    phrase: Node | None = node.find_ancestor(
        lambda n: n.parent is not None and n.parent.key == "phrases"
    )
    if phrase is None or "harmony" not in phrase:
        return None
    harmony_node: Node = phrase["harmony"]
    if harmony_node.value is None:
        return None
    chords: list[str] = []
    for child in harmony_node.children:
        assert isinstance(child.value, str), f"Harmony chord must be string, got {type(child.value).__name__}"
        chords.append(child.value)
    return tuple(chords) if chords else None


def _get_metre(node: Node) -> str:
    """Get metre from frame."""
    root: Node = node.root
    assert "frame" in root, "Tree missing required 'frame' node"
    assert "metre" in root["frame"], "Frame missing required 'metre' key"
    return root["frame"]["metre"].value


def _parse_metre(metre: str) -> Fraction:
    """Parse metre string to bar duration."""
    parts: list[str] = metre.split("/")
    return Fraction(int(parts[0]), int(parts[1]))


def _to_diatonic(notes: Notes, role: str) -> Notes:
    """Convert degrees to diatonic pitches for role."""
    base: int = DIATONIC_DEFAULTS.get(role, 21)
    base_octave: int = base // 7
    diatonic: tuple[int, ...] = tuple(
        base_octave * 7 + ((d - 1) % 7)
        for d in notes.pitches
    )
    return Notes(diatonic, notes.durations)
