# domain/

Category A pure functions. No I/O, no validation, no side effects.

All functions assume valid input. Validation happens in Category B orchestrators.

## Modules

| Module | Purpose |
|--------|---------|
| pitch_ops.py | Pitch conversions (diatonic ↔ MIDI) |
| material_ops.py | Material transformations (fit, shift, convert) |
| bass_ops.py | Bass generation (harmonic patterns) |
| transform_ops.py | Transform operations (augment, diminish, invert) |

## Dependencies

Imports only from `shared/` and stdlib. Never imports from handlers or adapters.

## Testing

100% line and branch coverage required. Tests use real inputs, no mocks.
