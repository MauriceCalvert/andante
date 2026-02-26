"""Diagnostic: check all stretto offsets for subject [8] via CPU path."""
import sys
sys.path.insert(0, r"D:\projects\Barok\barok\source\andante")

from motifs.head_generator import degrees_to_midi
from motifs.stretto_constraints import evaluate_all_offsets, _slots_per_bar, _note_onsets
from motifs.subject_gen.constants import DURATION_TICKS, X2_TICKS_PER_WHOLE

degrees = (4, 3, 0, 2, 1, 0, -1, -3, -2, 1, -1, -3)
durs_frac = (0.125, 0.125, 0.25, 0.25, 0.0625, 0.0625, 0.125, 0.125, 0.125, 0.25, 0.25, 0.25)
metre = (4, 4)
tonic_midi = 72
mode = "major"

midi = degrees_to_midi(degrees=degrees, tonic_midi=tonic_midi, mode=mode)
dur_slots = tuple(round(d * X2_TICKS_PER_WHOLE) for d in durs_frac)

print(f"MIDI: {midi}")
print(f"dur_slots: {dur_slots}  total={sum(dur_slots)}")
print(f"bar_slots: {_slots_per_bar(metre)}")

onsets = _note_onsets(dur_slots)
print(f"onsets: {onsets}")

results = evaluate_all_offsets(midi=midi, dur_slots=dur_slots, metre=metre)
print(f"\n{len(results)} results from evaluate_all_offsets:")
for r in results:
    print(f"  offset={r.offset_slots} viable={r.viable} "
          f"consonant={r.consonant_count}/{r.total_count} "
          f"cost={r.dissonance_cost} quality={r.quality:.2f}")
