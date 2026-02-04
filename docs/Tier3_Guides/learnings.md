# Andante System Learnings

This document captures hard-won lessons from developing Andante. These are practical guidelines beyond what's in lessons.md.

---

## Key Design Decisions

### Why Two-Phase Expansion?

The system expands first (E3: degrees), then realises (E4: MIDI pitches). This separation is critical:

1. **Outer voices are expanded without knowing inner voice pitches** - they define the harmonic framework
2. **Inner voices are solved after outer voices** - they fill the framework with constraints
3. **Guards check realised MIDI pitches** - parallel motion detection needs concrete intervals

If we tried to check parallels during expansion (before realisation), we'd have to guess octaves. The slice solver resolves octaves based on voice-leading cost, so parallels can only be detected after.

### Why CP-SAT for Counter-Subject?

The counter-subject generator uses OR-Tools CP-SAT solver instead of random generation because:

1. **Hard constraints** (consonance, no parallels) are mathematically expressible
2. **Soft constraints** (contrary motion, step-compensation) map to weighted costs
3. **Invertibility** requires checking both orientations simultaneously
4. **Random generation** would require many retries to satisfy all constraints

### Why Branch-and-Bound for Inner Voices?

Inner voices use branch-and-bound (with CP-SAT fallback) because:

1. **Phrase-level scoring** - we want globally good solutions, not just locally valid ones
2. **Multiple candidates per slice** - each inner voice at each offset has multiple options
3. **Combinatorial space** - N slices × M voices × K candidates = too large for exhaustive search
4. **Pruning** - branch-and-bound can skip subtrees that can't beat current best

---

## Common Pitfalls

### Pitfall 1: Two Code Paths for Same Concept

**Wrong:**
```python
if texture == "polyphonic":
    result = polyphonic_inner_voice(...)
elif texture == "homophonic":
    result = homophonic_inner_voice(...)
```

**Right:**
```python
# Only candidate generation varies by texture
candidates = get_candidates(texture, ...)
# Filter/select is always the same
result = filter_and_select(candidates, ...)
```

BUG-001 was caused by polyphonic and homophonic having different code paths for steps 2-3.

### Pitfall 2: Checking at Wrong Level

**Wrong:** Check parallel motion at attack points (slice level)
**Right:** Check parallel motion at common offsets (voice-pair level)

The slice solver operates at attack points. Guards operate at common offsets. These are different timelines. When one voice sustains while another attacks, they don't align.

**Solution:** Inner-to-outer parallels are filtered at candidate generation (deterministic). Inner-to-inner parallels are caught by guards with backtracking (post-hoc).

### Pitfall 3: Try/Except as Flow Control

**Wrong:**
```python
try:
    value = lookup[key]
except KeyError:
    value = default
```

**Right:**
```python
value = lookup.get(key, default)
# Or:
if key in lookup:
    value = lookup[key]
```

Try blocks hide bugs. If a KeyError happens for a reason we didn't anticipate, we silently use the default instead of failing loudly.

### Pitfall 4: Downstream Fixes

**Wrong:**
```python
def fix_parallels(voices):
    # Adjust pitches to avoid parallels found after generation
    for violation in find_parallels(voices):
        voices[violation.voice][violation.offset] += 1
```

**Right:** Fix the generator so it doesn't produce parallels in the first place.

Downstream fixes don't work because:
- Fixing one violation may introduce another
- The fix logic doesn't understand musical intent
- Multiple passes may oscillate without converging

### Pitfall 5: Magic Numbers in Music

**Wrong:**
```python
if interval == 7:  # Perfect fifth
    return False
```

**Right:**
```python
if interval in PERFECT_CONSONANCES:  # Loaded from predicates.yaml
    return False
```

All musical constants should be in data files. Code should be generic.

---

## Guard System Lessons

### Guards Run at Phrase End

Guards don't run continuously during expansion. They run after a complete phrase is expanded and realised. Why:

1. **Partial phrases are incomplete** - checking parallels between 3 notes of an 8-note phrase is meaningless
2. **Some issues self-resolve** - a parallel motion that looks bad mid-phrase may be corrected by phrase end
3. **Performance** - running guards after every note is too expensive

### Guard Violations Map to Slices

When a guard fails, it reports an offset. The backtracking system maps that offset back to a slice index, then tries a different candidate for that slice.

```python
# Guard reports: parallel octave at offset 3/4
# Map to slice index: slice_for_offset(3/4) = 2
# Increment choice for slice 2
choice_indices[2] += 1
```

### Guards Are Not Generators

Guards detect problems. Generators prevent problems. If a guard frequently fails, the fix is in the generator, not in adding more guards.

---

## YAML Data Lessons

### Keep YAML < 50 Lines

When a YAML file grows beyond 50 lines, split it into a subdirectory:

```
data/
  treatments.yaml (50 lines - OK)
  genres/
    invention.yaml
    fantasia.yaml
    chorale.yaml
    ...
```

### YAML Is the Contract

The YAML plan is the interface between planner and executor. Both sides must agree on:

- Field names (vocabulary.md)
- Field types (grammar.md)
- Constraints (validator.py)

If planner produces a field the executor doesn't understand, that's a contract violation.

### Fractions in YAML

Durations are fractions like `1/4`, not floats like `0.25`. This avoids floating-point precision issues in music:

```yaml
# Good
durations: [1/4, 1/8, 1/8, 1/2]

# Bad
durations: [0.25, 0.125, 0.125, 0.5]
```

---

## Testing Lessons

### Test Against Truths, Not Implementation

**Wrong:**
```python
def test_expansion():
    result = expand_phrase(...)
    # Test that internal method was called
    assert mock_internal.called
```

**Right:**
```python
def test_expansion():
    result = expand_phrase(...)
    # Test observable output
    assert sum(result.durations) == budget
    assert all(d in VALID_DURATIONS for d in result.durations)
```

### Integration Tests Catch Real Bugs

Unit tests verify components. Integration tests verify the system. Most Andante bugs were caught by integration tests (`run_exercises.py`) not unit tests.

### Seed Reproducibility

Tests should be reproducible. Use explicit seeds:

```python
def test_with_seed():
    result = expand_phrase(..., seed=42)
    # Same seed = same output
```

---

## Performance Lessons

### CP-SAT Has Timeouts

The CP-SAT solver can hang on hard problems. Always use timeouts:

```python
solver.parameters.max_time_in_seconds = 5.0
status = solver.Solve(model)
if status == cp_model.UNKNOWN:
    # Fall back to branch-and-bound
```

### Cache Expensive Lookups

Loading YAML files on every function call is expensive:

```python
# Wrong: Loads file every call
def get_treatment(name):
    treatments = yaml.safe_load(open("treatments.yaml"))
    return treatments[name]

# Right: Module-level cache
_TREATMENTS = None
def get_treatment(name):
    global _TREATMENTS
    if _TREATMENTS is None:
        _TREATMENTS = yaml.safe_load(open("treatments.yaml"))
    return _TREATMENTS[name]
```

### Backtracking Has Limits

Set max retries on backtracking loops:

```python
MAX_RETRIES = 100
for retry in range(MAX_RETRIES):
    result = try_expansion(seed=retry)
    if guards_pass(result):
        return result
raise SpecError("Exhausted retries - check plan constraints")
```

If backtracking exhausts, it's a spec error (plan asks for something impossible), not a code bug.

---

## Counter-Subject Alignment

### Why CS Requires Direct Mode

The counter-subject (CS) is generated by CP-SAT to be consonant with the subject at **specific time alignments**. When both voices are expanded:

1. **Direct mode**: Both voices cycle their material without bar treatments. Alignment preserved.
2. **Bar treatments**: Each voice picks different treatments (statement, sequence, inversion...) independently. Alignment broken.

If soprano uses CS with direct mode but bass uses subject with bar treatments, the notes no longer align at the positions CP-SAT verified. Result: dissonances.

**Solution**: When ANY voice uses counter_subject, BOTH voices must use direct mode. The system auto-enforces this in `_enforce_direct_for_cs()`.

### Why bass_delay Is Forbidden with CS

CP-SAT generates CS for delay=0 alignment. If the treatment specifies `bass_delay: 1/2`:

- Soprano starts CS at t=0
- Bass starts subject at t=0.5
- At t=0.5, soprano is on CS note 2, bass is on subject note 0
- This is NOT the alignment CP-SAT verified

Bach's approach: test specific delays empirically after composing CS. We store `valid_delays` with each CS, but currently only delay=0 is generated as valid.

**Solution**: The system throws `InvalidDelayError` if a treatment specifies non-zero delay with counter_subject.

### Why Swapping Voices Doesn't Break Consonance

When roles swap (soprano plays CS, bass plays subject instead of vice versa):

- Interval class is symmetric: |A-B| = |B-A|
- A consonant interval remains consonant when inverted
- Voice ranges are handled by the realiser, not the expander

So `imitation_cs` (soprano=CS, bass=subject) is consonant IF both use direct mode AND delay=0.

---

## Leading Tone Resolution

### Fux vs Bach

**Fux III.2 (strict)**: The leading tone (degree 7) must resolve upward by step to the tonic. Every occurrence.

**Bach (practical)**: Leading tone resolution is mandatory at **cadences**. In melodic/sequential contexts, degree 7 moves freely like any other scale degree.

Examples of Bach-acceptable patterns:
- `7 -> 5 -> 3 -> 1` (scalar descent through leading tone)
- `7 -> 6 -> 5` (stepwise descent, no immediate tonic)
- `1 -> 7 -> 5` (neighbor motion, resolves later)

### Why cad_001 Must Be Cadence-Scoped

The original cad_001 guard checked ALL leading tones in the soprano. This caused false positives:

1. Subject with `[7, 5, 3, 1]` would flag the 7->5 as unresolved
2. Cycling subject material created more "violations"
3. Baroque melodies legitimately use 7 as passing tone

**Fix**: Only validate leading tone resolution for tonic-resolving cadences (authentic, plagal, deceptive). Half cadences end on V, not I, so leading tone resolution doesn't apply there. Non-cadential phrases allow free melodic motion through degree 7.

### Guard Context Requirements

Key context must flow to guards for accurate leading-tone detection:

1. `check_guards()` receives `key: Key` parameter
2. Passes `key.tonic_pc` to `run_guards()`
3. Leading tone check uses actual tonic, not hardcoded C major

Without key context, the guard would look for B (pitch class 11) in all keys, causing wrong-key false positives.

### dis_003 Leading Tone Detection Bug

The original `validate_dissonance` check for "resolved upward" used:
```python
if soprano_motion > 0 and interval != 11:  # WRONG
```

This checked if the interval between soprano and bass was 11 semitones. But a leading tone is defined by the soprano pitch class, not the interval above bass.

**Fix**: The wrapper `_check_dissonance_resolved_up` now filters using:
```python
leading_tone_pc = (tonic_pc + 11) % 12
if soprano_pitch % 12 == leading_tone_pc:
    continue  # Leading tone may resolve up
```

### Hidden Fifth/Octave Tolerance (vl_003/vl_004)

Fux I.15 forbids hidden fifths/octaves when soprano leaps (> 2 semitones). But Bach frequently used them with small leaps.

**Original check**: `soprano_motion > 2` (anything beyond a step)
**Fixed check**: `soprano_motion > 4` (anything beyond a third)

Baroque keyboard music commonly has hidden motion with soprano moving by third. Only larger leaps (fourths+) are flagged.

---

## Bach-Practical Guard Filtering

### Fux vs Bach Philosophy

**Fux (Species Counterpoint)**: Strict rules for pedagogical exercises. Every dissonance prepared, every leading tone resolved, every motion controlled.

**Bach (Baroque Practice)**: Musical expressivity over strict rules. Appoggiaturas, escape tones, free melodic motion, unprepared dissonances for affect.

### Guard Scoping Strategy

Rather than disabling strict rules globally, we **downgrade them to warnings** in non-cadential contexts. They remain **blockers at tonic-resolving cadences** (authentic, plagal, deceptive).

This maintains strict voice-leading at structural boundaries while allowing baroque freedom elsewhere, and preserves visibility of the issues.

```python
tonic_cadences = {"authentic", "plagal", "deceptive"}
fux_strict_guards = {
    "cad_001", "cad_002",              # Leading tone rules
    "dis_001", "dis_002", "dis_004", # Dissonance treatment
    "vl_003", "vl_004",                # Hidden motion
}
if phrase.cadence not in tonic_cadences:
    # Downgrade Fux-strict blockers to warnings
    diagnostics[i] = Diagnostic(..., severity="warning", ...)
```

### Guard Reference: Fux-Strict vs Always-Active

| Guard | Rule | Behavior | Note |
|-------|------|----------|------|
| cad_001 | Leading tone unresolved | Warning (non-cad) | Bach allows melodic 7 freely |
| cad_002 | Leading tone down | Warning (non-cad) | Bach allows 7→6 motion |
| dis_001 | Unprepared dissonance | Warning (non-cad) | Bach uses appoggiaturas |
| dis_002 | Unresolved dissonance | Warning (non-cad) | Bach uses free resolution |
| dis_003 | Dissonance up | Wrapper-filtered | Allows actual leading tones |
| dis_004 | Invalid weak-beat diss | Warning (non-cad) | Bach uses escape tones |
| vl_003 | Hidden fifth | Warning (non-cad) | Bach uses in keyboard music |
| vl_004 | Hidden octave | Warning (non-cad) | Bach uses in keyboard music |
| tex_001 | Parallel fifths | Always blocker | Universal prohibition |
| tex_002 | Parallel octaves | Always blocker | Universal prohibition |

### Files Implementing Bach-Practical Filtering

- `engine/realiser_guards.py`: Downgrades Fux-strict to warnings post-realisation
- `engine/inner_voice.py`: Downgrades for N-voice backtracking
- `engine/guards/registry.py`: dis_003 wrapper with leading-tone pitch-class filter
- `engine/voice_checks.py`: Hidden motion threshold relaxed to 4 semitones (major third)

---

## Direction-Aware Interval Computation

### The Problem: Degree-Only Interval Ambiguity

Schema degrees alone cannot determine interval direction unambiguously:

- Degree 1→7: could be sixth_up (+6 steps) or step_down (-1 step)
- Degree 7→1: could be step_up (+1 step) or sixth_down (-6 steps)

The original `compute_interval()` assumed the shortest path, which was wrong when schemas specified contrary motion.

**Example bug**: Bass schema do_re_mi with degrees `[1, 7, 1]` should descend C→B→C. But `compute_interval(1, 7)` returned `sixth_up` (diff=6), causing bass to leap up an octave instead of stepping down.

### The Fix: Signed Degrees in Schema YAML

Schemas now use signed degree notation:

```yaml
do_re_mi:
  soprano_degrees: ["1", "+2", "+3"]  # ascending
  bass_degrees: ["1", "-7", "1"]       # descending to 7, then up to 1
```

First degree is unsigned (entry point). Subsequent degrees use:
- `+N` = ascending to degree N
- `-N` = descending to degree N
- `N` (no sign) = same pitch class, direction from previous

### Implementation Chain

1. **schemas.yaml**: Signed degree strings
2. **config_loader.py**: `_parse_signed_degrees()` extracts directions tuple
3. **types.py**: `SchemaConfig` and `Anchor` have `*_directions` fields
4. **schema_anchors.py**: Propagates directions to each Anchor
5. **selector.py**: `compute_interval_with_direction()` uses direction to resolve ambiguity

### Key Function: compute_interval_with_direction()

```python
def compute_interval_with_direction(degree_a, degree_b, direction):
    if direction == "down" and diff > 0:
        diff = diff - 7  # Wrap to negative
    elif direction == "up" and diff < 0:
        diff = diff + 7  # Wrap to positive
```

This ensures degree 1→7 with direction="down" yields diff=-1 (step_down), not diff=6 (sixth_up).

---

## Figure Rejection Debugging

### The Problem: Cryptic Error Messages

The original `FigureRejectionError` produced output like:

```
All figures rejected at bar 12 (interval=step_up, mode=FIGURATION):
  circolo_up note[7] exit_degree=-2 @end: exit_mismatch(expected=1, got=-2)
  circolo_up note[0] DiatonicPitch(step=31) @0: melodic_interval(tritone)
```

This was hard to diagnose because:
1. Reason codes were terse ("exit_mismatch", "melodic_interval")
2. Offsets were raw fractions, not musical positions
3. No grouping by reason — all rejections listed linearly
4. Interval names were internal codes ("step_up"), not readable ("ascending 2nd")

### The Fix: Human-Readable Formatting

Restructured `FigureRejectionError._format_message()` to:

1. **Group rejections by reason** — see all "melodic leap" failures together
2. **Expand reason codes** — "range(48-72)" becomes "pitch outside instrument range (48-72)"
3. **Translate interval names** — "step_up" becomes "ascending 2nd"
4. **Format offsets** — "0" becomes "start of figure", "end" stays "end of figure"
5. **Limit per-reason output** — show 5 examples, then "... and N more"

New output:

```
======================================================================
FIGURE REJECTION at bar 12
  Mode: FIGURATION
  Interval: ascending 2nd
  Attempted 5 figure(s), all rejected:
----------------------------------------------------------------------

  figure exit degree wrong: expected=1, got=-2:
    - circolo_up: note 7 (exit_degree=-2) at end of figure

  melodic leap too large: tritone:
    - circolo_up: note 0 (DiatonicPitch(step=31)) at start of figure
    - lower_neighbor_up: note 0 (DiatonicPitch(step=31)) at start of figure
    - direct_step_up: note 0 (DiatonicPitch(step=31)) at start of figure
======================================================================
```

### Files Changed

- `builder/types.py`: Added `_INTERVAL_NAMES`, `_expand_reason()`, `_format_offset()`, rewrote `FigureRejectionError._format_message()`

---

## Chainable Figure Bug

### The Problem: Oscillating Figures Cannot Chain

The `_tile_degrees()` function chains figures by repeating a base unit and accumulating offsets:

```python
for _ in range(repetitions):
    for deg in base:
        result.append(deg + offset)
    offset = result[-1]  # Last degree becomes new offset
```

This works for **progressive** figures where each unit advances toward the target:
- `filled_third_up`: `[0, 1, 2]` — unit `[0, 1]` chains as `[0, 1, 1, 2]` ✓

It fails for **oscillating** figures that return to their starting point:
- `circolo_up`: `[0, 1, 0, -1, 0, 1]` with chain_unit=4
- Base unit: `[0, 1, 0, -1]` — ends at -1, not 0
- Tiled for 8 notes: `[0, 1, 0, -1, -1, 0, -1, -2]` — exit at -2, not +1

The figure oscillates around 0 but the offset accumulates the wrong direction.

### Root Cause Analysis

The error manifested as:
```
FIGURE REJECTION at bar 12
  figure exit degree wrong: expected=1, got=-2
```

Initial misdiagnosis: thought it was a planner problem (anchor placement creating tritones). Added validation to `place_anchors_in_tessitura()` that rejected anchors creating tritone intervals.

But **anchor-level tritones are valid** — the figuration fills them stepwise. A tritone between degree 4 and degree 7 becomes a scalar run `[4, 5, 6, 7]`, no melodic tritone.

The actual bug: chainable figures with oscillating contours cannot be tiled because their base unit doesn't end at the interval they're supposed to traverse.

### Figures Affected

All oscillating figures had incorrect `chainable: true`:

| Figure | Degrees | chain_unit | Base Unit Exit | Expected Exit |
|--------|---------|------------|----------------|---------------|
| circolo_up | [0,1,0,-1,0,1] | 4 | -1 | +1 |
| circolo_down | [0,-1,0,1,0,-1] | 4 | +1 | -1 |
| turn_static | [0,1,0,-1,0] | 4 | -1 | 0 |
| trill_static | [0,1,0,1,0] | 2 | +1 | 0 |

### The Fix

Set `chainable: false` for all oscillating figures in `data/figuration/diminutions.yaml`.

Chaining only works for figures where:
1. The base unit ends at a degree that progresses toward the target interval
2. Accumulated offset correctly reaches the expected exit degree

No oscillating/circling figures meet this criterion.

### Architectural Insight

The chaining algorithm assumes **monotonic progression**. Oscillating figures are inherently non-monotonic. Rather than complicate the tiling logic with special cases, the correct fix is to mark these figures as non-chainable.

If longer oscillating patterns are needed, define them explicitly:
```yaml
- name: circolo_up_extended
  degrees: [0, 1, 0, -1, 0, 1, 0, -1, 0, 1]  # 10 notes, explicit
  chainable: false
```

### Files Changed

- `data/figuration/diminutions.yaml`: Set `chainable: false` for circolo_up, circolo_down, turn_static, trill_static
- `shared/pitch.py`: Removed overly strict anchor validation (tritones between anchors are valid when filled by figuration)

---

## Anchor Tritones vs Figure Tritones

### Key Distinction

**Anchor-level tritone**: The interval between consecutive schema anchor pitches is a tritone (e.g., B3 to F4). This is **valid** because figuration fills the gap with stepwise motion.

**Figure-level tritone**: The melodic interval between the previous note and the first note of a new figure is a tritone. This is **invalid** because it creates an exposed tritone leap.

### Why the Confusion

The error message "melodic leap too large: tritone" appeared at "note 0 at start of figure". This could mean:

1. Bad anchor placement (planner bug) — anchors too far apart
2. Bad figure chaining (data bug) — figure exit doesn't reach target
3. Genuine constraint conflict — no valid figuration exists

The message didn't distinguish these cases.

### Diagnostic Approach

1. **Check exit degree first**: If figures fail with "exit_mismatch", the figure data is wrong
2. **Check melodic interval**: If figures fail at note 0 with "melodic_interval", trace back to what produced the previous note
3. **Check anchor sequence**: If anchors are correctly placed but tritone appears, the previous figure ended in the wrong octave

### When to Validate at Which Level

| Check | Level | Action |
|-------|-------|--------|
| Anchor degrees form valid schema | Planner | Assert schema degrees are in YAML |
| Anchor MIDI pitches in range | Planner | `place_anchor_pitch()` constrains to voice range |
| Figure exit matches interval | Figure data | Ensure degrees[-1] equals interval offset |
| Melodic interval to figure start | Builder | `candidate_filter()` checks prev_midi to first note |

Don't validate anchor-to-anchor intervals as melodic leaps — they're not performed directly.

---

## Deferred MIDI Resolution

### The Problem: Premature Octave Decisions

The original architecture resolved anchor degrees to MIDI pitches early in the pipeline:

```
Planner -> place_anchors_in_tessitura() -> Anchors with MIDI -> Builder
```

This created several problems:

1. **No context for octave choice**: When placing anchor N, we don't know where the figuration for anchor N-1 will end
2. **Forced bad intervals**: Pre-resolved MIDI might create tritones or awkward leaps that figuration can't fix
3. **Direction hints ignored**: Schema direction hints (up/down) couldn't influence octave selection

### The Solution: Defer to Fill Time

New architecture resolves MIDI at the moment of use:

```
Planner -> Anchors with degrees + direction hints -> Builder -> resolve at fill time
```

**PlanAnchor** now contains only:
- `upper_degree`, `lower_degree` (1-7)
- `upper_direction`, `lower_direction` (up/down/same/None)
- `local_key`, `bar_beat`, `schema`, `stage`, `section`

**VoiceWriter._resolve_anchor_pitch()** resolves degree to MIDI using:
1. Previous note's actual MIDI (known at resolution time)
2. Direction hint from the anchor
3. Voice range constraints

### Resolution Algorithm

```python
def _place_degree_with_direction(key, degree, prev_midi, direction, range):
    # Get all valid octave placements for this degree
    candidates = [key.degree_to_midi(degree, oct) for oct in range(10)
                  if range.low <= midi <= range.high]
    
    if direction == "up":
        # Pick lowest candidate above prev_midi
        above = [m for m in candidates if m > prev_midi]
        return min(above) if above else max(candidates)
    
    if direction == "down":
        # Pick highest candidate below prev_midi
        below = [m for m in candidates if m < prev_midi]
        return max(below) if below else min(candidates)
    
    # No direction: pick closest to prev_midi
    return min(candidates, key=lambda m: abs(m - prev_midi))
```

### Example: Degree 1 → Degree 7

With C5 (72) as previous note:
- `direction=None`: resolves to B4 (71) - closest
- `direction="down"`: resolves to B4 (71) - below C5
- `direction="up"`: resolves to B5 (83) - above C5

This ensures the schema's intended motion is preserved.

### Files Changed

- `shared/plan_types.py`: Removed `upper_pitch`, `lower_pitch`, `upper_midi`, `lower_midi` from `PlanAnchor`; `AnacrusisPlan.target_pitch` → `target_degree`; `VoicePlan.tessitura_median` is now `int` (MIDI)
- `planner/voice_planning.py`: Removed `place_anchors_in_tessitura()` call; `_compute_interval()` and `_is_ascending()` now use degrees + direction hints
- `builder/voice_writer.py`: Added `_resolve_anchor_pitch()`, `_place_degree_near_median()`, `_place_degree_with_direction()`; updated `_compose_independent()`, `_compose_sequenced()`, `_compose_anacrusis()`
- `builder/types.py`: Removed `upper_midi`, `lower_midi` from `Anchor`
- `shared/pitch.py`: `place_anchors_in_tessitura()` now unused (can be removed)

### Why This Is Better

1. **Context-aware**: Octave decisions made with knowledge of actual previous pitch
2. **Direction-respecting**: Schema motion preserved (ascending stays ascending)
3. **Eliminates class of bugs**: No more pre-resolved octaves creating impossible figuration
4. **Simpler contract**: Planner only deals with degrees, builder handles MIDI

---

*Last updated: 2026-02-03*
