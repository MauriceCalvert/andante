# Tonal Planning Upgrade

## Status

Draft | Upgrade from stub to algorithmic tonal planning

---

## Problem Statement

Layer 2 (tonal.py) and Layer 3 (schematic.py) are currently pass-through stubs:

- Layer 2 returns `tonal_path` verbatim from affect config
- Layer 3 reads `schema_sequence` literally from genre YAML
- No algorithmic selection of keys, schemas, or cadences
- No enforcement of variety rules
- Hierarchical anchors (section, piece level) are absent

This upgrade makes tonal planning generative while respecting existing data structures.

---

## Design Principles

1. **Schema transitions graph is authoritative.** All schema selection must respect `schema_transitions.yaml`.
2. **Variety rules are hard constraints.** V-T001 through V-T004 from `tonal_planning.md` are non-negotiable.
3. **RNG in planner only.** Per A005, randomness lives here; downstream is deterministic.
4. **Validate, don't fix.** Per D001, reject invalid configurations rather than silently correcting.
5. **Single source of truth.** Per L017, no duplication of schema definitions or transition rules.

---

## Architecture Overview

```
Layer 2: Tonal Planning
├── Input: FormConfig, AffectConfig, GenreConfig
├── Process:
│   ├── Compute tonal regions from form structure
│   ├── Assign key areas to sections
│   └── Determine modulation pivot points
└── Output: TonalPlan (key areas, pivot bars, modality)

Layer 3: Schematic Planning  
├── Input: TonalPlan, GenreConfig, schemas dict
├── Process:
│   ├── For each section: select schema chain
│   ├── Allocate cadence types to phrase boundaries
│   └── Mark free passages where bass continuity fails
└── Output: SchemaChain (schemas, key_areas, cadences, free_passages)

Layer 4: Anchor Generation (existing schema_anchors.py, extended)
├── Input: SchemaChain, home_key, metre
├── Process:
│   ├── Generate piece-level anchors (tonic departure/return)
│   ├── Generate section-level anchors (cadence targets)
│   └── Generate phrase-level anchors (schema stages)
└── Output: List[Anchor] at three hierarchical levels
```

---

## Layer 2: Tonal Planning

### New Data Structure

```python
@dataclass(frozen=True)
class TonalPlan:
    """Output of Layer 2: tonal regions and pivot points."""
    sections: tuple[SectionTonalPlan, ...]
    home_key: str                    # e.g., "C major"
    modality: str                    # "diatonic" or "chromatic"
    density: str                     # "high", "medium", "low"


@dataclass(frozen=True)
class SectionTonalPlan:
    """Tonal plan for a single section."""
    name: str                        # Section name from genre
    start_bar: int
    end_bar: int
    key_area: str                    # Roman numeral relative to home
    cadence_type: str                # "authentic", "half", "deceptive", "open"
    pivot_bar: int | None            # Bar where modulation occurs (if any)
```

### Algorithm: Key Area Assignment

Input: `FormConfig`, `AffectConfig`, `GenreConfig`

```
1. Parse sections from GenreConfig
2. For each section, determine key area:
   
   Section position    | Default key area | Alternatives (RNG)
   --------------------|------------------|--------------------
   First               | I                | (none)
   Middle (odd index)  | V                | IV, vi
   Middle (even index) | IV               | ii, vi  
   Penultimate         | V                | (none, dominant prep)
   Final               | I                | (none)

3. Apply affect modifiers:
   - "chromatic" modality → allow secondary dominants at pivots
   - "high" density → more frequent modulations
   - "low" density → fewer modulations, longer tonal regions

4. Validate tonal path:
   - No consecutive identical non-tonic keys (V-T004)
   - Return to I before piece end
   - Modulations use valid pivot chords
```

### Algorithm: Cadence Type Assignment

```
1. Section endings get cadence types based on position:
   
   Section type        | Cadence type
   --------------------|---------------
   Final section       | authentic
   Penultimate         | half OR authentic
   Interior sections   | half, deceptive, or open
   First section       | open OR half

2. Apply variety rule V-T003:
   - No more than one authentic cadence per piece except final
   - Interior cadences must vary (no two consecutive half cadences)

3. Cadence strength follows from:
   - Position: downbeat > upbeat
   - Duration: longer notes > shorter
   - Voice leading: 7→1 soprano + 5→1 bass = strongest
```

---

## Layer 3: Schematic Planning

### Enhanced SchemaChain

```python
@dataclass(frozen=True)
class SchemaChain:
    """Output of Layer 3: schema sequence with full metadata."""
    schemas: tuple[str, ...]
    key_areas: tuple[str, ...]
    cadences: tuple[str | None, ...]     # Cadence type at each schema end
    free_passages: frozenset[tuple[int, int]]
    section_boundaries: tuple[int, ...]  # Schema indices where sections end
```

### Algorithm: Schema Selection

For each section in TonalPlan:

```
1. Determine required schema positions:
   
   Section function     | Required positions
   ---------------------|--------------------
   Opening (exordium)   | opening → riposte
   Continuation         | continuation (sequential allowed)
   Development          | continuation → pre_cadential
   Cadential            | pre_cadential → cadential
   Post-cadential       | post_cadential (optional)

2. Select opening schema:
   - Filter schemas where position == "opening"
   - Apply V-T002: opening schemas only in first phrase of sections
   - RNG choice from valid candidates

3. Select successor schemas via graph walk:
   
   FUNCTION select_next(current_schema, remaining_bars, target_cadence):
       candidates = get_allowed_next(current_schema)  # From transitions YAML
       
       # Filter by fit
       candidates = [s for s in candidates if schema_fits_bars(s, remaining_bars)]
       
       # Filter by variety (V-T001)
       candidates = [s for s in candidates if s != current_schema]
       
       # Prioritise by target
       IF target_cadence == "authentic":
           prefer cadential schemas (cadenza_semplice, cadenza_composta)
       ELIF target_cadence == "half":
           prefer half_cadence or ponte → half_cadence
       
       # RNG choice with weights
       RETURN weighted_choice(candidates, weights_by_position)

4. Walk until section budget exhausted:
   
   schemas = [opening_schema]
   bars_used = opening_schema.min_bars
   
   WHILE bars_used < section_bars:
       next_schema = select_next(schemas[-1], section_bars - bars_used, cadence_type)
       schemas.append(next_schema)
       bars_used += next_schema.min_bars
   
   # Verify cadential closure
   IF cadence_type in ("authentic", "half"):
       ASSERT schemas[-1].position in ("cadential", "pre_cadential")

5. Mark free passages:
   FOR i in range(len(schemas) - 1):
       IF NOT can_connect_direct(schemas[i], schemas[i+1]):
           free_passages.add((i, i+1))
```

### Bass Continuity Rules (from schema_transitions.yaml)

| Exit bass | Valid entry bass | Connection type |
|-----------|------------------|-----------------|
| 1         | 1, 2, 7          | Direct          |
| 1         | 4, 5             | Free passage    |
| 3         | 4, 2             | Direct (step)   |
| 3         | 1, 5, 7          | Free passage    |
| 5         | 1, 4, 6          | Direct          |
| 5         | 2, 3, 7          | Free passage    |

Free passages are 1-2 bars of counterpoint bridging incompatible bass degrees.

---

## Layer 4: Hierarchical Anchors

### Three Anchor Levels

**Level 1: Piece-level anchors**
- First downbeat: tonic (I)
- Final cadence target: tonic (I)
- Major structural pivots (e.g., dominant arrival before return)

**Level 2: Section-level anchors**
- Section cadence targets
- Key area boundaries
- Pivot chord moments

**Level 3: Phrase-level anchors**
- Schema stage arrivals (existing implementation)
- One anchor per stage per schema

### Anchor Generation Algorithm

```
FUNCTION generate_hierarchical_anchors(schema_chain, tonal_plan, home_key, metre):
    anchors = []
    
    # Level 1: Piece anchors
    anchors.append(Anchor(
        bar_beat="1.1",
        upper_degree=1,
        lower_degree=1,
        local_key=home_key,
        schema="piece_start",
        stage=1,
        section="piece",
    ))
    
    final_bar = sum(section.end_bar - section.start_bar + 1 for section in tonal_plan.sections)
    anchors.append(Anchor(
        bar_beat=f"{final_bar}.1",
        upper_degree=1,
        lower_degree=1,
        local_key=home_key,
        schema="piece_end",
        stage=1,
        section="piece",
    ))
    
    # Level 2: Section anchors
    FOR section in tonal_plan.sections:
        section_key = home_key.modulate_to(section.key_area)
        
        # Section start anchor
        anchors.append(Anchor(
            bar_beat=f"{section.start_bar}.1",
            upper_degree=_cadence_soprano(section.key_area, "entry"),
            lower_degree=_cadence_bass(section.key_area, "entry"),
            local_key=section_key,
            schema="section_start",
            stage=1,
            section=section.name,
        ))
        
        # Section cadence anchor
        cadence_degrees = CADENCE_DEGREES[section.cadence_type]
        anchors.append(Anchor(
            bar_beat=f"{section.end_bar}.1",
            upper_degree=cadence_degrees.soprano,
            lower_degree=cadence_degrees.bass,
            local_key=section_key if section.cadence_type != "authentic" else home_key,
            schema="section_cadence",
            stage=1,
            section=section.name,
        ))
    
    # Level 3: Phrase anchors (delegate to existing schema_anchors.py)
    schema_idx = 0
    current_bar = 1
    FOR section in tonal_plan.sections:
        WHILE schema_idx < len(schema_chain.schemas) AND current_bar <= section.end_bar:
            schema_name = schema_chain.schemas[schema_idx]
            schema_def = get_schema(schema_name)
            section_key = home_key.modulate_to(schema_chain.key_areas[schema_idx])
            
            phrase_anchors = generate_schema_anchors(
                schema_name=schema_name,
                schema_def=schema_def,
                start_bar=current_bar,
                end_bar=current_bar + schema_def.min_bars - 1,
                home_key=section_key,
                metre=metre,
                section=section.name,
            )
            anchors.extend(phrase_anchors)
            
            current_bar += schema_def.min_bars
            schema_idx += 1
    
    # Sort by bar_beat
    anchors.sort(key=lambda a: _bar_beat_to_float(a.bar_beat))
    
    RETURN anchors
```

### Cadence Target Degrees

```python
CADENCE_DEGREES = {
    "authentic": CadenceDegrees(soprano=1, bass=1),
    "half": CadenceDegrees(soprano=2, bass=5),
    "deceptive": CadenceDegrees(soprano=1, bass=6),
    "phrygian": CadenceDegrees(soprano=5, bass=6),  # Flat 6 in bass
    "open": CadenceDegrees(soprano=3, bass=1),      # No strong closure
}
```

---

## Variety Rules Implementation

### V-T001: No Adjacent Schema Repetition

```python
def validate_no_adjacent_repetition(schemas: list[str]) -> None:
    for i in range(len(schemas) - 1):
        assert schemas[i] != schemas[i + 1], (
            f"V-T001 violation: {schemas[i]} repeated at positions {i} and {i+1}"
        )
```

### V-T002: Schema Type Distribution

```python
OPENING_SCHEMAS = {"romanesca", "do_re_mi", "meyer", "sol_fa_mi"}

def validate_opening_placement(schemas: list[str], section_boundaries: list[int]) -> None:
    for i, schema in enumerate(schemas):
        if schema in OPENING_SCHEMAS:
            is_section_start = i == 0 or i in section_boundaries
            assert is_section_start, (
                f"V-T002 violation: opening schema {schema} at position {i}, "
                f"not at section boundary"
            )
```

### V-T003: Cadence Variety

```python
def validate_cadence_variety(cadences: list[str]) -> None:
    authentic_count = sum(1 for c in cadences[:-1] if c == "authentic")
    assert authentic_count <= 1, (
        f"V-T003 violation: {authentic_count} interior authentic cadences"
    )
    
    for i in range(len(cadences) - 1):
        if cadences[i] == "half" and cadences[i + 1] == "half":
            raise AssertionError(
                f"V-T003 violation: consecutive half cadences at {i} and {i+1}"
            )
```

### V-T004: Tonal Path Variety

```python
def validate_tonal_path_variety(key_areas: list[str]) -> None:
    for i in range(len(key_areas) - 1):
        if key_areas[i] != "I" and key_areas[i] == key_areas[i + 1]:
            raise AssertionError(
                f"V-T004 violation: consecutive non-tonic key {key_areas[i]} "
                f"at sections {i} and {i+1}"
            )
```

---

## File Structure

```
planner/
├── tonal.py              # Layer 2: TonalPlan generation (REWRITE)
├── schematic.py          # Layer 3: SchemaChain generation (REWRITE)
├── schema_loader.py      # Schema queries (EXISTS, extend)
├── variety.py            # Variety rule validators (NEW)
├── cadence.py            # Cadence allocation (NEW)
└── metric/
    └── schema_anchors.py # Phrase-level anchors (EXISTS, extend)

builder/
└── types.py              # Add TonalPlan, SectionTonalPlan, CadenceDegrees
```

---

## Implementation Order

### Phase 1: Data Structures
1. Add `TonalPlan`, `SectionTonalPlan` to `builder/types.py`
2. Add `CadenceDegrees` lookup to `shared/constants.py`
3. Extend `SchemaChain` with `cadences` and `section_boundaries`

### Phase 2: Layer 2 Rewrite
1. Implement key area assignment algorithm in `tonal.py`
2. Implement cadence type assignment
3. Add RNG with seed for reproducibility
4. Validate against variety rules

### Phase 3: Layer 3 Rewrite
1. Implement schema selection graph walk in `schematic.py`
2. Integrate bass continuity checking
3. Mark free passages
4. Validate against variety rules

### Phase 4: Hierarchical Anchors
1. Add piece-level anchor generation
2. Add section-level anchor generation
3. Integrate with existing phrase-level generation
4. Sort and validate anchor ordering

### Phase 5: Integration
1. Update `build_composition` to use new layers
2. End-to-end test with invention genre
3. Verify determinism with fixed seed

---

## Testing Strategy

### Unit Tests

| Test | Validates |
|------|-----------|
| `test_key_area_assignment` | Correct key areas for standard form |
| `test_cadence_assignment` | Authentic only at end, variety enforced |
| `test_schema_selection` | Valid transitions, no repetition |
| `test_bass_continuity` | Free passages marked correctly |
| `test_hierarchical_anchors` | Three levels present, sorted |
| `test_variety_rules` | V-T001 through V-T004 enforced |

### Integration Tests

| Test | Validates |
|------|-----------|
| `test_invention_generation` | Full pipeline produces valid output |
| `test_determinism` | Same seed → same output |
| `test_variety_across_seeds` | Different seeds → different schemas |

---

## Design Decisions

### 1. Affect-Weighted Schema Selection

**Decision:** Position-based weights in affect YAML.

Affects specify multipliers for schema positions rather than individual schemas. This is robust—adding a new schema automatically inherits the right weight from its position.

```yaml
# affects/energetic.yaml
position_weights:
  opening: 1.0
  riposte: 0.5
  continuation: 2.0    # Sequential schemas (monte, fonte) live here
  pre_cadential: 1.0
  cadential: 1.0
  post_cadential: 0.5

# affects/lyrical.yaml
position_weights:
  opening: 1.0
  riposte: 2.0         # Prinner, smooth descent
  continuation: 0.5
  pre_cadential: 1.5
  cadential: 1.0
  post_cadential: 1.0
```

**Implementation:**

```python
def select_schema(
    candidates: list[str],
    affect_config: AffectConfig,
    schemas: dict[str, SchemaConfig],
    rng: Random,
) -> str:
    """Select schema with position-based weighting."""
    weights: list[float] = []
    position_weights: dict[str, float] = affect_config.position_weights
    for name in candidates:
        position: str = schemas[name].position
        weight: float = position_weights.get(position, 1.0)
        weights.append(weight)
    return rng.choices(candidates, weights=weights, k=1)[0]
```

---

### 2. Free Passage Content

**Decision:** Scalar stepwise passage.

Bass walks stepwise from exit degree to entry degree over the allocated bars. Soprano moves in parallel thirds/sixths or contrary motion. Simple, predictable, historically accurate (partimento practice often used scalar bridges).

```python
@dataclass(frozen=True)
class FreePassage:
    """Scalar bridge between incompatible schemas."""
    start_bar: int
    end_bar: int
    start_bass: int      # Exit degree of preceding schema
    end_bass: int        # Entry degree of following schema
    start_soprano: int   # Exit degree of preceding schema
    end_soprano: int     # Entry degree of following schema
    motion: str          # "parallel" or "contrary"


def generate_scalar_passage(
    start_bass: int,
    end_bass: int,
    bars: int,
    home_key: Key,
) -> list[Anchor]:
    """Generate stepwise bass line from start to end degree."""
    direction: int = 1 if end_bass > start_bass else -1
    steps: int = abs(end_bass - start_bass)
    
    # Distribute steps across bars
    degrees: list[int] = []
    current: int = start_bass
    for bar_idx in range(bars):
        degrees.append(current)
        if bar_idx < steps:
            current += direction
    
    # Soprano in parallel thirds above bass
    anchors: list[Anchor] = []
    for bar_idx, bass_deg in enumerate(degrees):
        soprano_deg: int = ((bass_deg - 1 + 2) % 7) + 1  # Third above
        anchors.append(Anchor(
            bar_beat=f"{bar_idx + 1}.1",
            upper_degree=soprano_deg,
            lower_degree=bass_deg,
            local_key=home_key,
            schema="free_passage",
            stage=bar_idx + 1,
            section="bridge",
        ))
    return anchors
```

---

### 3. Schema Overlap

**Decision:** No overlap for now.

Some schemas share entry/exit points (e.g., Romanesca stage 5 = Prinner stage 1, both at soprano 6 / bass 4). Period composers exploited this to save bars. However, implementing overlap complicates:

- Bar accounting (one bar belongs to two schemas)
- Anchor generation (dual schema labels)
- Downstream processing (which schema "owns" the bar?)

**TODO:** Implement schema overlap as optimisation when bar budget is tight. Track in `future_enhancements.md`. Key requirements:

1. Detect compatible exit/entry pairs from transitions YAML ("direct" connections with identity)
2. Add `overlap_eligible: true` flag to schema pairs
3. Modify bar allocation to account for shared bars
4. Generate anchors with `schema="romanesca+prinner"` or similar compound label
5. Downstream consumers must handle compound labels

---

### 4. Sequential Schema Segment Count

**Decision:** Affect-driven.

Each affect specifies preferred segment count for sequential schemas. "Expansive" affects use 3 segments; "concise" affects use 2.

```yaml
# affects/confident.yaml
sequential_segments: 2

# affects/lyrical.yaml
sequential_segments: 3

# affects/energetic.yaml
sequential_segments: 3
```

**Implementation:**

```python
def choose_segment_count(
    schema_def: SchemaConfig,
    remaining_bars: int,
    affect_config: AffectConfig,
) -> int:
    """Choose segment count based on affect preference and bar budget."""
    preferred: int = affect_config.sequential_segments
    valid_counts: list[int] = [s for s in schema_def.segments if s <= remaining_bars]
    assert valid_counts, (
        f"No valid segment count for {schema_def.name} "
        f"with {remaining_bars} remaining bars"
    )
    # Use preferred if valid, else largest that fits
    if preferred in valid_counts:
        return preferred
    return max(valid_counts)
```

**Fallback logic:** If the preferred count exceeds bar budget, use the largest count that fits. This ensures the planner never fails due to affect preference.

---

## References

- `tonal_planning.md`: Original specification
- `schemas.yaml`: Schema definitions
- `schema_transitions.yaml`: Transition graph with proofs
- `architecture.md`: Six-layer model
- `laws.md`: Coding rules (especially A005, D001, L017)
