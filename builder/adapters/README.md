# adapters/

Infrastructure implementations that translate between external representations
and domain types.

## Modules

| Module | Purpose |
|--------|---------|
| tree.py | Immutable tree structure (Node, yaml_to_tree) |
| tree_reader.py | Extract domain objects from tree nodes |
| tree_writer.py | Write domain objects back to tree nodes |
| file_export.py | Export domain data to MIDI/.note files |

## Responsibilities

- All tree navigation logic lives here, not in domain
- Validation of tree structure happens here
- File I/O happens here

## Dependencies

Imports from domain/ for types, shared/ for errors.
