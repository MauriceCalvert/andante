"""Structure handlers - only for nodes that create new structure."""
from fractions import Fraction
from typing import Any

from builder.handlers.core import register, elaborate
from builder.tree import Node, yaml_to_tree


DIATONIC_DEFAULTS: dict[str, int] = {
    'soprano': 32,  # G4 (octave 4, degree 5)
    'bass': 21,     # C3 (octave 3, degree 1)
    'alto': 28,     # C4 (octave 4, degree 1)
    'tenor': 25,    # A3 (octave 3, degree 6)
}


@register('phrases', '*')
def handle_phrases(node: Node) -> Node:
    """Elaborate each phrase by creating bars."""
    results: list[Node] = []
    for phrase in node.children:
        results.append(_build_phrase(phrase, node))
    return node.with_children(tuple(results))


def _build_phrase(phrase: Node, parent: Node) -> Node:
    """Build a single phrase node by creating bars."""
    bar_count: int = phrase['bars'].value if 'bars' in phrase else 1
    voice_count: int = _get_voice_count(parent)

    bars_data: list[dict[str, Any]] = []
    for bar_idx in range(bar_count):
        bar_data: dict[str, Any] = {
            'bar_index': bar_idx,
            'voices': _create_voices_stub(voice_count),
        }
        bars_data.append(bar_data)

    bars_node: Node = yaml_to_tree(bars_data, key='bars', parent=phrase)
    built_bars: Node = elaborate(bars_node)

    results: list[Node] = list(phrase.children) + [built_bars]
    return phrase.with_children(tuple(results))


@register('voices', '*')
def handle_voices(node: Node) -> Node:
    """Generate notes for each voice."""
    metre: str = _get_metre(node)
    bar_duration: Fraction = _parse_metre(metre)

    results: list[Node] = []
    for voice in node.children:
        results.append(_build_voice(voice, bar_duration))
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

    notes_node: Node = yaml_to_tree(notes_data, key='notes', parent=voice)

    results: list[Node] = list(voice.children) + [notes_node]
    return voice.with_children(tuple(results))


def _get_voice_count(node: Node) -> int:
    """Get voice count from frame."""
    root: Node = node.root
    assert 'frame' in root, "Tree missing required 'frame' node"
    assert 'voices' in root['frame'], "Frame missing required 'voices' key"
    return root['frame']['voices'].value


def _get_metre(node: Node) -> str:
    """Get metre from frame."""
    root: Node = node.root
    assert 'frame' in root, "Tree missing required 'frame' node"
    assert 'metre' in root['frame'], "Frame missing required 'metre' key"
    return root['frame']['metre'].value


def _create_voices_stub(voice_count: int) -> list[dict[str, str]]:
    """Create stub voice data."""
    roles: list[str] = ['soprano', 'bass', 'alto', 'tenor'][:voice_count]
    return [{'role': role} for role in roles]


def _parse_metre(metre: str) -> Fraction:
    """Parse metre string to bar duration."""
    num: str
    den: str
    num, den = metre.split('/')
    return Fraction(int(num), int(den))
