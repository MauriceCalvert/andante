"""Test subject generator with semiquavers enabled."""
import time
from motifs.subject_generator import select_subject

t0 = time.time()
result = select_subject(
    mode="major",
    metre=(4, 4),
    tonic_midi=60,
    target_bars=2,
    seed=0,
    verbose=True,
)
elapsed = time.time() - t0

print(f"\nResult: {len(result.scale_indices)}n, score={result.score:.4f}")
print(f"  Degrees:  {result.scale_indices}")
print(f"  MIDI:     {result.midi_pitches}")
print(f"  Durs:     {result.durations}")
print(f"  Stretto:  {len(result.stretto_offsets)} viable offsets")
print(f"  Total:    {elapsed:.1f}s")

sq_count = sum(1 for d in result.durations if d == 1/16)
print(f"  Semiquavers: {sq_count}")
