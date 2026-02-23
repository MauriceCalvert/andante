"""Subject generator — CLI wrapper for subject_gen package.

Generates pitch sequences by exhaustive walk (no contour band), scores
them for dramatic shape, assigns the best-scoring duration sequence of
matching length, then evaluates stretto potential at every possible offset.

Duration sequences are assembled from per-bar fills so that no note
crosses a bar boundary.  Note counts vary with the fills chosen.

Diversity selection: select_diverse_subjects picks N subjects from the
full scored pool by greedy max-min Hamming distance, ensuring each
subject is genuinely different from the others.
"""

from motifs.subject_gen import GeneratedSubject, select_subject
from motifs.subject_gen.constants import DURATION_NAMES, DURATION_TICKS


# ═══════════════════════════════════════════════════════════════════
#  Display helpers
# ═══════════════════════════════════════════════════════════════════

def display_subject(rank: int, score: float, ivs: tuple, durs: tuple) -> None:
    """Pretty-print a ranked subject."""
    pitches = [0]
    for iv in ivs:
        pitches.append(pitches[-1] + iv)
    dur_names = [DURATION_NAMES[d] for d in durs]
    dur_ticks = [DURATION_TICKS[d] for d in durs]
    print(f"#{rank + 1}  score={score:.4f}")
    print(f"  Pitches:    {pitches}")
    print(f"  Intervals:  {list(ivs)}")
    print(f"  Rhythm:     {dur_names}")
    print(f"  Ticks:      {dur_ticks}  total={sum(dur_ticks)}")
    print()


def decode_subject(intervals: tuple, durations: tuple) -> None:
    """Print a human-readable subject."""
    pitches = [0]
    for iv in intervals:
        pitches.append(pitches[-1] + iv)
    print(f"  Pitches:   {pitches}")
    print(f"  Intervals: {list(intervals)}")
    print(f"  Durations: {[DURATION_NAMES[d] for d in durations]}")
    print(f"  Ticks:     {[DURATION_TICKS[d] for d in durations]}")


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate a fugue subject")
    parser.add_argument("--mode", type=str, default="major",
                        choices=["major", "minor"])
    parser.add_argument("--metre", type=int, nargs=2, default=[4, 4],
                        metavar=("NUM", "DEN"))
    parser.add_argument("--bars", type=int, default=2)
    parser.add_argument("--tonic", type=int, default=60)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--notes", type=str, default=None,
                        help="Note counts, e.g. '9,10' (default: all)")
    parser.add_argument("--contour", type=str, default=None,
                        choices=["arch", "valley", "swoop", "dip",
                                 "ascending", "descending", "zigzag"])
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    note_counts = None
    if args.notes:
        note_counts = tuple(int(x) for x in args.notes.split(","))
    result = select_subject(
        mode=args.mode,
        metre=tuple(args.metre),
        tonic_midi=args.tonic,
        target_bars=args.bars,
        pitch_contour=args.contour,
        note_counts=note_counts,
        seed=args.seed,
        verbose=args.verbose,
    )
    print(f"\nResult: {len(result.scale_indices)}n, score={result.score:.4f}")
    print(f"  Degrees: {result.scale_indices}")
    print(f"  MIDI:    {result.midi_pitches}")
    print(f"  Durs:    {result.durations}")
