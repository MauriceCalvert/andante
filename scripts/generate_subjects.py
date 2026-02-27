"""Subject triple assembly and file output.

Coordinates subject, answer, countersubject, and stretto analysis
into a SubjectTriple, then writes MIDI, YAML (.subject), and .note files.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import yaml

from motifs.countersubject_generator import GeneratedCountersubject, generate_countersubject
from motifs.head_generator import degrees_to_midi
from motifs.stretto_constraints import OffsetResult
from motifs.subject_gen import GeneratedSubject
from motifs.subject_gen.constants import X2_TICKS_PER_WHOLE
from motifs.subject_generator import parse_note_name
from shared.midi_writer import SimpleNote, write_midi_notes
from shared.pitch import midi_to_name as _midi_to_name

CS2_INVERSION_DISTANCE: int = 9  # tenth — alternate invertible distance

def invert_degrees(degrees: tuple[int, ...]) -> tuple[int, ...]:
    """Tonal inversion: negate each degree around the first note."""
    pivot = degrees[0]
    return tuple(pivot - (d - pivot) for d in degrees)

# ── Batch configuration ─────────────────────────────────────────────
SUPPORTED_METRES: tuple[tuple[int, int], ...] = (
    (4, 4), (3, 4), (2, 4), (2, 2), (6, 8),
)
TARGET_BAR_LENGTHS: tuple[int, ...] = (2, 3, 4)
TARGET_BAR_WEIGHTS: tuple[int, ...] = (4, 3, 2)
BATCH_BAR_COUNTS: tuple[int, ...] = (2, 2, 3, 3, 4, 4)

@dataclass(frozen=True)
class SubjectTriple:
    """Subject, answer, and countersubject as a coordinated unit."""
    subject: GeneratedSubject
    answer: 'GeneratedAnswer'
    countersubject: GeneratedCountersubject
    metre: tuple[int, int]
    tonic_midi: int
    seed: int
    stretto_offsets: Tuple = ()
    inversion_degrees: tuple[int, ...] = ()
    inversion_midi: tuple[int, ...] = ()
    inversion_stretto: Tuple = ()
    countersubject_2: GeneratedCountersubject | None = None

def _bar_duration(metre: tuple[int, int]) -> float:
    """Duration of one bar in whole-note units."""
    return metre[0] / metre[1]

def generate_triple(
    mode: str = "minor",
    metre: tuple[int, int] = (4, 4),
    seed: int | None = None,
    tonic_midi: int = 67,
    verbose: bool = False,
    target_bars: int | None = None,
    note_counts: tuple[int, ...] | None = None,
    pitch_contour: str | None = None,
    subject: 'GeneratedSubject | None' = None,
    inversion_distance: int = 7,
) -> SubjectTriple:
    """Generate coordinated subject, answer, and countersubject."""
    from motifs.answer_generator import generate_answer
    if subject is None:
        from motifs.subject_gen import select_subject
        subject = select_subject(
            mode=mode,
            metre=metre,
            tonic_midi=tonic_midi,
            target_bars=target_bars,
            pitch_contour=pitch_contour,
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
        inversion_distance=inversion_distance,
    )
    assert cs is not None, "Countersubject generation failed"
    cs2 = generate_countersubject(
        subject=subject,
        metre=metre,
        tonic_midi=tonic_midi,
        answer_degrees=answer.scale_indices,
        inversion_distance=CS2_INVERSION_DISTANCE,
    )
    # cs2 may be None — solver infeasible at distance 9. That's fine.
    inv_deg = invert_degrees(degrees=subject.scale_indices)
    inv_midi = degrees_to_midi(
        degrees=inv_deg,
        tonic_midi=tonic_midi,
        mode=subject.mode,
    )
    from motifs.stretto_analyser import find_stretto_offsets
    inv_stretto = find_stretto_offsets(
        leader_degrees=subject.scale_indices,
        leader_durations=subject.durations,
        follower_degrees=inv_deg,
        follower_durations=subject.durations,
        metre=metre,
        voice_label="inversion",
    )
    return SubjectTriple(
        subject=subject,
        answer=answer,
        countersubject=cs,
        metre=metre,
        tonic_midi=tonic_midi,
        seed=seed or 0,
        inversion_degrees=inv_deg,
        inversion_midi=tuple(inv_midi),
        inversion_stretto=tuple(inv_stretto),
        countersubject_2=cs2,
    )

def write_subject_file(triple: SubjectTriple, path: Path) -> None:
    """Write fugue triple to YAML .subject file."""
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
            'inversion_distance': triple.countersubject.inversion_distance,
        },
        'metadata': {
            'metre': list(triple.metre),
            'tonic': tonic_name,
            'tonic_midi': triple.tonic_midi,
            'seed': triple.seed,
        },
        'inversion': {
            'degrees': list(triple.inversion_degrees),
        },
        'stretto': [
            {
                'offset_slots': r.offset_slots,
                'consonant': f"{r.consonant_count}/{r.total_count}",
                'dissonance_cost': r.dissonance_cost,
                'quality': round(r.quality, 2),
            }
            for r in sorted(triple.subject.stretto_offsets, key=lambda r: r.offset_slots)
        ],
        'inversion_stretto': [
            {
                'offset_beats': round(r.offset_beats, 2),
                'quality': round(r.quality, 2),
            }
            for r in sorted(triple.inversion_stretto, key=lambda r: r.offset)
        ],
    }
    if triple.countersubject_2 is not None:
        data['countersubject_2'] = {
            'degrees': list(triple.countersubject_2.scale_indices),
            'durations': [float(d) for d in triple.countersubject_2.durations],
            'vertical_intervals': list(triple.countersubject_2.vertical_intervals),
            'inversion_distance': triple.countersubject_2.inversion_distance,
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

OCTAVE_SHIFT: int = 12

def write_subject_demo_midi(triple: SubjectTriple, path: Path, tempo: int = 80) -> None:
    """Write demo MIDI: subject, answer, CS, then stretto pairs at each viable offset."""
    bar_dur = _bar_duration(metre=triple.metre)
    notes: list[SimpleNote] = []
    offset = 0.0
    subj = triple.subject.midi_pitches
    subj_dur = triple.subject.durations
    subj_low = tuple(p - OCTAVE_SHIFT for p in subj)
    ans = triple.answer.midi_pitches
    ans_dur = triple.answer.durations
    cs = triple.countersubject.midi_pitches
    cs_dur = triple.countersubject.durations
    # 1. Subject solo
    offset = _add_melody(notes, subj, subj_dur, 0, offset)
    offset += bar_dur
    # 2. Answer solo
    offset = _add_melody(notes, ans, ans_dur, 0, offset)
    offset += bar_dur
    # 3. Inversion solo
    inv = triple.inversion_midi
    inv_dur = subj_dur  # Same rhythm
    offset = _add_melody(notes, inv, inv_dur, 0, offset)
    offset += bar_dur
    # 4. Countersubject solo
    offset = _add_melody(notes, cs, cs_dur, 0, offset)
    offset += bar_dur
    # 5. Subject + countersubject together
    _add_melody(notes, subj, subj_dur, 0, offset)
    offset = _add_melody(notes, cs, cs_dur, 1, offset)
    offset += bar_dur
    # 6. Subject vs subject stretto pairs, tightest first (entry within bar 1)
    viable: list[OffsetResult] = sorted(
        [r for r in triple.subject.stretto_offsets
         if r.offset_slots / X2_TICKS_PER_WHOLE <= bar_dur],
        key=lambda r: r.offset_slots,
    )
    for r in viable:
        stretto_delay = r.offset_slots / X2_TICKS_PER_WHOLE
        leader_end = _add_melody(notes, subj, subj_dur, 0, offset)
        follower_end = _add_melody(notes, subj_low, subj_dur, 1, offset + stretto_delay)
        offset = max(leader_end, follower_end) + bar_dur
    # 7. Subject vs inversion stretto pairs (entry within bar 1)
    from motifs.stretto_analyser import StrettoOffset
    inv_stretto: list[StrettoOffset] = sorted(
        [r for r in triple.inversion_stretto if r.offset <= bar_dur],
        key=lambda r: r.offset,
    )
    for r in inv_stretto:
        leader_end = _add_melody(notes, subj, subj_dur, 0, offset)
        follower_end = _add_melody(notes, inv, inv_dur, 1, offset + r.offset)
        offset = max(leader_end, follower_end) + bar_dur
    tonic_name = _midi_to_name(midi=triple.tonic_midi).rstrip('0123456789')
    write_midi_notes(
        path=str(path),
        notes=notes,
        tempo=tempo,
        time_signature=triple.metre,
        tonic=tonic_name,
        mode=triple.subject.mode,
    )

def _notes_to_csv(
    notes: list[SimpleNote],
    metre: tuple[int, int],
) -> str:
    """Convert SimpleNote list to .note CSV matching the MIDI layout."""
    bar_dur = _bar_duration(metre=metre)
    lines: list[str] = ["offset,midi,duration,track,bar,beat,pitch"]
    sorted_notes = sorted(notes, key=lambda n: (n.offset, n.track, n.pitch))
    for n in sorted_notes:
        bar = int(n.offset / bar_dur) + 1
        beat_in_bar = (n.offset % bar_dur) / bar_dur * metre[0] + 1
        name = _midi_to_name(midi=n.pitch)
        lines.append(
            f"{n.offset:.4f},{n.pitch},{n.duration:.4f},{n.track},"
            f"{bar},{beat_in_bar:.2f},{name}"
        )
    return "\n".join(lines)

def write_note_file(triple: SubjectTriple, path: Path) -> None:
    """Write .note CSV reflecting the full demo MIDI layout."""
    bar_dur = _bar_duration(metre=triple.metre)
    notes: list[SimpleNote] = []
    offset = 0.0
    subj = triple.subject.midi_pitches
    subj_dur = triple.subject.durations
    subj_low = tuple(p - OCTAVE_SHIFT for p in subj)
    ans = triple.answer.midi_pitches
    ans_dur = triple.answer.durations
    cs = triple.countersubject.midi_pitches
    cs_dur = triple.countersubject.durations
    # 1. Subject
    offset = _add_melody(notes, subj, subj_dur, 0, offset)
    offset += bar_dur
    # 2. Answer
    offset = _add_melody(notes, ans, ans_dur, 0, offset)
    offset += bar_dur
    # 3. Subject + countersubject together
    _add_melody(notes, subj, subj_dur, 0, offset)
    offset = _add_melody(notes, cs, cs_dur, 1, offset)
    offset += bar_dur
    # 4. Inversion solo
    inv = triple.inversion_midi
    inv_dur = subj_dur
    offset = _add_melody(notes, inv, inv_dur, 0, offset)
    offset += bar_dur
    # 5. Subject vs subject stretto pairs (entry within bar 1)
    viable: list[OffsetResult] = sorted(
        [r for r in triple.subject.stretto_offsets
         if r.offset_slots / X2_TICKS_PER_WHOLE <= bar_dur],
        key=lambda r: r.offset_slots,
    )
    for r in viable:
        stretto_delay = r.offset_slots / X2_TICKS_PER_WHOLE
        leader_end = _add_melody(notes, subj, subj_dur, 0, offset)
        follower_end = _add_melody(notes, subj_low, subj_dur, 1, offset + stretto_delay)
        offset = max(leader_end, follower_end) + bar_dur
    # 6. Subject vs inversion stretto pairs (entry within bar 1)
    from motifs.stretto_analyser import StrettoOffset
    inv_stretto: list[StrettoOffset] = sorted(
        [r for r in triple.inversion_stretto if r.offset <= bar_dur],
        key=lambda r: r.offset,
    )
    for r in inv_stretto:
        leader_end = _add_melody(notes, subj, subj_dur, 0, offset)
        follower_end = _add_melody(notes, inv, inv_dur, 1, offset + r.offset)
        offset = max(leader_end, follower_end) + bar_dur
    path.write_text(_notes_to_csv(notes, triple.metre), encoding="utf-8")

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

def patch_library_files(verbose: bool = False) -> None:
    """Add countersubject_2 to all library .subject files that lack it.

    Loads each file, builds a minimal GeneratedSubject shim from its data,
    runs the CS generator at distance 9, and writes CS2 back if feasible.
    Does not touch CS1 or any other section.
    """
    library_dir = Path(__file__).parent.parent / "motifs" / "library"
    subject_files = sorted(library_dir.glob("*.subject"))
    assert subject_files, f"No .subject files found in {library_dir}"

    for path in subject_files:
        with open(path, encoding="utf-8") as f:
            data: dict = yaml.safe_load(f)

        if "countersubject_2" in data:
            if verbose:
                print(f"[patch] {path.name}: already has CS2 — skipping")
            continue

        subj_data: dict = data["subject"]
        ans_data: dict = data["answer"]
        meta: dict = data["metadata"]

        degrees: tuple[int, ...] = tuple(subj_data["degrees"])
        durations: tuple[float, ...] = tuple(float(d) for d in subj_data["durations"])
        mode: str = subj_data["mode"]
        tonic_midi: int = int(meta["tonic_midi"])
        metre: tuple[int, int] = (int(meta["metre"][0]), int(meta["metre"][1]))
        answer_degrees: tuple[int, ...] = tuple(ans_data["degrees"])

        midi_pitches = degrees_to_midi(degrees=degrees, tonic_midi=tonic_midi, mode=mode)

        # Build minimal shim — CS generator only uses scale_indices, durations, mode
        subject_shim = GeneratedSubject(
            scale_indices=degrees,
            durations=durations,
            midi_pitches=midi_pitches,
            bars=int(subj_data["bars"]),
            score=0.0,
            seed=int(meta["seed"]),
            mode=mode,
            head_name=subj_data["head_name"],
            leap_size=int(subj_data["leap_size"]),
            leap_direction=subj_data["leap_direction"],
            tail_direction="",
        )

        cs2 = generate_countersubject(
            subject=subject_shim,
            metre=metre,
            tonic_midi=tonic_midi,
            answer_degrees=answer_degrees,
            inversion_distance=CS2_INVERSION_DISTANCE,
        )

        if cs2 is None:
            if verbose:
                print(f"[patch] {path.name}: CS2 infeasible at distance 9 — skipping")
            continue

        data["countersubject_2"] = {
            "degrees": list(cs2.scale_indices),
            "durations": [float(d) for d in cs2.durations],
            "vertical_intervals": list(cs2.vertical_intervals),
            "inversion_distance": cs2.inversion_distance,
        }

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        if verbose:
            print(f"[patch] {path.name}: CS2 added ({len(cs2.scale_indices)} notes)")


def patch_library_answers(verbose: bool = False) -> None:
    """Rebuild the answer section in all library .subject files.

    Loads each file, extracts subject degrees/mode/tonic_midi,
    calls generate_answer() with the corrected transposition constants,
    and overwrites just the answer degrees and mutation_points.
    All other sections are left untouched.
    """
    from motifs.answer_generator import generate_answer

    library_dir = Path(__file__).parent.parent / "motifs" / "library"
    subject_files = sorted(library_dir.glob("*.subject"))
    assert subject_files, f"No .subject files found in {library_dir}"

    for path in subject_files:
        with open(path, encoding="utf-8") as f:
            data: dict = yaml.safe_load(f)

        subj_data: dict = data["subject"]
        meta: dict = data["metadata"]

        degrees: tuple[int, ...] = tuple(subj_data["degrees"])
        durations: tuple[float, ...] = tuple(float(d) for d in subj_data["durations"])
        mode: str = subj_data["mode"]
        tonic_midi: int = int(meta["tonic_midi"])

        midi_pitches = degrees_to_midi(degrees=degrees, tonic_midi=tonic_midi, mode=mode)

        subject_shim = GeneratedSubject(
            scale_indices=degrees,
            durations=durations,
            midi_pitches=midi_pitches,
            bars=int(subj_data["bars"]),
            score=0.0,
            seed=int(meta["seed"]),
            mode=mode,
            head_name=subj_data["head_name"],
            leap_size=int(subj_data["leap_size"]),
            leap_direction=subj_data["leap_direction"],
            tail_direction="",
        )

        answer = generate_answer(subject=subject_shim, tonic_midi=tonic_midi)

        old_degrees = data["answer"]["degrees"]
        data["answer"]["degrees"] = list(answer.scale_indices)
        data["answer"]["mutation_points"] = list(answer.mutation_points)

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        if verbose:
            print(f"[patch-answers] {path.name}: degrees {old_degrees} -> {list(answer.scale_indices)}")


def main() -> None:
    """Generate subjects and write to .midi and .note files."""
    import argparse
    parser = argparse.ArgumentParser(description="Generate fugue subjects")
    parser.add_argument("--output", "-o", type=Path, default=Path(r"motifs\output"),
                        help=r"Output folder (default: motifs\output)")
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
    parser.add_argument("--bars", type=int, default=2, choices=[1, 2, 3, 4],
                        help="Subject length in bars (default: random 1-4)")
    parser.add_argument("--notes", type=str, default=12,
                        help="Note counts, e.g. '9,10,11' (default: all)")
    parser.add_argument("--batch", "-b", type=int, default=10,
                        help="Generate N subjects (default 10)")
    parser.add_argument("--pitches", type=str, default=None,
                        help="Fixed pitches, e.g. 'c5,d5,e5,f5' (bypasses pitch generation)")
    parser.add_argument("--contour", type=str, default=None,
                        choices=["arch", "valley", "swoop", "dip",
                                 "ascending", "descending", "zigzag"],
                        help="Pitch contour filter")
    parser.add_argument("--inversion-distance", type=int, default=7,
                        choices=[7, 9, 11],
                        help="Inversion distance in semitones: 7=octave, 9=tenth, 11=twelfth (default: 7)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print details")
    parser.add_argument("--patch-library", action="store_true",
                        help="Patch library .subject files to add countersubject_2 at distance 9")
    parser.add_argument("--patch-answers", action="store_true",
                        help="Rebuild answer section in all library .subject files")
    args = parser.parse_args()

    if args.patch_answers:
        patch_library_answers(verbose=args.verbose)
        return
    if args.patch_library:
        patch_library_files(verbose=args.verbose)
        return
    metre_parts = args.metre.split("/")
    metre = (int(metre_parts[0]), int(metre_parts[1]))
    note_counts = None
    if args.notes:
        note_counts = tuple(int(x) for x in str(args.notes).split(","))
    fixed_midi = None
    if args.pitches:
        fixed_midi = tuple(parse_note_name(n) for n in args.pitches.split(","))
        note_counts = (len(fixed_midi),)
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
    # ── Batch-wide diverse selection per bar count ────────────
    from collections import defaultdict
    from motifs.subject_gen import select_diverse_subjects
    groups: dict[int, list[int]] = defaultdict(list)
    for i, n_bars in enumerate(bar_counts):
        groups[n_bars].append(i)
    subject_by_index: dict[int, object] = {}
    for n_bars, indices in groups.items():
        subjects = select_diverse_subjects(
            n=len(indices),
            mode=args.mode,
            metre=metre,
            tonic_midi=tonic_midi,
            target_bars=n_bars,
            pitch_contour=args.contour,
            note_counts=note_counts,
            fixed_midi=fixed_midi,
            verbose=args.verbose,
        )
        if len(subjects) < len(indices):
            print(f"[subject_gen] only {len(subjects)} candidates found "
                  f"(requested {len(indices)} for {n_bars}-bar)")
            indices = indices[:len(subjects)]
        for j, idx in enumerate(indices):
            subject_by_index[idx] = subjects[j]
    for i, n_bars in enumerate(bar_counts):
        if i not in subject_by_index:
            continue
        base = outdir / f"subject{i:02d}_{n_bars}bar"
        triple = generate_triple(
            mode=args.mode,
            metre=metre,
            seed=(args.seed or 0) + i,
            tonic_midi=tonic_midi,
            verbose=args.verbose,
            target_bars=n_bars,
            note_counts=note_counts,
            pitch_contour=args.contour,
            subject=subject_by_index[i],
            inversion_distance=args.inversion_distance,
        )
        write_note_file(triple=triple, path=base.with_suffix(".note"))
        write_subject_demo_midi(triple=triple, path=base.with_suffix(".midi"), tempo=args.tempo)
        write_subject_file(triple=triple, path=base.with_suffix(".subject"))
        s = triple.subject
        bar_dur = _bar_duration(metre=metre)
        max_stretto_slots: int = int(bar_dur * X2_TICKS_PER_WHOLE)
        n_stretto = sum(1 for r in s.stretto_offsets if r.offset_slots <= max_stretto_slots)
        s_notes = ' '.join(_midi_to_name(m) for m in s.midi_pitches)
        _DUR_ABBREV = {0.0625: '16', 0.125: '8', 0.1875: '8.', 0.25: '4', 0.375: '4.', 0.5: '2', 1.0: '1'}
        s_durs = ' '.join(_DUR_ABBREV.get(d, f'{d}') for d in s.durations)
        print(
            f"[{i:02d}] {n_bars}bar | {s.bars}bar actual | "
            f"{s_notes} | {n_stretto} stretto offsets"
        )
        print(f"     Rhythm:  {s_durs}")
        if args.verbose:
            a = triple.answer
            c = triple.countersubject
            a_notes = ' '.join(_midi_to_name(m) for m in a.midi_pitches)
            c_notes = ' '.join(_midi_to_name(m) for m in c.midi_pitches)
            print(f"     Answer:  {a_notes}")
            print(f"     CS:      {c_notes}")
            slots_per_beat = 4 if metre[1] == 4 else 2
            max_offset_slots: int = int(bar_dur * X2_TICKS_PER_WHOLE)
            for r in sorted(s.stretto_offsets, key=lambda r: r.offset_slots):
                if r.offset_slots > max_offset_slots:
                    continue
                print(f"     Stretto: offset={r.offset_slots} slots "
                      f"({r.offset_slots / slots_per_beat:.1f} beats) "
                      f"cost={r.dissonance_cost} "
                      f"quality={r.quality:.2f}")
            inv_notes = ' '.join(_midi_to_name(m) for m in triple.inversion_midi)
            print(f"     Inv:     {inv_notes}")
            inv_viable = [r for r in triple.inversion_stretto if r.offset <= bar_dur]
            print(f"     Inv stretto: {len(inv_viable)} offsets")
            for r in sorted(inv_viable, key=lambda r: r.offset):
                print(f"       offset={r.offset_beats:.1f} beats "
                      f"quality={r.quality:.2f}")
    print(f"Generated {len(subject_by_index)} fugue triples in {outdir}")

if __name__ == "__main__":
    main()
