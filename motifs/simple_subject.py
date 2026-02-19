"""Generate 6 C-major subjects: 9 notes, 2 bars of 4/4, crotchet-to-semiquaver with dotted."""
import os
from itertools import product as iter_product

import motifs.subject_generator as sg
from motifs.subject_generator import (
    MIRROR_PAIRS,
    PITCH_CONTOURS,
    RHYTHM_CONTOURS,
    enumerate_bar_fills,
    enumerate_intervals,
    is_melodically_valid,
    score_intervals,
    score_joint,
    score_rhythm_fit,
)
from motifs.head_generator import degrees_to_midi
from shared.constants import NOTE_NAMES
from shared.midi_writer import write_midi

# ── Override to x4 encoding: crotchet–semiquaver with dotted ────────
sg.X2_TICKS_PER_WHOLE = 32
sg.DURATION_TICKS = (2, 3, 4, 6, 8)
sg.DURATION_NAMES = (
    'semiquaver', 'dotted_semiquaver', 'quaver', 'dotted_quaver', 'crotchet',
)
sg.NUM_DURATIONS = 5
sg.MIN_LAST_DUR_TICKS = 4
sg.MAX_NOTES_PER_BAR = 7
sg.MIN_NOTES_PER_BAR = 2

# ── Fixed parameters ───────────────────────────────────────────────
TARGET_NOTES: int = 9
NUM_INTERVALS: int = TARGET_NOTES - 1
TARGET_BARS: int = 2
TONIC_MIDI: int = 60
MODE: str = "major"
METRE: tuple[int, int] = (4, 4)
BAR_TICKS: int = sg.X2_TICKS_PER_WHOLE * METRE[0] // METRE[1]
TOP_K_IV: int = 300
TOP_K_DUR: int = 150

CONTOUR_CONFIGS: list[tuple[str, str]] = [
    ("arch", "motoric"),
    ("cascade", "busy_brake"),
    ("swoop", "motoric"),
    ("valley", "busy_brake"),
    ("ascent", "motoric"),
    ("dip", "busy_brake"),
]


def _midi_name(midi: int) -> str:
    return f"{NOTE_NAMES[midi % 12]}{midi // 12 - 1}"


def _ivs_to_degrees(ivs: tuple[int, ...]) -> tuple[int, ...]:
    acc: int = 0
    result: list[int] = [0]
    for iv in ivs:
        acc += iv
        result.append(acc)
    return tuple(result)


def main() -> None:
    # ── Enumerate durations, keep only 9-note sequences ─────────
    fills: list[tuple[int, ...]] = enumerate_bar_fills(BAR_TICKS)
    print(f"Bar fills (bar_ticks={BAR_TICKS}): {len(fills)}")
    all_durs: list[tuple[int, ...]] = []
    for combo in iter_product(fills, repeat=TARGET_BARS):
        seq: tuple[int, ...] = sum(combo, ())
        if len(seq) != TARGET_NOTES:
            continue
        if len(set(seq)) < 2:
            continue
        if sg.DURATION_TICKS[seq[-1]] < sg.MIN_LAST_DUR_TICKS:
            continue
        all_durs.append(seq)
    print(f"9-note duration sequences: {len(all_durs)}")
    # ── Enumerate intervals ─────────────────────────────────────
    all_ivs: list[tuple[int, ...]] = enumerate_intervals(NUM_INTERVALS)
    # ── Per-contour: score, pair, select, write MIDI ────────────
    os.makedirs("test_subjects", exist_ok=True)
    for i, (pname, rname) in enumerate(CONTOUR_CONFIGS):
        print(f"\n{'=' * 60}")
        print(f"Subject {i}: {pname} + {rname}")
        print(f"{'=' * 60}")
        # Score durations
        rwp = RHYTHM_CONTOURS[rname]
        dur_fits = [(score_rhythm_fit(d, rwp), d) for d in all_durs]
        dur_fits.sort(key=lambda x: x[0], reverse=True)
        top_durs = dur_fits[:TOP_K_DUR]
        # Score intervals
        pwp = PITCH_CONTOURS[pname]
        mwp = PITCH_CONTOURS[MIRROR_PAIRS[pname]]
        scored_ivs = score_intervals(
            all_ivs,
            num_notes=TARGET_NOTES,
            contour_waypoints=pwp,
            mirror_waypoints_list=mwp,
        )
        scored_ivs.sort(key=lambda x: x[0], reverse=True)
        top_ivs = [(sc, all_ivs[idx]) for sc, idx in scored_ivs[:TOP_K_IV]]
        # Pair and joint-score, keeping only melodically valid
        best_score: float = -1.0
        best_ivs_pick: tuple[int, ...] | None = None
        best_durs_pick: tuple[int, ...] | None = None
        best_midi: tuple[int, ...] | None = None
        for iv_sc, ivs in top_ivs:
            degrees = _ivs_to_degrees(ivs)
            midi = degrees_to_midi(degrees=degrees, tonic_midi=TONIC_MIDI, mode=MODE)
            if not is_melodically_valid(midi):
                continue
            for dur_sc, durs in top_durs:
                combined = (
                    0.4 * iv_sc
                    + 0.3 * dur_sc
                    + 0.3 * score_joint(ivs, durs, BAR_TICKS)
                )
                if combined > best_score:
                    best_score = combined
                    best_ivs_pick = ivs
                    best_durs_pick = durs
                    best_midi = midi
        if best_ivs_pick is None or best_durs_pick is None or best_midi is None:
            print("  No valid subject found, skipping")
            continue
        durations = tuple(
            sg.DURATION_TICKS[d] / sg.X2_TICKS_PER_WHOLE for d in best_durs_pick
        )
        pitch_names = [_midi_name(m) for m in best_midi]
        dur_names = [sg.DURATION_NAMES[d] for d in best_durs_pick]
        degrees = _ivs_to_degrees(best_ivs_pick)
        print(f"  Score:     {best_score:.4f}")
        print(f"  Degrees:   {list(degrees)}")
        print(f"  Pitches:   {' '.join(pitch_names)}")
        print(f"  Durations: {dur_names}")
        midi_path = f"test_subjects/subject_{i:02d}_{pname}_{rname}.midi"
        write_midi(
            path=midi_path,
            pitches=list(best_midi),
            durations=list(durations),
            tempo=100,
            time_signature=METRE,
        )
        print(f"  MIDI:      {midi_path}")


if __name__ == "__main__":
    main()
