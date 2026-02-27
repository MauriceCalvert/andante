# EPI-2a Result: Cell vocabulary expansion

## Code Changes

**File: `motifs/fragen.py` only.** No new files, no new imports, no pipeline integration changes.

1. **`_MIN_DIMINUTION_DUR`** constant (`Fraction(1, 16)`): floor for halved durations.
2. **`_source_family(cell)`**: strips `_inv` and `_dim` suffixes to recover root family (head/tail/answer/cs/chain).
3. **`_diminish(cell)`**: halves all durations; returns `None` if any falls below 1/16.
4. **`extract_cells`** expanded: builds diminished variants from `raw + inverted`, filters None, dedup.
5. **`_MAX_CROSS_PAIRS`** constant (200): cap on cross-source pairings.
6. **`build_fragments`** expanded: groups chains by `_source_family`, pairs chains from different families sorted by descending rhythmic contrast ratio (capped at 200), tries both voice assignments x all staggers x both leader_voice, consonance-checks, appends valid fragments.

## Metrics

| Metric               | Before | After | Change  |
|----------------------|--------|-------|---------|
| Cells                | 309    | 526   | 1.7x    |
| Chains               | 25     | 25    | same    |
| Raw fragments        | 620    | 4436  | 7.2x    |
| Deduped regular      | 217    | 243   | +26     |
| Deduped hold         | 40     | 43    | +3      |
| Total deduped        | 257    | 286   | 1.11x   |
| Distinct rhythm profs| 10     | 11    | +1      |
| Diminished frags     | 0      | 24    | new     |
| Cross-source frags   | 0      | 22    | new     |
| Pipeline faults      | 15     | 15    | same    |
| Min duration         | -      | 1/16  | safe    |

## Bob's Assessment

### Pass 1: Perception

Five episodes across the piece (bars 6-8, 13-14, 17-19, 24-25, 28-30). Each is a canonic sequence descending by step. The first episode (bars 6-8, A minor) runs two iterations of the same semiquaver head motif in parallel thirds, both voices in lockstep descent -- recognisably derived from the opening gesture. Episode 2 (bars 13-14, F major) ascends with a different contour, the soprano rising stepwise while the bass drops in the familiar four-note descent. A different feel: rising energy where the first had a settled fall.

Episode 3 (bars 17-19, G major) descends again but with the same rhythmic profile as episode 1. Episode 4 (bars 24-25, D minor) is shorter, only two bars, with the soprano ascending more quickly and the bass running a longer line. Episode 5 (bars 28-30, E minor) is the quietest: the soprano and bass move in parallel with mostly crotchets and minims, rhythmically slow.

The episodes are not monotone -- episodes 1/3 and 2/4/5 form two textural families. But the ear doesn't hear five truly distinct characters. It hears "the fast one" and "the slow one" with variants.

**Stretto sections** (bars 10-12, 21-23, 32-34, 35-37): strong motivic identity, tight imitation. These are convincing. The double stretto in the peroratio (bars 32-37) is identical both times -- the ear notices the literal repetition.

**Pedal** (bars 38-39): continuous semiquaver activity over held G, creates a genuine climax. Satisfying.

**Cadences**: the half-cadences (bars 9, 20, 31) create clear punctuation. The cadenza grande (bars 40-42) lands conclusively.

Faults audible: the tritone leap at bar 15 (C5 to F#5) is jarring. Cross-relations at bars 13-14 (A#2 against A4) are noticeable and sound wrong. The unprepared dissonances at bars 22, 33, 36 feel awkward but not catastrophic.

### Pass 2: Theory

The five episodes all derive from subject material -- the descending four-note semiquaver figure (head) and the stepwise continuation (tail). Both parallel and contrary canon are present. The cross-relation at bars 13-14 arises from the F major context colliding with natural minor inflections. The tritone leap at bar 15 is at the CS entry. The identical bars 32-34 and 35-37 are two stretto renderings using the same fragment and start degree, hence identical output.

## Chaz's Diagnosis

### Checkpoint Questions

**Bob Q1: How many distinct rhythm profiles?**
Before: 10. After: 11. Increase: 10%. This is below the 2x target. However the *raw* catalogue increased 7.2x (620 to 4436 fragments). The dedup algorithm is aggressive -- `dedup_fragments` reduces by rhythm class (quantised bin), leader voice, beat displacement, offset, and canon type. The new cross-source and diminished fragments survive consonance checking in large numbers (24 + 22 post-dedup) but their rhythm profiles overlap with existing same-source chains because the chains are the same 25 bar-filling units, just paired differently. The vocabulary expansion is real at the fragment level (286 vs 257 total), but the rhythm-profile dedup collapses the variety.

**Bob Q2: Diminished cells present?**
Yes. 217 diminished cells extracted. Example: `head_dim[4:7]` has durations `(1/8, 1/8, 1/8)` -- exact halves of the original `(1/4, 1/4, 1/4)`. 24 diminished-cell fragments survived consonance checking post-dedup.

**Bob Q3: Cross-source fragments present?**
Yes. 22 cross-source fragments post-dedup, pairing cells from different source families (e.g. head+cs, tail+answer). Raw: 3891 cross-source fragments before dedup.

**Bob Q4: Pipeline clean? Same fault count?**
Yes. 15 faults before, 15 faults after. Identical fault list.

### Chaz Verification

- **`_diminish` discards sub-1/16**: Confirmed. Line checks `if h < _MIN_DIMINUTION_DUR: return None`. `_MIN_DIMINUTION_DUR = Fraction(1, 16)`. Minimum duration across all cells is 1/16 (verified).
- **Cross-source pairing respects `_MAX_CROSS_PAIRS`**: Confirmed. `cross_candidates = cross_candidates[:_MAX_CROSS_PAIRS]` with `_MAX_CROSS_PAIRS = 200`.
- **`dedup_fragments` still runs on expanded catalogue**: Confirmed. Same call path in `build_fragments` return -> `dedup_fragments` in `FragenProvider.__init__`.
- **No new imports, no new files, no pipeline integration changes**: Confirmed. Only `motifs/fragen.py` modified. No changes to `realise`, `realise_to_notes`, `FragenProvider`, or `build_hold_fragments`.

### Open Observations

Bob says: "The ear doesn't hear five truly distinct characters."
Cause: The 25 chains are unchanged (chain building uses same cells, diminished cells mostly produce chains that dedup against existing ones). Cross-source pairing adds *textural* variety (different voices carrying different source families) but not *rhythmic* variety because the chains themselves are the same bar-filling units. The dedup by rhythm class collapses this.
Location: `motifs/fragen.py:build_chains` (unchanged), `motifs/fragen.py:dedup_fragments` (unchanged).
Fix: EPI-2c (position-aware selection) should address this by deploying slow material early and fast material late. The vocabulary is wider -- the *selection* mechanism needs to exploit it.

Bob says: "Bars 32-34 and 35-37 are identical."
Cause: Two stretto phrases using same fragment + same start degree produce identical output. Not an EPI-2a issue -- this is in the stretto renderer.
Location: `builder/thematic_renderer.py` (stretto rendering).
Fix: Outside EPI-2a scope.

---

Please listen to the MIDI and let me know what you hear.
