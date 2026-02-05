# Rhythmic Planning Upgrade

## Status

Draft | Upgrade from gap-level rhythm to hierarchical rhythmic planning

---

## Problem Statement

Rhythmic planning is fragmented across multiple components with no coherent hierarchy:

1. **rhythmic.py (Layer 6)**: Basic slot-activation system, barely used
2. **voice_planning.py**: Creates GapPlan with density/character, but only at gap level
3. **figuration**: Uses rhythm_templates.yaml for duration patterns, selected per-gap
4. **affects.yaml**: Has rhythm_states (RUN, HOLD, CADENCE, TRANSITION) that are not used

The result is monotonous rhythm: demo_fantasia shows 80% of bars using the same 5/8 + 1/8 + 1/4 pattern. There is no:

- Section-level rhythmic character
- Phrase-level motif development
- Variety rules preventing repetition
- Affect-driven rhythmic profiles
- Coordination between rhythmic and tonal planning

Per `rhythmic_planning.md`, rhythm should be a 3-level hierarchy. Currently only gap level exists.

---

## Design Principles

1. **Hierarchical planning.** Section profile → phrase motif → gap template. Each level constrains the next.
2. **Affect-driven character.** Mattheson's Affektenlehre maps affects to rhythmic character.
3. **Motif development.** Phrases after the first develop (diminute, augment, fragment) the base motif.
4. **Variety rules are hard constraints.** V-R001 through V-R005 from `rhythmic_planning.md` are non-negotiable.
5. **Density coordination.** Tonal planning's density specification flows to rhythmic density trajectory.
6. **RNG in planner only.** Per A005, randomness lives here; downstream is deterministic.

---

## Architecture Overview

```
Layer 6: Rhythmic Planning
├── Input: AffectConfig, FormSections, SchemaChain, TonalPlan
├── Process:
│   ├── For each section: compute RhythmicProfile
│   ├── For each phrase: select and develop RhythmicMotif
│   └── For each gap: derive GapRhythm from phrase motif
└── Output: RhythmPlan (profiles, motifs, gap rhythms)

Integration with existing:
├── voice_planning.py: Receives RhythmPlan, populates GapPlan.rhythm
├── figuration: Uses GapRhythm instead of template lookup
└── realisation: Uses start_beat from rhythm plan
```

---

## Layer 6: Rhythmic Planning

### Data Structures

```python
@dataclass(frozen=True)
class RhythmicProfile:
    """Section-level rhythmic character."""
    affect: str                    # Governing affect name
    base_density: str              # low/medium/high
    inequality: str                # none/mild/moderate/strong
    overdotting: str               # none/standard/pronounced
    hemiola_zones: tuple[tuple[int, int], ...]  # Bar ranges for hemiola
    climax_bar: int                # Peak rhythmic intensity
    density_trajectory: str        # constant/rising/falling/arc


@dataclass(frozen=True)
class RhythmicMotif:
    """Phrase-level rhythmic cell."""
    name: str                      # Identifier
    pattern: tuple[Fraction, ...]  # Duration sequence (sum = 1 bar)
    accent_pattern: tuple[int, ...]  # Metric weight per note (1-4)
    character: str                 # plain/expressive/energetic/ornate/bold
    compatible_metres: tuple[str, ...]  # Valid time signatures
    phrase_positions: tuple[str, ...]   # opening/interior/cadential
    weight: float                  # Selection probability


@dataclass(frozen=True)
class GapRhythm:
    """Gap-level duration specification."""
    durations: tuple[Fraction, ...]   # Exact durations for each note
    inequality_ratio: Fraction        # e.g., 3/2 for mild swing
    downbeat_emphasis: bool           # Accent first note
    pickup_to_next: bool              # Final note leads to next anchor
    motif_slice: tuple[int, int]      # Which portion of phrase motif


@dataclass(frozen=True)
class RhythmPlan:
    """Complete rhythmic plan for composition."""
    section_profiles: tuple[tuple[str, RhythmicProfile], ...]  # (section_name, profile)
    phrase_motifs: tuple[tuple[int, RhythmicMotif], ...]       # (phrase_idx, motif)
    gap_rhythms: tuple[GapRhythm, ...]                         # One per gap
```

### Algorithm: Section Profile Assignment

Input: `AffectConfig`, `FormSection`, `TonalPlan`

```
1. Get base parameters from affect:
   
   Affect → rhythmic character (from Mattheson):
   
   | Affect          | Base density | Inequality | Overdotting | Character   |
   |-----------------|--------------|------------|-------------|-------------|
   | Freudigkeit     | high         | mild       | standard    | energetic   |
   | Klage           | low          | none       | none        | plain       |
   | Zorn            | high         | none       | pronounced  | bold        |
   | Zaertlichkeit   | medium       | mild       | none        | expressive  |
   | Majestaet       | medium       | none       | pronounced  | ornate      |
   | default         | medium       | mild       | standard    | expressive  |

2. Modify for section function:
   
   | Section function | Density modifier | Character override |
   |------------------|------------------|--------------------|
   | exordium         | medium (establish)| plain             |
   | narratio         | high (develop)   | energetic          |
   | confirmatio      | medium (return)  | expressive         |
   | peroratio        | low (close)      | plain              |
   | episode          | high (activity)  | energetic          |
   | cadential        | low (prepare)    | expressive         |

3. Compute density trajectory from section length:
   
   | Section length | Trajectory |
   |----------------|------------|
   | <= 4 bars      | constant   |
   | 5-8 bars       | arc        |
   | > 8 bars       | rising→falling |

4. Locate climax bar (typically 2/3 through section):
   climax_bar = section.start_bar + int(section.length * 0.67)

5. Mark hemiola zones (triple metre only):
   IF section.metre in ("3/4", "6/8", "3/2") AND section.has_cadence:
       hemiola_zones = [(cadence_bar - 2, cadence_bar)]
   ELSE:
       hemiola_zones = ()

6. Apply tonal density coordination:
   IF tonal_plan.density == "high":
       density trajectory tends toward high
   IF tonal_plan.density == "low":
       density trajectory tends toward sparse
```

### Algorithm: Motif Selection and Development

For each phrase within a section:

```
1. Determine phrase position:
   - First phrase of section → "opening"
   - Last phrase before cadence → "cadential"
   - All others → "interior"

2. Filter motif candidates:
   candidates = [m for m in MOTIF_VOCABULARY 
                 if phrase_position in m.phrase_positions
                 and metre in m.compatible_metres
                 and profile.affect_compatible(m.character)]

3. Apply variety rule V-R001 (no consecutive identical):
   IF previous_motif is not None:
       candidates = [m for m in candidates if m.name != previous_motif.name]

4. Weight by profile density:
   weights = [density_weight(m, profile.base_density) for m in candidates]

5. Select via seeded RNG:
   base_motif = weighted_choice(candidates, weights, seed=phrase_idx)

6. Apply development for phrases 2+:
   
   FUNCTION develop_motif(base, phrase_idx, development_plan):
       IF phrase_idx == 0:
           RETURN base  # Establish
       
       IF development_plan == "intensifying":
           IF phrase_idx <= 2:
               RETURN base  # Repeat to establish
           ELIF phrase_idx <= 4:
               RETURN diminute(base)  # Double note count
           ELSE:
               RETURN fragment(base)  # First half only
       
       ELIF development_plan == "relaxing":
           IF phrase_idx > 2:
               RETURN augment(base)  # Halve note count
           RETURN base
       
       ELIF development_plan == "contrasting":
           IF phrase_idx % 2 == 1:
               RETURN invert(base)  # Reverse duration order
           RETURN base

7. Verify variety rule V-R002:
   ASSERT phrase_idx < 3 OR developed != base, (
       f"V-R002 violation: phrase {phrase_idx} uses literal base motif"
   )
```

### Algorithm: Gap Rhythm Derivation

For each gap within a phrase:

```
1. Compute gap position within phrase (0.0 to 1.0):
   gap_position = (gap.bar_num - phrase.start_bar) / phrase.length

2. Extract motif slice covering this gap:
   motif_slice = extract_slice(phrase_motif.pattern, gap_position, gap.duration)

3. Scale to actual gap duration:
   raw_durations = scale_to_duration(motif_slice, gap.duration)

4. Apply inequality if stepwise motion:
   IF gap.is_stepwise AND profile.inequality != "none":
       durations = apply_inequality(raw_durations, profile.inequality)
   ELSE:
       durations = raw_durations

5. Apply overdotting if enabled:
   IF profile.overdotting != "none" AND has_dotted_pattern(durations):
       durations = apply_overdotting(durations, profile.overdotting)

6. Verify variety rule V-R001:
   IF previous_gap is not None:
       ASSERT differs_from(durations, previous_gap.durations), (
           f"V-R001 violation: consecutive identical rhythms at bar {gap.bar_num}"
       )

7. Check cadential rhythm change (V-R003):
   IF gap.near_cadence:
       ASSERT is_cadential_rhythm(durations), (
           f"V-R003 violation: non-cadential rhythm near cadence"
       )

8. Return gap rhythm:
   RETURN GapRhythm(
       durations=durations,
       inequality_ratio=INEQUALITY_RATIOS[profile.inequality],
       downbeat_emphasis=gap.start_beat == 1,
       pickup_to_next=gap.near_cadence,
       motif_slice=(slice_start, slice_end),
   )
```

---

## Rhythmic Motif Vocabulary

### Foundational Cells (4/4 metre, 1 bar)

```yaml
even_quarters:
  pattern: [1/4, 1/4, 1/4, 1/4]
  accent_pattern: [4, 2, 3, 1]
  character: plain
  phrase_positions: [opening, interior]
  weight: 1.0

dotted_drive:
  pattern: [3/8, 1/8, 3/8, 1/8]
  accent_pattern: [4, 1, 3, 1]
  character: energetic
  phrase_positions: [opening, interior]
  weight: 1.2

lombardic_snap:
  pattern: [1/8, 3/8, 1/8, 3/8]
  accent_pattern: [3, 2, 3, 2]
  character: bold
  phrase_positions: [interior, cadential]
  weight: 0.8

syncopated:
  pattern: [1/8, 1/4, 1/4, 1/4, 1/8]
  accent_pattern: [2, 3, 2, 3, 1]
  character: expressive
  phrase_positions: [interior]
  weight: 0.7

long_short_short:
  pattern: [1/2, 1/4, 1/4]
  accent_pattern: [4, 2, 1]
  character: ornate
  phrase_positions: [opening]
  weight: 0.9

running_eighths:
  pattern: [1/8, 1/8, 1/8, 1/8, 1/8, 1/8, 1/8, 1/8]
  accent_pattern: [4, 1, 3, 1, 3, 1, 2, 1]
  character: energetic
  phrase_positions: [interior]
  weight: 1.0
```

### Cadential Cells

```yaml
cadential_dotted:
  pattern: [1/4, 3/8, 1/8, 1/4]
  accent_pattern: [3, 4, 1, 2]
  character: expressive
  phrase_positions: [cadential]
  weight: 1.5

hemiola_preparation:  # For 3/4, spans 2 bars
  pattern: [1/2, 1/2, 1/2, 1/2, 1/2, 1/2]
  accent_pattern: [4, 2, 3, 4, 2, 3]
  character: ornate
  phrase_positions: [cadential]
  weight: 1.0

final_long:
  pattern: [3/4, 1/4]
  accent_pattern: [4, 2]
  character: plain
  phrase_positions: [cadential]
  weight: 1.2
```

### 3/4 Metre Cells

```yaml
minuet_basic:
  pattern: [1/4, 1/4, 1/4]
  accent_pattern: [4, 2, 2]
  character: plain
  compatible_metres: ["3/4"]
  phrase_positions: [opening, interior]
  weight: 1.0

sarabande:
  pattern: [1/4, 1/2, 1/4]
  accent_pattern: [3, 4, 1]
  character: expressive
  compatible_metres: ["3/4"]
  phrase_positions: [opening, interior]
  weight: 0.9
```

---

## Motif Development Operations

```python
def diminute(motif: RhythmicMotif) -> RhythmicMotif:
    """Double note count, halve durations."""
    new_pattern = []
    for dur in motif.pattern:
        new_pattern.extend([dur / 2, dur / 2])
    return replace(motif, pattern=tuple(new_pattern), name=f"{motif.name}_dim")


def augment(motif: RhythmicMotif) -> RhythmicMotif:
    """Halve note count, double durations."""
    new_pattern = []
    for i in range(0, len(motif.pattern), 2):
        combined = motif.pattern[i]
        if i + 1 < len(motif.pattern):
            combined += motif.pattern[i + 1]
        new_pattern.append(combined)
    return replace(motif, pattern=tuple(new_pattern), name=f"{motif.name}_aug")


def fragment(motif: RhythmicMotif) -> RhythmicMotif:
    """Take first half of motif."""
    half = len(motif.pattern) // 2
    return replace(motif, pattern=motif.pattern[:half], name=f"{motif.name}_frag")


def invert(motif: RhythmicMotif) -> RhythmicMotif:
    """Reverse duration order."""
    return replace(motif, pattern=tuple(reversed(motif.pattern)), name=f"{motif.name}_inv")


def displace(motif: RhythmicMotif, offset: Fraction) -> RhythmicMotif:
    """Shift pattern by offset (for syncopation)."""
    # Rotate pattern based on offset
    total = sum(motif.pattern)
    offset_normalized = offset % total
    cumulative = Fraction(0)
    split_idx = 0
    for i, dur in enumerate(motif.pattern):
        cumulative += dur
        if cumulative >= offset_normalized:
            split_idx = i + 1
            break
    new_pattern = motif.pattern[split_idx:] + motif.pattern[:split_idx]
    return replace(motif, pattern=new_pattern, name=f"{motif.name}_disp")
```

---

## Inequality and Overdotting

### Inequality Ratios

```python
INEQUALITY_RATIOS: dict[str, Fraction] = {
    "none": Fraction(1, 1),      # Equal
    "mild": Fraction(3, 2),      # 60:40
    "moderate": Fraction(2, 1),  # 67:33
    "strong": Fraction(3, 1),    # 75:25
}


def apply_inequality(
    durations: tuple[Fraction, ...],
    inequality: str,
) -> tuple[Fraction, ...]:
    """Apply notes inégales to stepwise pairs."""
    ratio = INEQUALITY_RATIOS[inequality]
    result = list(durations)
    
    # Apply to pairs of equal short notes
    i = 0
    while i < len(result) - 1:
        if result[i] == result[i + 1] and result[i] <= Fraction(1, 8):
            total = result[i] + result[i + 1]
            long_part = total * ratio / (ratio + 1)
            short_part = total - long_part
            result[i] = long_part
            result[i + 1] = short_part
            i += 2
        else:
            i += 1
    
    return tuple(result)
```

### Overdotting Application

```python
OVERDOTTING_FACTORS: dict[str, Fraction] = {
    "none": Fraction(1, 1),
    "standard": Fraction(7, 6),      # Dotted becomes slightly more dotted
    "pronounced": Fraction(15, 12),  # Dotted becomes double-dotted
}


def apply_overdotting(
    durations: tuple[Fraction, ...],
    overdotting: str,
) -> tuple[Fraction, ...]:
    """Exaggerate dotted rhythms."""
    factor = OVERDOTTING_FACTORS[overdotting]
    result = list(durations)
    
    # Find dotted patterns (3:1 ratio)
    i = 0
    while i < len(result) - 1:
        if result[i] == result[i + 1] * 3:
            total = result[i] + result[i + 1]
            long_part = result[i] * factor
            short_part = total - long_part
            if short_part > 0:
                result[i] = long_part
                result[i + 1] = short_part
            i += 2
        else:
            i += 1
    
    return tuple(result)
```

---

## Variety Rules Implementation

### V-R001: No Consecutive Identical Rhythms

```python
def validate_no_consecutive_identical(gap_rhythms: list[GapRhythm]) -> None:
    for i in range(len(gap_rhythms) - 1):
        current = gap_rhythms[i].durations
        next_gap = gap_rhythms[i + 1].durations
        
        differs = (
            len(current) != len(next_gap) or
            any(c != n for c, n in zip(current, next_gap))
        )
        
        assert differs, (
            f"V-R001 violation: identical rhythms at gaps {i} and {i+1}"
        )
```

### V-R002: Phrase-Level Motif Variation

```python
def validate_motif_variation(
    phrase_motifs: list[tuple[int, RhythmicMotif]],
) -> None:
    base_motif: RhythmicMotif | None = None
    
    for phrase_idx, motif in phrase_motifs:
        if phrase_idx == 0:
            base_motif = motif
        elif phrase_idx >= 3:
            assert motif.pattern != base_motif.pattern, (
                f"V-R002 violation: phrase {phrase_idx} uses literal base motif"
            )
```

### V-R003: Cadential Rhythmic Change

```python
def validate_cadential_change(
    gap_rhythms: list[GapRhythm],
    cadence_bars: set[int],
) -> None:
    for i, rhythm in enumerate(gap_rhythms):
        bar = i + 1  # Simplified; actual implementation uses bar_num
        if bar in cadence_bars or bar - 1 in cadence_bars:
            # Must differ from 2 bars prior
            if i >= 2:
                prior = gap_rhythms[i - 2].durations
                current = rhythm.durations
                differs = (
                    len(current) != len(prior) or
                    any(c != p for c, p in zip(current, prior))
                )
                assert differs, (
                    f"V-R003 violation: no rhythmic change before cadence at bar {bar}"
                )
```

### V-R004: Section Density Arc

```python
def validate_density_arc(
    section_profile: RhythmicProfile,
    gap_rhythms: list[GapRhythm],
) -> None:
    if len(gap_rhythms) < 4:
        return  # Too short for arc
    
    # Compute density per gap (notes per beat)
    densities = [
        len(r.durations) / float(sum(r.durations))
        for r in gap_rhythms
    ]
    
    # Find peak
    peak_idx = densities.index(max(densities))
    
    if section_profile.density_trajectory == "arc":
        # Peak should be in middle third
        third = len(densities) // 3
        assert third <= peak_idx <= 2 * third, (
            f"V-R004 violation: density arc peak at {peak_idx}, "
            f"expected in [{third}, {2 * third}]"
        )
```

### V-R005: Cross-Phrase Continuity

```python
def validate_phrase_continuity(
    phrase_final_durations: list[Fraction],
    phrase_initial_durations: list[Fraction],
) -> None:
    for i in range(len(phrase_final_durations) - 1):
        final = phrase_final_durations[i]
        initial = phrase_initial_durations[i + 1]
        
        # Avoid two equal long notes creating seam
        seam = final >= Fraction(1, 4) and initial >= Fraction(1, 4) and final == initial
        assert not seam, (
            f"V-R005 violation: rhythmic seam between phrases {i} and {i+1}"
        )
```

---

## Integration with Tonal Planning

### Coordination Points

| Tonal planning output | Rhythmic planning input |
|-----------------------|-------------------------|
| `density` ("high"/"medium"/"low") | `base_density` in profile |
| Section boundaries | Profile boundaries |
| Cadence locations | Hemiola zones, cadential motifs |
| Climax section | Peak density trajectory |
| `sequential_segments` | Motif repetition count |

### Density Flow

```python
def coordinate_density(
    tonal_density: str,
    section_function: str,
) -> str:
    """Combine tonal and section density signals."""
    
    # Tonal density sets baseline
    base = {"high": 2, "medium": 1, "low": 0}[tonal_density]
    
    # Section function modifies
    modifier = {
        "exordium": 0,
        "narratio": 1,
        "confirmatio": 0,
        "peroratio": -1,
        "episode": 1,
    }.get(section_function, 0)
    
    combined = max(0, min(2, base + modifier))
    return {0: "low", 1: "medium", 2: "high"}[combined]
```

---

## File Structure

```
planner/
├── rhythmic.py           # Layer 6: RhythmPlan generation (REWRITE)
├── rhythmic_profile.py   # Section profile assignment (NEW)
├── rhythmic_motif.py     # Motif selection and development (NEW)
├── rhythmic_gap.py       # Gap rhythm derivation (NEW)
├── rhythmic_variety.py   # Variety rule validators (NEW)
├── voice_planning.py     # Receives RhythmPlan, populates GapPlan (MODIFY)
└── textural.py           # Unchanged

builder/
└── types.py              # Add RhythmicProfile, RhythmicMotif, GapRhythm, RhythmPlan

data/
└── rhythm/
    ├── motif_vocabulary.yaml    # Rhythmic cells by metre (NEW)
    ├── affect_profiles.yaml     # Affect → rhythmic character (NEW)
    └── development_rules.yaml   # Motif transformation rules (NEW)
```

---

## Implementation Order

### Phase 1: Data Structures
1. Add `RhythmicProfile`, `RhythmicMotif`, `GapRhythm`, `RhythmPlan` to `builder/types.py`
2. Create `data/rhythm/motif_vocabulary.yaml` with foundational cells
3. Create `data/rhythm/affect_profiles.yaml` with Mattheson mappings

### Phase 2: Section Profile
1. Implement `rhythmic_profile.py` with section profile algorithm
2. Load affect profiles from YAML
3. Compute density trajectory and climax bar
4. Identify hemiola zones

### Phase 3: Motif Selection
1. Implement `rhythmic_motif.py` with motif vocabulary loader
2. Implement selection with filtering and weighting
3. Implement development operations (diminute, augment, fragment, invert)
4. Validate V-R001 and V-R002

### Phase 4: Gap Rhythm Derivation
1. Implement `rhythmic_gap.py` with gap rhythm algorithm
2. Implement inequality application
3. Implement overdotting application
4. Validate V-R003, V-R004, V-R005

### Phase 5: Integration
1. Rewrite `rhythmic.py` to orchestrate profile → motif → gap flow
2. Modify `voice_planning.py` to receive RhythmPlan and populate GapPlan.rhythm
3. Modify figuration to use GapRhythm instead of template lookup
4. Add tonal density coordination

### Phase 6: Testing
1. Unit tests for each variety rule
2. Integration test: full pipeline produces varied rhythms
3. Regression test: demo_fantasia no longer has 80% identical patterns

---

## Testing Strategy

### Unit Tests

| Test | Validates |
|------|-----------|
| `test_profile_from_affect` | Correct Mattheson mapping |
| `test_profile_modifiers` | Section function modifies base |
| `test_motif_selection` | Filters by position and character |
| `test_motif_development` | Diminution, augmentation work |
| `test_inequality_application` | Notes inégales applied correctly |
| `test_overdotting_application` | Dotted rhythms exaggerated |
| `test_variety_V_R001` | No consecutive identical rhythms |
| `test_variety_V_R002` | Phrase motifs develop |
| `test_variety_V_R003` | Cadential rhythm changes |
| `test_variety_V_R004` | Density follows arc |
| `test_variety_V_R005` | No phrase seams |

### Integration Tests

| Test | Validates |
|------|-----------|
| `test_full_rhythm_plan` | Three levels produce coherent output |
| `test_density_coordination` | Tonal density flows to rhythmic |
| `test_invention_rhythms` | Demo produces varied patterns |
| `test_determinism` | Same seed → same rhythms |

---

## Design Decisions

### 1. Motif-First, Not Template-First

**Decision:** Rhythm derives from phrase motifs, not gap templates.

The current system queries `rhythm_templates.yaml` per gap, selecting by note count and metre. This guarantees monotony because adjacent gaps often have identical parameters.

The new system selects a phrase motif, then slices it for each gap. Adjacent gaps are coherent (from same motif) yet different (different slices).

**Consequence:** `rhythm_templates.yaml` becomes fallback for edge cases where motif slicing fails.

### 2. Development Plan from Section Profile

**Decision:** Each section profile specifies a development plan.

```python
class RhythmicProfile:
    ...
    development_plan: str  # "intensifying", "relaxing", "contrasting"
```

This ensures motif development matches section character:
- Narratio (development): intensifying → diminution
- Confirmatio (return): relaxing → augmentation
- Episode: contrasting → inversion

### 3. Inequality Cancellation

**Decision:** Inequality cancelled when smaller values present.

Per Quantz: notes inégales apply to the "smallest regular value". If a bar has semiquavers alongside quavers, inequality applies to semiquavers, not quavers.

**Implementation:** Track smallest note value per phrase. Apply inequality only to that value.

### 4. Beat-Class Inheritance

**Decision:** Rhythm plan inherits lead/accompany beat-class from textural planning.

Per `rhythm_explain.md`, the accompanying voice starts on beat 2, not beat 1. This affects gap rhythm derivation:
- Lead voice: full gap duration from beat 1
- Accompany voice: gap duration minus one beat, from beat 2

**Implementation:** GapRhythm includes `start_beat` field, derived from textural assignment.

---

## Diagnostic Output

The rhythmic planner outputs traceable decisions:

```
Section: narratio (bars 5-12)
  Profile: Freudigkeit, density=high, inequality=mild, trajectory=arc
  Climax bar: 9
  
  Phrase 1 (bars 5-6): motif=dotted_drive
    Development: base (establish)
    Gap 0 (bar 5): [3/8, 1/8, 3/8, 1/8] slice 0.0-1.0
    Gap 1 (bar 6): [3/8, 1/8, 3/8, 1/8] slice 0.0-1.0
  
  Phrase 2 (bars 7-8): motif=dotted_drive_dim
    Development: diminuted
    Gap 2 (bar 7): [3/16, 1/16, 3/16, 1/16, 3/16, 1/16, 3/16, 1/16] slice 0.0-1.0
    Gap 3 (bar 8): [3/16, 1/16, 3/16, 1/16, 3/16, 1/16, 3/16, 1/16] slice 0.0-1.0

Variety checks:
  V-R001: PASS (no consecutive identical)
  V-R002: PASS (phrase 2 uses developed motif)
  V-R003: PASS (cadential rhythm differs)
  V-R004: PASS (density arc with peak at bar 9)
  V-R005: PASS (no phrase seams)
```

---

## References

- `rhythmic_planning.md`: Normative specification
- `rhythm_explain.md`: Beat-class composition design
- `architecture.md`: Seven-layer model
- `tonal_planning_upgrade.md`: Density coordination
- `figuration.md`: Layer 6.5 specification
- `laws.md`: Coding rules (especially A005, D001, L017)
- Cooper & Meyer, *The Rhythmic Structure of Music* (1960)
- Quantz, *Versuch einer Anweisung die Flöte traversiere zu spielen* (1752)
- Mattheson, *Der vollkommene Capellmeister* (1739)
