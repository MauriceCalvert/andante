from motifs.subject_gen import select_diverse_subjects

results = select_diverse_subjects(n=6, mode='major', metre=(4,4), tonic_midi=60, target_bars=2, verbose=True)
for i, s in enumerate(results):
    print(f'[{i}] {s.head_name} {len(s.scale_indices)}n stretto={len(s.stretto_offsets)} durs={s.durations}')