# Figuration Integration Plan

## Problem Statement

Current output (e.g. `freude_invention.note`) fills bars with generic stepwise motion. The CP-SAT solver in L7 optimises for minimal leaps but has no concept of idiomatic baroque patterns.

Example from bar 1:
```
C5-D5-E5-C5-D5-E5-C5-D5-C5-B4-A4-G4-F4-E4-D4
```
This is correct but bland — not recognisable as baroque figuration.

## Current Pipeline

```
L1 Rhetorical  → trajectory, rhythm_vocab, tempo
L2 Tonal       → tonal_plan, density, modality
L3 Schematic   → schema_chain (sequence of schema names)
L4 Metric      → anchors (fixed pitch points at bar.beat positions)
L5 Textural    → treatment assignments (voice roles)
L6 Rhythmic    → active slots, durations per voice
L7 Melodic     → pitches for all active slots (CP-SAT solver)
Realise        → NoteFile
```

Key observation: L4 produces **anchors** (sparse, e.g. 2-4 per bar). L6 produces **active slots** (dense, 16 per bar at 1/16 resolution). L7 fills the gap by letting CP-SAT choose pitches freely, constrained only by:
- Anchors (fixed)
- Stepwise motion preference (soft cost)
- Parallel fifth/octave prohibition (hard)

## Proposed Change

Insert **figuration selection** between L4 anchors and L7 pitch assignment. Instead of CP-SAT choosing arbitrary stepwise pitches, figuration patterns dictate the pitch sequence between consecutive anchors.

### New Layer: L6.5 Figuration

```
L4 Metric      → anchors
L5 Textural    → treatment assignments
L6 Rhythmic    → active slots, durations
L6.5 Figuration → pitch_sequence per anchor pair  <-- NEW
counterpoint.py → validation (reject/retry if violations)
Realise        → NoteFile
```

CP-SAT solver (L7) is **orphaned** — kept in codebase but not called.

## Data Flow

### Input to L6.5
- Consecutive anchor pairs: (anchor_A, anchor_B)
- Schema context: which schema this connection belongs to
- Metric position: bar.beat of anchor_A
- Energy level: from affect
- Texture: voice roles from L5

### Voice Role Handling

Bass voice pattern source depends on texture role:

| Voice | Role | Pattern source |
|-------|------|----------------|
| Soprano | always | `figurations.yaml` via profile |
| Bass | thematic/leader | `figurations.yaml` via profile |
| Bass | accompaniment | `accompaniments.yaml` |

This follows existing texture definitions in `textures.yaml`:
- `polyphonic`, `baroque_invention`: bass is thematic → full figuration
- `homophonic`, `melody_accompaniment`: bass is accompaniment → simpler patterns

### Gap Filling Model

Anchor spacing is integer beats (2 beats in 4/4, 3 beats in 3/4). Patterns are shorter (typically 1-1.5 beats). Gaps decompose into chained patterns:

```
[hold A (leftover)] → [ornament on A] → [diminution to B] → [anchor B]
```

The `function` field distinguishes:
- `ornament` — decorates held tone (mordent, trill, doppelschlag)
- `diminution` — connects to next tone (circolo, tirata, groppo)
- `cadential` — phrase-ending connection (cadential_trill, cadential_turn)

**Selection process:**
1. Calculate gap duration (anchor_B.offset - anchor_A.offset)
2. Select diminution pattern arriving at B (filter: duration ≤ gap)
3. Calculate remaining time
4. Select ornament pattern on A (filter: duration ≤ remainder)
5. Any leftover: hold A

No scalar fill. All figuration.

### Cadential Detection

Use **cadential** pattern list (instead of **interior**) when both conditions met:
- Schema has `cadence_approach: true`
- AND this is final connection (stage == len(soprano_degrees) - 1)

**Example: Prinner schema**

```yaml
prinner:
  soprano_degrees: [4, 3, 2, 1]   # 4 stages
  cadence_approach: true
  figuration_profile: stepwise_descent
```

| Connection | Stages | Cadential? | Pattern source |
|------------|--------|------------|----------------|
| 4→3 | 0→1 | No | `interior` |
| 3→2 | 1→2 | No | `interior` |
| 2→1 | 2→3 | Yes | `cadential` |

Final connection gets `cadential_trill` instead of `circolo_mezzo_down`.

### Selection Filter Order

For each anchor pair (A → B):

1. **Direction** — ascending/descending/static (from pitch comparison)
2. **Approach** — step_above, step_below, etc. (from previous note)
3. **Metric** — strong/weak/across (from beat position)
4. **Duration** — pattern_duration ≤ gap_duration
5. **Energy** — low/medium/high (from affect)
6. **Function** — ornament/diminution/cadential (from position)

### Realisation

Convert pattern to concrete pitches:
- `offset_from_target` + target pitch → MIDI pitches
- Pattern length + `notes_per_beat` → durations

### Validation

After figuration produces pitch sequence:
- `counterpoint.validate_passage()` checks parallels, consonance, range
- If violations: reject pattern, try next candidate
- If all candidates fail: fall back to hold (degenerate case)

## Schema YAML Changes

Add to each schema in `schemas.yaml`:

```yaml
prinner:
  soprano_degrees: [4, 3, 2, 1]
  bass_degrees: [6, 5, 4, 3]
  cadence_approach: true
  figuration_profile: stepwise_descent
  figuration_override:
    "2->1": [cadential_tirata]
```

The override uses arrow notation: soprano degree before → soprano degree after.

## File Changes Required

### New Files

| File | Purpose |
|------|---------|
| `planner/figuration.py` | L6.5 implementation |
| `planner/figuration_loader.py` | Load YAML, validate |

### Modified Files

| File | Change |
|------|--------|
| `data/schemas.yaml` | Add `figuration_profile` to each schema |
| `planner/planner.py` | Insert L6.5 call, remove L7 call |

### Existing Files (no change needed)

| File | Status |
|------|--------|
| `data/figurations.yaml` | Already complete (42 patterns) |
| `data/figuration_profiles.yaml` | Already complete (14 profiles) |
| `data/accompaniments.yaml` | Already complete (bass patterns) |
| `builder/counterpoint.py` | Used for validation |
| `builder/solver.py` | Orphaned, kept for future |

## Implementation Order

### Phase 1: Loader and Validator
1. Create `figuration_loader.py`
2. Load `figurations.yaml` into FigurationPattern dataclass
3. Load `figuration_profiles.yaml` into FigurationProfile dataclass
4. Validate: all pattern names in profiles exist in figurations

### Phase 2: Schema Linkage
1. Add `figuration_profile` to 3 schemas: prinner, monte, do_re_mi
2. Update schema loader to parse new fields
3. Test: schema loads with profile reference

### Phase 3: Selection Logic
1. Create `figuration.py` with `select_figuration()`
2. Implement filter chain: direction, approach, metric, duration, energy, function
3. Implement gap decomposition: diminution + ornament + hold
4. Test: selection respects constraints

### Phase 4: Realisation
1. Create `realise_figuration()` in `figuration.py`
2. Input: pattern, target pitch, key
3. Output: list of (midi, duration) tuples
4. Test: circolo_mezzo_down from E5 produces correct sequence

### Phase 5: Integration
1. Add L6.5 call in `planner.py`
2. Add counterpoint validation after figuration
3. Remove L7 solver call
4. Verify output has baroque character

### Phase 6: Complete Coverage
1. Add `figuration_profile` to all schemas
2. Add `figuration_override` where needed
3. Implement bass accompaniment pattern selection
4. Final validation

## Success Criteria

1. `freude_invention.note` contains recognisable baroque figures
2. Figures follow Quantz/CPE Bach patterns from treatises
3. Direction matches schema trajectory (descending prinner descends)
4. Cadential patterns appear at phrase endings
5. Gaps filled with ornament + diminution chains, no scalar fill
6. Bass uses accompaniment patterns when role is accompaniment
7. No increase in counterpoint rule violations
