# builder/

Transforms planner YAML into playable notes via tree elaboration.

## Architecture

Follows ports/adapters pattern per A006:

```
types.py          ← Domain types (Notes, Metre, FrameContext, etc.)
domain/           ← Category A: Pure functions, no I/O, no validation
ports/            ← Interface definitions (Protocols)
adapters/         ← Infrastructure implementations (tree, file I/O)
handlers/         ← Category B: Orchestrators that validate and delegate
```

## Key Modules

| Module | Purpose |
|--------|---------|
| types.py | Frozen dataclasses for domain objects |
| transform.py | Transform system (backward compatibility wrapper) |
| export.py | MIDI/note export (backward compatibility wrapper) |
| tree.py | Immutable tree structure for YAML |
| music_math.py | Duration arithmetic (Category A) |

## Data Flow

```
YAML plan → tree.py → handlers/ → domain/ → adapters/ → MIDI/.note
```

## Dependencies

- `shared/` for errors, validation, constants
- stdlib only in domain/
