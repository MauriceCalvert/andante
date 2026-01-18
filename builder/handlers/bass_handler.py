"""Bass handler — orchestrates bass generation.

Category B: Validates inputs, delegates to domain functions.
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

    # Validate chord
    if chord not in TONAL_ROOTS:
        raise InvalidRomanNumeralError(
            f"Unknown chord: '{chord}'. Valid: {sorted(TONAL_ROOTS.keys())}"
        )

    bar_notes: Notes = _generate_bar_bass(chord, context)
    base_octave: int = DIATONIC_DEFAULTS.get("bass", 21) // 7
    final: Notes = compute_diatonic_bass(bar_notes, base_octave)

    return build_notes_tree(final, node.parent)


def _generate_bar_bass(chord: str, context: BarContext) -> Notes:
    """Generate bass pattern for a single chord."""
    root: int = compute_degree(chord, TONAL_ROOTS)
    metre_str: str = f"{context.frame.metre.numerator}/{context.frame.metre.denominator}"

    harmonic: dict[str, Any] = BASS_PATTERNS.get("harmonic", {})
    metres: dict[str, Any] = harmonic.get("metres", {})

    if metre_str not in metres:
        # Default: whole note on root
        return Notes((root,), (context.frame.metre.bar_duration,))

    pattern: dict[str, Any] = metres[metre_str]
    intervals: tuple[int, ...] = tuple(pattern["intervals"])
    durations: tuple[Fraction, ...] = tuple(Fraction(d) for d in pattern["durations"])

    return compute_harmonic_bass(root, intervals, durations)
