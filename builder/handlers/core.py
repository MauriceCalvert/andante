"""Core handler dispatch system."""
from pathlib import Path
from typing import Any, Callable

import yaml

from builder.tree import Node, yaml_to_tree

DATA_DIR: Path = Path(__file__).parent.parent.parent / "data"
BUILDER_DATA_DIR: Path = Path(__file__).parent.parent / "data"

HANDLERS: dict[tuple[str, str], Callable[[Node], Node]] = {}


def register(key: str, value: str = '*') -> Callable[[Callable[[Node], Node]], Callable[[Node], Node]]:
    """Register handler for (key, value). Use '*' for any value."""
    def decorator(fn: Callable[[Node], Node]) -> Callable[[Node], Node]:
        HANDLERS[(key, value)] = fn
        return fn
    return decorator


def get_handler(key: str, value: Any) -> Callable[[Node], Node] | None:
    """Look up handler, trying exact match then wildcard."""
    handler: Callable[[Node], Node] | None
    if value is not None:
        handler = HANDLERS.get((key, str(value)))
        if handler:
            return handler
    return HANDLERS.get((key, '*'))


def include(node: Node) -> Node | None:
    """Resolve YAML reference, preserving original key.

    Given a node like {arc: dance_stately}, looks for data/arcs.yaml
    and returns a node with key 'arc' containing the dance_stately content.
    """
    data_dir: Path
    for data_dir in (BUILDER_DATA_DIR, DATA_DIR):
        path: Path = data_dir / f"{node.key}s.yaml"
        if path.exists():
            root: Node = yaml_to_tree(yaml.safe_load(open(path, encoding="utf-8")))
            if node.value in root:
                content: Node = root.child(node.value)
                return node.with_children(content.children)
    return None


def elaborate(node: Node) -> Node:
    """Elaborate node tree via handler dispatch.

    For each child:
    1. Try (key, value) handler - exact match
    2. Try (key, '*') handler - wildcard
    3. Try include() - YAML resolution
    4. Recurse into non-leaf nodes
    5. Pass through leaf nodes
    """
    results: list[Node] = []
    child: Node
    for child in node.children:
        if child.is_leaf() and child.value is not None:
            handler: Callable[[Node], Node] | None = get_handler(child.key, child.value)
            if handler:
                results.append(handler(child))
                continue
            included: Node | None = include(child)
            if included:
                results.append(elaborate(included))
                continue
            results.append(child)
        elif not child.is_leaf():
            handler = get_handler(child.key, None)
            if handler:
                results.append(handler(child))
            else:
                results.append(elaborate(child))
        else:
            results.append(child)
    return node.with_children(tuple(results))
