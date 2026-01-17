"""Voice builder."""
from fractions import Fraction

from builder.builders.base import Builder, register
from builder.tree import Node, yaml_to_tree


DIATONIC_DEFAULTS = {
    'soprano': 32,  # G4 (octave 4, degree 5)
    'bass': 21,     # C3 (octave 3, degree 1)
    'alto': 28,     # C4 (octave 4, degree 1)
    'tenor': 25,    # A3 (octave 3, degree 6)
}


@register('voices')
class VoiceBuilder(Builder):
    """Builds the voices list by generating notes for each voice."""

    def elaborate(self) -> Node:
        """Process each voice in the list."""
        metre = self._get_metre()
        bar_duration = self._parse_metre(metre)

        results: list[Node] = []
        for child in self.node.children:
            result = self._build_voice(child, bar_duration)
            results.append(result)
        return self.node.with_children(tuple(results))

    def _build_voice(self, voice: Node, bar_duration: Fraction) -> Node:
        """Build a single voice node by generating stub notes."""
        role = voice['role'].value if 'role' in voice else 'soprano'
        diatonic = DIATONIC_DEFAULTS.get(role, 28)

        notes_data = [
            {'diatonic': diatonic, 'duration': str(bar_duration)}
        ]

        notes_node = yaml_to_tree(notes_data, key='notes', parent=voice)

        results: list[Node] = []
        for child in voice.children:
            results.append(child)
        results.append(notes_node)

        return voice.with_children(tuple(results))

    def _get_metre(self) -> str:
        """Get metre from frame."""
        try:
            return self.node.lookup('frame', 'metre')
        except KeyError:
            return '4/4'

    def _parse_metre(self, metre: str) -> Fraction:
        """Parse metre string to bar duration."""
        num, den = metre.split('/')
        return Fraction(int(num), int(den))
