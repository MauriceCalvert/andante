# Result: EPI-2b -- Fragen fallback retry

## Code Changes

**File: `builder/phrase_writer.py` only.**

1. Added `_FRAGEN_MAX_RETRIES: int = 3` at module level (line 36).

2. Replaced the single-attempt fragen block (lines 302-327) with a retry
   loop. On each iteration: request a fragment from the provider, attempt
   realisation, break on success or provider exhaustion, log INFO on each
   failed attempt. The downstream code (partition, label, trace, continue,
   fallback warning) is unchanged.

## Bob's Assessment

### Pass 1: What do I hear?

Bars 28-30 now have two voices moving together in dialogue. The bass
enters on beat 1 with a descending third (G3-E3), and the soprano follows
a beat later with the same figure an octave higher (G4-E4). Through bars
29-30 the voices continue in staggered parallel motion, each tracing the
same descending sequence (G-F#-D then F#-E) with the follower always one
beat behind. The canonic stagger is audible: I hear a leader-follower
texture, not two independent voices.

Previously bars 28-30 had static half-notes moving in lockstep -- two
voices plodding through the same rhythm simultaneously, no dialogue, no
imitative character. That texture stood out against the canonic episodes
elsewhere (bars 6-8, 13-14, 17-19, 24-25) which all had the staggered
two-voice dialogue.

Now all five episodes share the same textural family: one voice leads,
the other follows at a beat's delay, moving through sequential transpositions.
The episode at bars 28-30 fits.

No new faults. No change to any other bars.

### Pass 2: Why does it sound that way?

The fragment at bars 28-30 transposes a 2-note cell (third descent)
through the E minor scale in contrary-direction sequences. The half-beat
stagger creates a canon at the lower octave. The 7-note pattern per voice
fills three bars with continuous motion -- compared to the previous static
half-notes which filled three bars with only 6 attacks total.

## Chaz's Diagnosis

### Retry count and fallback status

Zero retries logged. Zero fallbacks to per-voice rendering. All 5
episodes (bars 6-8, 13-14, 17-19, 24-25, 28-30) rendered via fragen
on the first attempt. The trace confirms paired EPISODE renders at every
episode bar.

The bars 28-30 failure documented in EPI-1 known limitations ("realise_to_notes
returned None in E minor") no longer occurs. Root cause: EPI-2a's catalogue
expansion (309 to 526 cells, including diminished and cross-source fragments)
provided fragments that fit the E minor register on first attempt.

### Fault count

15 faults. Unchanged from EPI-2a (15) and EPI-1 (15). No faults at bars
28-30. All 15 faults are at previously documented locations (bars 13-14
cross-relations, bar 15 tritone, bars 17/21/32/35/38 stretto boundary
leaps and unprepared dissonances, bar 40 parallel rhythm).

### Mechanism verification

The retry loop at `phrase_writer.py:305` iterates up to 4 times
(_FRAGEN_MAX_RETRIES + 1). Each iteration calls `get_fragment` then
`realise_to_notes`. Breaks on: (a) provider returns None (exhausted),
(b) realisation succeeds. Logs INFO on each failed realisation. The
per-voice fallback warning (line 374) remains as final safety net.

### Acceptance criteria

- Zero fragen fallbacks to per-voice rendering: PASS (5/5 episodes via fragen).
- Fault count unchanged: PASS (15 = 15).
- Retry count logged: 0 retries needed with seed 42.

---

Please listen to the MIDI and let me know what you hear.
