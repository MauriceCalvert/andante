from pathlib import Path

import yaml

from builder.tree import Node, yaml_to_tree

DATA_DIR: Path = Path(__file__).parent.parent / "data"


def include(node: Node) -> Node | None:
    path: Path = DATA_DIR / f"{node.key}s.yaml"
    if not path.exists():
        return None
    root: Node = yaml_to_tree(yaml.safe_load(open(path, encoding="utf-8")))
    return root.child(node.value)


class Builder:
    def __init__(self, node: Node) -> None:
        self.node = node
        
    def elaborate(self) -> Node:
        results: list[Node] = []
        spaces: str = " " * self.node.depth * 2
        print(f"{spaces}elaborating {self.node}")
        for child in self.node.children:
            print(f"  child {child}")
            if child.is_leaf():
                if child.value is None:
                    print(f"{spaces}  leaf {child}")
                    results.append(child)
                    continue
                dispatch: Node = include(child)
                if dispatch:
                    print(f"{spaces}  dispatching {dispatch}")
                    results.append(dispatch)
                    continue
                print(f"{spaces}  leaf {child}")
                results.append(child)
            else:
                result: Node = build(child)
                if result:
                    print(f"{spaces}appending {result}")
                    results.append(result)
        return Node(key=self.node.key, children=tuple(results),value=None)

class BuildStructure(Builder):
    def __init__(self, node: Node) -> None:
        super().__init__(node)

def build(entity: Node) -> Node:
    """Build an entity by iterating across its children."""
    print(f"build {entity}")
    builder_class: type[Builder] = BUILDERS.get(entity.key, Builder)
    builder: Builder = builder_class(entity)
    result: Node = builder.elaborate()
    return result

BUILDERS: dict[str, type[Builder]] = {
    'structure': BuildStructure,
}

def main() -> None:
    fn: str = r"D:\projects\Barok\barok\source\andante\output\tests\level_01_full.yaml"
    path: Path = Path(fn)
    root: Node = yaml_to_tree(yaml.safe_load(open(path, encoding="utf-8")))
    result: Node = build(root['structure'])
    print("==============================================")
    result.print_tree()

if __name__ == "__main__":
    main()
