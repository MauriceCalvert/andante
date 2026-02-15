### 2026-02-15: IMP-4 Episode Auto-Insertion

**Implementation**:
- Removed explicit episode parsing from `subject_planner.py` (deleted lines ~52-56, 110-165)
- Added auto-insertion logic after section assignment, before BarAssignment construction
- Helper functions: `_extract_lead_voice_and_key()` identifies thematic material and key from entries, `_semitone_distance()` computes shortest mod-12 distance for direction
- Episode insertion at section boundaries: detects `entry_section_names[i] != entry_section_names[i-1]`, skips cadences
- Episode parameters: source_key from preceding entry, direction from key distance (positive semitone = ascending → negative iterations, negative semitone = descending → positive iterations), lead_voice opposite preceding entry's lead, length fixed at 2 bars
- Augmented entry list interleaves auto-episodes with parsed entries before BarAssignment building
- Total_bars recalculated to include episode bars
- Updated `types.py:VoiceAssignment.fragment_iteration` comment: "for sequential transposition in episodes (positive = descending, negative = ascending)"

**Result**:
- Invention now has 17 bars (13 original + 4 episode bars)
- 2 episodes auto-inserted: bars 5-6 (exordium→narratio), bars 11-12 (narratio→confirmatio)
- Episode structure: entry (2) + entry (2) + episode (2) + entry (4) + episode (2) + entry (4) + cadence (1)
- Episode fragments audible: bars 5-6 show degrees 5-3-1 / 6-4-2, bars 11-12 show 5-3-1 / 6-4-2 (subject head transposed by step)
- Both episodes ascending (fragment_iteration 0, -1) matching key relationships (G→A, F→G)
- Episode lead voice alternates: both in upper after lower-led entries
- No explicit episodes in invention.yaml (all auto-derived)
- Trace shows "L6t Render: bar 5 U EPISODE G maj" and "bar 11 U EPISODE F maj"
- All acceptance criteria met

**Bob assessment**:
- Episodes sound like bridge passages using the subject's opening gesture compressed
- Fragments step upward by scale degree (sequential transposition)
- Episodes provide directed motion between key areas, not static filler
- Monophonic texture (bass silent) is acceptable for IMP-4; harmonic projection is IMP-5 scope

**Chaz verification**:
- Total bars = original 13 + auto-inserted 4 = 17 ✓
- Episodes only at section boundaries (not within sections, not before cadence) ✓
- Fragment_iteration signs correct (negative = ascending) ✓
- Lead voice alternation confirmed ✓
- No crashes, all constraints respected ✓

### 2026-02-15: IMP-3 Entry Layout (SubjectPlan → PhrasePlans)

**Implementation**:
- Created `planner/imitative/entry_layout.py` with `build_imitative_plans()` to convert SubjectPlan into PhrasePlans
- Groups consecutive BarAssignments by (function, voice_roles) to identify entries
- Builds BeatRole tuples for imitative material (SUBJECT, ANSWER, CS, FREE)
- Populates cadence PhrasePlans from cadenza_composta schema
- Wired into `planner.py` lines 141-206: imitative branch now bypasses galant L3/L4/L5 entirely
- Fixed `compose.py` cross-phrase guard (lines 156-158) to handle empty degrees_upper/degree_keys
- Fixed `planner.py` line 379 to load fugue even when key is None (for library subjects)

**Result**:
- Invention now renders from SubjectPlan with recognizable subject/answer/CS entries
- Monophonic opening (bars 1-2): soprano only, bass silent
- Terminal cadence (bar 13): cadenza_composta resolves properly
- Trace shows L1 → L2 → L3 Imitative → L5 → L6t (galant layers bypassed)
- All 8 genres pass: invention 64+52 notes, galant genres unchanged
- No crashes from empty degree arrays

**Known limitations** (deferred to IMP-4/5/6):
- No harmonic grid (FREE voices use scale-only Viterbi)
- No intermediate cadences
- No episodes
- Cadence type hardcoded to cadenza_composta

### 2026-02-15: IMP-4 Episode Entries

**Implementation**:
- Extended invention.yaml entry_sequence format to support episode entries: `{type: episode, bars: N, lead_voice: upper/lower, fragment: head}`
- Updated `planner/imitative/subject_planner.py` to parse episode entries and create BarAssignments with incrementing fragment_iteration (0, 1, 2, ...) for sequential descent
- Removed "episode" from _UNSUPPORTED_ROLES
- Added EPISODE to _ROLE_MAP and _MATERIAL_MAP in `planner/imitative/entry_layout.py`
- Updated `scripts/yaml_validator.py` to validate episode entry structure
- Fixed bug in `builder/phrase_writer.py` EPISODE dispatch: now loops over all episode bars instead of rendering only the first bar
- invention.yaml now has 2 episodes (4-bar + 3-bar) between entries

**Result**:
- Invention expanded from 13 bars to 20 bars (12 entry + 7 episode + 1 cadence)
- Episodes show clear descending sequence of subject head fragment (G-E-C → F-D-B → E-C-A → D-B-G)
- Episode 1 (bars 5-8): bass leads with head descending by step
- Episode 2 (bars 13-15): soprano leads with head descending by step
- _render_episode_fragment (existing code) correctly transposes fragment degrees down by fragment_iteration steps
- Piece arc improved: Exposition + Episode → Development + Episode → Recapitulation + Cadence
- Episodes create directed motion between entries instead of sounding like random fill
- All 8 genres pass; invention now 73+64 notes

**Known limitations** (acknowledged in IMP-4 spec):
- Only head fragment supported (tail fragments in IMP-5a)
- Only descending by step (ascending/circle-of-fifths in IMP-5a)
- Episode companion is always FREE (double episodes in IMP-5a)
- No harmonic grid for episodes (cross-relation risk)


### 2026-02-15: IMP-5a.1 Pedal Point + Double Episodes

**Implementation**:
- **Pedal point**: Added {type: pedal, degree: 5, bars: 2} entry before cadence in invention.yaml
- **subject_planner.py**: Removed "pedal" from _UNSUPPORTED_ROLES; added pedal entry handling (lines 263-294) creating BarAssignments with function="pedal", voice 1 role="pedal" fragment=str(degree), voice 0 role="free"; updated auto-episode boundary check to skip pedal entries (lines 127-140)
- **Double episodes**: Changed auto-episode companion voice from role="free" to role="episode" fragment="tail" with same fragment_iteration as lead (line 243)
- **entry_layout.py**: Added "pedal": ThematicRole.PEDAL to _ROLE_MAP, "pedal": None to _MATERIAL_MAP; override material for episode (read from fragment: "head"/"tail") and pedal (read degree string from fragment) in _build_thematic_roles (lines 263-267)
- **thematic_renderer.py**: Dispatch on role.material in _render_episode_fragment (lines 142-153); if material=="tail" call extract_tail, if material=="head" call extract_head; return empty tuple for empty tail fragments
- **phrase_writer.py**: Added _has_pedal helper (line 566); added _write_pedal function (lines 569-666) creating held bass notes (one per bar, duration=bar_length) and Viterbi soprano with minimal structural anchors (degrees 1,1 at start/end); inserted pedal dispatch at Path 1.5 before thematic check (lines 720-725); added trace output for pedal rendering
- **yaml_validator.py**: Added pedal entry validation (lines 1177-1186) checking degree (int 1-7) and bars (int > 0)

**Result**:
- Invention now has 19 bars (17 previous + 2 pedal = 13 original + 4 episodes + 2 pedal)
- Pedal audible: bars 17-18 bass holds G3 (degree 5, dominant) for 2 bars, soprano moves freely above (8 notes E5..C6)
- Double episodes: bars 5-6 and 11-12 show EPISODE in both U and L voices (head in one voice, tail in other)
- Episode texture: head fragment = 6 notes (1 bar of subject), tail fragment = 14 notes (remaining bar) — both transpose together (same fragment_iteration)
- Trace shows "L6t Render: bar 17 L PEDAL C maj -> 2 notes G3..G3" and "bar 17 U FREE -> 8 notes E5..C6"
- Trace shows double episodes: "bar 5 U EPISODE G maj -> 6 notes" + "bar 5 L EPISODE G maj -> 14 notes"
- All 8 genres pass with no crashes (galant regression clean)

**Bob assessment**:
- Pedal creates tension before cadence: held dominant + soprano dissonances (C6/G3 unprepared 4th/11th) create expectation, bar 19 cadence resolves to tonic — exhale after held breath
- Double episodes sound busier than IMP-4 monophonic episodes: both voices carry recognizable subject fragments stepping together in quasi-canonic texture, not melody-over-aimless-accompaniment
- Episode tail busier than head (14 notes vs 6) due to subject's back-loaded rhythm — creates asymmetric texture but not wrong
- Pedal dissonances are correct but bland (consonant scale tones vs characteristic 4ths/7ths/9ths) — acceptable per Known Limitation #1 (no harmonic grid for pedal bars)
- Cross-relations in episodes (A#4 vs A3 at bars 10-11) from independent head/tail transposition — acceptable per Known Limitation #4 (no counterpoint check between fragments)

**Chaz verification**:
- Pedal dissonances: code location phrase_writer.py:631 (harmonic_grid=None) → scale-only Viterbi picks consonances; minimal fix is future work (add harmonic grid for pedal with deliberate dissonance targets)
- Cross-relations: code location subject_planner.py:232-249 (same fragment_iteration for both voices) → no vertical interval check; minimal fix is future work (add chromatic compatibility check)
- Empty tail fallback implemented (thematic_renderer.py:153 returns empty tuple) but not tested in this run (subject is 2 bars, has non-empty tail)
- All acceptance criteria met: pedal audible, double episodes in trace, tail fallback implemented, galant regression clean, bar count correct (19)


## 2026-02-15: IMP-5a.2 — Stretto

**Feature:** Added stretto (close canon) to imitative genres. Stretto allows both voices to state the subject simultaneously with the follower entering N beats after the leader, creating compression and urgency before cadences.

**Implementation:**
1. **invention.yaml**: Replaced last entry before pedal with `{type: stretto, key: I, delay: 2}`
2. **subject_planner.py**:  
   - Removed "stretto" from `_UNSUPPORTED_ROLES`  
   - Added stretto entry handler: voice 0 gets `role="subject"`, voice 1 gets `role="stretto"` with delay encoded in `fragment`  
   - Updated auto-episode boundary check to skip stretto entries (like pedal)
3. **entry_layout.py**: Added `"stretto": ThematicRole.STRETTO` to `_ROLE_MAP` and `"stretto": "subject"` to `_MATERIAL_MAP`; override material from VoiceAssignment.fragment
4. **phrase_writer.py**:  
   - Added `ThematicRole.STRETTO` to `_has_material()` and material_entries filter  
   - Added STRETTO rendering handlers for voice 0 and voice 1: parse delay, compute delay_offset, call `subject_to_voice_notes()` with delayed start, apply time window, label first note, trace render
5. **yaml_validator.py**: Added stretto entry validation (requires `key` string and `delay` int > 0)

**Musical result (Bob):**  
Bars 15-16 show audible stretto: soprano plays subject, bass enters 2 beats later with same subject. Both voices overlap, creating compression before the pedal (bar 17-18). No jarring vertical clashes. Follower truncated at phrase end (9 notes vs 10), which is idiomatic. Stretto → pedal → cadence creates escalating rhetorical arc.

**Technical verification (Chaz):**  
Trace confirms SUBJECT (10 notes) + STRETTO (9 notes) at bar 15. Bar count unchanged (19 bars). Galant regression clean: all 8 genres pass. Delay offset correctly computed (2 beats = 0.5 whole notes in 4/4). Time-window truncation working as specified.

**Known limitations (per task.md):**  
No vertical interval check between overlapping subjects (future: invertible counterpoint analysis). No harmonic grid for stretto bars (both voices fixed material). Only one delay value per stretto (future: augmentation stretto). Follower truncated at phrase end (acceptable, idiomatic).

**Files changed:**  
- data/genres/invention.yaml  
- planner/imitative/subject_planner.py  
- planner/imitative/entry_layout.py  
- builder/phrase_writer.py  
- scripts/yaml_validator.py


### 2026-02-15: IMP-6 Cadence Reform (Imitative Path)

**Implementation**:
- Expanded `cadenza_composta` 4/4 template from 1 bar to 2 bars in `data/cadence_templates/templates.yaml`
- Soprano degrees [4,3,2,1] now use uniform half-note durations ["1/2","1/2","1/2","1/2"] (was rushed ["1/8","1/8","1/4","1/2"])
- Bass degrees changed from [5,1] to [5,5,5,1] with half-note durations to hold dominant for 3 half notes before tonic resolution
- Changed `CADENCE_BARS` constant from 1 to 2 in `shared/constants.py`

**Musical Structure**:
- Bar 1 (preparation): Soprano 4→3 over bass degree 5 held (dominant pedal with suspension)
- Bar 2 (resolution): Soprano 2→1, bass 5→1 (both voices resolve to tonic)
- Rhythmic broadening: all half notes (vs. surrounding semiquaver motion) signals structural close

**Result**:
- Invention total bars: 20 (was 19)
- Cadence spans bars 19-20 (trace verified)
- Bass holds dominant (A2) for three half notes, resolves to tonic (D3) on bar 20 beat 3
- All 8 genres pass pipeline tests without crashes
- Proper Baroque instrumental cadence: preparation → resolution (no more hasty recitative-style compression)

**Bob assessment**:
- ✅ Preparation bar audible (dominant hold + soprano 4→3 suspension)
- ✅ Descent unhurried (all half notes)
- ✅ Piece ends properly (rhythmic broadening signals structural boundary)

**Chaz verification**:
- ✅ Total bars = 20 (was 19)
- ✅ Soprano: 4 notes, all half-note duration
- ✅ Bass: 4 notes (3×degree-5, 1×degree-1), all half-note duration
- ✅ Bass resolves V→I in final bar (not held tonic)

**Scope**:
- Only cadenza_composta 4/4 modified (other cadence types and metres unchanged)
- Galant path unaffected (uses schema bar allocation, not CADENCE_BARS)
- CADENCE_BARS only used in `subject_planner.py` for bar cost calculation

