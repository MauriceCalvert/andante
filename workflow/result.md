# Group E (I7) — Rhythmic Displacement in Episodes: Complete

## Summary of Changes

All changes are in `motifs/fragen.py`:

1. `Fragment` dataclass: added `beat_displacement: Fraction = Fraction(0)`
2. `_BEAT_DISPLACEMENTS` module-level constant: `(Fraction(1,4), Fraction(1,2))`
3. `_consonance_score`: added `cell_displacement` param; `bar_offset` now uses `(t + cell_displacement) % bar_length`
4. `build_fragments`: after main loop, generates displaced variants for each valid fragment; only kept if they pass `_MIN_CONSONANCE` with `cell_displacement`
5. `build_hold_fragments`: same displaced-variant generation with `_HOLD_CONSONANCE` threshold
6. `realise()`: `model_dur` extended by `beat_displacement` for the leader's voice end-time
7. `_emit_notes()`: for each iteration, emits a gap-fill held note for the leader (from iteration base to `beat_displacement`), then starts the leader cell at `beat_displacement` offset
8. `dedup_fragments`: `beat_displacement` added to dedup key so displaced variants survive deduplication
9. `_fragment_signature`: `beat_displacement` added to returned tuple so the diversity mechanism treats displaced fragments as perceptually distinct

---

## Checkpoint: Static Code Analysis

Pipeline run not performed (CLAUDE.md: "Do not run `run_pipeline`"). Evaluation from code structure only.

---

### Phase 1 — Bob

**Pass 1: What do I hear?**

I cannot hear it — the pipeline hasn't run. What I can say from reading the score logic: before this change every semiquaver burst in every episode started on the same downbeat. The episodes were identical in metric placement — four bars of "beat 1, rush, hold" repeated. Like hearing the same gesture photocopied at a lower pitch. The second episode didn't surprise me because the first one told me exactly what was coming.

After the change, the catalogue now holds three versions of every episode texture: starting on beat 1 (as before), starting on beat 2, starting on beat 3. The diversity mechanism cycles through them — the first episode gets the familiar beat-1 version (novel signature, first choice), later episodes get the displaced versions. A listener should hear the same darting figure appearing at different places in the bar. The held note, which used to always sit comfortably on beat 3, now sometimes presses onto beat 1 of the bar. That is a stronger position — it should feel like the phrase is making a point rather than trailing off.

During the displaced opening (the gap before the running voice enters), both voices hold. Brief, two beats at most. That is repose before motion, not deadness — Bach uses it deliberately.

**Pass 2: Why does it sound that way?**

The displacement works by shifting the running voice's onset within the bar. The held voice is unaffected. A gap-fill note prevents silence before the displaced entry. The consonance checker verifies that the displaced strong-beat alignment is acceptable before any displaced fragment enters the catalogue. The diversity mechanism's "prefer novel signature" policy ensures displaced versions are picked later rather than immediately, giving the first episode its expected metric placement before introducing metric variety.

---

### Phase 2 — Chaz

**Verification of `_consonance_score` with `cell_displacement`:**

```
Bob says: "the held note now sometimes lands on beat 1 — a stronger position"
Cause:    With beat_displacement=Fraction(1,2), the cell's held note (at model
          time 1/2) maps to bar_offset = (1/2 + 1/2) % 1 = 0 (strong beat 1
          of the next bar). The check correctly identifies this as strong.
Location: fragen.py:_consonance_score — bar_offset = (t + cell_displacement) % bar_length
Fix:      Already implemented.
```

**Verification of gap-fill consonance:**

```
Bob says: "both voices hold during the displaced opening — brief repose"
Cause:    Gap-fill note uses leader.degrees[0] at bar position 0. The undisplaced
          consonance check verified leader.degrees[0] against follower.degrees[0]
          at bar_offset=0 (strong beat 1). The gap-fill uses the identical degrees
          at the identical bar position. Consonance is therefore guaranteed by
          the existing undisplaced check on the base fragment.
Location: fragen.py:_emit_notes — gap-fill note emitted at t_base with leader's
          first degree; fragen.py:_consonance_score — t=0, bar_offset=0 check
          on undisplaced fragment validates this.
Fix:      No additional fix needed.
```

**Verification of no voice crossing in gap-fill:**

```
Cause:    _consonance_score returns 0.0 if u_midi - l_midi < _MIN_VOICE_SEPARATION
          at any check point. The displaced variant only enters the catalogue if
          rate >= _MIN_CONSONANCE. Gap-fill uses leader.degrees[0], verified
          against the follower at bar position 0 by the undisplaced check.
          Therefore gap-fill notes cannot produce voice crossing.
Location: fragen.py:_consonance_score line ~383
Fix:      No fix needed.
```

**Verification that displaced fragments survive dedup:**

```
Cause:    dedup_fragments key was (rhythm_class, leader_voice). Two fragments
          differing only in beat_displacement would have the same key and only
          the first would survive. beat_displacement now added to the key.
Location: fragen.py:dedup_fragments
Fix:      Already implemented.
```

**Verification that FragenProvider diversity rotates through displacements:**

```
Cause:    _fragment_signature now includes beat_displacement. Fragments with
          beat_displacement=0, 1/4, 1/2 return distinct signatures. The
          "prefer novel signatures" policy in get_fragment will pick each
          displacement at most once before cycling. Undisplaced fragments are
          in the catalogue first (build order), so the first episode picks
          an undisplaced variant (novel signature), later episodes pick displaced
          variants (also novel signatures at that point in the composition).
Location: fragen.py:_fragment_signature, fragen.py:FragenProvider.get_fragment
Fix:      Already implemented.
```

---

## Acceptance Criteria Check (Static)

- **At least 2 episode bars with non-zero beat_displacement:** The catalogue
  now contains displaced variants for every fragment that passes the displaced
  consonance check. With 4 episodes (bars 7–8, 9–10, 15–16, 17–18), the
  diversity mechanism will pick displaced variants for at least 2 of them
  (assuming the displaced checks pass for at least one fragment). Verifiable
  by running and checking the trace.

- **No new parallel perfects, cross-relations, voice crossings:** Enforced
  by `_consonance_score` at selection time. All displaced fragments must pass.

- **Gap-fill consonant with other voice:** Guaranteed by the undisplaced
  base fragment's consonance check (same degrees, same bar position 0).

- **Existing undisplaced episodes remain valid:** Undisplaced fragments are
  generated as before; only displaced variants are added. The main loop is
  unchanged.

- **No changes to phrase_writer.py or entry_layout.py:** Confirmed.

---

## Open Items

None for this task. Sub-beat displacement (quaver shift) and anacrusis
placement are documented Known Limitations and are out of scope.
