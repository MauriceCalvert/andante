from typing import Any, Callable, Iterator


class Node:
    """Immutable tree node for traversing YAML structures."""
    __slots__ = ('_key', '_value', '_parent', '_children')

    def __init__(
            self,
            key: str | int | None,
            value: Any,
            parent: 'Node | None' = None,
            children: tuple['Node', ...] = ()
    ) -> None:
        object.__setattr__(self, '_key', key)
        object.__setattr__(self, '_value', value)
        object.__setattr__(self, '_parent', parent)
        object.__setattr__(self, '_children', children)

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Node is immutable")

    def __iter__(self) -> Iterator['Node']:
        # for node in root: print(node.key)
        yield self
        for child in self._children:
            yield from child

    def __repr__(self) -> str:
        return f"Node({self._key!r}, {self._value!r}, children={len(self._children)})"

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Node is immutable")

    def __str__(self) -> str:
        return f"{self.path_string()} = {self._value!r}"

    def __getitem__(self, key: str | int) -> 'Node':
        # affect_node = root['brief']['affect']
        return self.child(key)

    def __contains__(self, key: str | int) -> bool:
        # if 'tempo' in node: process(node['tempo'])
        for c in self._children:
            if c._key == key:
                return True
        return False

    @property
    def children(self) -> tuple['Node', ...]:
        # for c in node.children: print(c.key)
        return self._children

    @property
    def depth(self) -> int:
        # if node.depth == 0: print("root")
        count: int = 0
        node: Node | None = self._parent
        while node is not None:
            count += 1
            node = node._parent
        return count

    @property
    def key(self) -> str | int | None:
        # name = node.key
        return self._key

    @property
    def parent(self) -> 'Node | None':
        # section = phrase.parent.parent
        return self._parent

    @property
    def root(self) -> 'Node':
        # brief = node.root.child('brief')
        node: Node = self
        while node._parent is not None:
            node = node._parent
        return node

    @property
    def value(self) -> Any:
        # tempo = node.value
        return self._value

    def ancestors(self) -> Iterator['Node']:
        # for a in node.ancestors(): print(a.key)
        node: Node | None = self._parent
        while node is not None:
            yield node
            node = node._parent

    def find_ancestor(self, predicate: Callable[['Node'], bool]) -> 'Node | None':
        # phrase = bar.find_ancestor(lambda n: n.parent and n.parent.key == 'phrases')
        for ancestor in self.ancestors():
            if predicate(ancestor):
                return ancestor
        return None

    def child(self, key: str | int) -> 'Node':
        # frame = root.child('frame')
        for c in self._children:
            if c._key == key:
                return c
        available: list[str | int | None] = [c._key for c in self._children]
        raise KeyError(f"'{key}' not found at {self.path_string()}. Available: {available}")

    def find(self, predicate: Callable[['Node'], bool]) -> Iterator['Node']:
        # for n in root.find(lambda n: n.key == 'cadence'): print(n.value)
        if predicate(self):
            yield self
        for child in self._children:
            yield from child.find(predicate)

    def is_leaf(self) -> bool:
        # if node.is_leaf(): process(node.value)
        return len(self._children) == 0

    def lookup(self, *keys: str | int) -> Any:
        # affect = node.lookup('brief', 'affect')
        node: Node = self.root
        for k in keys:
            node = node.child(k)
        return node.value

    def path(self) -> list[str | int]:
        # keys = node.path()  # ['structure', 'sections', 0, 'episodes', 0]
        parts: list[str | int] = []
        node: Node | None = self
        while node is not None and node._key is not None:
            parts.append(node._key)
            node = node._parent
        parts.reverse()
        return parts

    def path_string(self, sep: str = '/') -> str:
        # print(node.path_string())  # 'structure/sections/0/episodes/0'
        return sep.join(str(p) for p in self.path()) or '/'

    def print_tree(self, indent: str = '  ', _level: int = 0) -> None:
        # node.print_tree()
        prefix: str = indent * _level
        if self.is_leaf():
            print(f"{prefix}{self._key}: {self._value!r}")
        else:
            print(f"{prefix}{self._key}:")
            for child in self._children:
                child.print_tree(indent, _level + 1)

    def siblings(self) -> tuple['Node', ...]:
        # other_sections = section.siblings()
        if self._parent is None:
            return ()
        return tuple(c for c in self._parent._children if c is not self)

    def walk(self, visitor: Callable[['Node'], None]) -> None:
        # root.walk(lambda n: print(n.key))
        visitor(self)
        for child in self._children:
            child.walk(visitor)

    def walk_post(self, visitor: Callable[['Node'], None]) -> None:
        # root.walk_post(lambda n: totals[n.parent] += n.value)
        for child in self._children:
            child.walk_post(visitor)
        visitor(self)

    def with_children(self, children: tuple['Node', ...]) -> 'Node':
        # new_node = node.with_children((child1, child2))
        new_node: Node = Node(self._key, self._value, self._parent)
        # Reparent children to point to new_node
        reparented: tuple[Node, ...] = tuple(
            child._with_parent(new_node) for child in children
        )
        object.__setattr__(new_node, '_children', reparented)
        return new_node

    def _with_parent(self, parent: 'Node') -> 'Node':
        """Create copy of this node with new parent, recursively reparenting children."""
        new_node: Node = Node(self._key, self._value, parent)
        if self._children:
            reparented: tuple[Node, ...] = tuple(
                child._with_parent(new_node) for child in self._children
            )
            object.__setattr__(new_node, '_children', reparented)
        return new_node

    def with_value(self, value: Any) -> 'Node':
        # new_node = node.with_value(42)
        new_node: Node = Node(self._key, value, self._parent)
        if self._children:
            reparented: tuple[Node, ...] = tuple(
                child._with_parent(new_node) for child in self._children
            )
            object.__setattr__(new_node, '_children', reparented)
        return new_node


def yaml_to_tree(
        data: Any,
        key: str | int | None = None,
        parent: Node | None = None
) -> Node | None:
    # root = yaml_to_tree(yaml.safe_load(open('piece.yaml')))
    if data is None:
        return None
    node: Node
    children: tuple[Node, ...]
    if isinstance(data, dict):
        node = Node(key, data, parent)
        children = tuple(c for c in (yaml_to_tree(v, k, node) for k, v in data.items()) if c is not None)
        object.__setattr__(node, '_children', children)
    elif isinstance(data, list):
        node = Node(key, data, parent)
        children = tuple(c for c in (yaml_to_tree(v, i, node) for i, v in enumerate(data)) if c is not None)
        object.__setattr__(node, '_children', children)
    else:
        node = Node(key, data, parent)
    return node