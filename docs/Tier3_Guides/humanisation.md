# Humanisation Engine: Architectural Plan

## Philosophy

Real musical timing isn't random noise on a grid. It's the physical trace of a mind navigating musical structure—anticipating, breathing, emphasising, relaxing. We model the *causes*, not the *effects*.

---

## Architecture Overview

```
.note file
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                   ANALYSIS LAYER                        │
├─────────────────────────────────────────────────────────┤
│  Phrase detection │ Metric hierarchy │ Harmonic tension │
│  Melodic contour  │ Cadence location │ Voice roles      │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                   TIMING MODELS                         │
├─────────────────────────────────────────────────────────┤
│  Rubato    │ Agogic  │ Melodic │ Motor  │ Stochastic   │
│  Engine    │ Accent  │ Lead    │ Model  │ Drift        │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                   DYNAMICS MODELS                       │
├─────────────────────────────────────────────────────────┤
│  Phrase    │ Metric  │ Contour │ Harmonic │ Touch      │
│  Envelope  │ Weight  │ Shaping │ Tension  │ Variation  │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                 ARTICULATION MODEL                      │
├─────────────────────────────────────────────────────────┤
│  Legato/Staccato │ Overlap │ Release │ Attack Shape    │
└─────────────────────────────────────────────────────────┘
    │
    ▼
humanised .note file (or direct MIDI)
```

---

## Module 1: Analysis Layer

### 1.1 Phrase Detection

**Input**: .note with lyric annotations (you already have these)

**Enhancements**:
- Detect phrase boundaries from melodic contour (rests, long notes, direction changes)
- Identify phrase peaks (highest pitch, maximum tension)
- Mark phrase position: `attack | rise | peak | fall | cadence`

**Output**: Each note tagged with:
```python
@dataclass
class PhraseContext:
    phrase_id: int
    position_in_phrase: float      # 0.0 = start, 1.0 = end
    distance_to_peak: float        # signed, negative = before peak
    is_phrase_boundary: bool
    boundary_type: str             # 'breath' | 'cadence' | 'elision'
```

### 1.2 Metric Hierarchy

**Model**: Lerdahl & Jackendoff metric well-formedness

**Compute**: Weight for each metric position
```
4/4 example:
beat 1.0   = 1.0   (primary)
beat 3.0   = 0.7   (secondary)
beat 2.0   = 0.4   (weak)
beat 4.0   = 0.4   (weak)
beat 1.5   = 0.2   (off-beat)
beat 1.25  = 0.1   (sub-division)
```

**Output**:
```python
@dataclass
class MetricContext:
    metric_weight: float           # 0.0 to 1.0
    is_downbeat: bool
    is_syncopation: bool           # strong note on weak beat
    beat_subdivision: int          # 1, 2, 4, 8...
```

### 1.3 Harmonic Tension

**Input**: Both voices, infer vertical intervals

**Compute**:
- Consonance score (unison/octave/fifth = low tension, second/seventh = high)
- Dissonance preparation (was it prepared? suspension?)
- Resolution direction (resolving down = expected, up = unusual)

**Output**:
```python
@dataclass
class HarmonicContext:
    tension: float                 # 0.0 = consonant, 1.0 = harsh dissonance
    is_resolution: bool
    resolution_quality: float      # how satisfying: 0.0 to 1.0
    is_prepared_dissonance: bool
    is_appoggiatura: bool
```

### 1.4 Melodic Contour

**Compute** per voice:
- Interval to previous note (size and direction)
- Local direction (ascending/descending/static)
- Contour position (peak, trough, passing)
- Leap recovery (was previous interval a leap needing stepwise recovery?)

**Output**:
```python
@dataclass
class MelodicContext:
    interval_from_previous: int    # semitones, signed
    is_leap: bool                  # abs(interval) > 2
    is_peak: bool                  # local maximum
    is_trough: bool                # local minimum
    contour_direction: int         # -1, 0, +1
    needs_emphasis: bool           # arrival after leap, peak, etc.
```

### 1.5 Voice Role

**Determine**:
- Is this the melody or accompaniment?
- Is this voice currently stating thematic material?
- Voice density (how many notes per beat in this voice vs other)

**Output**:
```python
@dataclass 
class VoiceContext:
    is_melody: bool
    is_thematic: bool              # stating subject/countersubject
    activity_ratio: float          # notes_per_beat relative to other voice
    voice_id: int
```

---

## Module 2: Timing Models

Each model outputs a timing offset in seconds. These sum.

### 2.1 Rubato Engine

**Purpose**: Phrase-level tempo flexibility

**Model**: Tempo as a continuous curve, not note-by-note

```python
class RubatoEngine:
    def compute_tempo_curve(
        self,
        phrase: Phrase,
        base_tempo: float
    ) -> Callable[[float], float]:
        """
        Returns tempo multiplier as function of phrase position.
        
        Typical shape:
        - Slight acceleration 0.0 -> 0.4 (building energy)
        - Peak tempo at ~0.4 (before melodic peak)
        - Gradual deceleration 0.4 -> 0.9 (relaxing)
        - Ritardando 0.9 -> 1.0 (cadential)
        
        Magnitude depends on:
        - Phrase length (longer = more rubato permitted)
        - Style (baroque = subtle, romantic = dramatic)
        - Cadence strength (PAC = more rit than HC)
        """
```

**Parameters**:
```yaml
rubato:
    max_acceleration: 1.08        # up to 8% faster at peak
    max_deceleration: 0.85        # up to 15% slower at cadence
    acceleration_peak: 0.4        # phrase position of max speed
    cadence_ritardando_start: 0.85
    cadence_ritardando_strength: 0.12  # final 12% slower
    phrase_length_threshold: 4.0  # beats; shorter phrases = less rubato
```

**Implementation**: Compute tempo curve, then integrate to get onset times.

### 2.2 Agogic Accent

**Purpose**: Microdelays on important beats

**Model**: Important notes arrive slightly late (10-40ms), creating emphasis through anticipation.

```python
class AgogicAccent:
    def compute_delay(self, note: Note, ctx: AnalysisContext) -> float:
        delay = 0.0
        
        # Metric weight
        if ctx.metric.is_downbeat:
            delay += 0.015  # 15ms
        
        # Phrase peak gets extra weight
        if ctx.phrase.distance_to_peak == 0:
            delay += 0.025  # 25ms
        
        # Syncopation: early, not late (anticipation)
        if ctx.metric.is_syncopation:
            delay -= 0.020  # 20ms early
        
        # Appoggiatura: lean into it
        if ctx.harmonic.is_appoggiatura:
            delay += 0.012  # 12ms
        
        return delay
```

### 2.3 Melodic Lead

**Purpose**: Melody arrives before accompaniment

**Historical basis**: Measured in 18th-century performance practice studies. Pianists naturally do this; harpsichordists taught it explicitly.

```python
class MelodicLead:
    def compute_offset(self, note: Note, ctx: AnalysisContext) -> float:
        if not ctx.voice.is_melody:
            return 0.0
        
        # Base lead: 15-25ms
        lead = 0.020
        
        # More lead at phrase starts (announcing)
        if ctx.phrase.position_in_phrase < 0.1:
            lead += 0.010
        
        # Less lead in fast passages (would sound sloppy)
        if note.duration < 0.125:  # sixteenth or faster
            lead *= 0.5
        
        return -lead  # negative = earlier
```

### 2.4 Motor Model

**Purpose**: Physical constraints of human performance

**Model**: Based on Fitts's Law and piano biomechanics research.

```python
class MotorModel:
    def compute_offset(self, note: Note, prev_note: Note, ctx: AnalysisContext) -> float:
        offset = 0.0
        
        # Large intervals take longer to execute
        interval = abs(note.midi - prev_note.midi)
        if interval > 12:  # octave+
            offset += 0.008 * (interval - 12)  # ~8ms per semitone beyond octave
        
        # Hand crossing (voice crossing in our case) adds time
        if self.is_hand_cross(note, prev_note):
            offset += 0.025
        
        # Fast repeated notes: slight acceleration (drummer's rush)
        if interval == 0 and note.duration < 0.125:
            offset -= 0.005  # 5ms early
        
        # Fatigue: gradual drift late over long passages
        # (model as 1ms per 10 notes of continuous sixteenths)
        
        return offset
```

### 2.5 Stochastic Drift

**Purpose**: Human imprecision, but correlated, not white noise

**Model**: Brownian motion with mean reversion (Ornstein-Uhlenbeck process)

```python
class StochasticDrift:
    def __init__(self):
        self.theta = 0.3      # mean reversion rate
        self.sigma = 0.008    # volatility (8ms std dev)
        self.current = 0.0
    
    def step(self, dt: float) -> float:
        """Ornstein-Uhlenbeck step"""
        noise = random.gauss(0, 1)
        self.current += self.theta * (0 - self.current) * dt + self.sigma * noise * sqrt(dt)
        
        # Clamp to reasonable range
        self.current = max(-0.030, min(0.030, self.current))
        
        return self.current
```

**Why O-U, not white noise**: Human timing errors are autocorrelated. If you're 10ms late, you're probably still ~8ms late on the next note. White noise sounds jittery; O-U sounds human.

### 2.6 Timing Combination

```python
class TimingEngine:
    def compute_onset(self, note: Note, ctx: AnalysisContext) -> float:
        base_onset = note.offset
        
        # Rubato (multiplicative, affects all subsequent notes)
        rubato_onset = self.rubato.transform_onset(base_onset, ctx.phrase)
        
        # Additive offsets
        agogic = self.agogic.compute_delay(note, ctx)
        melodic_lead = self.melodic_lead.compute_offset(note, ctx)
        motor = self.motor.compute_offset(note, self.prev_note, ctx)
        drift = self.drift.step(note.duration)
        
        final_onset = rubato_onset + agogic + melodic_lead + motor + drift
        
        return final_onset
```

---

## Module 3: Dynamics Models

### 3.1 Phrase Envelope

```python
class PhraseEnvelope:
    def compute_velocity_multiplier(self, ctx: AnalysisContext) -> float:
        pos = ctx.phrase.position_in_phrase
        
        # Bell curve peaking at 0.4 (slightly before middle)
        # mf at start, f at peak, p at end
        peak_pos = 0.4
        
        if pos < peak_pos:
            # Rising: 0.85 -> 1.15
            return 0.85 + 0.30 * (pos / peak_pos)
        else:
            # Falling: 1.15 -> 0.75
            return 1.15 - 0.40 * ((pos - peak_pos) / (1 - peak_pos))
```

### 3.2 Metric Weight

```python
class MetricDynamics:
    def compute_velocity_offset(self, ctx: AnalysisContext) -> int:
        # Map metric weight 0-1 to velocity offset -8 to +8
        weight = ctx.metric.metric_weight
        return int((weight - 0.5) * 16)
```

### 3.3 Harmonic Tension

```python
class HarmonicDynamics:
    def compute_velocity_offset(self, ctx: AnalysisContext) -> int:
        offset = 0
        
        # Dissonances louder (lean in)
        if ctx.harmonic.tension > 0.5:
            offset += int(ctx.harmonic.tension * 12)
        
        # Resolutions softer (release)
        if ctx.harmonic.is_resolution:
            offset -= 8
        
        # Appoggiaturas: louder than their resolution
        if ctx.harmonic.is_appoggiatura:
            offset += 10
        
        return offset
```

### 3.4 Contour Following

```python
class ContourDynamics:
    def compute_velocity_offset(self, note: Note, ctx: AnalysisContext) -> int:
        # Higher notes slightly louder (natural voice/finger tendency)
        # Map typical range (C4-C6) to -5 to +5
        midi = note.midi
        normalized = (midi - 60) / 24  # 0 at C4, 1 at C6
        return int(normalized * 10)
```

### 3.5 Touch Variation

```python
class TouchVariation:
    def compute_velocity_offset(self) -> int:
        # Pure randomness, but small
        return random.randint(-4, 4)
```

### 3.6 Voice Balance

```python
class VoiceBalance:
    def compute_velocity_offset(self, ctx: AnalysisContext) -> int:
        if ctx.voice.is_melody:
            return +8  # melody prominence
        if ctx.voice.is_thematic:
            return +5  # thematic material audible
        return 0
```

---

## Module 4: Articulation Model

### 4.1 Duration Modification

```python
class ArticulationEngine:
    def compute_duration(
        self, 
        note: Note, 
        ctx: AnalysisContext,
        next_note: Optional[Note]
    ) -> float:
        base = note.duration
        
        # Default: slight shortening (notes don't perfectly connect)
        factor = 0.92
        
        # Legato phrases: overlap
        if self.is_legato_context(ctx):
            factor = 1.05
        
        # Staccato markings or detached style
        if self.is_detached_context(ctx):
            factor = 0.60
        
        # Phrase endings: slight separation (breath)
        if ctx.phrase.is_phrase_boundary:
            factor *= 0.85
        
        # Long notes in slow movements: fuller duration
        if note.duration > 0.5 and ctx.tempo < 80:
            factor = max(factor, 0.98)
        
        # Fast passages: crisper articulation
        if note.duration < 0.125:
            factor = min(factor, 0.88)
        
        return base * factor
```

### 4.2 Attack Shaping

For sample-based playback, control attack velocity curve:

```python
class AttackShape:
    def compute_attack_time(self, ctx: AnalysisContext) -> float:
        """
        Returns attack time in ms for sample envelope.
        Shorter = percussive, longer = gentle.
        """
        base = 5.0  # ms
        
        # Soft dynamics: gentler attack
        if ctx.target_velocity < 60:
            base += 3.0
        
        # Phrase starts: slightly harder attack
        if ctx.phrase.position_in_phrase < 0.05:
            base -= 2.0
        
        # Appoggiaturas: lean in gently
        if ctx.harmonic.is_appoggiatura:
            base += 2.0
        
        return max(2.0, base)
```

---

## Module 5: Instrument-Specific Profiles

### 5.1 Profile Structure

```yaml
harpsichord:
    timing:
        melodic_lead: 0.018          # prominent
        agogic_strength: 0.7         # subtle agogic accent
        rubato_range: [0.95, 1.05]   # restrained
    dynamics:
        # Harpsichord has minimal dynamic range
        velocity_range: [70, 90]     # compressed
        phrase_envelope_strength: 0.3
    articulation:
        default_duration_factor: 0.88  # crisp
        legato_overlap: 1.02

piano:
    timing:
        melodic_lead: 0.022
        agogic_strength: 1.0
        rubato_range: [0.88, 1.12]   # more freedom
    dynamics:
        velocity_range: [40, 110]    # full range
        phrase_envelope_strength: 1.0
    articulation:
        default_duration_factor: 0.92
        legato_overlap: 1.08

clavichord:
    timing:
        melodic_lead: 0.015
        agogic_strength: 1.2         # very expressive
        rubato_range: [0.85, 1.15]   # intimate, flexible
    dynamics:
        velocity_range: [50, 95]     # limited but real
        phrase_envelope_strength: 1.2
    articulation:
        default_duration_factor: 0.95  # sustained
        legato_overlap: 1.10
        bebung_eligible: true        # vibrato on sustained notes
```

---

## Module 6: Style Profiles

### 6.1 Baroque

```yaml
baroque:
    rubato:
        phrase_flexibility: 0.5      # restrained
        cadence_ritardando: 0.08     # subtle
    metric:
        hierarchy_strength: 1.2      # clear metric feel
        notes_inégales: true         # optional swing on paired eighths
    articulation:
        default: detached
        slurred_groups: legato
    ornamentation:
        appoggiatura_weight: 1.3     # emphasised
        trill_acceleration: true
```

### 6.2 Notes Inégales (Optional Enhancement)

For French baroque style:

```python
class NotesInegales:
    def apply(self, notes: List[Note], ctx: AnalysisContext) -> List[Note]:
        """
        Paired eighth notes become unequal (long-short).
        Ratio typically 3:2 or 2:1 depending on tempo.
        Only on stepwise motion.
        """
        ratio = self.compute_ratio(ctx.tempo)  # e.g., 1.4:0.6
        
        for i in range(0, len(notes) - 1, 2):
            if self.is_eligible_pair(notes[i], notes[i+1]):
                total = notes[i].duration + notes[i+1].duration
                notes[i].duration = total * ratio[0]
                notes[i+1].duration = total * ratio[1]
                notes[i+1].offset = notes[i].offset + notes[i].duration
        
        return notes
```

---

## Implementation Plan

### Phase 1: Foundation (Week 1)
```
humanisation/
├── __init__.py
├── analysis/
│   ├── __init__.py
│   ├── phrase.py          # Phrase detection and context
│   ├── metric.py          # Metric hierarchy analysis
│   ├── harmonic.py        # Tension/resolution detection
│   ├── melodic.py         # Contour analysis
│   └── voice.py           # Voice role identification
├── context.py             # Combined AnalysisContext dataclass
└── tests/
    └── test_analysis.py
```

**Deliverable**: Given a .note file, produce AnalysisContext for every note.

### Phase 2: Timing Engine (Week 2)
```
humanisation/
├── timing/
│   ├── __init__.py
│   ├── rubato.py          # Phrase-level tempo curve
│   ├── agogic.py          # Micro-delays for accent
│   ├── melodic_lead.py    # Voice separation
│   ├── motor.py           # Physical constraints
│   ├── stochastic.py      # O-U drift process
│   └── engine.py          # Combined timing computation
└── tests/
    └── test_timing.py
```

**Deliverable**: Transform .note onsets to humanised onsets.

### Phase 3: Dynamics Engine (Week 3)
```
humanisation/
├── dynamics/
│   ├── __init__.py
│   ├── phrase_envelope.py
│   ├── metric.py
│   ├── harmonic.py
│   ├── contour.py
│   ├── touch.py
│   ├── balance.py
│   └── engine.py          # Combined velocity computation
└── tests/
    └── test_dynamics.py
```

**Deliverable**: Compute expressive velocity for every note.

### Phase 4: Articulation (Week 4)
```
humanisation/
├── articulation/
│   ├── __init__.py
│   ├── duration.py
│   ├── attack.py
│   └── engine.py
└── tests/
    └── test_articulation.py
```

**Deliverable**: Modify durations for expressive articulation.

### Phase 5: Profiles & Integration (Week 5)
```
humanisation/
├── profiles/
│   ├── __init__.py
│   ├── instruments.yaml
│   ├── styles.yaml
│   └── loader.py
├── engine.py              # Master HumanisationEngine
├── io/
│   ├── note_reader.py
│   ├── note_writer.py
│   └── midi_writer.py
└── cli.py                 # Command-line interface
```

**Deliverable**: `humanise input.note --style baroque --instrument harpsichord -o output.mid`

### Phase 6: Refinement (Week 6)
- A/B testing against real performances
- Parameter tuning
- Edge case handling
- Documentation

---

## Validation Strategy

### 1. Onset Deviation Analysis

Compare humanised output against recordings of professionals playing the same pieces.

```python
def compare_to_recording(humanised: List[Note], transcribed: List[Note]) -> Report:
    """
    Compute:
    - Mean onset deviation
    - Standard deviation of deviations
    - Correlation of phrase-level rubato
    - Melodic lead consistency
    """
```

### 2. Listening Tests

Blind A/B tests:
- Quantised vs humanised
- Different parameter settings
- Compare to professional recordings

### 3. Spectral Regularity

Machine detectors for mechanical timing. Our humanised output should fail to be detected as machine-generated.

---

## Parameter Tuning Interface

For iterative refinement:

```yaml
# humanisation_config.yaml
timing:
    rubato:
        enabled: true
        strength: 1.0              # multiplier on all rubato params
    agogic:
        enabled: true
        downbeat_delay: 0.015
        peak_delay: 0.025
    melodic_lead:
        enabled: true
        base_lead: 0.020
    motor:
        enabled: true
        interval_coefficient: 0.008
    stochastic:
        enabled: true
        sigma: 0.008
        theta: 0.3

dynamics:
    phrase_envelope:
        enabled: true
        peak_boost: 0.30
        end_reduction: 0.40
    # ... etc

# Allow per-piece overrides
overrides:
    freude_invention:
        timing.rubato.strength: 0.8   # more restrained for this piece
```

---

## File Format Extension

Add humanisation hints to .note:

```csv
offset,midinote,duration,track,length,bar,beat,notename,lyric,h_onset,h_velocity,h_duration
0,72,0.25,0,,1,1.0,C5,statement,-0.002,78,0.23
...
```

Or separate humanisation layer:

```csv
# freude_invention.human
original_offset,humanised_offset,humanised_velocity,humanised_duration
0,−0.002,78,0.23
0.25,0.247,72,0.24
...
```

---

## Summary

**Total new modules**: ~20 Python files
**Estimated lines**: 2,000-2,500
**External dependencies**: None required (numpy optional for O-U process)
**Integration**: Slots between .note generation and MIDI rendering

This isn't a hack. It's a proper model of musical expression—layered, parameterised, and grounded in musicological research. The professional musician won't just fail to wince; they'll wonder who played it.
