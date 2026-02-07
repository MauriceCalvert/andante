# Anacrusis Implementation

## Problem

Fix 3 from plan1.md (upbeat offset) was never implemented. The only change site mentioned
in plan1 was `cumulative_bar = 0`, but the problem is much deeper: every offset formula
in phrase_writer.py assumes uniform bar length via `start_offset + (bar_num - 1) * bar_length`.
An anacrusis bar is shorter than a full bar, so this formula produces wrong offsets for
every bar after the first.

### Concrete example — gavotte (4/4, upbeat=1/2, bar_length=1)

Meyer schema, 3 stages. What we need:

| bar_num | offset | duration |
|---------|--------|----------|
| 1       | -1/2   | 1/2 (partial) |
| 2       | 0      | 1 (full) |
| 3       | 1      | 1 (full) |

What the naive formula gives with start_offset = -1/2:

| bar_num | computed         | correct | error |
|---------|------------------|---------|-------|
| 1       | -1/2             | -1/2    | —     |
| 2       | -1/2 + 1×1 = 1/2 | 0       | +1/2  |
| 3       | -1/2 + 2×1 = 3/2 | 1       | +1/2  |

Every bar after the anacrusis is shifted by `bar_length - anacrusis`. This same broken
formula appears in at least 9 places across phrase_writer.py and compose.py.

## Affected genres

- **Gavotte**: upbeat = 1/2 (already declared in YAML)
- **Bourrée**: upbeat = 1/4 (missing from YAML — comment says "quarter-note upbeat" but no field set)

## Design decisions

### 1. New field: `PhrasePlan.anacrusis`

Only the first phrase of the piece has an anacrusis. Rather than recomputing
`is_first_phrase and upbeat > 0` everywhere, the phrase planner sets
`anacrusis = upbeat` on the first PhrasePlan and `Fraction(0)` on all others.

### 2. Four helper functions in phrase_types.py

All offset arithmetic routed through these. Eliminates the repeated inline formula
and makes the anacrusis adjustment invisible to callers.

- `phrase_bar_start(plan, bar_num, bar_length)` → absolute offset where bar begins
- `phrase_bar_duration(plan, bar_num, bar_length)` → duration of that bar (partial for bar 1 with anacrusis)
- `phrase_degree_offset(plan, pos, bar_length, beat_unit)` → absolute offset for a BeatPosition
- `phrase_offset_to_bar(plan, offset, bar_length)` → reverse: offset → bar number

The key insight: with anacrusis, bar 1 runs from `start_offset` to `start_offset + anacrusis`.
Bar 2 onwards runs from `start_offset + anacrusis + (bar_num - 2) * bar_length`. Without
anacrusis, the old formula `start_offset + (bar_num - 1) * bar_length` is recovered exactly.

### 3. phrase_duration correction

Currently: `phrase_duration = bar_span * bar_length`.
With anacrusis: `phrase_duration = anacrusis + (bar_span - 1) * bar_length`.

For gavotte 3-stage meyer: 1/2 + 2×1 = 5/2, not 3.

### 4. cumulative_bar initialisation

In `build_phrase_plans`: `cumulative_bar = 0 if has_upbeat else 1`.
This makes the first schema get `first_bar = 0`, which is how Layer 4 anchors
already number the upbeat bar (see `compute_upbeat_bar_beat` which returns
`start_bar - 1`).

### 5. bourree.yaml fix

Add `upbeat: "1/4"` to match the genre definition.

## Change sites

| # | File | What | Current | Fix |
|---|------|------|---------|-----|
| 1 | phrase_types.py | New field | — | `anacrusis: Fraction = Fraction(0)` |
| 2 | phrase_types.py | Helpers | — | 4 functions (done) |
| 3 | phrase_planner.py | cumulative_bar init | always 1 | 0 for upbeat |
| 4 | phrase_planner.py | PhrasePlan construction | no anacrusis | pass anacrusis for first phrase |
| 5 | phrase_planner.py | phrase_duration | `bar_span * bar_length` | adjust for anacrusis |
| 6 | phrase_planner.py | `_compute_start_offset` | inline bar=0 branch | use anacrusis field |
| 7 | phrase_writer.py soprano | degree offset (×1) | inline formula | `phrase_degree_offset` |
| 8 | phrase_writer.py soprano | offset→bar (×2) | inline formula | `phrase_offset_to_bar` |
| 9 | phrase_writer.py soprano | bar→offset in loop (×1) | inline formula | `phrase_bar_start` |
| 10 | phrase_writer.py soprano | figuration bar_num (×1) | inline formula | `phrase_offset_to_bar` |
| 11 | phrase_writer.py bass | degree offset (×1) | inline formula | `phrase_degree_offset` |
| 12 | phrase_writer.py bass | offset→bar (×2) | inline formula | `phrase_offset_to_bar` |
| 13 | phrase_writer.py bass | soprano onset→bar (×2) | inline formula | `phrase_offset_to_bar` |
| 14 | phrase_writer.py bass | bar_start in loops (×3 textures) | inline formula | `phrase_bar_start` |
| 15 | compose.py | structural offset | inline formula | `phrase_degree_offset` |
| 16 | bourree.yaml | missing upbeat | absent | `upbeat: "1/4"` |

## Invariants preserved

- Non-upbeat genres: anacrusis = 0, all helpers reduce to the old formula. Zero behavioural change.
- `bar_span` still counts the number of bars the schema occupies (including the partial bar).
- `degree_positions` still use 1-based bar numbering within the phrase.
- Layer 4 anchors already handle upbeat correctly via `compute_upbeat_bar_beat`.
- Cadential phrases: handled by `write_cadence` which uses `start_offset` directly, not bar iteration. Anacrusis phrases are never cadential (anacrusis is first phrase, cadences come later).

## Risk

Moderate. Changes offset arithmetic throughout the note generation pipeline. Must verify
with gavotte and bourrée generation plus fault checker. Non-upbeat genres should be
completely unaffected (helpers are identity when anacrusis = 0).

## Status

- [x] phrase_types.py — anacrusis field and 4 helpers added
- [x] phrase_planner.py — cumulative_bar, anacrusis wiring, phrase_duration
- [x] phrase_writer.py — all inline formula replacements (soprano + bass)
- [x] compose.py — structural offset formula
- [x] bourree.yaml — add upbeat field
- [ ] test with gavotte generation
- [ ] test with non-upbeat genre (regression)
