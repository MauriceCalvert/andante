## Result: EPI-4a — Kernel episode demo (soprano only)

### Code Changes

1. **`motifs/fragen.py`** — Added new types and functions (no existing code modified):
   - `Kernel` dataclass (frozen): `name`, `degrees`, `durations`, `total_duration`, `source`
   - `extract_kernels(fugue: SubjectTriple) -> list[Kernel]`: Extracts 2/3/4-note
     contiguous subsequences from head, tail, cs, and answer. Normalises degrees
     (first=0), produces inversions (negated degrees), deduplicates by
     (degrees, durations).
   - `sequence_kernel(kernel, start_degree, step, iterations, voice) -> list[Note]`:
     Pure sequential transposition — each iteration offsets by `step` diatonic
     degrees and `kernel.total_duration` in time. No bar alignment, no chaining.
   - Helper functions: `_kernel_subsequences`, `_invert_kernel`, `_dedup_kernels`
   - Constants: `_KERNEL_MAX_NOTES=4`, `_KERNEL_MIN_NOTES=2`
   - Added `from shared.music_math import parse_metre` import

2. **`scripts/episode_kernel_demo.py`** — New standalone demo script:
   - Loads all subjects from `motifs/library/` (or single `--subject`)
   - Extracts kernels, generates descending (step=-1) and ascending (step=+1)
     sequences of 5 iterations each
   - Converts to MIDI via `degrees_to_midi` with subject's tonic/mode, start degree=7
   - Writes one MIDI file per subject: `output/episode_kernels_{name}.mid`
   - Prints summary table: kernel name, source, note count, duration, contour

### Checkpoint Results

1. Script runs without error for all 3 library subjects.
2. MIDI files written:
   - `output/episode_kernels_subject09_2bar.mid` (32KB, 61 kernels)
   - `output/episode_kernels_subject17_2bar.mid` (33KB, 66 kernels)
   - `output/episode_kernels_subject19_2bar.mid` (42KB, 155 kernels)
3. Summary tables printed for all subjects showing kernel count, sources, durations.
4. Spot-check: subject09 `head[0:4]` descending sequence confirmed —
   degrees (0,-1,-2,-3) in semiquavers, step=-1 produces:
   C-B-A-G -> B-A-G-F -> A-G-F-E -> G-F-E-D -> F-E-D-C
   Clean descending scale-fragment sequence stepping down by one diatonic degree
   per iteration.

### No existing pipeline code was modified.

Please listen to the MIDI and let me know what you hear.
