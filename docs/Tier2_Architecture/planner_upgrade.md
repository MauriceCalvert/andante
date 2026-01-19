# Planner Upgrade: Implementation Guide

## Overview

Convert the planner from melody-first to schema-first composition. This is a structural change affecting most planner modules.

Read first:
- `docs/Tier3_Guides/composerguide.md` — procedural guide
- `docs/Tier2_Architecture/planner_design.md` — design rationale

## Key Design Decisions

### SchemaSlot replaces Phrase (1:1)

SchemaSlot is the atomic planning unit. No sub-division into Phrases. The builder (which replaces the engine) will consume SchemaSlots directly.

Current Phrase fields map as follows:
- `bars` → `SchemaSlot.bars`
- `treatment` → `SchemaSlot.treatment` (contrapuntal only)
- `texture` → `SchemaSlot.texture`
- `tonal_target` → implicit in schema position + cadence_plan
- `cadence` → `SchemaSlot.cadence`
- `energy` → dropped (emergent from schema sequence)
- `harmony` → dropped (schema *is* the harmony)

### Treatment vocabulary: two orthogonal dimensions

| Dimension | Examples | Scope |
|-----------|----------|-------|
| Contrapuntal | statement, imitation, sequence, inversion, stretto | SchemaSlot.treatment |
| Figural | mordent, circulatio, groppo, anabasis | Builder concern, not planner |

The planner specifies only contrapuntal treatments (5 options). The 21 figural treatments in treatments.yaml are surface decoration applied by the builder based on affect + schema + treatment.

### Schema bar counts

`bars: 1` in schemas.yaml is the base unit. `SchemaSlot.bars = 2` means stretch: double all durations. A romanesca (4 bass degrees over 1 bar) becomes 4 bass degrees over 2 bars.

This matches baroque practice — same schema skeleton at different tempos/densities.

### Subject derivation

New functionality required. If no subject provided:
1. Take opening schema's soprano_degrees
2. Apply rhythmic profile from genre template (e.g., invention = motoric eighths)
3. Ensure result is invertible and answerable

Spec this in Phase 4 below.

### No engine compatibility needed

The engine will be replaced by builder. The planner outputs schema-based YAML; builder consumes it directly. No translation layer required.

## Files to Modify

### Delete (functionality absorbed elsewhere)
- `planner/episode_generator.py` — replaced by schema_generator
- `planner/macro_form.py` — replaced by cadence_planner + schema_generator
- `planner/section_planner.py` — replaced by schema_generator
- `planner/transition.py` — transitions become schema selections

### Create New
- `planner/cadence_planner.py` — cadence plan from frame + genre
- `planner/schema_generator.py` — schema chain from cadence plan
- `planner/schema_loader.py` — load and query schemas.yaml
- `planner/subject_validator.py` — validate subject against schema
- `planner/subject_deriver.py` — derive subject from opening schema

### Already Created
- `data/schema_transitions.yaml` — validated transition graph (see below)

### Modify
- `planner/planner.py` — new orchestration order
- `planner/structure.py` — output schema-based structure
- `planner/plannertypes.py` — new types for schemas
- `planner/serializer.py` — emit new YAML structure
- `data/genres/*.yaml` — add schema preferences per genre

## Schema Transition Graph

The file `data/schema_transitions.yaml` contains a validated transition graph based on:
- Gjerdingen (2007) *Music in the Galant Style* — defines functional roles and transitional probabilities (p. 372)
- Rabinovitch & Carter-Enyi (2024) "Melodic Organization and Sequential Ordering of Galant Schemata" — analysed 27 galant expositions from 1740s, identified 5-stage formal trajectory
- Open Music Theory and partimenti.org sources

Key patterns from the research:

**Formal stages (Rabinovitch & Carter-Enyi):**
1. Opening: romanesca, do_re_mi, meyer, sol_fa_mi
2. Riposte: prinner (appears in almost all expositions)
3. Post-riposte: half_cadence, comma
4. Middle: modulating_prinner, fonte, monte, passo_indietro
5. Final: passo_indietro → complete_cadence

**Documented pairs:**
- romanesca → prinner (archetypal)
- meyer → prinner
- prinner → half_cadence
- fonte → fonte (sequential repetition)
- modulating_prinner → passo_indietro → complete_cadence

The schema_generator should use `allowed_next` from schema_transitions.yaml to constrain valid successors.

## Implementation Order

### Phase 1: Types and Data

**1.1 Update plannertypes.py**

Add:
```python
@dataclass(frozen=True)
class CadencePoint:
    bar: int
    type: str  # half, authentic, deceptive, phrygian
    target: str  # I, V, vi, etc.

@dataclass(frozen=True)
class SchemaSlot:
    type: str  # romanesca, prinner, fonte, etc.
    bars: int
    texture: str  # imitative, melody_bass, free
    treatment: str  # statement, imitation, sequence, inversion, stretto
    voice_entry: str  # soprano, bass
    cadence: str | None  # if this schema ends on a cadence

@dataclass(frozen=True)
class SectionSchema:
    label: str
    key_area: str
    cadence_plan: tuple[CadencePoint, ...]
    schemas: tuple[SchemaSlot, ...]

@dataclass(frozen=True)
class SubjectValidation:
    valid: bool
    invertible: bool
    answerable: bool
    errors: tuple[str, ...]
```

Remove or deprecate: `Episode`, `Phrase`, `EpisodeSpec`, `MacroSection`, `MacroForm`, `SectionPlan`.

**1.2 Create schema_loader.py**

```python
"""Load and query schema definitions."""

def load_schemas() -> dict[str, Schema]:
    """Load all schemas from data/schemas.yaml."""

def load_transitions() -> dict[str, list[str]]:
    """Load allowed_next from data/schema_transitions.yaml."""

def get_opening_schemas(mode: str) -> list[str]:
    """Return schema names valid for opening."""
    # Filter by typical_position == 'opening' in schema_transitions.yaml

def get_allowed_next(schema_name: str) -> list[str]:
    """Return valid successor schemas."""

def get_schema_bars(schema_name: str) -> int:
    """Return base bar count for schema (from schemas.yaml)."""

def schema_fits_mode(schema_name: str, mode: str) -> bool:
    """Check if schema works in given mode."""
```

**1.3 Update data/genres/*.yaml**

Add to each genre file:
```yaml
schema_preferences:
  opening: [romanesca, do_re_mi]
  continuation: [fonte, monte, fenaroli]
  cadential: [prinner, sol_fa_mi]
  
cadence_template:
  density: high  # high=every 2-4 bars, medium=every 4-8, low=every 8+
  section_end: half
  final: authentic

texture: imitative  # or melody_bass

subject_rhythm:
  pattern: [1/8, 1/8, 1/8, 1/8]  # For subject derivation
  style: motoric  # or lyrical
```

### Phase 2: Cadence Planning

**2.1 Create cadence_planner.py**

```python
"""Plan cadence points from frame and genre."""

def plan_cadences(
    frame: Frame,
    genre: str,
    total_bars: int,
) -> tuple[CadencePoint, ...]:
    """Generate cadence plan for piece.
    
    Rules:
    - Final bar: authentic to I
    - Section boundaries: half or authentic
    - Density from genre template
    - Minor mode: may use phrygian half cadence
    """

def plan_section_cadences(
    section_bars: int,
    key_area: str,
    density: str,
    is_final: bool,
) -> tuple[CadencePoint, ...]:
    """Generate cadences for one section."""
```

### Phase 3: Schema Generation

**3.1 Create schema_generator.py**

```python
"""Generate schema chain from cadence plan."""

def generate_schema_chain(
    cadence_plan: tuple[CadencePoint, ...],
    genre: str,
    mode: str,
    total_bars: int,
    seed: int | None = None,
) -> tuple[SchemaSlot, ...]:
    """Fill bars between cadences with schemas.
    
    Algorithm:
    1. Start with opening schema (from genre preferences)
    2. Select next schema from allowed_next (schema_transitions.yaml)
    3. Approach each cadence with pre-cadential schema
    4. Assign texture per genre, treatment per position
    5. Ensure chain lands on all cadence points
    """

def select_schema(
    position: str,  # opening, continuation, pre_cadential
    prev_schema: str | None,
    mode: str,
    available_bars: int,
    history: list[str],
    genre_prefs: dict,
    rng: random.Random,
) -> str:
    """Select next schema in chain.
    
    Constraints (in order):
    1. Must be in allowed_next of prev_schema (if any)
    2. Prefer genre preferences for position
    3. Max 2 repetitions of same schema
    4. Fits available bars
    """

def assign_treatment(
    schema_type: str,
    position_in_section: int,
    texture: str,
) -> str:
    """Assign contrapuntal treatment.
    
    Rules:
    - First schema in section: statement
    - After opening in imitative texture: imitation
    - Sequential schemas (fonte, monte): sequence
    - Can use inversion/stretto for variety
    """
```

### Phase 4: Subject Handling

**4.1 Create subject_validator.py**

```python
"""Validate subject against opening schema."""

def validate_subject(
    subject: Motif,
    opening_schema: str,
    mode: str,
) -> SubjectValidation:
    """Check subject fits schema and is useable.
    
    Checks:
    1. First degree consonant with schema bass (1, 3, or 5)
    2. Last degree allows continuation (not on strong closure)
    3. Invertible (intervals stay consonant when flipped)
    4. Answerable at fifth (transposition stays in mode)
    """

def check_invertibility(degrees: list[int]) -> tuple[bool, str]:
    """Check if subject inverts cleanly.
    
    Inversion: degree d -> (tonic * 2) - d
    For each interval in original, check inverted interval is consonant.
    Consonant: unison, 3rd, 5th, 6th, octave
    Dissonant: 2nd, 7th, tritone
    """

def check_answerability(
    degrees: list[int],
    mode: str,
) -> tuple[bool, str]:
    """Check if subject answers at fifth.
    
    Answer: transpose up a fifth (degree + 4, mod 7)
    Check that no accidentals outside mode are required.
    In major: 4 -> 1 is tonal answer (not 4 -> #7)
    """

def check_schema_fit(
    subject_degrees: list[int],
    schema_name: str,
) -> tuple[bool, str]:
    """Check subject first/last degrees align with schema soprano."""
```

**4.2 Create subject_deriver.py**

```python
"""Derive subject from opening schema when none provided."""

def derive_subject(
    opening_schema: str,
    frame: Frame,
    genre: str,
) -> Motif:
    """Create subject from schema's soprano degrees.
    
    Steps:
    1. Get soprano_degrees from schema definition
    2. Get rhythm pattern from genre's subject_rhythm
    3. Combine: each degree gets duration from pattern
    4. Validate invertibility and answerability
    5. If invalid, adjust (e.g., avoid tritone leaps)
    """

def apply_rhythm_pattern(
    degrees: list[int],
    pattern: list[str],
    style: str,
) -> tuple[list[int], list[str]]:
    """Apply rhythmic pattern to scale degrees.
    
    May repeat/subdivide degrees to fit pattern length.
    Style 'motoric': even values, continuous motion
    Style 'lyrical': varied values, rests allowed
    """
```

### Phase 5: Planner Integration

**5.1 Rewrite planner.py**

New orchestration order:
```python
def build_plan(brief: Brief, ...) -> Plan:
    # 1. Frame (unchanged)
    frame = resolve_frame(brief)
    
    # 2. Cadence plan (NEW)
    cadence_plan = plan_cadences(frame, brief.genre, brief.bars)
    
    # 3. Schema chain (NEW)
    schema_chain = generate_schema_chain(
        cadence_plan, brief.genre, frame.mode, brief.bars, seed
    )
    
    # 4. Subject handling (NEW)
    if user_motif:
        validation = validate_subject(user_motif, schema_chain[0].type, frame.mode)
        assert validation.valid, f"Subject invalid: {validation.errors}"
        material = Material(subject=user_motif, ...)
    else:
        subject = derive_subject(schema_chain[0].type, frame, brief.genre)
        material = Material(subject=subject, ...)
    
    # 5. Build structure from schemas (CHANGED)
    structure = build_structure_from_schemas(schema_chain, cadence_plan)
    
    # 6. Validate and return
    ...
```

**5.2 Rewrite structure.py**

Replace `plan_structure()` and `plan_structure_from_macro()` with:
```python
def build_structure_from_schemas(
    schema_chain: tuple[SchemaSlot, ...],
    cadence_plan: tuple[CadencePoint, ...],
) -> Structure:
    """Build Structure from schema chain.
    
    Group schemas into sections based on cadence points.
    Each section ends at a cadence.
    """
```

Remove `generate_period()`, `generate_sentence()` — classical forms, not baroque.

**5.3 Update serializer.py**

Emit new YAML structure:
```yaml
structure:
  sections:
    - label: A
      key_area: I
      cadence_plan:
        - bar: 4
          type: half
          target: V
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

### Phase 6: Genre Updates

Update each `data/genres/*.yaml` to specify:
- `schema_preferences`
- `cadence_template`
- `texture`
- `subject_rhythm`

Remove:
- `episodes` lists
- `tonal_path` (replaced by cadence_plan)
- `arc` references (schemas determine arc)

### Phase 7: Cleanup

Delete:
- `planner/episode_generator.py`
- `planner/macro_form.py`
- `planner/section_planner.py`
- `planner/transition.py`
- `data/episode_constraints.yaml`
- `data/fantasia_arcs.yaml`
- `data/arcs.yaml` (if no longer needed)

Update tests to use new structure.

## Testing

**Test case:** `briefs/builder/freude_invention.brief`

Before: outputs episodes with phrases, harmony per phrase
After: outputs schema chain with cadence plan

Run:
```bash
python -m planner briefs/builder/freude_invention.brief
```

Compare output structure. The bar count should match; the internal representation changes.

## Constraints Checklist

Hard constraints (must implement):
- [ ] Schema chain lands on all cadence points
- [ ] Each schema successor is in allowed_next of predecessor
- [ ] Subject fits opening schema (if provided)
- [ ] Subject is invertible and answerable
- [ ] Final cadence is authentic to I

Soft constraints (prefer):
- [ ] Max 2 repetitions of same schema
- [ ] Prefer genre schema_preferences for each position
- [ ] Match typical_position from schema_transitions.yaml

## References

- `data/schema_transitions.yaml` — validated transition graph with sources
- Gjerdingen (2007) *Music in the Galant Style*
- Rabinovitch & Carter-Enyi (2024) MTO 30.1
