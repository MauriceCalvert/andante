"""Test plan-driven subject selection."""
from motifs.subject_gen.planned_selector import select_planned_subjects

results = select_planned_subjects(
    n=10,
    mode="major",
    metre=(4, 4),
    tonic_midi=60,
    target_bars=2,
    note_counts=tuple(range(10, 15)),
    verbose=True,
)
print(f"\n  {len(results)} subjects selected\n")
for i, s in enumerate(results):
    dur_ticks = [round(d * 16) for d in s.durations]
    has_sq = any(t == 1 for t in dur_ticks)
    ivs = tuple(
        s.scale_indices[j + 1] - s.scale_indices[j]
        for j in range(len(s.scale_indices) - 1)
    )
    leaps = [iv for iv in ivs if abs(iv) >= 3]
    steps = sum(1 for iv in ivs if abs(iv) <= 1)
    n_durs = len(set(s.durations))
    sq_label = " [SQ]" if has_sq else ""
    print(f"  [{i:02d}] {s.head_name:12s} {len(s.scale_indices):2d}n  "
          f"leaps={leaps!s:20s} steps={steps}/{len(ivs)}  "
          f"durs={n_durs}distinct  degrees={s.scale_indices}{sq_label}")
