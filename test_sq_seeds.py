"""Quick multi-seed test with per-stage timing."""
import time
from motifs.subject_generator import select_subject

t_total = time.time()
for seed in range(10):
    t0 = time.time()
    result = select_subject(
        mode="major",
        metre=(4, 4),
        tonic_midi=60,
        target_bars=2,
        seed=seed,
        verbose=(seed == 0),
    )
    dt = time.time() - t0
    sq = sum(1 for d in result.durations if d == 1/16)
    n = len(result.scale_indices)
    stretto = len(result.stretto_offsets)
    print(f"seed={seed:2d}  {n:2d}n  sq={sq}  stretto={stretto}  "
          f"score={result.score:.4f}  {dt:.1f}s  durs={result.durations}")
print(f"\nTotal: {time.time() - t_total:.1f}s")
