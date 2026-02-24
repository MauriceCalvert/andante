# Result: BUG-1 — Fix _fit_shift key destruction

## Status: Done

## Change

`builder/imitation.py` — `_fit_shift` fallback branch replaced.

**Before:** when no octave multiple fit in `[shift_lo, shift_hi]`, returned the
non-octave shift closest to zero (could be +1, +2 … semitones), turning the
subject/CS/answer into a chromatic transposition in the wrong key.

**After:** always picks the octave multiple (k×12) nearest the midpoint of
`[shift_lo, shift_hi]`. Three candidates (k_near−1, k_near, k_near+1) are
evaluated; ties broken by proximity to zero. A WARNING is logged when the
fallback fires.

Also added `import logging` and module-level `logger = logging.getLogger(__name__)`.

## Expected outcome

Bars 5–6 soprano (A-minor subject entry): A4 B4 C5 D5 B4 A4 — all diatonic
in A minor. No Bb/Db/Eb/Ab accidentals. The +1 semitone shift that produced
the Bb-minor colour is replaced by the nearest octave multiple, accepting the
minor range overflow permitted by L003.

## Files changed

- `builder/imitation.py`
