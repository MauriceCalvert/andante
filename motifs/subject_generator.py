"""Subject generator using head + tail construction.

Generates Baroque-style fugue subjects by:
1. Selecting a head (opening gesture with leap + gap fill)
2. Generating a tail (contrary motion, derived rhythm, tonic resolution)
3. Combining into subjects that span an integer number of bars
4. Scoring against figurae for affect appropriateness

Usage:
    from motifs.subject_generator import generate_subject, generate_subject_batch
"""
import random
from dataclasses import dataclass
from typing import List, Tuple

import yaml

from motifs.head_generator import (
    get_rhythm_cells,
    degrees_to_midi,
    Head,
    RHYTHM_CELLS_BY_METRE,
    MIN_DEGREE,
    MAX_DEGREE,
    MAX_INTERVAL,
    MIN_LEAP,
)
from shared.constants import NOTE_NAMES, TONIC_TRIAD_DEGREES
from motifs.tail_generator import (
    generate_tails_for_head,
    tail_to_degrees,
    Tail,
)
from motifs.figurae import get_figurae, score_motif_figurae, Figura
from motifs.affect_loader import get_affect_profile, score_subject_affect
from pathlib import Path
from shared.midi_writer import write_midi_notes, SimpleNote


SUPPORTED_METRES: tuple[tuple[int, int], ...] = tuple(RHYTHM_CELLS_BY_METRE.keys())


def _bar_duration(metre: tuple[int, int]) -> float:
    """Calculate duration of one bar for a given metre."""
    return metre[0] / metre[1]


@dataclass(frozen=True)
class GeneratedSubject:
    """Result of subject generation."""
    scale_indices: Tuple[int, ...]
    durations: Tuple[float, ...]
    midi_pitches: Tuple[int, ...]
    bars: int
    score: float
    seed: int
    mode: str
    head_name: str
    leap_size: int
    leap_direction: str
    tail_direction: str
    affect: str | None = None
    figurae_score: float = 0.0
    satisfied_figurae: Tuple[str, ...] = ()


@dataclass(frozen=True)
class FugueTriple:
    """Subject, answer, and countersubject as a coordinated unit."""
    subject: 'GeneratedSubject'
    answer: 'GeneratedAnswer'
    countersubject: 'GeneratedCountersubject'
    metre: Tuple[int, int]
    tonic_midi: int
    seed: int


def _intervals(degrees: tuple[int, ...]) -> list[int]:
    """Compute intervals between adjacent degrees."""
    return [degrees[i + 1] - degrees[i] for i in range(len(degrees) - 1)]


def _midi_intervals(midi_pitches: tuple[int, ...]) -> list[int]:
    """Compute semitone intervals between adjacent MIDI pitches."""
    return [midi_pitches[i + 1] - midi_pitches[i] for i in range(len(midi_pitches) - 1)]


def _has_seventh_leap(midi_pitches: tuple[int, ...]) -> bool:
    """Check if sequence has any 7th leap (10-11 semitones)."""
    for iv in _midi_intervals(midi_pitches=midi_pitches):
        if abs(iv) in (10, 11):
            return True
    return False


def _has_tritone_leap(midi_pitches: tuple[int, ...]) -> bool:
    """Check if sequence has any tritone leap (6 semitones)."""
    for iv in _midi_intervals(midi_pitches=midi_pitches):
        if abs(iv) == 6:
            return True
    return False


def _has_tritone_outline(midi_pitches: tuple[int, ...]) -> bool:
    """Check if any 4-note span outlines a tritone (6 semitones)."""
    if len(midi_pitches) < 4:
        return False
    for i in range(len(midi_pitches) - 3):
        span = abs(midi_pitches[i + 3] - midi_pitches[i])
        if span == 6:
            return True
    return False


def _has_consecutive_leaps_same_direction(midi_pitches: tuple[int, ...]) -> bool:
    """Check if sequence has two consecutive leaps (>2 semitones) in same direction."""
    intervals = _midi_intervals(midi_pitches=midi_pitches)
    for i in range(len(intervals) - 1):
        iv1, iv2 = intervals[i], intervals[i + 1]
        if abs(iv1) > 2 and abs(iv2) > 2:
            if (iv1 > 0 and iv2 > 0) or (iv1 < 0 and iv2 < 0):
                return True
    return False


def _has_unresolved_leading_tone(scale_indices: tuple[int, ...]) -> bool:
    """Check if any leading tone (degree 7 / index 6) fails to resolve to tonic."""
    for i in range(len(scale_indices) - 1):
        idx = scale_indices[i] % 7
        next_idx = scale_indices[i + 1] % 7
        if idx == 6 and next_idx != 0:
            return True
    return False


def _is_melodically_valid(midi_pitches: tuple[int, ...], scale_indices: tuple[int, ...] | None = None) -> bool:
    """Check if MIDI pitch sequence passes all melodic validation."""
    if _has_seventh_leap(midi_pitches=midi_pitches):
        return False
    if _has_tritone_leap(midi_pitches=midi_pitches):
        return False
    if _has_tritone_outline(midi_pitches=midi_pitches):
        return False
    if _has_consecutive_leaps_same_direction(midi_pitches=midi_pitches):
        return False
    if scale_indices is not None and _has_unresolved_leading_tone(scale_indices=scale_indices):
        return False
    return True


def _midi_to_name(midi: int) -> str:
    """Convert MIDI number to note name (e.g., 67 -> G4)."""
    names = ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')
    octave = midi // 12 - 1
    return f"{names[midi % 12]}{octave}"


def _largest_leap_position(intervals: list[int]) -> int:
    """Return 0-indexed position of largest leap, or -1 if no leap."""
    if not intervals:
        return -1
    max_size = 0
    max_pos = -1
    for i, iv in enumerate(intervals):
        if abs(iv) > max_size:
            max_size = abs(iv)
            max_pos = i
    return max_pos if max_size >= MIN_LEAP else -1


def _is_filled(intervals: list[int], leap_pos: int) -> bool:
    """Check if leap at position is followed by contrary stepwise motion."""
    if leap_pos < 0 or leap_pos >= len(intervals) - 1:
        return False
    leap_iv = intervals[leap_pos]
    next_iv = intervals[leap_pos + 1]
    if leap_iv > 0 and next_iv >= 0:
        return False
    if leap_iv < 0 and next_iv <= 0:
        return False
    return 1 <= abs(next_iv) <= 2


def _is_valid_pitch(degrees: tuple[int, ...]) -> tuple[bool, int, str]:
    """Check if pitch sequence has leap + fill. Returns (valid, leap_size, direction)."""
    intervals = _intervals(degrees=degrees)
    leap_pos = _largest_leap_position(intervals=intervals)
    if leap_pos < 0:
        return False, 0, ""
    if not _is_filled(intervals=intervals, leap_pos=leap_pos):
        return False, 0, ""
    leap_size = abs(intervals[leap_pos])
    direction = "up" if intervals[leap_pos] > 0 else "down"
    return True, leap_size, direction


def _random_pitch_sequence(n_notes: int, rng: random.Random) -> tuple[int, ...]:
    """Generate a random pitch sequence of given length."""
    start = rng.choice(TONIC_TRIAD_DEGREES)
    degrees = [start]
    for _ in range(n_notes - 1):
        last = degrees[-1]
        valid_intervals = [
            iv for iv in range(-MAX_INTERVAL, MAX_INTERVAL + 1)
            if MIN_DEGREE <= last + iv <= MAX_DEGREE
        ]
        iv = rng.choice(valid_intervals)
        degrees.append(last + iv)
    return tuple(degrees)


def _sample_valid_head(metre: tuple[int, int], rng: random.Random, max_attempts: int = 100) -> Head | None:
    """Sample a random valid head for the given metre."""
    rhythm_cells = get_rhythm_cells(metre=metre)
    valid_cells = [(r, n) for r, n in rhythm_cells if len(set(r)) >= 2]
    if not valid_cells:
        return None
    for _ in range(max_attempts):
        rhythm, rhythm_name = rng.choice(valid_cells)
        n_notes = len(rhythm)
        degrees = _random_pitch_sequence(n_notes=n_notes, rng=rng)
        valid, leap_size, direction = _is_valid_pitch(degrees=degrees)
        if valid:
            return Head(
                degrees=degrees,
                rhythm=rhythm,
                rhythm_name=rhythm_name,
                leap_size=leap_size,
                leap_direction=direction,
            )
    return None


def _crosses_barline(rhythm: tuple[float, ...], bar_dur: float) -> bool:
    """Check if any note in the rhythm crosses a barline."""
    offset = 0.0
    for dur in rhythm:
        end = offset + dur
        start_bar = int(offset / bar_dur)
        end_bar = int(end / bar_dur)
        if abs(end % bar_dur) < 0.0001:
            end_bar = start_bar
        if start_bar != end_bar:
            return True
        offset = end
    return False


def _combine_head_tail(
    head: Head,
    tail: Tail,
    bar_dur: float,
) -> tuple[tuple[int, ...], tuple[float, ...], int] | None:
    """Combine head and tail into a single subject."""
    tail_degrees = tail_to_degrees(tail=tail, start_degree=head.degrees[-1])
    full_degrees = head.degrees + tail_degrees[1:]
    full_rhythm = head.rhythm + tail.rhythm[1:]
    if _crosses_barline(rhythm=full_rhythm, bar_dur=bar_dur):
        return None
    total_dur = sum(full_rhythm)
    bars = total_dur / bar_dur
    if abs(bars - round(bars)) > 0.001:
        return None
    return full_degrees, full_rhythm, int(round(bars))


def generate_subject(
    mode: str = "major",
    metre: Tuple[int, int] = (4, 4),
    seed: int | None = None,
    tonic_midi: int = 60,
    verbose: bool = False,
    affect: str | None = None,
    max_attempts: int = 500,
) -> GeneratedSubject:
    """Generate a single subject using head + tail construction."""
    if metre not in SUPPORTED_METRES:
        raise ValueError(f"Unsupported metre {metre}. Supported: {SUPPORTED_METRES}")
    rng = random.Random(seed)
    bar_dur = _bar_duration(metre=metre)
    figurae_mgr = get_figurae()
    target_figurae: list[Figura] = []
    affect_profile = None
    if affect:
        target_figurae = figurae_mgr.select_for_motif(affect=affect, tension=0.5)
        affect_profile = get_affect_profile(affect=affect)
    if verbose:
        if affect:
            print(f"Affect: {affect}, target figurae: {[f.name for f in target_figurae]}")
            if affect_profile:
                print(f"  Profile: {affect_profile.interval_profile} intervals, {affect_profile.contour} contour")
    candidates: list[GeneratedSubject] = []
    target_candidates = 50 if affect else 5
    for _ in range(max_attempts):
        if len(candidates) >= target_candidates:
            break
        head = _sample_valid_head(metre=metre, rng=rng)
        if head is None:
            continue
        head_dur = sum(head.rhythm)
        for target_bars in [2, 1, 3, 4]:
            target_total = target_bars * bar_dur
            if target_total <= head_dur:
                continue
            tails = generate_tails_for_head(head=head, target_total=target_total)
            if not tails:
                continue
            tail = rng.choice(tails)
            result = _combine_head_tail(head=head, tail=tail, bar_dur=bar_dur)
            if result is None:
                continue
            degrees, rhythm, bars = result
            if len(set(rhythm)) < 2:
                continue
            fig_score = 0.0
            satisfied: list[str] = []
            if target_figurae:
                fig_score, satisfied = score_motif_figurae(
                    indices=list(degrees), durations=list(rhythm), figurae=target_figurae
                )
            affect_score = 0.0
            if affect_profile:
                affect_score = score_subject_affect(degrees=degrees, durations=rhythm, profile=affect_profile)
            midi_pitches = degrees_to_midi(degrees=degrees, tonic_midi=tonic_midi, mode=mode)
            if not _is_melodically_valid(midi_pitches=midi_pitches, scale_indices=degrees):
                continue
            total_score = 1.0 + fig_score + affect_score
            subject = GeneratedSubject(
                scale_indices=degrees,
                durations=rhythm,
                midi_pitches=midi_pitches,
                bars=bars,
                score=total_score,
                seed=seed or 0,
                mode=mode,
                head_name=head.rhythm_name,
                leap_size=head.leap_size,
                leap_direction=head.leap_direction,
                tail_direction=tail.direction,
                affect=affect,
                figurae_score=fig_score,
                satisfied_figurae=tuple(satisfied),
            )
            candidates.append(subject)
            break
    if not candidates:
        raise RuntimeError(
            f"Failed to generate subject for metre {metre} after {max_attempts} attempts."
        )
    best = max(candidates, key=lambda s: s.score)
    if verbose:
        pitch_str = ' '.join(f"{NOTE_NAMES[m % 12]}{m // 12 - 1}" for m in best.midi_pitches)
        print(f"Subject: {pitch_str}")
        print(f"  Bars: {best.bars}")
        print(f"  Head: {best.head_name}, leap {best.leap_direction} {best.leap_size}")
        print(f"  Tail: {best.tail_direction}")
        if affect:
            print(f"  Figurae score: {best.figurae_score:.2f}, satisfied: {best.satisfied_figurae}")
    return best


def generate_subject_batch(
    mode: str = "major",
    metre: Tuple[int, int] = (4, 4),
    seed: int | None = None,
    tonic_midi: int = 60,
    count: int = 10,
    verbose: bool = False,
) -> List[GeneratedSubject]:
    """Generate multiple subjects with variety."""
    if metre not in SUPPORTED_METRES:
        raise ValueError(f"Unsupported metre {metre}. Supported: {SUPPORTED_METRES}")
    rng = random.Random(seed)
    bar_dur = _bar_duration(metre=metre)
    results: List[GeneratedSubject] = []
    seen_degrees: set[tuple[int, ...]] = set()
    max_attempts = count * 50
    for _ in range(max_attempts):
        if len(results) >= count:
            break
        head = _sample_valid_head(metre=metre, rng=rng)
        if head is None:
            continue
        head_dur = sum(head.rhythm)
        for target_bars in [2, 1, 3, 4]:
            target_total = target_bars * bar_dur
            if target_total <= head_dur:
                continue
            tails = generate_tails_for_head(head=head, target_total=target_total)
            if not tails:
                continue
            tail = rng.choice(tails)
            result = _combine_head_tail(head=head, tail=tail, bar_dur=bar_dur)
            if result is None:
                continue
            degrees, rhythm, bars = result
            if degrees in seen_degrees:
                continue
            if len(set(rhythm)) < 2:
                continue
            midi_pitches = degrees_to_midi(degrees=degrees, tonic_midi=tonic_midi, mode=mode)
            if not _is_melodically_valid(midi_pitches=midi_pitches, scale_indices=degrees):
                continue
            seen_degrees.add(degrees)
            subject = GeneratedSubject(
                scale_indices=degrees,
                durations=rhythm,
                midi_pitches=midi_pitches,
                bars=bars,
                score=1.0,
                seed=seed or 0,
                mode=mode,
                head_name=head.rhythm_name,
                leap_size=head.leap_size,
                leap_direction=head.leap_direction,
                tail_direction=tail.direction,
            )
            results.append(subject)
            if verbose:
                pitch_str = ' '.join(f"{NOTE_NAMES[m % 12]}{m // 12 - 1}" for m in midi_pitches)
                print(f"[{len(results):02d}] {pitch_str} | {bars} bars | {head.rhythm_name}")
            break
    return results


def generate_fugue_triple(
    mode: str = "minor",
    metre: Tuple[int, int] = (4, 4),
    seed: int | None = None,
    tonic_midi: int = 67,
    verbose: bool = False,
) -> FugueTriple:
    """Generate coordinated subject, answer, and countersubject."""
    from motifs.answer_generator import generate_answer, GeneratedAnswer
    from motifs.countersubject_generator import generate_countersubject, GeneratedCountersubject
    subject = generate_subject(
        mode=mode,
        metre=metre,
        seed=seed,
        tonic_midi=tonic_midi,
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
    )
    assert cs is not None, "Countersubject generation failed"
    return FugueTriple(
        subject=subject,
        answer=answer,
        countersubject=cs,
        metre=metre,
        tonic_midi=tonic_midi,
        seed=seed or 0,
    )


def write_fugue_file(triple: FugueTriple, path: Path) -> None:
    """Write fugue triple to YAML .fugue file."""
    tonic_name = _midi_to_name(triple.tonic_midi).rstrip('0123456789')
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
    }
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def write_fugue_demo_midi(triple: FugueTriple, path: Path, tempo: int = 80) -> None:
    """Write demonstration MIDI showing subject, answer, CS, and combinations."""
    bar_dur = _bar_duration(metre=triple.metre)
    notes: list[SimpleNote] = []
    offset = 0.0
    def add_melody(pitches: tuple[int, ...], durations: tuple[float, ...], track: int, start: float) -> float:
        """Add a melody to notes list, return end offset."""
        pos = start
        for pitch, dur in zip(pitches, durations):
            notes.append(SimpleNote(pitch=pitch, offset=pos, duration=dur, velocity=80, track=track))
            pos += dur
        return pos
    offset = add_melody(
        pitches=triple.subject.midi_pitches,
        durations=triple.subject.durations,
        track=0,
        start=offset,
    )
    offset += bar_dur
    offset = add_melody(
        pitches=triple.answer.midi_pitches,
        durations=triple.answer.durations,
        track=0,
        start=offset,
    )
    offset += bar_dur
    offset = add_melody(
        pitches=triple.countersubject.midi_pitches,
        durations=triple.countersubject.durations,
        track=0,
        start=offset,
    )
    offset += bar_dur
    subj_end = add_melody(
        pitches=triple.subject.midi_pitches,
        durations=triple.subject.durations,
        track=0,
        start=offset,
    )
    cs_pitches_low = tuple(p - 12 for p in triple.countersubject.midi_pitches)
    add_melody(
        pitches=cs_pitches_low,
        durations=triple.countersubject.durations,
        track=1,
        start=offset,
    )
    offset = subj_end + bar_dur
    ans_end = add_melody(
        pitches=triple.answer.midi_pitches,
        durations=triple.answer.durations,
        track=0,
        start=offset,
    )
    add_melody(
        pitches=cs_pitches_low,
        durations=triple.countersubject.durations,
        track=1,
        start=offset,
    )
    offset = ans_end + bar_dur
    add_melody(
        pitches=cs_pitches_low,
        durations=triple.countersubject.durations,
        track=1,
        start=offset,
    )
    cs_end = add_melody(
        pitches=triple.subject.midi_pitches,
        durations=triple.subject.durations,
        track=0,
        start=offset,
    )
    tonic_name = _midi_to_name(triple.tonic_midi).rstrip('0123456789')
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
        name = _midi_to_name(midi)
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
    parser.add_argument("--output", "-o", type=Path, default=Path("subject"),
                        help="Output path without extension (default: subject)")
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
    parser.add_argument("--affect", "-a", type=str, default=None,
                        help="Affect name for figurae scoring")
    parser.add_argument("--batch", "-b", type=int, default=None,
                        help="Generate batch of N subjects")
    parser.add_argument("--fugue", "-f", action="store_true",
                        help="Generate full fugue triple (subject + answer + countersubject)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print details")
    args = parser.parse_args()
    metre_parts = args.metre.split("/")
    metre = (int(metre_parts[0]), int(metre_parts[1]))
    tonic_midi = {"C": 60, "D": 62, "E": 64, "F": 65, "G": 67, "A": 69, "B": 71,
                  "C#": 61, "Db": 61, "D#": 63, "Eb": 63, "F#": 66, "Gb": 66,
                  "G#": 68, "Ab": 68, "A#": 70, "Bb": 70}.get(args.tonic, 60)
    if args.fugue:
        triple = generate_fugue_triple(
            mode=args.mode,
            metre=metre,
            seed=args.seed,
            tonic_midi=tonic_midi,
            verbose=args.verbose,
        )
        fugue_path = args.output.with_suffix(".fugue")
        midi_path = args.output.with_suffix(".midi")
        write_fugue_file(triple=triple, path=fugue_path)
        write_fugue_demo_midi(triple=triple, path=midi_path, tempo=args.tempo)
        print(f"Wrote {fugue_path} and {midi_path}")
        if args.verbose:
            print(f"  Subject: {triple.subject.scale_indices}")
            print(f"  Answer:  {triple.answer.scale_indices} ({triple.answer.answer_type})")
            print(f"  CS:      {triple.countersubject.scale_indices}")
    elif args.batch:
        subjects = generate_subject_batch(
            mode=args.mode,
            metre=metre,
            seed=args.seed,
            tonic_midi=tonic_midi,
            count=args.batch,
            verbose=args.verbose,
        )
        for i, subj in enumerate(subjects):
            base = args.output.parent / f"{args.output.stem}_{i:02d}"
            write_note_file(subj, base.with_suffix(".note"))
            write_midi_file(subj, base.with_suffix(".midi"), args.tempo, args.tonic)
            if args.verbose:
                print(f"  Wrote {base}.note and {base}.midi")
        print(f"Generated {len(subjects)} subjects")
    else:
        subject = generate_subject(
            mode=args.mode,
            metre=metre,
            seed=args.seed,
            tonic_midi=tonic_midi,
            verbose=args.verbose,
            affect=args.affect,
        )
        write_note_file(subject, args.output.with_suffix(".note"))
        write_midi_file(subject, args.output.with_suffix(".midi"), args.tempo, args.tonic)
        print(f"Wrote {args.output}.note and {args.output}.midi ({subject.bars} bars)")


if __name__ == "__main__":
    main()
