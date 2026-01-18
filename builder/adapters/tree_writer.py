"""Write domain objects back to tree nodes.

Adapters translate domain types to Node structures.

Functions:
    build_notes_tree — Notes → Node
    notes_to_dicts   — Notes → list of dicts for tree insertion
"""
from typing import Any

from builder.tree import Node, yaml_to_tree
from builder.types import Notes


def build_notes_tree(notes: Notes, parent: Node) -> Node:
    """Convert Notes to tree node.

    Args:
        notes: Domain Notes object
        parent: Parent node (voice node)

    Returns:
        New Node with notes data
    """
    data: list[dict[str, Any]] = notes_to_dicts(notes)
    result: Node | None = yaml_to_tree(data, key="notes", parent=parent)
    if result is None:
        raise ValueError("Failed to create notes tree from empty data")
    return result


def notes_to_dicts(notes: Notes) -> list[dict[str, Any]]:
    """Convert Notes to list of note dicts for tree insertion.

    Args:
        notes: Domain Notes object

    Returns:
        List of dicts with 'diatonic' and 'duration' keys
    """
    return [
        {"diatonic": p, "duration": str(d)}
        for p, d in zip(notes.pitches, notes.durations)
    ]
