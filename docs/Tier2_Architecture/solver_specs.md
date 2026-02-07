# Solver Specifications

**Status: HISTORICAL.** The greedy solver (L8 Melodic) has been replaced by phrase-level generation in `builder/phrase_writer.py`. See `architecture.md` (v2.0.0) for the current design.

The content below is retained as historical reference.

---

Implementation details for the greedy solver formerly used in L8 Melodic. These are tuning parameters, not architectural decisions.

## Motive weighting (cost function)

| Motion type | Weight | Description |
|-------------|--------|-------------|
| Stepwise (diatonic 2nd) | 0.2 | Preferred — 80% of semiquaver motion |
| Skip (3rd) | 0.4 | Acceptable |
| Leap (4th–5th) | 0.8 | Penalised |
| Large leap (6th+) | 1.5 | Strongly penalised |

## Tessitura cost

Distance from voice median is penalised linearly. Each semitone away from the median adds cost proportional to the distance.

## Repetition penalties

| Pattern | Cost | Description |
|---------|------|-------------|
| Consecutive repeat | 0.3 | Same pitch twice in a row |
| Oscillation (A-B-A) | 0.5 | Immediate return to previous pitch |

## Solver determinism

| Rule | Specification |
|------|---------------|
| Tie-breaking | If multiple solutions have equal cost, select lexicographically first (lowest MIDI sum at each time slot, left to right) |
| Search order | Enumerate soprano before bass, bar 1 before bar 2, beat 1 before beat 2 |
| Randomisation | Forbidden — no random seed, no shuffling |
| First valid | Not acceptable — must complete enumeration to find true minimum cost |

These rules ensure identical output across different solver implementations.
