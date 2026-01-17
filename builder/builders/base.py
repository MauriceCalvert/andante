"""Base builder class and registry."""
from pathlib import Path
from typing import Any

import yaml

from builder.tree import Node, yaml_to_tree

DATA_DIR: Path = Path(__file__).parent.parent.parent / "data"
BUILDER_DATA_DIR: Path = Path(__file__).parent.parent / "data"

BUILDERS: dict[str, type['Builder']] = {}


def register(key: str):
    """Decorator to register a builder class for a node key."""
    def decorator(cls: type['Builder']) -> type['Builder']:
        BUILDERS[key] = cls
        return cls
    return decorator


def include(node: Node) -> Node | None:
    """Look up a reference in YAML data files.

    Given a node like {arc: dance_stately}, looks for data/arcs.yaml
    and returns the 'dance_stately' subtree.
    """
    for data_dir in (BUILDER_DATA_DIR, DATA_DIR):
        path: Path = data_dir / f"{node.key}s.yaml"
        if path.exists():
            root: Node = yaml_to_tree(yaml.safe_load(open(path, encoding="utf-8")))
            if node.value in root:
                return root.child(node.value)
    return None


def build(node: Node, context: dict[str, Any] | None = None) -> Node:
    """Build a node by dispatching to the appropriate builder."""
    if context is None:
        context = {}
    builder_class: type[Builder] = BUILDERS.get(node.key, Builder)
    builder: Builder = builder_class(node, context)
    return builder.elaborate()


class Builder:
    """Base builder that resolves references and recurses into children."""

    def __init__(self, node: Node, context: dict[str, Any]) -> None:
        self.node = node
        self.context = context

    def elaborate(self) -> Node:
        """Elaborate this node by processing its children.

        For each child:
        - If leaf with value: try to resolve via include()
        - If non-leaf: recursively build
        """
        results: list[Node] = []
        for child in self.node.children:
            if child.is_leaf():
                if child.value is None:
                    results.append(child)
                    continue
                dispatch: Node | None = include(child)
                if dispatch:
                    results.append(dispatch)
                else:
                    results.append(child)
            else:
                result: Node = build(child, self.context)
                results.append(result)
        return self.node.with_children(tuple(results))
