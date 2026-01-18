# handlers/

Category B orchestrators for tree elaboration.

Handlers validate inputs, extract context via adapters, call domain functions,
and write results back via adapters. They are the thin layer that coordinates
the system.

## Modules

| Module | Purpose |
|--------|---------|
| core.py | Handler registration and dispatch system |
| material_handler.py | Soprano voice note generation |
| bass_handler.py | Bass voice note generation |
| structure.py | Structural elaboration |

## Handler Pattern

```python
@register('notes', '*')
def handle_notes(node: Node) -> Node:
    # 1. Extract context via adapter
    context = extract_bar_context(node)

    # 2. Call domain functions
    notes = generate_notes(context)

    # 3. Write back via adapter
    return build_notes_tree(notes, node.parent)
```

## Dependencies

Imports from domain/, adapters/, shared/.
