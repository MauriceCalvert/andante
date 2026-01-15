# Andante Roadmap

## Version History

| Version | Status | Theme |
|---------|--------|-------|
| v1 | Complete (Jan 2025) | Core pipeline, treatments, guards |
| v2 | Complete (Jan 2025) | Genre expansion, dance forms |
| v3 | Complete (Jan 2025) | Motivic variety, counter-subject |
| v4 | Complete (Jan 2026) | Harmonic schemas, repetition elimination |
| v5 | Complete (Jan 2026) | Figured bass, walking bass, hemiola |
| v6 | Complete (Jan 2026) | N-voice architecture, CP-SAT solving |
| v7 | In progress | Planner dramaturgy, coherence |

---

## Current: v7 Planner Enhancement

### 7-Stage Pipeline

The planner now runs seven stages:
1. **Frame** - key, mode, metre, tempo, voices, form
2. **Dramaturgy** - archetype, rhetoric, tension curve
3. **Material** - subject generation/loading, counter-subject
4. **Structure** - sections, episodes, phrases
5. **Harmony** - key scheme, cadence targets
6. **Devices** - Figurenlehre device placement
7. **Coherence** - callbacks, surprises, proportions

**Status**: Basic implementation complete. Testing needed.

### Subject Generation

The `motifs/` module provides research-backed subject generation:
- Head + tail construction based on music cognition research
- 43 melodic cells for tail generation
- Figurae (baroque rhetorical figures) scoring
- 40+ melodic feature extractors

**Status**: Complete.

---

## Completed: v6 N-Voice Architecture

### Implementation Complete

| Component | File | Status |
|-----------|------|--------|
| Voice infrastructure | `engine/voice_config.py` | ✓ |
| Material types | `engine/voice_material.py` | ✓ |
| Phrase voice entries | `engine/voice_entry.py` | ✓ |
| N-voice expansion | `engine/n_voice_expander.py` | ✓ |
| Branch-and-bound | `engine/inner_voice.py` | ✓ |
| CP-SAT solver | `engine/cpsat_slice_solver.py` | ✓ |
| Harmonic context | `engine/harmonic_context.py` | ✓ |
| Voice pair checking | `engine/voice_pair.py` | ✓ |
| Voice-leading checks | `engine/voice_checks.py` | ✓ |
| Vertical slices | `engine/subdivision.py` | ✓ |

### Architecture

1. Outer voices (soprano, bass) expanded using 2-voice pipeline
2. Inner voices solved via CP-SAT with branch-and-bound fallback
3. Harmonic context inferred from outer voices for chord-tone candidates
4. All voice pairs checked for parallel fifths/octaves

---

## Completed: v5 Bass-Driven Harmony

| Feature | File | Status |
|---------|------|--------|
| Figured bass | `engine/figured_bass.py` | ✓ |
| Walking bass | `engine/walking_bass.py` | ✓ |
| Hemiola | `engine/hemiola.py` | ✓ |
| Passage patterns | `engine/passage.py` | ✓ |
| Cadenza | `engine/cadenza.py` | ✓ |

---

## Deferred Items

### Future Genres

| Genre | Complexity | Notes |
|-------|------------|-------|
| Prelude | Medium | Free, arpeggiated |
| Fugue | High | Subject/answer/countersubject |
| Capriccio | Medium | Virtuosic, violin-idiomatic |

### Instrument Support

- [ ] Instrument parameter in Brief (forces: violin)
- [ ] Realiser reads instrument YAML for range constraints
- [ ] capriccio.yaml genre

Violin constraints documented in Tier4_Reference/violin.md

### Constraint Expressiveness

- [ ] Weighted preferences for soft constraints
- [ ] Conditional rules (`if: soprano_leaps` / `then: bass_steps`)

### Deeper Backtracking

- [ ] Full phrase re-realisation with octave choices
- [ ] Record choice points in realise_voice
- [ ] Cross-phrase boundary guards

---

## Testing

### Current Status

- ~2575 tests passing
- 10 exercises generate successfully
- No blocker guard violations

### Test Progression

10-level test suite from minuet to toccata defined in Tier4_Reference/test_progression.md:

| Level | Genre | Bars | Complexity |
|-------|-------|------|------------|
| 1 | Minuet | 16 | Anna Magdalena |
| 2 | Gavotte | 24 | March |
| 3 | Bourrée | 24 | Minor mode |
| 4-6 | Invention | 24-40 | Simple to imitative |
| 7-8 | Fantasia | 60-90 | Sections, texture |
| 9-10 | Toccata | 120-150 | Virtuosic |

---

## Resolved Decisions

| Decision | Resolution |
|----------|------------|
| Degree arithmetic | Unbounded integers internally; validate at E1/E6 |
| Roman numerals | Functions in home key, not modulations |
| Voice crossing | Allowed; Bach crosses freely |
| Guard brittleness | Piece-level defaults; missing = warning |
| Backtracking scope | Per-phrase |
| Voice check timing | Phrase end, not continuous |
| Inner voice solving | CP-SAT primary, branch-and-bound fallback |
| Counter-subject | CP-SAT solver with invertibility constraints |

---

*Last updated: 2026-01-14*
