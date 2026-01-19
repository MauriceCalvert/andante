# Builder Upgrade: Schema-Based Note Generation

## Overview

Upgrade the builder to consume schema-based planner output. The builder transforms `SchemaSlot` into playable notes by loading schema definitions from `data/schemas.yaml` and realising them as voiced counterpoint.

## Input Format Change

### Current (phrase-based)
```yaml
structure:
  sections:
    - episodes:
        - phrases:
            - treatment: statement
              bars: 2
              harmony: [I, V]
```

### New (schema-based)
```yaml
structure:
  sections:
    - label: A
      key_area: I
      schemas:
        - type: romanesca
          bars: 2
          texture: imitative
          treatment: statement
          voice_entry: soprano
        - type: prinner
          bars: 2
          texture: imitative
          treatment: imitation
          voice_entry: bass
          cadence: half
```

## Schema Integration

### Data Source

`data/schemas.yaml` defines each schema:
```yaml
romanesca:
  bass_degrees: [1, 7, 6, 3]
  soprano_degrees: [1, 5, 1, 1]
  durations: [1/4, 1/4, 1/4, 1/4]
  bars: 1
  opening: true
```

Key fields:
- `bass_degrees` — scale degrees for bass voice (1-7, or dict with `degree` and `alter`)
- `soprano_degrees` — scale degrees for soprano voice
- `durations` — note durations as fractions (sum equals `bars` worth of time)
- `bars` — base duration in bars (always 1 in current file)

### Altered Degrees

Some schemas contain chromatic alterations:
```yaml
indugio:
  bass_degrees: [4, 4, {degree: 4, alter: 1}, 5]  # raised 4th
  soprano_degrees: [2, 4, 6, 7]

quiescenza:
  soprano_degrees: [{degree: 7, alter: -1}, 6, {degree: 7, alter: 1}, 1]  # b7, 6, #7, 1
```

The builder must handle both formats:
```python
def extract_degree(d: int | dict) -> tuple[int, int]:
    """Return (degree, alteration) where alteration is semitones."""
    if isinstance(d, dict):
        return d["degree"], d.get("alter", 0)
    return d, 0
```

### Duration Stretching

`SchemaSlot.bars` is a multiplier on the schema's base `bars`:

```
actual_duration[i] = schema.durations[i] × (slot.bars / schema.bars)
```

Example: romanesca with `slot.bars: 2`:
```
schema.durations: [1/4, 1/4, 1/4, 1/4]  # sum = 1 bar
schema.bars: 1

stretched durations: [1/2, 1/2, 1/2, 1/2]  # sum = 2 bars
```

The skeleton (degree sequence) stays identical; only timing changes.

## Voice Generation Pipeline

### Step 1: Load and Stretch Schema

```python
def load_stretched_schema(schema_type: str, target_bars: int) -> dict:
    """Load schema from YAML and stretch to target bars."""
    schema = SCHEMAS[schema_type]
    base_bars = schema.get("bars", 1)
    multiplier = Fraction(target_bars, base_bars)
    
    return {
        "bass_degrees": schema["bass_degrees"],
        "soprano_degrees": schema["soprano_degrees"],
        "durations": [parse_fraction(d) * multiplier for d in schema["durations"]],
    }
```

### Step 2: Realise Outer Voices

Convert scale degrees to diatonic pitches:

```python
def realise_voice(degrees: list, durations: list, octave: int, mode: str) -> Notes:
    """Convert scale degrees to diatonic pitches in given octave."""
    pitches = []
    for d in degrees:
        degree, alter = extract_degree(d)
        # degree 1-7 → diatonic pitch in octave
        diatonic = (degree - 1) + (octave * 7)
        # alter applied later during MIDI conversion (chromatic adjustment)
        pitches.append((diatonic, alter))
    return Notes(pitches, durations)
```

### Step 3: Apply Texture Rules

The `texture` field determines how subject and schema interact:

| Texture | Soprano Source | Bass Source |
|---------|----------------|-------------|
| `imitative` | subject (with treatment) | schema bass_degrees |
| `melody_bass` | schema soprano_degrees | schema bass_degrees |
| `free` | subject | functional bass from harmony |

For `imitative` texture:
1. The `voice_entry` voice carries the subject (transformed by `treatment`)
2. The other outer voice uses schema degrees
3. Voices may swap roles mid-schema for stretto

### Step 4: Apply Treatment to Subject

The 5 contrapuntal treatments transform the subject:

| Treatment | Transform |
|-----------|-----------|
| `statement` | literal subject |
| `imitation` | subject at fifth (transpose +4 degrees) |
| `sequence` | subject transposed by step |
| `inversion` | melodic inversion around pivot |
| `stretto` | overlapped entries (special handling) |

```python
def apply_treatment(subject: Notes, treatment: str, voice_entry: str) -> Notes:
    """Apply contrapuntal treatment to subject."""
    if treatment == "statement":
        return subject
    if treatment == "imitation":
        # Transpose by fifth (4 scale degrees)
        interval = 4 if voice_entry == "bass" else -4
        return transpose_degrees(subject, interval)
    if treatment == "inversion":
        pivot = (min(subject.pitches) + max(subject.pitches)) // 2
        return invert_around(subject, pivot)
    if treatment == "sequence":
        return transpose_degrees(subject, 1)
    # stretto handled separately
    return subject
```

### Step 5: Generate Inner Voices

Inner voices (alto, tenor) generated by existing CP-SAT solver. Harmony is implicit in schema — derive chord sequence from bass degrees:

```python
DEGREE_TO_CHORD = {1: "I", 2: "ii", 3: "iii", 4: "IV", 5: "V", 6: "vi", 7: "vii"}

def schema_to_harmony(bass_degrees: list, durations: list, bar_duration: Fraction) -> tuple[str, ...]:
    """Derive one chord per bar from bass degrees."""
    harmony = []
    current_pos = Fraction(0)
    current_bar = 0
    
    for degree, dur in zip(bass_degrees, durations):
        bar_idx = int(current_pos // bar_duration)
        if bar_idx >= len(harmony):
            deg, _ = extract_degree(degree)
            harmony.append(DEGREE_TO_CHORD.get(deg, "I"))
        current_pos += dur
    
    return tuple(harmony)
```

### Step 6: Apply Cadence (if specified)

When `SchemaSlot.cadence` is set, override final degrees with cadence formula from `data/cadences.yaml`:

```python
def apply_cadence(soprano: Notes, bass: Notes, cadence_type: str) -> tuple[Notes, Notes]:
    """Replace final events with cadence formula."""
    if cadence_type is None:
        return soprano, bass
    
    formula = CADENCES[cadence_type]
    # Replace last N events where N = len(formula)
    # Cadence formulas define soprano and bass degree sequences
    ...
```

## Handler Registration

### New Handler

Register `schemas` handler in `handlers/structure.py`:

```python
@register('schemas', '*')
def handle_schemas(node: Node) -> Node:
    """Process schema slots into voiced bars."""
    metre = _get_metre(node)
    bar_duration = _parse_metre(metre)
    results = []
    
    for schema_slot in node.children:
        built = _build_schema_slot(schema_slot, node, bar_duration)
        results.append(built)
    
    return node.with_children(tuple(results))
```

### Dispatch Logic

Check for `schemas` key before falling back to `episodes`:

```python
def _build_section(section: Node, ...) -> Node:
    if "schemas" in section:
        return _build_from_schemas(section, ...)
    if "episodes" in section:
        return _build_from_episodes(section, ...)  # deprecated path
    raise ValueError("Section needs schemas or episodes")
```

## File Changes

### Create

| File | Purpose |
|------|---------|
| `builder/domain/schema_ops.py` | Load schemas.yaml, stretch durations, extract voices |
| `builder/handlers/schema_handler.py` | Orchestrate schema → notes pipeline |

### Modify

| File | Change |
|------|--------|
| `builder/handlers/structure.py` | Add `@register('schemas', '*')` handler |
| `builder/types.py` | Add `SchemaContext` dataclass |
| `builder/adapters/tree_reader.py` | Add `extract_schema_slot()` |

### Deprecate

| File | Reason |
|------|--------|
| `builder/handlers/phrase_handler.py` | Replaced by schema_handler |
| `builder/domain/harmony_ops.py` | Harmony now from schema, not computed |

## Data Flow

```
plan.yaml (schema-based)
         │
         ▼
┌─────────────────────────┐
│ tree_reader             │  Parse YAML into Node tree
│ extract_schema_slot()   │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ schema_ops              │  
│ load_stretched_schema() │  Load from schemas.yaml, stretch durations
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ schema_handler          │
│ realise_outer_voices()  │  Degrees → diatonic pitches
│ apply_treatment()       │  Transform subject per texture
│ apply_cadence()         │  Override final degrees if cadence set
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ structure.py            │
│ generate_voice_cpsat()  │  Fill inner voices (existing solver)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ tree elaboration        │  Create bar nodes, collect notes
└────────────┬────────────┘
             │
             ▼
        .note file
```

## Module: schema_ops.py

```python
"""Schema operations: load, stretch, realise."""
from fractions import Fraction
from pathlib import Path
import yaml

DATA_DIR = Path(__file__).parent.parent.parent / "data"
_SCHEMAS: dict | None = None


def load_schemas() -> dict:
    """Load schemas from data/schemas.yaml (cached)."""
    global _SCHEMAS
    if _SCHEMAS is None:
        path = DATA_DIR / "schemas.yaml"
        assert path.exists(), f"Missing {path}"
        with open(path, encoding="utf-8") as f:
            _SCHEMAS = yaml.safe_load(f)
    return _SCHEMAS


def get_schema(name: str) -> dict:
    """Get schema by name."""
    schemas = load_schemas()
    assert name in schemas, f"Unknown schema: {name}. Valid: {sorted(schemas.keys())}"
    return schemas[name]


def stretch_schema(schema: dict, target_bars: int) -> dict:
    """Stretch schema durations to fill target_bars."""
    base_bars = schema.get("bars", 1)
    multiplier = Fraction(target_bars, base_bars)
    stretched = [_parse_duration(d) * multiplier for d in schema["durations"]]
    return {
        "bass_degrees": schema["bass_degrees"],
        "soprano_degrees": schema["soprano_degrees"],
        "durations": stretched,
        "bars": target_bars,
    }


def extract_degree(d: int | dict) -> tuple[int, int]:
    """Extract (degree, alteration) from degree spec."""
    if isinstance(d, dict):
        return d["degree"], d.get("alter", 0)
    return d, 0


def _parse_duration(d: str | Fraction | int) -> Fraction:
    """Parse duration to Fraction."""
    if isinstance(d, Fraction):
        return d
    if isinstance(d, str) and "/" in d:
        num, den = d.split("/")
        return Fraction(int(num), int(den))
    return Fraction(d)
```

## Module: schema_handler.py

```python
"""Schema-level voice generation."""
from fractions import Fraction
from builder.domain.schema_ops import get_schema, stretch_schema, extract_degree
from builder.domain.material_ops import convert_degrees_to_diatonic
from builder.adapters.tree_reader import extract_subject
from builder.tree import Node
from builder.types import Notes
from shared.constants import DIATONIC_DEFAULTS

DEGREE_TO_CHORD = {1: "I", 2: "ii", 3: "iii", 4: "IV", 5: "V", 6: "vi", 7: "vii"}


def compute_schema_voices(
    schema_node: Node,
    root: Node,
    bar_duration: Fraction,
) -> tuple[Notes, Notes, tuple[str, ...]]:
    """Compute soprano, bass, and harmony for schema slot.
    
    Returns:
        (soprano_notes, bass_notes, harmony_per_bar)
    """
    schema_type = schema_node["type"].value
    target_bars = schema_node["bars"].value
    texture = schema_node["texture"].value
    treatment = schema_node["treatment"].value
    voice_entry = schema_node["voice_entry"].value
    cadence = schema_node["cadence"].value if "cadence" in schema_node else None
    
    # Load and stretch
    schema = get_schema(schema_type)
    stretched = stretch_schema(schema, target_bars)
    
    # Realise outer voices based on texture
    if texture == "imitative":
        soprano, bass = _realise_imitative(
            stretched, root, treatment, voice_entry
        )
    else:
        soprano, bass = _realise_homophonic(stretched)
    
    # Apply cadence override
    if cadence:
        soprano, bass = _apply_cadence(soprano, bass, cadence, bar_duration)
    
    # Derive harmony from bass
    harmony = _bass_to_harmony(stretched["bass_degrees"], stretched["durations"], bar_duration)
    
    return soprano, bass, harmony


def _realise_imitative(
    schema: dict,
    root: Node,
    treatment: str,
    voice_entry: str,
) -> tuple[Notes, Notes]:
    """Realise voices for imitative texture."""
    subject = extract_subject(root)
    soprano_octave = DIATONIC_DEFAULTS["soprano"] // 7
    bass_octave = DIATONIC_DEFAULTS["bass"] // 7
    
    # Schema skeleton for non-subject voice
    soprano_skeleton = _degrees_to_notes(
        schema["soprano_degrees"], schema["durations"], soprano_octave
    )
    bass_skeleton = _degrees_to_notes(
        schema["bass_degrees"], schema["durations"], bass_octave
    )
    
    if subject is None:
        return soprano_skeleton, bass_skeleton
    
    # Apply treatment to subject
    treated = _apply_treatment(subject.notes, treatment)
    treated_pitched = convert_degrees_to_diatonic(
        treated, soprano_octave if voice_entry == "soprano" else bass_octave
    )
    
    if voice_entry == "soprano":
        return treated_pitched, bass_skeleton
    else:
        return soprano_skeleton, treated_pitched


def _realise_homophonic(schema: dict) -> tuple[Notes, Notes]:
    """Realise voices for melody_bass texture."""
    soprano_octave = DIATONIC_DEFAULTS["soprano"] // 7
    bass_octave = DIATONIC_DEFAULTS["bass"] // 7
    
    soprano = _degrees_to_notes(
        schema["soprano_degrees"], schema["durations"], soprano_octave
    )
    bass = _degrees_to_notes(
        schema["bass_degrees"], schema["durations"], bass_octave
    )
    return soprano, bass


def _degrees_to_notes(degrees: list, durations: list, octave: int) -> Notes:
    """Convert scale degrees to Notes in octave."""
    pitches = []
    for d in degrees:
        deg, alter = extract_degree(d)
        # degree 1 → diatonic 0 in octave
        diatonic = (deg - 1) + (octave * 7)
        # TODO: store alter for chromatic adjustment in MIDI export
        pitches.append(diatonic)
    return Notes(tuple(pitches), tuple(durations))


def _apply_treatment(subject: Notes, treatment: str) -> Notes:
    """Apply contrapuntal treatment."""
    if treatment == "statement":
        return subject
    if treatment == "imitation":
        # Transpose by fifth (4 degrees)
        return Notes(
            tuple(p + 4 for p in subject.pitches),
            subject.durations,
        )
    if treatment == "inversion":
        pivot = (min(subject.pitches) + max(subject.pitches)) // 2
        return Notes(
            tuple(2 * pivot - p for p in subject.pitches),
            subject.durations,
        )
    if treatment == "sequence":
        return Notes(
            tuple(p + 1 for p in subject.pitches),
            subject.durations,
        )
    return subject


def _bass_to_harmony(
    bass_degrees: list,
    durations: list[Fraction],
    bar_duration: Fraction,
) -> tuple[str, ...]:
    """Derive one chord per bar from bass."""
    harmony = []
    pos = Fraction(0)
    
    for degree, dur in zip(bass_degrees, durations):
        bar_idx = int(pos // bar_duration)
        if bar_idx >= len(harmony):
            deg, _ = extract_degree(degree)
            harmony.append(DEGREE_TO_CHORD.get(deg, "I"))
        pos += dur
    
    return tuple(harmony)


def _apply_cadence(
    soprano: Notes,
    bass: Notes,
    cadence_type: str,
    bar_duration: Fraction,
) -> tuple[Notes, Notes]:
    """Apply cadence formula to final events."""
    # TODO: load from data/cadences.yaml
    # For now, pass through
    return soprano, bass
```

## Testing

1. Create test schema-based plan:
```yaml
frame:
  key: C
  mode: major
  metre: 4/4
  voices: 2

material:
  subject:
    degrees: [1, 2, 3, 4, 5]
    durations: [1/8, 1/8, 1/8, 1/8, 1/2]

structure:
  sections:
    - label: A
      key_area: I
      schemas:
        - type: romanesca
          bars: 2
          texture: imitative
          treatment: statement
          voice_entry: soprano
```

2. Run builder:
```bash
python -m builder test_schema_plan.yaml
```

3. Verify:
   - Soprano follows subject (statement treatment)
   - Bass follows romanesca bass_degrees [1, 7, 6, 3]
   - Durations stretched to 2 bars: [1/2, 1/2, 1/2, 1/2]
   - Output .note file has correct pitches and timings

## Migration

During transition, support both formats:
```python
if "schemas" in section:
    return handle_schemas(section)
elif "episodes" in section:
    return handle_episodes(section)  # deprecated
```

Remove episode path once all briefs converted.
