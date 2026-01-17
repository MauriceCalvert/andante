"""Bar builder."""
from builder.builders.base import Builder, build, register
from builder.tree import Node


@register('bars')
class BarBuilder(Builder):
    """Builds the bars list by elaborating each bar."""

    def elaborate(self) -> Node:
        """Process each bar in the list."""
        results: list[Node] = []
        for child in self.node.children:
            result = self._build_bar(child)
            results.append(result)
        return self.node.with_children(tuple(results))

    def _build_bar(self, bar: Node) -> Node:
        """Build a single bar node by creating voices."""
        results: list[Node] = []
        for child in bar.children:
            if child.key == 'voices':
                result = build(child, self.context)
                results.append(result)
            else:
                results.append(child)
        return bar.with_children(tuple(results))
