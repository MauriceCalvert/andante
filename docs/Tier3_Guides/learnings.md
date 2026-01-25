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

*Last updated: 2026-01-16*
