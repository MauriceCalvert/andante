# Note File Format Specification

## Overview

`.note` files are CSV files representing musical scores in a flat, machine-readable format. Each row is a note event.

## Columns

| Column | Type | Description |
|--------|------|-------------|
| `Offset` | Fraction or float | Time from piece start in whole notes (1.0 = one bar in 4/4) |
| `midiNote` | Integer | MIDI pitch number (60 = C4, 72 = C5) |
| `Duration` | Fraction or float | Note length in whole notes |
| `track` | Integer | Voice/part: 0=soprano, 1=alto, 2=tenor, 3=bass |
| `Length` | (Reserved) | Currently unused; may specify tie/phrase length |
| `bar` | Integer | Bar number (1-indexed) |
| `beat` | Float | Beat within bar (1-indexed, 1.0 = downbeat) |
| `noteName` | String | Pitch name with octave (e.g., C4, F#3, Bb5) |
| `lyric` | String | Annotation for analysis or display |

## Lyric Field

The `lyric` field carries analytical annotations, not sung text. Examples:

- Schema markers: `Monte`, `Prinner`, `Fonte`, `Romanesca`
- Cadences: `PAC`, `HC`, `IAC`, `DC` (perfect/half/imperfect/deceptive authentic)
- Key changes: `→G`, `→vi`, `Modulate to D minor`
- Structural markers: `A`, `B`, `Coda`, `Episode`
- Treatment markers: `Subject`, `Answer`, `CS`, `Stretto`

Multiple annotations may be separated by semicolons: `Monte; →V`

## Example

```csv
offset,midinote,duration,track,length,bar,beat,notename,lyric
0,60,0.25,0,,1,1,C4,Subject
0,48,0.5,3,,1,1,C3,do_re_mi
0.25,62,0.25,0,,1,2,D4,
0.5,64,0.5,0,,1,3,E4,
0.5,55,0.25,3,,1,3,G3,
1,67,0.25,0,,2,1,G4,
1,48,0.5,3,,2,1,C3,HC
```

## Track Assignment

Standard SATB layout:
- Track 0: Soprano (highest voice / melody)
- Track 1: Alto
- Track 2: Tenor
- Track 3: Bass (lowest voice)

For 2-voice textures, use tracks 0 and 3 (soprano and bass).

## Time Representation

Offset and Duration use fractional whole notes:
- 1 = whole note / semibreve
- 1/2 = half note / minim
- 1/4 = quarter note / crotchet
- 1/8 = eighth note / quaver

In 3/4 time, one bar = 3/4 = 0.75.

## Comments

Lines starting with `#` are comments and should be ignored by parsers.

```csv
# Freude Minuet - C major, 3/4
# Generated 2026-01-20
offset,midinote,duration,track,length,bar,beat,notename,lyric
0,60,0.25,0,,1,1,C4,Subject
# Section A begins
0,48,0.5,3,,1,1,C3,do_re_mi
```

## File Conventions

- UTF-8 encoding
- Unix line endings (LF)
- No trailing comma
- Empty fields represented as empty string, not null
- Comments start with `#`
