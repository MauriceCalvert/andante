"""Diagnose: are semiquaver-containing durations being generated and scored?"""
from collections import Counter
from motifs.subject_generator import (
    DURATION_TICKS,
    enumerate_durations,
    score_duration_sequence,
    _bar_x2_ticks,
)

bar_ticks = _bar_x2_ticks((4, 4))
all_durs = enumerate_durations(n_bars=2, bar_ticks=bar_ticks)

has_sq = [d for d in all_durs if 0 in d]  # di=0 is semiquaver
no_sq = [d for d in all_durs if 0 not in d]

print(f"Total durations: {len(all_durs)}")
print(f"  With semiquavers: {len(has_sq)}")
print(f"  Without:          {len(no_sq)}")

# Score distribution
sq_scores = sorted([(score_duration_sequence(d), d) for d in has_sq],
                   key=lambda x: x[0], reverse=True)
no_scores = sorted([(score_duration_sequence(d), d) for d in no_sq],
                   key=lambda x: x[0], reverse=True)

print(f"\nTop 5 with semiquavers:")
for sc, d in sq_scores[:5]:
    ticks = [DURATION_TICKS[di] for di in d]
    names = []
    for di in d:
        names.append(['sq', 'q', 'cr', 'mi'][di])
    print(f"  {sc:.4f}  {names}  ticks={ticks}  n={len(d)}")

print(f"\nTop 5 without semiquavers:")
for sc, d in no_scores[:5]:
    ticks = [DURATION_TICKS[di] for di in d]
    names = []
    for di in d:
        names.append(['sq', 'q', 'cr', 'mi'][di])
    print(f"  {sc:.4f}  {names}  ticks={ticks}  n={len(d)}")

# Note count distribution for semiquaver sequences
c = Counter(len(d) for d in has_sq)
print(f"\nSemiquaver sequences by note count:")
for k in sorted(c):
    print(f"  {k:2d} notes: {c[k]}")
