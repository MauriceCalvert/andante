from motifs.subject_gen.selector import select_diverse_subjects
results = select_diverse_subjects(n=6, mode='major', metre=(4,4), tonic_midi=72, target_bars=2, note_counts=(12,), verbose=True)