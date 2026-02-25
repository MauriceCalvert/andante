"""Profile where time goes in select_diverse (cached run)."""
import time

from motifs.head_generator import degrees_to_midi
from motifs.subject_gen.cache import _load_cache
from motifs.subject_gen.constants import DURATION_TICKS, MIN_STRETTO_OFFSETS, _bar_x2_ticks
from motifs.subject_gen.duration_generator import _cached_scored_durations
from motifs.subject_gen.pitch_generator import _cached_validated_pitch
from motifs.subject_gen.scoring import score_subject, subject_features

MODE = "major"
TONIC = 72
METRE = (4, 4)
BAR_TICKS = _bar_x2_ticks(METRE)

# 1. Load durations + pitches
t0 = time.time()
all_durs = _cached_scored_durations(n_bars=2, bar_ticks=BAR_TICKS)
t1 = time.time()
print(f"Load durations: {t1-t0:.2f}s")

# 2. Build pool
pool = []
for nc in sorted(all_durs.keys()):
    pitches = _cached_validated_pitch(num_notes=nc, tonic_midi=TONIC, mode=MODE)
    for sp in pitches:
        for d_seq in all_durs[nc]:
            pool.append((sp, d_seq))
t2 = time.time()
print(f"Build pool ({len(pool):,}): {t2-t1:.2f}s")

# 3. Dedup
seen = set()
candidates = []
for sp, d_seq in pool:
    key = (sp.degrees, d_seq)
    if key not in seen:
        seen.add(key)
        candidates.append((sp, d_seq))
t3 = time.time()
print(f"Dedup ({len(candidates):,} unique): {t3-t2:.2f}s")

# 4. Cache lookup + scoring
cache_name = f"stretto_eval_{MODE}_2b_{BAR_TICKS}t.pkl"
stretto_cache = _load_cache(cache_name) or {}
t4 = time.time()
print(f"Load stretto cache ({len(stretto_cache):,} entries): {t4-t3:.2f}s")

scored = []
for sp, dur_seq in candidates:
    cache_key = (sp.degrees, dur_seq)
    viable = stretto_cache.get(cache_key, ())
    if len(viable) < MIN_STRETTO_OFFSETS:
        continue
    aes = score_subject(degrees=sp.degrees, ivs=sp.ivs, dur_indices=dur_seq)
    min_off = min(r.offset_slots for r in viable)
    feat = subject_features(degrees=sp.degrees, ivs=sp.ivs, dur_indices=dur_seq)
    scored.append((aes, min_off, sp, dur_seq, viable, feat))
t5 = time.time()
print(f"Score+filter ({len(scored):,} scored): {t5-t4:.2f}s")

# 5. Sort
scored.sort(key=lambda x: (-x[0], x[1]))
t6 = time.time()
print(f"Sort: {t6-t5:.2f}s")

# 6. Greedy max-min selection (vectorised)
import numpy as np

N = 25
n_cands = len(scored)
features = np.array([scored[i][5] for i in range(n_cands)], dtype=np.float32)

picks = [0]
# min_dist[i] = min squared distance from candidate i to any picked point so far
diff = features - features[0]
min_dist = np.einsum('ij,ij->i', diff, diff)
min_dist[0] = -1.0  # mark picked

for _ in range(N - 1):
    best_idx = int(np.argmax(min_dist))
    picks.append(best_idx)
    diff = features - features[best_idx]
    new_dist = np.einsum('ij,ij->i', diff, diff)
    np.minimum(min_dist, new_dist, out=min_dist)
    min_dist[best_idx] = -1.0
t7 = time.time()
print(f"Greedy selection (25 from {len(scored):,}): {t7-t6:.2f}s")
print(f"Total: {t7-t0:.2f}s")
