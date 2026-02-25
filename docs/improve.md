# Improve: Invention Quality

Combined assessment from Bob (detailed score reading) and Gemini
(comparison with BWV 772). Prioritised by musical impact.

Items already on the Parked list in todo.md are marked [PARKED].
New items are marked [NEW].

---

## Tier 1 — Structural faults (the piece is broken here)

### I1. Dead pedal (bars 19–22) [PARKED]

**What's wrong.** Bass holds G3 as a semibreve for two bars. Soprano
oscillates C4–D4–E4 with no direction, no chromatic intensification, no
cadential preparation. The piece stops moving four bars before it ends.
A dominant pedal should be the most tensely directed passage in the
piece; this one is the most inert.

**What both reviewers say.** Bob: "arrival without approach is not a
cadence — it's a stop." Gemini: "the upper voice just oscillates…
it lacks the mounting tension Bach usually builds before a PAC."

**What a musician does.** Over a dominant pedal the soprano drives
toward the cadence: sequential descent, suspensions against the pedal,
chromatic approach tones, accelerating rhythm. The ear should feel the
harmonic ground pulling toward resolution. Bach BWV 772 keeps continuous
semiquaver motion right through the final bars.

**Fix.** Two sub-tasks:
- **I1a — Pedal soprano tension** [PARKED as "Pedal soprano tension"].
  `_write_pedal` currently gives the soprano only two boundary knots,
  so Viterbi fills with aimless steps. Needs mid-phrase knots on a
  descending trajectory with rhythmic acceleration (crotchets→quavers→
  semiquavers) and at least one prepared suspension (4–3 or 7–6 against
  the pedal G).
- **I1b — Cadential bass formula** [PARKED as "Final cadence bass
  formula"]. The cadenza_composta bass is currently three repeated
  dominants then bare tonic. Needs a pre-dominant approach: at minimum
  IV–V–I or ii⁶–V–I in the final bar.

### I2. Parallel octaves (bars 4–6) [NEW]

**What's wrong.** Three parallel octaves in consecutive bars:
E5/E3→D5/D3, B4/B2→C5/C3, A4/A2→B4/B2. Fux red-ink faults. The
Viterbi solver for the countersubject is finding octave doublings and
moving through them in parallel.

**Fix.** Viterbi cost function (`viterbi/costs.py`) needs a heavy
penalty for parallel perfect consonances (P1/P5/P8) between consecutive
strong beats. This is a cost-weight issue, not an architectural one.
The parallel-detection code may already exist in `faults.py`; wire it
into the Viterbi transition cost rather than scanning post-hoc.

### I3. Answer truncation [NEW]

**What's wrong.** The subject is 2 bars: descending-thirds head
(G–E–C) plus ascending scale tail. The bass answer at bar 3 has no
head — it begins at the ascending run. The defining gesture of the
subject is missing from the answer. A listener who expects imitation
hears half a subject.

**What the data shows.** The `.fugue` file defines the answer with the
same 10 degrees as the subject (4,2,0,0,1,2,3,4,5,4), so the degrees
are present. The bug is in rendering: the answer starts at bar 3 beat
3 (offset 2.5), which is halfway through bar 3. The first half-bar of
the answer (the head: degrees 4,2,0 = G–E–C transposed to D–B–G) is
missing from the output. Either the answer offset or the answer start
time is wrong, or the head notes are being clipped.

**Fix.** Trace the answer rendering path in `imitation.py` /
`thematic_renderer.py`. The answer must start on bar 3 beat 1 (or
wherever `answer_offset_beats` places it), not beat 3. If the entry
layout puts the answer at beat 3, the layout is wrong for this subject.

### I4. Spacing collapse [NEW]

**What's wrong.** Seven bars have downbeat spacing below 10 semitones:
bars 9 (4st), 11 (8st), 12 (9st), 14 (8st), 18 (9st), 19 (5st),
20 (5st). Two-voice counterpoint needs 12–24 semitones of separation.
Below 10 the voices merge into one registral band. Bars 19–20 at 5st
are a fourth — both voices in one octave.

Bar 9 is the worst offender: bass leaps 15 semitones (A2→C4) into
the soprano's register, producing a M3 (4st) spacing on beat 1.

**What a musician does.** Maintains roughly a 10th to two octaves of
registral separation. Adjusts octave placement at phrase boundaries to
keep the voices in distinct bands.

**Fix.** Viterbi corridor constraints (`viterbi/corridors.py`) should
enforce a minimum separation from the other voice. A soft cost (not a
hard clamp, per L003) that penalises transitions below 10st separation
and strongly penalises below 7st. Episode boundary leaps (bar 9) need
proximity-aware start pitch selection — `_find_start` should reject
pitches that collapse into the other voice's register.

---

## Tier 2 — Textural failures (the piece sounds mechanical)

### I5. Lockstep homophony [NEW]

**What's wrong.** Bars 7, 9, and 13 have soprano and bass in identical
note counts and durations. An invention is defined by rhythmic
independence. Lockstep quarter notes three times in 22 bars sounds
like a chorale, not counterpoint.

**What Gemini says.** "Voices are not 100% equal — upper voice leads,
lower voice provides support." This is a rhythmic problem: when the
bass has the subject (active semiquavers), the soprano should have
a contrasting rhythm (held notes, syncopations), and vice versa.

**Fix.** The countersubject rhythm already provides contrast in CS
entries. The problem occurs in non-CS accompaniment bars (bars 7, 9,
13 where the "accompany" voice defaults to quarter-note chord tones).
The Viterbi solver should receive rhythm cells from the genre config
that differ from the active voice's rhythm, not identical quarter-note
grids. Wire `rhythm_cells.py` into accompaniment generation with a
constraint: accompaniment rhythm must differ from the active voice's
rhythm on at least 50% of beats.

### I6. Oblique monotony [NEW]

**What's wrong.** 52% oblique motion (one voice moves, the other holds).
Only 24% contrary. The voices take turns instead of conversing. Gemini:
"more like a melody with accompaniment than a true equal-voice
conversation."

**What a musician does.** In a two-voice invention, when one voice has
the subject the other has a composed countersubject or free counterpoint
that is rhythmically and directionally independent. Contrary motion
should be 30–40% in healthy two-voice writing.

**Fix.** Partly addressed by I5 (rhythmic independence reduces oblique
motion mechanically). Additionally, the Viterbi cost function should
include a contrary-motion bonus: when the soprano moves up, prefer
bass candidates that move down, and vice versa. This is a cost-weight
addition, not a hard constraint.

### I7. Rhythmic predictability [NEW]

**What Gemini says.** "The 1/16th-note runs appear in very predictable
blocks." The subject's semiquaver run always occupies the same position
within the bar (beats 1–2). There is no rhythmic displacement — the
motif never starts on a different beat.

**What a musician does.** Bach displaces motifs metrically: the same
figure appears starting on beat 1 in one entry, beat 3 in another.
Episodes fragment the subject and re-sequence fragments at different
metric positions.

**Fix.** This requires two things:
1. Episode fragments already come from fragen, which extracts cells
   at their original metric positions. Fragen should also offer
   cells at displaced positions (same pitches, different beat offset).
   This is a fragen catalogue enhancement.
2. Stretto entries already displace the answer by `delay` beats. More
   stretto entries with different delays would create metric variety.
   This is a planner-level decision (entry_sequence in the genre YAML).

### I8. Bars 17–18 rhythmic holes [NEW]

**What's wrong.** Bar 17 beat 1: soprano sounds, bass silent. Bar 18
beat 1: soprano silent (first note at beat 2). Two consecutive bars
with missing downbeats in one voice. In a two-voice texture every
downbeat should have at least one voice present.

**Fix.** This is likely a hold-exchange or episode boundary where the
entry layout leaves a gap. The phrase planner should ensure every bar
has at least one voice sounding on beat 1. Add a validation pass in
`phrase_planner.py` that flags beat-1 gaps and extends the prior note
or inserts a rest-filling note.

---

## Tier 3 — Musical depth (the piece lacks sophistication)

### I9. No melodic inversion [NEW]

**What Gemini says.** "Bach immediately turns the motive upside down.
This piece doesn't engage in rigorous melodic inversion." BWV 772's
subject is answered in inversion — the ascending scale becomes
descending. This creates the "mathematical puzzle solving itself"
quality.

**What the system supports.** The `.fugue` file defines a `real`
answer (same intervals, transposed). There is no `inverted` answer
type. The subject planner and answer generator would need an inversion
path: negate the degree intervals, adjust octave to maintain range.

**Fix.** Two parts:
1. **Answer generator reform** — add `type: inverted` support in
   `answer_generator.py`. Inverted answer = negate each interval
   (ascending becomes descending), then adjust to fit the dominant
   key. This is a well-defined transformation.
2. **Subject definition** — the `.fugue` file needs a flag or the
   subject generator needs to detect which subjects benefit from
   inversion (subjects with a clear ascending/descending asymmetry).

This is a significant feature. Park for after Tier 1–2.

### I10. No double counterpoint [NEW]

**What Gemini says.** "High use of double counterpoint" in BWV 772 vs
"standard rhetorical progression" here.

**What the system does.** The YAML says `invertible_counterpoint: true`
but completed.md notes: "CS is optimised per-entry by Viterbi, not
composed once to work both above and below the subject." True double
counterpoint means a single CS that is consonant when the soprano is
above AND when it's below (inverted at the octave). The current system
re-optimises each time, which means the CS changes between entries —
exactly what invertible counterpoint is supposed to prevent.

**Fix.** [PARKED as "Invertible counterpoint enforcement"]. This is
architectural: compose the CS once at the octave-invertible interval
set (3rds, 6ths, passing dissonance only; no 5ths which become 4ths
on inversion). Then stamp it in both orientations. The Viterbi solver
can refine locally but must not violate the invertibility constraint.

### I11. Harmonic simplicity [NEW]

**What Gemini says.** "BWV 772 uses more chromatic passing tones and
secondary dominants." The piece modulates to G and Am but everything
is diatonic. No applied dominants, no chromatic neighbour tones, no
modal mixture.

**What the system supports.** The harmonic layer (HRL) has only Phase
1 implemented. Phases 2–6 (harmonic interpolation, cadential
acceleration, inversions, secondary dominants) are on the Later list.

**Fix.** [PARKED as "HRL Phases 2–6"]. Specifically:
- Secondary dominants (V/V, V/vi) in the Viterbi pitch candidates.
- Chromatic passing tones in the diminution/figuration layer.
- Cadential acceleration (more harmonic changes per bar approaching
  cadences).

### I12. Late second voice entry [NEW]

**What Gemini says.** "The upper voice plays for a full two bars before
the lower voice provides any significant counterpoint." BWV 772's
answer enters after one bar (at the octave).

**What the system does.** `answer_offset_beats: 2` in the invention
YAML means the answer enters 2 beats after the subject. But the
subject is 2 bars long, and the answer begins at bar 3 — so the gap
is 2 bars, not 2 beats. Either the offset is misconfigured or the
rendering interprets it differently from the planner.

**Fix.** This may be the same bug as I3 (answer truncation). If the
answer genuinely starts at bar 3, the YAML `answer_offset_beats`
should be changed to produce a bar-2 entry (after 1 bar, as in BWV
772). If the answer is supposed to start at bar 2 beat 3 but is being
clipped, that's I3. Investigate together with I3.

---

## Tier 4 — Polish (after the above)

### I13. Continuous semiquaver drive [NEW]

**What Gemini says.** "Stop-and-start 1/16th-note sections" vs Bach's
"continuous 1/16th-note drive." The subject's semiquaver run stops
at beat 3 (half-note) every time, creating a start-stop rhythm.

**What a musician does.** In mature inventions the semiquaver motion
passes between voices almost continuously. When the soprano's run
ends, the bass's begins (or continues). The half-note at the end of
each subject statement is a natural breathing point, but the other
voice should be filling it.

**Fix.** The countersubject rhythm (from the `.fugue` file) already
has contrasting durations, but they're quarter and half notes. A
more active CS — or free counterpoint with semiquaver fragments
during the subject's held notes — would create continuous motion.
This requires either CS rhythm reform or a figuration layer that
fills held notes with diminutions.

### I14. Stronger episode variety [EXISTING]

**What Bob says.** Episode bars (9–10) have the bass leaping 15st into
the soprano register. Fragment variety is limited by the catalogue.

**Status.** F3 (fragen as class) and F4 (signature diversity) are
complete. The remaining issue is catalogue size: the call_response
subject generates few distinct fragments. More fragments require either
a richer subject or manual catalogue curation.

---

## Execution order

Grouped to reduce round trips. Dependencies respected within and
between groups.

```
Group A:  I3 + I12  Answer timing (1 brief — see notes below)
Group B:  I2 + I4 + I6  Viterbi cost fixes (parallel octaves, spacing, contrary motion)
Group C:  I1a + I1b  Pedal repair (soprano tension + cadential bass formula)
Group D:  I5 + I8  Rhythmic texture (lockstep fix + beat-1 gap validation)
Group E:  I7  Rhythmic displacement (fragen + planner)
Group F:  I9, I10, I11  Architectural / depth (separate briefs, deferred)
Group G:  I13 + I14  Polish (continuous drive + episode variety)
```

9 round trips instead of 14. Active work (A–E) is 5 instead of 10.

**Group A status notes:** Investigation shows the render_offset
mechanism in entry_layout.py correctly shifts the answer back by
answer_offset_beats, and the full 10-note answer including the
descending-thirds head is present in .note and MIDI output from bar 2
beat 3. However, I3 is NOT fixed: the MusicXML writer overflows bar 2.
`makeRests(fillGaps=True)` fills the initially-empty bar with rests,
then the answer notes at offset 6.0q (bar 2 beat 3) pile on top instead
of replacing the rests — producing 6 beats in a 4/4 bar. This is a
MusicXML writer bug, not a rendering bug.

I12 (late entry) is a YAML configuration issue: answer_offset_beats=2
produces a bar 2 beat 3 entry; changing to answer_offset_beats=4 would
produce a bar 2 beat 1 entry (1-bar delay, as in BWV 772). This also
requires verifying that the CS windowing handles the longer overlap and
that the phrase plan correctly accounts for the earlier entry.

Group A first because every downstream assessment changes if the answer
enters earlier. Group B next because parallel octaves are hard faults
that invalidate any other judgement, and spacing/contrary-motion are
all Viterbi cost additions to the same file family. Group C because
the pedal is the most audibly broken passage. Group D for texture once
pitches are right. Group E standalone. Groups F and G deferred.
