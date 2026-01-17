"""Section builder."""
from builder.builders.base import Builder, build, register
from builder.tree import Node


@register('sections')
class SectionBuilder(Builder):
    """Builds the sections list by elaborating each section."""

    def elaborate(self) -> Node:
        """Process each section in the list."""
        results: list[Node] = []
        for child in self.node.children:
            result = self._build_section(child)
            results.append(result)
        return self.node.with_children(tuple(results))

    def _build_section(self, section: Node) -> Node:
        """Build a single section node."""
        results: list[Node] = []
        for child in section.children:
            if child.key == 'episodes':
                result = build(child, self.context)
                results.append(result)
            else:
                results.append(child)
        return section.with_children(tuple(results))
