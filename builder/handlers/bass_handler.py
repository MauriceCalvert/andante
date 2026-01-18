"""Bass handler — orchestrates bass generation.
Category B: Validates inputs, delegates to domain functions.
Selects bass patterns based on energy and cadence context.
SIZE: 120 lines — Handler coordinates pattern selection based on
energy and cadence, with fallback to harmonic patterns.
"""
from fractions import Fraction
from pathlib import Path
from typing import Any
import yaml
from builder.adapters.tree_reader import extract_bar_context
from builder.adapters.tree_writer import build_notes_tree
from builder.domain.bass_ops import compute_degree, compute_diatonic_bass, compute_harmonic_bass
from builder.tree import Node
from builder.types import BarContext, Notes
from shared.constants import DIATONIC_DEFAULTS, TONAL_ROOTS
from shared.errors import InvalidRomanNumeralError
BUILDER_DATA_DIR: Path = Path(__file__).parent.parent / "data"
RISING_ENERGY: frozenset[str] = frozenset({"rising", "peak"})
MODERATE_ENERGY: frozenset[str] = frozenset({"moderate", "low"})

def _load_bass_patterns() -> dict[str, Any]:
    """Load bass patterns from YAML."""
    path: Path = BUILDER_DATA_DIR / "bass_patterns.yaml"
    with open(path, encoding="utf-8") as f:
        data: Any = yaml.safe_load(f)
    return data or {}
BASS_PATTERNS: dict[str, Any] = _load_bass_patterns()

def generate_bass_for_bar(node: Node) -> Node:
    """Generate bass notes for one bar from harmony.
    Category B orchestrator: extracts context, validates, calls domain.
    Selects pattern based on energy and cadence.
    Args:
        node: The 'notes' node for a bass voice
    Returns:
        New notes node with bass pitches
    """
    context: BarContext = extract_bar_context(node)
    if context.harmony is None:
        return node
    if context.bar_index >= len(context.harmony):
        return node
    chord: str = context.harmony[context.bar_index]
    if chord not in TONAL_ROOTS:
        raise InvalidRomanNumeralError(
            f"Unknown chord: '{chord}'. Valid: {sorted(TONAL_ROOTS.keys())}"
        )
    bar_notes: Notes = _generate_bar_bass(chord, context)
    base_octave: int = DIATONIC_DEFAULTS.get("bass", 21) // 7
    final: Notes = compute_diatonic_bass(bar_notes, base_octave)
    return build_notes_tree(final, node.parent)

def _generate_bar_bass(chord: str, context: BarContext) -> Notes:
    """Generate bass pattern for a single chord based on context."""
    root: int = compute_degree(chord, TONAL_ROOTS)
    metre_str: str = f"{context.frame.metre.numerator}/{context.frame.metre.denominator}"
    pattern_name, pattern_data = _select_pattern(context, metre_str)
    if pattern_data is None:
        return Notes((root,), (context.frame.metre.bar_duration,))
    intervals: tuple[int, ...] = tuple(pattern_data["intervals"])
    durations: tuple[Fraction, ...] = tuple(Fraction(d) for d in pattern_data["durations"])
    return compute_harmonic_bass(root, intervals, durations)

def _select_pattern(context: BarContext, metre_str: str) -> tuple[str, dict[str, Any] | None]:
    """Select bass pattern based on energy and cadence.
    Args:
        context: Bar context with energy and cadence
        metre_str: Time signature string (e.g., "4/4")
    Returns:
        (pattern_name, pattern_data) or (name, None) if not found
    """
    if context.cadence is not None:
        cadential: dict[str, Any] = BASS_PATTERNS.get("cadential", {})
        cadence_type: str = "authentic" if context.cadence == "authentic" else "half"
        cadence_data: dict[str, Any] = cadential.get(cadence_type, {})
        metres: dict[str, Any] = cadence_data.get("metres", {})
        if metre_str in metres:
            return (f"cadential_{cadence_type}", metres[metre_str])
    if context.energy in RISING_ENERGY:
        walking: dict[str, Any] = BASS_PATTERNS.get("walking_bass", {})
        metres = walking.get("metres", {})
        if metre_str in metres:
            return ("walking_bass", metres[metre_str])
    if context.energy in MODERATE_ENERGY:
        sustained: dict[str, Any] = BASS_PATTERNS.get("sustained", {})
        metres = sustained.get("metres", {})
        if metre_str in metres:
            return ("sustained", metres[metre_str])
    harmonic: dict[str, Any] = BASS_PATTERNS.get("harmonic", {})
    metres = harmonic.get("metres", {})
    if metre_str in metres:
        return ("harmonic", metres[metre_str])
    return ("default", None)
