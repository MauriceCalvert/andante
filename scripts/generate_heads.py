"""Generate head motifs and write to files.

Usage:
    python -m scripts.generate_heads
    python -m scripts.generate_heads --count 20
"""
import argparse
import os
import random
import sys
from pathlib import Path

from motifs.head_generator import generate_heads, degrees_to_midi, head_to_str, Head, NOTE_NAMES
from engine.output import Music21Writer
from engine.note import Note


ANDANTE_ROOT: Path = Path(__file__).parent.parent
DEFAULT_OUTPUT_DIR: Path = ANDANTE_ROOT / "output" / "heads"


def write_head(head: Head, index: int, output_dir: str, tonic: int, mode: str) -> None:
    """Write a head to MIDI and MusicXML."""
    midi_pitches = degrees_to_midi(head.degrees, tonic, mode)

    print(f"[head_{index:02d}] {head_to_str(head, tonic, mode)}")

    os.makedirs(output_dir, exist_ok=True)

    filename = f"head_{index:02d}"
    base_path = os.path.join(output_dir, filename)

    # Convert to engine.Note list for Music21Writer
    notes: list[Note] = []
    offset = 0.0
    for pitch, dur in zip(midi_pitches, head.rhythm):
        notes.append(Note(midiNote=pitch, Offset=offset, Duration=dur, track=0))
        offset += dur

    # Write MIDI + MusicXML
    tonic_name = NOTE_NAMES[tonic % 12]
    writer = Music21Writer()
    writer.write(base_path, notes, tonic=tonic_name, mode=mode, bpm=90)


def sample_diverse(heads: list[Head], count: int) -> list[Head]:
    """Sample diverse heads by varying leap size, direction, and rhythm."""
    # Group by (leap_size, leap_direction, rhythm_name, n_notes)
    buckets: dict[tuple, list[Head]] = {}
    for h in heads:
        key = (h.leap_size, h.leap_direction, h.rhythm_name, len(h.degrees))
        buckets.setdefault(key, []).append(h)

    # Sample from each bucket
    sampled = []
    bucket_keys = list(buckets.keys())
    random.shuffle(bucket_keys)

    for key in bucket_keys:
        if len(sampled) >= count:
            break
        h = random.choice(buckets[key])
        sampled.append(h)

    return sampled


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate head motifs")
    parser.add_argument("--count", type=int, default=20, help="Number of heads to output")
    parser.add_argument("--tonic", type=int, default=60, help="MIDI note for tonic (60=C4)")
    parser.add_argument("--mode", type=str, default="major", choices=["major", "minor"])
    parser.add_argument("--output-dir", type=str, default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling")

    args = parser.parse_args()
    random.seed(args.seed)

    # Generate all valid heads
    all_heads = generate_heads()
    print(f"Total valid heads: {len(all_heads)}")

    # Sample diverse subset
    heads = sample_diverse(all_heads, args.count)
    print(f"Sampled {len(heads)} diverse heads\n")

    print("=" * 60)
    for i, head in enumerate(heads, 1):
        write_head(head, i, args.output_dir, args.tonic, args.mode)

    print("=" * 60)
    print(f"\nWrote {len(heads)} heads to {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
