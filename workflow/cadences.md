# Cadence Consolidation

## Problem

Cadence data is split across three files with no cross-references:

1. **schemas.yaml** — defines cadential schemas (`cadenza_semplice`,
   `cadenza_composta`, `comma`, `half_cadence`) with `cadential_state`,
   `final`, `position: cadential`, soprano/bass degrees, bar counts
2. **cadences.yaml** — defines cadence *types* (`authentic`, `half`,
   `deceptive`, `plagal`, `phrygian`) with voice-leading formulas split
   into `internal` and `final` sections, plus `roman_numerals` and
   `transitions`
3. **cadence_templates/templates.yaml** — per-metre duration templates
   keyed by schema name

There is no link between a schema name and a cadence type. Nothing says
`cadenza_composta` is an `authentic` cadence. The `internal`/`final`
distinction in cadences.yaml already encodes finality, but schemas.yaml
duplicates this with `final: true/false` and `cadential_state: closed`.

## Principle

**cadences.yaml is the single source of truth for everything about a
cadence.** Everything else refers to it.

## Target cadences.yaml structure

```yaml
# Cadence Types
# =============
# Each type defines: harmonic identity, voice-leading, finality,
# and which schema(s) realise it.

types:
  authentic_internal:
    roman_numerals: [V, I]
    schemas: [cadenza_semplice]
    final: false
  authentic_final:
    roman_numerals: [V, I]
    schemas: [cadenza_composta]
    final: true
  half:
    roman_numerals: [V]
    schemas: [half_cadence]
    final: false
  comma:
    roman_numerals: [V, I]
    schemas: [comma]
    final: true
  deceptive:
    roman_numerals: [V, vi]
    schemas: []           # no schema realisation yet
    final: false
  plagal:
    roman_numerals: [IV, I]
    schemas: []           # no schema realisation yet
    final: false
  phrygian:
    roman_numerals: [iv, V]
    schemas: []           # no schema realisation yet
    final: false

# Voice-leading formulas (existing internal/final sections, unchanged)
internal:
  authentic:
    top: [7, 1]
    ...
  half:
    ...

final:
  stepwise:
    ...
  leap:
    ...
  decorated:
    ...
  invention:
    ...

# Transition lookup (existing, unchanged)
transitions:
  major:
    I_to_V: half
    V_to_I: authentic
    ...
  minor:
    ...
```

## What to remove from schemas.yaml

For each cadential schema (`cadenza_semplice`, `cadenza_composta`,
`comma`, `half_cadence`):

- Remove `cadential_state` — replaced by the `final` field on the
  cadence type in cadences.yaml
- Remove `final: true/false` — same reason

Non-cadential schemas keep `cadential_state: open` (means "this schema
does not cadence"). That field stays for non-cadential schemas.

Actually, simpler: rename `cadential_state` to something that only means
"does this schema produce a cadence at all" — but the existing usage
throughout the codebase only checks `position == "cadential"` to decide
this. `cadential_state` on non-cadential schemas is always `"open"` and
is never read. So:

- **Remove `cadential_state` from ALL schemas.** The `position` field
  already distinguishes cadential from non-cadential schemas.
- **Remove `final` from ALL schemas.** Finality lives in cadences.yaml.

## What to add to schemas.yaml

For each cadential schema, add `cadence_type` linking to cadences.yaml:

```yaml
cadenza_semplice:
  cadence_type: authentic_internal
  ...

cadenza_composta:
  cadence_type: authentic_final
  ...

comma:
  cadence_type: comma
  ...

half_cadence:
  cadence_type: half
  ...
```

## cadence_templates/templates.yaml — no change

Templates are keyed by schema name and metre. They define durations for
the schema's realisation. This is schema-specific (how long each degree
lasts in 3/4 vs 4/4), not cadence-type-specific. Stays as-is.

## Code changes

### 1. schema_types.py

In `SchemaConfig` dataclass:
- Remove `cadential_state: str`
- Add `cadence_type: str | None = None`

### 2. schema_loader.py

- Parse `cadence_type` from schema data instead of `cadential_state`
- `cadence_type=data.get("cadence_type")`

### 3. shared/constants.py or new cadence_loader.py

Add a loader that reads cadences.yaml types section:

```python
def load_cadence_types() -> dict[str, CadenceType]:
    """Load cadence type definitions from cadences.yaml."""
```

Returns dict mapping type name to a dataclass:

```python
@dataclass(frozen=True)
class CadenceTypeDef:
    roman_numerals: tuple[str, ...]
    schemas: tuple[str, ...]
    final: bool
```

### 4. Validator: yaml_validator.py

Replace the `final: true` check with:
- Load cadences.yaml `types` section
- Build set of final-eligible schema names: union of `schemas` lists
  from types where `final: true`
- Check last schema of last section is in that set
- Cross-validate: every `cadence_type` value in schemas.yaml must exist
  as a key in cadences.yaml `types`
- Remove `VALID_CADENTIAL_STATES` constant (no longer validated)

### 5. phrase_planner.py

Currently line 131:
```python
is_cadential: bool = schema_def.position == CADENTIAL_POSITION
```

No change needed — `position` still determines cadential identity.

Currently line 197-199:
```python
cadence_type: str | None = None
if is_cadential and schema_index < len(schema_chain.cadences):
    cadence_type = schema_chain.cadences[schema_index]
```

This reads from `schema_chain.cadences` which is populated by
`schematic.py` from the tonal plan. This is the *harmonic* cadence type
(authentic, half, etc.) assigned during tonal planning. It should cross-
check against the schema's `cadence_type` field but otherwise the flow
is correct. No change needed here initially.

### 6. cadence_writer.py

Line 141:
```python
if schema_def.position == "cadential" and metre is not None:
```

No change — still uses `position`.

### 7. builder/types.py (SchemaChain)

```python
cadences: tuple[str | None, ...] = ()
```

These are cadence types from tonal planning. They should be validated
against the `types` keys in cadences.yaml. No structural change.

### 8. note_writer.py

Currently maps `cadence_type` to abbreviation for .note output. The
type names may change (`authentic_final` vs `authentic`). Update
`CADENCE_ABBREV` dict.

## File change summary

| File | Action |
|------|--------|
| `data/cadences/cadences.yaml` | Add `types` section with schema mappings and `final` flags |
| `data/schemas/schemas.yaml` | Remove `cadential_state` and `final` from all schemas; add `cadence_type` to cadential schemas |
| `data/schemas/schema_transitions.yaml` | Remove `cadential_state` from all schema entries |
| `shared/schema_types.py` | Remove `cadential_state`, add `cadence_type: str \| None` |
| `planner/schema_loader.py` | Parse `cadence_type` instead of `cadential_state` |
| `scripts/yaml_validator.py` | Read finality from cadences.yaml types; cross-validate schema cadence_type values; remove `VALID_CADENTIAL_STATES` |
| `builder/note_writer.py` | Update `CADENCE_ABBREV` if type names change |

## Files that do NOT change

| File | Why |
|------|-----|
| `cadence_templates/templates.yaml` | Keyed by schema name, not cadence type |
| `cadence_writer.py` | Uses `position == "cadential"`, not `cadential_state` |
| `phrase_planner.py` | Uses `position`, reads cadence type from schema_chain |
| `compose.py` | Reads `plan.is_cadential` and `plan.cadence_type` |
| `bass_writer.py` | Reads `plan.is_cadential` and `plan.cadence_type` |

## Execution order

1. Add `types` section to cadences.yaml
2. Update schemas.yaml (remove cadential_state/final, add cadence_type)
3. Update schema_transitions.yaml (remove cadential_state)
4. Update schema_types.py and schema_loader.py
5. Update yaml_validator.py
6. Run validator
7. Run pipeline for minuet, gavotte, invention — verify no regression

## Resolved: type naming

The cadence *type* carries finality. A semplice and composta are
different types of authentic cadence — one internal, one final. The
naming (`authentic_internal`, `authentic_final`) makes the distinction
explicit in the data.

The `transitions` section in cadences.yaml keeps bare `authentic` — it
is not consumed by any Python code yet, and the eventual consumer will
resolve `_internal` vs `_final` by position in the tonal plan.

## Additional scope: schema_transitions.yaml

`schema_transitions.yaml` also carries `cadential_state` on every
schema entry (16 occurrences). These must be removed in the same pass
to maintain L017 (single source of truth).
