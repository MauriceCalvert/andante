# Note File Format Specification

## Overview

`.note` files are CSV files representing musical scores with analytical
annotations. Each row is a note event. Piece-level constants appear in
`##` metadata headers. Free-text comments use single `#`.

Written by `builder/note_writer.py`.

## Sort Order

Rows are sorted by offset ascending, then MIDI pitch descending. At any
given time position, the highest-sounding note appears first (score
order: soprano before bass). This invariant is guaranteed by the writer
and may be relied upon by all readers.

## Metadata Headers

Lines beginning with `##` are structured key-value metadata. Lines
beginning with single `#` are free-text comments. Parsers should
distinguish between the two by prefix length.

Metadata fields describe piece-level constants that do not vary per note.
Only variable data appears in columns.

```
## key: G major
## time: 4/4
## genre: gavotte
## voices: 2
## anacrusis: 1/2
```

| Field | Type | Description |
|-------|------|-------------|
| `key` | string | Home key: tonic and mode (e.g., `G major`, `D minor`) |
| `time` | string | Time signature (e.g., `4/4`, `3/4`) |
| `genre` | string | Genre name (e.g., `gavotte`, `invention`, `minuet`) |
| `voices` | integer | Number of active voices |
| `anacrusis` | fraction | Anacrusis duration in whole notes. Omitted if zero. |

## Columns

| Column | Type | Per | Description |
|--------|------|-----|-------------|
| `offset` | float | note | Time from piece start in whole notes |
| `midinote` | integer | note | MIDI pitch number (60 = C4) |
| `duration` | fraction | note | Note length in whole notes |
| `track` | integer | note | Voice: 0 = soprano, 3 = bass |
| `bar` | integer | note | Bar number (0-indexed in file; bar 0 = anacrusis) |
| `beat` | float | note | Beat within bar (1-indexed, 1.0 = downbeat) |
| `notename` | string | note | Pitch name with octave (e.g., `G5`, `F#3`) |
| `degree` | string | note | Scale degree relative to local key |
| `harmony` | string | beat | Roman numeral derived from bass note |
| `phrase` | string | phrase | Section label at phrase start |
| `cadence` | string | cadence | Cadence label at cadential arrival |

### Scope of Analytical Columns

- **degree**: written on every note. Values: `1`–`7` for diatonic,
  `#4`, `b7`, etc. for chromatic. Relative to the local key active
  at that bar.

- **harmony**: written on the first note at each offset where the bass
  harmony changes (figured-bass convention). Blank elsewhere. Derived
  from the actual bass note's scale degree, not from planner-level
  abstractions. Values: Roman numerals (`I`, `V`, `ii`, `viio`,
  `V/V`, etc.).

- **phrase**: written on the first note at each phrase start offset.
  Contains the section name, with a bracketed key label when the
  phrase is not in the home key (e.g., `B [D]` for section B in
  D major). Blank elsewhere.

- **cadence**: written on the first note of each cadential bar.
  Values: `PAC`, `HC`, `IAC`, `DC`, `PC`, `PHR`. Blank elsewhere.

## Column Presence

The header line declares which columns are present. Any tool that reads
the header adapts automatically. Files without analytical data simply
omit the `degree`, `harmony`, `phrase`, and `cadence` columns — no
schema version or mode flags required.

## Time Representation

Offset and duration use fractional whole notes:

| Value | Musical duration |
|-------|-----------------|
| 1 | semibreve |
| 1/2 | minim |
| 1/4 | crotchet |
| 1/8 | quaver |

In 3/4 time, one bar = 3/4 = 0.75.

## Track Assignment

Standard SATB layout:

| Track | Voice |
|-------|-------|
| 0 | Soprano (highest) |
| 1 | Alto |
| 2 | Tenor |
| 3 | Bass (lowest) |

For 2-voice textures, tracks 0 and 3 are used.

## Degree Labels

Major key (semitones above tonic → label):

| 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|----|----|
| 1 | b2 | 2 | b3 | 3 | 4 | #4 | 5 | b6 | 6 | b7 | 7 |

Minor key:

| 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|----|----|
| 1 | b2 | 2 | 3 | #3 | 4 | #4 | 5 | 6 | #6 | 7 | #7 |

## Harmony Derivation

Harmony is inferred from the actual bass note at each onset, following
figured-bass convention. Each bass pitch class maps to a Roman numeral:

Major: `1→I, b2→bII, 2→ii, b3→bIII, 3→iii, 4→IV, #4→V/V, 5→V,
b6→bVI, 6→vi, b7→bVII, 7→viio`

Minor: `1→i, b2→bII, 2→iio, 3→III, #3→V/vi, 4→iv, #4→V/V, 5→V,
6→VI, #6→V/iv, 7→VII, #7→viio`

Harmony labels appear only when the chord changes (the Roman numeral
differs from the previous one). This suppresses redundant labels when
the bass moves between octaves or passing tones of the same chord.

## Example

```csv
## key: G major
## time: 4/4
## genre: gavotte
## voices: 2
## anacrusis: 1/2
#
# Experimental output, Plan 3 Phase 1A
#
offset,midinote,duration,track,bar,beat,notename,degree,harmony,phrase,cadence
-0.5,79,1/2,0,0,1.0,G5,1,I,A,
-0.5,43,1/2,3,0,1.0,G2,1,,,,
0.0,81,1/2,0,0,3.0,A5,2,V,,
0.0,54,1/2,3,0,3.0,F#3,7,,,,
0.5,79,1/4,0,1,1.0,G5,1,I,,
0.5,48,1/2,3,1,1.0,C3,4,,,,
```

## File Conventions

- UTF-8 encoding
- Unix line endings (LF)
- No trailing comma
- Empty fields represented as empty string, not null
- `##` lines: structured metadata (key-value)
- `#` lines: free-text comments
- Rows sorted: offset ascending, MIDI pitch descending
