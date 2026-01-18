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
    Returns None only if:
    - Key is not a string (e.g., integer list index)
    - No matching YAML file exists
    Throws if file exists but entry is missing.
    """
    if node.key is None:
        return None
    if not isinstance(node.key, str):
        return None  # Integer keys (list indices) can't be included
    if node.value is None:
        return None
    data_dir: Path
    for data_dir in (BUILDER_DATA_DIR, DATA_DIR):
        path: Path = data_dir / f"{node.key}s.yaml"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                parsed: Node | None = yaml_to_tree(yaml.safe_load(f))
            if parsed is None:
                continue
            # Only include if entry exists; otherwise treat as data value
            if node.value not in parsed:
                continue
            content: Node = parsed.child(node.value)
            return node.with_children(content.children)
    return None

def _elaborate_child(child: Node) -> Node:
    """Elaborate a single child node."""
    handler: Callable[[Node], Node] | None
    # Non-leaf: try handler, else recurse
    if not child.is_leaf():
        handler = get_handler(child.key, None)
        if handler:
            return handler(child)
        return elaborate(child)
    # Leaf: try handler
    handler = get_handler(child.key, child.value)
    if handler:
        return handler(child)
    # Leaf: try YAML include
    included: Node | None = include(child)
    if included:
        return elaborate(included)
    # Pass through unhandled leaf nodes (data values like 'description', 'key', etc.)
    return child

def elaborate(node: Node) -> Node:
    """Elaborate node tree via handler dispatch."""
    children: tuple[Node, ...] = tuple(_elaborate_child(c) for c in node.children)
    return node.with_children(children)
