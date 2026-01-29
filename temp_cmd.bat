@echo off
cd /d D:\projects\Barok\barok\source\andante
git add -A
git commit -m "Fix: Replace rhythmic stagger hack with canonical beat-class placement

Beat-class is now intrinsic to figuration, not a post-hoc offset.
Lead voice occupies strong beats (1, 3); accompanying voice occupies
weak beats (2, 4). Durations scale to fit available space naturally.

Removed:
- RHYTHM_STAGGER_OFFSET, DENSE_PASSAGE_NOTE_THRESHOLD, SPARSE_PASSAGE_STAGGER_OFFSET
- _compute_stagger(), _is_dense_passage(), _get_passage_end_offset()
- All truncation and skip-past-boundary logic

Added:
- FiguredBar.start_beat field
- beat_class parameter flows from passage_assignments through figurate() to realiser
- compute_start_beat() derives beat from beat-class and metre

Net: ~50 lines of hack code removed, ~20 lines of proper beat-class logic added."
