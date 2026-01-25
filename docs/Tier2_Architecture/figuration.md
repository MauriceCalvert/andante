# Figuration Design

## Overview

Layer 6.5 (Figuration) elaborates structural tones provided by schemas into idiomatic baroque melodic lines. Patterns derive from Quantz's *Versuch einer Anweisung die Flöte traversiere zu spielen* (1752) and CPE Bach's *Versuch über die wahre Art das Clavier zu spielen* (1753).

## Relationship to Other Layers

```
L4 Metric          →  anchors: soprano/bass MIDI at bar.beat positions
L5 Textural        →  treatment assignments: voice roles per bar
L6 Rhythmic        →  active slots + durations per voice
L6.5 Figuration    →  pitch sequences from pattern vocabulary  <-- THIS LAYER
counterpoint.py    →  validation (reject/retry if violations)
Realise            →  NoteFile
```

Figuration sits between rhythmic planning (which slots are active) and realisation (final notes). It replaces the CP-SAT solver's arbitrary pitch selection with authentic baroque patterns.

**Note:** The CP-SAT solver (L7 Melodic) is orphaned — kept in codebase but not called.

## File Structure

Three files work together:

| File | Content | Purpose |
|------|---------|---------|
| `figurations.yaml` | 42 complete pattern definitions | Pattern vocabulary |
| `figuration_profiles.yaml` | Named groupings of patterns | Reusable presets |
| `schemas.yaml` | Schema definitions referencing profiles | Harmonic skeletons |

This separates concerns:
- Pattern mechanics (figurations.yaml) — stable, from treatises
- Usage groupings (figuration_profiles.yaml) — reusable across schemas
- Harmonic content (schemas.yaml) — schema-specific

### Similarly-Named Files (Clarification)

| File | Purpose | Layer |
|------|---------|-------|
| `figurations.yaml` | Melodic elaboration patterns | L6.5 |
| `figuration_profiles.yaml` | Groupings of pattern names | L6.5 |
| `accompaniments.yaml` | Bass patterns when role is accompaniment | L6.5 |
| `figurae.yaml` | Figurenlehre — rhetorical figures mapped to affects | L1 |
| `figures.yaml` | Figured bass symbols (6, 6/4, 7, 4-3) | L7 |

## Voice Role Handling

Bass voice pattern source depends on texture role (from L5):

| Voice | Role | Pattern source |
|-------|------|----------------|
| Soprano | always | `figurations.yaml` via profile |
| Bass | thematic/leader | `figurations.yaml` via profile |
| Bass | accompaniment | `accompaniments.yaml` |

This follows existing texture definitions in `textures.yaml`:
- `polyphonic`, `baroque_invention`: bass is thematic → full figuration
- `homophonic`, `melody_accompaniment`: bass is accompaniment → simpler patterns

## Gap Filling Model

Anchor spacing is always integer beats (2 beats in 4/4, 3 beats in 3/4). Patterns from treatises are shorter (typically 1-1.5 beats). Gaps decompose into chained patterns:

```
[hold A (leftover)] → [ornament on A] → [diminution to B] → [anchor B]
```

The `function` field distinguishes pattern roles:

| Function | Purpose | When selected |
|----------|---------|---------------|
| ornament | Decorates held tone | On anchor A pitch |
| diminution | Connects two tones | Arriving at anchor B |
| cadential | Phrase-ending connection | Final connection when cadence_approach=true |

**Selection process:**

1. Calculate gap duration (anchor_B.offset - anchor_A.offset)
2. Select diminution pattern arriving at B (filter: duration ≤ gap)
3. Calculate remaining time
4. Select ornament pattern on A (filter: duration ≤ remaining)
5. Any leftover: hold anchor A pitch

No scalar fill. All figuration.

**Example: 2-beat gap**

```
Gap: 2 beats
Selected diminution: circolo_mezzo_down (1 beat)
Remaining: 1 beat
Selected ornament: mordent (0.75 beats)
Leftover: 0.25 beats → hold

Result: [hold A 0.25] → [mordent 0.75] → [circolo_mezzo 1.0] → [arrive B]
```

## Cadential Detection

Use **cadential** pattern list (instead of **interior**) when both conditions met:

1. Schema has `cadence_approach: true`
2. AND this is final connection (from stage N-1 to stage N)

**Example: Prinner schema**

```yaml
prinner:
  soprano_degrees: [4, 3, 2, 1]   # 4 stages → 3 connections
  cadence_approach: true
  figuration_profile: stepwise_descent
```

| Connection | Stages | Cadential? | Pattern source |
|------------|--------|------------|----------------|
| 4→3 | 0→1 | No | `interior` |
| 3→2 | 1→2 | No | `interior` |
| 2→1 | 2→3 | Yes | `cadential` |

Final connection gets `cadential_trill` or `cadential_tirata` instead of plain `circolo_mezzo_down`.

## Pattern Definition (figurations.yaml)

Each figuration defines complete pattern mechanics:

```yaml
circolo_mezzo_down:
  description: Half-circle descending - up-down-down (Quantz)
  offset_from_target: [1, 2, 1, 0]
  notes_per_beat: 4
  metric: weak
  function: diminution
  approach: step_above
  energy: medium
```

### Fields

**offset_from_target** — Sequence of scale degrees relative to destination tone. `0` is always the target. Signs indicate direction from target:
- Positive = above target
- Negative = below target
- Example: `[1, 2, 1, 0]` means "one above, two above, one above, arrive at target"

**notes_per_beat** — Rhythmic density. A 4-note pattern at `notes_per_beat: 4` fills one beat. Pattern duration = len(offset_from_target) / notes_per_beat.

**metric** — Beat placement constraint:
- `strong` — Must begin on beat
- `weak` — Must begin off beat
- `across` — Spans beat or barline

**function** — Musical role:

| Value | Purpose | When selected |
|-------|---------|---------------|
| ornament | Decorates single held tone | Remaining time after diminution |
| diminution | Connects two structural tones | Between schema degrees |
| cadential | Phrase endings | Final connection before cadence |
| sequential | Repetition at different pitch | Episodes, continuation |

**approach** — Constraint on preceding tone:

| Value | Meaning |
|-------|---------|
| step_above | Previous note one step higher |
| step_below | Previous note one step lower |
| leap_above | Previous note leap higher |
| leap_below | Previous note leap lower |
| repeated | Previous note same pitch |
| any | No constraint |

**energy** — Links to L1 tension. High-energy patterns (tirata_long, tremolo) for climaxes; low-energy (nachschlag, mordent) for relaxation.

### Pattern Categories

| Category | Count | Examples |
|----------|-------|----------|
| Ornamental | 12 | mordent, schneller, pralltriller, trillo, doppelschlag |
| Diminution | 14 | tirata, circolo_mezzo, groppo, passaggio, broken_third |
| Cadential | 5 | cadential_trill, cadential_turn, cadential_tirata |
| Sequential | 5 | sequence_step_down, sequence_third_up, rosalia |
| Sustained | 4 | batterie, tremolo, bariolage, pedal_figuration |

## Profile Definition (figuration_profiles.yaml)

Profiles group pattern names for common musical contexts:

```yaml
stepwise_descent:
  description: Descending by step (prinner, rule_of_octave_desc)
  interior: [circolo_mezzo_down, groppo_down, passaggio_down, mordent, doppelschlag]
  cadential: [cadential_trill, cadential_turn, cadential_gruppetto]

sequence_descending:
  description: Descending sequences (fonte)
  interior: [sequence_step_down, sequence_third_down, passaggio_down]
  cadential: [cadential_trill, cadential_turn]
```

### Profile Categories

| Category | Profiles |
|----------|----------|
| Stepwise | stepwise_descent, stepwise_ascent, stepwise_mixed |
| Sequential | sequence_descending, sequence_ascending |
| Static | repeated_tone, pedal |
| Leap | leap_descent, leap_ascent |
| Virtuosic | virtuosic_descent, virtuosic_ascent |
| Compound | galant_general, episode_general |

## Schema-Figuration Linkage (schemas.yaml)

Schemas reference profiles by name, with optional per-connection overrides:

```yaml
prinner:
  description: Stepwise descent to cadence
  bass_degrees: [6, 5, 4, 3]
  soprano_degrees: [4, 3, 2, 1]
  bars: 2
  cadence_approach: true
  figuration_profile: stepwise_descent
  figuration_override:
    "2->1": [cadential_tirata]
```

### Fields

**figuration_profile** — Name from figuration_profiles.yaml. Provides default interior and cadential lists.

**figuration_override** — Per-connection exceptions using arrow notation. Soprano degree before arrow → soprano degree after arrow.

## Selection Filter Order

For each anchor pair (A → B):

1. **Direction** — ascending/descending/static (from pitch comparison)
2. **Approach** — step_above, step_below, etc. (from previous note)
3. **Duration** — pattern_duration ≤ gap_duration
4. **Metric** — strong/weak/across (from beat position)
5. **Energy** — low/medium/high (from affect)
6. **Function** — ornament/diminution/cadential (from position)

## Validation

After figuration produces pitch sequences:

1. `counterpoint.validate_passage()` checks:
   - Parallel fifths/octaves/unisons
   - Strong-beat consonance
   - Pitch-class membership (diatonic)
   - Voice range

2. If violations: reject pattern, try next candidate from filtered list

3. If all candidates fail: fall back to hold (degenerate case)

## Usage Context

**Galant/Dance** — Figuration-heavy. Schemas provide skeleton; figurations provide flesh. Mostly selection with local validation, not constraint solving.

**Fugue** — Figuration-light. Used in episodes and cadences only. Subject, answer, counter-subject governed by counterpoint rules.

**Invention** — Mixed. Subject entries use full figuration. Episodes may use lighter patterns.

## Future: Interest Mechanisms

Current design yields correct but potentially bland output. Deferred enhancements:
- Motif registry with callback requirements
- Personality profiles (consistent quirks per piece)
- Strategic surprise placement
- Generate-and-rank by interest metrics
