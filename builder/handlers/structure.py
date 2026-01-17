"""Structure handlers for sections, episodes, phrases, bars, voices."""
from fractions import Fraction

from builder.handlers.core import register, elaborate
from builder.tree import Node, yaml_to_tree


DIATONIC_DEFAULTS = {
    'soprano': 32,  # G4 (octave 4, degree 5)
    'bass': 21,     # C3 (octave 3, degree 1)
    'alto': 28,     # C4 (octave 4, degree 1)
    'tenor': 25,    # A3 (octave 3, degree 6)
}


@register('sections', '*')
def handle_sections(node: Node) -> Node:
    """Elaborate each section in the list."""
    results = []
    for section in node.children:
        results.append(elaborate(section))
    return node.with_children(tuple(results))


@register('episodes', '*')
def handle_episodes(node: Node) -> Node:
    """Elaborate each episode in the list."""
    results = []
    for episode in node.children:
        results.append(elaborate(episode))
    return node.with_children(tuple(results))


@register('phrases', '*')
def handle_phrases(node: Node) -> Node:
    """Elaborate each phrase by creating bars."""
    results = []
    for phrase in node.children:
        results.append(_build_phrase(phrase, node))
    return node.with_children(tuple(results))


def _build_phrase(phrase: Node, parent: Node) -> Node:
    """Build a single phrase node by creating bars."""
    bar_count = phrase['bars'].value if 'bars' in phrase else 1
    voice_count = _get_voice_count(parent)
    metre = _get_metre(parent)

    bars_data = []
    for bar_idx in range(bar_count):
        bar_data = {
            'bar_index': bar_idx,
            'voices': _create_voices_stub(voice_count),
        }
        bars_data.append(bar_data)

    bars_node = yaml_to_tree(bars_data, key='bars', parent=phrase)
    built_bars = elaborate(bars_node)

    results = list(phrase.children) + [built_bars]
    return phrase.with_children(tuple(results))


@register('bars', '*')
def handle_bars(node: Node) -> Node:
    """Elaborate each bar by creating voices."""
    results = []
    for bar in node.children:
        results.append(elaborate(bar))
    return node.with_children(tuple(results))


@register('voices', '*')
def handle_voices(node: Node) -> Node:
    """Generate notes for each voice."""
    metre = _get_metre(node)
    bar_duration = _parse_metre(metre)

    results = []
    for voice in node.children:
        results.append(_build_voice(voice, bar_duration))
    return node.with_children(tuple(results))


def _build_voice(voice: Node, bar_duration: Fraction) -> Node:
    """Build a single voice node by generating stub notes."""
    role = voice['role'].value if 'role' in voice else 'soprano'
    diatonic = DIATONIC_DEFAULTS.get(role, 28)

    notes_data = [
        {'diatonic': diatonic, 'duration': str(bar_duration)}
    ]

    notes_node = yaml_to_tree(notes_data, key='notes', parent=voice)

    results = list(voice.children) + [notes_node]
    return voice.with_children(tuple(results))


def _get_voice_count(node: Node) -> int:
    """Get voice count from frame."""
    try:
        return node.lookup('frame', 'voices')
    except KeyError:
        return 2


def _get_metre(node: Node) -> str:
    """Get metre from frame."""
    try:
        return node.lookup('frame', 'metre')
    except KeyError:
        return '4/4'


def _create_voices_stub(voice_count: int) -> list[dict]:
    """Create stub voice data."""
    roles = ['soprano', 'bass', 'alto', 'tenor'][:voice_count]
    return [{'role': role} for role in roles]


def _parse_metre(metre: str) -> Fraction:
    """Parse metre string to bar duration."""
    num, den = metre.split('/')
    return Fraction(int(num), int(den))
