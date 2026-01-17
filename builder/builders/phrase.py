"""Phrase builder."""
from fractions import Fraction

from builder.builders.base import Builder, build, register
from builder.tree import Node, yaml_to_tree


@register('phrases')
class PhraseBuilder(Builder):
    """Builds the phrases list by elaborating each phrase and creating bars."""

    def elaborate(self) -> Node:
        """Process each phrase in the list."""
        results: list[Node] = []
        for child in self.node.children:
            result = self._build_phrase(child)
            results.append(result)
        return self.node.with_children(tuple(results))

    def _build_phrase(self, phrase: Node) -> Node:
        """Build a single phrase node by creating bars."""
        bar_count = phrase['bars'].value if 'bars' in phrase else 1
        voice_count = self._get_voice_count()
        metre = self._get_metre()

        bars_data = []
        for bar_idx in range(bar_count):
            bar_data = {
                'bar_index': bar_idx,
                'voices': self._create_voices_stub(voice_count, metre),
            }
            bars_data.append(bar_data)

        bars_node = yaml_to_tree(bars_data, key='bars', parent=phrase)

        built_bars = build(bars_node, self.context)

        results: list[Node] = []
        for child in phrase.children:
            results.append(child)
        results.append(built_bars)

        return phrase.with_children(tuple(results))

    def _get_voice_count(self) -> int:
        """Get voice count from frame."""
        try:
            return self.node.lookup('frame', 'voices')
        except KeyError:
            return 2

    def _get_metre(self) -> str:
        """Get metre from frame."""
        try:
            return self.node.lookup('frame', 'metre')
        except KeyError:
            return '4/4'

    def _create_voices_stub(self, voice_count: int, metre: str) -> list[dict]:
        """Create stub voice data."""
        roles = ['soprano', 'bass', 'alto', 'tenor'][:voice_count]
        return [{'role': role} for role in roles]
