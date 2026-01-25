# Rhythm Refactor Brief

## Problem Summary

The current implementation has critical pipeline failures:

1. **Layer 5 (Thematic)** fills ALL 320 slots for BOTH voices with 1/16 notes
2. **Layer 6 (Textural)** runs AFTER pitch generation — too late to influence rhythm
3. **No voice independence** — bass mirrors soprano rhythm exactly
4. **No rhythm variety** — every note is 1/16, no longer values at arrivals

## Architectural Change: 6 Layers → 7 Layers

The old model had Textural after Thematic, which is backwards. Treatment assignments (which voice carries the subject) must be known before rhythm and pitch generation.

### Old Model (Broken)

```
L4 Metric → anchors
L5 Thematic → pitches (fills all slots, both voices)
L6 Textural → treatment labels (too late, barely used)
```

### New Model (Correct)

```
L4 Metric → anchors
L5 Textural → treatment assignments (voice roles per bar)
L6 Rhythmic → active slots and durations per voice
L7 Melodic → pitches for active slots only
```

## New 7-Layer Architecture

| Layer | Name | Input | Output |
|-------|------|-------|--------|
| 1 | Rhetorical | Genre | Trajectory, rhythm vocab, tempo |
| 2 | Tonal | Affect | Tonal plan, density, modality |
| 3 | Schematic | Tonal plan | Schema chain |
| 4 | Metric | Schema chain | Bar assignments, anchors |
| 5 | Textural | Genre + sections | Treatment assignments (voice roles per bar) |
| 6 | Rhythmic | Anchors + treatments + density | Active slots, durations per voice |
| 7 | Melodic | Active slots + anchors | Pitches |

Realisation assembles final notes from L6 durations + L7 pitches.

---

## Implementation Plan

### Phase 1: New Types in `builder/types.py`

Add these dataclasses:

```python
@dataclass(frozen=True)
class TreatmentAssignment:
    """Voice role assignment for a bar range."""
    start_bar: int
    end_bar: int
    treatment: str  # "subject", "answer", "episode", "cadential"
    subject_voice: int | None  # 0=soprano, 1=bass, None=both

@dataclass(frozen=True)
class RhythmPlan:
    """Output of Layer 6: which slots are active per voice."""
    soprano_active: frozenset[int]  # slot indices (0 to total_slots-1)
    bass_active: frozenset[int]
    soprano_durations: dict[int, Fraction]  # slot index -> duration
    bass_durations: dict[int, Fraction]
```

### Phase 2: Refactor `planner/textural.py` (Layer 5)

**Current:** Returns `TextureSequence` with schema-indexed treatments, runs after L5.

**New:** Returns `tuple[TreatmentAssignment, ...]` with bar ranges, runs before L6.

New function signature:

```python
def layer_5_textural(
    genre_config: GenreConfig,
    form_config: FormConfig,
) -> tuple[TreatmentAssignment, ...]:
    """Execute Layer 5: Determine voice roles per bar range."""
```

Logic for invention:
- Exordium bars 1-2: subject_voice=0 (soprano has subject)
- Exordium bars 3-4: subject_voice=1 (bass has answer)
- Narratio: subject_voice=None (episode, both voices active)
- Confirmatio: subject_voice=None (schematic)
- Peroratio: subject_voice=None (cadential)

### Phase 3: New `planner/rhythmic.py` (Layer 6)

**New file.** Determines active slots and durations per voice.

```python
def layer_6_rhythmic(
    anchors: list[Anchor],
    treatments: tuple[TreatmentAssignment, ...],
    density: str,
    total_bars: int,
    metre: str,
) -> RhythmPlan:
    """Execute Layer 6: Generate rhythm plan."""
```

Logic:
1. **Anchor slots** — always active in both voices, duration = 1/8 (quaver)
2. **Subject voice** — dense filling (75% of slots for "high" density)
3. **Accompaniment voice** — sparse filling (25-40% of slots), longer durations
4. **Episode/cadential** — moderate density both voices (50%)

Slot activation algorithm:

```python
SLOTS_PER_BAR = 16

for bar in range(1, total_bars + 1):
    treatment = get_treatment_for_bar(bar, treatments)
    bar_start_slot = (bar - 1) * SLOTS_PER_BAR
    
    for slot_in_bar in range(SLOTS_PER_BAR):
        slot = bar_start_slot + slot_in_bar
        is_strong_beat = slot_in_bar in (0, 8)  # beats 1 and 3 in 4/4
        is_anchor = slot in anchor_slots
        
        if is_anchor:
            # Both voices active at anchors
            soprano_active.add(slot)
            bass_active.add(slot)
            soprano_durations[slot] = Fraction(1, 8)
            bass_durations[slot] = Fraction(1, 8)
        elif treatment.subject_voice == 0:
            # Soprano has subject: soprano dense, bass sparse
            if should_activate(slot_in_bar, density="high"):
                soprano_active.add(slot)
                soprano_durations[slot] = Fraction(1, 16)
            if should_activate(slot_in_bar, density="low") or is_strong_beat:
                bass_active.add(slot)
                bass_durations[slot] = Fraction(1, 8) if is_strong_beat else Fraction(1, 16)
        elif treatment.subject_voice == 1:
            # Bass has subject: bass dense, soprano sparse
            # (mirror of above)
        else:
            # Both voices moderate
            if should_activate(slot_in_bar, density="medium"):
                soprano_active.add(slot)
                bass_active.add(slot)
```

### Phase 4: Modify `builder/greedy_solver.py`

**Current:** Iterates all offsets for all voices.

**New:** Only iterates active slots per voice.

Change `solve_greedy` signature:

```python
def solve_greedy(
    anchors: dict[tuple[Fraction, int], int],
    rhythm_plan: RhythmPlan,  # CHANGED from offsets: list[Fraction]
    config: GreedyConfig,
) -> GreedySolution:
```

Key changes:
1. Build separate offset lists per voice from `rhythm_plan.soprano_active` and `rhythm_plan.bass_active`
2. Iterate each voice independently
3. Look-ahead finds next anchor in that voice's active slots

### Phase 5: Rename `planner/thematic.py` → `planner/melodic.py` (Layer 7)

**Current:** Named thematic.py, generates all offsets, calls greedy solver, creates uniform 1/16 durations.

**New:** Named melodic.py, receives rhythm plan, passes to solver, uses rhythm plan durations.

```python
def layer_7_melodic(
    schema_chain: SchemaChain,
    affect_config: AffectConfig,
    key_config: KeyConfig,
    genre_config: GenreConfig,
    schemas: dict[str, SchemaConfig],
    total_bars: int,
    anchors: list[Anchor],
    rhythm_plan: RhythmPlan,  # NEW
) -> Solution:
```

In `_convert_solution`:
- Use `rhythm_plan.soprano_durations` and `rhythm_plan.bass_durations`
- Only include pitches for active slots

### Phase 6: Update `planner/planner.py`

Reorder layer calls:

```python
# Layer 4: Metric
bar_assignments, arrivals, total_bars = layer_4_metric(...)

# Layer 5: Textural (MOVED EARLIER)
treatments = layer_5_textural(genre_config, form_config)

# Layer 6: Rhythmic (NEW)
rhythm_plan = layer_6_rhythmic(
    arrivals, treatments, density, total_bars, genre_config.metre
)

# Layer 7: Melodic (was Thematic)
solution = layer_7_melodic(
    schema_chain, affect_config, key_config, genre_config,
    schemas, total_bars, arrivals, rhythm_plan
)
```

Remove old Layer 6 call. Update debug messages.

### Phase 7: Simplify `builder/realisation.py`

**Current:** Has rhythm state machine that tries to assign durations post-hoc.

**New:** Durations come from Solution (which got them from RhythmPlan). Realisation just assembles notes.

Remove:
- `RhythmState` logic
- Duration assignment in main loop
- The slot-skipping logic

Keep:
- `_merge_repeated_pitches`
- Lyric/annotation adding
- Note assembly

### Phase 8: Increase Tessitura Span

In `planner/melodic.py`:

```python
TESSITURA_SPAN: int = 18  # was 12
```

### Phase 9: Documentation Already Updated

`docs/Tier2_Architecture/architecture.md` updated to v1.5.0:
- Seven Layers model with L7 named "Melodic"
- Solver config moved to `solver_specs.md`

---

## File Change Summary

| File | Action | Est. Lines |
|------|--------|------------|
| `builder/types.py` | Add 2 dataclasses | +20 |
| `planner/textural.py` | Refactor to return TreatmentAssignment | ~60 rewrite |
| `planner/rhythmic.py` | New file | ~100 |
| `builder/greedy_solver.py` | Accept RhythmPlan, per-voice iteration | ~50 changes |
| `planner/thematic.py` | Rename to melodic.py, use rhythm_plan | ~40 changes |
| `planner/planner.py` | Reorder layers, new calls | ~30 changes |
| `builder/realisation.py` | Remove rhythm state machine | ~-40 (deletions) |

## Test Command

After each phase:

```
cd D:\projects\Barok\barok\source\andante
python -m scripts.run_pipeline pieces/freude_invention.yaml
```

## Success Criteria

1. Soprano has dense 1/16 runs in bars 1-2 (subject), bass has sparse accompaniment
2. Bass has dense 1/16 runs in bars 3-4 (answer), soprano has countersubject
3. Anchors have longer durations (1/8) in both voices
4. No uniform 1/16 wall-of-notes
5. Bass rhythm differs from soprano rhythm
6. Wider pitch range (tessitura span 18 vs 12)

---

## Execution Notes for Claude Code

1. Implement and test only at the end
2. Keep DEBUG output in planner.py to verify layer outputs
3. Type-hint everything per Maurice's standards
4. One class per file, methods alphabetical
5. Assert preconditions and tensor shapes
6. No blank lines inside functions
7. ≤100 lines per module unless splitting harms cohesion
