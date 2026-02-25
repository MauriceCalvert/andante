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
#  Note-name parsing
# ═══════════════════════════════════════════════════════════════════

_NOTE_TO_CHROMA: dict[str, int] = {
    "c": 0, "c#": 1, "db": 1,
    "d": 2, "d#": 3, "eb": 3,
    "e": 4, "fb": 4,
    "f": 5, "e#": 5, "f#": 6, "gb": 6,
    "g": 7, "g#": 8, "ab": 8,
    "a": 9, "a#": 10, "bb": 10,
    "b": 11, "cb": 11,
}


def parse_note_name(name: str) -> int:
    """Parse a note name like 'c5' or 'f#4' to MIDI number."""
    name = name.strip().lower()
    # Split into pitch class and octave
    for i in range(1, len(name)):
        if name[i].isdigit() or (name[i] == "-" and i + 1 < len(name)):
            pitch_class: str = name[:i]
            octave: int = int(name[i:])
            break
    else:
        raise ValueError(f"Cannot parse note name: {name!r}")
    assert pitch_class in _NOTE_TO_CHROMA, (
        f"Unknown pitch class: {pitch_class!r} in {name!r}"
    )
    return (octave + 1) * 12 + _NOTE_TO_CHROMA[pitch_class]


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
    parser.add_argument("--tonic", type=str, default="60",
                        help="Tonic as MIDI number or note name, e.g. 60 or c4")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--notes", type=str, default=10,
                        help="Note counts, e.g. '9,10' (default: all)")
    parser.add_argument("--pitches", type=str, default=None,
                        help="Fixed pitches, e.g. 'c5,d5,e5,f5' (bypasses pitch generation)")
    parser.add_argument("--contour", type=str, default=None,
                        choices=["arch", "valley", "swoop", "dip",
                                 "ascending", "descending", "zigzag"])
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    tonic_midi: int = int(args.tonic) if args.tonic.isdigit() else parse_note_name(args.tonic)
    note_counts = None
    if args.notes:
        note_counts = tuple(int(x) for x in args.notes.split(","))
    fixed_midi = None
    if args.pitches:
        fixed_midi = tuple(parse_note_name(n) for n in args.pitches.split(","))
        note_counts = (len(fixed_midi),)
    result = select_subject(
        mode=args.mode,
        metre=tuple(args.metre),
        tonic_midi=tonic_midi,
        target_bars=args.bars,
        pitch_contour=args.contour,
        note_counts=note_counts,
        fixed_midi=fixed_midi,
        seed=args.seed,
        verbose=args.verbose,
    )
    print(f"\nResult: {len(result.scale_indices)}n, score={result.score:.4f}")
    print(f"  Degrees: {result.scale_indices}")
    print(f"  MIDI:    {result.midi_pitches}")
    print(f"  Durs:    {result.durations}")
