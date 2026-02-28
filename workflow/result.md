## EPI-8 — Episode endpoint navigation: Result

### Code changes

**`planner/imitative/types.py`**
- Updated `fragment_iteration` docstring: `0 for episodes (trajectory computed at render time)`.

**`planner/imitative/subject_planner.py`**
- Removed `ascending`, `ep_to_key`, `dist`, `iteration`, `upper_iteration`, `lower_iteration` from episode loop.
- All episode `VoiceAssignment` now use `fragment_iteration=0`.

**`motifs/episode_dialogue.py`**
- Added `_compute_step_schedule(start_deg, end_deg, bar_count)`: front-loaded step schedule (first `r` bars get `q+1`, rest get `q`; produces cumulative offsets).
- `generate()`: removed `ascending: bool`; added `target_upper_midi: int`, `target_lower_midi: int`, `journey: str = "stepwise"`; priors now `int` (not `int | None`). Snaps all 4 MIDI pitches to diatonic degree via `_midi_to_nearest_degree`, computes per-voice schedules, dispatches.
- `_generate_paired()`: per-voice `upper_schedule` / `lower_schedule` replace single `step`+`start_degree`. `IMITATION_DEGREE_OFFSET` removed. Voice exchange restored: soprano takes bass contour renormalized by `−lower_degrees[0]` (starts at 0 → soprano register); bass takes soprano contour directly (upper_degrees[0]=0, `start_lower_deg` provides register).
- `_generate_fallback()`: same schedule changes; `IMITATION_DEGREE_OFFSET` removed.

**`builder/phrase_writer.py`**
- Added `_compute_next_entry_pitch(role, beat_role, key, voice_range, fugue) → int | None`: dispatches SUBJECT/ANSWER/CS/STRETTO via `_fit_shift`; returns None for HOLD/FREE/EPISODE.
- EPISODE block: removed `ascending`; computes `target_upper_midi` / `target_lower_midi` by within-phrase peek-ahead, then cross-phrase via `degree_to_nearest_midi`, then static fallback.
- Updated `generate()` call: drop `ascending`, add `target_upper_midi`, `target_lower_midi`.

**`builder/entry_renderer.py`**, **`builder/thematic_renderer.py`**
- EPISODE branch and `_render_episode_fragment` marked `# DEAD CODE — episodes route through EpisodeDialogue in phrase_writer. Retained for reference. See EPI-8.`

---

### Bob's assessment

**Episode endings → next entry** (both voices, specific bars):

- Ep 2 (bars 4–10) → Ep 3 (bars 11–16): soprano A4→A4, bass C3→A2 — seamless, same soprano note.
- Ep 5 (bars 19–25) → bar 32 CS[0]: soprano G5→G5 — **perfect arrival, 0 semitones**. Bass lands C2 approaching the E-minor bass entry. Clean.
- Ep 8 (bars 34–40) → half-cadence bar 41: soprano A4→G4 (2 semitones), bass lands E2→E2 — tight.
- Ep 3 (bars 11–16) → bar 17 ANSWER: soprano ends A#4=70, entry starts C6=84 — 14-semitone gap. The engine has a static fallback here (compose.py does not propagate cross-phrase degree for episode→subject transitions), so EPI-8's schedule never fires for ep 3.
- Ep 6 (bars 26–31) → bar 32 CS[0]: soprano ends C5, entry G5 — 7 semitones.

**Voice independence**: Episode 5 (G major) — soprano ascends C5→G5 while bass navigates C2–B2 with a different contour post voice-exchange. Episode 6 — soprano holds G5 register throughout while bass descends to E2–G1 territory. Not locked parallel. ✓

**Departure→transit→arrival**: Clear arc in episodes 5 and 8, where the cross-phrase target was available or the kernel naturally converged. Episodes 2, 3, 6 show static or weakly-targeted motion — structurally correct but without committed arrival. The machine is wired correctly; the missing ingredient is compose.py passing `next_phrase_entry_degree` for episode→subject-entry phrase transitions.

**What's still wrong**:
- Bass tessitura excursions during voice exchange: G1 (bars 29–30, episode 6), A1/B1 (episode 8). These are 3–5 semitones below C2. Voice exchange pushes the bass toward the soprano's starting degree, which combines with a descending lower_schedule to temporarily dip below range.
- Tritone leaps C5↔F#4 in episode 5 (G major) — pre-existing, not EPI-8's scope.
- Parallel octaves in episodes 2, 3, 8 — structural (CEG-arpeggio kernel), not EPI-8's scope.
- Fault count: 65 → 41. Reduction of 24 faults.

---

### Chaz's diagnosis

**`_compute_next_entry_pitch` agreement with rendered first pitch**:
- Episode 5 target soprano = G5=79 (CS[0] E-minor, computed via `_fit_shift`). Rendered first note of bar 32 soprano = G5=79. Match. ✓
- Episode 3 target soprano = static fallback (compose.py did not provide `next_phrase_entry_degree` for episode phrase [3]; the next phrase [4] is a subject_entry, but `next_phrase_entry_degree` is only set for cadential or galant phrases). Confirms the 14-semitone gap at bar 17 is a compose.py plumbing gap, not an EPI-8 defect.

**Schedule totals** (episode 5 soprano verified):
- prior_upper=C5=72 in G major (tonic 67): degree 4. target=G5=79: degree 11. `total_steps=7, bar_count=7, q=1, r=0`. Schedule=[1,2,3,4,5,6,7]. Last value = 7 = end_deg − start_deg. ✓

**`fragment_iteration=0` for all episode bars**: planner episode loop simplified — all VoiceAssignments set fragment_iteration=0. ✓

**No `ascending` references** in `episode_dialogue.py`, `phrase_writer.py`, `subject_planner.py`. ✓

**Voice exchange register fix**: `pk_lower_base = lower_degrees[0]` (the register gap, typically −14 for 2-octave soprano/bass span). During exchange:
- Soprano: `[d − pk_lower_base for d in lower_degrees]` → renormalized to 0, soprano register maintained.
- Bass: `list(upper_degrees)` → upper_degrees[0]=0, `start_lower_deg` already provides bass register; no additional shift needed (adding pk_lower_base would push bass 14+ degrees too low, causing D1/C1 excursions — tested and reverted).

**Remaining acceptance-criteria gap**: "zero tessitura_excursion faults caused by episodes" — not yet met. G1/A1/B1 excursions remain in bass during voice-exchange second halves of episodes 6 and 8. Root: descending lower_schedule combined with start_lower_deg near the search floor (−7) pushes kernel degrees to −20 or below; `_place_near` resolves most but occasionally a raw MIDI lands within 6 semitones of an already-low prior, suppressing the octave correction. Next task: either raise the degree search floor, or anchor each kernel's first note to `degree_to_nearest_midi` against voice_range rather than `_place_near` against prior.

---

Please listen to the MIDI and let me know what you hear.
