# Baroque Implementation Plan

A numbered, logical implementation guide for Claude Code. Each section specifies WHAT to implement, WHY it matters, and HOW to validate.

Reference: `baroque_literature.md` for full theory.

---

## Phase 1: Voice-Leading Hard Constraints

**Priority**: CRITICAL — violations make output unusable.

### 1.1 Parallel Motion Detection

**What**: Detect parallel fifths, octaves, unisons between any voice pair.

**Implementation**:
```python
def detect_parallel(voice_a: List[int], voice_b: List[int]) -> List[Violation]:
    """
    For each consecutive pair of notes:
    1. Calculate interval_1 = abs(voice_a[i] - voice_b[i]) % 12
    2. Calculate interval_2 = abs(voice_a[i+1] - voice_b[i+1]) % 12
    3. If interval_1 == interval_2 AND interval_1 in {0, 7} (unison/octave or fifth):
       - Check neither voice is stationary (both moved)
       - Check same direction (both ascending or both descending)
       - If all true: VIOLATION
    """
```

**Test cases**:
- C-G followed by D-A (parallel fifths) → VIOLATION
- C-G followed by D-G (oblique motion) → OK
- C-C followed by D-D (parallel unison) → VIOLATION

### 1.2 Direct (Hidden) Fifth/Octave Detection

**What**: Detect similar motion approaching perfect consonance when soprano leaps.

**Implementation**:
```python
def detect_direct_perfect(soprano: List[int], bass: List[int]) -> List[Violation]:
    """
    For each transition:
    1. Calculate arriving_interval = abs(soprano[i+1] - bass[i+1]) % 12
    2. If arriving_interval in {0, 7, 12}:  # unison, fifth, octave
       - Check similar motion (both ascending or both descending)
       - Check soprano leaped (abs(soprano[i+1] - soprano[i]) > 2)
       - If both true: VIOLATION
    """
```

**Exception**: Allow if soprano moves by step (Fux).

### 1.3 Dissonance Validation

**What**: Ensure all dissonances are properly prepared and resolved.

**Implementation**:
```python
def validate_dissonance(beat: Beat, prev_beat: Beat, next_beat: Beat) -> List[Violation]:
    """
    1. Identify dissonant intervals: {1, 2, 6, 10, 11} semitones
    2. For each dissonance on STRONG beat:
       - Check preparation: same pitch must be present on previous weak beat
       - Check resolution: must step DOWN to consonance
       - Exception: leading tone may resolve UP
    3. For each dissonance on WEAK beat:
       - Check it's approached by step (passing) OR
       - Check it's a neighbour (step away and return) OR
       - Check it's an anticipation (same pitch follows)
    """
```

**Dissonant intervals** (semitones): 1 (m2), 2 (M2), 6 (tritone), 10 (m7), 11 (M7).

### 1.4 Voice Overlap Detection

**What**: Detect when a voice crosses the previous position of an adjacent voice.

**Implementation**:
```python
def detect_voice_overlap(voices: List[List[int]]) -> List[Violation]:
    """
    For adjacent voice pairs (S-A, A-T, T-B):
    1. Get previous position of lower voice: prev_lower = voices[lower][i]
    2. Get current position of upper voice: curr_upper = voices[upper][i+1]
    3. If curr_upper < prev_lower: VIOLATION (upper crossed below previous lower)
    4. Similarly check lower voice crossing above previous upper
    """
```

---

## Phase 2: Melodic Constraints

**Priority**: HIGH — affects melodic quality.

### 2.1 Leap Compensation

**What**: Leaps should be followed by contrary stepwise motion.

**Implementation**:
```python
def check_leap_compensation(melody: List[int]) -> List[Violation]:
    """
    1. Detect leap: abs(melody[i+1] - melody[i]) > 2 (more than step)
    2. Check compensation: 
       - Following interval should be step (abs <= 2)
       - Following direction should be opposite
    3. Penalty if not compensated (not hard violation)
    """
```

**Cost**: 10 points per uncompensated leap.

### 2.2 Consecutive Same-Direction Leaps

**What**: Avoid two leaps in the same direction.

**Implementation**:
```python
def check_consecutive_leaps(melody: List[int]) -> List[Violation]:
    """
    1. For each note triplet [a, b, c]:
       - interval_1 = b - a
       - interval_2 = c - b
    2. If abs(interval_1) > 2 AND abs(interval_2) > 2:
       - If sign(interval_1) == sign(interval_2): VIOLATION
    """
```

**Cost**: 15 points per occurrence.

### 2.3 Tritone Outline

**What**: Avoid melodic lines that outline a tritone within 4 notes.

**Implementation**:
```python
def check_tritone_outline(melody: List[int]) -> List[Violation]:
    """
    For each 4-note window [a, b, c, d]:
    1. Calculate outer interval = abs(d - a) % 12
    2. If outer_interval == 6: VIOLATION (tritone outline)
    """
```

**Cost**: 20 points per occurrence.

### 2.4 Augmented/Large Intervals

**What**: Avoid augmented intervals and sevenths.

**Implementation**:
```python
def check_forbidden_intervals(melody: List[int]) -> List[Violation]:
    """
    For each melodic interval:
    1. Calculate interval = melody[i+1] - melody[i]
    2. abs_interval = abs(interval)
    3. If abs_interval in {6, 10, 11}: VIOLATION (tritone, m7, M7)
    4. If abs_interval > 12: VIOLATION (larger than octave)
    """
```

**Costs**: Augmented = 30, Seventh = 25, >Octave = 30.

---

## Phase 3: Harmonic Realisation

**Priority**: HIGH — determines harmonic vocabulary.

### 3.1 Rule of the Octave Implementation

**What**: Harmonise scalar bass according to direction and degree.

**Implementation**:
```python
RULE_OF_OCTAVE = {
    'ascending': {
        1: '5/3', 2: '6/3', 3: '6/3', 4: '6/5/3',
        5: '5/3', 6: '6/3', 7: '6/5/3', 8: '5/3'
    },
    'descending': {
        8: '5/3', 7: '6/3', 6: '#6/4/3', 5: '5/3',
        4: '6/4/2', 3: '6/3', 2: '6/4/3', 1: '5/3'
    }
}

def harmonise_bass(bass_degrees: List[int], directions: List[str]) -> List[str]:
    """
    1. For each bass degree with known direction:
       - Look up chord in RULE_OF_OCTAVE[direction][degree]
    2. For degrees 4 descending and 6 descending:
       - Apply special dissonance (raised 6th, 6/4/2)
    3. Return figured bass symbols
    """
```

### 3.2 Bass Motion Pattern Detection

**What**: Detect sequential patterns and apply appropriate harmonisation.

**Implementation**:
```python
BASS_PATTERNS = {
    'circle_fifths': ([4, -5], ['5/3', '5/3']),  # up 4th, down 5th
    'up3_down1': ([3, -1], ['5/3', '6/3']),      # up 3rd, down step
    'down3_up1': ([-3, 1], ['5/3', '6/3']),      # down 3rd, up step
    # ... etc
}

def detect_bass_pattern(bass: List[int]) -> Optional[str]:
    """
    1. Calculate intervals between consecutive bass notes
    2. Match against known patterns
    3. Return pattern name or None
    """

def harmonise_pattern(bass: List[int], pattern: str) -> List[str]:
    """
    1. Get harmonisation options for pattern
    2. Select based on context (dissonant options for cadential)
    3. Return figured bass
    """
```

### 3.3 Suspension Implementation

**What**: Generate and resolve suspensions according to rules.

**Implementation**:
```python
SUSPENSION_TYPES = {
    '4-3': {'preparation': [8, 3, 5, 6], 'resolution': 'step_down'},
    '7-6': {'preparation': [8, 3, 5, 6], 'resolution': 'step_down'},
    '9-8': {'preparation': [3, 5], 'resolution': 'step_down'},
    '2-3': {'preparation': 'any_consonance', 'resolution': 'bass_step_up'},
}

def generate_suspension(chord: Chord, suspension_type: str) -> Chord:
    """
    1. Verify preparation consonance is present
    2. Delay resolution note by one beat
    3. Ensure accompanying intervals are correct (4th needs 5th present)
    4. Return modified chord
    """
```

---

## Phase 4: Phrase Structure

**Priority**: HIGH — determines formal organisation.

### 4.1 Phrase Sequence Validation

**What**: Validate that phrase sequences follow Koch's rules.

**Implementation**:
```python
PHRASE_SEQUENCES = {
    ('I', 'V'): True,   # I-phrase → V-phrase: OK
    ('I', 'I'): False,  # I-phrase → I-phrase: FORBIDDEN
    ('V', 'I'): False,  # V-phrase → I-phrase (at start): FORBIDDEN
    ('V', 'V'): 'different_key_only',  # V → V only in different keys
    ('V', 'CAD'): True, # V-phrase → Cadence: OK
    ('I', 'CAD'): True, # I-phrase → Cadence: OK
}

def validate_phrase_sequence(phrases: List[Phrase]) -> List[Violation]:
    """
    1. For each consecutive phrase pair:
       - Get phrase types (I, V, CAD)
       - Look up in PHRASE_SEQUENCES
       - If False: VIOLATION
       - If 'different_key_only': check keys differ
    """
```

### 4.2 Caesura Placement

**What**: Ensure caesuras fall on strong beats with proper bass.

**Implementation**:
```python
def validate_caesura(phrase: Phrase) -> List[Violation]:
    """
    1. Get caesura position (last note of phrase)
    2. Check metrical position is strong beat
    3. Check bass note is root of caesura chord (not 6th chord)
       - Exception: incises may use 6th chord
    4. Check caesura chord matches phrase type:
       - I-phrase: tonic chord
       - V-phrase: dominant chord
    """
```

### 4.3 Extension Method Implementation

**What**: Implement phrase extension by repetition, appendix, sequence, parenthesis.

**Implementation**:
```python
def extend_by_repetition(phrase: Phrase, segment: str, varied: bool) -> Phrase:
    """
    1. Extract segment (measure or incise)
    2. If incomplete incises: MUST repeat both
    3. Repeat with or without variation
    4. Return extended phrase
    """

def extend_by_sequence(phrase: Phrase, segment_size: int, steps: int) -> Phrase:
    """
    1. Extract segment of segment_size measures
    2. Repeat on different scale degrees
    3. CRITICAL: maintain segment equality throughout
    4. Return extended phrase
    """

def extend_by_appendix(phrase: Phrase, content: str) -> Phrase:
    """
    1. Add clarifying segment after phrase-ending
    2. Appendix doesn't change rhythmic value
    3. Return extended phrase
    """
```

### 4.4 Period Structure Generation

**What**: Generate standard 8+8 bar periods.

**Implementation**:
```python
def generate_period(key: str, mode: str) -> Period:
    """
    First Half (8 bars):
    1. Phrase 1: I-phrase or V-phrase (4 bars)
    2. Phrase 2: Cadence in I or V (4 bars)
    
    Second Half (8 bars):
    3. Phrase 3: Development/modulation (4 bars)
    4. Phrase 4: Cadence in I (4 bars)
    
    Modulation targets:
    - Major: V (dominant)
    - Minor: v or III
    """
```

---

## Phase 5: Cadence Generation

**Priority**: HIGH — determines phrase endings.

### 5.1 Cadence Formula Implementation

**What**: Generate proper cadence formulas with preparation-cadential-caesura structure.

**Implementation**:
```python
def generate_cadence(cadence_type: str, key: str) -> CadenceFormula:
    """
    1. Create preparation note on strong beat
       - May be decorated with passing/neighbour
    2. Create cadential note proper
    3. Create caesura note
    4. Bass: V-I motion (or variant for type)
    5. Soprano: NEVER end on 5th for authentic cadence
    """

CADENCE_TYPES = {
    'perfect_authentic': {'bass': 'V-I', 'soprano': '2-1 or 7-1'},
    'imperfect_authentic': {'bass': 'V-I', 'soprano': 'to 3 or 5'},
    'half': {'bass': 'to V', 'soprano': 'any'},
    'deceptive': {'bass': 'V-vi', 'soprano': '7-1 (in vi)'},
    'phrygian': {'bass': 'iv6-V', 'soprano': 'descending'},
}
```

### 5.2 Cadence Validation

**What**: Validate cadence follows rules.

**Implementation**:
```python
def validate_cadence(cadence: Cadence) -> List[Violation]:
    """
    1. Check bass motion is correct for type
    2. Check soprano NOT on 5th at authentic cadence
    3. Check leading tone resolves up
    4. Check preparation is properly on strong beat
    """
```

---

## Phase 6: Schema Implementation

**Priority**: MEDIUM — provides idiomatic vocabulary.

### 6.1 Schema Data Structure

**What**: Define schemas with bass/melody scale degrees and metric positions.

**Implementation**:
```python
@dataclass
class Schema:
    name: str
    events: List[SchemaEvent]
    function: str  # 'opening', 'riposte', 'sequence', 'thematic', 'framing'
    
@dataclass
class SchemaEvent:
    metric: str  # 'strong' or 'weak'
    melody_degree: int
    bass_degree: int
    figured_bass: str

SCHEMAS = {
    'romanesca': Schema(
        name='romanesca',
        events=[
            SchemaEvent('strong', 1, 1, '5/3'),
            SchemaEvent('weak', None, 7, '6/3'),
            SchemaEvent('strong', None, 6, '6/3'),
            SchemaEvent('weak', 1, 3, '6/3'),
        ],
        function='opening'
    ),
    'prinner': Schema(
        name='prinner',
        events=[
            SchemaEvent('strong', 6, 4, '5/3'),
            SchemaEvent('weak', 5, 3, '6/3'),
            SchemaEvent('strong', 4, 2, '6/3'),
            SchemaEvent('weak', 3, 1, '5/3'),
        ],
        function='riposte'
    ),
    # ... etc
}
```

### 6.2 Schema Selection

**What**: Select appropriate schema based on context.

**Implementation**:
```python
def select_schema(context: PhraseContext) -> Schema:
    """
    1. If opening: DO_RE_MI or ROMANESCA
    2. If follows opening: PRINNER (riposte)
    3. If after double bar: FONTE or PONTE
    4. If needs ascending sequence: MONTE
    5. If post-cadence: QUIESCENZA
    6. If dominant key: FENAROLI
    7. If slow tempo: SOL_FA_MI
    8. Default: MEYER
    """
```

---

## Phase 7: Ornamentation

**Priority**: MEDIUM — adds period authenticity.

### 7.1 Appoggiatura Generation

**What**: Generate appoggiaturas according to CPE Bach rules.

**Implementation**:
```python
def add_appoggiatura(note: Note, time_signature: TimeSignature) -> Note:
    """
    1. Determine duration:
       - Duple time: half of principal note
       - Triple time: two-thirds of principal
    2. Pitch: step above or below principal
    3. Dynamics: louder than resolution
    4. Articulation: slurred to following
    """
```

### 7.2 Trill Generation

**What**: Generate trills according to rules.

**Implementation**:
```python
def add_trill(note: Note) -> Trill:
    """
    1. Start from upper note (always)
    2. Check no augmented 2nd interval with upper
    3. Add suffix if cadential
    4. Suffix speed = trill speed
    """
```

### 7.3 Ornament Placement Rules

**What**: Determine where ornaments are appropriate.

**Implementation**:
```python
def should_ornament(note: Note, context: Context) -> Optional[str]:
    """
    1. Long notes in slow movements: TRILL
    2. Short detached notes: MORDENT (but not on descending 2nds)
    3. Cadential approaches: APPOGGIATURA
    4. Sustained notes: TURN
    5. Fast passages: typically unornamented
    """
```

---

## Phase 8: Motif Development

**Priority**: MEDIUM — provides thematic variety.

### 8.1 Counter-Subject Generation

**What**: Generate counter-subject that complements subject.

**Implementation**:
```python
def generate_countersubject(subject: List[Note]) -> List[Note]:
    """
    1. Analyse subject for rhythm pattern
    2. Generate complementary rhythm (fast where slow, slow where fast)
    3. Generate contrary motion (ascending where descending)
    4. Validate invertibility:
       - Check no parallel 5ths that become 4ths
       - Test with voices swapped
    """
```

### 8.2 Head/Tail Extraction

**What**: Extract head and tail motifs from subject.

**Implementation**:
```python
def extract_motifs(subject: List[Note]) -> Dict[str, List[Note]]:
    """
    1. Head: first 3-4 notes (to first rhythmic boundary)
    2. Tail: last 3-4 notes
    3. Store as independent motifs for separate development
    """
```

### 8.3 Derived Motif Generation

**What**: Pre-compute derived motifs from subject.

**Implementation**:
```python
def generate_derived_motifs(subject: List[Note]) -> Dict[str, List[Note]]:
    """
    1. motif_inversion: invert all intervals
    2. motif_augmentation: double all durations
    3. motif_retrograde: reverse note order
    4. motif_head_inverted: invert head only
    5. Store all as independent material for phrase variation
    """
```

---

## Phase 9: Meter and Rhythm

**Priority**: MEDIUM — maintains metric coherence.

### 9.1 Metrical Stress Validation

**What**: Ensure accompaniment maintains metrical motion during melody rests.

**Implementation**:
```python
def validate_metrical_stress(melody: Voice, accompaniment: Voice) -> List[Violation]:
    """
    1. For each beat where melody rests or ties:
       - Check accompaniment has activity
    2. Maximum 2 consecutive tied subdivisions allowed
    3. If melody figure unclear, accompaniment must clarify
    """
```

### 9.2 Rhythmic Complement

**What**: Generate rhythmically complementary accompaniment.

**Implementation**:
```python
def complement_rhythm(melody: Voice) -> Voice:
    """
    1. Where melody has long notes: use shorter values in accompaniment
    2. Where melody rests: fill with activity
    3. Where melody moves quickly: accompaniment may rest or hold
    4. Maintain metric clarity throughout
    """
```

---

## Phase 10: Expression and Affect

**Priority**: LOW — refinement layer.

### 10.1 Affect-Driven Parameter Selection

**What**: Set tempo, mode, key from intended affect.

**Implementation**:
```python
AFFECTS = {
    'joyful': {'tempo': 'allegro', 'mode': 'major', 'keys': ['D', 'A', 'G']},
    'sorrowful': {'tempo': 'adagio', 'mode': 'minor', 'keys': ['E', 'C', 'G']},
    'tender': {'tempo': 'andante', 'mode': 'major', 'keys': ['F', 'Bb']},
    'martial': {'tempo': 'vivace', 'mode': 'major', 'keys': ['D', 'C']},
    # ... etc
}

def select_parameters(affect: str) -> CompositionParams:
    """
    1. Look up affect in AFFECTS dictionary
    2. Return tempo, mode, key suggestions
    """
```

---

## Validation Test Suite

### Unit Tests per Phase

**Phase 1 Tests**:
- `test_parallel_fifths_detected()` — known parallel 5ths flagged
- `test_parallel_octaves_detected()` — known parallel 8ves flagged
- `test_oblique_motion_allowed()` — oblique motion not flagged
- `test_direct_fifth_soprano_leap()` — hidden 5th with soprano leap flagged
- `test_dissonance_preparation()` — unprepared strong-beat dissonance flagged
- `test_dissonance_resolution()` — unresolved dissonance flagged

**Phase 2 Tests**:
- `test_leap_compensation()` — uncompensated leap penalised
- `test_consecutive_leaps()` — same-direction leaps penalised
- `test_tritone_outline()` — tritone outline flagged

**Phase 3 Tests**:
- `test_rule_of_octave_ascending()` — correct chords for ascending bass
- `test_rule_of_octave_descending()` — correct chords for descending bass
- `test_suspension_preparation()` — suspensions properly prepared
- `test_suspension_resolution()` — suspensions resolve down by step

**Phase 4 Tests**:
- `test_phrase_sequence_I_V()` — I→V allowed
- `test_phrase_sequence_I_I()` — I→I forbidden
- `test_caesura_strong_beat()` — caesura on strong beat
- `test_sequence_segment_equality()` — segment equality maintained

**Phase 5 Tests**:
- `test_authentic_cadence_soprano()` — soprano not on 5th
- `test_leading_tone_resolution()` — leading tone resolves up
- `test_cadence_bass_motion()` — V-I bass motion

---

## Implementation Order

Execute in this order to build on foundations:

1. **Phase 1** — Voice-leading hard constraints (blocks bad output)
2. **Phase 2** — Melodic constraints (improves line quality)
3. **Phase 5** — Cadences (defines phrase endings)
4. **Phase 4** — Phrase structure (organises form)
5. **Phase 3** — Harmonic realisation (fills in chords)
6. **Phase 6** — Schemas (provides idiomatic patterns)
7. **Phase 9** — Meter/rhythm (ensures metric coherence)
8. **Phase 8** — Motif development (adds variety)
9. **Phase 7** — Ornamentation (period authenticity)
10. **Phase 10** — Expression/affect (refinement)

---

## File Locations

| Phase | Primary File | Data File |
|-------|--------------|-----------|
| 1 | `engine/voice_checks.py` | — |
| 2 | `engine/voice_checks.py` | — |
| 3 | `engine/rule_of_octave.py` | `data/rule_of_octave.yaml` |
| 4 | `planner/phrase_structure.py` | `data/phrase_rules.yaml` |
| 5 | `engine/cadence.py` | `data/cadences.yaml` |
| 6 | `planner/schemata.py` | `data/schemas.yaml` |
| 7 | `engine/ornament.py` | `data/ornaments.yaml` |
| 8 | `planner/motif.py` | — |
| 9 | `engine/meter.py` | — |
| 10 | `planner/affect.py` | `data/affects.yaml` |

---

## Success Criteria

A piece is valid baroque if:

1. **Zero hard constraint violations** (Phase 1)
2. **Melodic penalty score < 50** (Phase 2)
3. **All cadences follow rules** (Phase 5)
4. **Phrase sequences valid** (Phase 4)
5. **Harmonic vocabulary from RO/patterns** (Phase 3)
6. **At least 50% schema-derived material** (Phase 6)
7. **Metric stress maintained** (Phase 9)
8. **Thematic unity via motif development** (Phase 8)

---

*Implementation plan created: 2026-01-16*
*Reference: baroque_literature.md*
