# Result: Plans 5, 6, 7

## Status: COMPLETE

---

## Plan 5 — Phrase Boundary Register Smoothing

### Phase 5.1: Audit
Boundary audit across minuet and gavotte (scripts/boundary_audit.py):
- Soprano avg boundary interval: 2.2st (both genres)
- Bass avg boundary interval: 3.8-3.9st
- Soprano >5th: 0/13 (minuet), 1/15 (gavotte, 10st)
- Bass >5th: 0/13 (minuet), 1/15 (gavotte, 10st)
- No simultaneous large leaps in either genre

### Phase 5.2–5.3: Already addressed
`degree_to_nearest_midi` with `target_midi=prev_exit_midi` already provides proximity-based octave selection. The soprano_writer threads `prev_exit_midi` across phrases. The audit confirms this works: boundaries are smooth. No code changes needed.

---

## Plan 6 — Motivic Return

### Phase 6.1: Head motif capture
Added `HeadMotif` dataclass to `builder/phrase_types.py`. After first non-cadential phrase, `_extract_head_motif` in `compose.py` captures interval_sequence, duration_sequence, and figure_name from the soprano's first figuration span.

### Phase 6.2: Recall in figuration selection
`select_figure` in `builder/figuration/selection.py` accepts `recall_figure_name`. When set, searches the figure pool for a matching figure by name and returns it immediately if found. Parameter threads through `figurate_soprano_span` → `generate_soprano_phrase` → `write_phrase`.

### Phase 6.3: Placement policy
`_mark_recall_phrases` in `builder/phrase_planner.py` marks:
- First non-cadential phrase of section B
- Last non-cadential phrase before the final cadence

Verified: minuet marks plans 3 (monte) and 5 (passo_indietro); gavotte marks plans 3 (fonte) and 6 (passo_indietro).

### Modified files
- `builder/phrase_types.py`: HeadMotif dataclass, recall_motif field
- `builder/compose.py`: _extract_head_motif, recall_figure threading
- `builder/phrase_planner.py`: _mark_recall_phrases
- `builder/figuration/selection.py`: recall_figure_name parameter
- `builder/figuration/soprano.py`: recall_figure_name parameter
- `builder/soprano_writer.py`: recall_figure_name parameter
- `builder/phrase_writer.py`: recall_figure_name parameter

---

## Plan 7 — Additional Genre Validation

### Bug fix: Bass routing for continuo_walking
`builder/bass_writer.py` line 1384: `continuo_walking` pattern was excluded from pattern bass but fell through to pillar bass instead of walking bass. Fixed routing so `continuo_walking` explicitly routes to `_generate_walking_bass`. Bourree bass went from 58 notes (pillar) to 75 notes (walking).

### Phase 7.4: Genre Comparison Table

| Genre | Metre | Tempo | Notes (S+B) | Completes? | Faults | Genre character? | Key gaps |
|-------|-------|-------|-------------|------------|--------|-----------------|----------|
| Minuet | 3/4 | 115 | 49+62 | Yes | 0 | **Yes** — pattern bass bounce, ternary rhythm | — |
| Gavotte | 4/4 | 71 | 66+49 | Yes | 0 | **Yes** — half-bar bass, upbeat, moderate pace | — |
| Sarabande | 3/4 | 63 | 43+22 | Yes | 2 (cross-rel) | **Partial** — sustained bass correct; no beat-2 weight | Cross-relations at key boundaries; beat-2 emphasis not expressed |
| Bourree | 4/4 | 95 | 57+58 | Yes | 0 | **Yes** — walking bass correct, upbeat correct, brisk | Soprano descends monotonically |
| Invention | 4/4 | 105 | 64+57 | Yes | 0 | **Partial** — 4-section structure works, bass active | No imitation; lead_voice not wired |

### Sarabande assessment
- Sustained bass (1 note per bar, 3/4 duration) — correct
- Soprano ornamental with broken thirds, circolo, tirata figures
- 2 cross-relations at key boundaries (D minor ↔ F major)
- Beat-2 emphasis not audible from .note data (rhythm cells don't differentiate)
- Character: stately and spare, recognisable as sarabande from bass texture

### Bourree assessment
- Walking bass works correctly after routing fix (continuo_walking → walking bass branch)
- Upbeat (1/4 at beat 4) placed correctly at offset -0.25
- 0 faults — walking bass parallel-avoidance catches all issues
- Soprano descends from C5 to C4 without compensating ascent
- Character: brisk tempo, walking bass gives stepwise motion, proper dance feel

### Invention assessment
- 4-section through-composed form (exordium/narratio/confirmatio/peroratio) works
- Walking bass in exordium/narratio/confirmatio, chordal in peroratio (from section config)
- Romanesca climax hits C6, then descent to C4 at peroratio
- 0 faults
- No imitative dialogue (lead_voice not wired, IMITATIVE role not implemented)
- Character: continuous argument structure present, but voices are independent rather than conversational

### Key findings
1. All 5 genres complete without crashes, 0 faults (except sarabande cross-relations)
2. No regressions from Plans 5-6 — all 3752 tests pass
3. Cross-relations at minor-key boundaries need attention (sarabande)
4. Invention needs imitative counterpoint for genre identity (major feature)
5. Bourree/gavotte/minuet have audible genre character; sarabande/invention are partial
