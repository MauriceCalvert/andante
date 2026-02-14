"""Measure strong-beat dissonance quality from .note files.

Classifies each strong-beat dissonance as:
- suspension: same pitch as previous note, resolved down by step
- accented passing tone: approached AND left by step
- unprepared: everything else (the actual fault)
"""
import csv
import sys
from pathlib import Path

CONSONANT = frozenset({0, 3, 4, 5, 7, 8, 9})
MAX_STEP = 2  # semitones: a major second


def measure_file(path: Path) -> None:
    """Print dissonance quality stats for one .note file."""
    metre = "4/4"
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("## time:"):
                metre = line.split(":")[1].strip()
            if not line.startswith("#"):
                break
    beats_per_bar = int(metre.split("/")[0])
    # Read notes per voice, sorted by offset
    soprano_notes: list[tuple[float, int, float]] = []  # (offset, midi, beat)
    bass_notes: list[tuple[float, int, float]] = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(
            (line for line in f if not line.startswith("#")),
        )
        for row in reader:
            offset = float(row["offset"])
            midi = int(row["midinote"])
            beat = float(row["beat"])
            track = row["track"]
            if track == "0":
                soprano_notes.append((offset, midi, beat))
            elif track == "3":
                bass_notes.append((offset, midi, beat))
    soprano_notes.sort()
    bass_notes.sort()
    # Index by offset for pairing
    sop_by_off: dict[float, int] = {o: m for o, m, _ in soprano_notes}
    bass_by_off: dict[float, int] = {o: m for o, m, _ in bass_notes}
    sop_beats: dict[float, float] = {o: bt for o, _, bt in soprano_notes}
    # Build predecessor maps (previous note in same voice)
    sop_prev: dict[float, int | None] = {}
    prev: int | None = None
    for o, m, _ in soprano_notes:
        sop_prev[o] = prev
        prev = m
    bass_prev: dict[float, int | None] = {}
    prev = None
    for o, m, _ in bass_notes:
        bass_prev[o] = prev
        prev = m
    # Build successor maps (next note in same voice)
    sop_next: dict[float, int | None] = {}
    for i, (o, m, _) in enumerate(soprano_notes):
        sop_next[o] = soprano_notes[i + 1][1] if i + 1 < len(soprano_notes) else None
    bass_next: dict[float, int | None] = {}
    for i, (o, m, _) in enumerate(bass_notes):
        bass_next[o] = bass_notes[i + 1][1] if i + 1 < len(bass_notes) else None
    # Find shared onsets
    shared = sorted(set(sop_by_off) & set(bass_by_off))
    strong_consonant = 0
    strong_suspension = 0
    strong_passing = 0
    strong_unprepared = 0
    weak_consonant = 0
    weak_dissonant = 0
    details: list[str] = []
    for off in shared:
        s_midi = sop_by_off[off]
        b_midi = bass_by_off[off]
        interval_class = abs(s_midi - b_midi) % 12
        is_cons = interval_class in CONSONANT
        beat = sop_beats[off]
        half_bar = 1.0 + beats_per_bar / 2.0
        is_strong = abs(beat - 1.0) < 0.01 or abs(beat - half_bar) < 0.01
        if not is_strong:
            if is_cons:
                weak_consonant += 1
            else:
                weak_dissonant += 1
            continue
        if is_cons:
            strong_consonant += 1
            continue
        # Dissonance on strong beat — classify by both voices
        # Check soprano: is it a suspension, passing tone, or unprepared?
        s_prev = sop_prev[off]
        s_next = sop_next[off]
        b_prev = bass_prev[off]
        b_next = bass_next[off]
        # Suspension: soprano held from previous, resolves down by step
        s_is_suspension = (
            s_prev is not None
            and s_prev == s_midi
            and s_next is not None
            and 0 < s_midi - s_next <= MAX_STEP
        )
        # Bass suspension: bass held from previous, resolves down by step
        b_is_suspension = (
            b_prev is not None
            and b_prev == b_midi
            and b_next is not None
            and 0 < b_midi - b_next <= MAX_STEP
        )
        # Accented passing: approached and left by step in same direction
        s_is_passing = (
            s_prev is not None
            and s_next is not None
            and abs(s_midi - s_prev) <= MAX_STEP
            and abs(s_next - s_midi) <= MAX_STEP
            and s_prev != s_midi
            and s_next != s_midi
        )
        b_is_passing = (
            b_prev is not None
            and b_next is not None
            and abs(b_midi - b_prev) <= MAX_STEP
            and abs(b_next - b_midi) <= MAX_STEP
            and b_prev != b_midi
            and b_next != b_midi
        )
        is_tritone: bool = interval_class == 6
        if not is_tritone and (s_is_suspension or b_is_suspension):
            strong_suspension += 1
            label = "susp"
        elif not is_tritone and (s_is_passing or b_is_passing):
            strong_passing += 1
            label = "pass"
        else:
            strong_unprepared += 1
            label = "UNPR"
            # Show detail for unprepared
            bar = int(off) + 1
            details.append(
                f"  bar {bar} beat {beat}: S={s_midi} B={b_midi} "
                f"ic={interval_class} "
                f"(S prev={s_prev} next={s_next}, B prev={b_prev} next={b_next})"
            )
    strong_total = strong_consonant + strong_suspension + strong_passing + strong_unprepared
    name = path.stem
    print(f"\n{name}  ({metre})")
    if strong_total > 0:
        print(f"  Strong beats: {strong_total} total")
        print(f"    Consonant:       {strong_consonant:3d}  ({100.0 * strong_consonant / strong_total:.1f}%)")
        print(f"    Suspension:      {strong_suspension:3d}  ({100.0 * strong_suspension / strong_total:.1f}%)")
        print(f"    Accented pass:   {strong_passing:3d}  ({100.0 * strong_passing / strong_total:.1f}%)")
        print(f"    Unprepared:      {strong_unprepared:3d}  ({100.0 * strong_unprepared / strong_total:.1f}%)")
        good = strong_consonant + strong_suspension + strong_passing
        print(f"    Controlled:      {good:3d}  ({100.0 * good / strong_total:.1f}%)  <- target >90%")
    if details:
        print(f"  Unprepared detail:")
        for d in details:
            print(d)
    weak_total = weak_consonant + weak_dissonant
    if weak_total > 0:
        print(f"  Weak beats: {weak_consonant}/{weak_total} consonant ({100.0 * weak_consonant / weak_total:.1f}%)")


SCRIPT_DIR: Path = Path(__file__).resolve().parent
PROJECT_DIR: Path = SCRIPT_DIR.parent
DEFAULT_OUTPUT_DIR: Path = PROJECT_DIR / "output"


def main() -> None:
    """Measure dissonance quality for .note files."""
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT_DIR
    if path.is_dir():
        files = sorted(path.glob("*.note"))
        if not files:
            print(f"No .note files in {path}")
            sys.exit(1)
        for f in files:
            measure_file(path=f)
    else:
        measure_file(path=path)


if __name__ == "__main__":
    main()
