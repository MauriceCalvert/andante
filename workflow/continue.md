# Continue — Semitone stretto + cache + opening snap (2026-02-19)

## What happened this session

### 1. Stretto evaluation moved to semitone space

Root cause: `stretto_constraints.py` tested consonance in mod-7 degree space.
Mod-7 cannot distinguish perfect fifth from diminished fifth, or perfect fourth
from tritone.  Result: every subject failed stretto at every offset.

Fix: rewrote `evaluate_offset` and `evaluate_all_offsets` to accept MIDI pitches.
All consonance checks now use semitone intervals (mod 12), reusing existing
constants from `shared/constants.py`:
- Strong beats: `CONSONANT_INTERVALS_ABOVE_BASS` (P4 excluded)
- Weak beats: `CONSONANT_INTERVALS` (P4 included as passing consonance)
- Weak-beat fatal: only `TRITONE_SEMITONES = 6`

API change: `degrees=` parameter → `midi=` parameter on `evaluate_offset` and
`evaluate_all_offsets`.  Callers in `subject_generator.py` updated.

### 2. Stretto offsets restricted to leader note onsets

Follower must enter when leader is articulating, not mid-held-note.
Changed `evaluate_all_offsets` to iterate over leader note onsets only
(from `_note_onsets(dur_slots)`) instead of every slot from 1 to half.

### 3. Duration scorer: opening snap

8/10 subjects started with a minim because `s_contrast` (weight 0.40) rewarded
long-first patterns.  Added `s_opening` component: penalises first note > crotchet
(halves that sub-score).  Rebalanced weights: entropy 0.10, contrast 0.30,
coherence 0.20, final 0.20, opening 0.20.

### 4. Enumeration cache

Added disk cache (`.cache/subject/`) for scored pitch and duration sequences.
Cache stores ALL scored sequences sorted descending, not just top-K.  TOP_K_PITCH
and TOP_K_DURATIONS removed — the full cross-product runs against the complete
cache.  TOP_K_PAIRED (100) remains as stretto evaluation shortlist.

First run builds cache (~35s).  Subsequent runs load from pickle — enumeration
and scoring are instant.

**Cache invalidation:** delete `.cache/subject/` whenever scoring functions or
enumeration constraints change.  Files: `pitch_scored_{n}n.pkl`,
`dur_scored_{n}b_{t}t.pkl`.

### Files changed
- `motifs/stretto_constraints.py` — full rewrite (semitone space, StrettoCheck,
  onset-only offsets)
- `motifs/subject_generator.py` — cache layer, opening snap scorer, removed
  TOP_K_PITCH/TOP_K_DURATIONS, API updates for midi= parameter
- `shared/constants.py` — added FOURTH_MOD7 (renamed from TRITONE_MOD7),
  added 5th to CONSONANT_MOD7 (these mod-7 constants no longer used by stretto)
- `.gitignore` — added `.cache/`
- `test_stretto_diag.py` — rewritten for semitone diagnostics

### Verification
`python -m motifs.subject_generator --bars 2 --seed 0 -v`:
10-note valley subject, 2 viable stretto offsets at real note onsets, score 0.77.
Seeds 0–3 all produced subjects with 2–8 stretto offsets, some with semiquavers.

### What needs attention next
1. **Full cross-product timing** — currently running uncapped (all pitch × all
   durations per note count).  10n = 1.1M × ~300 = 330M pairings.  May need
   capping if too slow, but try first.
2. **Downstream impact** — verify thematic_renderer, imitation, answer/CS
   generators handle semiquaver durations.  Initial writers test showed "cool
   counterpoint" so pipeline is functional.
3. **Shape scorer tuning** — top shape scores had 65% melodic validation rate.
   Could improve by moving melodic checks into the recursion.
4. **Speed after cache** — second run should be <1s for enumeration.  Pairing
   loop is the remaining cost.
