# Subject Generation Algorithm

This document specifies the complete rules and constraints for generating fugue subjects, answers, and countersubjects in Andante.

## Overview

Subject generation follows a **head + tail construction** method inspired by Baroque compositional practice:

1. **Head**: The memorable opening gesture (3-6 notes)
2. **Tail**: The continuation leading to resolution (3-12 notes)
3. **Subject**: Head + Tail combined (spans exactly 1-4 bars)
4. **Answer**: The subject transposed to the dominant, with tonal mutations
5. **Countersubject**: A complementary melody that works with both subject and answer

---

## 1. Head Generation

**Source**: `motifs/head_generator.py`

### 1.1 Pitch Constraints

| Constraint | Value | Rationale |
|------------|-------|-----------|
| `MIN_LEAP` | 3 scale degrees | Must have at least one "leap" interval |
| `MAX_INTERVAL` | 7 scale degrees | No interval larger than an octave |
| `MIN_DEGREE` | 0 | Lowest allowed scale degree (0-indexed) |
| `MAX_DEGREE` | 14 | Highest allowed (two octaves above tonic) |
| `START_DEGREES` | (0, 2, 4) | Must start on tonic triad (1, 3, or 5) |

### 1.2 Validity Rules (Music Cognition Based)

A head is valid if and only if:

1. **Leap Requirement**: Contains at least one interval ≥ 3 scale degrees
2. **Gap Fill**: The largest leap is immediately followed by contrary stepwise motion (interval of 1 or 2 in opposite direction)
3. **Rhythm Variety**: Uses at least 2 distinct note durations

### 1.3 Rhythm Cells by Metre

Rhythm cells define the durational patterns for heads. Durations are expressed as fractions of a whole note.

#### 4/4 Time (head duration: 0.75–1.0 bar)

| Notes | Durations | Name |
|-------|-----------|------|
| 4 | (0.25, 0.125, 0.125, 0.25) | long-short-short-long |
| 4 | (0.125, 0.25, 0.125, 0.25) | short-long-short-long |
| 4 | (0.375, 0.125, 0.125, 0.125) | dotted-run |
| 4 | (0.25, 0.25, 0.25, 0.25) | quarters |
| 4 | (0.375, 0.125, 0.25, 0.25) | dotted-quarters |
| 4 | (0.25, 0.125, 0.125, 0.5) | short-to-long |
| 4 | (0.5, 0.125, 0.125, 0.25) | long-to-short |
| 5 | (0.25, 0.125, 0.0625, 0.0625, 0.25) | long-short-ornament |
| 5 | (0.125, 0.125, 0.125, 0.25, 0.125) | run-accent |
| 5 | (0.25, 0.25, 0.125, 0.125, 0.25) | quarters-run |
| 5 | (0.25, 0.125, 0.125, 0.25, 0.25) | run-quarters |
| 5 | (0.375, 0.125, 0.125, 0.125, 0.25) | dotted-run-quarter |
| 5 | (0.25, 0.125, 0.25, 0.125, 0.25) | alternating |
| 6 | (0.25, 0.125, 0.125, 0.125, 0.125, 0.25) | long-run-long |
| 6 | (0.125, 0.125, 0.25, 0.125, 0.125, 0.25) | run-accent-run |

#### 3/4 Time (head duration: 0.375–0.5 bar, total subject = 1.5)

| Notes | Durations | Name |
|-------|-----------|------|
| 3 | (0.125, 0.125, 0.125) | triplet-run |
| 3 | (0.1875, 0.0625, 0.125) | dotted-short |
| 4 | (0.125, 0.0625, 0.0625, 0.125) | long-ornament-long |
| 4 | (0.0625, 0.125, 0.0625, 0.125) | short-long-alt |
| 4 | (0.125, 0.125, 0.125, 0.125) | even-eighths-3 |
| 4 | (0.1875, 0.0625, 0.125, 0.125) | dotted-eighths-3 |
| 5 | (0.125, 0.0625, 0.0625, 0.125, 0.125) | ornament-eighths-3 |
| 5 | (0.0625, 0.0625, 0.125, 0.125, 0.125) | sixteenths-eighths-3 |

#### 2/4 Time (head duration: 0.375–0.5 bar, total subject = 1.0)

| Notes | Durations | Name |
|-------|-----------|------|
| 3 | (0.125, 0.125, 0.125) | triplet-2 |
| 3 | (0.1875, 0.0625, 0.125) | dotted-short-2 |
| 4 | (0.125, 0.125, 0.125, 0.125) | even-eighths |
| 4 | (0.1875, 0.0625, 0.125, 0.125) | dotted-run-2 |
| 4 | (0.125, 0.0625, 0.0625, 0.25) | run-long-2 |
| 4 | (0.25, 0.0625, 0.0625, 0.125) | long-ornament-2 |
| 5 | (0.125, 0.0625, 0.0625, 0.125, 0.125) | run-eighths-2 |
| 5 | (0.0625, 0.0625, 0.125, 0.125, 0.125) | sixteenths-eighths-2 |

#### 2/2 Cut Time (same as 4/4)

Uses the same patterns as 4/4.

#### 6/8 Compound Time (head duration: 0.375–0.5 bar, total subject = 1.5)

| Notes | Durations | Name |
|-------|-----------|------|
| 3 | (0.125, 0.125, 0.125) | compound-triplet |
| 3 | (0.1875, 0.0625, 0.125) | compound-dotted |
| 4 | (0.125, 0.125, 0.125, 0.125) | compound-run |
| 4 | (0.1875, 0.0625, 0.125, 0.125) | compound-dotted-run |
| 4 | (0.25, 0.0625, 0.0625, 0.125) | compound-long-ornament |
| 5 | (0.1875, 0.0625, 0.125, 0.125, 0.125) | compound-dotted-eighths |
| 5 | (0.125, 0.125, 0.125, 0.1875, 0.0625) | compound-run-dotted |
| 5 | (0.125, 0.125, 0.125, 0.125, 0.125) | compound-even-eighths |

### 1.4 Head Output

Each valid head contains:
- `degrees`: Tuple of 0-indexed scale degrees
- `rhythm`: Tuple of float durations
- `rhythm_name`: Descriptive name of the pattern
- `leap_size`: Size of the characteristic leap (3-7)
- `leap_direction`: "up" or "down"

---

## 2. Tail Generation

**Source**: `motifs/tail_generator.py`

### 2.1 Tail Cells

Tails are constructed from melodic cells, each with a net directional motion:

#### Downward Cells (net < 0)

| Intervals | Name | Net Motion |
|-----------|------|------------|
| (-1,) | step-down | -1 |
| (-1, -1) | run-down-2 | -2 |
| (-1, -1, -1) | run-down-3 | -3 |
| (-1, -1, -1, -1) | run-down-4 | -4 |
| (-2,) | skip-down-3rd | -2 |
| (-2, -1) | skip-step-down-3 | -3 |
| (-2, -2) | skip-skip-down | -4 |
| (-1, -1, 1) | down-turn | -1 |
| (-2, 1) | skip-step-down | -1 |
| (-1, -2) | step-skip-down | -3 |
| (-1, -1, -2) | run-skip-down | -4 |
| (-2, -1, -1) | skip-run-down | -4 |

#### Upward Cells (net > 0)

| Intervals | Name | Net Motion |
|-----------|------|------------|
| (1,) | step-up | 1 |
| (1, 1) | run-up-2 | 2 |
| (1, 1, 1) | run-up-3 | 3 |
| (1, 1, 1, 1) | run-up-4 | 4 |
| (2,) | skip-up-3rd | 2 |
| (2, 1) | skip-step-up-3 | 3 |
| (2, 2) | skip-skip-up | 4 |
| (1, 1, -1) | up-turn | 1 |
| (2, -1) | skip-step-up | 1 |
| (1, 2) | step-skip-up | 3 |
| (1, 1, 2) | run-skip-up | 4 |
| (2, 1, 1) | skip-run-up | 4 |

### 2.2 Tail Validity Rules

A tail is valid if and only if:

1. **Contrary Direction**: Net motion is opposite to the head's leap direction
   - If head leaps up → tail moves down
   - If head leaps down → tail moves up

2. **Rhythm from Head**: Durations drawn exclusively from the head's duration vocabulary

3. **Stepwise Limitation**: At most 50% of intervals can be stepwise (±1)

4. **No Oscillation**: No boring back-and-forth patterns like (+1, -1, +1, -1)

5. **Stable Resolution**: Final degree must be on the tonic triad (degrees 0, 2, or 4 mod 7)

6. **Minimum Pitch Range**: Cumulative pitch motion must span at least 3 degrees (a fourth)

7. **Pitch Bounds**: All degrees must stay within [min_degree, max_degree]
   - Default: -4 to 11 (F3 to G5 in C major)

### 2.3 Rhythm Combination Algorithm

Tail rhythms are constructed to:
1. Sum to exactly `target_duration - head_duration`
2. End with the pattern: `[..., smallest_duration, largest_duration]` (cadential feel)
3. Use only durations from the head's vocabulary

The body (all notes except the final two) is solved as a linear combination:
```
n_a × duration_a + n_b × duration_b + ... = body_target
```

### 2.4 Tail Note Count

- **Minimum**: 3 notes (including shared note with head)
- **Maximum**: 12 notes

---

## 3. Subject Assembly

**Source**: `motifs/subject_generator.py`

### 3.1 Combining Head and Tail

The subject is formed by:
1. Taking all notes from the head
2. Taking all notes from the tail except the first (which is shared with head's last note)
3. Combining rhythms similarly

```python
subject_degrees = head.degrees + tail_degrees[1:]
subject_rhythm = head.rhythm + tail.rhythm[1:]
```

### 3.2 Barline Constraint

The combined rhythm must not have any note crossing a barline. A note crosses a barline if its start and end fall in different bars (unless the end is exactly on the barline).

### 3.3 Integer Bar Constraint

The total duration must equal an **integer number of bars**. The number of bars is determined by the head+tail combination, not fixed in advance.

| Metre | Bar Duration | Typical Subject Bars |
|-------|--------------|---------------------|
| 4/4 | 1.0 | 1, 2, 3, or 4 |
| 3/4 | 0.75 | 1, 2, 3, or 4 |
| 2/4 | 0.5 | 1, 2, 3, or 4 |
| 2/2 | 1.0 | 1, 2, 3, or 4 |
| 6/8 | 0.75 | 1, 2, 3, or 4 |

### 3.4 Melodic Validation

Subjects must pass melodic validation before acceptance:

| Check | Description | Forbidden |
|-------|-------------|-----------|
| Seventh leap | Any interval of 10-11 semitones | Yes |
| Tritone leap | Any interval of 6 semitones | Yes |
| Tritone outline | 4-note span outlining 6 semitones | Yes |
| Consecutive leaps | Two leaps (>2 semitones) same direction | Yes |
| Leading tone | Degree 7 not resolving to tonic | Yes |

### 3.5 Selection Algorithm (Random Sampling)

The algorithm uses **random sampling** rather than exhaustive enumeration:

1. **Sample a valid head** (up to 100 random attempts per head):
   - Pick a random rhythm cell from the metre's cells
   - Generate a random pitch sequence
   - Validate: must have leap + gap fill

2. **Try different bar counts** (priority: 2, 1, 3, 4 bars):
   - Calculate target duration for each bar count
   - Generate tails that sum to target duration
   - Pick a random valid tail

3. **Combine and validate**:
   - Must have at least 2 distinct durations
   - Must not cross barlines
   - Must span an integer number of bars
   - Must pass melodic validation

4. **Affect scoring** (if affect specified):
   - Generate 50 candidates
   - Score each against figurae for the affect
   - Return highest-scoring candidate

5. **Otherwise** return first valid combination (after 5 candidates found)

---

## 4. Answer Generation

**Source**: `motifs/answer_generator.py`

The answer is the subject transposed to the dominant key, with tonal mutations to preserve harmonic coherence.

### 4.1 Real vs Tonal Answer

**Real answer**: Exact transposition up a 5th (4 scale degrees). Valid only when the subject doesn't prominently cross the tonic-dominant boundary.

**Tonal answer**: Certain intervals are mutated to maintain tonal coherence. Required when the subject opens with motion between tonic and dominant.

### 4.2 Tonal Mutation Rules

The fundamental principle: when the subject emphasises the tonic-dominant axis, the answer reciprocates.

| Subject Motion | Answer Motion | Reason |
|----------------|---------------|--------|
| 1 → 5 (tonic to dominant) | 5 → 1 (dominant to tonic) | Maintains tonal balance |
| 5 → 1 (dominant to tonic) | 1 → 5 (tonic to dominant) | Reciprocal |
| Other intervals | Real transposition (+4 degrees) | No boundary crossing |

### 4.3 Boundary Detection

The tonic-dominant boundary is typically crossed in the subject's **head** (first strong beat). Common patterns requiring tonal mutation:

| Subject Opening | Requires Tonal Answer |
|-----------------|----------------------|
| Starts on 1, leaps to 5 | Yes |
| Starts on 5, moves to 1 | Yes |
| Starts on 1, stays within 1-3 | No (real answer OK) |
| Starts on 5, stays within 5-7 | No (real answer OK) |

### 4.4 Algorithm

```
for each note in subject:
    if this is a boundary-crossing interval:
        apply tonal mutation (contract/expand)
    else:
        apply real transposition (+4 degrees)
```

The mutation typically affects only the first 1-3 notes; the remainder uses real transposition.

### 4.5 Example: Little Fugue BWV 578

Subject (G minor): G4 → D5 → Bb4 → G4 → Bb4 → A4 → G4 → F#4 → A4 → D4

- Opens with G → D (scale degrees 1 → 5)
- Answer must mutate: D → G (5 → 1) instead of D → A (5 → 2)
- Remainder: real transposition at the 5th

Answer: D5 → G5 → F5 → D5 → F5 → E5 → D5 → C#5 → E5 → A4

### 4.6 Output

```python
@dataclass
class GeneratedAnswer:
    scale_indices: tuple[int, ...]    # Degrees in dominant key
    durations: tuple[float, ...]       # Same as subject
    midi_pitches: tuple[int, ...]
    answer_type: str                   # "real" or "tonal"
    mutation_points: tuple[int, ...]   # Indices where mutation applied
```

---

## 5. Countersubject Generation

**Source**: `motifs/countersubject_generator.py`

The countersubject is a melodic line that:
1. Accompanies the subject (when one voice has the subject)
2. Works correctly when voices are swapped (invertible counterpoint at the octave)
3. Has melodic independence from the subject

### 5.1 Design Simplifications

| Decision | Rationale |
|----------|----------|
| Same rhythm as subject | Pitch-only optimisation; rhythmic complement deferred to Phase 5 |
| Same note count | One CS pitch variable per subject note |
| Optimise against subject only | Answer verification post-hoc; answer is subject +4 degrees with minor mutations |
| Work in scale degrees | Mode-independent; eliminates semitone interval calculation |
| Voice crossing allowed | L004: Bach crosses freely in counterpoint |

### 5.2 Degree-Based Interval Classification

Vertical intervals are computed as `abs(cs_degree - subject_degree) % 7`:

| Degree Interval | Musical Interval | Invertibility |
|-----------------|------------------|---------------|
| 0 | Unison/Octave | Consonant, stays consonant |
| 1 | Second/Ninth | Dissonant, stays dissonant |
| 2 | Third/Tenth | Consonant, becomes 6th (consonant) |
| 3 | Fourth/Eleventh | Dissonant, becomes 5th (consonant) |
| 4 | Fifth/Twelfth | Consonant, becomes 4th (DISSONANT) |
| 5 | Sixth/Thirteenth | Consonant, becomes 3rd (consonant) |
| 6 | Seventh/Fourteenth | Dissonant, becomes 2nd (dissonant) |

**Invertible consonances**: {0, 2, 5} mod 7 (unison, third, sixth)

**Critical insight**: Perfect 5ths (degree interval 4) are consonant but become dissonant 4ths when inverted. They must be restricted.

### 5.3 Strong vs Weak Beat Treatment

Baroque practice allows passing dissonances and 5ths on weak beats:

| Beat Type | Allowed Degree Intervals | Rationale |
|-----------|-------------------------|----------|
| Strong (1, 3 in 4/4) | {0, 2, 5} | Invertible consonances only |
| Weak (2, 4 in 4/4) | {0, 1, 2, 4, 5, 6} | Passing tones + 5ths allowed |

Weak-beat 5ths become passing 4ths when inverted, which is acceptable Baroque practice.

### 5.4 CP-SAT Constraint Set

**Hard Constraints** (must be satisfied):

| ID | Constraint | Formula |
|----|------------|--------|
| H1 | Strong-beat invertible consonance | `(cs[i] - subj[i]) % 7 in {0, 2, 5}` when beat is strong |
| H2 | Weak-beat non-tritone | `(cs[i] - subj[i]) % 7 != 3` (no tritones even on weak beats) |
| H3 | No consecutive unisons | `not (interval[i] == 0 and interval[i+1] == 0)` |
| H4 | No direct motion to unison | If both voices move same direction, target != unison |
| H5 | Degree range | `min_degree <= cs[i] <= max_degree` |

**Soft Constraints** (penalties):

| ID | Constraint | Penalty | Rationale |
|----|------------|---------|----------|
| S1 | Weak-beat 5th | 20 | Prefer other consonances |
| S2 | Weak-beat dissonance | 10 | Prefer consonances |
| S3 | Leap > 4 degrees | 30 | Singability |
| S4 | Repeated pitch | 25 | Melodic interest |
| S5 | Interior unison | 15 | Reserve for boundaries |
| S6 | Parallel motion | 10 | Prefer contrary/oblique |

**Rewards** (bonuses):

| ID | Constraint | Reward | Rationale |
|----|------------|--------|----------|
| R1 | Contrary motion | 15 | Voice independence |
| R2 | Stepwise motion | 5 | Singability |
| R3 | Start/end on stable degree | 10 | Tonal grounding |

### 5.5 Beat Classification

Beat strength depends on metre:

| Metre | Strong Beats | Weak Beats |
|-------|--------------|------------|
| 4/4 | 1, 3 | 2, 4 |
| 3/4 | 1 | 2, 3 |
| 2/4 | 1 | 2 |
| 6/8 | 1, 4 | 2, 3, 5, 6 |
| 2/2 | 1, 3 | 2, 4 |

Beat position is computed from cumulative duration at each note onset.

### 5.6 Algorithm

```
1. Create CP-SAT model
2. Add variables: cs[i] for i in 0..n-1, domain [min_degree, max_degree]
3. Compute beat positions from subject durations and metre
4. For each note i:
   a. Compute interval = (cs[i] - subject[i]) % 7
   b. If strong beat: add H1 constraint
   c. Always: add H2 constraint (no tritones)
5. For consecutive pairs (i, i+1):
   a. Add H3 (no consecutive unisons)
   b. Add H4 (no direct motion to unison)
6. Add soft constraints as weighted penalties
7. Add rewards as weighted bonuses
8. Solve with timeout
9. Extract solution, convert to MIDI
```

### 5.7 Post-Generation Verification

After generation, verify against answer:

1. Transpose subject by +4 degrees (with tonal mutations) to get answer
2. Check all strong-beat intervals between CS and answer
3. If any violations, log warning but accept (answer mutations are minor)

### 5.8 Output

```python
@dataclass
class GeneratedCountersubject:
    scale_indices: tuple[int, ...]      # 0-indexed degrees
    durations: tuple[float, ...]        # Same as subject
    midi_pitches: tuple[int, ...]       # Resolved pitches
    vertical_intervals: tuple[int, ...] # Degree intervals against subject
```

---

## 6. Fugue Triple: Subject + Answer + Countersubject

### 6.1 Coordination

The three components must work together:

```
Voice 1: [--SUBJECT--][--COUNTERSUBJECT--]...
Voice 2:              [----ANSWER----][--CS--]...
Voice 3:                               [--SUBJ--]...
```

### 6.2 Verification Tests

| Test | Description |
|------|-------------|
| CS + Subject | Countersubject valid against subject |
| CS + Answer | Countersubject valid against answer |
| Inverted CS + Subject | Swapped voices still valid |
| Inverted CS + Answer | Swapped voices still valid |

### 6.3 File Format

Proposed `.subject` YAML format:

```yaml
subject:
  degrees: [0, 4, 2, 1, 2, 0, 1, -1, 0]
  durations: [0.375, 0.125, 0.125, 0.125, 0.25, 0.125, 0.125, 0.125, 0.5]
  mode: minor
  
answer:
  degrees: [4, 7, 6, 5, 6, 4, 5, 3, 4]
  durations: [0.375, 0.125, 0.125, 0.125, 0.25, 0.125, 0.125, 0.125, 0.5]
  type: tonal
  mutation_points: [0, 1]
  
countersubject:
  degrees: [2, 1, 2, 4, 3, 2, 1, 0, 2]
  durations: [0.125, 0.125, 0.25, 0.125, 0.125, 0.25, 0.125, 0.25, 0.5]
  invertible: true
  
metadata:
  metre: [4, 4]
  tonic: G
  seed: 42
```

---

## 7. Degree Representation

### 7.1 Internal Representation (0-indexed)

Used throughout head/tail generation:
- 0 = tonic (1st degree)
- 1 = supertonic (2nd degree)
- 2 = mediant (3rd degree)
- ...
- 6 = leading tone (7th degree)
- 7 = octave (1st degree, octave above)

Extended range: -4 to 14 for two-octave span.

### 7.2 External Representation (1-indexed)

Used in YAML files and planner output:
- 1 = tonic
- 2 = supertonic
- ...
- 7 = leading tone

Conversion: `external_degree = (internal_degree % 7) + 1`

### 7.3 MIDI Conversion

```python
MAJOR_SCALE = (0, 2, 4, 5, 7, 9, 11)  # Semitones from tonic
MINOR_SCALE = (0, 2, 3, 5, 7, 8, 10)

def degree_to_midi(degree, tonic_midi, mode):
    scale = MINOR_SCALE if mode == "minor" else MAJOR_SCALE
    octave = degree // 7
    scale_idx = degree % 7
    return tonic_midi + octave * 12 + scale[scale_idx]
```

---

## 8. Supported Time Signatures

| Metre | Supported | Notes |
|-------|-----------|-------|
| 4/4 | Yes | Default, most rhythm cells |
| 3/4 | Yes | Shorter subjects (1.5 duration) |
| 2/4 | Yes | Short subjects (1.0 duration) |
| 2/2 | Yes | Uses 4/4 rhythm cells |
| 6/8 | Yes | Compound metre, 1.5 duration |

---

## 9. Affect Integration

When an affect is specified:

1. Load figurae (melodic figures) associated with that affect
2. Generate 50 subject candidates
3. Score each candidate against the figurae
4. Return the highest-scoring subject

Figurae scoring considers:
- Presence of characteristic intervals
- Rhythmic patterns matching the affect
- Overall melodic contour

---

## 10. Algorithm Complexity

| Component | Complexity | Typical Time |
|-----------|------------|--------------|
| Head sampling | O(attempts × notes) | <10ms |
| Tail generation | O(rhythm_combos × interval_seqs) | <50ms |
| Subject assembly | O(1) | <1ms |
| Answer generation | O(n) | <1ms |
| CS generation (CP-SAT) | NP-hard | <10s |

---

## 11. Implementation Plan

### Phase 1: Answer Generator

**File**: `motifs/answer_generator.py`

**Scope**: ~80 lines

**Functions**:
```python
def detect_boundary_crossing(degrees: tuple[int, ...]) -> list[int]:
    """Return indices where subject crosses tonic-dominant boundary."""

def generate_answer(
    subject: GeneratedSubject,
    mode: str = "major",
) -> GeneratedAnswer:
    """Generate tonal or real answer for a subject."""
```

**Algorithm**:
1. Scan subject for 1→5 or 5→1 motion in head region
2. If found: apply tonal mutation at those points
3. Apply real transposition (+4 degrees) elsewhere
4. Convert to MIDI pitches in dominant key

**Test cases**:
- Little Fugue BWV 578 (tonal answer, 1→5 opening)
- Subject starting on 3 (should use real answer)
- Subject with multiple boundary crossings

### Phase 2: Countersubject Generator

**File**: `motifs/countersubject_generator.py`

**Scope**: ~150 lines

**Approach**: CP-SAT optimisation with degree-based intervals

**Variables**:
- `cs[i]`: Scale degree of note i (domain: min_degree to max_degree)
- Same rhythm as subject (no duration variables)

**Hard constraints**:
- H1: Strong-beat intervals in {0, 2, 5} mod 7 (invertible consonances)
- H2: No tritones (interval 3 mod 7) even on weak beats
- H3: No consecutive unisons
- H4: No direct motion to unison
- H5: Degree range bounds

**Soft constraints (penalties)**:
- Weak-beat 5th: 20
- Weak-beat dissonance: 10
- Leap > 4 degrees: 30
- Repeated pitch: 25
- Interior unison: 15
- Parallel motion: 10

**Rewards**:
- Contrary motion: +15
- Stepwise motion: +5
- Start/end on stable degree: +10

### Phase 3: Invertibility Checker

**File**: `motifs/invertibility.py`

**Scope**: ~50 lines

**Functions**:
```python
def check_invertible_octave(
    subject_pitches: tuple[int, ...],
    cs_pitches: tuple[int, ...],
) -> tuple[bool, list[str]]:
    """Check if CS is invertible at the octave against subject.
    
    Returns (valid, list of violations).
    """

def invert_countersubject(
    cs_pitches: tuple[int, ...],
    subject_pitches: tuple[int, ...],
) -> tuple[int, ...]:
    """Return CS pitches transposed to work below the subject."""
```

### Phase 4: Integration and Testing

**File**: `motifs/fugue_triple.py`

**Scope**: ~100 lines

**Functions**:
```python
def generate_fugue_triple(
    mode: str = "minor",
    metre: tuple[int, int] = (4, 4),
    seed: int | None = None,
    affect: str | None = None,
) -> FugueTriple:
    """Generate coordinated subject, answer, and countersubject."""

def verify_fugue_triple(triple: FugueTriple) -> tuple[bool, list[str]]:
    """Verify all combinations are contrapuntally valid."""

def write_fugue_file(triple: FugueTriple, path: Path) -> None:
    """Write fugue triple to YAML file."""
```

**Validation suite**:
1. Generate 100 triples
2. Verify each against counterpoint rules
3. Test invertibility of each countersubject
4. Compare statistical properties to Little Fugue reference

### Phase 5: Refinement

Based on listening tests and statistical analysis:
- Tune penalty weights in CS generator
- Add affect-aware countersubject generation
- Implement double/triple fugue extensions
- Add episode material generation

---

## 12. Example Subject Generation

### Input
```python
generate_subject(
    mode="major",
    metre=(4, 4),
    seed=42,
    tonic_midi=60  # C4
)
```

### Output
```python
GeneratedSubject(
    scale_indices=(0, 4, 2, 1, 3, 1, 2, 0, 1, -1, -2),
    durations=(0.375, 0.125, 0.125, 0.125, 0.25, 0.125, 0.125, 0.125, 0.125, 0.125, 0.375),
    midi_pitches=(60, 67, 64, 62, 65, 62, 64, 60, 62, 59, 57),
    bars=2,
    head_name="dotted-quarters",
    leap_size=4,
    leap_direction="up",
    tail_direction="down"
)
```

### Interpretation
- Head: C4 → G4 (leap up of 4 = perfect 5th), gap-filled by E4
- Tail: Descending motion back toward tonic
- Opens with 1 → 5, so answer will require tonal mutation
