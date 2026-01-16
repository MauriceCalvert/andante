# Comprehensive Counterpoint Rules

Synthesized from baroque and classical treatises for CP-SAT solver implementation.

---

## Sources

| Treatise | Author | Year | Focus |
|----------|--------|------|-------|
| Gradus ad Parnassum | Johann Joseph Fux | 1725 | Species counterpoint, foundational rules |
| Treatise on Harmony | Jean-Philippe Rameau | 1722 | Chord theory, fundamental bass |
| Essay on the True Art of Playing Keyboard | C.P.E. Bach | 1753-62 | Galant style, figured bass realization |
| The Art of Strict Musical Composition | Johann Kirnberger | 1771-79 | Synthesis of Fux with modern practice |
| Versuch einer Anleitung zur Composition | Heinrich Christoph Koch | 1782-93 | Phrase structure, melody |
| Abhandlung von der Fuge | Friedrich Wilhelm Marpurg | 1753-54 | Fugue, imitation, invertible counterpoint |
| Der vollkommene Capellmeister | Johann Mattheson | 1739 | Comprehensive composition guide |
| Traité de l'harmonie | Rameau | 1722 | Fundamental bass theory |

---

## Rule Categories

### Category A: Absolute Prohibitions (Hard Constraints)

These produce immediate rejection. No exceptions in strict style.

#### A1. Parallel Perfect Consonances

| Rule | Description | Source | Penalty |
|------|-------------|--------|---------|
| A1.1 | Parallel fifths | Fux I.14, Kirnberger II.3 | ∞ |
| A1.2 | Parallel octaves | Fux I.14, Kirnberger II.3 | ∞ |
| A1.3 | Parallel unisons | Fux I.14 | ∞ |

**Detection**: Both intervals = target (0, 7, or 12 mod 12), both voices move same direction, neither stationary.

**Exception**: None in strict counterpoint. In free style, parallel octaves may occur between bass and an inner voice doubling melody.

#### A2. Direct (Hidden) Perfect Consonances to Outer Voices

| Rule | Description | Source | Penalty |
|------|-------------|--------|---------|
| A2.1 | Direct fifth by similar motion, soprano leaps | Fux I.15 | ∞ |
| A2.2 | Direct octave by similar motion, soprano leaps | Fux I.15 | ∞ |

**Detection**: Arrive at fifth/octave by similar motion where upper voice leaps.

**Exception**: Acceptable if soprano moves by step (Fux). In inner voices, penalty reduced.

#### A3. Dissonance Treatment

| Rule | Description | Source | Penalty |
|------|-------------|--------|---------|
| A3.1 | Unprepared dissonance on strong beat | Fux II.1 | ∞ |
| A3.2 | Unresolved dissonance | Fux II.2 | ∞ |
| A3.3 | Dissonance resolved by leap | Fux II.2 | ∞ |
| A3.4 | Dissonance resolved upward (except leading tone) | Fux II.3 | ∞ |

**Dissonant intervals**: minor 2nd (1), major 2nd (2), tritone (6), minor 7th (10), major 7th (11).

**Legal dissonance**:
- Passing tone: weak beat, approached and left by step in same direction
- Neighbor tone: weak beat, step away and return
- Suspension: strong beat, prepared by same pitch on previous weak beat, resolved down by step
- Anticipation: weak beat, same pitch as following strong beat

#### A4. Voice Overlap

| Rule | Description | Source | Penalty |
|------|-------------|--------|---------|
| A4.1 | Voice moves past previous position of adjacent voice | Kirnberger II.5 | ∞ |

**Detection**: Current pitch of voice N crosses previous pitch of voice N±1.

---

### Category B: Strong Penalties (Soft Constraints, High Cost)

These are technically legal but produce poor counterpoint.

#### B1. Hidden Perfect Consonances (Inner Voices)

| Rule | Description | Source | Cost |
|------|-------------|--------|------|
| B1.1 | Hidden fifth between inner voices | Kirnberger II.4 | 20 |
| B1.2 | Hidden octave between inner voices | Kirnberger II.4 | 20 |

#### B2. Voice Crossing

| Rule | Description | Source | Cost |
|------|-------------|--------|------|
| B2.1 | Brief crossing (1-2 beats) for melodic continuity | Marpurg III.2 | 5 |
| B2.2 | Sustained crossing (3+ beats) | Kirnberger II.5 | 40 |
| B2.3 | Crossing more than a third | Kirnberger II.5 | 25 |

**Note**: Brief crossing where a voice completes a melodic line is acceptable and even desirable. Sustained crossing confuses voice identity.

#### B3. Spacing

| Rule | Description | Source | Cost |
|------|-------------|--------|------|
| B3.1 | More than octave between soprano-alto | Kirnberger III.1 | 15 |
| B3.2 | More than octave between alto-tenor | Kirnberger III.1 | 10 |
| B3.3 | More than twelfth between tenor-bass | Traditional | 5 |
| B3.4 | Unison between adjacent voices (non-cadential) | Fux I.12 | 30 |

#### B4. Melodic Intervals (Leaps)

| Rule | Description | Source | Cost |
|------|-------------|--------|------|
| B4.1 | Augmented interval | Fux I.10 | 30 |
| B4.2 | Seventh | Fux I.10 | 25 |
| B4.3 | Leap larger than octave | Fux I.10 | 30 |
| B4.4 | Two leaps in same direction | Fux I.11 | 15 |
| B4.5 | Leap not followed by contrary step | Fux I.11 | 10 |
| B4.6 | Tritone outline in melodic line | Fux I.10 | 20 |

**Exception**: Octave leap acceptable if followed by contrary motion. Leaps of third common and free.

#### B5. Repetition and Monotony

| Rule | Description | Source | Cost |
|------|-------------|--------|------|
| B5.1 | Same pitch more than 3 times consecutively | Koch II.3 | 15 |
| B5.2 | Same rhythm pattern more than 4 bars | Mattheson V.2 | 10 |
| B5.3 | Static bass for more than 2 bars (non-pedal) | Rameau III.4 | 20 |

---

### Category C: Moderate Penalties (Soft Constraints, Medium Cost)

These affect style but don't break counterpoint.

#### C1. Motion Quality

| Rule | Description | Source | Cost |
|------|-------------|--------|------|
| C1.1 | All voices move in similar motion | Fux I.16 | 12 |
| C1.2 | Parallel thirds for more than 3 beats | Kirnberger II.6 | 8 |
| C1.3 | Parallel sixths for more than 3 beats | Kirnberger II.6 | 8 |
| C1.4 | All voices leap simultaneously | Fux I.17 | 15 |

#### C2. Range and Tessitura

| Rule | Description | Source | Cost |
|------|-------------|--------|------|
| C2.1 | Voice outside comfortable range | Traditional | 10 |
| C2.2 | Voice at extreme of range for extended passage | Traditional | 15 |
| C2.3 | Bass above tenor range | Kirnberger III.2 | 20 |

**Comfortable ranges** (MIDI):
- Soprano: C4-G5 (60-79)
- Alto: G3-D5 (55-74)
- Tenor: C3-G4 (48-67)
- Bass: E2-C4 (40-60)

#### C3. Harmonic Rhythm

| Rule | Description | Source | Cost |
|------|-------------|--------|------|
| C3.1 | Chord change on weak beat only | Rameau II.5 | 8 |
| C3.2 | Same harmony for entire bar in fast tempo | Traditional | 5 |
| C3.3 | Harmony change every beat in slow tempo | Traditional | 5 |

---

### Category D: Rewards (Negative Cost / Bonus)

These improve quality and should be encouraged.

#### D1. Motion Types

| Rule | Description | Source | Reward |
|------|-------------|--------|--------|
| D1.1 | Contrary motion between outer voices | Fux I.16 | -12 |
| D1.2 | Oblique motion (one voice stationary) | Fux I.16 | -4 |
| D1.3 | Stepwise motion | Fux I.9 | -10 |
| D1.4 | Complementary rhythm (one moves, other holds) | Mattheson IV.3 | -8 |

#### D2. Cadential Patterns

| Rule | Description | Source | Reward |
|------|-------------|--------|--------|
| D2.1 | Proper leading tone resolution (up by step) | Fux III.2 | -15 |
| D2.2 | 4-3 suspension at cadence | Fux III.3 | -12 |
| D2.3 | 7-6 suspension chain | Fux III.3 | -10 |
| D2.4 | Bass moves by fifth at cadence | Rameau II.3 | -10 |

#### D3. Thematic Integration

| Rule | Description | Source | Reward |
|------|-------------|--------|--------|
| D3.1 | Voice contains subject fragment | Marpurg II.4 | -20 |
| D3.2 | Voice contains countersubject fragment | Marpurg II.4 | -15 |
| D3.3 | Sequential repetition (down a step) | Mattheson V.4 | -10 |
| D3.4 | Imitation at octave/unison | Marpurg II.1 | -15 |
| D3.5 | Imitation at fifth/fourth | Marpurg II.1 | -12 |

#### D4. Voice Independence

| Rule | Description | Source | Reward |
|------|-------------|--------|--------|
| D4.1 | Each voice has distinct rhythm | Kirnberger IV.2 | -8 |
| D4.2 | Staggered entries | Marpurg II.3 | -6 |
| D4.3 | Melodic climax at different points | Koch III.1 | -5 |

#### D5. Compound Melody / Implied Voices

| Rule | Description | Source | Reward |
|------|-------------|--------|--------|
| D5.1 | Two voices create coherent implied third voice | Bach analysis | -25 |
| D5.2 | Alternating register creates polyphonic effect | Bach analysis | -20 |
| D5.3 | Voice pair interlocks to fill harmonic space | Traditional | -15 |

---

## Species-Specific Rules (Fux)

### First Species (Note against Note)

- Only consonances: unison, third, fifth, sixth, octave
- Begin and end on perfect consonance
- No repeated notes
- Contrary motion preferred

### Second Species (Two notes against one)

- Strong beat: consonance only
- Weak beat: consonance or passing dissonance
- No repeated notes on consecutive strong beats

### Third Species (Four notes against one)

- First note of each bar: consonance
- Second, third, fourth: consonance or passing/neighbor
- Cambiata figure allowed (leap from dissonance)

### Fourth Species (Syncopation)

- Tied notes create suspensions
- Dissonance on strong beat must be prepared and resolved
- 7-6, 4-3, 9-8 suspensions preferred
- 2-1, 2-3 suspensions in upper voice only

### Fifth Species (Florid)

- Combines all previous species
- Variety of rhythm essential
- Each bar should have clear species character

---

## Fugue-Specific Rules (Marpurg)

### Subject Design

| Rule | Description |
|------|-------------|
| Clear tonal answer (real or tonal) | Modulating subject requires tonal adjustment |
| Subject should outline key | Begin/end on tonic or dominant |
| Characteristic rhythm | Memorable, not too complex |
| Singable range | Usually within tenth |

### Answer Types

| Type | When | Adjustment |
|------|------|------------|
| Real | Subject stays in key | Exact transposition at fifth |
| Tonal | Subject outlines I-V | V becomes I, I becomes V at boundary |

### Countersubject

| Rule | Description |
|------|-------------|
| Invertible at octave | Must work above or below subject |
| Contrasting rhythm | Fill gaps in subject rhythm |
| Complementary contour | Move contrary to subject |

### Stretto

| Rule | Description |
|------|-------------|
| Valid stretto distance | Must not create forbidden parallels |
| Increasing intensity | Later strettos closer together |
| Climactic placement | Near end of fugue |

---

## Figured Bass Realization (C.P.E. Bach)

### Voice Distribution

| Figure | Chord | Typical spacing |
|--------|-------|-----------------|
| No figure | 5/3 (root position) | Root doubled |
| 6 | First inversion | Third or root doubled |
| 6/4 | Second inversion | Fifth doubled |
| 7 | Seventh chord | No doubling of seventh |
| 6/5 | First inv. seventh | No doubling of seventh |
| 4/3 | Second inv. seventh | No doubling of seventh |
| 4/2 | Third inv. seventh | No doubling of seventh |

### Doubling Priorities

1. Double the bass (if root)
2. Double the root (if bass is not root)
3. Double the fifth
4. Never double the leading tone
5. Never double a chromatically altered tone
6. Never double the seventh

---

## Implementation Priority

### Phase 1: Core (Current Focus)

```python
HARD_CONSTRAINTS = {
    'parallel_fifth': A1.1,
    'parallel_octave': A1.2,
    'direct_fifth_outer': A2.1,
    'direct_octave_outer': A2.2,
    'unprepared_dissonance': A3.1,
    'unresolved_dissonance': A3.2,
    'voice_overlap': A4.1,
}
```

### Phase 2: Quality

```python
SOFT_CONSTRAINTS = {
    'hidden_fifth_inner': (B1.1, 20),
    'voice_crossing_brief': (B2.1, 5),
    'voice_crossing_sustained': (B2.2, 40),
    'spacing_soprano_alto': (B3.1, 15),
    'spacing_alto_tenor': (B3.2, 10),
    'leap_augmented': (B4.1, 30),
    'leap_seventh': (B4.2, 25),
    'consecutive_leaps': (B4.4, 15),
}
```

### Phase 3: Style

```python
REWARDS = {
    'contrary_motion': (D1.1, -12),
    'stepwise_motion': (D1.3, -10),
    'subject_fragment': (D3.1, -20),
    'implied_voice': (D5.1, -25),
}
```

---

## ComposerMind Profiles

Different composers weight rules differently:

### Bach Profile

```yaml
name: bach
parallel_fifth_penalty: 100  # Absolute
hidden_fifth_penalty: 15     # Moderate concern
voice_crossing_brief: 3      # Very tolerant
subject_fragment_reward: 25  # Highly values thematic unity
implied_voice_reward: 30     # Master of compound melody
stepwise_preference: 0.8     # Prefers steps but accepts leaps
```

### Handel Profile

```yaml
name: handel
parallel_fifth_penalty: 100
hidden_fifth_penalty: 10     # Less concerned
voice_crossing_brief: 8      # Less tolerant
subject_fragment_reward: 15  # Less obsessive about unity
homophonic_bonus: 10         # Values clear harmony
leap_tolerance: 0.9          # More tolerant of leaps
```

### Telemann Profile

```yaml
name: telemann
parallel_fifth_penalty: 100
hidden_fifth_penalty: 8      # Galant tolerance
voice_crossing_brief: 2      # Very tolerant
sequential_bonus: 20         # Loves sequences
parallel_thirds_bonus: 5     # Galant acceptance
melodic_singability: 1.2     # Prioritizes tuneful lines
```

---

*Document version: 1.0*
*Last updated: January 2025*
