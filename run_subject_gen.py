"""Test subject generation — write MIDI for listening."""
import time
from pathlib import Path

from motifs.head_generator import degrees_to_midi, NOTE_NAMES
from motifs.subject_generator import (
    DURATION_NAMES, DURATION_TICKS, X2_TICKS_PER_WHOLE,
    select_subject,
)
from shared.midi_writer import SimpleNote, write_midi_notes


OUTPUT_DIR: Path = Path("test_subjects")
N_SUBJECTS: int = 5
TONIC_MIDI: int = 60  # C4
TEMPO: int = 100


def _midi_name(midi: int) -> str:
    return f"{NOTE_NAMES[midi % 12]}{midi // 12 - 1}"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_notes: list[SimpleNote] = []
    offset = 0.0
    gap = 1.0  # one whole note gap between subjects
    for i in range(N_SUBJECTS):
        t0 = time.time()
        s = select_subject(
            mode="major",
            metre=(4, 4),
            tonic_midi=TONIC_MIDI,
            target_bars=2,
            note_counts=(9, 10),
            verbose=False,
        )
        elapsed = time.time() - t0
        # Individual MIDI
        notes: list[SimpleNote] = []
        pos = 0.0
        for midi, dur in zip(s.midi_pitches, s.durations):
            notes.append(SimpleNote(
                pitch=midi, offset=pos, duration=dur,
                velocity=80, track=0,
            ))
            pos += dur
        path = OUTPUT_DIR / f"subject_{i:02d}_major_44_2bar.midi"
        write_midi_notes(
            path=str(path), notes=notes, tempo=TEMPO,
            time_signature=(4, 4), tonic="C", mode="major",
        )
        # Append to combined
        for n in notes:
            all_notes.append(SimpleNote(
                pitch=n.pitch, offset=n.offset + offset,
                duration=n.duration, velocity=n.velocity, track=0,
            ))
        offset += pos + gap
        # Print
        pitch_str = " ".join(_midi_name(m) for m in s.midi_pitches)
        dur_ticks = [int(d * X2_TICKS_PER_WHOLE) for d in s.durations]
        dur_idx = [DURATION_TICKS.index(t) if t in DURATION_TICKS else -1 for t in dur_ticks]
        dur_str = " ".join(
            DURATION_NAMES[di] if di >= 0 else f"?{t}"
            for di, t in zip(dur_idx, dur_ticks)
        )
        print(f"[{i:02d}] major 4/4 2bar | "
              f"{elapsed:.1f}s | score={s.score:.4f} | {s.head_name}")
        print(f"     {pitch_str}")
        print(f"     {dur_str}")
        print(f"     degrees={s.scale_indices}")
        print()
    # Combined MIDI
    combined_path = OUTPUT_DIR / "all_subjects.midi"
    write_midi_notes(
        path=str(combined_path), notes=all_notes, tempo=TEMPO,
        time_signature=(4, 4), tonic="C", mode="major",
    )
    print(f"Written {N_SUBJECTS} subjects to {OUTPUT_DIR}/")
    print(f"Combined: {combined_path}")


if __name__ == "__main__":
    main()
