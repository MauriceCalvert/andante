"""
subject_render.py — Render 8 subjects from 4 pitch × 4 rhythm contours.

Each pitch contour used twice, each rhythm contour used twice.
Every subject has a unique melody and unique rhythm.
"""

from shared.midi_writer import SimpleNote, write_midi_notes

from subject_contours import PITCH_CONTOURS, RHYTHM_CONTOURS, score_rhythm_fit
from subject_generator import DURATION_NAMES, DURATION_TICKS, enumerate_durations, enumerate_intervals
from subject_scorer import display_subject, score_intervals, score_joint

# ── Rendering parameters ────────────────────────────────────────────
C_MAJOR_SCALE = (60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79, 81, 83, 84)
#                C4  D4  E4  F4  G4  A4  B4  C5  D5  E5  F5  G5  A5  B5  C6
START_DEGREE = 7     # C5
TICKS_PER_BAR = 16   # 4 crotchets in x2 encoding
TICKS_PER_WHOLE = 32 # whole note in x2 encoding
REST_BARS = 1
OUTPUT_PATH = 'subjects_by_contour.mid'


def degree_to_midi(degree: int) -> int:
    """Convert scale degree offset to MIDI pitch."""
    idx = START_DEGREE + degree
    assert 0 <= idx < len(C_MAJOR_SCALE), f"degree {degree} out of range"
    return C_MAJOR_SCALE[idx]


def run() -> None:
    """Full pipeline: 4 pitch contours × 4 rhythm contours → 8 subjects."""
    all_ivs = enumerate_intervals()
    all_durs = enumerate_durations()
    # Score intervals per pitch contour → best 2 melodies each
    pitch_names = list(PITCH_CONTOURS.keys())
    melodies = {}  # pitch_name → list of (score, ivs)
    for pname in pitch_names:
        pwp = PITCH_CONTOURS[pname]
        print(f"\nPitch contour: {pname}  {pwp}")
        iv_scores = score_intervals(all_ivs, contour_waypoints=pwp)
        iv_scores.sort(key=lambda x: x[0], reverse=True)
        # Pick 2 diverse melodies (Hamming >= 4)
        picks = []
        for sc, idx in iv_scores:
            ivs = all_ivs[idx]
            if picks and sum(1 for a, b in zip(ivs, picks[0][1]) if a != b) < 4:
                continue
            picks.append((sc, ivs))
            if len(picks) >= 2:
                break
        melodies[pname] = picks
        for i, (sc, ivs) in enumerate(picks):
            pitches = [0]
            for iv in ivs:
                pitches.append(pitches[-1] + iv)
            print(f"  Melody {i+1}: {list(ivs)}  pitches={pitches}  score={sc:.4f}")
    # Score durations per rhythm contour → best 2 rhythms each
    rhythm_names = list(RHYTHM_CONTOURS.keys())
    rhythms = {}  # rhythm_name → list of (score, durs)
    for rname in rhythm_names:
        rwp = RHYTHM_CONTOURS[rname]
        print(f"\nRhythm contour: {rname}  {rwp}")
        best = []
        for dur_seq in all_durs:
            fit = score_rhythm_fit(dur_seq, rwp)
            best.append((fit, dur_seq))
        best.sort(key=lambda x: x[0], reverse=True)
        # Pick 2 diverse rhythms (Hamming >= 3)
        picks = []
        for sc, durs in best:
            if picks and sum(1 for a, b in zip(durs, picks[0][1]) if a != b) < 3:
                continue
            picks.append((sc, durs))
            if len(picks) >= 2:
                break
        rhythms[rname] = picks
        for i, (sc, durs) in enumerate(picks):
            names = [DURATION_NAMES[d] for d in durs]
            ticks = [DURATION_TICKS[d] for d in durs]
            print(f"  Rhythm {i+1}: {names}  ticks={ticks} total={sum(ticks)}  fit={sc:.4f}")
    # 4 pitch × 2 rhythm = 8 subjects, each pitch gets both rhythms
    pairs = []
    for pi in range(len(pitch_names)):
        for ri in range(len(rhythm_names)):
            pairs.append((pi, ri % 2, ri, 0))
    all_subjects = []
    print(f"\n{'=' * 60}")
    print(f"8 SUBJECTS")
    print(f"{'=' * 60}")
    for pi, mi, ri, di in pairs:
        pname = pitch_names[pi]
        rname = rhythm_names[ri]
        iv_score, ivs = melodies[pname][mi]
        dur_score, durs = rhythms[rname][di]
        j_score = score_joint(ivs, durs)
        combined = 0.4 * iv_score + 0.3 * dur_score + 0.3 * j_score
        rank = len(all_subjects)
        print(f"\n--- #{rank+1}  pitch={pname}[{mi+1}]  rhythm={rname}[{di+1}] ---")
        display_subject(rank, combined, ivs, durs)
        all_subjects.append((f"{pname}+{rname}", combined, ivs, durs))
    # Render to MIDI
    notes = []
    offset = 0.0
    rest_whole = REST_BARS * TICKS_PER_BAR / TICKS_PER_WHOLE
    for i, (label, score, ivs, durs) in enumerate(all_subjects):
        if i > 0:
            offset += rest_whole
        pitches_deg = [0]
        for iv in ivs:
            pitches_deg.append(pitches_deg[-1] + iv)
        for j in range(len(pitches_deg)):
            midi_pitch = degree_to_midi(pitches_deg[j])
            dur_ticks = DURATION_TICKS[durs[j]]
            dur_whole = dur_ticks / TICKS_PER_WHOLE
            notes.append(SimpleNote(
                pitch=midi_pitch,
                offset=offset,
                duration=dur_whole,
            ))
            offset += dur_whole
    ok = write_midi_notes(
        path=OUTPUT_PATH,
        notes=notes,
        tempo=100,
        tonic='C',
        mode='major',
    )
    n = len(all_subjects)
    if ok:
        print(f"\nWrote {OUTPUT_PATH}: {n} subjects ({len(notes)} notes)")
    else:
        print("Failed to write MIDI")


if __name__ == '__main__':
    run()
