"""Diagnose stretto failures for longer subjects — semitone space."""
from motifs.subject_generator import (
    generate_pitch_sequences, score_pitch_sequence,
    score_duration_sequence, enumerate_durations,
    is_melodically_valid, _bar_x2_ticks, DURATION_TICKS,
)
from motifs.head_generator import degrees_to_midi
from motifs.stretto_constraints import (
    evaluate_offset, derive_check_points,
)
from shared.constants import (
    CONSONANT_INTERVALS, CONSONANT_INTERVALS_ABOVE_BASS, TRITONE_SEMITONES,
)

bar_ticks = _bar_x2_ticks((4, 4))
all_durs = enumerate_durations(n_bars=2, bar_ticks=bar_ticks)
durs_8 = [d for d in all_durs if len(d) == 8]
scored_durs = [(score_duration_sequence(d), d) for d in durs_8]
scored_durs.sort(key=lambda x: x[0], reverse=True)
best_dur = scored_durs[0][1]

sequences = generate_pitch_sequences(8)
scored_pitch = [(score_pitch_sequence(s), s) for s in sequences]
scored_pitch.sort(key=lambda x: x[0], reverse=True)

total = len(scored_pitch)
valid = sum(1 for _, ivs in scored_pitch
            if is_melodically_valid(
                degrees_to_midi(
                    degrees=(0,) + tuple(sum(ivs[:i+1]) for i in range(len(ivs))),
                    tonic_midi=60, mode='major')))
print(f"8n: {total} total, {valid} melodically valid ({100*valid/total:.1f}%)")

shown = 0
for sc, ivs in scored_pitch:
    degs = (0,) + tuple(sum(ivs[:i + 1]) for i in range(len(ivs)))
    midi = degrees_to_midi(degrees=degs, tonic_midi=60, mode='major')
    if not is_melodically_valid(midi):
        continue
    dur_slots = tuple(DURATION_TICKS[d] for d in best_dur)
    total_slots = sum(dur_slots)
    dur_frac = tuple(t / 16 for t in dur_slots)
    print(f"\n#{shown} degs={degs} shape={sc:.3f}")
    print(f"  midi={midi} durs={dur_frac}")
    viable_count = 0
    for offset in range(1, total_slots // 2 + 1):
        result = evaluate_offset(
            midi=midi, dur_slots=dur_slots,
            offset_slots=offset, metre=(4, 4),
        )
        if result.viable:
            viable_count += 1
            print(f"  offset={offset:2d} VIABLE  consonant={result.consonant_count}/{result.total_count} cost={result.dissonance_cost}")
        else:
            checks = derive_check_points(
                dur_slots=dur_slots, offset_slots=offset, metre=(4, 4),
            )
            fails = []
            for ck in checks:
                st = abs(midi[ck.leader_idx] - midi[ck.follower_idx]) % 12
                if ck.is_strong and st not in CONSONANT_INTERVALS_ABOVE_BASS:
                    fails.append(f"strong({ck.leader_idx}v{ck.follower_idx}:st={st})")
                elif not ck.is_strong and st == TRITONE_SEMITONES:
                    fails.append(f"tritone({ck.leader_idx}v{ck.follower_idx})")
            print(f"  offset={offset:2d} FAIL    {' '.join(fails)}")
    print(f"  => {viable_count} viable offsets")
    shown += 1
    if shown >= 5:
        break
