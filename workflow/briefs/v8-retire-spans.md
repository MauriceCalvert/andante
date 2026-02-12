## Task: V6 — Retire span infrastructure

Read these files first:
- `builder/voice_writer.py`
- `builder/voice_types.py`
- `builder/strategies/diminution.py`
- `builder/pitch_selection.py`
- `builder/soprano_writer.py` (post V4)

### Goal

Delete the span-based pipeline code that the viterbi solver replaces.
This is dead code removal, not functional change.

### What to delete

**builder/voice_types.py:**
- `SpanBoundary` dataclass
- `SpanResult` dataclass
- `SpanMetadata` dataclass
- `FillStrategy` protocol
- `DiminutionMetadata` dataclass
- `WalkingMetadata` dataclass
- Any other span-related types no longer referenced

Keep: `StructuralTone`, `VoiceConfig`, `WriteResult` (if still used by
the adapter or validation).

**builder/voice_writer.py:**
- `write_voice` function (the 7-step span pipeline)
- Any helper functions only called by `write_voice`

Keep: `validate_voice`, `audit_voice` (post-hoc safety nets).

**builder/strategies/diminution.py:**
- Entire file (DiminutionFill strategy)

**builder/pitch_selection.py:**
- `select_best_pitch` function
- `_score_pitch` function
- Any helpers only called by these

If the entire file becomes empty, delete it.

### Verification method

Before deleting anything:
1. Grep every symbol being deleted across the entire codebase.
2. Confirm zero remaining references outside the files being deleted.
3. If a reference exists elsewhere, it's either a bug (should also be
   updated) or a dependency that must be preserved.

### Constraints

- Do not delete `validate_voice` or `audit_voice`.
- Do not delete `StructuralTone` or `VoiceConfig` if still referenced.
- Do not delete any test files — update them if they import deleted
  symbols, or mark them as skip/deprecated with a comment.
- Run the full test suite after deletion. Any import errors reveal
  missed references.

### Checkpoint

1. No import errors across the project.
2. Full pipeline still generates output for at least one gavotte and one
   invention phrase.
3. The deleted files/symbols are genuinely unreachable.
