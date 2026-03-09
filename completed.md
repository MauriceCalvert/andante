## Technique 5 — Harmonic rhythm acceleration (2026-03-09 T2)

Implemented `technique_5` in `builder/techniques.py` and
`_generate_accelerating` in `builder/episode_dialogue.py`. Final
ACCEL_BAR_COUNT=2 bars emit two half-fragments per bar at midpoint/endpoint
transposition levels, doubling rhythmic density (20 vs 11 events/bar).

Added `ACCEL_BAR_COUNT` constant, `"harmonic_rhythm_acceleration"` dispatch
entry, and `invention_t5_demo.brief`.

**Known**: sub-iterations land on same pitch when register trajectory is
small (1 diatonic step over 6 bars). Bars 8-9 are pitch-identical. Rhythmic
acceleration is audible; harmonic acceleration requires wider register plan
or future harmonic grid (EPI-7).

## Technique 4 — Circle-of-fifths sequential episode (2026-03-09)

Implemented `technique_4` in `builder/techniques.py`. Cumulative schedule of
−4 diatonic degrees per bar passed to `_generate_fallback`. The fifths
transposition is structurally correct and audible in bars 4–6 of the demo
(A4→D4→G3 downbeats).

**Actual limitation**: range overrun begins at bar 4 beat 4 (first bar of the
episode), not bar 7. Starting from degree 6 (A4), 6 iterations of −4 degrees
= 24-degree total descent, roughly 3.5 octaves. No starting position in the
soprano range survives this. The demo is unlistenable beyond the first two
episode bars. The circle-of-fifths transposition interval is correct; the
start-degree selection problem is EPI-7 scope.

**Accepted as known limitation.** Not re-attempted. EPI-7 (planner episode-type
selection) will select start_degree to keep the full sequence in range before
wiring this technique into production.

**Files**: `builder/techniques.py`, `scripts/yaml_validator.py`,
`briefs/builder/invention_cof_demo.brief`.

