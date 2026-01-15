# Subject Generation Algorithm

This document specifies the complete rules and constraints for generating fugue subjects, heads, tails, and counter-subjects in Andante.

## Overview

Subject generation follows a **head + tail construction** method inspired by Baroque compositional practice:

1. **Head**: The memorable opening gesture (3-6 notes)
2. **Tail**: The continuation leading to resolution (3-12 notes)
3. **Subject**: Head + Tail combined (spans exactly 2 bars)
4. **Counter-subject**: A complementary melody generated via CP-SAT optimization

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

### 3.4 Selection Algorithm (Random Sampling)

The algorithm uses **random sampling** rather than exhaustive enumeration for performance:

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

4. **Affect scoring** (if affect specified):
   - Generate 50 candidates
   - Score each against figurae for the affect
   - Return highest-scoring candidate

5. **Otherwise** return first valid combination (after 5 candidates found)

This approach generates subjects in ~50-100ms regardless of metre complexity.

---

## 4. Counter-Subject Generation

**Source**: `planner/cs_generator.py`

Counter-subjects are generated using Google OR-Tools CP-SAT solver for joint optimization of pitch and rhythm.

### 4.1 Valid Durations

| Value | Name |
|-------|------|
| 1/2 | Half note |
| 3/8 | Dotted quarter |
| 1/4 | Quarter note |
| 3/16 | Dotted eighth |
| 1/8 | Eighth note |
| 1/16 | Sixteenth note |

Allowed CS durations:
- All durations present in the subject
- One step faster than subject's fastest
- One step slower than subject's slowest

### 4.2 Consonant Intervals

| Type | Interval Classes (semitones mod 12) |
|------|-------------------------------------|
| Perfect consonances | 0 (unison), 7 (fifth) |
| Imperfect consonances | 3, 4 (thirds), 8, 9 (sixths) |

All other intervals are **dissonant** and forbidden at attack points.

### 4.3 Hard Constraints

| Constraint | Description |
|------------|-------------|
| H1: Duration Match | CS total duration = subject total duration |
| H2: Contiguous Notes | No gaps (if note i is inactive, note i+1 must be inactive) |
| H3: Note Count | min(3, n_subject - 2) ≤ CS notes ≤ n_subject + 2 |
| H4: Forbidden Degrees | Major: avoid 7; Minor: avoid 6, 7 |
| H5: No Dissonance | All vertical intervals must be consonant |
| H6: No Parallel Fifths/Octaves | Consecutive perfect intervals in parallel motion forbidden |

### 4.4 Soft Constraints (Penalties)

| Constraint | Penalty | Description |
|------------|---------|-------------|
| Perfect fifth | 80 | Avoid (becomes dissonant when inverted) |
| Interior unison | 120 | Avoid unisons except at start/end |
| Immediate repetition | 20 | Don't repeat same pitch |
| Large leap (6-7 semitones) | 30 | Prefer smaller intervals |
| Very large leap (>7 semitones) | 150 | Strongly discourage |
| Non-stepwise motion | 10 | Prefer stepwise (70% target) |
| Attack collision on weak beat | 100 | Avoid simultaneous attacks off strong beats |
| Consecutive equal durations | 15 | Encourage rhythmic variety |
| Non-final ending degree | 50 | Final note should be 1 or 5 |
| Non-stepwise approach to final | 40 | Penultimate should approach by step |
| Non-subject duration | 5 | Prefer subject's duration vocabulary |
| Climax collision | 25 | CS high point shouldn't match subject's |

### 4.5 Invertibility Constraints

For standard counterpoint:
- Perfect fifths are penalized (become fourths when inverted)

For **interleaved (Goldberg-style)** counterpoint:
- Seconds (1-2 semitones) are **strongly penalized** (200 points)
- These become sevenths when inverted at the unison
- Thirds and sixths are preferred (remain consonant when inverted)

### 4.6 Strong Beats

Strong beats (where attack collisions are acceptable):
- Beat 1 (position 0 within bar)
- Beat 3 (position 0.5 within bar in 4/4)

### 4.7 Solver Configuration

- Timeout: 10 seconds default
- Workers: 4 parallel search threads
- Accepts OPTIMAL or FEASIBLE solutions

---

## 5. Degree Representation

### 5.1 Internal Representation (0-indexed)

Used throughout head/tail generation:
- 0 = tonic (1st degree)
- 1 = supertonic (2nd degree)
- 2 = mediant (3rd degree)
- ...
- 6 = leading tone (7th degree)
- 7 = octave (1st degree, octave above)

Extended range: -4 to 14 for two-octave span.

### 5.2 External Representation (1-indexed)

Used in YAML files and planner output:
- 1 = tonic
- 2 = supertonic
- ...
- 7 = leading tone

Conversion: `external_degree = (internal_degree % 7) + 1`

### 5.3 MIDI Conversion

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

## 6. Supported Time Signatures

| Metre | Supported | Notes |
|-------|-----------|-------|
| 4/4 | Yes | Default, most rhythm cells |
| 3/4 | Yes | Shorter subjects (1.5 duration) |
| 2/4 | Yes | Short subjects (1.0 duration) |
| 2/2 | Yes | Uses 4/4 rhythm cells |
| 6/8 | Yes | Compound metre, 1.5 duration |

---

## 7. Affect Integration

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

## 8. Algorithm Complexity

| Component | Complexity | Typical Count |
|-----------|------------|---------------|
| Head enumeration | O(cells × 15^notes) | ~21,000 heads for 4/4 |
| Tail generation per head | O(rhythm_combos × interval_seqs) | 0-100 tails per head |
| Subject assembly | O(1) | 1 per head+tail pair |
| CS generation | CP-SAT (NP-hard) | 10s timeout |

Note: For 3/4 metre, only ~3% of heads produce valid tails due to stricter constraints.

---

## 9. Example Subject Generation

### Input
```python
generate_subject(
    mode="major",
    metre=(4, 4),
    duration_bars=2,
    seed=42,
    tonic_midi=60  # C4
)
```

### Output
```python
GeneratedSubject(
    scale_indices=(0, 0, 3, 2, 1, 4, 3, 2, 5, 4, 0, 2),
    durations=(0.25, 0.125, 0.125, 0.25, 0.25, 0.125, 0.125, 0.25, 0.25, 0.125, 0.125, 0.25),
    midi_pitches=(60, 60, 65, 64, 62, 67, 65, 64, 69, 67, 60, 64),
    head_name="long-short-short-long",
    leap_size=3,
    leap_direction="up",
    tail_direction="down"
)
```

### Interpretation
- Head: C4 → C4 → F4 → E4 (leap up of 3, filled by step down)
- Tail: Descending motion E4 → D4 → G4 → F4 → E4 → A4 → G4 → C4 → E4
- Total duration: 2.0 (exactly 2 bars in 4/4)
- Final note: E4 (mediant, stable)
