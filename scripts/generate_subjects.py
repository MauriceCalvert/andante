"""Generate subjects by combining heads with derived tails.

Usage:
    python -m scripts.generate_subjects_v2
    python -m scripts.generate_subjects_v2 --count 20
"""
import argparse
import os
import random
import sys
from pathlib import Path

from motifs.head_generator import generate_heads, degrees_to_midi, Head, NOTE_NAMES
from motifs.tail_generator import generate_tails_for_head, tail_to_degrees, Tail
from engine.output import Music21Writer
from engine.note import Note


ANDANTE_ROOT: Path = Path(__file__).parent.parent
DEFAULT_OUTPUT_DIR: Path = ANDANTE_ROOT / "output" / "subjects_v2"


def _crosses_barline(rhythm: tuple[float, ...]) -> bool:
    """Check if any note in the rhythm crosses a barline."""
    offset = 0.0
    for dur in rhythm:
        end = offset + dur
        # Crosses if start and end are in different bars (and doesn't end exactly on barline)
        if int(offset) != int(end) and abs(end % 1.0) > 0.001:
            return True
        offset = end
    return False


def combine_head_tail(
    head: Head,
    tail: Tail,
) -> tuple[tuple[int, ...], tuple[float, ...]] | None:
    """Combine head and tail into a single subject.

    Returns None if rhythm crosses barlines.
    """
    # Tail starts from last degree of head
    tail_degrees = tail_to_degrees(tail, head.degrees[-1])
    # Skip first note of tail (it's the same as last note of head)
    full_degrees = head.degrees + tail_degrees[1:]
    # Skip first duration of tail (shared note)
    full_rhythm = head.rhythm + tail.rhythm[1:]

    # Reject if any note crosses a barline
    if _crosses_barline(full_rhythm):
        return None

    return full_degrees, full_rhythm


def subject_to_str(head: Head, tail: Tail, degrees: tuple[int, ...], tonic: int, mode: str) -> str:
    """Format subject as readable string."""
    midi = degrees_to_midi(degrees, tonic, mode)
    pitch_str = ' '.join(f"{NOTE_NAMES[m % 12]}{m // 12 - 1}" for m in midi)
    return f"{pitch_str} | head: {head.rhythm_name} leap {head.leap_direction} {head.leap_size} | tail: {tail.direction}"


def write_subject(
    head: Head,
    tail: Tail,
    degrees: tuple[int, ...],
    rhythm: tuple[float, ...],
    index: int,
    output_dir: str,
    tonic: int,
    mode: str,
) -> None:
    """Write a subject to MIDI and MusicXML."""
    midi_pitches = degrees_to_midi(degrees, tonic, mode)

    print(f"[subject_{index:02d}] {subject_to_str(head, tail, degrees, tonic, mode)}")

    os.makedirs(output_dir, exist_ok=True)

    filename = f"subject_{index:02d}"
    base_path = os.path.join(output_dir, filename)

    # Convert to engine.Note list
    notes: list[Note] = []
    offset = 0.0
    for pitch, dur in zip(midi_pitches, rhythm):
        notes.append(Note(midiNote=pitch, Offset=offset, Duration=dur, track=0))
        offset += dur

    # Write MIDI + MusicXML
    tonic_name = NOTE_NAMES[tonic % 12]
    writer = Music21Writer()
    writer.write(base_path, notes, tonic=tonic_name, mode=mode, bpm=90)


def sample_subjects(
    heads: list[Head],
    count: int,
) -> list[tuple[Head, Tail, tuple[int, ...], tuple[float, ...]]]:
    """Sample head+tail combinations.

    For each head, generates valid tails derived from that head's rhythm vocabulary.
    Filters for exactly 3 distinct durations in combined subject.
    """
    # Group heads by (leap_size, leap_direction, duration)
    head_buckets: dict[tuple, list[Head]] = {}
    for h in heads:
        dur = round(sum(h.rhythm), 2)
        key = (h.leap_size, h.leap_direction, dur)
        head_buckets.setdefault(key, []).append(h)

    print(f"Head buckets: {len(head_buckets)}")

    sampled = []
    attempts = 0
    max_attempts = count * 200

    bucket_keys = list(head_buckets.keys())

    while len(sampled) < count and attempts < max_attempts:
        attempts += 1

        # Pick random head bucket
        key = random.choice(bucket_keys)
        head = random.choice(head_buckets[key])

        # Generate tails for this head
        tails = generate_tails_for_head(head)
        if not tails:
            continue

        # Pick random tail
        tail = random.choice(tails)

        # Combine (returns None if crosses barline)
        result = combine_head_tail(head, tail)
        if result is None:
            continue

        degrees, rhythm = result

        # Must have exactly 3 distinct durations
        if len(set(rhythm)) != 3:
            continue

        sampled.append((head, tail, degrees, rhythm))

    return sampled


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate subjects (head + tail)")
    parser.add_argument("--count", type=int, default=20, help="Number of subjects to output")
    parser.add_argument("--tonic", type=int, default=60, help="MIDI note for tonic (60=C4)")
    parser.add_argument("--mode", type=str, default="major", choices=["major", "minor"])
    parser.add_argument("--output-dir", type=str, default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--seed", type=int, default=42, help="Random seed")

    args = parser.parse_args()
    random.seed(args.seed)

    # Generate all valid heads
    heads = generate_heads()
    print(f"Heads: {len(heads)}")

    # Sample combinations
    subjects = sample_subjects(heads, args.count)
    print(f"Sampled {len(subjects)} subjects (exactly 3 distinct durations, 2 bars)\n")

    print("=" * 70)
    for i, (head, tail, degrees, rhythm) in enumerate(subjects, 1):
        write_subject(head, tail, degrees, rhythm, i, args.output_dir, args.tonic, args.mode)

    print("=" * 70)
    print(f"\nWrote {len(subjects)} subjects to {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
