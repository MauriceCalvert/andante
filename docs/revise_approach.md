# Revision Plan: Schema-First Composition Pipeline

## Context

The andante builder generates weak baroque output. Analysis of `freude_invention.note` reveals five interconnected failures in the schema-first pipeline described in `docs/Tier2_Architecture/planner_design.md`.

### Current Failures

| Issue | Current Behaviour | Correct Behaviour |
|-------|-------------------|-------------------|
| Cadence plan | Half→V every 2 bars (11 consecutive) | Varied cadences articulating tonal journey |
| Key area | Equals cadence target (22 bars "in V") | Where you ARE, not where you're going |
| Modulation | None — schemas always in home key | Transpose schemas to current key area |
| Subject | Ignored — schema soprano used literally | Subject realises schema trajectory |
| Bass | Walking pattern overrides schema bass_degrees | Schema bass defines targets, CP-SAT fills gaps |

### Design Document Reference

The correct approach is specified in `docs/Tier2_Architecture/planner_design.md`. That document is sound. The implementation fails to follow it.

---

## Design Principles

1. **Determinism** — Given seed, output is identical. RNG in planner only; builder is purely deterministic.
2. **Tonal journey drives structure** — Key areas first, then cadences articulate boundaries.
3. **Schemas are skeletons** — They define voice-leading relationships (degree sequences), not literal notes.
4. **Schemas tile, never stretch** — Slot bars must be clean multiple of schema bars. No duration scaling.
5. **Subject is rhythmically invariant** — Rhythm never changed. Internal intervals preserved. Only cadential arrivals may adjust by ≤2 degrees.
6. **CP-SAT with constraints** — Schema degrees and subject entries are hard constraints; solver finds optimal passing tones around them.
7. **Separation of concerns** — Pitch from schema, rhythm from pattern, surface from subject.
8. **Fail early, degrade gracefully** — Validate in planner where possible. Runtime failures use deterministic fallback with logged warning.

---

## Failure Policy

### Principle

Fail early where possible. When runtime failure is unavoidable, use deterministic fallback with logged warning. Never produce silently degraded output.

### Case 1: Subject Incompatible with Schema Soprano

**When**: Subject rises where schema descends, or intervals too large to adjust (>2 degrees).

**Policy**: Validation in planner, not runtime failure.

Extend `validate_subject` in planner:

```python
def validate_subject(
    subject: Motif,
    opening_schema: str,
    mode: str,
) -> ValidationResult:
    """
    Checks:
    - First degree consonant with schema soprano entry
    - Contour compatibility (same general direction at phrase boundaries)
    - Arrival adjustment feasible (≤2 degrees)
    """
```

If validation fails, planner raises `SubjectValidationError`:

```
SubjectValidationError: Subject incompatible with schema 'prinner'.
Subject rises (degrees 1→5) at bar 2 beat 1, but prinner soprano descends (6→3).
Maximum adjustment exceeded (need 4 degrees, limit 2).
Suggestion: Use 'monte' schema or modify subject.
```

### Case 2: CP-SAT Timeout or Infeasible

**When**: No solution satisfies all hard constraints, or solver times out.

**Policy**: Hierarchical constraint relaxation with warning.

```python
def generate_voice_cpsat(...) -> Notes:
    # Attempt 1: All constraints
    result = _solve_with_constraints(
        schema_targets=schema_targets,
        forbid_parallels=True,
        timeout=timeout_seconds,
    )
    if result is not None:
        return result
    
    # Attempt 2: Relax parallel constraint
    logger.warning(
        f"CP-SAT: relaxing parallel 5th/8ve constraint for {voice_role}"
    )
    result = _solve_with_constraints(
        schema_targets=schema_targets,
        forbid_parallels=False,
        timeout=timeout_seconds,
    )
    if result is not None:
        return result
    
    # Attempt 3: Relax schema targets to soft constraints
    logger.warning(
        f"CP-SAT: relaxing schema targets to soft constraints for {voice_role}"
    )
    result = _solve_with_soft_targets(
        schema_targets=schema_targets,
        timeout=timeout_seconds,
    )
    if result is not None:
        return result
    
    # Attempt 4: Fallback to simple chord tones
    logger.error(
        f"CP-SAT: all relaxations failed for {voice_role}. "
        f"Falling back to chord-tone generator."
    )
    return _generate_simple_chord_tones(harmony, bar_duration, voice_role)
```

### Case 3: Tonal Section Too Short

**When**: Section shorter than minimum schema bars (e.g., 1-bar section, all schemas need ≥2).

**Policy**: Planner merges short sections automatically.

```python
def plan_tonal_journey(...) -> tuple[TonalSection, ...]:
    MIN_SECTION_BARS = 2
    
    sections = _compute_sections_from_proportions(...)
    
    merged = []
    for section in sections:
        length = section.end_bar - section.start_bar + 1
        if length < MIN_SECTION_BARS and merged:
            prev = merged[-1]
            merged[-1] = TonalSection(
                start_bar=prev.start_bar,
                end_bar=section.end_bar,
                key_area=prev.key_area,
                relationship=prev.relationship,
            )
            logger.warning(f"Merged short section ({length} bars) into previous.")
        else:
            merged.append(section)
    
    return tuple(merged)
```

### Case 4: No Valid Schema Chain

**When**: Schema transition graph has no path to cadence within bar budget.

**Policy**: Fallback to universal connector schemas.

```python
def generate_schema_chain(...) -> tuple[SchemaSlot, ...]:
    try:
        return _generate_constrained_chain(...)
    except NoValidChainError as e:
        logger.warning(f"No valid schema chain. Using fallback. Reason: {e}")
        return _generate_fallback_chain(...)

def _generate_fallback_chain(section_bars: int, key_area: str, cadence_type: str):
    """Use fenaroli + prinner/sol_fa_mi — always valid."""
    slots = []
    remaining = section_bars
    
    while remaining > 2:
        slots.append(_make_slot("fenaroli", bars=2, key_area=key_area))
        remaining -= 2
    
    cadential = "sol_fa_mi" if cadence_type == "authentic" else "prinner"
    slots.append(_make_slot(cadential, bars=remaining, key_area=key_area))
    
    return tuple(slots)
```

### Summary Table

| Failure | Phase | Policy | User Action |
|---------|-------|--------|-------------|
| Subject incompatible | Planner | Throw with suggestion | Fix brief |
| CP-SAT infeasible | Builder | Relax constraints hierarchically | Inspect logs |
| Section too short | Planner | Merge sections | None (automatic) |
| No schema chain | Planner | Fallback to universal connectors | None (automatic) |
| Invalid proportions | Planner load | Throw | Fix genre YAML |
| Unknown key area | Planner | Throw | Fix template |

### Logging Levels

- `ERROR`: Fallback used, output degraded
- `WARNING`: Constraint relaxed, output acceptable
- `INFO`: Normal operation
- `DEBUG`: Constraint solving details

---

## Phase 1: Tonal Journey Planner

### Purpose

Generate sequence of key areas before cadence planning. The tonal journey is the harmonic backbone of the piece.

### New File

`planner/tonal_planner.py`

### Data Structure

Add to `planner/plannertypes.py`:

```python
@dataclass(frozen=True)
class TonalSection:
    """A section in a single key area."""
    start_bar: int      # 1-indexed, inclusive
    end_bar: int        # 1-indexed, inclusive
    key_area: str       # Roman numeral: I, V, vi, IV, i, III, etc.
    relationship: str   # "tonic", "dominant", "relative", "subdominant"
```

### Data Files

Create `data/genres/_default.yaml`:

```yaml
# Default tonal journey for genres without explicit template
tonal_journey:
  major:
    - {proportion: 0.40, area: I, relationship: tonic}
    - {proportion: 0.30, area: V, relationship: dominant}
    - {proportion: 0.30, area: I, relationship: tonic}
  minor:
    - {proportion: 0.40, area: i, relationship: tonic}
    - {proportion: 0.25, area: III, relationship: relative}
    - {proportion: 0.35, area: i, relationship: tonic}
```

Add to `data/genres/invention.yaml`:

```yaml
tonal_journey:
  major:
    - {proportion: 0.33, area: I, relationship: tonic}
    - {proportion: 0.34, area: V, relationship: dominant}
    - {proportion: 0.33, area: I, relationship: tonic}
  minor:
    - {proportion: 0.33, area: i, relationship: tonic}
    - {proportion: 0.25, area: III, relationship: relative}
    - {proportion: 0.25, area: v, relationship: dominant}
    - {proportion: 0.17, area: i, relationship: tonic}
```

### Validation

Validate at load time:

```python
def _validate_tonal_template(
    template: list[dict],
    total_bars: int,
    mode: str,
) -> None:
    """Validate tonal journey template at load time."""
    # Sum to 1.0
    total = sum(t["proportion"] for t in template)
    assert 0.99 <= total <= 1.01, f"Proportions sum to {total}, expected 1.0"
    
    # All positive
    for t in template:
        assert t["proportion"] > 0, f"Proportion must be positive: {t}"
    
    # Valid key areas
    for t in template:
        normalised = normalise_key_area(t["area"]).upper()
        assert normalised in KEY_AREA_OFFSETS, f"Unknown key area: {t['area']}"
    
    # First and last must be tonic
    assert template[0]["area"] in ("I", "i"), "First section must be tonic"
    assert template[-1]["area"] in ("I", "i"), "Last section must be tonic"
    
    # Bar boundaries (warn if non-integer, don't fail)
    cumulative = 0.0
    for t in template:
        cumulative += t["proportion"]
        boundary = cumulative * total_bars
        if abs(boundary - round(boundary)) > 0.1:
            logger.warning(
                f"Section boundary {boundary:.2f} not integer; will round"
            )
```

### Function Signature

```python
def plan_tonal_journey(
    genre: str,
    mode: str,
    total_bars: int,
    seed: int | None = None,
) -> tuple[TonalSection, ...]:
    """
    Generate tonal journey for piece.
    
    Args:
        genre: Genre name for template lookup
        mode: 'major' or 'minor'
        total_bars: Total bars in piece
        seed: Random seed for deterministic variation
    
    Returns:
        Tuple of TonalSection covering all bars
    """
```

### Constraints

- First section must be tonic (I or i)
- Last section must be tonic (I or i)
- No adjacent sections in same key area
- Section boundaries rounded to integer bars
- Sections shorter than MIN_SECTION_BARS merged with previous

---

## Phase 2: Cadence Planner Revision

### Purpose

Place cadences at tonal section boundaries. Cadences articulate the tonal journey, not arbitrary rhythmic intervals.

### File

`planner/cadence_planner.py` — rewrite existing

### Data Structure Change

Modify `CadencePoint` in `planner/plannertypes.py`:

```python
@dataclass(frozen=True)
class CadencePoint:
    bar: int
    type: str           # "authentic", "half", "deceptive", "phrygian", "plagal"
    target: str         # Roman numeral target of cadence
    in_key_area: str    # The key area where this cadence occurs
    beat: Fraction | None = None  # None means downbeat; allows future precision
```

### Cadence Transition Data

Create `data/cadence_transitions.yaml`:

```yaml
major:
  I_to_V: half
  V_to_I: authentic
  I_to_vi: deceptive
  vi_to_IV: half
  IV_to_V: half
  IV_to_I: plagal
  I_to_IV: half
  vi_to_V: half
  vi_to_I: half
  _default: half

minor:
  i_to_III: half
  III_to_v: half
  v_to_i: authentic
  i_to_iv: half
  iv_to_V: half
  i_to_v: half
  i_to_VI: half
  VI_to_v: half
  III_to_i: authentic
  _default: half
```

When using `_default`, log warning so missing transitions can be added.

### Algorithm

Input: `tonal_sections: tuple[TonalSection, ...]`, `mode: str`, `seed: int | None`

Output: `tuple[CadencePoint, ...]`

Steps:
1. Load cadence transitions from `data/cadence_transitions.yaml`
2. For each tonal section except last:
   - Place cadence at `section.end_bar`
   - Look up cadence type for `{from_area}_to_{to_area}`
   - If not found, use `_default` and log warning
   - Set `in_key_area` to current section's key_area
3. For final section:
   - Place authentic cadence at final bar
   - Target I (or i), in_key_area is tonic

### Cadence Target Logic

```python
def _cadence_target(cadence_type: str, mode: str) -> str:
    if cadence_type == "authentic":
        return "I" if mode == "major" else "i"
    elif cadence_type == "half":
        return "V"
    elif cadence_type == "deceptive":
        return "vi" if mode == "major" else "VI"
    elif cadence_type == "phrygian":
        return "V"
    elif cadence_type == "plagal":
        return "I" if mode == "major" else "i"
    return "I"
```

### Remove

- `distribute_cadences` function
- `CADENCE_DENSITY` usage for interval-based placement
- All logic that places cadences at regular bar intervals

### Function Signature

```python
def plan_cadences(
    tonal_sections: tuple[TonalSection, ...],
    mode: str,
    seed: int | None = None,
) -> tuple[CadencePoint, ...]:
    """
    Place cadences at tonal section boundaries.
    """
```

---

## Phase 3: Schema Generator with Key Area

### Purpose

Assign `key_area` to each `SchemaSlot`. Enforce clean bar multiples (no stretching).

### File

`planner/schema_generator.py` — modify existing

### Data Structure Change

Modify `SchemaSlot` in `planner/plannertypes.py`:

```python
@dataclass(frozen=True)
class SchemaSlot:
    type: str
    bars: int
    texture: str
    treatment: str
    dux_voice: str                          # RENAMED from voice_entry
    cadence: str | None
    key_area: str                           # Which key area this schema operates in
    stretto_overlap_beats: Fraction | None  # For treatment=stretto only
    sequence_repetitions: int | None        # For treatment=sequence only
```

### Backwards Compatibility

Old plans without new fields use defaults:

```python
key_area = slot_data.get("key_area", "I")
if "key_area" not in slot_data:
    logger.warning("SchemaSlot missing key_area, defaulting to I")

dux_voice = slot_data.get("dux_voice", slot_data.get("voice_entry", "soprano"))
stretto_overlap_beats = slot_data.get("stretto_overlap_beats")
sequence_repetitions = slot_data.get("sequence_repetitions")
```

### Schema Selection Constraint

Modify `schema_fits_bars` in `planner/schema_loader.py`:

```python
def schema_fits_bars(schema_name: str, available_bars: int) -> bool:
    """Check if schema can fill available_bars exactly.
    
    Returns True only if available_bars is a clean multiple of schema.bars.
    """
    schema = get_schema(schema_name)
    if available_bars < schema.bars:
        return False
    return available_bars % schema.bars == 0
```

### Remove stretch_schema

Delete `stretch_schema` from `builder/domain/schema_ops.py`. Replace with:

```python
def tile_schema(schema: dict, repetitions: int) -> dict:
    """Tile schema by repeating it.
    
    Args:
        schema: Schema dict with bass_degrees, soprano_degrees, durations, bars
        repetitions: Number of times to repeat (must be >= 1)
    
    Returns:
        Dict with repeated degree sequences and durations
    """
    assert repetitions >= 1, f"repetitions must be >= 1, got {repetitions}"
    
    return {
        "bass_degrees": schema["bass_degrees"] * repetitions,
        "soprano_degrees": schema["soprano_degrees"] * repetitions,
        "durations": schema["durations"] * repetitions,
        "bars": schema["bars"] * repetitions,
    }
```

### Function Signature

```python
def generate_schema_chain(
    tonal_sections: tuple[TonalSection, ...],
    cadence_plan: tuple[CadencePoint, ...],
    genre: str,
    mode: str,
    total_bars: int,
    seed: int | None = None,
) -> tuple[SchemaSlot, ...]:
    """
    Generate schemas within each tonal section.
    
    Each slot carries key_area from its containing tonal section.
    Treatment-specific parameters generated using seeded RNG.
    """
```

---

## Phase 4: Subject Realisation

### Purpose

Subject material realises the schema soprano trajectory. Schema soprano degrees are structural targets; subject provides surface rhythm and contour.

### New File

`builder/domain/subject_realiser.py`

### Concept

The subject is **rhythmically invariant**:
- **Rhythm**: Never changed
- **Internal intervals**: Preserved within phrases
- **Cadential arrivals**: May adjust final note of phrase segment by ≤2 degrees to match schema target

### Treatment Behaviours

| Treatment | Behaviour |
|-----------|-----------|
| statement | Subject presented once in dux_voice |
| imitation | Subject in dux_voice, answer at fifth in comes voice after subject completes |
| sequence | Subject head repeated, transposed per schema direction |
| inversion | Subject with intervals negated |
| stretto | Subject entries overlapped by stretto_overlap_beats |

### Imitation Timing

For `imitation` treatment, the answer (comes) enters **after subject completes**. No overlap.

If subject is 1.5 bars, answer enters at offset 1.5 bars. Stretto is a distinct treatment with explicit overlap.

### Sequence Direction

Inferred from schema metadata in `data/schemas.yaml`:

```yaml
fonte:
  sequential: true
  direction: descending

monte:
  sequential: true
  direction: ascending
```

Realiser reads `schema["direction"]` when treatment is `sequence`.

### Counter-Subject Handling

1. **During subject entry**: Other voice rests or holds pedal
2. **After subject completes**: Counter-subject enters against the answer
3. **Counter-subject source**:
   - If `material.counter_subject` exists → use it
   - Else → schema's bass degrees become melodic CS
   - If neither → generate via CP-SAT

### Arrival Adjustment

```python
def _adjust_arrival(
    notes: Notes,
    target_offset: Fraction,
    target_degree: int,
    max_adjustment: int = 2,
) -> Notes:
    """
    Modify final note of phrase to match schema target.
    
    Only adjusts if:
    - Note exists at target_offset
    - Adjustment needed is <= max_adjustment degrees
    
    Raises:
        ValueError: If adjustment exceeds max_adjustment
    """
```

### Function Signature

```python
def realise_subject(
    subject: Motif,
    counter_subject: Motif | None,
    schema_soprano_degrees: list[int],
    schema_bass_degrees: list[int],
    schema_durations: list[Fraction],
    treatment: str,
    dux_voice: str,
    target_bars: int,
    bar_duration: Fraction,
    key_area_offset: int,
    stretto_overlap_beats: Fraction | None = None,
    sequence_repetitions: int | None = None,
    schema_direction: str | None = None,
) -> tuple[Notes, Notes | None, Notes | None]:
    """
    Realise subject over schema slot.
    
    Returns:
        (dux_notes, comes_notes, counter_subject_notes)
    """
```

---

## Phase 5: Transpose Module

### Purpose

Transpose diatonic degrees when operating in a non-tonic key area. Chromatic alterations handled at MIDI export, not here.

### New File

`builder/domain/transpose.py`

### Concept

Transposition shifts diatonic degree numbers only. Accidentals (e.g., F→F♯ in G major) are applied by `pitch_ops.compute_midi_from_diatonic` at export time, which gains a `key_area` parameter.

This follows L009: "Tonal targets are functions, not modulations — realiser uses home_key for all melodic content."

### Functions

```python
KEY_AREA_OFFSETS: dict[str, int] = {
    "I": 0, "i": 0,
    "II": 1, "ii": 1,
    "III": 2, "iii": 2,
    "IV": 3, "iv": 3,
    "V": 4, "v": 4,
    "VI": 5, "vi": 5,
    "VII": 6, "vii": 6,
    "viio": 6,
}


def normalise_key_area(key_area: str) -> str:
    """Strip quality markers from Roman numeral.
    
    Examples: "viio" → "vii", "idim" → "i"
    """
    base = key_area
    for suffix in ("o", "dim", "aug", "+"):
        if base.endswith(suffix):
            base = base[:-len(suffix)]
    return base


def transpose_degree(degree: int, key_area: str) -> int:
    """Transpose degree from tonic to key_area."""
    normalised = normalise_key_area(key_area)
    offset = KEY_AREA_OFFSETS.get(normalised.upper(), 0)
    return degree + offset


def transpose_degrees(degrees: list[int], key_area: str) -> list[int]:
    """Transpose list of degrees."""
    return [transpose_degree(d, key_area) for d in degrees]
```

### MIDI Export Change

Modify `builder/domain/pitch_ops.py`:

```python
def compute_midi_from_diatonic(
    diatonic: int,
    key_offset: int = 0,
    key_area: str = "I",
    home_mode: str = "major",
) -> int:
    """
    Convert diatonic pitch to MIDI note number.
    
    Applies key area accidentals based on relationship to home key.
    """
```

---

## Phase 6: CP-SAT with Schema Constraints and Fixed Regions

### Purpose

Schema bass degrees become hard constraints. Subject/answer entries become fixed regions that CP-SAT cannot modify.

### File

`builder/solver/cpsat_voice.py` — modify existing

### New Data Structure

```python
@dataclass(frozen=True)
class FixedRegion:
    """A time region with fixed pitch (from subject/answer entry)."""
    start: Fraction
    end: Fraction
    pitch: int
```

### New Parameters

```python
def generate_voice_cpsat(
    existing_voices: list[Notes],
    harmony: tuple[str, ...],
    voice_role: str,
    bar_duration: Fraction,
    pattern: Pattern,
    schema_targets: list[tuple[Fraction, int]] | None = None,
    fixed_regions: list[FixedRegion] | None = None,
    key_area_offset: int = 0,
    timeout_seconds: float = 10.0,
) -> Notes:
    """
    Generate voice using CP-SAT.
    
    Args:
        schema_targets: (offset, degree) hard constraints, applied outside fixed_regions
        fixed_regions: Time regions where pitch is predetermined (not decision variables)
        key_area_offset: Diatonic offset for transposition
    """
```

### Fixed Region Handling

```python
def _get_fixed_pitch(
    offset: Fraction,
    fixed_regions: list[FixedRegion] | None,
) -> int | None:
    """Return fixed pitch if offset falls within a fixed region."""
    if fixed_regions is None:
        return None
    for region in fixed_regions:
        if region.start <= offset < region.end:
            return region.pitch
    return None


def _get_schema_target(
    offset: Fraction,
    schema_targets: list[tuple[Fraction, int]] | None,
) -> int | None:
    """Return schema target degree at exact offset."""
    if schema_targets is None:
        return None
    for target_offset, degree in schema_targets:
        if target_offset == offset:  # Exact equality, no tolerance
            return degree
    return None
```

In model building:
- For attacks within fixed_regions: pitch is constant (not a decision variable)
- For attacks outside: normal optimisation with schema_targets as hard constraints

### Schema Targets Extraction

```python
def _extract_bass_targets(
    schema_bass_degrees: list[int | dict],
    schema_durations: list[Fraction],
) -> list[tuple[Fraction, int]]:
    """Extract (offset, degree) pairs from schema bass."""
    targets = []
    offset = Fraction(0)
    for degree, dur in zip(schema_bass_degrees, schema_durations):
        if isinstance(degree, dict):
            deg = degree["degree"]
        else:
            deg = degree
        targets.append((offset, deg))
        offset += dur
    return targets
```

### Fixed Regions from Subject Entry

```python
def _notes_to_fixed_regions(notes: Notes) -> list[FixedRegion]:
    """Convert Notes to list of FixedRegion."""
    regions = []
    offset = Fraction(0)
    for pitch, dur in zip(notes.pitches, notes.durations):
        regions.append(FixedRegion(start=offset, end=offset + dur, pitch=pitch))
        offset += dur
    return regions
```

### Harmony Parameter

The `harmony` parameter maps bass degrees to chord symbols for candidate generation. `schema_targets` constrain the final choice. Both needed: harmony populates candidates, schema_targets select from them.

```python
def _derive_harmony(tiled_schema: dict, target_bars: int) -> tuple[str, ...]:
    """Derive chord symbols from schema bass degrees."""
    # Maps degree 1→I, degree 4→IV, etc.
```

---

## Phase 7: Integration in Schema Handler

### File

`builder/handlers/schema_handler.py` — rewrite `build_schema_slot`

### Subject Threading

Subject retrieved from tree root:

```python
def _get_subject_from_tree(root: Node) -> Motif:
    """Extract subject from tree root."""
    assert "material" in root, "Tree missing 'material' node"
    assert "subject" in root["material"], "Material missing 'subject'"
    return _motif_from_node(root["material"]["subject"])


def _get_counter_subject_from_tree(root: Node) -> Motif | None:
    """Extract counter-subject if present."""
    if "material" not in root:
        return None
    if "counter_subject" not in root["material"]:
        return None
    return _motif_from_node(root["material"]["counter_subject"])
```

### New Flow

```python
def build_schema_slot(
    schema_node: Node,
    section_node: Node,
    bar_duration: Fraction,
    voice_count: int,
    metre: str,
) -> Node:
    """Build schema slot with subject realisation and constrained bass."""
    
    root = schema_node.root
    
    # 1. Get subject and counter-subject
    subject = _get_subject_from_tree(root)
    counter_subject = _get_counter_subject_from_tree(root)
    
    # 2. Extract slot fields
    schema_type = schema_node["type"].value
    target_bars = schema_node["bars"].value
    treatment = schema_node["treatment"].value
    dux_voice = schema_node["dux_voice"].value
    key_area = schema_node["key_area"].value
    
    stretto_overlap = None
    if "stretto_overlap_beats" in schema_node:
        stretto_overlap = Fraction(schema_node["stretto_overlap_beats"].value)
    
    sequence_reps = None
    if "sequence_repetitions" in schema_node:
        sequence_reps = schema_node["sequence_repetitions"].value
    
    # 3. Load and tile schema
    schema = get_schema(schema_type)
    repetitions = target_bars // schema["bars"]
    tiled = tile_schema(schema, repetitions)
    
    # 4. Compute key area offset
    key_area_offset = KEY_AREA_OFFSETS.get(normalise_key_area(key_area).upper(), 0)
    
    # 5. Get schema direction for sequence
    schema_direction = schema.get("direction")
    
    # 6. Realise subject
    dux_notes, comes_notes, cs_notes = realise_subject(
        subject=subject,
        counter_subject=counter_subject,
        schema_soprano_degrees=tiled["soprano_degrees"],
        schema_bass_degrees=tiled["bass_degrees"],
        schema_durations=tiled["durations"],
        treatment=treatment,
        dux_voice=dux_voice,
        target_bars=target_bars,
        bar_duration=bar_duration,
        key_area_offset=key_area_offset,
        stretto_overlap_beats=stretto_overlap,
        sequence_repetitions=sequence_reps,
        schema_direction=schema_direction,
    )
    
    # 7. Assign to voices
    if dux_voice == "soprano":
        soprano = dux_notes
        bass_entry = comes_notes
    else:
        soprano = comes_notes if comes_notes else _rest_notes(target_bars, bar_duration)
        bass_entry = dux_notes
    
    # 8. Build fixed regions from bass entry
    bass_fixed: list[FixedRegion] = []
    if bass_entry is not None:
        bass_fixed = _notes_to_fixed_regions(bass_entry)
    
    # 9. Extract bass targets
    bass_targets = _extract_bass_targets(
        schema_bass_degrees=tiled["bass_degrees"],
        schema_durations=tiled["durations"],
    )
    
    # 10. Generate bass with constraints
    bass = generate_voice_cpsat(
        existing_voices=[soprano],
        harmony=_derive_harmony(tiled, target_bars),
        voice_role="bass",
        bar_duration=bar_duration,
        pattern=load_pattern(get_default_pattern("bass"), metre, "bass"),
        schema_targets=bass_targets,
        fixed_regions=bass_fixed,
        key_area_offset=key_area_offset,
    )
    
    # 11. Generate inner voices (no schema constraints)
    # ...
```

---

## Planner Integration

### File

`planner/planner.py` — modify `build_schema_plan`

### New Flow

```python
def build_schema_plan(
    brief: Brief,
    user_motif: Motif | None = None,
    seed: int | None = None,
    user_frame: Frame | None = None,
) -> SchemaPlan:
    # Step 1: Resolve frame (unchanged)
    frame = user_frame if user_frame else resolve_frame(brief)
    
    # Step 2: Plan tonal journey (NEW)
    tonal_sections = plan_tonal_journey(
        genre=brief.genre,
        mode=frame.mode,
        total_bars=brief.bars,
        seed=seed,
    )
    
    # Step 3: Plan cadences from tonal sections (CHANGED)
    cadence_plan = plan_cadences(
        tonal_sections=tonal_sections,
        mode=frame.mode,
        seed=seed,
    )
    
    # Step 4: Generate schema chain with key areas (CHANGED)
    schema_chain = generate_schema_chain(
        tonal_sections=tonal_sections,
        cadence_plan=cadence_plan,
        genre=brief.genre,
        mode=frame.mode,
        total_bars=brief.bars,
        seed=seed,
    )
    
    # Step 5: Handle subject (unchanged)
    opening_schema = schema_chain[0].type
    if user_motif is not None:
        validation = validate_subject(user_motif, opening_schema, frame.mode)
        assert validation.valid, f"Subject invalid: {validation.errors}"
        subject = user_motif
    else:
        subject = derive_subject(opening_schema, frame, brief.genre)
    
    material = Material(subject=subject, counter_subject=None)
    
    # Step 6: Build structure (unchanged)
    structure = build_structure_from_schemas(schema_chain, cadence_plan)
    
    # Step 7: Compute actual bars
    actual_bars = compute_actual_bars(schema_chain)
    
    return SchemaPlan(
        brief=brief,
        frame=frame,
        material=material,
        structure=structure,
        cadence_plan=cadence_plan,
        schema_chain=schema_chain,
        actual_bars=actual_bars,
    )
```

---

## File Summary

### New Files

| File | Purpose | Lines (est.) |
|------|---------|--------------|
| `planner/tonal_planner.py` | Tonal journey generation | 100-120 |
| `builder/domain/subject_realiser.py` | Subject realisation per treatment | 180-220 |
| `builder/domain/transpose.py` | Key area transposition | 40-50 |
| `data/genres/_default.yaml` | Default tonal journey | 15 |
| `data/cadence_transitions.yaml` | Cadence type lookup | 30 |

### Modified Files

| File | Changes |
|------|---------|
| `planner/plannertypes.py` | Add `TonalSection`, modify `CadencePoint`, modify `SchemaSlot` |
| `planner/cadence_planner.py` | Rewrite to use tonal sections |
| `planner/schema_generator.py` | Accept tonal sections, propagate key_area |
| `planner/schema_loader.py` | Tighten `schema_fits_bars` to require clean multiples |
| `planner/planner.py` | Insert tonal planning step |
| `builder/domain/schema_ops.py` | Remove `stretch_schema`, add `tile_schema` |
| `builder/domain/pitch_ops.py` | Add `key_area` parameter to MIDI conversion |
| `builder/solver/cpsat_voice.py` | Add `schema_targets`, `fixed_regions`, `key_area_offset` |
| `builder/handlers/schema_handler.py` | Use subject_realiser, pass constraints to CP-SAT |

---

## Implementation Order

```
Phase 1: tonal_planner.py + _default.yaml
    └── No dependencies
    
Phase 5: transpose.py
    └── No dependencies (parallel with Phase 1)
    
Phase 2: cadence_planner.py + cadence_transitions.yaml
    └── Depends on Phase 1 (TonalSection type)
    
Phase 3: schema_generator.py + schema_loader.py + schema_ops.py
    └── Depends on Phases 1-2
    
Phase 4: subject_realiser.py
    └── Depends on Phase 5
    
Phase 6: cpsat_voice.py
    └── Depends on Phase 5
    
Phase 7: schema_handler.py
    └── Depends on Phases 4, 5, 6
    
Integration: planner.py + pitch_ops.py
    └── Depends on Phases 1, 2, 3
```

Suggested order: 1 → 5 → 2 → 3 → 4 → 6 → 7 → Integration

---

## Testing

### Unit Tests

```
tests/planner/test_tonal_planner.py
tests/planner/test_cadence_planner.py
tests/builder/domain/test_subject_realiser.py
tests/builder/domain/test_transpose.py
tests/builder/solver/test_cpsat_voice.py
```

### Integration Test

After all phases, regenerate `freude_invention.note` and verify:

1. **Tonal variety**: Bars 1-8 in C, bars 9-16 in G, bars 17-24 in C
2. **Cadence variety**: Authentic cadences at section boundaries, not all half→V
3. **Subject presence**: Recognisable "Freude" contour, not schema semibreves
4. **Schema voice-leading**: Prinner bass is 4-3-2-1 (transposed), not generic walking
5. **Rhythmic interest**: Quavers and crotchets from subject

### Determinism Test

```python
def test_deterministic_output():
    plan1 = build_schema_plan(brief, seed=42)
    plan2 = build_schema_plan(brief, seed=42)
    assert plan1 == plan2
```

---

## Conventions

- Type hints on all parameters except loop variables
- One major class per file
- Methods sorted alphabetically within class
- Modules under 100 lines where possible
- Assert preconditions at function entry
- No Greek symbols in code
- Single-line docstrings for public APIs

---

## References

- `docs/Tier2_Architecture/planner_design.md` — canonical design document
- `data/schemas.yaml` — schema definitions
- `shared/constants.py` — shared constants
