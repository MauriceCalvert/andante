"""Test all 6 contours to see stretto yield vs arch-only."""
from motifs.subject_generator import (
    generate_pitch_sequences, interpolate_contour, PITCH_CONTOURS,
    score_pitch_sequence, score_duration_sequence, score_pairing,
    enumerate_durations, is_melodically_valid, _bar_x2_ticks,
    DURATION_TICKS, TOP_K_PITCH, TOP_K_DURATIONS, TOP_K_PAIRED,
)
from motifs.head_generator import degrees_to_midi
from motifs.stretto_constraints import evaluate_all_offsets, score_stretto

bar_ticks = _bar_x2_ticks((4, 4))
all_durs = enumerate_durations(n_bars=2, bar_ticks=bar_ticks)
durs_by_count = {}
for d in all_durs:
    durs_by_count.setdefault(len(d), []).append(d)

ranked_durs = {}
for nc, seqs in durs_by_count.items():
    scored = [(score_duration_sequence(d), d) for d in seqs]
    scored.sort(key=lambda x: x[0], reverse=True)
    ranked_durs[nc] = scored[:TOP_K_DURATIONS]

stretto_viable = 0
total_candidates = 0
best_with_stretto = None
best_stretto_score = -1

for nc in sorted(durs_by_count.keys()):
    for pname in PITCH_CONTOURS:
        targets = interpolate_contour(PITCH_CONTOURS[pname], nc)
        sequences = generate_pitch_sequences(nc, targets)
        if not sequences:
            continue
        scored_pitch = [(score_pitch_sequence(s, targets), s) for s in sequences]
        scored_pitch.sort(key=lambda x: x[0], reverse=True)
        top_pitch = scored_pitch[:TOP_K_PITCH]
        for p_sc, ivs in top_pitch:
            if nc not in ranked_durs:
                continue
            for d_sc, durs in ranked_durs[nc]:
                pair_sc = score_pairing(ivs, durs)
                if pair_sc < 0:
                    continue
                degs = (0,) + tuple(sum(ivs[:i + 1]) for i in range(len(ivs)))
                midi = degrees_to_midi(degrees=degs, tonic_midi=60, mode='major')
                if not is_melodically_valid(midi):
                    continue
                dur_slots = tuple(DURATION_TICKS[d] for d in durs)
                total_slots = sum(dur_slots)
                offsets = evaluate_all_offsets(
                    degrees=degs, dur_slots=dur_slots, metre=(4, 4),
                )
                viable = [r for r in offsets if r.viable]
                total_candidates += 1
                if viable:
                    stretto_viable += 1
                    st_sc = score_stretto(
                        offset_results=offsets, total_slots=total_slots,
                    )
                    combined = 0.4 * p_sc + 0.3 * d_sc + 0.3 * pair_sc
                    final = 0.60 * combined + 0.40 * st_sc
                    sq = sum(1 for d in durs if DURATION_TICKS[d] == 1)
                    if final > best_stretto_score:
                        best_stretto_score = final
                        best_with_stretto = (
                            nc, pname, degs, durs, sq,
                            len(viable), final, combined, st_sc,
                        )
    print(f"  {nc}n done: {total_candidates} candidates, {stretto_viable} with stretto")

print(f"\nTotal: {total_candidates}, stretto viable: {stretto_viable}")
if best_with_stretto:
    nc, pn, degs, durs, sq, nv, fin, comb, st = best_with_stretto
    dur_ticks = tuple(DURATION_TICKS[d] for d in durs)
    dur_frac = tuple(t / 16 for t in dur_ticks)
    print(
        f"Best stretto: {nc}n {pn} sq={sq} stretto={nv} "
        f"final={fin:.4f} combined={comb:.4f} stretto_sc={st:.4f}"
    )
    print(f"  degrees={degs}")
    print(f"  durs={dur_frac}")
else:
    print("No stretto-viable candidates found.")
