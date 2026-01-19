"""Bass handler — extracts pre-generated bass from phrase.

No fallbacks. If bass not pre-generated, throws with actionable message.
"""
from fractions import Fraction
from builder.adapters.tree_reader import extract_bar_context
from builder.adapters.tree_writer import build_notes_tree
from builder.tree import Node
from builder.types import BarContext, Notes
from shared.errors import MissingContextError


def generate_bass_for_bar(node: Node) -> Node:
    """Extract bass notes for one bar from pre-generated phrase bass.

    Args:
        node: The 'notes' node for a bass voice

    Returns:
        New notes node with bass pitches

    Raises:
        MissingContextError: If bass not pre-generated on phrase
    """
    context: BarContext = extract_bar_context(node)
    bass: Notes = _extract_bar_bass(node, context)
    return build_notes_tree(bass, node.parent)


def _extract_bar_bass(node: Node, context: BarContext) -> Notes:
    """Extract pre-generated bass for this bar from phrase.

    Raises:
        MissingContextError: If bass not found on phrase
    """
    # Navigate to phrase node
    phrase: Node | None = node.find_ancestor(
        lambda n: n.parent is not None and n.parent.key == "phrases"
    )
    if phrase is None:
        raise MissingContextError(
            "Bass handler: cannot find phrase ancestor. "
            "Ensure bass voice is within a phrase structure."
        )

    # Check for pre-generated bass on phrase
    if "bass" not in phrase:
        raise MissingContextError(
            f"Bass handler: no pre-generated bass on phrase (bar {context.bar_index + 1}). "
            "Ensure harmony is specified in phrase and voice count >= 2."
        )

    bass_node: Node = phrase["bass"]
    if "pitches" not in bass_node or "durations" not in bass_node:
        raise MissingContextError(
            f"Bass handler: phrase bass missing pitches/durations (bar {context.bar_index + 1})."
        )

    # Extract pitches and durations
    pitches: list[int] = [c.value for c in bass_node["pitches"].children]
    durations: list[Fraction] = [Fraction(c.value) for c in bass_node["durations"].children]
    phrase_bass: Notes = Notes(tuple(pitches), tuple(durations))

    # Extract this bar's slice
    bar_duration: Fraction = context.frame.metre.bar_duration
    return _slice_notes(phrase_bass, context.bar_index, bar_duration)


def _slice_notes(notes: Notes, bar_index: int, bar_duration: Fraction) -> Notes:
    """Extract notes for a specific bar from phrase notes."""
    offset: Fraction = bar_duration * bar_index
    window_end: Fraction = offset + bar_duration

    result_pitches: list[int] = []
    result_durations: list[Fraction] = []
    current: Fraction = Fraction(0)

    for p, d in zip(notes.pitches, notes.durations):
        note_start: Fraction = current
        current += d
        if note_start < offset:
            continue
        if note_start >= window_end:
            break
        result_pitches.append(p)
        result_durations.append(d)

    return Notes(tuple(result_pitches), tuple(result_durations))
