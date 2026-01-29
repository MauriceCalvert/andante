# Rhythm Complementarity: Beat-Class Composition

## Status

Design document for Phase 16: Rhythm fix and module refactoring.

---

## Problem Statement

When soprano and bass are both figurated (contrapuntal texture), they produce **parallel rhythm**: both voices attack at the same positions, creating a mechanical, non-baroque sound.

Example from current output (bars 9-14):
```
Bar 9:  Soprano: beat 1.5, 3.5    Bass: beat 1.5, 3.5   ← PARALLEL
Bar 10: Soprano: beat 1.5, 3.5    Bass: beat 1.5, 3.5   ← PARALLEL
Bar 11: Soprano: beat 1.5, 2.5... Bass: beat 1.5, 2.5...← PARALLEL
```

The current mitigation (`RHYTHM_STAGGER_OFFSET = 1/8`) shifts the non-lead voice by one eighth note. This fails because:

1. **Overflow**: Notes shifted past bar boundaries create timing errors
2. **Wrong emphasis**: Sparse passages (half notes) starting on beat 1.5 sound weak
3. **Still parallel**: Both voices have the same rhythm pattern, just offset

---

## Previous Failed Approaches

| Approach | Failure Mode |
|----------|--------------|
| Timeline stagger (RHYTHM_STAGGER_OFFSET) | Notes overflow bars; sparse passages get weak-beat emphasis |
| Beat-class quantisation | Both voices quantised to same grid → duplicate offsets |
| Onset coverage scoring | Complex machinery; bonus computed but discarded; schema sections bypassed |

All approaches share a common flaw: they try to **fix** rhythm after figuration, rather than **composing** correct rhythm from the start.

---

## Bach's Practice

In Bach's two-part inventions, rhythm complementarity arises from composition, not post-processing:

1. **Lead voice enters on beat 1** with the subject (dense figuration, many notes)
2. **Accompanying voice enters on beat 2** with supporting material (sparse figuration, fewer notes)
3. **Different material types**: Lead gets runs, turns, diminutions. Accompany gets sustained notes, simple arpeggios.

The key insight: **Bach composes the accompanying voice for a 3-beat window (beats 2-4), not a 4-beat window shifted by 1 beat.**

This means:
- The accompanying voice's durations naturally sum to 3 beats, not 4
- No notes overflow the bar
- Beat emphasis is correct (downbeat is beat 2, not beat 1.5)

---

## Solution: Beat-Class Composition

### Core Principle

Determine **at figuration time** whether each voice leads or accompanies in each bar. Compose material that fits the available beats from the start.

### Data Model

```
Lead voice:      | beat 1 | beat 2 | beat 3 | beat 4 |
                 |<-------- 4 beats available ------->|
                 
Accompany voice:          | beat 2 | beat 3 | beat 4 |
                          |<----- 3 beats available ->|
```

### Implementation

**FiguredBar gains `start_beat` field:**
```python
@dataclass(frozen=True)
class FiguredBar:
    bar: int
    degrees: tuple[int, ...]
    durations: tuple[Fraction, ...]
    figure_name: str
    start_beat: int = 1  # NEW: 1 for lead, 2 for accompany
```

**Figuration receives passage assignments:**
```python
def figurate(
    anchors: Sequence[Anchor],
    key: Key,
    metre: str,
    seed: int,
    density: str = "medium",
    affect_character: str = "plain",
    voice: str = "soprano",
    soprano_figured_bars: list[FiguredBar] | None = None,
    passage_assignments: Sequence[PassageAssignment] | None = None,  # NEW
) -> list[FiguredBar]:
```

**Per-bar logic:**
```python
lead_voice = get_lead_voice_for_bar(bar, passage_assignments)
voice_index = 0 if voice == "soprano" else 1

if lead_voice is None:
    # Equal: both on beat 1
    start_beat = 1
    effective_gap = gap_duration
elif lead_voice == voice_index:
    # This voice leads: beat 1, full gap
    start_beat = 1
    effective_gap = gap_duration
else:
    # This voice accompanies: beat 2, reduced gap
    start_beat = 2
    beat_value = Fraction(1, int(metre.split("/")[1]))
    effective_gap = gap_duration - beat_value
```

**Realisation uses start_beat directly:**
```python
bar_offset = _bar_beat_to_offset(anchor.bar_beat, beats_per_bar)
beat_value = Fraction(1, 4)  # quarter note in 4/4
note_offset = bar_offset + (figured_bar.start_beat - 1) * beat_value
```

### Density Adjustment

Accompanying voice uses one density level sparser:
- Affect says "high" → accompanying voice uses "medium"
- Affect says "medium" → accompanying voice uses "low"
- Affect says "low" → accompanying voice uses "low"

This ensures the accompanying voice has fewer, longer notes—matching baroque practice.

---

## Module Refactoring

The implementation requires touching `figurate.py` (550 lines) and `realisation.py` (450 lines). Both are unmaintainable. We refactor first.

### New Module Structure

```
builder/figuration/
├── figurate.py          # Entry points only (~100 lines)
├── bar_context.py       # Per-bar: beat_class, tension, function (~80 lines)
├── phrase.py            # Phrase position, deformation, schema sections (~100 lines)
├── cadential.py         # Cadential figure selection (~60 lines)
├── selector.py          # Filter functions only (~150 lines)
├── selection.py         # Selection pipeline, misbehaviour (~80 lines)
├── realiser.py          # Unchanged
├── strategies.py        # Unchanged
├── junction.py          # Unchanged
├── loader.py            # Unchanged
├── types.py             # Add start_beat field
└── bass.py              # Unchanged

builder/
├── realisation.py       # Slimmed (~200 lines)
├── realisation_bass.py  # Bass patterns, consonance (~150 lines)
├── realisation_util.py  # Offset conversion, passage lookup (~100 lines)
```

### Extraction Map

| Source | Functions | Destination |
|--------|-----------|-------------|
| figurate.py | `_detect_schema_sections`, `_in_schema_section` | phrase.py |
| figurate.py | `_determine_position_with_deformation`, `_select_phrase_deformation` | phrase.py |
| figurate.py | `_compute_harmonic_tension`, `_compute_bar_function`, `_compute_next_anchor_strength` | bar_context.py |
| figurate.py | `_select_cadential_figure`, `_cadential_to_figure`, `_cadential_minor_safe`, `_interval_to_approach_key` | cadential.py |
| selector.py | `apply_misbehaviour`, `sort_by_weight`, `select_figure` | selection.py |
| realisation.py | `_get_function_for_bar`, `_get_lead_voice_for_bar`, `_get_passage_end_offset`, `_get_expansion_for_bar` | realisation_util.py |
| realisation.py | `_bar_beat_to_offset`, `_get_beats_per_bar`, `_anchor_sort_key` | realisation_util.py |
| realisation.py | `_build_stacked_lyric`, `_get_bass_articulation` | realisation_util.py |
| realisation.py | Bass pattern blocks, `_adjust_downbeat_consonance`, `_is_dissonant_interval`, `_find_consonant_bass`, `_pitch_sounding_at` | realisation_bass.py |

---

## Implementation Phases

### Phase A: Refactor (no behaviour change)

1. Create new modules with extracted functions
2. Update imports
3. Verify no test failures
4. Commit: "refactor: extract figuration and realisation modules"

### Phase B: Beat-class implementation

1. Add `start_beat: int = 1` to `FiguredBar`
2. Add `passage_assignments` parameter to `figurate()`
3. Implement `compute_beat_class()` and `compute_effective_gap()` in `bar_context.py`
4. Update `figurate()` to use beat-class logic
5. Implement density reduction for accompanying voice
6. Update `realisation.py` to use `figured_bar.start_beat`
7. Remove `RHYTHM_STAGGER_OFFSET` from constants.py
8. Remove all stagger logic from `realisation.py`
9. Commit: "fix: beat-class composition for rhythm complementarity"

---

## Expected Outcome

After implementation, bars 7-14 (where bass leads, soprano accompanies) should show:

```
Bar 7:  Bass: beat 1.0, ...     Soprano: beat 2.0, ...   ← COMPLEMENTARY
Bar 8:  Bass: beat 1.0, ...     Soprano: beat 2.0, ...   ← COMPLEMENTARY
```

And bars 1-6 (where soprano leads, bass accompanies):

```
Bar 1:  Soprano: beat 1.0, ...  Bass: beat 2.0, ...      ← COMPLEMENTARY
Bar 2:  Soprano: beat 1.0, ...  Bass: beat 2.0, ...      ← COMPLEMENTARY
```

Passages with `lead_voice=None` (equal) have both voices on beat 1, accepting potential parallel rhythm in those sections (this is stylistically appropriate for episodes and development).

---

## Verification

Check `output/invention.note` after implementation:

1. **No overflow**: All notes end before bar boundary
2. **Correct beat emphasis**: Accompanying voice notes start on integer beats (2, 3, 4), not fractional (1.5, 2.5)
3. **Complementary rhythm**: Lead and accompany voices attack at different positions
4. **Sparse accompaniment**: Accompanying voice has fewer notes per bar than lead voice

---

## Document History

| Date | Change |
|------|--------|
| 2025-01-29 | Initial design based on failed approaches analysis |
