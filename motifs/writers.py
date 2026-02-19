"""Fugue triple assembly and file output.

Coordinates subject, answer, countersubject, and stretto analysis
into a FugueTriple, then writes MIDI, YAML (.fugue), and .note files.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import yaml

from motifs.head_generator import degrees_to_midi, RHYTHM_CELLS_BY_METRE
from motifs.subject_generator import GeneratedSubject
from shared.midi_writer import SimpleNote, write_midi_notes


# ── Batch configuration ─────────────────────────────────────────────
SUPPORTED_METRES: tuple[tuple[int, int], ...] = tuple(RHYTHM_CELLS_BY_METRE.keys())
TARGET_BAR_LENGTHS: tuple[int, ...] = (2, 3, 4)
TARGET_BAR_WEIGHTS: tuple[int, ...] = (4, 3, 2)
BATCH_BAR_COUNTS: tuple[int, ...] = (2, 2, 3, 3, 4, 4)


@dataclass(frozen=True)
class FugueTriple:
    """Subject, answer, and countersubject as a coordinated unit."""
    subject: GeneratedSubject
    answer: 'GeneratedAnswer'
    countersubject: 'GeneratedCountersubject'
    metre: Tuple[int, int]
    tonic_midi: int
    seed: int
    stretto_offsets: Tuple = ()


def _bar_duration(metre: tuple[int, int]) -> float:
    """Duration of one bar in whole-note units."""
    return metre[0] / metre[1]


def _midi_to_name(midi: int) -> str:
    """Convert MIDI number to note name (e.g., 67 -> G4)."""
    names = ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')
    octave = midi // 12 - 1
    return f"{names[midi % 12]}{octave}"


def generate_fugue_triple(
    mode: str = "minor",
    metre: Tuple[int, int] = (4, 4),
    seed: int | None = None,
    tonic_midi: int = 67,
    verbose: bool = False,
    target_bars: int | None = None,
    note_counts: tuple[int, ...] | None = None,
) -> FugueTriple:
    """Generate coordinated subject, answer, and countersubject."""
    from motifs.answer_generator import generate_answer
    from motifs.countersubject_generator import generate_countersubject
    from motifs.stretto_analyser import analyse_stretto
    from motifs.subject_generator import select_subject
    subject = select_subject(
        mode=mode,
        metre=metre,
        tonic_midi=tonic_midi,
        target_bars=target_bars,
        note_counts=note_counts,
        seed=seed or 0,
        verbose=verbose,
    )
    answer = generate_answer(
        subject=subject,
        tonic_midi=tonic_midi,
    )
    cs = generate_countersubject(
        subject=subject,
        metre=metre,
        tonic_midi=tonic_midi,
        answer_degrees=answer.scale_indices,
    )
    assert cs is not None, "Countersubject generation failed"
    stretto = analyse_stretto(
        subject=subject,
        answer=answer,
        metre=metre,
    )
    return FugueTriple(
        subject=subject,
        answer=answer,
        countersubject=cs,
        metre=metre,
        tonic_midi=tonic_midi,
        seed=seed or 0,
        stretto_offsets=stretto.valid_offsets,
    )


def write_fugue_file(triple: FugueTriple, path: Path) -> None:
    """Write fugue triple to YAML .fugue file."""
    tonic_name = _midi_to_name(midi=triple.tonic_midi).rstrip('0123456789')
    data = {
        'subject': {
            'degrees': list(triple.subject.scale_indices),
            'durations': [float(d) for d in triple.subject.durations],
            'mode': triple.subject.mode,
            'bars': triple.subject.bars,
            'head_name': triple.subject.head_name,
            'leap_size': triple.subject.leap_size,
            'leap_direction': triple.subject.leap_direction,
        },
        'answer': {
            'degrees': list(triple.answer.scale_indices),
            'durations': [float(d) for d in triple.answer.durations],
            'type': triple.answer.answer_type,
            'mutation_points': list(triple.answer.mutation_points),
        },
        'countersubject': {
            'degrees': list(triple.countersubject.scale_indices),
            'durations': [float(d) for d in triple.countersubject.durations],
            'vertical_intervals': list(triple.countersubject.vertical_intervals),
        },
        'metadata': {
            'metre': list(triple.metre),
            'tonic': tonic_name,
            'tonic_midi': triple.tonic_midi,
            'seed': triple.seed,
        },
        'stretto': [
            {
                'offset': s.offset,
                'offset_beats': s.offset_beats,
                'overlap_notes': s.overlap_notes,
                'all_consonant': s.all_consonant,
                'voice': s.voice,
            }
            for s in triple.stretto_offsets
        ],
    }
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def _add_melody(
    notes: list[SimpleNote],
    pitches: tuple[int, ...],
    durations: tuple[float, ...],
    track: int,
    start: float,
    velocity: int = 80,
) -> float:
    """Append notes to list; return offset after last note."""
    pos = start
    for pitch, dur in zip(pitches, durations):
        notes.append(SimpleNote(pitch=pitch, offset=pos, duration=dur, velocity=velocity, track=track))
        pos += dur
    return pos


def write_fugue_demo_midi(triple: FugueTriple, path: Path, tempo: int = 80) -> None:
    """Write demonstration MIDI: solos, pairs, then every valid stretto."""
    bar_dur = _bar_duration(metre=triple.metre)
    notes: list[SimpleNote] = []
    offset = 0.0
    cs_low = tuple(p - 12 for p in triple.countersubject.midi_pitches)
    # 1. Subject solo
    offset = _add_melody(notes, triple.subject.midi_pitches, triple.subject.durations, 0, offset)
    offset += bar_dur
    # 2. Answer solo
    offset = _add_melody(notes, triple.answer.midi_pitches, triple.answer.durations, 0, offset)
    offset += bar_dur
    # 3. CS solo
    offset = _add_melody(notes, triple.countersubject.midi_pitches, triple.countersubject.durations, 0, offset)
    offset += bar_dur
    # 4. Subject + CS
    end = _add_melody(notes, triple.subject.midi_pitches, triple.subject.durations, 0, offset)
    _add_melody(notes, cs_low, triple.countersubject.durations, 3, offset)
    offset = end + bar_dur
    # 5. Answer + CS
    end = _add_melody(notes, triple.answer.midi_pitches, triple.answer.durations, 0, offset)
    _add_melody(notes, cs_low, triple.countersubject.durations, 3, offset)
    offset = end + bar_dur
    # 6. Every valid stretto entry, tightest first
    sorted_stretti = sorted(triple.stretto_offsets, key=lambda s: s.offset)
    for s in sorted_stretti:
        leader = triple.subject.midi_pitches
        leader_dur = triple.subject.durations
        if s.voice == "subject":
            follower = tuple(p - 12 for p in triple.subject.midi_pitches)
            follower_dur = triple.subject.durations
        else:
            follower = tuple(p - 12 for p in triple.answer.midi_pitches)
            follower_dur = triple.answer.durations
        _add_melody(notes, leader, leader_dur, 0, offset)
        follower_end = _add_melody(notes, follower, follower_dur, 3, offset + s.offset)
        offset = max(offset + sum(leader_dur), follower_end) + bar_dur
    tonic_name = _midi_to_name(midi=triple.tonic_midi).rstrip('0123456789')
    write_midi_notes(
        path=str(path),
        notes=notes,
        tempo=tempo,
        time_signature=triple.metre,
        tonic=tonic_name,
        mode=triple.subject.mode,
    )


def write_note_file(subject: GeneratedSubject, path: Path, track: int = 0) -> None:
    """Write subject to .note CSV file."""
    lines: list[str] = ["offset,midi,duration,track,length,bar,beat,pitch,lyric"]
    offset = 0.0
    for midi, dur in zip(subject.midi_pitches, subject.durations):
        bar = int(offset) + 1
        beat = (offset % 1.0) * 4 + 1
        name = _midi_to_name(midi=midi)
        lines.append(f"{offset},{midi},{dur},{track},,{bar},{beat},{name},")
        offset += dur
    path.write_text("\n".join(lines), encoding="utf-8")


def write_midi_file(
    subject: GeneratedSubject,
    path: Path,
    tempo: int = 100,
    tonic: str = "C",
) -> None:
    """Write subject to MIDI file."""
    from shared.midi_writer import write_midi
    write_midi(
        path=str(path),
        pitches=list(subject.midi_pitches),
        durations=list(subject.durations),
        tempo=tempo,
        tonic=tonic,
        mode=subject.mode,
    )


def main() -> None:
    """Generate subjects and write to .midi and .note files."""
    import argparse
    parser = argparse.ArgumentParser(description="Generate fugue subjects")
    parser.add_argument("--output", "-o", type=Path, default=Path("subjects"),
                        help="Output folder (default: subjects)")
    parser.add_argument("--mode", "-m", type=str, default="major",
                        choices=["major", "minor"], help="Mode (default: major)")
    parser.add_argument("--metre", type=str, default="4/4",
                        help="Time signature (default: 4/4)")
    parser.add_argument("--seed", "-s", type=int, default=None,
                        help="Random seed")
    parser.add_argument("--tonic", "-k", type=str, default="C",
                        help="Tonic note (default: C)")
    parser.add_argument("--tempo", "-t", type=int, default=100,
                        help="Tempo in BPM (default: 100)")
    parser.add_argument("--bars", type=int, default=None, choices=[2, 3, 4],
                        help="Subject length in bars (default: random 2-4)")
    parser.add_argument("--notes", type=str, default=None,
                        help="Note counts, e.g. '9,10' (default: all)")
    parser.add_argument("--batch", "-b", type=int, default=None,
                        help="Generate batch of N subjects (default 6: 2x2bar, 2x3bar, 2x4bar)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print details")
    args = parser.parse_args()
    metre_parts = args.metre.split("/")
    metre = (int(metre_parts[0]), int(metre_parts[1]))
    note_counts = None
    if args.notes:
        note_counts = tuple(int(x) for x in args.notes.split(","))
    tonic_midi = {"C": 72, "D": 74, "E": 76, "F": 77, "G": 79, "A": 81, "B": 83,
                  "C#": 73, "Db": 73, "D#": 75, "Eb": 75, "F#": 78, "Gb": 78,
                  "G#": 80, "Ab": 80, "A#": 82, "Bb": 82}.get(args.tonic, 72)
    outdir = args.output
    outdir.mkdir(parents=True, exist_ok=True)
    count = args.batch or 6
    if args.bars is not None:
        bar_counts = [args.bars] * count
    elif count == 6:
        bar_counts = list(BATCH_BAR_COUNTS)
    else:
        bar_counts = [TARGET_BAR_LENGTHS[i % len(TARGET_BAR_LENGTHS)] for i in range(count)]
    for i, n_bars in enumerate(bar_counts):
        base = outdir / f"subject{i:02d}_{n_bars}bar"
        triple = generate_fugue_triple(
            mode=args.mode,
            metre=metre,
            seed=(args.seed or 0) + i,
            tonic_midi=tonic_midi,
            verbose=args.verbose,
            target_bars=n_bars,
            note_counts=note_counts,
        )
        write_note_file(subject=triple.subject, path=base.with_suffix(".note"))
        write_fugue_demo_midi(triple=triple, path=base.with_suffix(".midi"), tempo=args.tempo)
        write_fugue_file(triple=triple, path=base.with_suffix(".fugue"))
        n_stretto = len(triple.stretto_offsets)
        stretto_subj = sum(1 for s in triple.stretto_offsets if s.voice == "subject")
        stretto_ans = sum(1 for s in triple.stretto_offsets if s.voice == "answer")
        s = triple.subject
        s_notes = ' '.join(_midi_to_name(m) for m in s.midi_pitches)
        print(
            f"[{i:02d}] {n_bars}bar | {s.bars}bar actual | "
            f"{s_notes} | {n_stretto} stretto: {stretto_subj}S {stretto_ans}A"
        )
        if args.verbose:
            a = triple.answer
            c = triple.countersubject
            a_notes = ' '.join(_midi_to_name(m) for m in a.midi_pitches)
            c_notes = ' '.join(_midi_to_name(m) for m in c.midi_pitches)
            print(f"     Answer:  {a_notes}")
            print(f"     CS:      {c_notes}")
            for so in triple.stretto_offsets:
                print(f"     Stretto: {so.voice} at {so.offset_beats} beats, {so.overlap_notes} overlaps, consonant={so.all_consonant}")
    print(f"Generated {count} fugue triples in {outdir}")


if __name__ == "__main__":
    main()
