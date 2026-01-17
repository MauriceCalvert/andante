"""Episode builder."""
from builder.builders.base import Builder, build, register
from builder.tree import Node


@register('episodes')
class EpisodeBuilder(Builder):
    """Builds the episodes list by elaborating each episode."""

    def elaborate(self) -> Node:
        """Process each episode in the list."""
        results: list[Node] = []
        for child in self.node.children:
            result = self._build_episode(child)
            results.append(result)
        return self.node.with_children(tuple(results))

    def _build_episode(self, episode: Node) -> Node:
        """Build a single episode node."""
        results: list[Node] = []
        for child in episode.children:
            if child.key == 'phrases':
                result = build(child, self.context)
                results.append(result)
            else:
                results.append(child)
        return episode.with_children(tuple(results))
