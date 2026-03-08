# Result: Technique 2 — Parallel-sixths episode texture

## Code changes

**`builder/episode_dialogue.py`**
- Added import: `VOICE_RANGES` from `shared.constants`
- Added module-level constants: `PARALLEL_SIXTH_OFFSET = -5`, `PARALLEL_TENTH_OFFSET = -9`,
  `_SOPRANO_RANGE = Range(*VOICE_RANGES[TRACK_SOPRANO])`
- Added method `_generate_parallel` (between `_generate_paired` and `_generate_fallback`):
  per bar: computes `upper_base = start_upper_deg + upper_schedule[i]`,
  derives `lower_base = upper_base + PARALLEL_SIXTH_OFFSET`, applies
  `_apply_consonance_check`, range-checks lower MIDI values, falls back to
  `PARALLEL_TENTH_OFFSET` if any note exceeds `lower_range`, emits both
  voices with `_emit_paired_voice_notes` at identical onsets.

**`builder/techniques.py`**
- Replaced `technique_2` stub body: removed `_log.warning`, now calls
  `dialogue._generate_parallel(...)` with `bar_count`, `start_offset`,
  `tonic_midi`, `mode`, `start_upper_deg`, `upper_schedule`, `lower_range`.

---

## Bob's assessment

Bars 1-3 are familiar: subject entry alone, then answer enters below while the
upper voice weaves a countersubject above. Two voices speaking in turn, chasing.

Bar 4 is immediately different. Both voices lock together at beat 1, no delay.
They descend together -- four quick steps, then three long notes landing lower.
Settled, confident, no catch effect.

However, bar 5 repeats the same figure at the same pitch. Bar 6 -- same again.
Six bars of identical pitches: the passage circles back to itself instead of
moving through the key. No sequential transposition = no sense of journey.

At each bar boundary there is a jarring upward leap. The voices end low, then
jump roughly a seventh to restart. By bar 8 this has repeated four times and
draws attention to the stasis.

Checkpoint answers:
1. Lockstep rhythm, no delay -- YES
2. Blended block texture distinct from imitative exposition -- YES
3. Sequential transposition through the key -- NO (flat upper_schedule)
4. Audible dissonances on structural beats -- NO (all consonant tenths);
   but a repeated minor-7th inter-bar leap is present 5 times

---

## Chaz's diagnosis

"Six bars of identical pitch, no sequencing"
Cause: upper_schedule = [1, 1, 1, 1, 1, 1]. _compute_step_schedule(7, 8, 6)
yields cumulative delta = 1 for every bar, so upper_base is constant (D5).
The planner planned E5->D5 but the actual prior (last CS note) was C5.
start_upper_deg = 7, end_upper_deg = 8, total delta = 1 over 6 bars -> flat
schedule. Documented: Known Limitation 4 in task brief. No fix in this task.
Location: episode_dialogue.py:generate() lines 454-473.

"Jarring inter-bar leap (minor 7th)"
Cause: _fragment_degrees[-1] = -6. Last note per bar is at upper_base - 6;
next bar restarts at upper_base. Gap = 6 diatonic steps = minor 7th in context.
In paired/fallback paths a follower sustain bridges this junction. _generate_parallel
has no such bridge -- both voices leap together. Out of scope per spec constraints.
Location: episode_dialogue.py:_generate_parallel, inter-bar junction between
_emit_paired_voice_notes calls.

---

Please listen to the MIDI and let me know what you hear.
