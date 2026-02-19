"""Quick multi-seed test to see if any seeds produce semiquaver subjects."""
from motifs.subject_generator import select_subject

for seed in range(10):
    result = select_subject(
        mode="major",
        metre=(4, 4),
        tonic_midi=60,
        target_bars=2,
        seed=seed,
        verbose=False,
    )
    sq = sum(1 for d in result.durations if d == 1/16)
    n = len(result.scale_indices)
    stretto = len(result.stretto_offsets)
    print(f"seed={seed:2d}  {n:2d}n  sq={sq}  stretto={stretto}  "
          f"score={result.score:.4f}  durs={result.durations}")
