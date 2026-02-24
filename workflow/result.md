## Result: F4 — Canonic Episode Texture

### Changes Made

File modified: `motifs/fragen.py`

**Change 1 — Constants:**
- Deleted `_FOLLOWER_OFFSETS` (sub-beat offsets 0, 1/8, 1/4) and `_RHYTHMIC_CONTRAST` (2x ratio filter).
- Added `_CANONIC_STAGGERS = (Fraction(1,4), Fraction(1,2))` — 1 or 2 crotchet beats.
- Removed dead code: `_avg_duration` function, `product` import.

**Change 2 — `build_fragments`:**
- Replaced cross-pairing (`product(cells, repeat=2)` with rhythmic contrast filter) with canonic pairing: each cell paired with itself (parallel canon) and with its inversion (contrary motion).
- Loops over `_CANONIC_STAGGERS` instead of `_FOLLOWER_OFFSETS`.
- Passes `leader_voice` to `_consonance_score`.

**Change 3 — `_consonance_score`:**
- Added `leader_voice: int = VOICE_SOPRANO` parameter.
- Fixed `model_dur`: when bass leads, `model_dur = max(lower.total_duration, upper.total_duration + offset)`.
- Fixed t-loop: when bass leads, lower is checked at `t` (leader time) and upper at `t - offset` (follower time). Boundary checks respect the leader/follower roles.

**Change 4 — `_emit_notes`:**
- Fixed offset logic: leader enters at `beat_disp`, follower enters at `beat_disp + fragment.offset`. Previously when leader was bass, the bass was delayed by `offset` (backwards).
- Fixed `realise` model_dur: both leader_end and follower_end now include `disp` consistently.

**Change 5 — Signature and dedup:**
- `_fragment_signature` now returns 5-tuple including `is_contrary` flag (upper.source != lower.source).
- `dedup_fragments` key now includes `f.offset` (stagger) and `is_contrary` flag, so same cell with different staggers/canon types are preserved as distinct.

### Pipeline Checkpoint

Ran invention pipeline (seed 42, fugueA subject). Three episodes generated (bars 7-8, 13-14, 24-25).

**Bob:**
- Episode 2 (bars 13-14) achieves the target: overlapping canon with 1-beat stagger, contrary motion (bass ascending, soprano descending), recognisable motivic cell in both voices.
- Episodes 1 and 3 use 1/2-bar stagger with 1/2-bar cell = antiphonal alternation (valid per Known Limitation 3 but less rich).
- Gap-fill extends notes at iteration boundaries (Known Limitation 4).
- All episodes show staggered onsets — no simultaneous chorale-like attacks.

**Chaz:**
- Antiphonal texture occurs when cell_duration == stagger. Not a bug — both are valid episode textures per task spec Known Limitation 3.
- Gap-fill behaviour is pre-existing and acceptable per Known Limitation 4.
- Episode length (2 bars) determined upstream by entry_layout, out of scope.

### Acceptance Criteria

- [x] Episode bars show staggered onsets (follower enters 1 or 2 beats after leader)
- [x] Both voices carry the same rhythmic profile (same cell durations)
- [x] At least one episode uses contrary motion (Episode 2: inverted cell in follower)
- [x] No voice crossing, no parallel perfects, no cross-relations in episodes
- [x] Pipeline runs successfully

### Note

The invention.yaml `subject: subject00_2bar` references a missing library file. Temporarily used `fugueA` for testing, then reverted. The missing subject is a pre-existing issue.
