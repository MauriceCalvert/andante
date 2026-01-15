# Violin Playability Constraints

Reference for generating idiomatic violin music. All constraints derived from professional technique.

## Range

| Boundary | Note | MIDI | Context |
|----------|------|------|---------|
| Absolute low | G3 | 55 | Open G string |
| Absolute high | A7 | 105 | 14th-15th position, virtuoso |
| Practical high | E7 | 100 | 8th position, orchestral limit |
| Comfortable high | G6 | 91 | Student/amateur limit |

**Open strings:** G3 (55), D4 (62), A4 (69), E5 (76)

## Positions

| Position | 1st finger on G | 1st finger on E | Notes |
|----------|-----------------|-----------------|-------|
| 1st | A3 (57) | F#5 (78) | Most common |
| 2nd | B3 (59) | G#5 (80) | Rarely used alone |
| 3rd | C4 (60) | A5 (81) | Second learned |
| 4th | D4 (62) | B5 (83) | |
| 5th | E4 (64) | C#6 (85) | |
| 6th | F4 (65) | D6 (86) | |
| 7th | G4 (67) | E6 (88) | |
| 8th+ | A4+ (69+) | F6+ (89+) | Virtuoso territory |

Each position spans a perfect fourth (5 semitones) with four fingers.

## Double Stops (Two Simultaneous Notes)

### Constraint: Adjacent Strings Only

Only these string pairs can sound together:
- G + D (MIDI 55-61 + 62-73)
- D + A (MIDI 62-73 + 69-80)
- A + E (MIDI 69-80 + 76-100)

**Impossible:** G + A, G + E, D + E (non-adjacent)

### Interval Limits by Type

| Interval | Semitones | Finger Pattern | Difficulty | Notes |
|----------|-----------|----------------|------------|-------|
| Minor 2nd | 1 | 4-3 or 3-2 | Hard | Dissonant, rare |
| Major 2nd | 2 | 4-3 or 3-2 | Hard | Stretch required |
| Minor 3rd | 3 | 3-1, 4-2 | Easy | Very common |
| Major 3rd | 4 | 3-1, 4-2 | Easy | Very common |
| Perfect 4th | 5 | 2-1, 3-2, 4-3 | Easy | Higher finger on lower string |
| Augmented 4th | 6 | varies | Medium | Tritone |
| Perfect 5th | 7 | single finger | Hard | One finger bars two strings |
| Minor 6th | 8 | 1-2, 2-3 | Easy | Very common |
| Major 6th | 9 | 1-2, 2-3 | Easy | Very common |
| Minor 7th | 10 | 1-3 | Medium | Less common |
| Major 7th | 11 | 1-3 | Medium | Less common |
| Octave | 12 | 1-4 | Medium | Stretch, easier in high positions |
| Minor 9th | 13 | 1-4 + stretch | Hard | Large hands only |
| Major 9th | 14 | 1-4 + stretch | Hard | Large hands only |
| Minor 10th | 15 | 1-4 + extreme | Very hard | Virtuoso, large hands |
| Major 10th | 16 | 1-4 + extreme | Very hard | Maximum practical stretch |

**Rule:** Intervals become easier in higher positions (shorter string = smaller physical distance).

### Easiest Double Stops
1. **Thirds** (3-4 semitones) — most common, comfortable hand frame
2. **Sixths** (8-9 semitones) — natural hand position, pleasing sound
3. **Octaves** (12 semitones) — stretch but standard technique

### Hardest Double Stops
1. **Fifths** — single finger must press two strings cleanly
2. **Tenths** — extreme stretch, virtuoso repertoire only
3. **Seconds** — awkward, dissonant, tuning difficult

## Triple and Quadruple Stops

### Triple Stops (3 notes)
- Require forte dynamics (heavy bow pressure)
- At softer dynamics, arpeggiated (bottom note first, then top two)
- All three notes must be on adjacent strings (G+D+A or D+A+E)
- Typically short, accented chords

### Quadruple Stops (4 notes, all strings)
- Always arpeggiated in practice
- Bottom 1-2 notes sound briefly, then top 2 sustain
- Creates illusion of four-note chord
- Used for dramatic effect (Bach Chaconne, Tchaikovsky concerto)

### Chord Voicing Rules
- Open strings reduce fingers needed (easier)
- More fingers = harder
- Maximum 3 stopped notes practical
- Prefer voicings with open strings or fifths (single finger)

## Melodic Intervals

### Comfortable Melodic Leaps
| Interval | Semitones | Notes |
|----------|-----------|-------|
| Step | 1-2 | Easiest, no shift |
| Third | 3-4 | Easy, same position |
| Fourth | 5 | Easy, often same position |
| Fifth | 7 | May require shift |
| Sixth | 8-9 | Usually requires shift |
| Octave | 12 | Shift or string change |

### Avoid in Melodic Lines
- **Tritone** (6 semitones) — historically "diabolus in musica," hard to tune
- **Major 7th** (11 semitones) — awkward, difficult to pitch accurately
- **Leaps > octave** — possible but require careful preparation

### String Crossing Considerations
- Adjacent string crossings: easy
- Skipping one string (G→A, D→E): harder, requires arm motion
- Skipping two strings (G→E): very difficult at speed

## Bowing Constraints

### Down Bow vs Up Bow
- **Down bow:** frog to tip, naturally accented, use on strong beats (1, 3)
- **Up bow:** tip to frog, lighter, use on weak beats (2, 4)
- **Pick-up notes:** up bow (to land on down bow for next bar)

### Speed Limits
- Détaché (alternating strokes): very fast possible
- String crossing: slower as more strings involved
- Bariolage (rapid adjacent string alternation): wrist motion at high speed

### Slurs
- Multiple notes per bow stroke
- Practical limit: ~8-12 notes per bow at moderate tempo
- More notes = quieter, less articulated

## Natural Harmonics

Produced by lightly touching (not pressing) at node points:

| Node | Fraction | Position | Resulting pitch |
|------|----------|----------|-----------------|
| Octave | 1/2 | 4th finger, 4th position | Octave above open |
| Octave + 5th | 1/3 | 3rd finger, 3rd position | 12th above open |
| 2 Octaves | 1/4 | 4th finger, high | 2 octaves above open |

Most reliable: 1/2 and 1/3 nodes. Higher partials less reliable.

## Implementation Notes

### For Monophonic Generation (Capriccio, Solo Line)
```yaml
violin:
  min: 55  # G3
  max: 91  # G6 comfortable, 100 E7 professional
  median: 73  # C#5, middle of comfortable range
```

### For Double Stops
- Validate both notes on adjacent strings
- Check interval against difficulty table
- Prefer thirds, sixths for sustained passages
- Allow fifths, octaves for special effect

### For Chords
- Maximum 4 notes
- 3-4 note chords: expect arpeggiation
- Validate all notes on consecutive string pairs
- Open strings simplify fingering

### Guards to Implement
1. **Range check:** min/max MIDI values
2. **Adjacent string check:** for simultaneous notes
3. **Interval stretch check:** based on position (lower = stricter)
4. **String skip check:** avoid G→E leaps at speed

## Sources

- [Violinspiration - Double Stops Chart](https://violinspiration.com/violin-double-stops-chart/)
- [Violinspiration - Violin Range](https://violinspiration.com/violin-range/)
- [Violin Online - Advanced Fingering Chart](https://www.violinonline.com/fingeringchart-advanced.html)
- [The Orchestra: A User's Manual - Violin Chords](https://andrewhugill.com/OrchestraManual/violin_chords.html)
- [Violin Lounge - Bowing Rules](https://violinlounge.com/up-bow-or-down-bow-22-violin-bowing-rules-violin-lounge-tv-467/)
- [Strings Magazine - Double Stops](https://stringsmagazine.com/brush-up-your-double-stops-on-violin-with-this-tricky-interval-exercise/)
- [Violinspiration - Harmonics](https://violinspiration.com/violin-harmonics-simplified-so-you-can-play-them-easily/)
- [Wikipedia - Double Stop](https://en.wikipedia.org/wiki/Double_stop)
