"""Generate demo MIDIs for curated invention subjects — v2.

Focus: rhythmic drama, contrast, anticipation.
Each subject has a distinctive rhythmic profile.
No rests — the CS generator requires note-for-note correspondence.
All subjects exactly 2 bars (2.0 whole notes) in 4/4.
"""
from pathlib import Path

from motifs.answer_generator import generate_answer
from motifs.countersubject_generator import generate_countersubject
from motifs.head_generator import degrees_to_midi
from motifs.subject_generator import (
    GeneratedSubject,
    FugueTriple,
    write_fugue_demo_midi,
    write_fugue_file,
)

TONIC_MIDI = 60  # C4
MODE = "major"
METRE = (4, 4)
TEMPO = 100
BAR_DUR = 1.0  # 4/4 = 1.0 whole note per bar
TARGET_BARS = 2
TARGET_DUR = TARGET_BARS * BAR_DUR  # 2.0

# Durations reference:
#   1/16 = 0.0625   1/8 = 0.125   d8 = 0.1875   1/4 = 0.25
#   d4  = 0.375    1/2 = 0.5     d2 = 0.75      1  = 1.0
#
# Degrees (0-based scale index): 0=C 1=D 2=E 3=F 4=G 5=A 6=B 7=C5
# Negative: -1=B3, -2=A3 etc.

SUBJECTS = [
    (
        "A_bold_descent",
        "Dotted half G holds for 3 beats — pure anticipation. Then sixteenths cascade down, resolving to C.",
        # G(d2)              G(16) F(16) E(16) D(16) | E(q)  D(8)  C(8)  C(h)
        (4,                  4,    3,    2,    1,      2,    1,    0,    0),
        (0.75,               0.0625,0.0625,0.0625,0.0625, 0.25, 0.125,0.125, 0.5),
    ),
    (
        "B_rocket",
        "Sixteenth-note rocket C-D-E-F explodes upward, lands on G held for 3 beats. Dotted descent home.",
        # C(16) D(16) E(16) F(16) | G(d2)          F(d8) E(16) D(q)  C(h)
        (0,    1,    2,    3,      4,              3,    2,    1,    0),
        (0.0625,0.0625,0.0625,0.0625, 0.75,        0.1875,0.0625,0.25, 0.5),
    ),
    (
        "C_toccata",
        "Ornamental turn on E, then sustained G. Second bar: sixteenth plunge F-E-D-C, step back, settle.",
        # E(d4)      D(16) E(16)  G(h)         | F(16) E(16) D(16) C(16) D(8)  C(8)  C(h)
        (2,          1,    2,     4,              3,    2,    1,    0,    1,    0,    0),
        (0.375,      0.0625,0.0625, 0.5,          0.0625,0.0625,0.0625,0.0625, 0.125,0.125, 0.5),
    ),
    (
        "D_stately_then_quick",
        "Two dotted-quarter pronouncements (C, G) — regal. Then eighths and sixteenths tumble home.",
        # C(d4)  E(8) | G(d4)  G(8) | F(8)  E(16) D(16) E(8)  D(8) C(h)
        (0,      2,    4,      4,     3,    2,    1,    2,   1,   0),
        (0.375,  0.125, 0.375, 0.125, 0.125,0.0625,0.0625,0.125,0.125,0.5),
    ),
    (
        "E_dotted_swing",
        "Dotted quarters give a lopsided, pushing feel. Like someone insisting, then relenting.",
        # G(d4)  A(8) | G(8) E(d4)   | F(8) E(8)  D(q)  C(h)
        (4,      5,    4,   2,         3,   2,    1,    0),
        (0.375,  0.125, 0.125, 0.375,  0.125,0.125, 0.25, 0.5),
    ),
    (
        "F_call_response",
        "Descending call G-E-C on long notes. Held C. Then rushing sixteenth answer back up, settles.",
        # G(q)  E(q) C(h)          | C(16) D(16) E(16) F(16) G(8)  A(8)  G(h)
        (4,    2,   0,              0,    1,    2,    3,    4,   5,    4),
        (0.25, 0.25, 0.5,           0.0625,0.0625,0.0625,0.0625, 0.125,0.125, 0.5),
    ),
]


def _verify_duration(name: str, degrees: tuple, durations: tuple) -> None:
    """Assert subject is well-formed."""
    assert len(degrees) == len(durations), (
        f"{name}: {len(degrees)} degrees but {len(durations)} durations"
    )
    total = sum(durations)
    assert abs(total - TARGET_DUR) < 0.001, (
        f"{name}: total duration {total} != {TARGET_DUR}"
    )


def _make_subject(
    name: str,
    degrees: tuple[int, ...],
    durations: tuple[float, ...],
) -> GeneratedSubject:
    """Construct a GeneratedSubject from curated data."""
    _verify_duration(name=name, degrees=degrees, durations=durations)
    midi_pitches = degrees_to_midi(
        degrees=degrees,
        tonic_midi=TONIC_MIDI,
        mode=MODE,
    )
    return GeneratedSubject(
        scale_indices=degrees,
        durations=durations,
        midi_pitches=midi_pitches,
        bars=TARGET_BARS,
        score=1.0,
        seed=0,
        mode=MODE,
        head_name=f"curated_{name}",
        leap_size=0,
        leap_direction="up",
        tail_direction="down",
    )


def main() -> None:
    """Generate demo MIDIs for all curated subjects."""
    output_dir = Path("output/subjects")
    output_dir.mkdir(parents=True, exist_ok=True)
    pitch_names = ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')
    success = 0
    for name, description, degrees, durations in SUBJECTS:
        print(f"\n{'='*60}")
        print(f"{name}: {description}")
        _verify_duration(name=name, degrees=degrees, durations=durations)
        midi_pitches = degrees_to_midi(
            degrees=degrees,
            tonic_midi=TONIC_MIDI,
            mode=MODE,
        )
        note_names = [f"{pitch_names[m % 12]}{m // 12 - 1}" for m in midi_pitches]
        dur_names = []
        for d in durations:
            if d == 1.0: dur_names.append("w")
            elif d == 0.75: dur_names.append("d2")
            elif d == 0.5: dur_names.append("h")
            elif d == 0.375: dur_names.append("dq")
            elif d == 0.25: dur_names.append("q")
            elif d == 0.1875: dur_names.append("d8")
            elif d == 0.125: dur_names.append("8")
            elif d == 0.0625: dur_names.append("16")
            else: dur_names.append(f"{d}")
        print(f"  Notes: {' '.join(f'{n}({r})' for n, r in zip(note_names, dur_names))}")
        subject = _make_subject(name=name, degrees=degrees, durations=durations)
        answer = generate_answer(subject=subject, tonic_midi=TONIC_MIDI)
        ans_names = [f"{pitch_names[m % 12]}{m // 12 - 1}" for m in answer.midi_pitches]
        print(f"  Answer ({answer.answer_type}): {' '.join(ans_names)}")
        cs = generate_countersubject(
            subject=subject,
            metre=METRE,
            tonic_midi=TONIC_MIDI,
            answer_degrees=answer.scale_indices,
        )
        if cs is None:
            print(f"  ** CS generation FAILED")
            continue
        cs_names = [f"{pitch_names[m % 12]}{m // 12 - 1}" for m in cs.midi_pitches]
        print(f"  CS: {' '.join(cs_names)}")
        triple = FugueTriple(
            subject=subject,
            answer=answer,
            countersubject=cs,
            metre=METRE,
            tonic_midi=TONIC_MIDI,
            seed=0,
        )
        midi_path = output_dir / f"{name}.midi"
        fugue_path = output_dir / f"{name}.fugue"
        write_fugue_demo_midi(triple=triple, path=midi_path, tempo=TEMPO)
        write_fugue_file(triple=triple, path=fugue_path)
        print(f"  -> {midi_path}")
        success += 1
    print(f"\n{'='*60}")
    print(f"{success}/{len(SUBJECTS)} subjects generated successfully.")
    print(f"Each MIDI plays: subject | gap | answer | gap | CS | gap | subj+CS | ans+CS | CS+subj")


if __name__ == "__main__":
    main()
