# B5 — Chromatic approach tones: raised 7th in minor

## Draft

### Musical Goal

When the piece is in a minor key, cadences sound modal rather than tonal.
The soprano resolves by whole step (degree 2→1) without the leading tone,
and the pre-cadential approach lacks the chromatic inflection that signals
"this phrase is about to cadence." The raised 7th of each minor key area
should appear in the bars approaching a cadence, creating the semitone
pull toward the tonic that defines tonal minor-key cadences (Principle 1:
tension and release).

### Idiomatic Model

**What the listener hears**: In a minor-key cadence, there's a moment of
chromatic intensification — a note that doesn't belong to the natural scale
appears, pulling hard toward the tonic. The ear registers this as "we're
arriving." Without it, the cadence feels like a modal plateau, not a tonal
arrival. The semitone tension is the rhetorical signal that the phrase is
ending.

**What a competent musician does**: In D minor, a keyboard player
approaching a cadence introduces C# — the leading tone — in the last bar
or two before the arrival on D. This C# appears as a passing tone or
neighbour in the melodic line, always resolving upward by semitone to D.
The player does NOT use C# freely throughout the phrase; it appears only
in the cadential approach zone (typically the last 1–2 bars before the
cadence). Outside this zone, C natural is the norm. The player also avoids
the augmented second between Bb (degree 6) and C# (raised 7th) — if C# is
present, Bb is typically avoided in the same melodic line (or degree 6 is
also raised to B natural, giving ascending melodic minor).

The raised 7th appears in BOTH voices but not simultaneously in contradictory
forms. If the soprano has C#, the bass must not have C natural sounding
nearby — that's a cross-relation (Principle 2).

**Rhythm**: No rhythmic change. The raised 7th appears on the same beats
the natural 7th would have occupied. It's a pitch alteration, not a
rhythmic one.

**Genre character**: Applies to all genres when the local key is minor.
The raised 7th is a tonal convention, not a genre-specific idiom.

**Phrase arc**: The raised 7th is the final intensification device in the
phrase arc. It appears in the cadential approach zone (last 1–2 bars),
not at the phrase opening or middle. This is Principle 8: emphasis requires
contrast. If the raised 7th appeared throughout the phrase, it would just
be a different scale (harmonic minor used everywhere) rather than a
cadential inflection.

### What Bad Sounds Like

- **Modal plateau**: Cadence arrives without the semitone pull. The
  resolution sounds Dorian or Aeolian rather than tonal minor. Violates
  Principle 1 (no tension at the point of maximum expected release).

- **Harmonic minor everywhere**: Raised 7th used in every bar of every
  minor-key phrase. The augmented second (Bb→C# in D minor) becomes a
  melodic cliché. Violates Principle 8 (universal application destroys
  emphasis).

- **Cross-relation**: C# in one voice, C natural in the other within a
  beat or two. The ear hears the clash between the two forms of the same
  pitch class. Violates Principle 2 (voices exist in relation to each other).

### Known Limitations

1. **Raised 6th (melodic minor ascending) not addressed.** The code will
   use harmonic minor (raised 7th only). A musician would also raise
   degree 6 when ascending through 6→7→1 to avoid the augmented second.
   Code: harmonic minor scale. Musician: melodic minor ascending. Gap is
   acceptable — the augmented second is penalised by the Viterbi step cost
   (3 semitones = expensive), so the solver will avoid it when stepwise
   alternatives exist.

2. **Cadential templates don't include degree 7.** Our cadence templates
   use [4, 3, 2, 1] for soprano. A musician might use [4, 3, 7#, 1]. The
   template is unchanged in this phase. The raised 7th will appear in the
   PRE-cadential Viterbi phrase, not in the template cadence itself. This is
   acceptable: the leading tone approaching from the previous phrase is more
   impactful than adding it inside the formulaic cadence.

3. **Phase applies to Viterbi-generated phrases only.** Thematic material
   (subject, answer, CS, episodes) uses pre-composed fragments, not Viterbi.
   The raised 7th won't appear inside subject statements. This is acceptable:
   the subject is in the home key and its material is fixed. The chromatic
   inflection belongs in the FREE counterpoint alongside thematic material,
   not in the material itself.

4. **Both voices get harmonic minor simultaneously.** A musician might use
   the raised 7th in the soprano while the bass stays natural, or vice
   versa. The current approach gives both voices the same key. The
   cross-relation cost should prevent contradictory usage, but it's less
   nuanced than voice-independent chromaticism. Acceptable for Phase 1.

### Implementation

**1. Constants** (`shared/constants.py`):
Add `HARMONIC_MINOR_SCALE: tuple[int, ...] = (0, 2, 3, 5, 7, 8, 11)`.

**2. Key class** (`shared/key.py`):
Add property `cadential_pitch_class_set` that returns `pitch_class_set`
using `HARMONIC_MINOR_SCALE` for minor keys, identical to `pitch_class_set`
for major keys. Also add `cadential_scale` property returning
`HARMONIC_MINOR_SCALE` for minor, `MAJOR_SCALE` for major.

**3. PhrasePlan** (`builder/phrase_types.py`):
Add optional field `cadential_approach: bool = False`. Set to `True` when
the phrase immediately precedes a cadential phrase in a minor key.

**4. Composition loop** (`builder/compose.py`):
When computing next_entry info, if the next phrase is cadential AND
`next_plan.local_key.mode == "minor"`, set `cadential_approach=True` on
the current plan (via `dataclasses.replace`).

**5. Soprano Viterbi** (`builder/soprano_viterbi.py`):
When building `KeyInfo`, check `plan.cadential_approach`. If True, use
`plan.local_key.cadential_pitch_class_set` instead of
`plan.local_key.pitch_class_set`.

**6. Bass Viterbi** (`builder/bass_viterbi.py`):
Same as soprano: when `plan.cadential_approach`, use cadential pitch class
set.

**7. Law update** (`docs/Tier1_Normative/laws.md`):
Update L010 to: "Leading tone in cadential context only (pre-cadential
approach + cadential phrases in minor keys)."

### Constraints

- Do not modify the Viterbi solver (costs.py, pipeline.py, corridors.py,
  pathfinder.py).
- Do not modify cadence templates (templates.yaml).
- Do not modify thematic_renderer.py or entry_renderer.py.
- Do not introduce raised 6th (melodic minor) — that's a separate phase.
- Major key behaviour must be completely unchanged.

### Checkpoint (mandatory)

Generate an invention in D minor (use `--key d_minor` if available, or
modify the test to force D minor). Evaluate as Bob, then diagnose as Chaz.

Bob:
1. In the phrase before the cadence, does the raised 7th appear? Where?
2. Does it resolve upward by step (semitone) to the tonic?
3. Is there any cross-relation (natural 7th in one voice, raised 7th in
   the other within 2 beats)?
4. Does the cadence sound more tonal than before?
5. Does the augmented second (degree 6 → raised 7) appear? If so, is it
   melodically awkward?

Chaz:
For each of Bob's complaints, trace to code location and propose fix.

Also run the invention in D major to confirm zero change in major-key
output.

### Acceptance Criteria

- In minor-key pre-cadential phrases, the raised 7th appears at least once
  in the soprano or bass (CC-measurable proxy).
- The raised 7th always resolves by ascending semitone within 2 notes
  (CC-measurable proxy — Bob's ear is the real test).
- No cross-relations between voices at the raised 7th (existing
  cross-relation cost should prevent this; verify).
- Major-key output byte-identical to baseline.
- No augmented seconds in the melodic line (Viterbi step cost should
  prevent this; verify).

---

## Musician Review

### A. Counterpoint relationship (Principle 2)

The brief says both voices get harmonic minor simultaneously. This is
correct for cadential approach — both the soprano and bass should be in
the same tonal space. The cross-relation risk is named explicitly (Known
Limitation 4). The brief specifies that the raised 7th must not appear
in one voice while the natural 7th sounds in the other.

Gap: the brief doesn't say what happens when one voice has thematic material
(which uses the original key) while the other has Viterbi counterpoint
(which would use harmonic minor). In a pre-cadential thematic phrase, the
subject might have C natural while the Viterbi companion has C#. This is
a cross-relation.

**Fix**: The `cadential_approach` flag should only affect Viterbi-generated
voices. For thematic phrases with mixed material/FREE voices, the FREE
voice must use the same pitch set as the thematic material — natural minor.
Add to constraints: cadential_approach only applies to fully schematic
(galant-path) phrases, not to thematic phrases. Thematic phrases in minor
already have their material in natural minor and the FREE companion must
match. This is Known Limitation 3, now made explicit as a constraint.

### B. Harmonic implication (Principle 4)

The brief treats the raised 7th as a melodic device (passing tone,
neighbour tone). In harmonic terms, it implies a dominant chord (V or vii°).
The brief doesn't address whether the bass should be on degree 5 when the
raised 7th appears. In practice, the raised 7th against a bass on degree
5 creates a dominant seventh sonority — desirable. Against other bass
degrees, the raised 7th might create odd harmonies.

**Assessment**: The Viterbi solver already penalises dissonance, so the
raised 7th will naturally gravitate to consonant positions against the bass.
No explicit harmonic constraint needed. The brief's approach (let the solver
handle it) is adequate for Phase 1.

### C. Directional logic (Principle 5)

The brief says the raised 7th appears in the "last 1–2 bars." But the
implementation gives the entire pre-cadential phrase harmonic minor. For
a 4-bar schematic phrase, that means the raised 7th is available in bars
1–4, not just bars 3–4.

**Assessment**: The solver won't use it gratuitously — it only appears
where it fits stepwise and consonant. But the brief should acknowledge
this is a coarser granularity than ideal. The phrase-level key switch is
a Phase 1 simplification. Phase 2 could restrict to the last bar only
(by splitting the corridor or using beat-indexed key changes). Added to
Known Limitations.

### D. Rhythmic idiom (Principle 6)

Addressed. The brief explicitly states no rhythmic change.

### E. Tension and release (Principle 1)

The raised 7th creates semitone tension toward the tonic. The brief
correctly positions this as the final intensification. The cadence
template then resolves via degree 2→1 (whole step), but the raised 7th
in the preceding phrase has already established the tonal pull. Adequate.

### F. Textbook red flags (Principle 5)

No universal application — the brief restricts to pre-cadential minor
phrases only (Principle 8). No arbitrary thresholds. No clichés. Clean.

### G. Practitioner test

A baroque keyboard player reading this brief would produce correct output.
The one gap is the augmented second risk (6→#7), which the brief names
but delegates to the step cost. A practitioner would actively avoid it.
The solver's penalty is a reasonable proxy.

### H. Rhetorical selectivity (Principle 8)

Explicitly addressed. The raised 7th only in cadential approach, not
throughout. The default (natural minor) is named. The trigger condition
(next phrase is cadential AND key is minor) is clear. Pass.

## Revised Brief

Changes from draft:

1. Added Known Limitation 5: the entire pre-cadential phrase gets harmonic
   minor, not just the last 1–2 bars. Phase 2 refinement.

2. Added constraint: `cadential_approach` only applies to schematic
   (galant-path) phrases. Thematic phrases with mixed material/FREE voices
   must use natural minor for both voices to avoid cross-relations between
   thematic material and Viterbi companion.

3. Implementation step 4 updated: only set `cadential_approach=True` when
   the current phrase is NOT thematic (no thematic_roles with material).
