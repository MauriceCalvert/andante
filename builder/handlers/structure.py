"""Structure handlers - only for nodes that create new structure."""
from fractions import Fraction
from typing import Any

from builder.handlers.core import register, elaborate
from builder.handlers.phrase_handler import compute_phrase_melody
from builder.tree import Node, yaml_to_tree
from builder.types import Notes
from shared.constants import DIATONIC_DEFAULTS


@register('phrases', '*')
def handle_phrases(node: Node) -> Node:
    """Elaborate each phrase by creating bars."""
    metre: str = _get_metre(node)
    bar_duration: Fraction = _parse_metre(metre)

    results: list[Node] = []
    for phrase in node.children:
        results.append(_build_phrase(phrase, node, bar_duration))
    return node.with_children(tuple(results))


def _build_phrase(phrase: Node, parent: Node, bar_duration: Fraction) -> Node:
    """Build phrase: compute melody, derive bar count, create bars."""
    root: Node = parent.root
    voice_count: int = _get_voice_count(parent)

    # Compute phrase melody and bar count from subject + treatment
    melody, bar_count = compute_phrase_melody(phrase, root, bar_duration)

    # Store melody on phrase for bar handlers to access
    melody_data: dict[str, Any] = {
        "pitches": list(melody.pitches),
        "durations": [str(d) for d in melody.durations],
    }
    melody_node: Node | None = yaml_to_tree(melody_data, key="melody", parent=phrase)

    # Add melody to phrase BEFORE elaborating bars (bars need to access it)
    phrase_with_melody: Node = phrase.with_children(
        tuple(phrase.children) + (melody_node,)
    )

    bars_data: list[dict[str, Any]] = []
    for bar_idx in range(bar_count):
        bars_data.append({
            'bar_index': bar_idx,
            'voices': _create_voices_stub(voice_count),
        })

    bars_node: Node | None = yaml_to_tree(bars_data, key='bars', parent=phrase_with_melody)
    assert bars_node is not None, "bars_data produced empty tree"
    built_bars: Node = elaborate(bars_node)

    results: list[Node] = list(phrase_with_melody.children) + [built_bars]
    return phrase_with_melody.with_children(tuple(results))


@register('voices', '*')
def handle_voices(node: Node) -> Node:
    """Generate notes for each voice."""
    metre: str = _get_metre(node)
    bar_duration: Fraction = _parse_metre(metre)

    results: list[Node] = []
    for voice in node.children:
        built: Node = _build_voice(voice, bar_duration)
        elaborated: Node = elaborate(built)
        results.append(elaborated)
    return node.with_children(tuple(results))


def _build_voice(voice: Node, bar_duration: Fraction) -> Node:
    """Build a single voice node by generating stub notes."""
    assert 'role' in voice, "Voice node missing required 'role' key"
    role: str = voice['role'].value
    assert role in DIATONIC_DEFAULTS, f"Unknown voice role: '{role}'. Valid: {sorted(DIATONIC_DEFAULTS.keys())}"
    diatonic: int = DIATONIC_DEFAULTS[role]

    notes_data: list[dict[str, Any]] = [
        {'diatonic': diatonic, 'duration': str(bar_duration)}
    ]

    notes_node: Node | None = yaml_to_tree(notes_data, key='notes', parent=voice)
    assert notes_node is not None, "notes_data produced empty tree"

    results: list[Node] = list(voice.children) + [notes_node]
    return voice.with_children(tuple(results))


def _get_voice_count(node: Node) -> int:
    """Get voice count from frame."""
    root: Node = node.root
    assert 'frame' in root, "Tree missing required 'frame' node"
    assert 'voices' in root['frame'], "Frame missing required 'voices' key"
    val: Any = root['frame']['voices'].value
    assert isinstance(val, int), f"voices must be int, got {type(val).__name__}"
    assert val > 0, f"voices must be positive, got {val}"
    return val


def _get_metre(node: Node) -> str:
    """Get metre from frame."""
    root: Node = node.root
    assert 'frame' in root, "Tree missing required 'frame' node"
    assert 'metre' in root['frame'], "Frame missing required 'metre' key"
    val: Any = root['frame']['metre'].value
    assert isinstance(val, str), f"metre must be string, got {type(val).__name__}"
    return val


def _create_voices_stub(voice_count: int) -> list[dict[str, str]]:
    """Create stub voice data."""
    assert 1 <= voice_count <= 4, f"voice_count must be 1-4, got {voice_count}"
    roles: list[str] = ['soprano', 'bass', 'alto', 'tenor'][:voice_count]
    return [{'role': role} for role in roles]


def _parse_metre(metre: str) -> Fraction:
    """Parse metre string to bar duration."""
    assert '/' in metre, f"Invalid metre format: '{metre}'. Expected 'n/d' (e.g., '4/4')"
    parts: list[str] = metre.split('/')
    assert len(parts) == 2, f"Invalid metre format: '{metre}'. Expected 'n/d' (e.g., '4/4')"
    num_str: str = parts[0]
    den_str: str = parts[1]
    assert num_str.isdigit(), f"Invalid metre numerator: '{num_str}' in '{metre}'"
    assert den_str.isdigit(), f"Invalid metre denominator: '{den_str}' in '{metre}'"
    return Fraction(int(num_str), int(den_str))
