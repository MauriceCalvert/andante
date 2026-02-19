"""Check: do semiquaver-containing candidates make it through stage 4?"""
import time
from motifs.subject_generator import (
    DURATION_TICKS, PITCH_CONTOURS, TOP_K_PITCH, TOP_K_DURATIONS, TOP_K_PAIRED,
    enumerate_durations, score_duration_sequence, _bar_x2_ticks,
    generate_pitch_sequences, interpolate_contour, score_pitch_sequence,
    score_pairing, is_melodically_valid,
)
from motifs.head_generator import degrees_to_midi
from motifs.stretto_constraints import evaluate_all_offsets, score_stretto

metre = (4, 4)
bar_ticks = _bar_x2_ticks(metre)
tonic_midi = 60
mode = "major"

all_durs = enumerate_durations(n_bars=2, bar_ticks=bar_ticks)
durs_by_count = {}
for d in all_durs:
    durs_by_count.setdefault(len(d), []).append(d)

ranked_durs = {}
for nc, seqs in durs_by_count.items():
    scored = [(score_duration_sequence(d), d) for d in seqs]
    scored.sort(key=lambda x: x[0], reverse=True)
    ranked_durs[nc] = scored[:TOP_K_DURATIONS]

# Check one note count that has semiquavers: 8n
for nc in [8, 9, 10]:
    # How many of the top-k durations contain semiquavers?
    top_durs = ranked_durs.get(nc, [])
    sq_durs = [(sc, d) for sc, d in top_durs if 0 in d]
    print(f"{nc}n: {len(top_durs)} top durations, {len(sq_durs)} with semiquavers")
    if sq_durs:
        for sc, d in sq_durs[:3]:
            names = ['sq' if di == 0 else 'q' if di == 1 else 'cr' if di == 2 else 'mi' for di in d]
            print(f"  {sc:.4f} {names}")

    # Generate pitch and pair
    targets = interpolate_contour(PITCH_CONTOURS['arch'], nc)
    sequences = generate_pitch_sequences(nc, targets)
    if not sequences:
        print(f"  No pitch sequences")
        continue

    scored_pitch = sorted(
        [(score_pitch_sequence(s, targets), s) for s in sequences],
        key=lambda x: x[0], reverse=True,
    )[:TOP_K_PITCH]

    # Pair with semiquaver durations only
    sq_candidates = 0
    for p_sc, ivs in scored_pitch:
        for d_sc, durs in sq_durs:
            pair_sc = score_pairing(ivs, durs)
            if pair_sc < 0:
                continue
            degs = (0,) + tuple(sum(ivs[:i+1]) for i in range(len(ivs)))
            midi = degrees_to_midi(degrees=degs, tonic_midi=tonic_midi, mode=mode)
            if not is_melodically_valid(midi):
                continue
            sq_candidates += 1
    print(f"  Semiquaver candidates after pairing+validation: {sq_candidates}")
    print()
