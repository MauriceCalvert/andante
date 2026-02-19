# Stretto-First Subject Generation — Prototype Design

## Core idea

Invert the pipeline. Instead of generating a melody and hoping it has
stretto, treat stretto consonance as a constraint during pitch
enumeration. Only degree sequences that produce valid counterpoint at
the target offset survive.

A stretto is a short canon: the subject overlaps a time-shifted copy of
itself. At every simultaneous sounding point in the overlap region, the
vertical interval must be consonant. This is a hard constraint on the
relationship between degree values at specific index pairs — knowable
in advance once rhythm and offset are fixed.

## Definitions

```
subject:     n notes, degrees d[0]..d[n-1], d[0] = 0
rhythm:      duration of each note in time slots (e.g. semiquaver = 1 slot)
offset:      stretto entry delay in time slots (the follower enters this
             many slots after the leader)
overlap:     the time region where both voices sound simultaneously,
             from slot `offset` to slot `total_slots - 1`
check point: any note onset in either voice during the overlap
```

## Constraint derivation

Given a fixed rhythm and offset k:

1. Build a slot-to-note-index map: for each time slot t (0..total_slots-1),
   which note index is sounding. This is a simple cumulative-duration
   lookup.

2. For each time slot t in the overlap [k, total_slots-1]:
   - leader_idx = note_at(t)         — the leader's note index
   - follower_idx = note_at(t - k)   — the follower's note index
   - beat_type = strong or weak (from metre)

3. Deduplicate: multiple consecutive slots may map to the same
   (leader_idx, follower_idx) pair. Keep only unique pairs, each
   tagged with its strictest beat type (strong trumps weak).

4. Result: two kinds of constraint:

   **Hard constraints** (strong beats): the interval must be consonant.
   ```
   (leader_idx, follower_idx, allowed_intervals_mod7)
   ```
   where allowed_intervals_mod7 = {0, 2, 5} (unison, 3rd, 6th).
   Violations are pruned during enumeration.

   **Soft constraints** (weak beats): dissonance is permitted but
   penalised by duration. The cost of a weak-beat dissonance depends
   on the minimum sounding duration of the two notes at the collision
   point. A semiquaver passing tone against a held note is near-free;
   two sustained notes clashing for a dotted quaver is expensive.

   leader_idx >= follower_idx always (leader is further into the subject).

### Dissonance cost model

At each weak-beat check point, compute:
- `leader_dur`: remaining duration of the leader's note from this slot
- `follower_dur`: remaining duration of the follower's note from this slot
- `collision_dur`: min(leader_dur, follower_dur) — the actual sounding
  overlap of the dissonance

The dissonance cost at this check point is `collision_dur` (in slots).
A 1-slot collision (semiquaver) costs 1. A 4-slot collision (crotchet)
costs 4. Consonances cost 0 regardless of duration.

The total dissonance cost for a given offset is the sum across all
weak-beat check points. This feeds the scoring, not the pruning —
the enumeration still produces all candidates that pass hard
constraints, ranked by combined melodic + dissonance score.

Exception: tritone (interval mod 7 = 3) remains a hard constraint
on all beats. It is never merely penalised.

## Index for forward checking

Group hard constraints by their higher index (the one assigned later
during enumeration):

```
constraints_at[i] = [(j, allowed_set) for each hard constraint involving
                     index i paired with j < i]
```

When the enumerator assigns degree[i], it checks every entry in
constraints_at[i]. If (degree[i] - degree[j]) mod 7 is not in the
allowed set for any entry, prune this branch.

Soft constraints are evaluated after enumeration completes, during
scoring. They do not prune.

## Enumeration

Reuse the existing recursive interval enumeration, adding one check.

```python
def _recurse(pos, pitch, ...existing params...):
    # Existing pruning: range, step fraction, contour band, etc.
    ...
    # NEW: stretto hard constraint check
    degree_at_pos = pitch  # pitch IS the cumulative degree from root
    for (j, allowed_set) in hard_constraints_at[pos]:
        interval_mod7 = abs(degree_at_pos - degrees[j]) % 7
        if interval_mod7 not in allowed_set:
            return  # prune
    # Continue recursion
    ...
```

The `degrees` array stores already-assigned degree values (cumulative
sum of intervals). degree[0] = 0 always. At position `pos`, we know
degree[pos] = pitch (the running cumulative pitch in the existing code).

## Offset strategy

Try every offset from 1 to `total_slots - 1`. Each offset is
independent — constraints are derived and enumeration runs separately
per offset.

For each candidate degree sequence, record which offsets it survives
(hard constraints pass) and the dissonance cost at each surviving
offset.

### Stretto score

A subject's stretto value reflects:
1. **Count**: how many offsets produce valid stretto. More is better.
   Each viable offset is a compositional opportunity — tighter
   offsets for climactic stretto, looser ones for expository entries.
2. **Tightness**: tighter offsets (smaller values) are worth more.
   Offset 1 is extraordinary; offset 12 is routine.
3. **Dissonance quality**: lower total dissonance cost across viable
   offsets is better.

The final subject score combines melodic quality (existing) with
stretto score. A subject viable at 6 offsets outranks one viable at
2, even if both include very tight entries.

### Why not intersect constraints across offsets?

Intersection finds subjects viable at ALL targeted offsets
simultaneously — but this is needlessly restrictive and may yield
zero results. Instead, enumerate per-offset independently and score
by the set of viable offsets. This is also simpler: no merging logic,
each offset is a clean independent run.

## Pipeline

```
1. Enumerate rhythms            — from existing enumerate_durations()
2. For each rhythm:
   a. For each offset 1..total_slots-1:
      i.   Derive hard + soft constraint pairs
      ii.  Enumerate degree sequences with melodic + hard stretto constraints
      iii. Score each sequence: melodic quality + dissonance cost at this offset
   b. Aggregate: for each degree sequence, collect the set of viable offsets
      and total dissonance cost across all offsets
   c. Rank by combined stretto score + melodic score
3. Pair across rhythms, final selection (unchanged)
```

Duration enumeration happens first: rhythm determines the constraint
topology. Pitch enumeration runs per-rhythm. This is the same
structure as now, with an extra constraint derivation step between
rhythm selection and pitch generation.

## Slot-to-note mapping

```python
def build_slot_to_note(dur_ticks: tuple[int, ...]) -> list[int]:
    """Map each time slot to the note index sounding at that slot."""
    total = sum(dur_ticks)
    slot_map = [0] * total
    t = 0
    for i, d in enumerate(dur_ticks):
        for s in range(d):
            slot_map[t + s] = i
        t += d
    return slot_map
```

Where dur_ticks are in semiquaver units (e.g. semiquaver=1, quaver=2,
crotchet=4). The existing x2-tick system uses semiquaver=2, so divide
by the minimum tick value.

## Constraint derivation

```python
def derive_stretto_constraints(
    dur_ticks: tuple[int, ...],
    offset_slots: int,
    metre: tuple[int, int],
) -> tuple[list[HardConstraint], list[SoftConstraint]]:
    """Derive hard and soft constraints from rhythm + offset.

    Hard: (leader_idx, follower_idx, allowed_mod7) — strong beats + tritone
    Soft: (leader_idx, follower_idx, collision_dur) — weak-beat dissonance cost
    """
    CONSONANT = frozenset({0, 2, 5})
    TRITONE = 3
    slot_map = build_slot_to_note(dur_ticks)
    total_slots = len(slot_map)

    # Identify check points: note onsets in either voice during overlap
    leader_onsets = set()
    t = 0
    for d in dur_ticks:
        if t >= offset_slots:
            leader_onsets.add(t)
        t += d
    follower_onsets = set()
    t = 0
    for d in dur_ticks:
        ft = t + offset_slots
        if ft < total_slots:
            follower_onsets.add(ft)
        t += d
    check_times = sorted(leader_onsets | follower_onsets)

    hard = {}   # (hi, lo) -> allowed_set
    soft = {}   # (hi, lo) -> collision_dur

    for t in check_times:
        if t >= total_slots or t - offset_slots < 0:
            continue
        li = slot_map[t]
        fi = slot_map[t - offset_slots]
        if li == fi:
            continue  # same note index — interval is 0 (unison), always OK
        key = (li, fi) if li > fi else (fi, li)
        is_strong = is_strong_beat(t, metre)

        if is_strong:
            # Hard constraint: consonance required
            if key in hard:
                hard[key] = hard[key] & CONSONANT
            else:
                hard[key] = CONSONANT
        else:
            # Soft constraint: dissonance penalised by collision duration
            # Compute minimum sounding duration at this check point
            leader_remaining = note_remaining_dur(li, t, dur_ticks, offset=0)
            follower_remaining = note_remaining_dur(fi, t - offset_slots,
                                                     dur_ticks, offset=0)
            collision = min(leader_remaining, follower_remaining)
            if key in soft:
                soft[key] = max(soft[key], collision)  # worst case for this pair
            else:
                soft[key] = collision

    # Tritone is always hard, even on weak beats
    # (handled during scoring: if interval mod 7 == 3, treat as hard fail)

    hard_list = [(hi, lo, allowed) for (hi, lo), allowed in hard.items()]
    soft_list = [(hi, lo, dur) for (hi, lo), dur in soft.items()]
    return hard_list, soft_list
```

## Interaction with existing code

The stretto-first generator is a new function, not a modification of
`generate_pitch_sequences`. It wraps the same recursive logic but with
additional constraint checking. Call signature:

```python
def generate_stretto_subjects(
    num_notes: int,
    contour_targets: list[float],
    hard_constraints: list[tuple[int, int, frozenset[int]]],
    soft_constraints: list[tuple[int, int, int]],
    # ... existing params (range, step fraction, etc.)
) -> list[tuple[tuple[int, ...], int]]:
    """Returns (degree_sequence, dissonance_cost) pairs."""
```

The caller (`select_subject`) derives constraints from the rhythm and
each offset, then passes them in. Everything downstream (duration
scoring, pairing, final selection) is unchanged except for the
addition of stretto score to the ranking.

## Expected behaviour

For a 9-note subject with semiquaver-heavy rhythm (16 slots total):
- Offsets 1-3: very tight, many check points, few or no survivors —
  but if any survive, they are exceptional subjects
- Offsets 4-6: tight, good overlap, moderate constraint density
- Offsets 8-10: moderate, the sweet spot for most rhythms
- Offsets 12-14: loose, most subjects survive, low stretto value

The search tree is pruned at each step by hard constraints, so tight
offsets with no survivors terminate very quickly. Running all offsets
is cheap.

## Advantages over current approach

1. Every generated subject is stretto-viable by construction
2. Tighter stretto offsets become possible (currently impossible)
3. Enumeration is faster per offset (more pruning = smaller search tree)
4. All offsets are tested; subjects scored by stretto richness
5. No post-hoc filter, no fallback scanner
6. Dissonance quality is graded, not binary — short passing clashes
   are nearly free, sustained clashes are expensive

## What stays the same

- Contour band pruning
- All melodic constraints (range, step fraction, allowed finals, etc.)
- Duration enumeration (runs first, determines constraint topology)
- Pairing and scoring (augmented with stretto score)
- Melodic validation (MIDI intervals: tritone, 7th, etc.)
- Answer and CS generation
- Stretto analyser (now used for verification, not filtering)

## Implementation plan

1. `build_slot_to_note()` — trivial helper
2. `derive_stretto_constraints()` — derive hard + soft constraint pairs
3. `generate_stretto_subjects()` — modified enumeration with forward checking
4. Stretto scoring — count viable offsets, weight by tightness and dissonance
5. Update `select_subject()` to use the new generator, loop all offsets
6. Verify: generated subjects should all pass the existing stretto analyser

## Known limitations (prototype)

- **Diatonic only.** The mod 7 interval check works in a single key.
  Chromatic alterations (e.g. raised leading tone) would need semitone-
  aware checks. Acceptable for prototype; flag for later.

- **Self-stretto only.** Answer-stretto (subject vs answer) and stretto
  at intervals other than the unison (e.g. stretto at the 5th) are
  deferred. Self-stretto first.

- **No inversion stretto.** Stretto with the follower in inversion is
  a separate problem. Deferred.
