# Period Style Support: Classical and Romantic

Future work to support Classical (1750-1820) and Romantic (1820-1900) periods.

## Architecture

Extract hardcoded baroque assumptions into `StyleProfile` loaded from YAML.

```
data/styles/
├── baroque.yaml      # Current defaults
├── classical.yaml
└── romantic.yaml

engine/
└── style_profile.py  # StyleProfile dataclass + loader
```

## StyleProfile Structure

```python
@dataclass
class StyleProfile:
    name: str
    period: str  # "baroque", "classical", "romantic"

    # Voice leading
    step_bonus: float           # baroque=1.0, romantic=0.5
    leap_tolerance: int         # baroque=7, classical=9, romantic=12
    chromatic_passing: bool     # baroque=False, romantic=True

    # Sonority
    non_chord_tone_cost: float  # baroque=15, classical=12, romantic=5
    seventh_default: bool       # baroque=False, classical=True, romantic=True
    ninth_allowed: bool         # baroque=False, classical=False, romantic=True
    chromatic_color_bonus: float  # baroque=0, romantic=8

    # Spacing
    min_voice_separation: int   # baroque=3, romantic=2
    crossing_penalty: float     # baroque=50, classical=40, romantic=20
    unison_penalty: float       # baroque=50, classical=30, romantic=15
    octave_doubling_cost: float # baroque=8, classical=5, romantic=2

    # Parallels
    parallel_fifth_penalty: float   # baroque=100, romantic=80
    parallel_octave_penalty: float  # baroque=100, romantic=60
    hidden_fifth_ok: bool           # baroque=False, classical=True, romantic=True
    parallel_thirds_bonus: float    # baroque=0, classical=5, romantic=10
    parallel_sixths_bonus: float    # baroque=0, classical=5, romantic=10

    # Motion preferences
    contrary_bonus: float       # baroque=12, classical=8, romantic=5
    oblique_bonus: float        # baroque=4, classical=3, romantic=2
    parallel_cost: float        # baroque=6, classical=3, romantic=0

    # Bass behavior
    bass_assumes_root: bool     # baroque=True, classical=False, romantic=False
    bass_leap_tolerance: int    # baroque=12, romantic=16
    pedal_point_ok: bool        # all=True
    walking_bass_weight: float  # baroque=1.0, classical=0.5, romantic=0.3

    # Texture
    voice_independence_weight: float  # baroque=1.0, classical=0.7, romantic=0.5
    homophonic_default: bool          # baroque=False, classical=True, romantic=True
```

---

## Classical Period Specifics

### Harmonic Language
- [ ] Support Alberti bass patterns (broken chord accompaniment)
- [ ] Add cadential 6/4 chord recognition (bass on 5th, not root)
- [ ] Implement dominant seventh as default dominant function
- [ ] Add secondary dominants (V/V, V/vi common)
- [ ] Support half cadences ending on V

### Voice Leading
- [ ] Allow hidden fifths between outer voices if soprano moves by step
- [ ] Reduce penalty for parallel thirds/sixths (galant style)
- [ ] Support wider melodic leaps (octave leaps common in Mozart)
- [ ] Allow more voice crossings in inner voices

### Texture
- [ ] Melody + accompaniment as default texture
- [ ] Implement Alberti bass generator
- [ ] Support "singing allegro" style (lyrical melody over active bass)
- [ ] Add horn fifth patterns for wind writing

### Form
- [ ] Periodic phrase structure (4+4 bar phrases)
- [ ] Support antecedent-consequent relationships
- [ ] Half cadence at phrase midpoint
- [ ] PAC at phrase end

### Specific Patterns
```yaml
# Alberti bass patterns
alberti_a:
  pattern: [root, fifth, third, fifth]  # C-G-E-G
  duration: 1/16 each

alberti_b:
  pattern: [root, third, fifth, third]  # C-E-G-E
  duration: 1/16 each

# Cadential patterns
classical_cadence:
  bass: [I6/4, V7, I]
  soprano: [scale_degree_1, leading_tone, tonic]
```

---

## Romantic Period Specifics

### Harmonic Language
- [ ] Support chromatic mediants (C major to Ab major, E major)
- [ ] Add augmented sixth chords (Italian, French, German)
- [ ] Implement Neapolitan sixth
- [ ] Support enharmonic modulation
- [ ] Add chromatic passing chords
- [ ] Ninth, eleventh, thirteenth chord support
- [ ] Tritone substitution awareness

### Voice Leading
- [ ] Reduce all parallel penalties (orchestral doubling common)
- [ ] Allow chromatic passing tones freely
- [ ] Support cross-relations between voices
- [ ] Large leaps (10ths, 12ths) acceptable with preparation
- [ ] Voice crossing nearly free in thick textures

### Texture
- [ ] Support melody + rich harmonic accompaniment
- [ ] Implement arpeggiated accompaniment patterns
- [ ] Tremolo patterns for strings
- [ ] Thick chord voicings (5-6 note chords)
- [ ] Support octave doubling of melody

### Dynamics and Expression
- [ ] Wider dynamic range affects voicing density
- [ ] Crescendo/diminuendo affect texture buildup
- [ ] Rubato markers affect rhythmic flexibility

### Specific Patterns
```yaml
# Romantic accompaniment patterns
romantic_arpeggio:
  pattern: [root, third, fifth, octave, fifth, third]
  duration: 1/8 each

chopin_waltz_bass:
  pattern: [root_low, chord, chord]  # Oom-pah-pah
  durations: [1/4, 1/4, 1/4]

tremolo:
  pattern: [note, octave_above]
  duration: 1/32 each
  repeat: true
```

---

## Chord Inference Refactoring

Current `infer_chord_from_bass` assumes root position. This breaks for:
- Classical: Frequent inversions (6, 6/4 chords)
- Romantic: Bass often chromatic, non-functional

### Proposed Solution

```python
def infer_chord_smart(
    soprano_midi: int,
    bass_midi: int,
    key: Key,
    style: StyleProfile,
) -> set[int]:
    """Infer chord tones from outer voices."""

    if style.bass_assumes_root:
        # Baroque: bass = root
        return infer_chord_from_bass(bass_midi, key)

    # Classical/Romantic: analyze interval
    interval = (soprano_midi - bass_midi) % 12
    bass_pc = bass_midi % 12
    soprano_pc = soprano_midi % 12

    # Check if bass is chord tone of soprano-implied chord
    # If soprano on C and bass on E, likely C major first inversion
    # If soprano on C and bass on G, likely C major second inversion

    # Try building triads where both outer voices are chord tones
    candidates = []
    for root_pc in range(12):
        third_pc = (root_pc + 3) % 12  # minor third
        major_third_pc = (root_pc + 4) % 12
        fifth_pc = (root_pc + 7) % 12

        # Check if both soprano and bass fit
        chord_pcs = {root_pc, major_third_pc, fifth_pc}
        if bass_pc in chord_pcs and soprano_pc in chord_pcs:
            candidates.append(chord_pcs)

        chord_pcs_minor = {root_pc, third_pc, fifth_pc}
        if bass_pc in chord_pcs_minor and soprano_pc in chord_pcs_minor:
            candidates.append(chord_pcs_minor)

    # Prefer diatonic chords
    diatonic = [c for c in candidates if _is_diatonic(c, key)]
    if diatonic:
        return diatonic[0]

    # Fallback to bass-as-root
    return infer_chord_from_bass(bass_midi, key)
```

---

## Files Requiring Changes

### Core Scoring
- `engine/slice_solver.py` - Replace constants with StyleProfile lookups
- `engine/inner_voice.py` - Pass StyleProfile to scoring
- `engine/bass_solver.py` - Period-specific bass patterns

### Pattern Data
- `data/bass_patterns/` - Period-specific subdirectories
- `data/cadence_patterns/` - Classical and Romantic cadences
- `data/accompaniment_patterns/` - Alberti, arpeggios, etc.

### Pipeline
- `engine/pipeline.py` - Accept style parameter
- `engine/expander.py` - Pass style through expansion
- `planner/` - Style-aware planning

### New Files
- `engine/style_profile.py` - StyleProfile dataclass
- `engine/style_loader.py` - YAML loader
- `data/styles/*.yaml` - Period definitions

---

## Migration Strategy

1. Extract current baroque constants to `baroque.yaml`
2. Create `StyleProfile` that loads from YAML
3. Add `style: str = "baroque"` parameter to pipeline entry points
4. Replace hardcoded constants with `style.constant_name`
5. Verify baroque output unchanged
6. Add classical profile with adjusted values
7. Add romantic profile
8. Test with period-appropriate compositions

---

## Test Cases Needed

### Classical
- Mozart K.545 opening (Alberti bass + singing melody)
- Haydn symphony theme (periodic phrasing)
- Classical cadence with 6/4

### Romantic
- Chopin nocturne texture (melody + arpeggiated accompaniment)
- Wagner chromatic passage (non-functional harmony)
- Brahms intermezzo (thick voicing, voice crossing)

---

## Priority

1. **P1**: StyleProfile extraction (enables everything else)
2. **P1**: Chord inference refactoring (fixes scoring accuracy)
3. **P2**: Classical Alberti bass patterns
4. **P2**: Classical cadential 6/4
5. **P3**: Romantic chromatic mediants
6. **P3**: Romantic thick voicings
