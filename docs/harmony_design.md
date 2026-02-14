# Harmonic Rhythm Layer — Design

## The Problem

The Viterbi solver interpolates melodically between schema anchor points.
It has no idea what chord is active at any given beat. "Consonance" is
currently measured against the other voice's surface pitch — not against
harmonic function. The 22% Bach match confirms this: the system produces
pitch interpolation, not voice-leading.

The consequence is pervasive. The soprano can't prefer chord tones on
strong beats because it doesn't know what the chord is. The bass can't
imply a harmonic progression because it doesn't know what progression to
imply. Both voices move correctly relative to each other but aimlessly
relative to harmony.

## The Insight

The schemas already encode harmony — we just haven't made it explicit.

A do_re_mi with soprano 1, 2, 3 over bass 1, 7, 1 is not three pairs
of intervals. It is I, V, I. A prinner with soprano 6, 5, 4, 3 over
bass 4, 3, 2, 1 is IV (or ii), I, V, I. Every schema in the galant
vocabulary implies a specific chord progression. The progression is not
computed from the degrees — it *is* the schema. Gjerdingen's entire
taxonomy is organised by harmonic function.

This means the harmonic rhythm layer doesn't need to guess, infer, or
compute harmony from voice pitches. It reads it from the schema. The
schema is the harmony, declared in advance, upstream of both voices.

## The Design: Schema-Annotated Block Harmony

### Data in YAML

Each schema in `schemas.yaml` gets a `harmony` field: a list of Roman
numeral strings, one per degree position, stating the chord at that
structural point. Harmony encodes root and quality only — inversion is
derived from the schema's bass degree (if bass=3 and harmony=I, that is
I6 by definition; the pitch-class set is identical either way).

```yaml
do_re_mi:
  harmony: ["I", "V", "I"]

prinner:
  harmony: ["IV", "I", "V", "I"]

romanesca:
  harmony: ["I", "V", "vi", "III", "IV", "I"]

fonte:
  segment:
    harmony: ["V", "i"]

cadenza_semplice:
  harmony: ["V", "V7", "I"]

cadenza_composta:
  harmony: ["IV", "V", "V7", "I"]
```

Roman numeral notation is conventional, compact, and deterministic:

- Case encodes quality: I = major, ii = minor
- Degree suffixes: ° = diminished, + = augmented
- 7 suffix = adds diatonic 7th (V7 = dominant 7th)
- Each string maps to exactly one set of chord-tone scale degrees

Inversion is NOT encoded in the harmony string. The schema's bass degree
already determines which chord member is in the bass. This avoids
redundancy and consistency risk.

This is Law A003 (rules are data). The harmony is musicologically curated,
not algorithmically inferred.

### The ChordLabel

```python
@dataclass(frozen=True)
class ChordLabel:
    root: int                          # scale degree 1-7
    quality: str                       # "major" | "minor" | "diminished" | "augmented"
    members: tuple[int, ...]           # scale degrees in the chord, e.g. (1, 3, 5)
    has_seventh: bool                  # V7, viio7, etc.
    numeral: str                       # original Roman numeral string for display
```

### The Parser

A small module (`builder/harmony.py`, < 100 lines) provides:

```
parse_roman(numeral: str) -> ChordLabel
```

Parsing rules:
- Root from numeral base: I/i=1, II/ii=2, ... VII/vii=7
- Quality from case + suffix: upper=major, lower=minor, °=diminished
- 7 suffix adds the diatonic 7th above the root
- Members: scale degrees of the triad (+ 7th if present) built on root

No key needed at parse time — members are scale degrees, not pitch classes.
Conversion to pitch classes happens at query time via the Key.

### The HarmonicGrid

```python
@dataclass(frozen=True)
class HarmonicGrid:
    entries: tuple[tuple[Fraction, ChordLabel], ...]   # sorted by offset
    key: Key
    default: ChordLabel                                 # tonic chord (void state)
```

Methods:
- `chord_at(offset) -> ChordLabel` — block lookup: latest entry at or before
  query offset. Returns `default` if before first entry.
- `chord_pcs_at(offset) -> frozenset[int]` — pitch classes of chord tones,
  converting member degrees to pitch classes via the Key.
- `to_beat_list(beat_grid) -> list[frozenset[int]]` — parallel list for
  Viterbi solver. One frozenset per beat position.

The void state between schemas (and before the first schema entry) returns
the default chord (tonic). The last chord extends indefinitely. The grid
never returns None.

### Building the Grid

```
def build_harmonic_grid(plan: PhrasePlan) -> HarmonicGrid
```

For each schema degree position:
1. Look up the schema's `harmony` annotation
2. Parse the Roman numeral at that position
3. Compute the absolute offset of that degree position
4. Emit a `(offset, ChordLabel)` entry

The grid is sparse — one entry per schema structural point. Block lookup
means the chord holds until the next structural point. This is correct:
the schema defines the harmonic skeleton, and between structural points
the harmony is stable.

### Integration

The harmonic grid is built once per phrase, before any voice generation:

```
Current:  PhrasePlan -> soprano_writer -> bass_writer
                         (derives chord from surface bass)

New:      PhrasePlan -> build_harmonic_grid -> HarmonicGrid
                         |                      |
                   soprano generation      bass generation
                   (both see same grid)
```

Both voices receive the same harmonic information. The ~60 lines of
ad-hoc chord inference in `generate_soprano_viterbi()` (the H3 block)
are replaced by a single `grid.to_beat_list(beat_grid)` call.

### What Changes in the Solver

Nothing. The solver already accepts `chord_pcs_per_beat` and applies
`chord_tone_cost`. The data just gets better.

## What This Does NOT Do (Known Limitations)

1. **No interpolation between schema positions.** If a schema spans
   four bars with two structural points, the chord holds for two bars.
   Real music would have faster harmonic rhythm. Phase 1 block harmony
   is always correct — just not always sufficient.

2. **No passing chords.** Between structural harmonies, a real continuo
   player would place passing chords on intermediate strong beats.

3. **No cadential acceleration.** Cadential approach zones typically
   have one chord per beat.

4. **No secondary dominants.** Fonte and monte imply local tonicisations.

5. **No bass inversion preference.** The grid says which pitch classes
   are chord tones but not which the bass should prefer. Inversion is
   derivable (bass degree vs chord root) but not yet used as a cost.

Each gap is a natural future enhancement that slots into the grid.

## Extension Roadmap

### Phase 2: Harmonic Interpolation (densify_grid)

When the gap between schema positions exceeds one bar, insert
conventional approach chords at intermediate strong beats. Vocabulary:
tonic-to-dominant inserts predominant (IV or ii); dominant-to-tonic
resolves directly; other progressions use Rule of the Octave defaults.

Implementation: `densify_grid(grid, metre) -> HarmonicGrid` adds
entries to the sparse grid. Solver interface unchanged.

### Phase 3: Cadential Acceleration

Last two beats before cadential positions get one chord per beat
(typically ii6, V or IV, V). Produces the characteristic "gathering."
Uses existing `cadence_approach: true` flag in schema YAML.

### Phase 4: Bass Inversion Preference

Derive inversion from bass degree vs chord root. Add cost bonus for
the bass preferring the inversion-appropriate pitch class on strong
beats. Root-position chords prefer root in bass; first-inversion
prefer third.

### Phase 5: Secondary Dominants

Sequential schemas (fonte, monte) carry local keys via `degree_keys`.
Mark the chord before a local tonic as V/x, enabling chromatic leading
tones in the solver.

### Phase 6: Note Writer Integration

Every note in the .note file gets `chord` (Roman numeral) and
`chord_role` (chord_tone, passing, neighbour, suspension, appoggiatura)
columns. Enables Bob to read harmony.

## Files

| File | Action |
|------|--------|
| `data/schemas/schemas.yaml` | Add `harmony` field to every schema |
| `builder/harmony.py` | New: ChordLabel, HarmonicGrid, parse_roman, build_harmonic_grid |
| `builder/phrase_writer.py` | Build grid before voice generation, pass to both voices |
| `builder/soprano_writer.py` | Remove H3 chord derivation, accept grid from caller |
| `builder/phrase_types.py` | Possibly add harmony_annotations to schema config type |
| `viterbi/generate.py` | No change (already accepts chord_pcs_per_beat) |
| `viterbi/costs.py` | No change (already has chord_tone_cost) |

## Acceptance

Musical: strong-beat pitches are predominantly chord tones of the
schema-implied harmony. Non-chord-tones on strong beats are
approachable/resolvable (suspensions, accented passing tones).

Measurable proxy: strong-beat chord-tone rate > 80% against the schema
harmony grid (vs current ~74% against surface-bass triads).

Real test: does the bass sound like it's going somewhere harmonically?
