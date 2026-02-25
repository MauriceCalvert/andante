# Three-Voice Fugue — Scoping Analysis

## What exists

The imitative pipeline (subject → answer → CS → episode → stretto → pedal
→ cadence) is working for two-voice invention. The infrastructure assumes
two voices throughout:

- `entry_layout.py`: VoiceAssignment keyed by voice index {0, 1}
- `subject_planner.py`: walks `upper`/`lower` keys in entry_sequence dicts
- `thematic_renderer.py`: dispatches upper/lower
- `phrase_writer.py`: builds two-voice PhraseResult
- `compose.py`: assembles two voices
- `fragen.py`: builds fragments for two-voice episodes
- Viterbi: pairwise costs between two voices
- MIDI/MusicXML writers: two tracks
- `.note` CSV: two voice columns
- VOICE_RANGES: indices 0–3 exist but only 0 and 3 are used

## What a three-voice fugue requires

### 1. The middle voice (alto or tenor)

A fugue in C major for keyboard: soprano (RH upper), alto (RH lower /
LH upper), bass (LH lower). Voice ranges already defined:
- Soprano: 55–84 (index 0)
- Alto: 50–74 (index 1)  
- Tenor: 45–69 (index 2)

For a three-voice keyboard fugue, the natural mapping is soprano (0),
alto (1), bass (3). Tenor (2) is the alternative if the subject sits
lower.

### 2. Exposition structure

Standard three-voice fugue exposition:
```
Bar 1:  Voice 1 — Subject (I)
Bar 3:  Voice 2 — Answer (V),  Voice 1 — CS1
Bar 5:  Voice 3 — Subject (I), Voice 2 — CS1 (or CS2), Voice 1 — free/CS2
```

Third entry is the architectural novelty. When voice 3 enters with the
subject, voices 1 and 2 must both be doing something. This means:
- The entry_sequence YAML needs a third voice key
- subject_planner must handle three voice assignments per bar
- entry_layout must produce three-voice BarAssignments
- phrase_writer must compose three voices per phrase

### 3. Three-voice counterpoint

The Viterbi engine currently computes pairwise costs against ONE
companion voice. With three voices, any generated voice must be
consonant with TWO companions. Options:

**A. Pairwise sum.** Run existing pairwise cost against each companion,
sum the costs. Simple, preserves current cost functions. Misses
three-voice interactions (e.g., voice-crossing between alto and bass
is fine pairwise but sounds wrong in context).

**B. Multi-voice cost function.** New cost that takes all sounding
voices as input. More correct but a larger change.

Recommendation: **A first, B later.** Pairwise sum gets us running.
The main three-voice fault it misses is spacing — but we already have
graduated spacing costs that can be applied per pair.

### 4. What changes, module by module

#### Planner layer
- `subject_planner.py`: parse three-voice entry_sequence; assign
  roles to three voices per bar
- `types.py`: no change needed — VoiceAssignment dict already keyed
  by int, just needs three entries
- `entry_layout.py`: build PhrasePlans with three voices; voice
  ranges for soprano/alto/bass

#### Builder layer
- `phrase_writer.py`: three-voice dispatch — thematic for subject
  carriers, Viterbi for free voices. Order: subject voice fixed,
  then generate remaining voices against it
- `thematic_renderer.py`: render subject/answer/CS into any of
  three voices (not just upper/lower)
- `compose.py`: assemble three voices
- `soprano_viterbi.py` / `bass_viterbi.py`: need to accept a list
  of companion voices, not just one
- `fragen.py`: three-voice episodes — leader + two followers, or
  two-voice fragment + held note in third voice

#### Viterbi layer
- `costs.py`: pairwise cost summed over multiple companions
- `generate.py`: pass multiple companion note sequences
- `corridors.py`: range corridors for alto voice

#### Output layer
- `midi_writer.py`: three tracks
- `musicxml_writer.py`: three parts (or two staves with voice
  splitting for keyboard)
- `note_writer.py`: three voice columns
- `faults.py`: check all three voice pairs

#### Data layer
- `data/genres/fugue.yaml`: new genre config with three voices,
  entry_sequence, subject definition
- `shared/constants.py`: possibly new voice-pair constants

### 5. Execution phases

Rough phasing — each phase is a self-contained brief:

**Phase F0 — Genre scaffold.**
Create `fugue.yaml` with three voices, exposition entry_sequence,
one development cycle, stretto, pedal, cadence. No code changes —
just the data file. Run pipeline to see what breaks.

**Phase F1 — Three-voice planner.**
Extend `subject_planner.py` and `entry_layout.py` to handle three
voice keys per entry. Output: SubjectPlan with three-voice
BarAssignments.

**Phase F2 — Three-voice rendering.**
Extend `phrase_writer.py` to compose three voices. First pass:
subject/answer/CS voices rendered thematically, third voice gets
Viterbi free counterpoint against the other two (pairwise sum).

**Phase F3 — Viterbi multi-companion.**
Extend Viterbi cost pipeline to accept N companion voices. Pairwise
cost summed. Test on three-voice texture.

**Phase F4 — Three-voice episodes.**
Extend fragen to produce three-voice episode textures. Options:
two-voice imitation + held note, or three-voice sequential fragments.

**Phase F5 — Three-voice cadences.**
Extend cadence_writer for three-voice clausulae (cantizans, tenorizans,
basizans).

**Phase F6 — Output.**
Three-track MIDI, three-part MusicXML, three-voice .note CSV.

**Phase F7 — Listening and iteration.**
Same improve cycle as invention: listen, assess, brief fixes.

### 6. Risk assessment

**Main risk: phrase_writer complexity.** Currently it has three
dispatch paths (cadential, thematic, schematic). Adding a third voice
multiplies the combinations. Mitigation: in a fugue, every bar has a
clear thematic assignment for each voice. The dispatch is simpler than
galant because the subject plan dictates everything.

**Secondary risk: Viterbi beam width.** Three-voice pairwise costs
are more constraining — the beam may need widening further. Already
increased from 300 to 500 for I2; may need 800+.

**Low risk: voice crossing.** Alto and soprano ranges overlap (50–74
vs 55–84). The spacing cost should handle this, but may need a
voice-crossing penalty specific to adjacent voices.

### 7. Subject choice

The invention subject (call_response) is designed for two voices.
A fugue subject should be:
- 2 bars long (4/4) — same as invention
- Narrow range (octave or less) — so it fits soprano, alto, and bass
- Clear head motive — for episode fragmentation
- Tonal, not real answer — dominant answer with mutation at the fourth

BWV 846 (C major prelude/fugue, WTC I) has a good pedagogical subject.
Or generate a new one. Separate decision.

### 8. What stays the same

- Key system, pitch types, duration system
- Viterbi pathfinder algorithm (just more companions)
- Fragen architecture (just more voice combinations)
- Cadence template system (just more voices per template)
- Fault checking logic (just more voice pairs)
- CLI, tracing, configuration loading
